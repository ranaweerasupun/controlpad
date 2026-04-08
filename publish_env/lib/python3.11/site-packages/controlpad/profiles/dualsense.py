"""
controlpad.profiles.dualsense
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Profile for the Sony DualSense (CFI-ZCT1W / CFI-ZCT1G).

Axis mapping verified on Raspberry Pi 5 (Linux) and macOS 14.
Note: Windows via SDL may enumerate axes differently — use the
`controlpad detect` CLI tool to verify on your platform.
"""

from .base import ControllerProfile

DUALSENSE = ControllerProfile(
    name="DualSense",
    axis_map={
        "left_x":  0,   # Left stick horizontal  (-1 = left,  +1 = right)
        "left_y":  1,   # Left stick vertical    (-1 = up,    +1 = down, raw)
        "l2":      2,   # L2 trigger             (-1 = off,   +1 = full)
        "right_x": 3,   # Right stick horizontal (-1 = left,  +1 = right)
        "right_y": 4,   # Right stick vertical   (-1 = up,    +1 = down, raw)
        "r2":      5,   # R2 trigger             (-1 = off,   +1 = full)
    },
    button_map={
        "cross":    0,
        "circle":   1,
        "square":   2,
        "triangle": 3,
        "l1":       4,
        "r1":       5,
        "l2":       6,   # Digital press (axis 2 gives analogue value)
        "r2":       7,   # Digital press (axis 5 gives analogue value)
        "share":    8,
        "options":  9,
        "l3":       10,  # Left stick click
        "r3":       11,  # Right stick click
        "ps":       12,
        "touchpad": 13,
    },
    invert_axes={"left_y", "right_y"},   # Make up = +1
    trigger_axes={"l2", "r2"},           # Normalise to [0, 1]
    hat_map={"dpad": 0},
)
