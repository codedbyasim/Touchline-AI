"""Precompute deterministic responses so the broadcast UI survives a dead API.

The cache covers 5 moments × 3 personas × 3 languages × 2 clubs × 5 spotlights,
plus struggle answers, the full-time recap, auto-event clips, and a slim
telemetry frame for every minute of the match. AIML is forced off: this file
must be identical on every machine.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["AIML_API_KEY"] = ""

from backend.agents.orchestrator import run_analyze, run_diagnose, run_recap  # noqa: E402
from backend.engine.auto_event import auto_event_segment  # noqa: E402
from backend.engine.telemetry_engine import build_telemetry, match_rollup  # noqa: E402

MOMENTS = (22, 54, 67, 82, 90)
PERSONAS = ("CASUAL_FAN", "TACTICO_ANALYST", "BROADCAST_STUDIO")
LANGUAGES = ("en", "es", "ar")
CLUBS = ("NLR", "MCB")
SPOTS = ("", "NLR_07", "MCB_02", "NLR_08", "MCB_09")
OUT = ROOT / "frontend" / "src" / "generated" / "fallback-cache.json"


def insight_key(minute: int, persona: str, language: str, club: str, spotlight: str) -> str:
    return f"{minute}|{persona}|{language}|{club}|{spotlight}"


def _slim_insight(result: dict) -> dict:
    result.pop("telemetry", None)
    result.pop("positions_22_players", None)
    overlay = result.get("broadcast_overlay")
    if isinstance(overlay, dict):
        overlay.pop("graphic_vectors", None)
    return result


async def build() -> dict:
    scrub = {}
    roll = match_rollup()
    for minute in range(1, 91):
        tel = build_telemetry(minute=minute)
        if minute == 90:
            tel["match_rollup"] = roll
        scrub[str(minute)] = {
            "current_minute": minute,
            "scoreline": tel["scoreline"],
            "control_vs_chaos_index": tel["control_vs_chaos_index"],
            "rhythm_state": tel["rhythm_state"],
            "positions_22_players": tel["positions_22_players"],
            "tactical_anomalies": [
                {"anomaly_type": a.get("anomaly_type"), "metric_proof": a.get("metric_proof")}
                for a in tel["tactical_anomalies"]
            ],
            "window_comparison": tel["window_comparison"],
        }

    insights = {}
    for minute in MOMENTS:
        for persona in PERSONAS:
            for language in LANGUAGES:
                for club in CLUBS:
                    for spot in SPOTS:
                        result = await run_analyze(
                            {
                                "minute": minute,
                                "persona": persona,
                                "language": language,
                                "favorite_club": club,
                                "spotlight_player_id": spot or None,
                            }
                        )
                        insights[insight_key(minute, persona, language, club, spot)] = _slim_insight(result)

    diagnose = {}
    for minute in MOMENTS:
        for team in CLUBS:
            for persona in PERSONAS:
                for language in LANGUAGES:
                    result = await run_diagnose(
                        {"minute": minute, "team_id": team, "persona": persona, "language": language}
                    )
                    diagnose[f"{minute}|{team}|{persona}|{language}"] = _slim_insight(result)

    recap = {}
    for persona in PERSONAS:
        for language in LANGUAGES:
            for club in CLUBS:
                recap[f"{persona}|{language}|{club}"] = await run_recap(persona, language, club)

    auto_event = {}
    for minute in MOMENTS:
        clip = auto_event_segment(minute)
        clip.pop("frames_preview", None)
        auto_event[str(minute)] = clip

    return {
        "version": 1,
        "moments": list(MOMENTS),
        "scrub": scrub,
        "insights": insights,
        "diagnose": diagnose,
        "recap": recap,
        "auto_event": auto_event,
    }


def main() -> None:
    payload = asyncio.run(build())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(text)} bytes, {len(payload['insights'])} insights)")


if __name__ == "__main__":
    main()
