"""Agent 1 — deterministic telemetry and spatial-delta engine.

Windows follow SRS §4.1: baseline [t-20, t-5], active [t-5, t], with the
clock parked at minute:59 so the featured action inside that minute counts.
"""

from __future__ import annotations

from functools import lru_cache

from backend.engine.formulas import (
    centroid,
    control_vs_chaos,
    pass_difficulty,
    ppda,
    rhythm_state,
    shift_distance,
    shot_xg,
    speed_kmh,
    sprint_triggered,
    xt_delta,
)
from backend.synthetic.match_generator import active_bounds, baseline_bounds, load_golden
from backend.synthetic.shapes import OFF_PITCH, SHAPES
from backend.synthetic.squads import MATCH_ID, SQUAD, ZONE_14, player

DEFENSIVE = {"tackle", "interception", "pressure"}
ON_BALL = {"pass", "shot"}
FULLBACK_ROLES = {"RB", "LB"}
ANOMALY_TYPES = (
    "HIGH_PRESS_TURNOVER_TRAP",
    "STRUCTURAL_INVERSION_OVERLOAD",
    "LOW_BLOCK_PRESSING_COLLAPSE",
    "SUBSTITUTION_PACE_MISMATCH",
)


def _in(ts: int, bounds: tuple[int, int]) -> bool:
    return bounds[0] < ts <= bounds[1]


def _events(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("record_type", "event") == "event"]


def _outside_def_third(defending_team: str, x: float) -> bool:
    # NLR defends x <= 40 for the whole match; MCB defends x >= 80.
    if defending_team == "NLR":
        return x > 40.0
    return x < 80.0


def _ppda_for(events: list[dict], team: str, bounds: tuple[int, int]) -> float | None:
    passes = 0
    actions = 0
    for event in events:
        if not _in(event["timestamp_ms"], bounds):
            continue
        if event["event_type"] == "pass" and event["team_id"] != team:
            if _outside_def_third(team, event["start_xy"][0]):
                passes += 1
        elif event["event_type"] in DEFENSIVE and event["team_id"] == team:
            actions += 1
    return ppda(passes, actions)


def _possession(events: list[dict], bounds: tuple[int, int]) -> dict[str, float]:
    on = [e for e in events if e["event_type"] in ON_BALL and _in(e["timestamp_ms"], bounds)]
    on.sort(key=lambda e: e["timestamp_ms"])
    if not on:
        return {"NLR": 50.0, "MCB": 50.0}
    times = {"NLR": 0.0, "MCB": 0.0}
    start, end = bounds
    times[on[0]["team_id"]] += on[0]["timestamp_ms"] - start
    for index, event in enumerate(on):
        nxt = on[index + 1]["timestamp_ms"] if index + 1 < len(on) else end
        times[event["team_id"]] += max(0.0, nxt - event["timestamp_ms"])
    total = times["NLR"] + times["MCB"] or 1.0
    return {team: 100.0 * value / total for team, value in times.items()}


def _pass_accuracy(events: list[dict], team: str, bounds: tuple[int, int]) -> float | None:
    passes = [
        e
        for e in events
        if e["event_type"] == "pass" and e["team_id"] == team and _in(e["timestamp_ms"], bounds)
    ]
    if not passes:
        return None
    accurate = sum(1 for e in passes if e.get("accurate"))
    return 100.0 * accurate / len(passes)


def _xt_sum(events: list[dict], team: str, bounds: tuple[int, int], central_only: bool = False) -> float:
    total = 0.0
    for event in events:
        if event["event_type"] != "pass" or event["team_id"] != team:
            continue
        if not _in(event["timestamp_ms"], bounds):
            continue
        end = event["end_xy"]
        if central_only and not _in_zone(end, ZONE_14):
            continue
        delta = xt_delta(event["start_xy"], end)
        if delta > 0:
            total += delta
    return float(total)


def _in_zone(xy, zone: dict) -> bool:
    return zone["x_min"] <= xy[0] <= zone["x_max"] and zone["y_min"] <= xy[1] <= zone["y_max"]


def _touches(records: list[dict], player_id: str, bounds: tuple[int, int]) -> list[list[float]]:
    points = []
    for rec in records:
        if not _in(rec.get("timestamp_ms", 0), bounds):
            continue
        kind = rec.get("record_type", "event")
        if kind == "touch" and rec.get("player_id") == player_id:
            points.append(rec["xy"])
        elif kind == "sample" and rec.get("player_id") == player_id:
            points.append(rec["xy"])
        elif kind == "event" and rec.get("player_id") == player_id and rec["event_type"] in {"pass", "shot", *DEFENSIVE}:
            points.append(rec["start_xy"])
    return points


def _kinematics(records: list[dict], player_id: str, bounds: tuple[int, int]) -> tuple[float, float]:
    samples = [
        rec
        for rec in records
        if rec.get("record_type") == "sample"
        and rec.get("player_id") == player_id
        and _in(rec["timestamp_ms"], bounds)
    ]
    samples.sort(key=lambda r: r["timestamp_ms"])
    if len(samples) < 2:
        return 0.0, 0.0
    peak = 0.0
    distance = 0.0
    for left, right in zip(samples, samples[1:]):
        dist = ((right["xy"][0] - left["xy"][0]) ** 2 + (right["xy"][1] - left["xy"][1]) ** 2) ** 0.5
        dt = (right["timestamp_ms"] - left["timestamp_ms"]) / 1000.0
        distance += dist
        peak = max(peak, speed_kmh(dist, dt))
    return peak, distance


def _ball_speed(event: dict) -> float | None:
    flight = event.get("flight_time_s")
    if not flight or event["event_type"] not in {"pass", "shot"}:
        return None
    start, end = event["start_xy"], event["end_xy"]
    dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
    return speed_kmh(dist, float(flight))


def _mean_ball_speed(events: list[dict], bounds: tuple[int, int]) -> float:
    speeds = []
    for event in events:
        if event["event_type"] != "pass" or not _in(event["timestamp_ms"], bounds):
            continue
        speed = _ball_speed(event)
        if speed is not None:
            speeds.append(speed)
    if not speeds:
        return 0.0
    return float(sum(speeds) / len(speeds))


def _turnovers(events: list[dict], bounds: tuple[int, int]) -> int:
    return sum(
        1
        for e in events
        if e["event_type"] == "possession_change" and _in(e["timestamp_ms"], bounds)
    )


def _flank_pressures(events: list[dict], team: str, bounds: tuple[int, int]) -> int:
    return sum(
        1
        for e in events
        if e["event_type"] == "pressure"
        and e["team_id"] == team
        and _in(e["timestamp_ms"], bounds)
        and e["start_xy"][1] <= 20.0
    )


def _final_third_entries(events: list[dict], team: str, bounds: tuple[int, int]) -> int:
    # NLR attacks toward x=120, so the final third is x > 80.
    limit = 80.0 if team == "NLR" else 40.0
    count = 0
    for event in events:
        if event["event_type"] != "pass" or event["team_id"] != team:
            continue
        if not _in(event["timestamp_ms"], bounds):
            continue
        end_x = event["end_xy"][0]
        if team == "NLR" and end_x > limit:
            count += 1
        elif team == "MCB" and end_x < limit:
            count += 1
    return count


def _yellow_in_lookback(events: list[dict], team: str, now: int) -> dict | None:
    window = (now - 600_000, now)
    cards = [
        e
        for e in events
        if e["event_type"] == "yellow_card" and e["team_id"] == team and _in(e["timestamp_ms"], window)
    ]
    return cards[-1] if cards else None


def _substitution_in_baseline(events: list[dict], bounds: tuple[int, int]) -> list[dict]:
    return [
        e
        for e in events
        if e["event_type"] == "substitution" and _in(e["timestamp_ms"], bounds)
    ]


def _scoreline(events: list[dict], now: int) -> dict[str, int]:
    nlr = mcb = 0
    for event in events:
        if event["event_type"] == "goal" and event["timestamp_ms"] <= now:
            if event["team_id"] == "NLR":
                nlr += 1
            else:
                mcb += 1
    return {"NLR": nlr, "MCB": mcb}


def _zone_counts(positions: list[dict]) -> tuple[int, int]:
    nlr = mcb = 0
    for row in positions:
        if row.get("on_pitch") and _in_zone(row["active_xy"], ZONE_14):
            if row["team_id"] == "NLR":
                nlr += 1
            else:
                mcb += 1
    return mcb, nlr


def build_positions(records: list[dict], minute: int) -> list[dict]:
    """22 on-pitch players. Measured centroids override the shape on a real shift."""
    events = _events(records)
    active = active_bounds(minute)
    baseline = baseline_bounds(minute)
    shape = SHAPES.get(minute, {})
    off = set(OFF_PITCH.get(minute, []))
    # A sub who has not entered yet, and the player they replaced.
    if minute < 75:
        off.add("NLR_19")
    if minute >= 75:
        off.add("NLR_11")
    rows = []
    for who in SQUAD:
        if who["player_id"] in off:
            continue
        base_pts = _touches(records, who["player_id"], baseline)
        act_pts = _touches(records, who["player_id"], active)
        base_c = centroid(base_pts)
        act_c = centroid(act_pts)
        shift = shift_distance(base_c, act_c) if base_c and act_c else None
        preset = shape.get(who["player_id"], who["home_xy"])
        if shift is not None and shift >= 15.0 and who["player_role"] in FULLBACK_ROLES:
            baseline_xy = [round(base_c[0], 3), round(base_c[1], 3)]
            active_xy = [round(act_c[0], 3), round(act_c[1], 3)]
        else:
            baseline_xy = [float(preset[0]), float(preset[1])]
            active_xy = [float(preset[0]), float(preset[1])]
            # Still expose the measured active point for the featured fullback
            # even when the shape preset is what we draw for everyone else.
            if shift is not None and shift >= 15.0:
                baseline_xy = [round(base_c[0], 3), round(base_c[1], 3)]
                active_xy = [round(act_c[0], 3), round(act_c[1], 3)]
        peak, dist5 = _kinematics(records, who["player_id"], active)
        rows.append(
            {
                "player_id": who["player_id"],
                "team_id": who["team_id"],
                "player_name": who["player_name"],
                "shirt_number": who["shirt_number"],
                "player_role": who["player_role"],
                "baseline_xy": baseline_xy,
                "active_xy": active_xy,
                "shift_m": None if shift is None else round(shift, 3),
                "max_speed_kmh": round(peak, 3),
                "distance_5m_m": round(dist5, 3),
                "on_pitch": True,
                "home_xy": list(who["home_xy"]),
            }
        )
    return rows


def _annotate_pass(event: dict) -> dict:
    opponents = [
        p["xy"]
        for p in event.get("tracking_players") or []
        if p.get("team_id") and p["team_id"] != event["team_id"]
    ]
    metrics = pass_difficulty(event["start_xy"], event["end_xy"], opponents, event["end_xy"])
    metrics["accurate"] = bool(event.get("accurate"))
    ball = _ball_speed(event)
    return {"metrics": metrics, "ball_speed_kmh": ball, "xt_delta": xt_delta(event["start_xy"], event["end_xy"])}


def build_telemetry(records: list[dict] | None = None, minute: int = 54, spotlight_player_id: str | None = None) -> dict:
    records = records if records is not None else load_match()
    events = _events(records)
    active = active_bounds(minute)
    baseline = baseline_bounds(minute)
    now = now_from_bounds(active)
    score = _scoreline(events, now)
    possession = _possession(events, active)

    def team_block(team: str) -> dict:
        ppda_5 = _ppda_for(events, team, active)
        ppda_base = _ppda_for(events, team, baseline)
        acc = _pass_accuracy(events, team, active)
        return {
            "possession_pct_5m": round(possession[team], 1),
            "ppda_5m": None if ppda_5 is None else round(ppda_5, 1),
            "ppda_baseline": None if ppda_base is None else round(ppda_base, 1),
            "xt_5m": round(_xt_sum(events, team, active), 4),
            "xt_central_5m": round(_xt_sum(events, team, active, central_only=True), 4),
            "xt_central_baseline": round(_xt_sum(events, team, baseline, central_only=True), 4),
            "pass_accuracy_5m": None if acc is None else round(acc, 1),
        }

    metrics = {"NLR": team_block("NLR"), "MCB": team_block("MCB")}
    # CCI uses the PPDA of the side with less of the ball — the team that is defending.
    defending = "NLR" if possession["NLR"] <= possession["MCB"] else "MCB"
    defending_ppda = _ppda_for(events, defending, active)
    cci_ppda = 10.0 if defending_ppda is None else defending_ppda
    turnovers = _turnovers(events, active)
    mean_speed = _mean_ball_speed(events, active)
    cci = control_vs_chaos(turnovers, mean_speed, cci_ppda)

    positions = build_positions(records, minute)
    anomalies = _anomalies(records, events, minute, metrics, positions, turnovers, cci)
    highlights = _highlights(events, records, active)
    spotlight = _spotlight(records, events, active, baseline, spotlight_player_id or _primary_player(anomalies))

    flank_base = _flank_pressures(events, "NLR", baseline)
    flank_act = _flank_pressures(events, "NLR", active)
    flank_drop = None
    if flank_base:
        flank_drop = (flank_base - flank_act) / flank_base

    return {
        "match_id": MATCH_ID,
        "current_minute": minute,
        "scoreline": score,
        "window_comparison": {
            "baseline_window": f"{minute - 20}'–{minute - 5}'",
            "active_window": f"{minute - 5}'–{minute}'",
        },
        "control_vs_chaos_index": cci,
        "rhythm_state": rhythm_state(cci),
        "team_metrics": metrics,
        "tactical_anomalies": anomalies,
        "speed_and_pass_highlights": highlights,
        "player_spotlight_telemetry": spotlight,
        "defending_team_for_cci": defending,
        "turnovers_5m": turnovers,
        "mean_ball_speed_5m": mean_speed,
        "nlr_flank_press_baseline": flank_base,
        "nlr_flank_press_5m": flank_act,
        "nlr_flank_press_drop": flank_drop,
        "nlr_flank_press_drop_pct": None if flank_drop is None else int(round(flank_drop * 100)),
        "nlr_final_third_entries_5m": _final_third_entries(events, "NLR", active),
        "sprint_threshold_kmh": 31.5,
        "positions_22_players": positions,
    }


def now_from_bounds(active: tuple[int, int]) -> int:
    return active[1]


def _primary_player(anomalies: list[dict]) -> str | None:
    if not anomalies:
        return None
    return anomalies[0].get("primary_player_id")


def _anomalies(records, events, minute, metrics, positions, turnovers, cci) -> list[dict]:
    found = []
    active = active_bounds(minute)
    baseline = baseline_bounds(minute)
    now = active[1]

    for team in ("NLR", "MCB"):
        value = _ppda_for(events, team, active)
        if value is not None and value < 6.5 and turnovers >= 6:
            found.append(
                {
                    "anomaly_id": f"anom_{minute}_press_{team.lower()}",
                    "anomaly_type": "HIGH_PRESS_TURNOVER_TRAP",
                    "severity": round(min(1.0, (6.5 - value) / 6.5 + turnovers / 20.0), 2),
                    "primary_player_id": "NLR_07" if team == "NLR" else "MCB_11",
                    "primary_player_name": player("NLR_07" if team == "NLR" else "MCB_11")["player_name"],
                    "team_id": team,
                    "metric_proof": f"{team} PPDA {value:.1f} with {turnovers} turnovers in 5 minutes",
                }
            )

    mcb_count, nlr_count = _zone_counts(positions)
    for row in positions:
        if row["player_role"] not in FULLBACK_ROLES or row["shift_m"] is None:
            continue
        if row["shift_m"] < 15.0:
            continue
        base = _touches(records, row["player_id"], baseline)
        act = _touches(records, row["player_id"], active)
        base_c = centroid(base)
        act_c = centroid(act)
        if not base_c or not act_c:
            continue
        inward = abs(act_c[1] - 40.0) < abs(base_c[1] - 40.0)
        if not inward:
            continue
        overload = mcb_count >= nlr_count + 1 if row["team_id"] == "MCB" else nlr_count >= mcb_count + 1
        if not overload:
            continue
        central_now = metrics["MCB"]["xt_central_5m"]
        central_then = metrics["MCB"]["xt_central_baseline"]
        lift = None
        if central_then:
            lift = (central_now - central_then) / central_then * 100.0
        found.append(
            {
                "anomaly_id": f"anom_{minute}_invert_{row['player_id'].lower()}",
                "anomaly_type": "STRUCTURAL_INVERSION_OVERLOAD",
                "severity": round(min(1.0, row["shift_m"] / 28.0), 2),
                "primary_player_id": row["player_id"],
                "primary_player_name": f"{row['player_name']} (#{row['shirt_number']})",
                "team_id": row["team_id"],
                "baseline_centroid_xy": base_c,
                "active_centroid_xy": act_c,
                "shift_distance_m": shift_distance(base_c, act_c),
                "target_zone": "ZONE_14_CENTRAL",
                "zone_numerical_state": f"{mcb_count}v{nlr_count}_OVERLOAD_{row['team_id']}",
                "metric_proof": (
                    f"#{row['shirt_number']} shifted {row['shift_m']:.1f}m inside; "
                    f"central xT {central_then:.2f} -> {central_now:.2f}"
                    + (f" ({lift:.0f}%)" if lift is not None else "")
                ),
            }
        )

    card = _yellow_in_lookback(events, "NLR", now)
    flank_base = _flank_pressures(events, "NLR", baseline)
    flank_act = _flank_pressures(events, "NLR", active)
    if card and flank_base and (flank_base - flank_act) / flank_base > 0.50:
        drop = (flank_base - flank_act) / flank_base
        entries = _final_third_entries(events, "NLR", active)
        found.append(
            {
                "anomaly_id": f"anom_{minute}_lowblock",
                "anomaly_type": "LOW_BLOCK_PRESSING_COLLAPSE",
                "severity": round(min(1.0, drop), 2),
                "primary_player_id": card["player_id"],
                "primary_player_name": card["player_name"],
                "team_id": "NLR",
                "flank_press_drop": drop,
                "final_third_entries_5m": entries,
                "cci": cci,
                "metric_proof": (
                    f"NLR left-flank press -{drop:.0%} after the yellow card; "
                    f"CCI {cci:.1f}; final-third entries {entries}"
                ),
            }
        )

    subs = _substitution_in_baseline(events, baseline)
    for sub in subs:
        peak, _dist = _kinematics(records, sub["player_id"], active)
        if peak <= 33.0:
            continue
        tired = None
        tired_speed = None
        for row in positions:
            if row["player_role"] not in FULLBACK_ROLES or row["team_id"] != sub["team_id"]:
                continue
            if row["player_id"] == sub["player_id"]:
                continue
            speed, _ = _kinematics(records, row["player_id"], active)
            if speed and speed < 24.0 and (tired_speed is None or speed < tired_speed):
                tired = row
                tired_speed = speed
        if tired is None:
            continue
        found.append(
            {
                "anomaly_id": f"anom_{minute}_pace_{sub['player_id'].lower()}",
                "anomaly_type": "SUBSTITUTION_PACE_MISMATCH",
                "severity": round(min(1.0, peak / 36.0), 2),
                "primary_player_id": sub["player_id"],
                "primary_player_name": f"{sub['player_name']} (#{sub['shirt_number']})",
                "team_id": sub["team_id"],
                "peak_speed_kmh": round(float(peak), 1),
                "tired_fullback_id": tired["player_id"],
                "tired_fullback_speed_kmh": round(float(tired_speed), 1),
                "metric_proof": (
                    f"#{sub['shirt_number']} {peak:.1f} km/h vs fatigued fullback "
                    f"#{tired['shirt_number']} at {tired_speed:.1f} km/h"
                ),
            }
        )
    return found


def _highlights(events, records, bounds) -> list[dict]:
    best = None
    best_pdr = -1.0
    fastest_ball = None
    for event in events:
        if event["event_type"] != "pass" or not _in(event["timestamp_ms"], bounds):
            continue
        annotated = _annotate_pass(event)
        pdr = annotated["metrics"]["pass_difficulty_rating"]
        if pdr > best_pdr:
            best_pdr = pdr
            best = (event, annotated)
        ball = annotated["ball_speed_kmh"] or 0.0
        if fastest_ball is None or ball > fastest_ball[0]:
            fastest_ball = (ball, event)
    rows = []
    if best and best_pdr >= 60:
        event, annotated = best
        metrics = annotated["metrics"]
        who = player(event["player_id"])
        ball = annotated["ball_speed_kmh"] or 0.0
        rows.append(
            {
                "type": "HIGH_DIFFICULTY_LINE_BREAKER",
                "player_id": event["player_id"],
                "player_name": f"{who['player_name']} (#{who['shirt_number']})",
                "value": round(metrics["pass_difficulty_rating"], 2),
                "ball_speed_kmh": ball,
                "defenders_bypassed": metrics["defenders_bypassed"],
                "value_str": (
                    f"PDR {metrics['pass_difficulty_rating']:.1f}/100 • "
                    f"{ball:.1f} km/h Ball Speed • "
                    f"{metrics['defenders_bypassed']} Defenders Bypassed"
                ),
            }
        )
    # Fastest sprinter in the window.
    fastest = None
    for who in SQUAD:
        peak, dist5 = _kinematics(records, who["player_id"], bounds)
        if fastest is None or peak > fastest[0]:
            fastest = (peak, dist5, who)
    if fastest and sprint_triggered(fastest[0], fastest[1]):
        peak, dist5, who = fastest
        rows.append(
            {
                "type": "SPRINT_THRESHOLD_ALERT",
                "player_id": who["player_id"],
                "player_name": f"{who['player_name']} (#{who['shirt_number']})",
                "value": round(peak, 2),
                "distance_5m_m": round(dist5, 1),
                "value_str": f"{peak:.1f} km/h Peak Sprint (>{31.5} km/h Threshold) • {dist5:.0f}m in 5 mins",
            }
        )
    # Fastest shot in the window.
    best_shot = None
    for event in events:
        if event["event_type"] != "shot" or not _in(event["timestamp_ms"], bounds):
            continue
        speed = _ball_speed(event) or 0.0
        if best_shot is None or speed > best_shot[0]:
            best_shot = (speed, event)
    if best_shot and best_shot[0] >= 80:
        speed, event = best_shot
        who = player(event["player_id"])
        rows.append(
            {
                "type": "SHOT_SPEED",
                "player_id": event["player_id"],
                "player_name": f"{who['player_name']} (#{who['shirt_number']})",
                "value": round(speed, 2),
                "value_str": f"Shot speed {speed:.1f} km/h",
            }
        )
    return rows


def _gravity(records, player_id: str, bounds) -> float:
    """How many opponents sit inside 12 m of this player's active centroid."""
    me = centroid(_touches(records, player_id, bounds))
    if me is None:
        return 0.0
    who = player(player_id)
    near = 0
    for other in SQUAD:
        if other["team_id"] == who["team_id"]:
            continue
        point = centroid(_touches(records, other["player_id"], bounds))
        if point is None:
            continue
        dist = ((point[0] - me[0]) ** 2 + (point[1] - me[1]) ** 2) ** 0.5
        if dist <= 12.0:
            near += 1
    return float(near)


def _spotlight(records, events, active, baseline, player_id: str | None) -> dict | None:
    if not player_id or player_id not in {p["player_id"] for p in SQUAD}:
        return None
    who = player(player_id)
    passes = [
        e
        for e in events
        if e["event_type"] == "pass" and e["player_id"] == player_id and _in(e["timestamp_ms"], active)
    ]
    pdrs = []
    for event in passes:
        pdrs.append(_annotate_pass(event)["metrics"]["pass_difficulty_rating"])
    peak, dist5 = _kinematics(records, player_id, active)
    base = centroid(_touches(records, player_id, baseline))
    act = centroid(_touches(records, player_id, active))
    return {
        "player_id": player_id,
        "player_name": who["player_name"],
        "shirt_number": who["shirt_number"],
        "touches_5m": len(_touches(records, player_id, active)),
        "avg_xy_15m": base,
        "avg_xy_5m": act,
        "max_speed_kmh": round(peak, 2),
        "distance_5m_m": round(dist5, 1),
        "avg_pass_difficulty": round(sum(pdrs) / len(pdrs), 2) if pdrs else None,
        "defensive_gravity_markers": _gravity(records, player_id, active),
    }


_ROLLUP: dict | None = None


def match_rollup(records: list[dict] | None = None) -> dict:
    global _ROLLUP
    if records is None and _ROLLUP is not None:
        return _ROLLUP
    records = records if records is not None else load_match()
    events = _events(records)
    xg = {"NLR": 0.0, "MCB": 0.0}
    peak_pdr = 0.0
    for event in events:
        if event["event_type"] == "shot":
            xg[event["team_id"]] += shot_xg(event["start_xy"], event["team_id"])
        elif event["event_type"] == "pass":
            pdr = _annotate_pass(event)["metrics"]["pass_difficulty_rating"]
            peak_pdr = max(peak_pdr, pdr)
    types = set()
    for minute in range(1, 91):
        telemetry = build_telemetry(records, minute)
        for anomaly in telemetry["tactical_anomalies"]:
            types.add(anomaly["anomaly_type"])
    result = {
        "xg": {"NLR": round(float(xg["NLR"]), 2), "MCB": round(float(xg["MCB"]), 2)},
        "peak_pdr": round(float(peak_pdr), 1),
        "tactical_shifts": len(types),
        "anomaly_types": sorted(types),
        "scoreline": _scoreline(events, 90 * 60 * 1000 + 59 * 1000),
    }
    if records is None or records is load_match():
        _ROLLUP = result
    return result


@lru_cache(maxsize=1)
def load_match() -> tuple:
    return tuple(load_golden())


def get_records() -> list[dict]:
    return list(load_match())
