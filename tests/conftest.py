"""
Shared pytest fixtures.

The Gamepad class requires a real controller, so we mock the backend
to allow unit tests to run anywhere — no hardware needed.

The key technique throughout this file is patching 'controlpad.gamepad.get_backend'
at the point where Gamepad.__init__ calls it. This prevents any attempt to
import pygame (or evdev), so the full test suite runs on any machine — including
CI servers with no display and no game controller libraries installed.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

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
    backend.open.return_value         = "DualSense Wireless Controller"
    backend.poll.return_value         = raw_state_neutral
    backend.is_connected.return_value = True
    backend.count.return_value        = 1
    return backend


@pytest.fixture
def gamepad(mock_backend):
    """
    A Gamepad wired to the mock backend — no real controller required.

    Uses patch() so that Gamepad.__init__ never calls get_backend() for real,
    meaning pygame is never imported even if it isn't installed.
    """
    from controlpad.gamepad import Gamepad

    with patch("controlpad.gamepad.get_backend", return_value=mock_backend):
        gp = Gamepad(profile="dualsense")

    gp._profile          = DUALSENSE
    gp._connected        = True
    gp._controller_name  = "DualSense Wireless Controller"
    return gp


@pytest.fixture
def fresh_gamepad():
    """
    A Gamepad with a mock backend but NOT connected.

    Use this for tests that exercise functionality which does not require
    a live connection — most importantly, playback() which feeds recorded
    data through the pipeline without touching hardware at all.
    """
    from controlpad.gamepad import Gamepad

    mock_backend = MagicMock()
    mock_backend.is_connected.return_value = False

    with patch("controlpad.gamepad.get_backend", return_value=mock_backend):
        gp = Gamepad(profile="dualsense")

    return gp
