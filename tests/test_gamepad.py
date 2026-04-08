"""Tests for controlpad.gamepad using the mock backend fixture."""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock

from controlpad.backends.base import RawState
from controlpad.exceptions import ControllerDisconnected


class TestControllerState:
    def test_axis_returns_named_value(self, gamepad):
        raw = RawState(
            axes    = [0.5, 0.0, -1.0, 0.0, 0.0, -1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()

        assert state.axis("left_x") == pytest.approx(0.5, abs=0.04)

    def test_axis_default_for_unknown(self, gamepad):
        state = gamepad.read()
        assert state.axis("nonexistent_axis", default=99.0) == 99.0

    def test_button_returns_true_when_pressed(self, gamepad):
        buttons = [False] * 14
        buttons[0] = True   # cross = index 0 on DualSense
        raw = RawState(
            axes    = [0.0] * 6,
            buttons = buttons,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.button("cross") is True

    def test_dpad_state(self, gamepad):
        raw = RawState(
            axes    = [0.0] * 6,
            buttons = [False] * 14,
            hats    = [(1, 0)],   # Right on D-pad
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.dpad == (1, 0)

    def test_trigger_normalised_to_0_1(self, gamepad):
        # L2 (axis index 2 on DualSense) fully pressed → raw +1.0
        raw = RawState(
            axes    = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.axis("l2") == pytest.approx(1.0, abs=0.01)

    def test_trigger_released_is_zero(self, gamepad):
        # L2 fully released → raw -1.0 → normalised 0.0
        raw = RawState(
            axes    = [0.0, 0.0, -1.0, 0.0, 0.0, -1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.axis("l2") == pytest.approx(0.0, abs=0.01)

    def test_y_axis_inverted(self, gamepad):
        # DualSense left_y: raw -1.0 (stick up) should become +1.0
        raw = RawState(
            axes    = [0.0, -1.0, -1.0, 0.0, 0.0, -1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.axis("left_y") == pytest.approx(1.0, abs=0.02)


class TestDeadzone:
    def test_small_input_zeroed(self, gamepad):
        gamepad.set_deadzone(0.1)
        raw = RawState(
            axes    = [0.05, 0.05, -1.0, 0.0, 0.0, -1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.axis("left_x") == 0.0
        assert state.axis("left_y") == 0.0

    def test_large_input_passes(self, gamepad):
        gamepad.set_deadzone(0.1)
        raw = RawState(
            axes    = [0.9, 0.0, -1.0, 0.0, 0.0, -1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        assert state.axis("left_x") > 0.5


class TestCallbacks:
    def test_button_press_callback_fires(self, gamepad):
        fired = []

        @gamepad.on_button_press("cross")
        def on_cross():
            fired.append(True)

        # First read: released
        released = RawState(
            axes=[0.0]*6, buttons=[False]*14, hats=[(0,0)],
            name="DualSense Wireless Controller"
        )
        gamepad._backend.poll.return_value = released
        state = gamepad.read()
        gamepad._fire_callbacks(state)
        assert len(fired) == 0

        # Second read: pressed
        buttons = [False] * 14
        buttons[0] = True
        pressed = RawState(
            axes=[0.0]*6, buttons=buttons, hats=[(0,0)],
            name="DualSense Wireless Controller"
        )
        gamepad._backend.poll.return_value = pressed
        state = gamepad.read()
        gamepad._fire_callbacks(state)
        assert len(fired) == 1

    def test_button_release_callback_fires(self, gamepad):
        released_events = []

        @gamepad.on_button_release("circle")
        def on_release():
            released_events.append(True)

        buttons_on = [False] * 14
        buttons_on[1] = True   # circle

        # Press
        gamepad._backend.poll.return_value = RawState(
            axes=[0.0]*6, buttons=buttons_on, hats=[(0,0)],
            name="DualSense Wireless Controller"
        )
        s = gamepad.read()
        gamepad._fire_callbacks(s)

        # Release
        gamepad._backend.poll.return_value = RawState(
            axes=[0.0]*6, buttons=[False]*14, hats=[(0,0)],
            name="DualSense Wireless Controller"
        )
        s = gamepad.read()
        gamepad._fire_callbacks(s)

        assert len(released_events) == 1

    def test_axis_callback_receives_values(self, gamepad):
        received = []

        @gamepad.on_axis("left_x", "left_y")
        def on_stick(x, y):
            received.append((x, y))

        raw = RawState(
            axes    = [0.8, -0.6, -1.0, 0.0, 0.0, -1.0],
            buttons = [False] * 14,
            hats    = [(0, 0)],
            name    = "DualSense Wireless Controller",
        )
        gamepad._backend.poll.return_value = raw
        state = gamepad.read()
        gamepad._fire_callbacks(state)

        assert len(received) == 1
        x, y = received[0]
        assert x > 0.5
        assert y > 0.5   # Inverted: raw -0.6 → +0.6 after inversion


class TestDisconnect:
    def test_disconnect_raises_when_reconnect_false(self, gamepad):
        gamepad._reconnect = False
        gamepad._backend.poll.side_effect = ControllerDisconnected("Gone")
        gamepad._backend.is_connected.return_value = False

        with pytest.raises(ControllerDisconnected):
            gamepad.read()
