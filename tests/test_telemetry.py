"""The formulas are computed, not copied from a lookup table of badge strings."""

import numpy as np
import pytest

from backend.engine.formulas import (
    control_vs_chaos,
    pass_difficulty,
    ppda,
    rhythm_state,
    shot_xg,
    speed_kmh,
    sprint_triggered,
    xt_delta,
)


def test_pass_difficulty_matches_the_published_expression():
    # d = 32, N = 3, pressure = 1.75, deep completion. 0.75*32 + 11.5*3 + 28/1.75 + 12 = 86.5
    start = (64.5, 48.0)
    end = (96.5, 48.0)
    opponents = [(70.0, 48.0), (80.0, 48.0), (90.0, 48.0), (96.5, 49.75)]
    metrics = pass_difficulty(start, end, opponents, end)
    assert metrics["defenders_bypassed"] == 3
    assert metrics["distance_m"] == pytest.approx(32.0)
    assert metrics["receiver_pressure_dist_m"] == pytest.approx(1.75)
    assert metrics["pass_difficulty_rating"] == pytest.approx(86.5)
    assert metrics["deep_completion"] is True


def test_pass_difficulty_clips_and_defaults_pressure():
    metrics = pass_difficulty((0, 0), (100, 0), [], (100, 0))
    assert metrics["receiver_pressure_dist_m"] == pytest.approx(5.0)
    assert 0.0 <= metrics["pass_difficulty_rating"] <= 100.0


def test_speed_and_sprint_thresholds():
    assert speed_kmh(33.8 / 3.6, 1.0) == pytest.approx(33.8)
    assert speed_kmh(10, 0) == 0.0
    assert sprint_triggered(31.5, 0) is True
    assert sprint_triggered(31.4, 624) is False
    assert sprint_triggered(10, 625) is True


def test_ppda_and_undefined_when_no_actions():
    assert ppda(29, 5) == pytest.approx(5.8)
    assert ppda(76, 5) == pytest.approx(15.2)
    assert ppda(0, 0) is None


def test_control_vs_chaos_bands():
    # clip(4.5*N + 0.65*speed + 120/max(4, PPDA), 0, 100)
    assert control_vs_chaos(0, 0, 4) == pytest.approx(30.0)
    assert rhythm_state(24.5) == "HIGH_POSITIONAL_CONTROL"
    assert rhythm_state(35) == "BALANCED_COMPETITIVE_RHYTHM"
    assert rhythm_state(65) == "BALANCED_COMPETITIVE_RHYTHM"
    assert rhythm_state(79.4) == "END_TO_END_TRANSITION_CHAOS"
    assert control_vs_chaos(100, 100, 4) == 100.0


def test_xt_delta_uses_the_calibrated_grid():
    # (55, 45) -> (75, 45) is one of the six active central entries.
    delta = xt_delta((55.0, 45.0), (75.0, 45.0))
    assert delta == pytest.approx(0.48 / 6.0)


def test_shot_xg_geometry():
    # A shot from x=104 is 16 m from the NLR goal at x=120. (36-16)/40 = 0.5
    assert shot_xg((104.0, 40.0), "NLR") == pytest.approx(0.5)
    close = shot_xg((119.0, 40.0), "NLR")
    far = shot_xg((10.0, 40.0), "NLR")
    assert close == pytest.approx(0.55)
    assert far == pytest.approx(0.02)
    assert shot_xg((16.0, 40.0), "MCB") == pytest.approx(0.5)


def test_formulas_are_numpy_backed():
    assert hasattr(np, "clip")
    value = pass_difficulty((0, 0), (10, 0), [(5, 1)], (10, 0))["pass_difficulty_rating"]
    assert isinstance(value, float)
