"""
controlpad.filters
~~~~~~~~~~~~~~~~~~
Input filters: deadzone clamping, linear/exponential smoothing.

All filters operate on values in the range [-1.0, +1.0].
"""

from __future__ import annotations
import math


def apply_deadzone(value: float, deadzone: float) -> float:
    """
    Apply a circular deadzone to a single axis value.

    Values within `deadzone` of zero are clamped to zero.
    Values outside are rescaled so the output still spans [-1, +1],
    eliminating the dead "step" at the edge of the deadzone.

    Args:
        value:    Raw axis value in [-1.0, +1.0].
        deadzone: Fraction of the range to treat as zero [0.0, 1.0).

    Returns:
        Filtered value in [-1.0, +1.0].
    """
    if deadzone <= 0.0:
        return value

    abs_val = abs(value)
    if abs_val < deadzone:
        return 0.0

    # Rescale: map [deadzone, 1.0] → [0.0, 1.0]
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs_val - deadzone) / (1.0 - deadzone)


def apply_deadzone_2d(x: float, y: float, deadzone: float) -> tuple[float, float]:
    """
    Apply a radial (circular) deadzone to a 2-axis stick.

    Unlike per-axis deadzones, this treats the stick as a 2D vector so the
    dead region is a circle rather than a square, giving smoother diagonals.

    Args:
        x, y:     Raw stick values in [-1.0, +1.0].
        deadzone: Circular deadzone radius [0.0, 1.0).

    Returns:
        Tuple (x, y) after deadzone, each in [-1.0, +1.0].
    """
    if deadzone <= 0.0:
        return x, y

    magnitude = math.sqrt(x * x + y * y)
    if magnitude < deadzone:
        return 0.0, 0.0

    # Rescale the vector so magnitude spans [0, 1] outside the dead circle
    scale = (magnitude - deadzone) / (1.0 - deadzone) / magnitude
    return x * scale, y * scale


def apply_expo(value: float, expo: float) -> float:
    """
    Apply an exponential curve to an axis value.

    Expo reduces sensitivity near centre while preserving full range at the
    edges — standard on RC transmitters and flight controllers.

    Args:
        value: Axis value in [-1.0, +1.0].
        expo:  Curve strength in [0.0, 1.0].
                0.0 = linear (no effect), 1.0 = maximum curve.

    Returns:
        Curved value in [-1.0, +1.0].
    """
    if expo <= 0.0:
        return value

    expo = max(0.0, min(1.0, expo))
    abs_val = abs(value)
    sign = 1.0 if value >= 0 else -1.0

    # Blend linear and cubic: output = v*(1-e) + v³*e
    curved = abs_val * (1.0 - expo) + (abs_val ** 3) * expo
    return sign * curved


class ExponentialSmoother:
    """
    Single-axis low-pass filter using exponential moving average.

    Smooths out jitter and sudden spikes without introducing significant lag.
    A lower `alpha` gives more smoothing but more lag; higher = more responsive.

    Usage::

        smoother = ExponentialSmoother(alpha=0.2)
        smoothed = smoother.update(raw_value)
    """

    def __init__(self, alpha: float = 0.3):
        """
        Args:
            alpha: Smoothing factor in (0.0, 1.0].
                   0.1 = heavy smoothing, 0.5 = light, 1.0 = no smoothing.
        """
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        self.alpha = alpha
        self._value: float | None = None

    def update(self, raw: float) -> float:
        """Feed a new raw value and return the smoothed output."""
        if self._value is None:
            self._value = raw
        else:
            self._value = self.alpha * raw + (1.0 - self.alpha) * self._value
        return self._value

    def reset(self) -> None:
        """Reset filter state (e.g. after reconnect)."""
        self._value = None
