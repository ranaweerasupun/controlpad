"""Tests for controlpad.filters"""

import math
import pytest
from controlpad.filters import (
    apply_deadzone,
    apply_deadzone_2d,
    apply_expo,
    ExponentialSmoother,
)


class TestApplyDeadzone:
    def test_zero_within_deadzone(self):
        assert apply_deadzone(0.03, 0.05) == 0.0

    def test_full_value_unchanged(self):
        assert apply_deadzone(1.0, 0.05) == pytest.approx(1.0)

    def test_negative_full_value(self):
        assert apply_deadzone(-1.0, 0.05) == pytest.approx(-1.0)

    def test_rescaled_outside_deadzone(self):
        # Value just outside deadzone should be close to 0 but not 0
        val = apply_deadzone(0.06, 0.05)
        assert 0.0 < val < 0.1

    def test_no_deadzone(self):
        assert apply_deadzone(0.5, 0.0) == pytest.approx(0.5)


class TestApplyDeadzone2D:
    def test_zero_within_radius(self):
        x, y = apply_deadzone_2d(0.03, 0.03, 0.1)
        assert x == 0.0
        assert y == 0.0

    def test_full_magnitude_preserved(self):
        x, y = apply_deadzone_2d(1.0, 0.0, 0.1)
        mag = math.sqrt(x * x + y * y)
        assert mag == pytest.approx(1.0, abs=0.01)

    def test_direction_preserved(self):
        raw_x, raw_y = 0.8, 0.6
        x, y = apply_deadzone_2d(raw_x, raw_y, 0.05)
        # Direction should be same as input
        raw_angle = math.atan2(raw_y, raw_x)
        out_angle = math.atan2(y, x)
        assert raw_angle == pytest.approx(out_angle, abs=1e-5)


class TestApplyExpo:
    def test_zero_expo_is_linear(self):
        assert apply_expo(0.5, 0.0) == pytest.approx(0.5)

    def test_full_range_preserved(self):
        assert apply_expo(1.0, 0.5) == pytest.approx(1.0)
        assert apply_expo(-1.0, 0.5) == pytest.approx(-1.0)

    def test_expo_reduces_centre(self):
        # With expo, mid-range values should be smaller
        linear = apply_expo(0.5, 0.0)
        curved = apply_expo(0.5, 0.8)
        assert curved < linear

    def test_sign_preserved(self):
        assert apply_expo(-0.5, 0.5) < 0


class TestExponentialSmoother:
    def test_first_value_passthrough(self):
        s = ExponentialSmoother(alpha=0.3)
        assert s.update(0.8) == pytest.approx(0.8)

    def test_converges_to_constant(self):
        s = ExponentialSmoother(alpha=0.5)
        for _ in range(50):
            v = s.update(1.0)
        assert v == pytest.approx(1.0, abs=0.001)

    def test_reset_clears_state(self):
        s = ExponentialSmoother(alpha=0.5)
        s.update(1.0)
        s.reset()
        # After reset, next value should be returned as-is
        assert s.update(0.5) == pytest.approx(0.5)

    def test_invalid_alpha_raises(self):
        with pytest.raises(ValueError):
            ExponentialSmoother(alpha=0.0)
        with pytest.raises(ValueError):
            ExponentialSmoother(alpha=1.5)
