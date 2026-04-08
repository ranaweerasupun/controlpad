"""
controlpad.profiles.generic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Fallback profile for any HID gamepad not explicitly supported.

Axes and buttons are accessible by their raw index:
  axis_0, axis_1, ..., axis_N
  button_0, button_1, ..., button_N

Use `controlpad detect` to discover the mapping for your specific
controller, then create a custom profile.
"""

from __future__ import annotations
from .base import ControllerProfile


def build_generic_profile(num_axes: int, num_buttons: int) -> ControllerProfile:
    """
    Dynamically build a profile for an unknown controller.

    Args:
        num_axes:    Number of axes reported by pygame.
        num_buttons: Number of buttons reported by pygame.

    Returns:
        A ControllerProfile with generic axis_N / button_N names.
    """
    axis_map = {f"axis_{i}": i for i in range(num_axes)}
    button_map = {f"button_{i}": i for i in range(num_buttons)}

    return ControllerProfile(
        name="Generic",
        axis_map=axis_map,
        button_map=button_map,
        hat_map={"dpad": 0},
    )
