"""
controlpad.mappers
~~~~~~~~~~~~~~~~~~
Output mapping: rescale processed axis values into any target range.

After deadzone and expo are applied, axis values live in [-1.0, +1.0]
(or [0.0, +1.0] for triggers and one-sided axes).  Every robotics or
drone application then has to translate those values into whatever the
hardware expects — PWM microseconds, servo degrees, motor driver counts.
This module provides that translation so developers never have to write
it themselves.

Basic usage::

    from controlpad.mappers import Mapper, PWM, SERVO

    pwm   = PWM()            # (-1, 1) → (1000, 2000 µs)
    servo = SERVO()          # (-1, 1) → (-90°, +90°)

    @gp.on_axis("left_y")
    def on_throttle(value):
        esc.set_pulse(pwm.scale(value))
        rudder.set_angle(servo.scale(value))
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Mapper:
    """
    Rescale a processed axis value from one numeric range to another.

    A ``Mapper`` converts the clean [-1, +1] output of a ``Gamepad`` axis
    into whatever unit your hardware needs — PWM microseconds, servo degrees,
    motor driver byte values, and so on.

    Attributes:
        source:          The input range to map from.  Defaults to (-1.0, +1.0),
                         which matches standard two-sided axes.  Use (0.0, 1.0)
                         for triggers and other one-sided axes.
        target:          The output range to map to.
        invert:          Flip the output so that source minimum maps to target
                         maximum and vice-versa.  Equivalent to swapping the
                         target tuple but more explicit at the call site.
        clamp:           Clamp the input to ``source`` before scaling.
                         Defaults to ``True`` — prevents out-of-range output
                         when a stick is not perfectly zeroed or calibrated.
        center_deadband: A ±band around the centre of the *target* range within
                         which the output is snapped to the exact centre value.
                         Useful for ESCs that are sensitive around neutral —
                         e.g. ``center_deadband=10`` on a PWM(1000, 2000) mapper
                         holds the output at exactly 1500 µs until the stick
                         moves far enough to leave the ±10 µs band.
                         Set to 0.0 (default) to disable.

    Examples::

        # Two-sided axis → PWM
        pwm = Mapper(target=(1000, 2000))
        pwm.scale(0.0)    # → 1500.0
        pwm.scale(1.0)    # → 2000.0
        pwm.scale(-1.0)   # → 1000.0

        # Trigger (0–1) → motor driver (0–255)
        motor = Mapper(source=(0.0, 1.0), target=(0, 255))
        motor.scale(0.5)  # → 127.5

        # Inverted channel
        inv = Mapper(target=(1000, 2000), invert=True)
        inv.scale(1.0)    # → 1000.0

        # Snap to 1500 µs until stick leaves ±15 µs of centre
        esc = Mapper(target=(1000, 2000), center_deadband=15)
        esc.scale(0.01)   # → 1500.0  (inside deadband)
        esc.scale(0.5)    # → 1750.0  (outside deadband)
    """

    source:          tuple[float, float] = (-1.0, 1.0)
    target:          tuple[float, float] = (-1.0, 1.0)
    invert:          bool                = False
    clamp:           bool                = True
    center_deadband: float               = 0.0

    def __post_init__(self) -> None:
        src_lo, src_hi = self.source
        tgt_lo, tgt_hi = self.target

        if src_lo == src_hi:
            raise ValueError(
                f"source range cannot be zero-width: {self.source}"
            )
        if self.center_deadband < 0.0:
            raise ValueError(
                f"center_deadband must be >= 0, got {self.center_deadband}"
            )

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def scale(self, value: float) -> float:
        """
        Rescale *value* from the source range to the target range.

        Args:
            value: The processed axis value to rescale.

        Returns:
            The mapped value in the target range (or exactly at the target
            centre if ``center_deadband`` is set and the value falls within it).
        """
        src_lo, src_hi = self.source
        tgt_lo, tgt_hi = self.target

        # 1. Clamp to source range
        if self.clamp:
            value = max(src_lo, min(src_hi, value))

        # 2. Normalise to [0.0, 1.0]
        t = (value - src_lo) / (src_hi - src_lo)

        # 3. Invert
        if self.invert:
            t = 1.0 - t

        # 4. Map to target range
        output = tgt_lo + t * (tgt_hi - tgt_lo)

        # 5. Center deadband (snap to target midpoint)
        if self.center_deadband > 0.0:
            centre = (tgt_lo + tgt_hi) / 2.0
            if abs(output - centre) <= self.center_deadband:
                output = centre

        return output

    # ──────────────────────────────────────────────────────────────────
    # Convenience
    # ──────────────────────────────────────────────────────────────────

    @property
    def center(self) -> float:
        """The exact midpoint of the target range."""
        return (self.target[0] + self.target[1]) / 2.0

    def __repr__(self) -> str:
        return (
            f"Mapper(source={self.source}, target={self.target}, "
            f"invert={self.invert}, clamp={self.clamp}, "
            f"center_deadband={self.center_deadband})"
        )


# ══════════════════════════════════════════════════════════════════════
# Preset factories
# ══════════════════════════════════════════════════════════════════════

def PWM(
    *,
    min_us:          int   = 1000,
    max_us:          int   = 2000,
    one_sided:       bool  = False,
    invert:          bool  = False,
    center_deadband: float = 0.0,
) -> Mapper:
    """
    Mapper for PWM ESCs and servos that accept microsecond pulse widths.

    The standard RC PWM range is 1000–2000 µs, with 1500 µs as neutral.
    Most ESCs and flight controllers expect values in this range.

    Args:
        min_us:          Minimum pulse width in microseconds (default 1000).
        max_us:          Maximum pulse width in microseconds (default 2000).
        one_sided:       Set ``True`` for throttle / trigger axes that run
                         0 → 1 rather than -1 → +1.
        invert:          Reverse the direction of the output.
        center_deadband: µs band around 1500 µs that snaps to exactly neutral.
                         Useful for ESCs sensitive around the arming point.

    Returns:
        A configured :class:`Mapper` instance.

    Examples::

        # Standard two-sided axis (pitch, roll, yaw)
        pwm = PWM()
        pwm.scale(0.0)    # → 1500.0
        pwm.scale(1.0)    # → 2000.0
        pwm.scale(-1.0)   # → 1000.0

        # Throttle from trigger (0 → 1)
        throttle = PWM(one_sided=True)
        throttle.scale(0.0)   # → 1000.0
        throttle.scale(1.0)   # → 2000.0
        throttle.scale(0.5)   # → 1500.0

        # Inverted channel
        inv = PWM(invert=True)
        inv.scale(1.0)    # → 1000.0

        # Deadband around neutral to avoid ESC chatter
        esc = PWM(center_deadband=15)
        esc.scale(0.01)   # → 1500.0 (snapped to neutral)
    """
    source = (0.0, 1.0) if one_sided else (-1.0, 1.0)
    return Mapper(
        source          = source,
        target          = (float(min_us), float(max_us)),
        invert          = invert,
        center_deadband = center_deadband,
    )


def SERVO(
    *,
    min_deg:         float = -90.0,
    max_deg:         float =  90.0,
    invert:          bool  = False,
    center_deadband: float = 0.0,
) -> Mapper:
    """
    Mapper for servos that accept angular position in degrees.

    Args:
        min_deg:         Minimum angle in degrees (default -90°).
        max_deg:         Maximum angle in degrees (default +90°).
        invert:          Reverse the direction of travel.
        center_deadband: Degree band around 0° that snaps to exactly centre.

    Returns:
        A configured :class:`Mapper` instance.

    Examples::

        servo = SERVO()
        servo.scale(0.0)    # → 0.0°
        servo.scale(1.0)    # → 90.0°
        servo.scale(-1.0)   # → -90.0°

        # 180° servo
        wide = SERVO(min_deg=-90, max_deg=90)

        # Snap to 0° within ±2° of centre
        precise = SERVO(center_deadband=2.0)
        precise.scale(0.01)  # → 0.0° (snapped)
    """
    return Mapper(
        source          = (-1.0, 1.0),
        target          = (min_deg, max_deg),
        invert          = invert,
        center_deadband = center_deadband,
    )


def MOTOR(
    *,
    min_value:       int   = 0,
    max_value:       int   = 255,
    one_sided:       bool  = False,
    invert:          bool  = False,
    center_deadband: float = 0.0,
) -> Mapper:
    """
    Mapper for motor drivers that accept integer byte values (0–255 or similar).

    Args:
        min_value:       Minimum driver value (default 0).
        max_value:       Maximum driver value (default 255).
        one_sided:       Set ``True`` for axes that run 0 → 1 (triggers,
                         throttle levers) rather than -1 → +1.
        invert:          Reverse the direction of the output.
        center_deadband: Band around the midpoint that snaps to exactly centre.

    Returns:
        A configured :class:`Mapper` instance.

    Examples::

        # Full bidirectional motor (-255 to +255 driver)
        motor = MOTOR(min_value=-255, max_value=255)
        motor.scale(0.0)    # → 0.0
        motor.scale(1.0)    # → 255.0
        motor.scale(-1.0)   # → -255.0

        # Trigger → 0–255 (always forward)
        drive = MOTOR(one_sided=True)
        drive.scale(0.0)    # → 0.0
        drive.scale(1.0)    # → 255.0
        drive.scale(0.5)    # → 127.5
    """
    source = (0.0, 1.0) if one_sided else (-1.0, 1.0)
    return Mapper(
        source          = source,
        target          = (float(min_value), float(max_value)),
        invert          = invert,
        center_deadband = center_deadband,
    )
