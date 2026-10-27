"""The five broadcast moments have to fall out of the engine."""

from backend.agents.grounding import build_badges
from backend.engine.telemetry_engine import build_telemetry, match_rollup


def _labels(minute: int) -> list[str]:
    telemetry = build_telemetry(minute=minute)
    if minute == 90:
        telemetry["match_rollup"] = match_rollup()
    return [badge["label"] for badge in build_badges(telemetry)]


def test_minute_22_high_press():
    telemetry = build_telemetry(minute=22)
    assert telemetry["scoreline"] == {"NLR": 1, "MCB": 0}
    assert telemetry["tactical_anomalies"][0]["anomaly_type"] == "HIGH_PRESS_TURNOVER_TRAP"
    assert telemetry["team_metrics"]["NLR"]["ppda_5m"] == 5.8
    assert _labels(22) == [
        "NLR PPDA: 5.8",
        "Shot Speed: 104.2 km/h",
        "Pass Difficulty: 82.4/100",
    ]


def test_minute_54_inversion():
    telemetry = build_telemetry(minute=54)
    anomaly = telemetry["tactical_anomalies"][0]
    assert telemetry["scoreline"] == {"NLR": 1, "MCB": 0}
    assert anomaly["anomaly_type"] == "STRUCTURAL_INVERSION_OVERLOAD"
    assert anomaly["shift_distance_m"] == 26.2
    assert anomaly["zone_numerical_state"].startswith("3v2")
    nlr = telemetry["team_metrics"]["NLR"]
    mcb = telemetry["team_metrics"]["MCB"]
    assert nlr["ppda_5m"] == 15.2
    assert nlr["ppda_baseline"] == 8.4
    assert nlr["possession_pct_5m"] == 32.0
    assert mcb["possession_pct_5m"] == 68.0
    assert mcb["pass_accuracy_5m"] == 91.4
    assert nlr["pass_accuracy_5m"] == 74.2
    assert mcb["xt_central_5m"] == 0.48
    assert telemetry["control_vs_chaos_index"] == 24.5
    assert telemetry["rhythm_state"] == "HIGH_POSITIONAL_CONTROL"
    highlight = telemetry["speed_and_pass_highlights"][0]
    assert highlight["value"] == 86.5
    assert highlight["ball_speed_kmh"] == 68.4
    assert _labels(54) == [
        "#2 Shift: 26.2m Inside",
        "NLR PPDA: 8.4 → 15.2",
        "Central xT +340% (0.48)",
        "Line-Break PDR: 86.5/100",
    ]


def test_minute_67_collapse():
    telemetry = build_telemetry(minute=67)
    assert telemetry["scoreline"] == {"NLR": 1, "MCB": 1}
    assert telemetry["tactical_anomalies"][0]["anomaly_type"] == "LOW_BLOCK_PRESSING_COLLAPSE"
    assert telemetry["control_vs_chaos_index"] == 79.4
    assert telemetry["nlr_flank_press_drop"] == 0.64
    assert telemetry["nlr_final_third_entries_5m"] == 0
    assert telemetry["rhythm_state"] == "END_TO_END_TRANSITION_CHAOS"
    assert _labels(67) == [
        "CCI: 79.4",
        "NLR Left-Flank Press: -64%",
        "NLR Final-Third Entries (5m): 0",
    ]


def test_minute_82_pace():
    telemetry = build_telemetry(minute=82)
    anomaly = telemetry["tactical_anomalies"][0]
    assert telemetry["scoreline"] == {"NLR": 2, "MCB": 1}
    assert anomaly["anomaly_type"] == "SUBSTITUTION_PACE_MISMATCH"
    assert anomaly["peak_speed_kmh"] == 33.8
    highlight = next(h for h in telemetry["speed_and_pass_highlights"] if h["type"] == "HIGH_DIFFICULTY_LINE_BREAKER")
    assert highlight["value"] == 91.2
    assert highlight["ball_speed_kmh"] == 74.6
    assert _labels(82) == [
        "#19 Sprint: 33.8 km/h",
        "#8 Line-Break PDR: 91.2/100",
        "Ball Speed: 74.6 km/h",
    ]


def test_full_time_rollup():
    roll = match_rollup()
    assert roll["xg"] == {"NLR": 1.84, "MCB": 1.42}
    assert roll["peak_pdr"] == 91.2
    assert roll["tactical_shifts"] == 4
    assert roll["scoreline"] == {"NLR": 2, "MCB": 1}
    assert set(roll["anomaly_types"]) == {
        "HIGH_PRESS_TURNOVER_TRAP",
        "STRUCTURAL_INVERSION_OVERLOAD",
        "LOW_BLOCK_PRESSING_COLLAPSE",
        "SUBSTITUTION_PACE_MISMATCH",
    }
    assert _labels(90) == [
        "xG NLR 1.84 – MCB 1.42",
        "Peak PDR: 91.2",
        "Tactical Shifts: 4",
    ]
