"""Auto-eventing from raw 25 fps tracking frames.

A pass or shot is emitted only when the ball leaves a player's control
(<1.5 m to >2.0 m) with ball acceleration above 8.0 m/s². Frames carry
player ids and coordinates. They never carry an event label.
"""

from __future__ import annotations

import math

from backend.engine.formulas import ball_acceleration, pass_difficulty, speed_kmh
from backend.synthetic.squads import BY_ID

FPS = 25
DT = 1.0 / FPS


def _dist(a, b) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def synthesize_frames(segment_minute: int) -> list[dict]:
    """Deterministic clip: a line-breaking pass, a shot on goal, one sprint.

    The minute only picks which players are on the ball. Detection does not
    read that choice as a label — it reads positions.
    """
    if segment_minute >= 75:
        passer, receiver, shooter, sprinter = "NLR_08", "NLR_09", "NLR_07", "NLR_19"
        defenders = ["MCB_16", "MCB_08", "MCB_03", "MCB_05"]
    elif segment_minute >= 46:
        passer, receiver, shooter, sprinter = "MCB_02", "MCB_16", "MCB_09", "MCB_11"
        defenders = ["NLR_06", "NLR_04", "NLR_08"]
    else:
        passer, receiver, shooter, sprinter = "NLR_10", "NLR_08", "NLR_07", "MCB_11"
        defenders = ["MCB_16", "MCB_08", "MCB_03"]

    pass_from = (40.0, 40.0)
    pass_to = (62.0, 40.0)
    shot_from = (104.0, 40.0)
    roster_xy = {
        passer: pass_from,
        receiver: pass_to,
        shooter: shot_from,
        sprinter: (20.0, 18.0),
    }
    for index, pid in enumerate(defenders):
        roster_xy[pid] = (44.0 + index * 4.0, 42.0)

    frames: list[dict] = []

    def emit(t: float, ball, moving=None):
        players = []
        seen = set()
        for pid, xy in roster_xy.items():
            if pid in seen:
                continue
            seen.add(pid)
            point = xy
            if moving and pid == moving[0]:
                point = moving[1]
            who = BY_ID[pid]
            players.append({"player_id": pid, "team_id": who["team_id"], "xy": [round(point[0], 3), round(point[1], 3)]})
        frames.append(
            {
                "frame_id": int(segment_minute * 1000 + round(t * FPS)),
                "timestamp_ms": int(segment_minute * 60 * 1000 + round(t * 1000)),
                "ball_xy": [round(ball[0], 3), round(ball[1], 3)],
                "players": players,
            }
        )

    # Pass hold: ball 0.4 m from the passer.
    for i in range(8):
        emit(i * DT, (pass_from[0] + 0.4, pass_from[1]))
    # Release frame: ball is now 3.2 m away. The step from the previous frame
    # is ~2.8 m in 0.04 s (~70 m/s) against a near-zero incoming speed.
    emit(8 * DT, (pass_from[0] + 3.2, pass_from[1]))
    for i in range(1, 28):
        f = i / 27
        ball = (
            pass_from[0] + 3.2 + (pass_to[0] - (pass_from[0] + 3.2)) * f,
            pass_from[1],
        )
        emit((8 + i) * DT, ball)

    # Shot hold, then a strike toward x=120, y=40 (inside the 36–44 goal mouth).
    base = len(frames)
    for i in range(6):
        emit((base + i) * DT, (shot_from[0] + 0.3, shot_from[1]))
    emit((base + 6) * DT, (shot_from[0] + 3.4, shot_from[1]))
    for i in range(1, 12):
        emit((base + 6 + i) * DT, (shot_from[0] + 3.4 + i * 1.05, shot_from[1]))

    # Sprint lasts the whole clip. 33.8 km/h = 9.388... m/s.
    step = (33.8 / 3.6) * DT
    for index, frame in enumerate(frames):
        for player in frame["players"]:
            if player["player_id"] == sprinter:
                player["xy"] = [round(20.0 + index * step, 3), 18.0]
    return frames


def detect_events(frames: list[dict]) -> list[dict]:
    events = []
    released: set[str] = set()
    for i in range(2, len(frames) - 1):
        older, prev, cur = frames[i - 2], frames[i - 1], frames[i]
        owner, owner_d = _nearest(prev)
        _current, now_d = _nearest(cur)
        if owner is None or owner["player_id"] in released:
            continue
        if not (owner_d < 1.5 and now_d > 2.0):
            continue
        v_prev = _dist(older["ball_xy"], prev["ball_xy"]) / DT
        v_now = _dist(prev["ball_xy"], cur["ball_xy"]) / DT
        accel = ball_acceleration(v_prev, v_now, DT)
        if accel <= 8.0:
            continue
        released.add(owner["player_id"])
        tagged = _tag(frames, i, owner)
        if tagged:
            events.append(tagged)
    events.extend(_sprints(frames))
    return events


def _nearest(frame, ball=None):
    ball = ball if ball is not None else frame["ball_xy"]
    best, best_d = None, 1e9
    for player in frame["players"]:
        d = _dist(player["xy"], ball)
        if d < best_d:
            best, best_d = player, d
    return best, best_d


def _tag(frames, index, owner) -> dict | None:
    who = BY_ID[owner["player_id"]]
    start = frames[index - 1]["ball_xy"]
    receiver = None
    receive = None
    for frame in frames[index : index + 40]:
        for player in frame["players"]:
            if player["team_id"] != owner["team_id"] or player["player_id"] == owner["player_id"]:
                continue
            if _dist(player["xy"], frame["ball_xy"]) <= 1.5:
                receiver = player
                receive = frame
                break
        if receiver:
            break
    if receiver and receive:
        end = receive["ball_xy"]
        dt = max(DT, (receive["timestamp_ms"] - frames[index]["timestamp_ms"]) / 1000.0)
        opponents = [p["xy"] for p in receive["players"] if p["team_id"] != owner["team_id"]]
        metrics = pass_difficulty(start, end, opponents, end)
        return {
            "event_type": "pass",
            "team_id": who["team_id"],
            "player_id": who["player_id"],
            "player_name": who["player_name"],
            "shirt_number": who["shirt_number"],
            "start_xy": start,
            "end_xy": end,
            "pass_metrics": {
                "distance_m": round(metrics["distance_m"], 2),
                "accurate": True,
                "defenders_bypassed": metrics["defenders_bypassed"],
                "receiver_pressure_dist_m": round(metrics["receiver_pressure_dist_m"], 2),
                "pass_difficulty_rating": round(metrics["pass_difficulty_rating"], 1),
            },
            "ball_speed_kmh": round(speed_kmh(_dist(start, end), dt), 1),
            "shot_speed_kmh": None,
            "receiver_id": receiver["player_id"],
            "sprint_threshold_triggered": False,
        }
    later = frames[min(len(frames) - 1, index + 1)]
    x1, y1 = frames[index]["ball_xy"]
    x2, y2 = later["ball_xy"]
    if x2 > x1:
        t = (120.0 - x1) / (x2 - x1)
        y_at = y1 + t * (y2 - y1)
        if t > 0 and 36.0 <= y_at <= 44.0:
            far = frames[min(len(frames) - 1, index + 10)]
            dt = max(DT, (far["timestamp_ms"] - frames[index - 1]["timestamp_ms"]) / 1000.0)
            return {
                "event_type": "shot",
                "team_id": who["team_id"],
                "player_id": who["player_id"],
                "player_name": who["player_name"],
                "shirt_number": who["shirt_number"],
                "start_xy": frames[index - 1]["ball_xy"],
                "end_xy": [120.0, round(y_at, 2)],
                "pass_metrics": None,
                "ball_speed_kmh": None,
                "shot_speed_kmh": round(speed_kmh(_dist(frames[index - 1]["ball_xy"], far["ball_xy"]), dt), 1),
                "sprint_threshold_triggered": False,
            }
    return None


def _sprints(frames: list[dict]) -> list[dict]:
    tracks: dict[str, list] = {}
    for frame in frames:
        for player in frame["players"]:
            tracks.setdefault(player["player_id"], []).append((frame["timestamp_ms"], player["xy"]))
    found = []
    for pid, samples in tracks.items():
        peak = 0.0
        for (t0, p0), (t1, p1) in zip(samples, samples[1:]):
            dt = (t1 - t0) / 1000.0
            if dt <= 0:
                continue
            peak = max(peak, speed_kmh(_dist(p0, p1), dt))
        if peak >= 31.5:
            who = BY_ID[pid]
            found.append(
                {
                    "event_type": "sprint",
                    "team_id": who["team_id"],
                    "player_id": pid,
                    "player_name": who["player_name"],
                    "shirt_number": who["shirt_number"],
                    "player_speed_kmh": round(peak, 1),
                    "sprint_threshold_triggered": True,
                    "pass_metrics": None,
                    "ball_speed_kmh": None,
                    "shot_speed_kmh": None,
                }
            )
    return found


def auto_event_segment(segment_minute: int) -> dict:
    frames = synthesize_frames(int(segment_minute))
    return {
        "segment_minute": int(segment_minute),
        "fps": FPS,
        "frame_count": len(frames),
        "frames_preview": frames[:6],
        "events": detect_events(frames),
        "method": "Ball leaves control (<1.5 m to >2.0 m) with acceleration > 8.0 m/s². Names come from the tracking ids. No pre-labeled event tags.",
    }
