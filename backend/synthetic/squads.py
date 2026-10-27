"""Synthetic squads. Invented surnames only — no real players and no trademarks."""

from __future__ import annotations

MATCH_ID = "pl_syn_2026_nlr_mcb"
SEED = 2026

# Home (x, y) on a 120 x 80 pitch. NLR always attacks toward x = 120.
# A few homes sit inside the Zone 14 pocket used at 54' so the 3v2 is real.
SQUAD: list[dict] = [
    {"player_id": "NLR_01", "team_id": "NLR", "shirt_number": 1, "player_name": "M. Pellam", "player_role": "GK", "home_xy": [8.0, 40.0]},
    {"player_id": "NLR_02", "team_id": "NLR", "shirt_number": 2, "player_name": "J. Brant", "player_role": "RB", "home_xy": [28.0, 66.0]},
    {"player_id": "NLR_04", "team_id": "NLR", "shirt_number": 4, "player_name": "N. Tarn", "player_role": "CB", "home_xy": [26.0, 48.0]},
    {"player_id": "NLR_05", "team_id": "NLR", "shirt_number": 5, "player_name": "P. Quillan", "player_role": "CB", "home_xy": [26.0, 28.0]},
    {"player_id": "NLR_03", "team_id": "NLR", "shirt_number": 3, "player_name": "L. Vexley", "player_role": "LB", "home_xy": [28.0, 14.0]},
    {"player_id": "NLR_06", "team_id": "NLR", "shirt_number": 6, "player_name": "R. Tambor", "player_role": "DM", "home_xy": [72.0, 46.0]},
    {"player_id": "NLR_10", "team_id": "NLR", "shirt_number": 10, "player_name": "F. Lorne", "player_role": "CM", "home_xy": [52.0, 28.0]},
    {"player_id": "NLR_08", "team_id": "NLR", "shirt_number": 8, "player_name": "M. Elwick", "player_role": "CAM", "home_xy": [62.0, 42.0]},
    {"player_id": "NLR_07", "team_id": "NLR", "shirt_number": 7, "player_name": "B. Harland", "player_role": "RW", "home_xy": [85.0, 66.0]},
    {"player_id": "NLR_09", "team_id": "NLR", "shirt_number": 9, "player_name": "I. Calloway", "player_role": "ST", "home_xy": [75.0, 25.0]},
    {"player_id": "NLR_11", "team_id": "NLR", "shirt_number": 11, "player_name": "K. Vesper", "player_role": "LW", "home_xy": [72.0, 12.0]},
    {"player_id": "NLR_19", "team_id": "NLR", "shirt_number": 19, "player_name": "L. Torven", "player_role": "LW", "home_xy": [78.0, 16.0], "substitute": True},
    {"player_id": "MCB_01", "team_id": "MCB", "shirt_number": 1, "player_name": "N. Sorell", "player_role": "GK", "home_xy": [110.0, 40.0]},
    {"player_id": "MCB_02", "team_id": "MCB", "shirt_number": 2, "player_name": "K. Whitmore", "player_role": "RB", "home_xy": [92.0, 66.0]},
    {"player_id": "MCB_03", "team_id": "MCB", "shirt_number": 3, "player_name": "M. Drayton", "player_role": "CB", "home_xy": [94.0, 48.0]},
    {"player_id": "MCB_05", "team_id": "MCB", "shirt_number": 5, "player_name": "L. Harrow", "player_role": "CB", "home_xy": [94.0, 32.0]},
    {"player_id": "MCB_06", "team_id": "MCB", "shirt_number": 6, "player_name": "B. Ellison", "player_role": "LB", "home_xy": [92.0, 14.0]},
    {"player_id": "MCB_16", "team_id": "MCB", "shirt_number": 16, "player_name": "E. Marlow", "player_role": "DM", "home_xy": [66.0, 44.0]},
    {"player_id": "MCB_08", "team_id": "MCB", "shirt_number": 8, "player_name": "H. Quenby", "player_role": "CM", "home_xy": [74.0, 62.0]},
    {"player_id": "MCB_17", "team_id": "MCB", "shirt_number": 17, "player_name": "A. Fenby", "player_role": "CAM", "home_xy": [55.0, 45.0]},
    {"player_id": "MCB_07", "team_id": "MCB", "shirt_number": 7, "player_name": "I. Corvin", "player_role": "RW", "home_xy": [38.0, 66.0]},
    {"player_id": "MCB_11", "team_id": "MCB", "shirt_number": 11, "player_name": "J. Ashcombe", "player_role": "LW", "home_xy": [48.0, 14.0]},
    {"player_id": "MCB_09", "team_id": "MCB", "shirt_number": 9, "player_name": "E. Bramley", "player_role": "ST", "home_xy": [46.0, 40.0]},
]

BY_ID = {p["player_id"]: p for p in SQUAD}
STARTERS = [p["player_id"] for p in SQUAD if not p.get("substitute")]


def player(player_id: str) -> dict:
    return BY_ID[player_id]


# Zone 14 pocket used for the 54' overload (absolute pitch coordinates).
ZONE_14 = {"x_min": 54.0, "x_max": 82.0, "y_min": 32.0, "y_max": 56.0}
# Zone 2, where NLR's high press traps MCB at 22'.
ZONE_2 = {"x_min": 4.0, "x_max": 32.0, "y_min": 48.0, "y_max": 76.0}
# Left flank (top touchline, y near 0).
LEFT_FLANK_Y = 20.0
