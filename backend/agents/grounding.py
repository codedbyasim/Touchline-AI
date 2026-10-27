"""Agent 4 — grounding and hallucination auditor.

Every number in model prose is checked against TelemetryStatePayload.
A claim is verified when some payload number lies within ±0.5. Anything else
is stripped. Questions the tracking stream cannot answer get an epistemic note.
"""

from __future__ import annotations

import re

NUMBER_RE = re.compile(r"(?<![\w])(-?\d+(?:\.\d+)?)(?![\w])")
UNANSWERABLE_RE = re.compile(
    r"heart|injur|locker|muscle|fitness|mood|speech|manager|slept|sleep|oxygen|wage|contract|girlfriend|wife|diet",
    re.IGNORECASE,
)
TOLERANCE = 0.5


def collect_numbers(payload) -> list[float]:
    found: list[float] = []

    def walk(node) -> None:
        if isinstance(node, bool) or node is None:
            return
        if isinstance(node, (int, float)):
            found.append(float(node))
            return
        if isinstance(node, str):
            for match in NUMBER_RE.finditer(node):
                found.append(float(match.group(1)))
            return
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
            return
        if isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(payload)
    return found


def is_grounded(value: float, allowed: list[float]) -> bool:
    return any(abs(value - candidate) <= TOLERANCE + 1e-9 for candidate in allowed)


def strip_ungrounded(text: str, allowed: list[float]) -> tuple[str, int, int]:
    """Replace unverified numbers. Returns text, kept count, stripped count."""
    if not text:
        return text or "", 0, 0
    kept = 0
    stripped = 0

    def repl(match: re.Match) -> str:
        nonlocal kept, stripped
        value = float(match.group(1))
        if is_grounded(value, allowed):
            kept += 1
            return match.group(0)
        stripped += 1
        return "[unverified]"

    return NUMBER_RE.sub(repl, text), kept, stripped


def epistemic_note(question: str | None, model_note: str | None, stripped: int) -> str | None:
    if question and UNANSWERABLE_RE.search(question):
        return (
            "The tracking stream can prove positions, speeds, pass difficulty, PPDA and the "
            "control-versus-chaos index. It cannot prove heart rate, injury, locker-room speech "
            "or anything off the ball. That part stays unknown."
        )
    if model_note and model_note.strip() and model_note.strip().lower() not in {"null", "none"}:
        return model_note.strip()
    if stripped:
        return "Some figures were removed because they were not in the telemetry payload."
    return None


def _shirt(name: str | None, default: str) -> str:
    if name and "#" in name:
        return name.split("#", 1)[1].rstrip(")").strip() or default
    return default


def build_badges(telemetry: dict) -> list[dict]:
    """Badges are formatted from engine numbers, so they verify by construction."""
    if telemetry.get("current_minute") == 90 and telemetry.get("match_rollup"):
        roll = telemetry["match_rollup"]
        xg = roll.get("xg") or {}
        return [
            {
                "metric_key": "xg",
                "label": f"xG NLR {float(xg.get('NLR', 0)):.2f} – MCB {float(xg.get('MCB', 0)):.2f}",
                "verified": True,
            },
            {
                "metric_key": "peak_pdr",
                "label": f"Peak PDR: {float(roll.get('peak_pdr', 0)):.1f}",
                "verified": True,
            },
            {
                "metric_key": "tactical_shifts",
                "label": f"Tactical Shifts: {roll.get('tactical_shifts', 0)}",
                "verified": True,
            },
        ]

    badges: list[dict] = []
    anomalies = telemetry.get("tactical_anomalies") or []
    types = {a.get("anomaly_type") for a in anomalies}
    nlr = (telemetry.get("team_metrics") or {}).get("NLR") or {}
    mcb = (telemetry.get("team_metrics") or {}).get("MCB") or {}
    highlights = telemetry.get("speed_and_pass_highlights") or []

    def add(key: str, label: str) -> None:
        badges.append({"metric_key": key, "label": label, "verified": True})

    def highlight(kind: str) -> dict | None:
        return next((h for h in highlights if h.get("type") == kind), None)

    if "HIGH_PRESS_TURNOVER_TRAP" in types and nlr.get("ppda_5m") is not None:
        add("ppda_5m", f"NLR PPDA: {nlr['ppda_5m']:.1f}")
        shot = highlight("SHOT_SPEED")
        if shot:
            add("shot_speed_kmh", f"Shot Speed: {shot['value']:.1f} km/h")
        pdr = highlight("HIGH_DIFFICULTY_LINE_BREAKER")
        if pdr:
            add("pass_difficulty_rating", f"Pass Difficulty: {pdr['value']:.1f}/100")

    inversion = next((a for a in anomalies if a.get("anomaly_type") == "STRUCTURAL_INVERSION_OVERLOAD"), None)
    if inversion:
        shift = float(inversion.get("shift_distance_m") or 0)
        shirt = _shirt(inversion.get("primary_player_name"), "2")
        add("shift_distance_m", f"#{shirt} Shift: {shift:.1f}m Inside")
        if nlr.get("ppda_baseline") is not None and nlr.get("ppda_5m") is not None:
            add("ppda_5m", f"NLR PPDA: {nlr['ppda_baseline']:.1f} → {nlr['ppda_5m']:.1f}")
        base = mcb.get("xt_central_baseline") or 0
        now = mcb.get("xt_central_5m") or 0
        if base:
            lift = round((now - base) / base * 100)
            add("xt_5m", f"Central xT +{lift}% ({now:.2f})")
        pdr = highlight("HIGH_DIFFICULTY_LINE_BREAKER")
        if pdr:
            add("pass_difficulty_rating", f"Line-Break PDR: {pdr['value']:.1f}/100")

    if "LOW_BLOCK_PRESSING_COLLAPSE" in types:
        add("control_vs_chaos_index", f"CCI: {float(telemetry.get('control_vs_chaos_index') or 0):.1f}")
        drop = telemetry.get("nlr_flank_press_drop")
        if drop is not None:
            add("flank_press_drop", f"NLR Left-Flank Press: -{float(drop):.0%}")
        entries = telemetry.get("nlr_final_third_entries_5m")
        add("final_third_entries", f"NLR Final-Third Entries (5m): {entries}")

    if "SUBSTITUTION_PACE_MISMATCH" in types:
        sprint = highlight("SPRINT_THRESHOLD_ALERT")
        pdr = highlight("HIGH_DIFFICULTY_LINE_BREAKER")
        if sprint:
            shirt = _shirt(sprint.get("player_name"), "19")
            add("sprint_kmh", f"#{shirt} Sprint: {sprint['value']:.1f} km/h")
        if pdr:
            shirt = _shirt(pdr.get("player_name"), "8")
            add("pass_difficulty_rating", f"#{shirt} Line-Break PDR: {pdr['value']:.1f}/100")
            if pdr.get("ball_speed_kmh") is not None:
                add("ball_speed_kmh", f"Ball Speed: {pdr['ball_speed_kmh']:.1f} km/h")
    return badges


def audit_text(text: str, telemetry: dict) -> tuple[str, int, int]:
    return strip_ungrounded(text, collect_numbers(telemetry))
