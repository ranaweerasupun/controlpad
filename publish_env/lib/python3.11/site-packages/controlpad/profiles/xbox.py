"""
controlpad.profiles.xbox
~~~~~~~~~~~~~~~~~~~~~~~~~
Profile for Xbox One / Series X|S controllers (via USB or Bluetooth).

Axis mapping verified on Linux (xpadneo driver) and macOS.
"""

from .base import ControllerProfile

XBOX = ControllerProfile(
    name="Xbox",
    axis_map={
        "left_x":  0,
        "left_y":  1,
        "right_x": 3,
        "right_y": 4,
        "lt":      2,   # Left trigger  (-1 = off, +1 = full)
        "rt":      5,   # Right trigger (-1 = off, +1 = full)
    },
    button_map={
        "a":       0,
        "b":       1,
        "x":       2,
        "y":       3,
        "lb":      4,
        "rb":      5,
        "lt":      6,
        "rt":      7,
        "select":  6,   # Back / View
        "start":   7,   # Menu
        "l3":      8,
        "r3":      9,
        "home":    10,
        "share":   11,
    },
    invert_axes={"left_y", "right_y"},
    trigger_axes={"lt", "rt"},
    hat_map={"dpad": 0},
)
