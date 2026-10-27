"""Four-agent pipeline.

Agent 1 is the NumPy telemetry engine. Agents 2 and 3 are Semantic Kernel
ChatCompletionAgents pointed at the AIML API. Agent 4 is the grounding auditor
and always runs. A missing key, a timeout, or bad JSON hands the blackboard
to the deterministic templates. Latencies are measured with perf_counter.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any

from backend.agents.blackboard import MatchBlackboardState
from backend.agents.fallback import _clip, causal_from_copy, render_copy
from backend.agents.grounding import audit_text, build_badges, epistemic_note
from backend.agents.prompts import AGENT2_LIVE, AGENT3_LIVE, STRUGGLE_LIVE
from backend.engine.auto_event import auto_event_segment
from backend.engine.telemetry_engine import build_telemetry, match_rollup
from backend.synthetic.squads import BY_ID

AIML_BASE_URL = "https://api.aimlapi.com/v1"
AIML_MODEL = "gpt-4o-mini"
# Per-agent ceiling. Agents 2 and 3 run together, so the wall clock is the
# slower of the two, not the sum. Eight seconds is enough for a slim gpt-4o-mini
# call and still far inside a 60-second Vercel function. A hung call hands the
# blackboard to the template. The template path itself stays under 20 ms.
AGENT_TIMEOUT_S = 8.0
MAX_TOKENS = 320

TURNING_POINTS = (22, 54, 82)


def _key() -> str:
    return os.environ.get("AIML_API_KEY", "").strip()


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if content is None:
        return str(message)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(getattr(item, "text", item)))
        return "\n".join(parts)
    return str(content)


def _parse_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model returned no JSON object")
    parsed = json.loads(raw[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model JSON was not an object")
    return parsed


_TEAM_KEYS = (
    "ppda_5m",
    "ppda_baseline",
    "possession_pct_5m",
    "pass_accuracy_5m",
    "xt_central_5m",
    "xt_central_baseline",
)

_ES_WORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "que", "en", "y", "se",
    "por", "con", "al", "nuestro", "nuestra", "nos", "para", "su", "sus", "más",
    "porque", "cuando", "pero", "está", "esta", "medio", "lateral",
}
_EN_WORDS = {
    "the", "and", "our", "we", "of", "to", "in", "is", "are", "with", "from",
    "their", "this", "that", "into", "inside", "while", "after", "because",
    "full", "back", "steps", "opens", "middle", "block",
}

_client = None


def _aiml_client():
    """One AsyncOpenAI client for the process. Built only when a key is set."""
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        _client = AsyncOpenAI(api_key=_key(), base_url=AIML_BASE_URL, timeout=AGENT_TIMEOUT_S + 1)
    return _client


def _team_slice(team: dict | None) -> dict:
    team = team or {}
    return {key: team[key] for key in _TEAM_KEYS if team.get(key) is not None}


def _facts(telemetry: dict) -> dict:
    """The slice the model is allowed to see. No 22-player board, no raw windows."""
    anomalies = []
    for row in (telemetry.get("tactical_anomalies") or [])[:2]:
        anomalies.append(
            {
                "type": row.get("anomaly_type"),
                "proof": row.get("metric_proof"),
                "player": row.get("primary_player_name"),
                "shift_m": row.get("shift_distance_m"),
                "zone": row.get("zone_numerical_state"),
                "peak_kmh": row.get("peak_speed_kmh"),
            }
        )
    highlights = []
    for row in (telemetry.get("speed_and_pass_highlights") or [])[:3]:
        highlights.append(
            {
                "type": row.get("type"),
                "value": row.get("value"),
                "player": row.get("player_name"),
                "ball_kmh": row.get("ball_speed_kmh"),
            }
        )
    spot = telemetry.get("player_spotlight_telemetry") or None
    spotlight = None
    if spot:
        spotlight = {
            "player_id": spot.get("player_id"),
            "name": spot.get("player_name"),
            "shirt": spot.get("shirt_number"),
            "max_speed_kmh": spot.get("max_speed_kmh"),
            "avg_pass_difficulty": spot.get("avg_pass_difficulty"),
            "distance_5m_m": spot.get("distance_5m_m"),
        }
    teams = telemetry.get("team_metrics") or {}
    return {
        "minute": telemetry.get("current_minute"),
        "scoreline": telemetry.get("scoreline"),
        "cci": telemetry.get("control_vs_chaos_index"),
        "rhythm": telemetry.get("rhythm_state"),
        "anomalies": anomalies,
        "highlights": highlights,
        "nlr": _team_slice(teams.get("NLR")),
        "mcb": _team_slice(teams.get("MCB")),
        "flank_press_drop": telemetry.get("nlr_flank_press_drop"),
        "final_third_entries_5m": telemetry.get("nlr_final_third_entries_5m"),
        "spotlight": spotlight,
        "rollup": telemetry.get("match_rollup"),
    }


def _in_language(text: str, language: str) -> bool:
    if language == "ar":
        return bool(re.search(r"[\u0600-\u06FF]", text or ""))
    if language != "es":
        return True
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", text or "")
    low = [word.lower() for word in words]
    spanish = sum(word in _ES_WORDS for word in low)
    english = sum(word in _EN_WORDS for word in low)
    if re.search(r"[áéíóúñÁÉÍÓÚÑ¿¡]", text or ""):
        spanish += 2
    return spanish > english


def _pin_locale(headline: str, narrative: str, why: str, telemetry: dict, copy_args: dict) -> tuple[str, str, str]:
    """Spanish and Arabic lower-thirds come from the localized templates.

    The model often translates the narrative and leaves the headline in English.
    Headline, why-it-matters, and therefore the lower-third title and subtitle
    are pinned. A narrative that is already in the target language is kept.
    """
    language = copy_args.get("language") or "en"
    if language == "en":
        return headline, narrative, why
    local = render_copy(telemetry, **copy_args)
    if not _in_language(narrative, language):
        narrative = local["narrative_body"]
    return local["headline"], narrative, local["why_it_matters"]


async def _timed_agent(name: str, instructions: str, user: str, max_tokens: int = MAX_TOKENS):
    started = time.perf_counter()
    try:
        raw = await asyncio.wait_for(
            _invoke_agent(name, instructions, user, max_tokens=max_tokens),
            timeout=AGENT_TIMEOUT_S,
        )
        return _parse_json(raw), "ok", _ms(started), None
    except Exception as exc:  # noqa: BLE001 — failure recovery is the product
        return None, "recovered", _ms(started), exc


async def _invoke_agent(name: str, instructions: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
    """Lazy Semantic Kernel import so a keyless demo never loads the package."""
    from semantic_kernel.agents import ChatCompletionAgent
    from semantic_kernel.connectors.ai.open_ai import (
        OpenAIChatCompletion,
        OpenAIChatPromptExecutionSettings,
    )
    from semantic_kernel.contents import ChatHistory
    from semantic_kernel.kernel import Kernel

    client = _aiml_client()
    service = OpenAIChatCompletion(ai_model_id=AIML_MODEL, async_client=client, service_id="aiml")
    kernel = Kernel()
    kernel.add_service(service)
    settings = OpenAIChatPromptExecutionSettings(
        service_id="aiml",
        temperature=0.2,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    agent = ChatCompletionAgent(
        service_id="aiml",
        kernel=kernel,
        name=name,
        instructions=instructions,
        execution_settings=settings,
    )
    history = ChatHistory()
    history.add_user_message(user)
    chunks: list[str] = []
    async for message in agent.invoke(history):
        chunks.append(_message_text(message))
    return "\n".join(chunks)


def _spotlight_block(telemetry: dict, player_id: str | None) -> dict | None:
    if not player_id:
        return None
    block = telemetry.get("player_spotlight_telemetry")
    if block and block.get("player_id") == player_id:
        return block
    return None


def _preferences(body: dict) -> dict:
    return {
        "persona": body.get("persona") or "CASUAL_FAN",
        "favorite_club": body.get("favorite_club") or "NLR",
        "spotlight_player_id": body.get("spotlight_player_id") or None,
        "language": body.get("language") or "en",
        "custom_question": body.get("custom_question") or None,
        "intent": body.get("intent") or "analyze",
    }


async def run_analyze(body: dict) -> dict:
    prefs = _preferences(body)
    minute = int(body.get("minute") or 54)
    minute = min(90, max(1, minute))
    spotlight_id = prefs["spotlight_player_id"]
    if spotlight_id and spotlight_id not in BY_ID:
        spotlight_id = None
        prefs["spotlight_player_id"] = None

    board = MatchBlackboardState()
    t0 = time.perf_counter()
    telemetry = build_telemetry(minute=minute, spotlight_player_id=spotlight_id)
    if minute == 90:
        telemetry["match_rollup"] = match_rollup()
    board.telemetry = telemetry
    agent1_ms = _ms(t0)
    board.handoff("Agent 1 Telemetry", "Agent 2 Causality", "TelemetryStatePayload written to the blackboard")

    copy_args = dict(
        persona=prefs["persona"],
        language=prefs["language"],
        favorite_club=prefs["favorite_club"],
        spotlight=_spotlight_block(telemetry, spotlight_id),
        intent=prefs["intent"] if prefs["intent"] == "diagnose" else None,
    )
    mode = "semantic_kernel"
    agent2_status = "ok"
    agent3_status = "ok"
    causal: dict | None = None
    personal: dict | None = None

    if not _key():
        mode = "fallback"
        agent2_status = "fallback"
        agent3_status = "fallback"
        board.errors.append("AIML_API_KEY empty; Agents 2 and 3 used deterministic templates")
        t2 = time.perf_counter()
        causal = causal_from_copy(render_copy(telemetry, **copy_args), telemetry)
        agent2_ms = _ms(t2)
        t3 = time.perf_counter()
        personal = render_copy(telemetry, **copy_args)
        agent3_ms = _ms(t3)
        board.handoff("Agent 2 Causality", "Fallback template", "no API key")
    else:
        facts = _facts(telemetry)
        analyst_user = json.dumps(
            {"facts": facts, "question": prefs["custom_question"], "intent": prefs["intent"]},
            ensure_ascii=False,
        )
        personal_user = json.dumps({"facts": facts, "preferences": prefs}, ensure_ascii=False)
        (causal, agent2_status, agent2_ms, err2), (personal, agent3_status, agent3_ms, err3) = await asyncio.gather(
            _timed_agent("CausalAnalyst", AGENT2_LIVE, analyst_user),
            _timed_agent("BroadcastPersonalizer", AGENT3_LIVE, personal_user),
        )
        board.handoff("Agent 1 Telemetry", "Agent 2 and Agent 3", "parallel slim facts")
        if err2 is not None:
            board.errors.append(f"Agent 2 failed ({type(err2).__name__}); deterministic template took the handoff")
            board.handoff("Agent 2 Causality", "Fallback template", type(err2).__name__)
        if err3 is not None:
            mode = "fallback"
            board.errors.append(f"Agent 3 failed ({type(err3).__name__}); deterministic template took the handoff")
            board.handoff("Agent 3 Personalizer", "Fallback template", type(err3).__name__)
            personal = render_copy(telemetry, **copy_args)
        if causal is None:
            causal = causal_from_copy(personal if isinstance(personal, dict) else render_copy(telemetry, **copy_args), telemetry)

    board.causal = causal
    board.personalization = personal
    if agent3_status == "ok":
        board.handoff("Agent 3 Personalizer", "Agent 4 Auditor", "personalized copy")
    else:
        board.handoff("Fallback template", "Agent 4 Auditor", "deterministic copy")

    t4 = time.perf_counter()
    headline = str((personal or {}).get("headline") or "")
    narrative = str((personal or {}).get("narrative_body") or (personal or {}).get("narrative") or "")
    why = str((personal or {}).get("why_it_matters") or (causal or {}).get("why_it_matters") or "")
    audited_headline, kept_h, strip_h = audit_text(headline, telemetry)
    audited_narrative, kept_n, strip_n = audit_text(narrative, telemetry)
    audited_why, kept_w, strip_w = audit_text(why, telemetry)
    stripped = strip_h + strip_n + strip_w
    kept = kept_h + kept_n + kept_w
    if stripped >= 2 or not audited_narrative:
        replacement = render_copy(telemetry, **copy_args)
        audited_headline = replacement["headline"]
        audited_narrative = replacement["narrative_body"]
        audited_why = replacement["why_it_matters"]
        personal = replacement
        board.errors.append("Agent 4 replaced ungrounded prose with the deterministic narrative")
        board.handoff("Agent 4 Auditor", "Fallback template", f"stripped {stripped} numbers")
        mode = "fallback"
    model_note = None
    if prefs["custom_question"] and isinstance(causal, dict):
        model_note = causal.get("uncertainty_note")
    note = epistemic_note(prefs["custom_question"], model_note, stripped)
    # Do not let a model note smuggle an ungrounded number past the auditor.
    if note:
        note, _, note_stripped = audit_text(note, telemetry)
        if note_stripped:
            note = epistemic_note(prefs["custom_question"], None, note_stripped)
    audited_headline, audited_narrative, audited_why = _pin_locale(
        audited_headline, audited_narrative, audited_why, telemetry, copy_args
    )
    audited_headline = _clip(audited_headline, 12)
    audited_narrative = _clip(audited_narrative, 55)
    audited_why = _clip(audited_why, 40)
    badges = build_badges(telemetry, prefs["language"])
    # Coordinates and the lower-third title/subtitle come from the engine copy.
    overlay = render_copy(telemetry, **copy_args)["broadcast_overlay"]
    overlay["title"] = audited_headline
    overlay["subtitle"] = audited_why
    agent4_ms = _ms(t4)
    board.audit = {"kept": kept, "stripped": stripped}
    board.handoff("Agent 4 Auditor", "Broadcast", "grounded insight")

    trace = [
        {
            "agent_id": "agent_1",
            "name": "Telemetry Engine",
            "role": "Ingest and interpret the event stream with NumPy",
            "stage": "interpret",
            "latency_ms": agent1_ms,
            "status": "ok",
        },
        {
            "agent_id": "agent_2",
            "name": "Causal Analyst",
            "role": "Explain why the anomaly matters",
            "stage": "explain",
            "latency_ms": agent2_ms,
            "status": agent2_status,
        },
        {
            "agent_id": "agent_3",
            "name": "Broadcast Personalizer",
            "role": "Render persona, language, club, and spotlight",
            "stage": "personalize",
            "latency_ms": agent3_ms,
            "status": agent3_status,
        },
        {
            "agent_id": "agent_4",
            "name": "Grounding Auditor",
            "role": "Strip any number the telemetry cannot support",
            "stage": "render",
            "latency_ms": agent4_ms,
            "status": "ok",
        },
    ]
    return {
        "mode": mode,
        "orchestrator": "Microsoft Semantic Kernel",
        "minute": minute,
        "persona": prefs["persona"],
        "language": prefs["language"],
        "favorite_club": prefs["favorite_club"],
        "spotlight_player_id": spotlight_id,
        "intent": prefs["intent"],
        "headline": audited_headline,
        "narrative_body": audited_narrative,
        "why_it_matters": audited_why,
        "epistemic_note": note,
        "badges": badges,
        "broadcast_overlay": overlay,
        "rhythm_state": telemetry.get("rhythm_state"),
        "control_vs_chaos_index": telemetry.get("control_vs_chaos_index"),
        "scoreline": telemetry.get("scoreline"),
        "telemetry": telemetry,
        "positions_22_players": telemetry.get("positions_22_players"),
        "agent_trace": trace,
        "handoffs": board.handoffs,
        "errors": board.errors,
        "audit": board.audit,
    }


async def run_diagnose(body: dict) -> dict:
    """One compact ChatCompletionAgent, then Agent 4. Not the two-call analyze chain."""
    payload = dict(body)
    payload["intent"] = "diagnose"
    payload["favorite_club"] = body.get("team_id") or body.get("favorite_club") or "NLR"
    if not payload.get("custom_question"):
        payload["custom_question"] = "Why are we struggling?"
    if not _key():
        return await run_analyze(payload)

    prefs = _preferences(payload)
    minute = min(90, max(1, int(payload.get("minute") or 54)))
    spotlight_id = prefs["spotlight_player_id"]
    if spotlight_id and spotlight_id not in BY_ID:
        spotlight_id = None
        prefs["spotlight_player_id"] = None
    board = MatchBlackboardState()
    t0 = time.perf_counter()
    telemetry = build_telemetry(minute=minute, spotlight_player_id=spotlight_id)
    if minute == 90:
        telemetry["match_rollup"] = match_rollup()
    board.telemetry = telemetry
    agent1_ms = _ms(t0)
    copy_args = dict(
        persona=prefs["persona"],
        language=prefs["language"],
        favorite_club=prefs["favorite_club"],
        spotlight=_spotlight_block(telemetry, spotlight_id),
        intent="diagnose",
    )
    user = json.dumps(
        {"facts": _facts(telemetry), "preferences": prefs, "question": prefs["custom_question"]},
        ensure_ascii=False,
    )
    personal, agent2_status, agent2_ms, err = await _timed_agent(
        "StruggleDesk", STRUGGLE_LIVE, user, max_tokens=280
    )
    agent3_status = "combined"
    agent3_ms = 0.0
    mode = "semantic_kernel"
    if err is not None or not isinstance(personal, dict):
        mode = "fallback"
        agent2_status = "recovered"
        agent3_status = "fallback"
        board.errors.append(
            f"Agent 2 failed ({type(err).__name__ if err else 'bad JSON'}); deterministic template took the handoff"
        )
        board.handoff("Struggle desk", "Fallback template", type(err).__name__ if err else "bad JSON")
        personal = render_copy(telemetry, **copy_args)
    else:
        board.handoff("Agent 1 Telemetry", "Struggle desk", "single compact call")
    causal = causal_from_copy(personal, telemetry) if not isinstance(personal, dict) or "cited_metrics" not in personal else {
        "causal_diagnosis": personal.get("headline"),
        "why_it_matters": personal.get("why_it_matters"),
        "cited_metrics": [],
        "uncertainty_note": personal.get("uncertainty_note"),
    }
    board.causal = causal
    board.personalization = personal
    board.handoff("Struggle desk", "Agent 4 Auditor", "one-call copy")

    t4 = time.perf_counter()
    headline = str((personal or {}).get("headline") or "")
    narrative = str((personal or {}).get("narrative_body") or "")
    why = str((personal or {}).get("why_it_matters") or "")
    audited_headline, kept_h, strip_h = audit_text(headline, telemetry)
    audited_narrative, kept_n, strip_n = audit_text(narrative, telemetry)
    audited_why, kept_w, strip_w = audit_text(why, telemetry)
    stripped = strip_h + strip_n + strip_w
    kept = kept_h + kept_n + kept_w
    if stripped >= 2 or not audited_narrative:
        replacement = render_copy(telemetry, **copy_args)
        audited_headline = replacement["headline"]
        audited_narrative = replacement["narrative_body"]
        audited_why = replacement["why_it_matters"]
        board.errors.append("Agent 4 replaced ungrounded prose with the deterministic narrative")
        board.handoff("Agent 4 Auditor", "Fallback template", f"stripped {stripped} numbers")
        mode = "fallback"
    note = epistemic_note(prefs["custom_question"], None, stripped)
    audited_headline, audited_narrative, audited_why = _pin_locale(
        audited_headline, audited_narrative, audited_why, telemetry, copy_args
    )
    audited_headline = _clip(audited_headline, 12)
    audited_narrative = _clip(audited_narrative, 55)
    audited_why = _clip(audited_why, 40)
    badges = build_badges(telemetry, prefs["language"])
    overlay = render_copy(telemetry, **copy_args)["broadcast_overlay"]
    overlay["title"] = audited_headline
    overlay["subtitle"] = audited_why
    agent4_ms = _ms(t4)
    board.audit = {"kept": kept, "stripped": stripped}
    board.handoff("Agent 4 Auditor", "Broadcast", "grounded struggle answer")
    return {
        "mode": mode,
        "orchestrator": "Microsoft Semantic Kernel",
        "minute": minute,
        "persona": prefs["persona"],
        "language": prefs["language"],
        "favorite_club": prefs["favorite_club"],
        "spotlight_player_id": spotlight_id,
        "intent": "diagnose",
        "headline": audited_headline,
        "narrative_body": audited_narrative,
        "why_it_matters": audited_why,
        "epistemic_note": note,
        "badges": badges,
        "broadcast_overlay": overlay,
        "rhythm_state": telemetry.get("rhythm_state"),
        "control_vs_chaos_index": telemetry.get("control_vs_chaos_index"),
        "scoreline": telemetry.get("scoreline"),
        "telemetry": telemetry,
        "positions_22_players": telemetry.get("positions_22_players"),
        "agent_trace": [
            {
                "agent_id": "agent_1",
                "name": "Telemetry Engine",
                "role": "Ingest and interpret the event stream with NumPy",
                "stage": "interpret",
                "latency_ms": agent1_ms,
                "status": "ok",
            },
            {
                "agent_id": "agent_2",
                "name": "Causal Analyst",
                "role": "Single compact struggle call",
                "stage": "explain",
                "latency_ms": agent2_ms,
                "status": agent2_status,
            },
            {
                "agent_id": "agent_3",
                "name": "Broadcast Personalizer",
                "role": "Folded into the single struggle call",
                "stage": "personalize",
                "latency_ms": agent3_ms,
                "status": agent3_status,
            },
            {
                "agent_id": "agent_4",
                "name": "Grounding Auditor",
                "role": "Strip any number the telemetry cannot support",
                "stage": "render",
                "latency_ms": agent4_ms,
                "status": "ok",
            },
        ],
        "handoffs": board.handoffs,
        "errors": board.errors,
        "audit": board.audit,
    }


def run_auto_event(segment_minute: int) -> dict:
    started = time.perf_counter()
    result = auto_event_segment(segment_minute)
    result["latency_ms"] = _ms(started)
    result["agent"] = "Telemetry Engine"
    return result


async def run_recap(persona: str, language: str, favorite_club: str) -> dict:
    started = time.perf_counter()
    cards = []
    template_ms = 0.0
    audit_ms = 0.0
    for minute in TURNING_POINTS:
        telemetry = build_telemetry(minute=minute)
        if minute == 90:
            telemetry["match_rollup"] = match_rollup()
        t_copy = time.perf_counter()
        copy = render_copy(
            telemetry,
            persona=persona,
            language=language,
            favorite_club=favorite_club,
            spotlight=None,
        )
        template_ms += _ms(t_copy)
        t_audit = time.perf_counter()
        headline, _, _ = audit_text(copy["headline"], telemetry)
        narrative, _, _ = audit_text(copy["narrative_body"], telemetry)
        audit_ms += _ms(t_audit)
        cards.append(
            {
                "minute": minute,
                "headline": headline,
                "narrative_body": narrative,
                "badges": build_badges(telemetry, language),
                "scoreline": telemetry["scoreline"],
                "rhythm_state": telemetry["rhythm_state"],
                "control_vs_chaos_index": telemetry["control_vs_chaos_index"],
            }
        )
    roll = match_rollup()
    agent1 = _ms(started)
    return {
        "mode": "fallback",
        "persona": persona,
        "language": language,
        "favorite_club": favorite_club,
        "turning_points": cards,
        "xg": roll["xg"],
        "peak_pdr": roll["peak_pdr"],
        "tactical_shifts": roll["tactical_shifts"],
        "anomaly_types": roll["anomaly_types"],
        "scoreline": roll["scoreline"],
        "agent_trace": [
            {
                "agent_id": "agent_1",
                "name": "Telemetry Engine",
                "role": "Roll the three turning points and the match xG",
                "stage": "interpret",
                "latency_ms": agent1,
                "status": "ok",
            },
            {
                "agent_id": "agent_2",
                "name": "Causal Analyst",
                "role": "Recap uses the grounded templates so three chains stay instant",
                "stage": "explain",
                "latency_ms": round(template_ms / 2.0, 2),
                "status": "fallback",
            },
            {
                "agent_id": "agent_3",
                "name": "Broadcast Personalizer",
                "role": "Persona, language, and club voice on each card",
                "stage": "personalize",
                "latency_ms": round(template_ms / 2.0, 2),
                "status": "fallback",
            },
            {
                "agent_id": "agent_4",
                "name": "Grounding Auditor",
                "role": "Cards were checked against each minute's telemetry",
                "stage": "render",
                "latency_ms": round(audit_ms, 2),
                "status": "ok",
            },
        ],
        "handoffs": [
            "Agent 1 Telemetry -> Agent 4 Auditor: three TelemetryStatePayloads",
            "Agent 4 Auditor -> Broadcast: three grounded turning points",
        ],
    }


def run_telemetry(minute: int) -> dict:
    minute = min(90, max(1, minute))
    telemetry = build_telemetry(minute=minute)
    if minute == 90:
        telemetry["match_rollup"] = match_rollup()
    telemetry["badges"] = build_badges(telemetry)
    return telemetry


def health() -> dict:
    return {
        "status": "healthy",
        "orchestrator": "Microsoft Semantic Kernel",
        "llm_provider": "AIML API (gpt-4o-mini)",
        "fallback_ready": True,
        "llm_configured": bool(_key()),
    }
