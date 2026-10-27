"""With no AIML key the desk still answers, in every language, inside the word caps."""

import asyncio
import json
import time

from backend.agents.fallback import render_copy
from backend.agents.orchestrator import run_analyze
from backend.engine.telemetry_engine import build_telemetry

MOMENTS = (22, 54, 67, 82, 90)
PERSONAS = ("CASUAL_FAN", "TACTICO_ANALYST", "BROADCAST_STUDIO")
LANGUAGES = ("en", "es", "ar")


def _run(**kwargs):
    body = {
        "minute": 54,
        "persona": "CASUAL_FAN",
        "language": "en",
        "favorite_club": "NLR",
        "spotlight_player_id": None,
    }
    body.update(kwargs)
    return asyncio.run(run_analyze(body))


def test_empty_key_uses_fallback_for_every_moment_persona_and_language():
    for minute in MOMENTS:
        for persona in PERSONAS:
            for language in LANGUAGES:
                result = _run(minute=minute, persona=persona, language=language)
                assert result["mode"] == "fallback"
                assert result["headline"]
                assert len(result["headline"].split()) <= 12
                assert len(result["narrative_body"].split()) <= 55
                assert result["badges"]
                assert all(badge["verified"] is True for badge in result["badges"])
                assert [row["status"] for row in result["agent_trace"]][0] == "ok"
                assert result["agent_trace"][1]["latency_ms"] >= 0
                assert result["agent_trace"][1]["latency_ms"] < 20


def test_favorite_club_changes_the_voice():
    ours = _run(favorite_club="NLR")
    theirs = _run(favorite_club="MCB")
    assert ours["narrative_body"] != theirs["narrative_body"]
    assert "We" in ours["narrative_body"]
    assert "We" in theirs["narrative_body"]


def test_spotlight_centers_the_named_player():
    result = _run(spotlight_player_id="MCB_02")
    assert "Whitmore" in result["narrative_body"]


def test_spanish_and_arabic_pin_headline_why_overlay_and_badges():
    english = _run(minute=54, language="en")
    for language in ("es", "ar"):
        result = _run(minute=54, language=language)
        assert result["headline"] != english["headline"]
        assert result["why_it_matters"] != english["why_it_matters"]
        assert result["broadcast_overlay"]["title"] == result["headline"]
        assert result["broadcast_overlay"]["subtitle"] == result["why_it_matters"]
        assert result["badges"][0]["label"] != english["badges"][0]["label"]
        assert "26.2" in result["badges"][0]["label"]
        if language == "ar":
            assert any("\u0600" <= char <= "\u06FF" for char in result["headline"])
            assert any("\u0600" <= char <= "\u06FF" for char in result["badges"][0]["label"])


def test_live_path_replaces_an_english_headline(monkeypatch):
    monkeypatch.setenv("AIML_API_KEY", "present-but-unused")

    async def english(name, _instructions, _user, max_tokens=0):
        if name == "CausalAnalyst":
            return json.dumps(
                {
                    "causal_diagnosis": "The full-back stepped inside",
                    "why_it_matters": "The middle opened up",
                    "cited_metrics": ["26.2"],
                    "uncertainty_note": None,
                }
            )
        return json.dumps(
            {
                "headline": "Full-back steps inside and the middle opens",
                "narrative_body": "Un lateral entra y el medio se abre con 26.2 metros.",
                "why_it_matters": "It matters because the block split.",
                "broadcast_overlay": {"title": "Full-back steps inside", "subtitle": "the block split"},
            }
        )

    monkeypatch.setattr("backend.agents.orchestrator._invoke_agent", english)
    result = _run(minute=54, language="es")
    assert result["headline"] == "Un lateral entra por dentro y se abre el medio"
    assert result["broadcast_overlay"]["title"] == result["headline"]
    assert result["broadcast_overlay"]["subtitle"] == result["why_it_matters"]
    assert "26.2" in result["narrative_body"]
    assert "Desplazamiento" in result["badges"][0]["label"]
    assert "Full-back" not in result["headline"]
    assert "Full-back" not in result["why_it_matters"]


def test_unanswerable_question_gets_an_epistemic_note():
    result = _run(custom_question="What is his heart rate and what did the manager say in the locker room?")
    assert result["epistemic_note"]
    assert "cannot prove" in result["epistemic_note"].lower()


def test_templates_render_in_under_20ms():
    telemetry = build_telemetry(minute=54)
    started = time.perf_counter()
    for _ in range(30):
        render_copy(
            telemetry,
            persona="TACTICO_ANALYST",
            language="es",
            favorite_club="MCB",
            spotlight=telemetry["player_spotlight_telemetry"],
        )
    per_call_ms = (time.perf_counter() - started) / 30 * 1000
    assert per_call_ms < 20


def test_timeout_hands_off_to_the_template(monkeypatch):
    monkeypatch.setenv("AIML_API_KEY", "present-but-unused")

    async def explode(*_args, **_kwargs):
        raise TimeoutError("agent timed out")

    monkeypatch.setattr("backend.agents.orchestrator._invoke_agent", explode)
    result = _run()
    assert result["mode"] == "fallback"
    assert any("Agent 2" in error for error in result["errors"])
    assert any("Fallback" in hop for hop in result["handoffs"])
    assert result["headline"]
    assert result["agent_trace"][1]["status"] == "recovered"
