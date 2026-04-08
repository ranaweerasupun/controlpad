"""Tests for controlpad.profiles"""

import pytest
from controlpad.profiles import (
    get_profile,
    register_profile,
    list_profiles,
    detect_profile,
    DUALSENSE,
    XBOX,
    ControllerProfile,
)
from controlpad.exceptions import UnknownProfile


class TestRegistry:
    def test_get_dualsense(self):
        p = get_profile("dualsense")
        assert p.name == "DualSense"

    def test_get_xbox(self):
        p = get_profile("xbox")
        assert p.name == "Xbox"

    def test_case_insensitive(self):
        assert get_profile("DualSense") == get_profile("dualsense")

    def test_unknown_raises(self):
        with pytest.raises(UnknownProfile):
            get_profile("nonexistent_controller_xyz")

    def test_list_profiles_includes_builtins(self):
        names = list_profiles()
        assert "dualsense" in names
        assert "xbox" in names

    def test_register_custom(self):
        custom = ControllerProfile(
            name="TestController",
            axis_map={"x": 0, "y": 1},
            button_map={"fire": 0},
        )
        register_profile(custom)
        assert get_profile("testcontroller") is custom


class TestDetectProfile:
    def test_detects_dualsense(self):
        p = detect_profile("Sony Interactive Entertainment DualSense Wireless Controller")
        assert p is not None
        assert "dual" in p.name.lower() or p.name == "DualSense"

    def test_detects_wireless_controller(self):
        p = detect_profile("Wireless Controller")
        assert p is not None

    def test_detects_xbox(self):
        p = detect_profile("Xbox Series X Controller")
        assert p is not None
        assert p.name == "Xbox"

    def test_unknown_returns_none(self):
        p = detect_profile("Unknown HID Joystick Device 9000")
        assert p is None


class TestDualSenseProfile:
    def test_axis_map_complete(self):
        expected = {"left_x", "left_y", "right_x", "right_y", "l2", "r2"}
        assert expected.issubset(set(DUALSENSE.axis_map.keys()))

    def test_button_map_has_face_buttons(self):
        assert "cross" in DUALSENSE.button_map
        assert "circle" in DUALSENSE.button_map
        assert "square" in DUALSENSE.button_map
        assert "triangle" in DUALSENSE.button_map

    def test_y_axes_inverted(self):
        assert "left_y" in DUALSENSE.invert_axes
        assert "right_y" in DUALSENSE.invert_axes

    def test_triggers_in_trigger_axes(self):
        assert "l2" in DUALSENSE.trigger_axes
        assert "r2" in DUALSENSE.trigger_axes
