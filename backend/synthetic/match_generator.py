"""Deterministic seeded generator for the 90-minute NLR vs MCB fixture.

Event counts in each golden window are chosen so the NumPy formulas in
``backend.engine.formulas`` reproduce the published badge values. The seed
fixes timestamp ordering. Nothing here is a hardcoded metric — PPDA, PDR,
CCI, xT, xG and speeds are all recomputed by the engine.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from backend.engine.formulas import speed_kmh
from backend.synthetic.squads import MATCH_ID, SEED, player

GOLDEN_PATH = Path(__file__).with_name("golden_match.jsonl")

# Whitmore (#2) baseline centroid from the SRS example, active point chosen
# so the Euclidean shift is exactly 26.2 m (dx = 10.5).
WP_BASELINE = (54.0, 72.0)
_DX = 10.5
_DY = -math.sqrt(26.2**2 - _DX**2)
WP_ACTIVE = (54.0 + _DX, 72.0 + _DY)


def now_ms(minute: int) -> int:
    """Bookmark clock sits at minute:59 so events during that minute count."""
    return (minute * 60 + 59) * 1000


def active_bounds(minute: int) -> tuple[int, int]:
    end = now_ms(minute)
    return end - 300_000, end


def baseline_bounds(minute: int) -> tuple[int, int]:
    end = now_ms(minute) - 300_000
    return end - 900_000, end


def _linspace(start: int, end: int, count: int) -> list[int]:
    if count <= 0:
        return []
    step = (end - start) / (count + 1)
    return [int(start + step * (i + 1)) for i in range(count)]


class MatchBuilder:
    def __init__(self, seed: int = SEED) -> None:
        self.rng = random.Random(seed)
        self.records: list[dict] = []
        self._seq = 0

    def _stamp(self, ts: int) -> dict:
        total_s = ts / 1000.0
        minute = int(total_s // 60)
        second = int(total_s % 60)
        return {"minute": minute, "second": second, "period": 1 if minute <= 45 else 2}

    def add_event(self, ts: int, event_type: str, player_id: str, **fields) -> dict:
        self._seq += 1
        who = player(player_id)
        stamp = self._stamp(ts)
        event = {
            "record_type": "event",
            "event_id": f"evt_{stamp['minute']:03d}_{self._seq:04d}",
            "match_id": MATCH_ID,
            "period": stamp["period"],
            "minute": stamp["minute"],
            "second": stamp["second"],
            "timestamp_ms": int(ts),
            "event_type": event_type,
            "team_id": who["team_id"],
            "player_id": player_id,
            "player_name": who["player_name"],
            "shirt_number": who["shirt_number"],
            "player_role": who["player_role"],
            "start_xy": fields.get("start_xy", list(who["home_xy"])),
            "end_xy": fields.get("end_xy", list(who["home_xy"])),
            "player_speed_kmh": fields.get("player_speed_kmh"),
            "distance_covered_last_5m_m": fields.get("distance_covered_last_5m_m"),
            "sprint_threshold_triggered": False,
            "ball_speed_kmh": None,
            "shot_speed_kmh": None,
            "pass_metrics": None,
            "under_pressure": bool(fields.get("under_pressure", False)),
            "xt_delta": None,
            "score_state": {"NLR": 0, "MCB": 0},
            "flight_time_s": fields.get("flight_time_s"),
            "accurate": fields.get("accurate"),
            "tracking_players": fields.get("tracking_players", []),
        }
        self.records.append(event)
        return event

    def add_touch(self, ts: int, player_id: str, xy) -> None:
        who = player(player_id)
        self.records.append(
            {
                "record_type": "touch",
                "player_id": player_id,
                "team_id": who["team_id"],
                "timestamp_ms": int(ts),
                "xy": [float(xy[0]), float(xy[1])],
            }
        )

    def add_sample(self, ts: int, player_id: str, xy) -> None:
        who = player(player_id)
        self.records.append(
            {
                "record_type": "sample",
                "player_id": player_id,
                "team_id": who["team_id"],
                "timestamp_ms": int(ts),
                "xy": [float(xy[0]), float(xy[1])],
            }
        )

    def vertical_passes(
        self,
        player_id: str,
        times: list[int],
        accurate_flags: list[bool],
        speed: float,
    ) -> None:
        home = player(player_id)["home_xy"]
        start = [float(home[0]), float(home[1])]
        end = [float(home[0]), float(home[1]) + 0.5]
        dist = 0.5
        flight = dist * 3.6 / speed if speed else 0.2
        for ts, accurate in zip(times, accurate_flags):
            self.add_event(
                ts,
                "pass",
                player_id,
                start_xy=start,
                end_xy=end,
                accurate=accurate,
                flight_time_s=flight,
            )

    def scripted_pass(
        self,
        ts: int,
        player_id: str,
        start,
        end,
        opponents: list[tuple[str, float, float]],
        speed: float,
        accurate: bool = True,
    ) -> None:
        dist = math.hypot(end[0] - start[0], end[1] - start[1])
        flight = dist * 3.6 / speed
        tracking = []
        for pid, x, y in opponents:
            who = player(pid)
            tracking.append(
                {"player_id": pid, "team_id": who["team_id"], "xy": [x, y]}
            )
        # Receiver: a teammate standing on the end point, not an opponent.
        self.add_event(
            ts,
            "pass",
            player_id,
            start_xy=[float(start[0]), float(start[1])],
            end_xy=[float(end[0]), float(end[1])],
            accurate=accurate,
            flight_time_s=flight,
            tracking_players=tracking,
            under_pressure=True,
        )

    def scripted_shot(self, ts: int, player_id: str, start, end, speed: float) -> None:
        dist = math.hypot(end[0] - start[0], end[1] - start[1])
        self.add_event(
            ts,
            "shot",
            player_id,
            start_xy=[float(start[0]), float(start[1])],
            end_xy=[float(end[0]), float(end[1])],
            flight_time_s=dist * 3.6 / speed,
            accurate=True,
        )


def _flags(n: int, accurate_n: int, rng: random.Random) -> list[bool]:
    flags = [True] * accurate_n + [False] * (n - accurate_n)
    rng.shuffle(flags)
    return flags


def _chunk(times: list[int], sizes: list[int]) -> list[list[int]]:
    out = []
    cursor = 0
    for size in sizes:
        out.append(times[cursor : cursor + size])
        cursor += size
    if cursor != len(times):
        raise RuntimeError(f"chunk mismatch {cursor} != {len(times)}")
    return out


def generate_match(seed: int = SEED) -> list[dict]:
    b = MatchBuilder(seed)
    rng = b.rng

    # ------------------------------------------------------------------
    # 54' active (E). Possession 32/68, PPDA, accuracy, xT, signature pass.
    # ------------------------------------------------------------------
    a0, a1 = active_bounds(54)
    dur = a1 - a0
    switch = a0 + int(0.32 * dur)
    # NLR block then MCB block. 120 NLR passes, 105 MCB passes.
    nlr_times = _linspace(a0, switch, 120)
    mcb_times = _linspace(switch, a1, 104)  # signature uses its own timestamp
    # Pin the handoff so possession time is 32/68 rather than a linspace gap.
    nlr_times[0] = a0 + 1
    nlr_times[-1] = switch - 1
    mcb_times[0] = switch + 1
    mcb_times[-1] = a1 - 1
    signature_ts = 54 * 60 * 1000 + 18 * 1000
    if not (switch < signature_ts <= a1):
        raise RuntimeError("signature pass fell outside the MCB possession block")

    # Speeds: one pass at 68.4, the rest share the mean required by CCI 24.5.
    # CCI uses NLR PPDA 15.2 (the team with less possession) and 1 turnover.
    ppda_54 = 76 / 5
    v_mean = (24.5 - 4.5 * 1 - 120.0 / ppda_54) / 0.65
    n_passes = 225
    filler_speed = (v_mean * n_passes - 68.4) / (n_passes - 1)

    # NLR: 86 by Harland (start x=85, inside MCB's third, excluded from MCB PPDA),
    # 34 by central/deeper players (start x<80) including the 0.06 xT pass.
    nlr_ids = ["NLR_10", "NLR_08", "NLR_06", "NLR_09", "NLR_04", "NLR_02"]
    nlr_sizes = [6, 6, 6, 6, 5, 5]  # 34
    nlr_flags = _flags(120, 89, rng)
    saka_flags = nlr_flags[:86]
    other_flags = nlr_flags[86:]
    b.vertical_passes("NLR_07", nlr_times[:86], saka_flags, filler_speed)
    other_times = _chunk(nlr_times[86:], nlr_sizes)
    for pid, times, flags in zip(nlr_ids, other_times, _chunk(other_flags, nlr_sizes)):
        b.vertical_passes(pid, times, flags, filler_speed)
    # Replace NLR_09's first pass with the 0.06 xT progression.
    # Find it and rewrite end point. Easier to add geometry by editing the record.
    for rec in b.records:
        if rec.get("player_id") == "NLR_09" and rec.get("event_type") == "pass":
            rec["start_xy"] = [75.0, 25.0]
            rec["end_xy"] = [85.0, 25.0]
            dist = 10.0
            rec["flight_time_s"] = dist * 3.6 / filler_speed
            rec["accurate"] = True
            break

    # MCB: 29 inside NLR's third (x<=40) by #7, 75 outside, plus the signature.
    mcb_outside_ids = ["MCB_17", "MCB_16", "MCB_08", "MCB_11", "MCB_03", "MCB_05", "MCB_06"]
    mcb_sizes = [12, 11, 11, 11, 10, 10, 10]  # 75
    # 96 accurate of 105. Signature is accurate, so 95 of the other 104 are.
    mcb_flags = _flags(104, 95, rng)
    inside_flags = mcb_flags[:29]
    outside_flags = mcb_flags[29:]
    b.vertical_passes("MCB_07", mcb_times[:29], inside_flags, filler_speed)
    outside_times = _chunk(mcb_times[29:], mcb_sizes)
    for pid, times, flags in zip(mcb_outside_ids, outside_times, _chunk(outside_flags, mcb_sizes)):
        b.vertical_passes(pid, times, flags, filler_speed)
    # Six of Fenby's passes become the central xT entries (delta 0.08 each).
    xt_done = 0
    for rec in b.records:
        if rec.get("player_id") == "MCB_17" and rec.get("event_type") == "pass" and a0 < rec["timestamp_ms"] <= a1:
            rec["start_xy"] = [55.0, 45.0]
            rec["end_xy"] = [75.0, 45.0]
            rec["flight_time_s"] = 20.0 * 3.6 / filler_speed
            rec["accurate"] = True
            xt_done += 1
            if xt_done == 6:
                break
    if xt_done != 6:
        raise RuntimeError(f"expected 6 xT passes, built {xt_done}")

    # Signature line-breaker. d=32, N=3, pressure=1.75, x2>80 -> PDR 86.5.
    y = WP_ACTIVE[1]
    b.scripted_pass(
        signature_ts,
        "MCB_02",
        WP_ACTIVE,
        (WP_ACTIVE[0] + 32.0, y),
        [
            ("NLR_06", 70.0, y),
            ("NLR_08", 78.0, y + 6.0),
            ("NLR_10", 86.0, y - 6.0),
            ("NLR_04", WP_ACTIVE[0] + 32.0, y + 1.75),
        ],
        speed=68.4,
    )

    # Defensive actions and the single turnover that CCI counts.
    for ts in _linspace(switch, a1, 5):
        b.add_event(ts + 3, "tackle", "NLR_04", start_xy=[26.0, 48.0], end_xy=[26.0, 48.0])
    for ts in _linspace(a0, switch, 5):
        b.add_event(ts + 3, "tackle", "MCB_03", start_xy=[94.0, 48.0], end_xy=[94.0, 48.0])
    b.add_event(switch + 50, "possession_change", "NLR_06", start_xy=[72.0, 46.0], end_xy=[66.0, 44.0])

    # Whitmore baseline touches, early in the 15-minute window so they do not
    # leak into minute 67's baseline.
    b.add_touch(2_200_000, "MCB_02", WP_BASELINE)
    b.add_touch(2_260_000, "MCB_02", WP_BASELINE)

    # ------------------------------------------------------------------
    # 54' baseline (C, before it overlaps minute 67): PPDA 8.4 and 11.2, xT.
    # ------------------------------------------------------------------
    c0, _c1 = baseline_bounds(54)
    # Exclusive slice before 67's baseline opens at 2879s.
    c_end = 2_879_000
    base_mcb_times = _linspace(c0, c0 + (c_end - c0) // 2, 42)
    base_nlr_times = _linspace(c0 + (c_end - c0) // 2, c_end, 56)
    b.vertical_passes("MCB_16", base_mcb_times, _flags(42, 36, rng), 22.0)
    base_nlr_ids = ["NLR_08", "NLR_06", "NLR_10", "NLR_09"]
    base_sizes = [14, 14, 14, 14]
    base_flags = _flags(56, 40, rng)
    for pid, times, flags in zip(base_nlr_ids, _chunk(base_nlr_times, base_sizes), _chunk(base_flags, base_sizes)):
        b.vertical_passes(pid, times, flags, 22.0)
    # One MCB baseline pass carries the central xT that makes +340%.
    for rec in b.records:
        if (
            rec.get("player_id") == "MCB_16"
            and rec.get("event_type") == "pass"
            and c0 < rec["timestamp_ms"] <= c_end
        ):
            rec["start_xy"] = [55.0, 45.0]
            rec["end_xy"] = [65.0, 35.0]
            rec["flight_time_s"] = math.hypot(10, 10) * 3.6 / 22.0
            rec["accurate"] = True
            break
    for ts in _linspace(c0, c_end, 5):
        b.add_event(ts + 7, "tackle", "NLR_04", start_xy=[26.0, 48.0], end_xy=[26.0, 48.0])
        b.add_event(ts + 11, "interception", "MCB_05", start_xy=[94.0, 32.0], end_xy=[94.0, 32.0])

    # ------------------------------------------------------------------
    # 22' high press. NLR PPDA 5.8, 8 turnovers, PDR 82.4, shot 104.2.
    # ------------------------------------------------------------------
    h0, h1 = active_bounds(22)
    press_times = _linspace(h0, h1, 29)
    b.vertical_passes("MCB_11", press_times, _flags(29, 20, rng), 30.0)
    for ts in _linspace(h0, h1, 5):
        b.add_event(ts + 4, "tackle", "NLR_06", start_xy=[52.0, 40.0], end_xy=[52.0, 40.0])
    for ts in _linspace(h0, h1, 8):
        b.add_event(ts + 9, "possession_change", "NLR_08", start_xy=[60.0, 42.0], end_xy=[40.0, 40.0])
    # Assist. d=29.2, N=3, pressure=2, x2>80 -> PDR 82.4.
    b.scripted_pass(
        22 * 60 * 1000 + 12 * 1000,
        "NLR_10",
        (52.0, 36.0),
        (81.2, 36.0),
        [
            ("MCB_16", 60.0, 34.0),
            ("MCB_08", 68.0, 38.0),
            ("MCB_03", 76.0, 34.0),
            ("MCB_05", 81.2, 38.0),
        ],
        speed=61.0,
    )
    # Harland shot. 16 m to goal, 104.2 km/h.
    b.scripted_shot(
        22 * 60 * 1000 + 18 * 1000,
        "NLR_07",
        (104.0, 40.0),
        (120.0, 40.0),
        speed=104.2,
    )
    b.add_event(
        22 * 60 * 1000 + 19 * 1000,
        "goal",
        "NLR_07",
        start_xy=[104.0, 40.0],
        end_xy=[120.0, 40.0],
    )

    # ------------------------------------------------------------------
    # 67' pressing collapse. CCI 79.4, flank press -64%, final third 0.
    # ------------------------------------------------------------------
    g0, g1 = active_bounds(67)
    # 25 left-flank pressures after 54' has closed and before 67' active opens,
    # so they sit in the 67' baseline only.
    for ts in _linspace(3_300_000, 3_770_000, 25):
        b.add_event(ts, "pressure", "NLR_03", start_xy=[28.0, 14.0], end_xy=[30.0, 14.0])
    b.add_event(
        61 * 60 * 1000 + 18 * 1000,
        "yellow_card",
        "NLR_11",
        start_xy=[40.0, 14.0],
        end_xy=[40.0, 14.0],
    )
    # Active: 180 MCB passes, 9 flank pressures, 12 turnovers. PPDA = 20.
    # v = 19.4/0.65 so CCI = 4.5*12 + 19.4 + 120/20 = 79.4.
    chaos_speed = 19.4 / 0.65
    chaos_ids = ["MCB_11", "MCB_16", "MCB_08", "MCB_17", "MCB_03", "MCB_06"]
    chaos_sizes = [30, 30, 30, 30, 30, 30]
    chaos_times = _linspace(g0, g1, 180)
    chaos_flags = _flags(180, 150, rng)
    for pid, times, flags in zip(chaos_ids, _chunk(chaos_times, chaos_sizes), _chunk(chaos_flags, chaos_sizes)):
        b.vertical_passes(pid, times, flags, chaos_speed)
    for ts in _linspace(g0, g1, 9):
        b.add_event(ts + 2, "pressure", "NLR_03", start_xy=[28.0, 12.0], end_xy=[28.0, 12.5])
    for ts in _linspace(g0, g1, 12):
        b.add_event(ts + 6, "possession_change", "MCB_16", start_xy=[66.0, 44.0], end_xy=[50.0, 40.0])

    # Equaliser, inside 67's baseline and outside every other golden active window.
    b.scripted_shot(58 * 60 * 1000 + 12 * 1000, "MCB_09", (16.0, 40.0), (0.0, 40.0), speed=98.0)
    b.add_event(58 * 60 * 1000 + 13 * 1000, "goal", "MCB_09", start_xy=[16.0, 40.0], end_xy=[0.0, 40.0])

    # ------------------------------------------------------------------
    # 82' sub sprint and the 91.2 line-breaker.
    # ------------------------------------------------------------------
    b.add_event(
        75 * 60 * 1000,
        "substitution",
        "NLR_19",
        start_xy=[50.0, 16.0],
        end_xy=[78.0, 16.0],
    )
    sprint_dt = 1.0
    sprint_dist = 33.8 / 3.6 * sprint_dt
    sprint_t = 82 * 60 * 1000 + 10 * 1000
    b.add_sample(sprint_t, "NLR_19", (70.0, 16.0))
    b.add_sample(sprint_t + int(sprint_dt * 1000), "NLR_19", (70.0 + sprint_dist, 16.0))
    tired_dist = 20.0 / 3.6 * sprint_dt
    b.add_sample(sprint_t, "NLR_02", (36.0, 66.0))
    b.add_sample(sprint_t + int(sprint_dt * 1000), "NLR_02", (36.0 + tired_dist, 66.0))
    # d=25.6, N=4, pressure=2, x2>80 -> PDR 91.2. Ball speed 74.6.
    b.scripted_pass(
        82 * 60 * 1000 + 20 * 1000,
        "NLR_08",
        (62.0, 42.0),
        (87.6, 42.0),
        [
            ("MCB_16", 66.0, 44.0),
            ("MCB_08", 72.0, 40.0),
            ("MCB_03", 78.0, 46.0),
            ("MCB_05", 84.0, 38.0),
            ("MCB_06", 87.6, 44.0),
        ],
        speed=74.6,
    )
    b.scripted_shot(82 * 60 * 1000 + 28 * 1000, "NLR_19", (106.0, 40.0), (120.0, 40.0), speed=89.0)
    b.add_event(82 * 60 * 1000 + 29 * 1000, "goal", "NLR_19", start_xy=[106.0, 40.0], end_xy=[120.0, 40.0])

    # xG fillers in the dead zone between 22' and 54' (and after 82') so the
    # match totals land on 1.84 and 1.42. Locations are inverted from the xG
    # formula and sit outside every golden window.
    _top_up_xg(b)
    _retune_accuracy(b.records)

    _apply_score_states(b.records)
    b.records.sort(key=lambda r: (r.get("timestamp_ms", 0), r.get("event_id", "")))
    return b.records


def _top_up_xg(b: MatchBuilder) -> None:
    """Add shots whose geometry-xG tops the match up to 1.84 / 1.42."""
    from backend.engine.formulas import shot_xg

    def current(team: str) -> float:
        total = 0.0
        for rec in b.records:
            if rec.get("event_type") == "shot" and rec.get("team_id") == team:
                total += shot_xg(rec["start_xy"], team)
        return total

    def add(team: str, xg: float, ts: int, player_id: str) -> None:
        dist = 36.0 - 40.0 * xg
        if team == "NLR":
            start = [120.0 - dist, 40.0]
            end = [120.0, 40.0]
        else:
            start = [dist, 40.0]
            end = [0.0, 40.0]
        # Keep the shot on the pitch and inside the clip range of the formula.
        start[0] = min(119.0, max(1.0, start[0]))
        b.scripted_shot(ts, player_id, start, end, speed=80.0)

    # Gaps: 25:00-34:00 and 86:00-88:00. Clear of every golden window.
    nlr_need = 1.84 - current("NLR")
    mcb_need = 1.42 - current("MCB")
    ts = 26 * 60 * 1000
    for team, need, pid in (("NLR", nlr_need, "NLR_09"), ("MCB", mcb_need, "MCB_09")):
        remaining = need
        while remaining > 0.56:
            add(team, 0.55, ts, pid)
            remaining -= 0.55
            ts += 30_000
        if remaining > 0.021:
            add(team, remaining, ts, pid)
            ts += 30_000


def _retune_accuracy(records: list[dict]) -> None:
    """Force the 54' pass-accuracy ratios after geometry edits flip flags."""
    a0, a1 = active_bounds(54)

    def tune(team: str, want: int) -> None:
        passes = [
            r
            for r in records
            if r.get("event_type") == "pass"
            and r.get("team_id") == team
            and a0 < r["timestamp_ms"] <= a1
        ]
        # Keep the scripted line-breaker accurate.
        pinned = [r for r in passes if r["player_id"] == "MCB_02"]
        free = [r for r in passes if r not in pinned]
        for rec in pinned:
            rec["accurate"] = True
        need = want - len(pinned)
        for index, rec in enumerate(free):
            rec["accurate"] = index < need

    tune("MCB", 96)
    tune("NLR", 89)


def _apply_score_states(records: list[dict]) -> None:
    goals = sorted(
        (r["timestamp_ms"], r["team_id"])
        for r in records
        if r.get("event_type") == "goal"
    )
    for rec in records:
        nlr = mcb = 0
        ts = rec.get("timestamp_ms", 0)
        for gts, team in goals:
            if gts <= ts:
                if team == "NLR":
                    nlr += 1
                else:
                    mcb += 1
        if rec.get("record_type", "event") == "event":
            rec["score_state"] = {"NLR": nlr, "MCB": mcb}


def write_golden(path: Path | None = None, seed: int = SEED) -> Path:
    path = path or GOLDEN_PATH
    records = generate_match(seed)
    lines = [json.dumps(rec, separators=(",", ":"), sort_keys=True) for rec in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_golden(path: Path | None = None) -> list[dict]:
    path = path or GOLDEN_PATH
    if not path.exists():
        write_golden(path)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


if __name__ == "__main__":
    out = write_golden()
    print(f"wrote {out} ({sum(1 for _ in out.open())} rows)")
