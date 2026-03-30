"""
Shared pytest fixtures.

The Gamepad class requires a real controller, so we mock the backend
to allow unit tests to run anywhere — no hardware needed.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock

from controlpad.backends.base import RawState
from controlpad.profiles import DUALSENSE


@pytest.fixture
def raw_state_neutral() -> RawState:
    """A RawState with all axes at zero and all buttons unpressed."""
    return RawState(
        axes    = [0.0] * 6,
        buttons = [False] * 14,
        hats    = [(0, 0)],
        name    = "DualSense Wireless Controller",
    )


@pytest.fixture
def mock_backend(raw_state_neutral):
    """A fake backend that returns a neutral state and never raises."""
    backend = MagicMock()
    backend.open.return_value   = "DualSense Wireless Controller"
    backend.poll.return_value   = raw_state_neutral
    backend.is_connected.return_value = True
    backend.count.return_value  = 1
    return backend


@pytest.fixture
def gamepad(mock_backend):
    """A Gamepad wired to the mock backend — no real controller required."""
    from controlpad.gamepad import Gamepad

    gp = Gamepad(profile="dualsense")
    gp._backend = mock_backend
    gp._profile = DUALSENSE
    gp._connected = True
    return gp
