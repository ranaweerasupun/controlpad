"""
Recording and playback example
===============================
Demonstrates the three main uses of controlpad's session system:
recording live input, replaying a session in real time, and using
recorded sessions as fast, hardware-free test fixtures.

Usage:
    python recording_playback.py record    # record a session to file
    python recording_playback.py replay    # replay last session in real time
    python recording_playback.py test      # demonstrate test fixture usage
"""

import sys
import time
from pathlib import Path

from controlpad import Gamepad
from controlpad.session import Session

SESSION_FILE = "my_session.json"


# ─────────────────────────────────────────────────────────────────────
# 1. Recording
# ─────────────────────────────────────────────────────────────────────

def record_session() -> None:
    """
    Connect to a real controller, record input, and save it to a file.
    Press the Options button (or Ctrl-C) to stop.
    """
    gp = Gamepad(deadzone=0.08)

    @gp.on_button_press("options")
    def stop():
        print("\nStopping recording...")
        gp.stop()

    gp.connect()
    print(f"Connected: {gp.profile.name}")
    print("Recording — press Options or Ctrl-C to stop.\n")

    gp.start_recording()
    gp.run()

    session = gp.stop_recording()
    session.save(SESSION_FILE)

    print(
        f"\nSaved '{SESSION_FILE}': {session.snapshot_count} snapshots "
        f"over {session.duration:.2f}s "
        f"({session.average_poll_rate:.1f} Hz avg)"
    )


# ─────────────────────────────────────────────────────────────────────
# 2. Real-time replay (no hardware needed)
# ─────────────────────────────────────────────────────────────────────

def replay_session() -> None:
    """
    Load the saved session and replay it at real-time speed.
    No controller hardware required — the same callbacks fire as during
    the original recording.
    """
    path = Path(SESSION_FILE)
    if not path.exists():
        print(f"No session found. Run: python recording_playback.py record")
        return

    session = Session.load(path)
    print(
        f"Replaying '{SESSION_FILE}': {session.snapshot_count} snapshots, "
        f"{session.duration:.2f}s\n"
    )

    # Note: no gp.connect() — playback requires no hardware.
    gp = Gamepad(profile=session.profile_name, deadzone=0.08)

    @gp.on_axis("left_x", "left_y")
    def on_left(x, y):
        if abs(x) > 0.05 or abs(y) > 0.05:
            print(f"  Left  →  x={x:+.2f}  y={y:+.2f}")

    @gp.on_axis("right_x", "right_y")
    def on_right(x, y):
        if abs(x) > 0.05 or abs(y) > 0.05:
            print(f"  Right →  x={x:+.2f}  y={y:+.2f}")

    @gp.on_button_press("cross")
    def on_cross():
        print("  ✕ Cross pressed")

    @gp.on_button_press("triangle")
    def on_triangle():
        print("  △ Triangle pressed")

    @gp.on_connect()
    def started(name):
        print(f"Playback started ({name})\n")

    @gp.on_disconnect()
    def finished():
        print("\nPlayback complete.")

    gp.playback(session, speed=1.0)


# ─────────────────────────────────────────────────────────────────────
# 3. Test fixture demonstration (speed=0, instantaneous)
# ─────────────────────────────────────────────────────────────────────

def demonstrate_test_usage() -> None:
    """
    Shows how a recorded session can serve as a hardware-free test fixture.

    The key feature: speed=0 replays all snapshots instantly. A 30-second
    recording runs in milliseconds, making it practical to include in a
    test suite that runs on every commit — on any machine, with no hardware.
    """
    path = Path(SESSION_FILE)
    if not path.exists():
        print(f"No session found. Run: python recording_playback.py record")
        return

    session = Session.load(path)
    print(
        f"Test session: {session.snapshot_count} snapshots, "
        f"{session.duration:.2f}s original duration\n"
    )

    # Simulate the system-under-test: a drone flight controller.
    # In a real test, this would be your actual application code.
    class MockDrone:
        def __init__(self):
            self.velocity_history:  list[tuple[float, float]] = []
            self.button_events:     list[str]                  = []

        def set_velocity(self, x: float, y: float) -> None:
            self.velocity_history.append((x, y))

        def land(self) -> None:
            self.button_events.append("land")

        def take_off(self) -> None:
            self.button_events.append("take_off")

    drone = MockDrone()

    gp = Gamepad(profile=session.profile_name, deadzone=0.08)

    @gp.on_axis("left_x", "left_y")
    def on_sticks(x, y):
        drone.set_velocity(x, y)

    @gp.on_axis("l2")
    def on_left_trigger(value):
        if value > 0.02:
            print(f"L2 trigger  → {value:.2f}")


    @gp.on_button_press("l1")
    def on_l1():
        print("L1 pressed")

    @gp.on_button_press("r1")
    def on_r1():
        print("R1 pressed")


    @gp.on_axis("r2")
    def on_r2(value):
        if value > 0.02:   # small threshold to ignore noise at rest
            print(f"R2 trigger → {value:.2f}")

    @gp.on_button_press("cross")
    def on_cross():
        drone.land()

    @gp.on_button_press("triangle")
    def on_triangle():
        drone.take_off()

    start = time.monotonic()
    gp.playback(session, speed=0)   # instantaneous — no real-time waiting
    elapsed = time.monotonic() - start

    print(f"Replay completed in {elapsed * 1000:.1f} ms  "
          f"(original: {session.duration * 1000:.0f} ms)")
    print(f"Velocity commands delivered: {len(drone.velocity_history)}")
    print(f"Button events recorded:      {drone.button_events}")
    print(
        f"\nSpeedup: {session.duration / elapsed:.0f}x faster than real time.\n"
        f"This is how fast your tests run when you use speed=0 with "
        f"recorded sessions as fixtures."
    )


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "help"

    commands = {
        "record": record_session,
        "replay": replay_session,
        "test":   demonstrate_test_usage,
    }

    if command in commands:
        commands[command]()
    else:
        print("Usage:")
        print("  python recording_playback.py record   — record a session")
        print("  python recording_playback.py replay   — replay at real-time speed")
        print("  python recording_playback.py test     — demonstrate test fixture usage")
