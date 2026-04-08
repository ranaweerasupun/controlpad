"""
tests/test_mappers.py
~~~~~~~~~~~~~~~~~~~~~
Tests for the output mapping system introduced in v0.3.0.

Organised into five areas:

  1. Mapper core — scale(), clamping, inversion, center_deadband
  2. Mapper validation — invalid construction arguments
  3. Mapper properties — center, repr
  4. PWM preset
  5. SERVO preset
  6. MOTOR preset
"""

from __future__ import annotations

import pytest
from controlpad.mappers import Mapper, PWM, SERVO, MOTOR


# ═══════════════════════════════════════════════════════════════════════
# 1. Mapper core
# ═══════════════════════════════════════════════════════════════════════

class TestMapperScale:

    def test_centre_maps_to_centre(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        assert m.scale(0.0) == pytest.approx(1500.0)

    def test_source_min_maps_to_target_min(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        assert m.scale(-1.0) == pytest.approx(1000.0)

    def test_source_max_maps_to_target_max(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        assert m.scale(1.0) == pytest.approx(2000.0)

    def test_midpoint_value(self):
        m = Mapper(source=(-1.0, 1.0), target=(0.0, 100.0))
        assert m.scale(0.5) == pytest.approx(75.0)

    def test_one_sided_source(self):
        """Trigger axes run 0→1, not -1→+1."""
        m = Mapper(source=(0.0, 1.0), target=(1000.0, 2000.0))
        assert m.scale(0.0) == pytest.approx(1000.0)
        assert m.scale(1.0) == pytest.approx(2000.0)
        assert m.scale(0.5) == pytest.approx(1500.0)

    def test_negative_target_range(self):
        """Target range can run high→low (reversed)."""
        m = Mapper(source=(-1.0, 1.0), target=(2000.0, 1000.0))
        assert m.scale(-1.0) == pytest.approx(2000.0)
        assert m.scale(1.0)  == pytest.approx(1000.0)
        assert m.scale(0.0)  == pytest.approx(1500.0)

    def test_custom_source_range(self):
        m = Mapper(source=(0.0, 100.0), target=(0.0, 1.0))
        assert m.scale(50.0) == pytest.approx(0.5)

    def test_float_target_range(self):
        m = Mapper(source=(-1.0, 1.0), target=(-90.0, 90.0))
        assert m.scale(0.0)   == pytest.approx(0.0)
        assert m.scale(1.0)   == pytest.approx(90.0)
        assert m.scale(-1.0)  == pytest.approx(-90.0)


class TestMapperClamping:

    def test_clamp_above_source_max(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), clamp=True)
        assert m.scale(1.5) == pytest.approx(2000.0)

    def test_clamp_below_source_min(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), clamp=True)
        assert m.scale(-1.5) == pytest.approx(1000.0)

    def test_clamp_disabled_allows_out_of_range(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), clamp=False)
        # 1.5 → normalised t = 1.25 → output = 1000 + 1.25 * 1000 = 2250
        assert m.scale(1.5) == pytest.approx(2250.0)

    def test_clamp_enabled_by_default(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        assert m.clamp is True
        assert m.scale(99.0) == pytest.approx(2000.0)


class TestMapperInvert:

    def test_invert_flips_min_and_max(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), invert=True)
        assert m.scale(-1.0) == pytest.approx(2000.0)
        assert m.scale(1.0)  == pytest.approx(1000.0)

    def test_invert_preserves_centre(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), invert=True)
        assert m.scale(0.0) == pytest.approx(1500.0)

    def test_no_invert_by_default(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        assert m.invert is False
        assert m.scale(1.0) == pytest.approx(2000.0)


class TestMapperCenterDeadband:

    def test_value_inside_deadband_snaps_to_centre(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=15.0)
        # scale(0.01) → ~1505, which is within ±15 of 1500
        assert m.scale(0.01) == pytest.approx(1500.0)

    def test_value_outside_deadband_is_not_snapped(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=15.0)
        # scale(0.5) → 1750, well outside ±15 of 1500
        result = m.scale(0.5)
        assert result == pytest.approx(1750.0)
        assert result != pytest.approx(1500.0)

    def test_exact_centre_value_snaps(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=15.0)
        assert m.scale(0.0) == pytest.approx(1500.0)

    def test_deadband_edge_snaps(self):
        """A value that maps to exactly centre ± deadband should snap."""
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=15.0)
        # scale(0.03) → 1515.0, which is exactly at the edge → should snap
        assert m.scale(0.03) == pytest.approx(1500.0)

    def test_zero_deadband_disabled(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=0.0)
        # Even a tiny input should produce a non-centre output
        result = m.scale(0.01)
        assert result != pytest.approx(1500.0)

    def test_deadband_works_with_negative_target_side(self):
        """Deadband applies symmetrically on both sides of centre."""
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=15.0)
        # scale(-0.01) → ~1495, within ±15 of 1500
        assert m.scale(-0.01) == pytest.approx(1500.0)


# ═══════════════════════════════════════════════════════════════════════
# 2. Mapper validation
# ═══════════════════════════════════════════════════════════════════════

class TestMapperValidation:

    def test_zero_width_source_raises(self):
        with pytest.raises(ValueError, match="zero-width"):
            Mapper(source=(1.0, 1.0), target=(0.0, 100.0))

    def test_negative_center_deadband_raises(self):
        with pytest.raises(ValueError, match="center_deadband"):
            Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=-1.0)

    def test_valid_zero_deadband_does_not_raise(self):
        Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0), center_deadband=0.0)


# ═══════════════════════════════════════════════════════════════════════
# 3. Mapper properties
# ═══════════════════════════════════════════════════════════════════════

class TestMapperProperties:

    def test_center_symmetric_range(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        assert m.center == pytest.approx(1500.0)

    def test_center_asymmetric_range(self):
        m = Mapper(source=(-1.0, 1.0), target=(0.0, 180.0))
        assert m.center == pytest.approx(90.0)

    def test_center_negative_range(self):
        m = Mapper(source=(-1.0, 1.0), target=(-255.0, 255.0))
        assert m.center == pytest.approx(0.0)

    def test_repr_contains_key_info(self):
        m = Mapper(source=(-1.0, 1.0), target=(1000.0, 2000.0))
        r = repr(m)
        assert "Mapper" in r
        assert "source" in r
        assert "target" in r


# ═══════════════════════════════════════════════════════════════════════
# 4. PWM preset
# ═══════════════════════════════════════════════════════════════════════

class TestPWM:

    def test_default_range(self):
        pwm = PWM()
        assert pwm.scale(-1.0) == pytest.approx(1000.0)
        assert pwm.scale(0.0)  == pytest.approx(1500.0)
        assert pwm.scale(1.0)  == pytest.approx(2000.0)

    def test_custom_range(self):
        pwm = PWM(min_us=900, max_us=2100)
        assert pwm.scale(-1.0) == pytest.approx(900.0)
        assert pwm.scale(1.0)  == pytest.approx(2100.0)

    def test_one_sided(self):
        pwm = PWM(one_sided=True)
        assert pwm.scale(0.0) == pytest.approx(1000.0)
        assert pwm.scale(1.0) == pytest.approx(2000.0)
        assert pwm.scale(0.5) == pytest.approx(1500.0)

    def test_invert(self):
        pwm = PWM(invert=True)
        assert pwm.scale(1.0)  == pytest.approx(1000.0)
        assert pwm.scale(-1.0) == pytest.approx(2000.0)
        assert pwm.scale(0.0)  == pytest.approx(1500.0)

    def test_center_deadband(self):
        pwm = PWM(center_deadband=15.0)
        assert pwm.scale(0.01) == pytest.approx(1500.0)
        assert pwm.scale(0.5)  == pytest.approx(1750.0)

    def test_returns_mapper_instance(self):
        assert isinstance(PWM(), Mapper)


# ═══════════════════════════════════════════════════════════════════════
# 5. SERVO preset
# ═══════════════════════════════════════════════════════════════════════

class TestSERVO:

    def test_default_range(self):
        servo = SERVO()
        assert servo.scale(-1.0) == pytest.approx(-90.0)
        assert servo.scale(0.0)  == pytest.approx(0.0)
        assert servo.scale(1.0)  == pytest.approx(90.0)

    def test_custom_range(self):
        servo = SERVO(min_deg=-45.0, max_deg=45.0)
        assert servo.scale(-1.0) == pytest.approx(-45.0)
        assert servo.scale(1.0)  == pytest.approx(45.0)
        assert servo.scale(0.0)  == pytest.approx(0.0)

    def test_invert(self):
        servo = SERVO(invert=True)
        assert servo.scale(1.0)  == pytest.approx(-90.0)
        assert servo.scale(-1.0) == pytest.approx(90.0)

    def test_center_deadband(self):
        servo = SERVO(center_deadband=2.0)
        assert servo.scale(0.01) == pytest.approx(0.0)
        assert servo.scale(0.5)  == pytest.approx(45.0)

    def test_returns_mapper_instance(self):
        assert isinstance(SERVO(), Mapper)


# ═══════════════════════════════════════════════════════════════════════
# 6. MOTOR preset
# ═══════════════════════════════════════════════════════════════════════

class TestMOTOR:

    def test_default_bidirectional_range(self):
        motor = MOTOR()
        assert motor.scale(-1.0) == pytest.approx(0.0)
        assert motor.scale(0.0)  == pytest.approx(127.5)
        assert motor.scale(1.0)  == pytest.approx(255.0)

    def test_symmetric_bidirectional(self):
        motor = MOTOR(min_value=-255, max_value=255)
        assert motor.scale(-1.0) == pytest.approx(-255.0)
        assert motor.scale(0.0)  == pytest.approx(0.0)
        assert motor.scale(1.0)  == pytest.approx(255.0)

    def test_one_sided(self):
        motor = MOTOR(one_sided=True)
        assert motor.scale(0.0) == pytest.approx(0.0)
        assert motor.scale(1.0) == pytest.approx(255.0)
        assert motor.scale(0.5) == pytest.approx(127.5)

    def test_invert(self):
        motor = MOTOR(min_value=-255, max_value=255, invert=True)
        assert motor.scale(1.0)  == pytest.approx(-255.0)
        assert motor.scale(-1.0) == pytest.approx(255.0)

    def test_custom_range(self):
        motor = MOTOR(min_value=0, max_value=1023)
        assert motor.scale(-1.0) == pytest.approx(0.0)
        assert motor.scale(1.0)  == pytest.approx(1023.0)

    def test_center_deadband(self):
        motor = MOTOR(min_value=-255, max_value=255, center_deadband=10.0)
        assert motor.scale(0.02) == pytest.approx(0.0)
        assert motor.scale(0.5)  == pytest.approx(127.5)

    def test_returns_mapper_instance(self):
        assert isinstance(MOTOR(), Mapper)
