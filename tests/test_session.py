"""
tests/test_session.py
~~~~~~~~~~~~~~~~~~~~~
Tests for the recording and playback system introduced in v0.2.0.

The tests are organised around four distinct areas:

  1. Snapshot — immutability and data integrity
  2. Session save/load — JSON serialisation roundtrip and error handling
  3. Recording — capturing live controller input into a Session
  4. Playback — replaying a Session through the callback pipeline

A recurring theme across this file is the 'speed=0' pattern for testing:
playback with speed=0 replays all snapshots instantaneously, which makes
tests that would otherwise take seconds complete in milliseconds, without
sacrificing any of the behavioural verification.
"""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

from controlpad import Gamepad
from controlpad.session import Session, Snapshot
from controlpad.backends.base import RawState
from controlpad.profiles import DUALSENSE


# ═══════════════════════════════════════════════════════════════════════
# Helpers — reusable session factories used across multiple test classes
# ═══════════════════════════════════════════════════════════════════════


def _gamepad(*args, **kwargs):
    """
    Construct a Gamepad with the pygame backend mocked out.
    Use this in any test that creates a Gamepad directly rather than
    using the 'gamepad' or 'fresh_gamepad' fixtures from conftest.
    """
    from controlpad.gamepad import Gamepad
    mock = MagicMock()
    mock.is_connected.return_value = False
    with patch("controlpad.gamepad.get_backend", return_value=mock):
        gp = Gamepad(*args, **kwargs)
    return gp


def _make_session(
    n: int = 5,
    axes: list[float] | None = None,
    buttons: list[bool] | None = None,
    hats: list[tuple[int, int]] | None = None,
) -> Session:
    """
    Create a simple synthetic Session for use in tests.

    All snapshots have identical content (same axes/buttons/hats),
    spaced 1/60th of a second apart to simulate a 60 Hz recording.
    """
    axes    = axes    or [0.5, 0.0, -1.0, 0.0, 0.0, -1.0]
    buttons = buttons or [False] * 14
    hats    = hats    or [(0, 0)]

    snapshots = [
        Snapshot(t=i / 60.0, axes=axes, buttons=buttons, hats=hats)
        for i in range(n)
    ]
    return Session(
        controller_name = "DualSense Wireless Controller",
        profile_name    = "dualsense",
        recorded_at     = "2026-01-01T00:00:00+00:00",
        duration        = n / 60.0,
        snapshots       = snapshots,
    )


# ═══════════════════════════════════════════════════════════════════════
# 1. Snapshot
# ═══════════════════════════════════════════════════════════════════════

class TestSnapshot:

    def test_snapshot_is_immutable(self):
        """
        Snapshots are frozen dataclasses — they represent a moment in time
        and must never be modified after creation. This test verifies that
        attempting to change any field raises an exception.
        """
        s = Snapshot(t=0.0, axes=[0.0]*6, buttons=[False]*14, hats=[(0, 0)])
        with pytest.raises(Exception):   # FrozenInstanceError
            s.t = 1.0

    def test_snapshot_equality(self):
        """Two snapshots with identical fields should compare as equal."""
        a = Snapshot(t=0.5, axes=[0.1]*6, buttons=[True, False]*7, hats=[(1, 0)])
        b = Snapshot(t=0.5, axes=[0.1]*6, buttons=[True, False]*7, hats=[(1, 0)])
        assert a == b

    def test_snapshot_inequality_on_time(self):
        a = Snapshot(t=0.0, axes=[0.0]*6, buttons=[False]*14, hats=[(0, 0)])
        b = Snapshot(t=0.1, axes=[0.0]*6, buttons=[False]*14, hats=[(0, 0)])
        assert a != b


# ═══════════════════════════════════════════════════════════════════════
# 2. Session save / load
# ═══════════════════════════════════════════════════════════════════════

class TestSessionSaveLoad:

    def test_roundtrip_preserves_controller_name(self, tmp_path):
        session = _make_session()
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.controller_name == session.controller_name

    def test_roundtrip_preserves_profile_name(self, tmp_path):
        session = _make_session()
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.profile_name == session.profile_name

    def test_roundtrip_preserves_snapshot_count(self, tmp_path):
        session = _make_session(n=10)
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.snapshot_count == 10

    def test_roundtrip_preserves_axis_values(self, tmp_path):
        axes = [0.123456, -0.654321, 0.0, 1.0, -1.0, 0.5]
        session = _make_session(axes=axes)
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.snapshots[0].axes == pytest.approx(axes, abs=1e-5)

    def test_roundtrip_preserves_button_states(self, tmp_path):
        buttons = [True, False, True] + [False] * 11
        session = _make_session(buttons=buttons)
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.snapshots[0].buttons == buttons

    def test_roundtrip_preserves_hat_values(self, tmp_path):
        session = _make_session(hats=[(1, -1)])
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.snapshots[0].hats[0] == (1, -1)

    def test_hats_are_tuples_after_load(self, tmp_path):
        """
        JSON has no tuple type — hats are serialised as [x, y] lists.
        Session.load() must convert them back to tuples so that the loaded
        snapshots have the same types as freshly-created ones.
        """
        session = _make_session(hats=[(1, 0), (0, -1)])
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        for hat in loaded.snapshots[0].hats:
            assert isinstance(hat, tuple), (
                f"Expected tuple after load, got {type(hat).__name__}. "
                "JSON deserialises lists, so Session.load() must convert them."
            )

    def test_roundtrip_preserves_duration(self, tmp_path):
        session = _make_session(n=60)   # 1 second at 60 Hz
        path = tmp_path / "session.json"
        session.save(path)
        loaded = Session.load(path)
        assert loaded.duration == pytest.approx(session.duration, abs=1e-3)

    def test_saved_file_is_valid_json(self, tmp_path):
        session = _make_session()
        path = tmp_path / "session.json"
        session.save(path)
        # If this doesn't raise, the file is valid JSON
        data = json.loads(path.read_text())
        assert "snapshots" in data

    def test_saved_file_contains_format_version(self, tmp_path):
        """
        Format versioning ensures future controlpad releases can read old
        session files. The version field must be present in every saved file.
        """
        session = _make_session()
        path = tmp_path / "session.json"
        session.save(path)
        data = json.loads(path.read_text())
        assert "format_version" in data
        assert data["format_version"] == "1"

    def test_load_rejects_unknown_format_version(self, tmp_path):
        """
        A session file from a future controlpad release (format version 2+)
        should be rejected with a clear error, not silently misread.
        """
        path = tmp_path / "future.json"
        path.write_text(json.dumps({
            "format_version": "99",
            "controller_name": "Test",
            "profile_name": "generic",
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "duration": 1.0,
            "snapshot_count": 0,
            "snapshots": [],
        }))
        with pytest.raises(ValueError, match="Unsupported session format version"):
            Session.load(path)

    def test_load_rejects_invalid_json(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("{ this is not valid json }")
        with pytest.raises(ValueError, match="not valid JSON"):
            Session.load(path)

    def test_load_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Session.load("/definitely/does/not/exist/session.json")

    def test_load_rejects_missing_required_fields(self, tmp_path):
        """
        A JSON file that is valid JSON but missing expected keys should
        produce a ValueError, not an unhelpful KeyError from deep in the code.
        """
        path = tmp_path / "incomplete.json"
        path.write_text(json.dumps({
            "format_version": "1",
            # missing controller_name, snapshots, etc.
        }))
        with pytest.raises(ValueError, match="unexpected structure"):
            Session.load(path)

    def test_session_computed_properties(self):
        session = _make_session(n=60)
        assert session.snapshot_count == 60
        # 60 snapshots over 60/60 = 1.0 seconds → average rate of 60 Hz
        assert session.average_poll_rate == pytest.approx(60.0, abs=1.0)

    def test_average_poll_rate_zero_for_empty_session(self):
        session = Session(
            controller_name="Test", profile_name="generic",
            recorded_at="2026-01-01T00:00:00+00:00",
            duration=0.0, snapshots=[]
        )
        assert session.average_poll_rate == 0.0


# ═══════════════════════════════════════════════════════════════════════
# 3. Recording
# ═══════════════════════════════════════════════════════════════════════

class TestRecording:
    """
    Tests for the start_recording / stop_recording lifecycle.

    All tests in this class use the 'gamepad' fixture from conftest.py,
    which provides a Gamepad wired to a mock backend (no hardware needed).
    """

    def test_start_recording_requires_connect(self):
        """
        start_recording() must fail immediately if the gamepad isn't connected,
        with a message that tells the user what to do.
        """
        gp = _gamepad()
        with pytest.raises(RuntimeError, match="Call gp.connect()"):
            gp.start_recording()

    def test_start_recording_twice_raises(self, gamepad):
        gamepad.start_recording()
        try:
            with pytest.raises(RuntimeError, match="Already recording"):
                gamepad.start_recording()
        finally:
            gamepad.stop_recording()

    def test_stop_recording_without_start_raises(self, gamepad):
        with pytest.raises(RuntimeError, match="Not currently recording"):
            gamepad.stop_recording()

    def test_recording_captures_one_snapshot_per_read(self, gamepad):
        gamepad.start_recording()
        for _ in range(7):
            gamepad.read()
        session = gamepad.stop_recording()
        assert session.snapshot_count == 7

    def test_recording_captures_axis_values(self, gamepad, mock_backend):
        mock_backend.poll.return_value = RawState(
            axes=[0.75, -0.25, -1.0, 0.0, 0.0, -1.0],
            buttons=[False] * 14,
            hats=[(0, 0)],
            name="DualSense Wireless Controller",
        )
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()

        assert session.snapshots[0].axes == pytest.approx(
            [0.75, -0.25, -1.0, 0.0, 0.0, -1.0]
        )

    def test_recording_captures_button_states(self, gamepad, mock_backend):
        buttons = [True] + [False] * 13   # cross pressed
        mock_backend.poll.return_value = RawState(
            axes=[0.0] * 6, buttons=buttons,
            hats=[(0, 0)], name="DualSense Wireless Controller",
        )
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()
        assert session.snapshots[0].buttons[0] is True

    def test_recording_captures_hat_values(self, gamepad, mock_backend):
        mock_backend.poll.return_value = RawState(
            axes=[0.0]*6, buttons=[False]*14,
            hats=[(1, 0)], name="DualSense Wireless Controller",
        )
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()
        assert session.snapshots[0].hats[0] == (1, 0)

    def test_recording_stores_raw_state_not_processed(self, gamepad, mock_backend):
        """
        Snapshots must store the raw hardware value, not the processed value.
        This matters because raw values outside the deadzone but near it will
        be rescaled by apply_deadzone(). The raw value must be stored so that
        replaying with different deadzone settings produces different results.
        """
        # A raw value of 0.03 is inside the default 0.05 deadzone.
        # After processing, left_x would be 0.0 (zeroed by deadzone).
        # But the snapshot must store the original 0.03.
        mock_backend.poll.return_value = RawState(
            axes=[0.03, 0.0, -1.0, 0.0, 0.0, -1.0],
            buttons=[False]*14, hats=[(0,0)],
            name="DualSense Wireless Controller",
        )
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()

        # The snapshot must have the raw 0.03, not the processed 0.0
        assert session.snapshots[0].axes[0] == pytest.approx(0.03, abs=1e-5)

    def test_snapshot_timestamps_are_monotonically_increasing(self, gamepad):
        gamepad.start_recording()
        for _ in range(5):
            gamepad.read()
            time.sleep(0.001)  # tiny delay so timestamps differ
        session = gamepad.stop_recording()

        times = [s.t for s in session.snapshots]
        for i in range(1, len(times)):
            assert times[i] > times[i - 1], (
                f"Snapshot timestamps should increase: t[{i}]={times[i]} "
                f"is not greater than t[{i-1}]={times[i-1]}"
            )

    def test_first_snapshot_time_is_near_zero(self, gamepad):
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()
        assert session.snapshots[0].t == pytest.approx(0.0, abs=0.05)

    def test_duration_is_positive_after_stop(self, gamepad):
        gamepad.start_recording()
        time.sleep(0.02)
        session = gamepad.stop_recording()
        assert session.duration > 0.0

    def test_session_has_correct_profile_name(self, gamepad):
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()
        # The gamepad fixture uses the DualSense profile
        assert session.profile_name == "dualsense"

    def test_session_has_correct_controller_name(self, gamepad):
        gamepad.start_recording()
        gamepad.read()
        session = gamepad.stop_recording()
        assert "dualSense" in session.controller_name.lower() or \
               "wireless" in session.controller_name.lower()

    def test_recording_does_not_affect_read_output(self, gamepad):
        """
        Recording is a side effect of read() — it must not change what
        read() returns. The ControllerState from a recording read should
        be identical to a non-recording read with the same raw input.
        """
        state_before = gamepad.read()

        gamepad.start_recording()
        state_during = gamepad.read()
        gamepad.stop_recording()

        state_after = gamepad.read()

        assert state_before.axes == state_during.axes
        assert state_during.axes == state_after.axes

    def test_can_record_multiple_sessions_sequentially(self, gamepad):
        """
        After stopping one recording, it should be possible to start another.
        The second session must be independent of the first.
        """
        gamepad.start_recording()
        for _ in range(3):
            gamepad.read()
        session1 = gamepad.stop_recording()

        gamepad.start_recording()
        for _ in range(5):
            gamepad.read()
        session2 = gamepad.stop_recording()

        assert session1.snapshot_count == 3
        assert session2.snapshot_count == 5


# ═══════════════════════════════════════════════════════════════════════
# 4. Playback
# ═══════════════════════════════════════════════════════════════════════

class TestPlayback:
    """
    Tests for the playback() method.

    All playback tests use speed=0 (instantaneous) to make the test suite
    fast. The timing behaviour of speed > 0 is tested separately.
    """

    def test_playback_fires_axis_callbacks(self):
        """
        The most fundamental playback contract: axis callbacks should fire
        once per snapshot, with values derived from the snapshot's raw state.
        """
        session = _make_session(n=5, axes=[0.8, 0.0, -1.0, 0.0, 0.0, -1.0])
        gp = _gamepad(profile="dualsense")
        received = []

        @gp.on_axis("left_x")
        def on_x(x):
            received.append(x)

        gp.playback(session, speed=0)

        assert len(received) == 5, (
            f"Expected 5 axis callbacks (one per snapshot), got {len(received)}."
        )
        # left_x raw was 0.8, well outside the 0.05 deadzone, so output > 0
        assert all(v > 0 for v in received)

    def test_playback_fires_button_press_callbacks_on_transition(self):
        """
        Button press callbacks fire on False→True transitions only, not on
        every frame where the button is held. This tests that the same edge
        detection logic used for live input works correctly during playback.
        """
        # 2 frames released, 2 frames pressed → exactly 1 press event
        snapshots = [
            Snapshot(t=0.00, axes=[0.0]*6, buttons=[False]*14, hats=[(0,0)]),
            Snapshot(t=0.01, axes=[0.0]*6, buttons=[False]*14, hats=[(0,0)]),
            Snapshot(t=0.02, axes=[0.0]*6,
                     buttons=[True] + [False]*13, hats=[(0,0)]),
            Snapshot(t=0.03, axes=[0.0]*6,
                     buttons=[True] + [False]*13, hats=[(0,0)]),
        ]
        session = Session(
            controller_name="DualSense Wireless Controller",
            profile_name="dualsense",
            recorded_at="2026-01-01T00:00:00+00:00",
            duration=0.03,
            snapshots=snapshots,
        )

        gp = _gamepad(profile="dualsense")
        presses = []

        @gp.on_button_press("cross")
        def on_cross():
            presses.append(True)

        gp.playback(session, speed=0)

        assert len(presses) == 1, (
            f"Expected exactly 1 press event for the False→True transition, "
            f"got {len(presses)}."
        )

    def test_playback_fires_button_release_callbacks(self):
        """Button release fires on True→False transitions."""
        snapshots = [
            Snapshot(t=0.00, axes=[0.0]*6,
                     buttons=[True] + [False]*13, hats=[(0,0)]),
            Snapshot(t=0.01, axes=[0.0]*6, buttons=[False]*14, hats=[(0,0)]),
        ]
        session = Session(
            controller_name="DualSense Wireless Controller",
            profile_name="dualsense",
            recorded_at="2026-01-01T00:00:00+00:00",
            duration=0.01,
            snapshots=snapshots,
        )

        gp = _gamepad(profile="dualsense")
        releases = []

        @gp.on_button_release("cross")
        def on_release():
            releases.append(True)

        gp.playback(session, speed=0)

        assert len(releases) == 1

    def test_playback_fires_connect_callback(self):
        """on_connect fires at the start of playback with the controller name."""
        session = _make_session(n=2)
        gp = _gamepad(profile="dualsense")
        connected_names = []

        @gp.on_connect()
        def on_connect(name):
            connected_names.append(name)

        gp.playback(session, speed=0)

        assert len(connected_names) == 1
        assert connected_names[0] == session.controller_name

    def test_playback_fires_disconnect_callback(self):
        """on_disconnect fires at the end of playback (last snapshot delivered)."""
        session = _make_session(n=2)
        gp = _gamepad(profile="dualsense")
        disconnect_count = [0]

        @gp.on_disconnect()
        def on_disconnect():
            disconnect_count[0] += 1

        gp.playback(session, speed=0)

        assert disconnect_count[0] == 1

    def test_playback_does_not_require_connect(self):
        """
        This is the defining property of playback for testing: it must work
        without any hardware connection. No connect() call should be needed.
        """
        session = _make_session(n=3)
        gp = _gamepad(profile="dualsense")
        # Deliberately no gp.connect() here

        received = []

        @gp.on_axis("left_x")
        def on_x(x):
            received.append(x)

        gp.playback(session, speed=0)   # must not raise

        assert len(received) == 3

    def test_playback_speed_zero_is_fast(self):
        """
        speed=0 must replay all snapshots with no sleeping. A session of
        100 snapshots that spans 1.67 seconds in real time should complete
        in well under 0.5 seconds with speed=0.
        """
        session = _make_session(n=100)   # 100 snapshots × 1/60 s ≈ 1.67 s real-time

        gp = _gamepad(profile="dualsense")
        start = time.monotonic()
        gp.playback(session, speed=0)
        elapsed = time.monotonic() - start

        assert elapsed < 0.5, (
            f"speed=0 should be near-instantaneous, but took {elapsed:.3f}s "
            f"for 100 snapshots (would be {session.duration:.2f}s at 1x speed)."
        )

    def test_playback_negative_speed_raises(self):
        session = _make_session()
        gp = _gamepad(profile="dualsense")
        with pytest.raises(ValueError, match="speed must be"):
            gp.playback(session, speed=-1.0)

    def test_playback_uses_session_profile_by_default(self):
        """
        If the Gamepad has no profile set (never connected), playback should
        load the profile from the session's profile_name field automatically.
        """
        session = _make_session()  # profile_name="dualsense"
        gp = _gamepad()              # no profile set, never connected
        # This must not raise UnknownProfile
        gp.playback(session, speed=0)
        assert gp.profile is not None
        assert gp.profile.name.lower() == "dualsense"

    def test_playback_profile_override(self):
        """
        Passing profile= to playback() should use the specified profile
        regardless of what the session stored.
        """
        session = _make_session()  # profile_name="dualsense"
        gp = _gamepad()

        # Override with xbox profile — this should not raise
        gp.playback(session, speed=0, profile="xbox")
        assert gp.profile.name.lower() == "xbox"

    def test_playback_resets_edge_detection_state(self):
        """
        If a button was pressed during live use (or a previous playback),
        _prev_buttons might show it as pressed. Playback must reset this
        state so the new playback starts from a clean baseline, preventing
        spurious release events on the first frame.
        """
        session = _make_session(n=3)  # all buttons unpressed
        gp = _gamepad(profile="dualsense")

        # Manually dirty the state as if cross was pressed before playback
        gp._profile = DUALSENSE
        gp._prev_buttons = {"cross": True}

        releases = []

        @gp.on_button_release("cross")
        def on_release():
            releases.append(True)

        gp.playback(session, speed=0)

        # After the reset, _prev_buttons is clean, so there should be
        # no release event even though we seeded it as pressed.
        assert len(releases) == 0, (
            "Playback should reset _prev_buttons before starting, preventing "
            "spurious release events from stale state."
        )

    def test_playback_callback_exception_does_not_stop_playback(self):
        """
        A broken callback must not crash the playback loop. The same
        error isolation that protects the live run loop must apply to playback.
        """
        session = _make_session(n=5)
        gp = _gamepad(profile="dualsense")

        @gp.on_axis("left_x")
        def broken_callback(x):
            raise RuntimeError("Intentional error in callback")

        # The playback must complete all 5 snapshots despite the broken callback.
        # If it raises, this test fails because the exception propagates out of playback().
        gp.playback(session, speed=0)

    def test_playback_async_returns_thread(self):
        session = _make_session(n=3)
        gp = _gamepad(profile="dualsense")

        thread = gp.playback_async(session, speed=0)
        assert isinstance(thread, threading.Thread)
        thread.join(timeout=2.0)
        assert not thread.is_alive(), "Playback thread should have completed."

    def test_playback_empty_session(self):
        """An empty session (no snapshots) should be a no-op — no error, no callbacks."""
        session = Session(
            controller_name="Test",
            profile_name="dualsense",
            recorded_at="2026-01-01T00:00:00+00:00",
            duration=0.0,
            snapshots=[],
        )
        gp = _gamepad(profile="dualsense")
        received = []

        @gp.on_axis("left_x")
        def on_x(x):
            received.append(x)

        gp.playback(session, speed=0)
        assert len(received) == 0


# ═══════════════════════════════════════════════════════════════════════
# 5. Full roundtrip: record → save → load → playback
# ═══════════════════════════════════════════════════════════════════════

class TestRoundtrip:
    """
    End-to-end tests that exercise the complete record → save → load → playback
    pipeline. These verify that data survives the full journey from live
    hardware input to a JSON file and back into callback-firing playback.
    """

    def test_full_roundtrip_fires_correct_number_of_callbacks(
        self, gamepad, mock_backend, tmp_path
    ):
        mock_backend.poll.return_value = RawState(
            axes=[0.8, 0.3, -1.0, 0.0, 0.0, -1.0],
            buttons=[False]*14, hats=[(0, 0)],
            name="DualSense Wireless Controller",
        )

        # Record
        gamepad.start_recording()
        for _ in range(8):
            gamepad.read()
        session = gamepad.stop_recording()

        # Save and reload
        path = tmp_path / "roundtrip.json"
        session.save(path)
        loaded = Session.load(path)

        # Playback on a fresh Gamepad (backend mocked — no hardware needed)
        replay_gp = _gamepad(profile="dualsense")
        received = []

        @replay_gp.on_axis("left_x")
        def on_x(x):
            received.append(x)

        replay_gp.playback(loaded, speed=0)

        assert len(received) == 8

    def test_full_roundtrip_preserves_axis_magnitude(
        self, gamepad, mock_backend, tmp_path
    ):
        """
        After the full roundtrip, the processed axis values delivered to
        callbacks should match what they would have been during live use
        with the same raw input and the same Gamepad settings.
        """
        mock_backend.poll.return_value = RawState(
            axes=[0.9, 0.0, -1.0, 0.0, 0.0, -1.0],
            buttons=[False]*14, hats=[(0, 0)],
            name="DualSense Wireless Controller",
        )

        # Record one snapshot with live hardware
        gamepad.start_recording()
        live_state = gamepad.read()
        session = gamepad.stop_recording()

        live_left_x = live_state.axis("left_x")

        # Save, reload, and replay
        path = tmp_path / "magnitude.json"
        session.save(path)
        loaded = Session.load(path)

        replay_gp = _gamepad(profile="dualsense", deadzone=0.05)  # same settings
        replayed = []

        @replay_gp.on_axis("left_x")
        def on_x(x):
            replayed.append(x)

        replay_gp.playback(loaded, speed=0)

        assert len(replayed) == 1
        assert replayed[0] == pytest.approx(live_left_x, abs=0.01), (
            "The axis value during playback should match what was produced "
            "during live recording, since both go through the same pipeline "
            "with the same settings."
        )
