"""Broadcast shapes for the five bookmarks.

Ghost and active coincide unless a player has a measured structural shift.
These coordinates are the on-screen formation; the telemetry engine still
reports measured centroids, and the API overrides a player with those
centroids when the shift is at least 15 m.
"""

from __future__ import annotations

# player_id -> [x, y]
SHAPE_54 = {
    "NLR_01": [10, 40], "NLR_02": [30, 66], "NLR_04": [28, 50], "NLR_05": [28, 34],
    "NLR_03": [30, 16], "NLR_06": [72, 46], "NLR_10": [58, 30], "NLR_08": [62, 42],
    "NLR_07": [84, 64], "NLR_09": [88, 36], "NLR_11": [86, 16],
    "MCB_01": [110, 40], "MCB_02": [92, 70], "MCB_03": [96, 50], "MCB_05": [96, 34],
    "MCB_06": [94, 16], "MCB_16": [66, 44], "MCB_08": [74, 62], "MCB_17": [55, 45],
    "MCB_07": [48, 64], "MCB_11": [50, 18], "MCB_09": [46, 40],
}

# High press: MCB squeezed into Zone 2, NLR stepped up.
SHAPE_22 = {
    "NLR_01": [14, 40], "NLR_02": [42, 64], "NLR_04": [40, 48], "NLR_05": [40, 32],
    "NLR_03": [42, 16], "NLR_06": [52, 46], "NLR_10": [58, 36], "NLR_08": [60, 42],
    "NLR_07": [70, 62], "NLR_09": [68, 40], "NLR_11": [66, 18],
    "MCB_01": [8, 40], "MCB_02": [22, 66], "MCB_03": [16, 50], "MCB_05": [16, 32],
    "MCB_06": [22, 18], "MCB_16": [28, 58], "MCB_08": [26, 44], "MCB_17": [24, 36],
    "MCB_07": [30, 68], "MCB_11": [30, 22], "MCB_09": [20, 40],
}

# NLR pinned in a flat 5-4-1 after the booking. Ghost == active.
SHAPE_67 = {
    "NLR_01": [8, 40], "NLR_02": [22, 64], "NLR_04": [18, 50], "NLR_05": [18, 30],
    "NLR_03": [22, 16], "NLR_06": [34, 40], "NLR_10": [36, 52], "NLR_08": [36, 28],
    "NLR_07": [48, 62], "NLR_09": [46, 40], "NLR_11": [48, 18],
    "MCB_01": [112, 40], "MCB_02": [78, 66], "MCB_03": [88, 50], "MCB_05": [88, 32],
    "MCB_06": [78, 14], "MCB_16": [70, 40], "MCB_08": [64, 54], "MCB_17": [64, 28],
    "MCB_07": [56, 66], "MCB_11": [56, 16], "MCB_09": [52, 40],
}

# #19 is on, #11 is off. Odegaard is advanced enough to play the winner.
SHAPE_82 = {
    "NLR_01": [10, 40], "NLR_02": [36, 66], "NLR_04": [32, 50], "NLR_05": [32, 32],
    "NLR_03": [36, 16], "NLR_06": [48, 44], "NLR_10": [58, 32], "NLR_08": [62, 42],
    "NLR_07": [86, 64], "NLR_09": [90, 40], "NLR_19": [84, 18],
    "MCB_01": [110, 40], "MCB_02": [96, 66], "MCB_03": [100, 50], "MCB_05": [100, 32],
    "MCB_06": [96, 14], "MCB_16": [80, 44], "MCB_08": [74, 56], "MCB_17": [72, 30],
    "MCB_07": [64, 66], "MCB_11": [64, 16], "MCB_09": [58, 40],
}

SHAPE_90 = dict(SHAPE_82)

SHAPES = {22: SHAPE_22, 54: SHAPE_54, 67: SHAPE_67, 82: SHAPE_82, 90: SHAPE_90}
OFF_PITCH = {22: [], 54: ["NLR_19"], 67: ["NLR_19"], 82: ["NLR_11"], 90: ["NLR_11"]}
