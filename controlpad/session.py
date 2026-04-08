"""
controlpad.session
~~~~~~~~~~~~~~~~~~
Data model for recording and replaying controller sessions.

A Session is an ordered sequence of Snapshots — timestamped raw hardware
states — plus the metadata needed to replay them faithfully. Sessions can
be saved as human-readable JSON and loaded back without any controller
hardware present, making them ideal as test fixtures.

The key design decision: sessions store *raw* hardware state (the values
from the hardware before profile mapping, deadzone, and filtering). This
means a recorded session can be replayed through a differently-configured
Gamepad, which lets you ask "how would my drone behave if I increase the
deadzone?" without needing a human to fly the same path twice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar


@dataclass(frozen=True)
class Snapshot:
    """
    A single timestamped sample of raw controller hardware state.

    Snapshots are immutable — each one is a permanent record of what the
    hardware reported at a specific moment in time. The ``t`` field is
    relative to the session start (t=0.0 is the first snapshot), so sessions
    are portable across machines with different system clocks.

    Raw state is stored (before profile mapping, deadzone, expo, or smoothing)
    so that replaying through a differently-configured Gamepad produces results
    that reflect the new settings rather than being locked to the original.

    Attributes:
        t: Seconds since the start of the recording session. Always >= 0.
        axes: Raw axis values as reported by the hardware, in [-1.0, +1.0].
        buttons: Raw button states. True = pressed.
        hats: D-pad/hat states as (x, y) tuples where each component is
            -1 (left/down), 0 (centre), or +1 (right/up).
    """

    t:       float
    axes:    list[float]
    buttons: list[bool]
    hats:    list[tuple[int, int]]


@dataclass
class Session:
    """
    A complete recording of controller input over a period of time.

    A Session captures everything needed to replay a controller session
    without hardware: the sequence of raw states, their timestamps, and
    the metadata about which controller and profile were in use.

    Sessions are saved as compact, human-readable JSON. The format is
    versioned so that future controlpad releases can evolve the file
    structure while still reading old session files.

    Attributes:
        controller_name: The OS/SDL name of the controller that was recorded.
        profile_name:    The controlpad profile active during recording.
        recorded_at:     ISO 8601 timestamp of when the recording started.
        duration:        Total length of the recording in seconds.
        snapshots:       Ordered list of raw state snapshots, earliest first.

    Example:
        Recording::

            gp = Gamepad()
            gp.connect()
            gp.start_recording()
            gp.run()                          # fly the drone manually
            session = gp.stop_recording()
            session.save("patrol_route.json")

        Replaying (no hardware needed)::

            session = Session.load("patrol_route.json")
            gp = Gamepad(profile="dualsense")

            @gp.on_axis("left_x", "left_y")
            def steer(x, y):
                drone.set_velocity(x, y)

            gp.playback(session)
    """

    # The format version is a class-level constant used during save/load.
    # If we ever need to change the JSON structure in an incompatible way,
    # we increment this and add migration logic to Session.load().
    FORMAT_VERSION: ClassVar[str] = "1"

    controller_name: str
    profile_name:    str
    recorded_at:     str          # ISO 8601
    duration:        float
    snapshots:       list[Snapshot] = field(default_factory=list)

    # ──────────────────────────────────────────────────────────────────
    # Computed properties
    # ──────────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        """The number of snapshots in this session."""
        return len(self.snapshots)

    @property
    def average_poll_rate(self) -> float:
        """
        The average polling frequency of this session in Hz.

        Returns 0.0 for sessions with fewer than two snapshots (a rate
        cannot be computed from a single point in time).
        """
        if len(self.snapshots) < 2 or self.duration <= 0.0:
            return 0.0
        return len(self.snapshots) / self.duration

    # ──────────────────────────────────────────────────────────────────
    # Serialisation
    # ──────────────────────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """
        Serialise this session to a JSON file.

        The file is human-readable and diff-friendly: each snapshot occupies
        one logical line in the ``snapshots`` array, which makes the file
        easy to inspect in a text editor and produces clean diffs in version
        control when sessions change between recordings.

        Args:
            path: File path to write. Created or overwritten if it exists.

        Raises:
            OSError: If the path cannot be written (permissions, disk full).
        """
        path = Path(path)

        data: dict[str, Any] = {
            "format_version":  self.FORMAT_VERSION,
            "controller_name": self.controller_name,
            "profile_name":    self.profile_name,
            "recorded_at":     self.recorded_at,
            # Round duration to 4 decimal places — sub-millisecond precision
            # is meaningless for a controller session.
            "duration":        round(self.duration, 4),
            "snapshot_count":  len(self.snapshots),
            "snapshots": [
                {
                    "t":       round(s.t, 4),
                    # 6 decimal places is sub-microvolt precision on an axis —
                    # far more than any gamepad ADC can actually resolve.
                    "axes":    [round(v, 6) for v in s.axes],
                    "buttons": list(s.buttons),
                    # JSON has no tuple type. We store hats as [x, y] lists
                    # and convert back to tuples in Session.load().
                    "hats":    [list(h) for h in s.hats],
                }
                for s in self.snapshots
            ],
        }

        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Session:
        """
        Load a session from a JSON file previously saved with :meth:`save`.

        Args:
            path: Path to the session JSON file.

        Returns:
            A fully reconstructed :class:`Session` with all snapshots loaded.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError: If the file is not a valid controlpad session.
        """
        path = Path(path)

        try:
            raw_text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"'{path}' is not valid JSON: {exc}"
            ) from exc

        # Version check. If we ship format version 2 in the future, we
        # would add an if/elif here to handle migration from v1 → v2
        # rather than silently reading an incompatible structure.
        version = data.get("format_version", "unknown")
        if version != cls.FORMAT_VERSION:
            raise ValueError(
                f"Unsupported session format version '{version}' in '{path}'. "
                f"This version of controlpad only supports format version "
                f"'{cls.FORMAT_VERSION}'. "
                f"Update controlpad to read this file."
            )

        try:
            snapshots = [
                Snapshot(
                    t       = float(s["t"]),
                    axes    = [float(v) for v in s["axes"]],
                    buttons = [bool(v) for v in s["buttons"]],
                    # Convert [x, y] lists back into (x, y) tuples to match
                    # the type that RawState uses for hats.
                    hats    = [tuple(h) for h in s["hats"]],
                )
                for s in data["snapshots"]
            ]

            return cls(
                controller_name = str(data["controller_name"]),
                profile_name    = str(data["profile_name"]),
                recorded_at     = str(data["recorded_at"]),
                duration        = float(data["duration"]),
                snapshots       = snapshots,
            )

        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"'{path}' has an unexpected structure and may be corrupted: {exc}"
            ) from exc

    # ──────────────────────────────────────────────────────────────────
    # Internal factory used by Gamepad.start_recording()
    # ──────────────────────────────────────────────────────────────────

    @classmethod
    def _new_recording(
        cls,
        controller_name: str,
        profile_name: str,
    ) -> Session:
        """
        Create an empty session ready to receive snapshots.

        This is intentionally private — users receive :class:`Session`
        objects via :meth:`Gamepad.stop_recording`, not by constructing
        them directly during a recording.
        """
        return cls(
            controller_name = controller_name,
            profile_name    = profile_name,
            recorded_at     = datetime.now(timezone.utc).isoformat(),
            duration        = 0.0,
            snapshots       = [],
        )
