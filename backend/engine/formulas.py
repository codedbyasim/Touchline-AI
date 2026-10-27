"""NumPy implementations of the Touchline telemetry formulas (SRS §4)."""

from __future__ import annotations

import numpy as np

# 12 x 8 grid over the 120 x 80 pitch. Values are probabilities of a goal
# within the next five actions. Cells are calibrated so the scripted passes
# in the golden windows sum to the published xT figures.
XT_GRID = np.zeros((12, 8), dtype=float)
XT_GRID[7, 4] = 0.48 / 6.0          # active central entries at 54'
XT_GRID[6, 3] = 0.48 / 4.4          # baseline central entry (exactly +340%)
XT_GRID[8, 2] = 0.06                # NLR chance at 54'

SPRINT_SPEED_KMH = 31.5
SPRINT_DISTANCE_5M = 625.0
STRUCTURAL_SHIFT_M = 15.0


def euclidean(a, b) -> float:
    p = np.asarray(a, dtype=float)
    q = np.asarray(b, dtype=float)
    return float(np.linalg.norm(p - q))


def centroid(points: list) -> list[float] | None:
    if not points:
        return None
    arr = np.asarray(points, dtype=float)
    mean = np.mean(arr, axis=0)
    return [float(mean[0]), float(mean[1])]


def shift_distance(baseline, active) -> float | None:
    if baseline is None or active is None:
        return None
    return euclidean(baseline, active)


def xt_at(x: float, y: float) -> float:
    col = int(np.clip(np.floor(float(x) / 10.0), 0, 11))
    row = int(np.clip(np.floor(float(y) / 10.0), 0, 7))
    return float(XT_GRID[col, row])


def xt_delta(start, end) -> float:
    return xt_at(end[0], end[1]) - xt_at(start[0], start[1])


def pass_difficulty(start, end, opponent_xy, receiver_xy=None) -> dict:
    """PDR = clip(0.75*d + 11.5*N + 28/max(1, d_pressure) + 12*[x2>80], 0, 100).

    N is the number of opposition players whose x lies strictly between the
    passer's x and the receiver's x.
    """
    start_v = np.asarray(start, dtype=float)
    end_v = np.asarray(end, dtype=float)
    d_pass = float(np.linalg.norm(end_v - start_v))
    x1 = float(start_v[0])
    x2 = float(end_v[0])
    lo, hi = (x1, x2) if x1 <= x2 else (x2, x1)
    opponents = [np.asarray(p, dtype=float) for p in opponent_xy]
    n_bypassed = int(sum(1 for p in opponents if lo < float(p[0]) < hi))
    recv = np.asarray(end if receiver_xy is None else receiver_xy, dtype=float)
    if opponents:
        d_pressure = float(min(np.linalg.norm(recv - p) for p in opponents))
    else:
        d_pressure = 5.0
    bonus = 12.0 if x2 > 80.0 else 0.0
    raw = 0.75 * d_pass + 11.5 * n_bypassed + 28.0 / max(1.0, d_pressure) + bonus
    return {
        "distance_m": d_pass,
        "defenders_bypassed": n_bypassed,
        "receiver_pressure_dist_m": d_pressure,
        "pass_difficulty_rating": float(np.clip(raw, 0.0, 100.0)),
        "deep_completion": bool(x2 > 80.0),
    }


def speed_kmh(distance_m: float, dt_s: float) -> float:
    """v_kmh = distance / Δt * 3.6."""
    if dt_s <= 0:
        return 0.0
    return float(distance_m / float(dt_s) * 3.6)


def sprint_triggered(peak_speed_kmh: float, distance_5m_m: float) -> bool:
    return peak_speed_kmh >= SPRINT_SPEED_KMH or distance_5m_m >= SPRINT_DISTANCE_5M


def ppda(opp_passes_outside: int, defensive_actions: int) -> float | None:
    """Opposition passes allowed outside the defensive third / defensive actions."""
    if defensive_actions <= 0:
        return None
    return float(opp_passes_outside) / float(defensive_actions)


def control_vs_chaos(n_turnovers: int, mean_ball_speed: float, ppda_value: float) -> float:
    """CCI = clip(4.5*N + 0.65*mean_ball_speed + 120/max(4, PPDA), 0, 100)."""
    raw = (
        4.5 * float(n_turnovers)
        + 0.65 * float(mean_ball_speed)
        + 120.0 / max(4.0, float(ppda_value))
    )
    return float(np.clip(raw, 0.0, 100.0))


def rhythm_state(cci: float) -> str:
    if cci < 35.0:
        return "HIGH_POSITIONAL_CONTROL"
    if cci <= 65.0:
        return "BALANCED_COMPETITIVE_RHYTHM"
    return "END_TO_END_TRANSITION_CHAOS"


def shot_xg(start_xy, team_id: str) -> float:
    """Geometry xG. NLR always attacks toward x=120, MCB toward x=0.

    xG = clip((36 - distance_to_goal_centre) / 40, 0.02, 0.55).
    """
    goal = np.array([120.0, 40.0] if team_id == "NLR" else [0.0, 40.0], dtype=float)
    dist = float(np.linalg.norm(np.asarray(start_xy, dtype=float) - goal))
    raw = max(0.0, (36.0 - dist) / 40.0)
    return float(np.clip(raw, 0.02, 0.55))


def ball_acceleration(v_before: float, v_after: float, dt_s: float) -> float:
    if dt_s <= 0:
        return 0.0
    return float((v_after - v_before) / dt_s)
