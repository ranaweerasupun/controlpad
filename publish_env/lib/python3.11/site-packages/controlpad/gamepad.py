"""
controlpad.gamepad
~~~~~~~~~~~~~~~~~~
The main public API: the Gamepad class.

Typical usage (event-driven)::

    from controlpad import Gamepad

    gp = Gamepad()

    @gp.on_axis("left_x", "left_y")
    def on_left_stick(x, y):
        robot.set_velocity(x, y)

    @gp.on_button_press("cross")
    def on_cross():
        robot.jump()

    gp.run()

Typical usage (polling)::

    from controlpad import Gamepad

    gp = Gamepad()
    gp.connect()

    while True:
        state = gp.read()
        print(state.axis("left_x"), state.axis("left_y"))
"""

from __future__ import annotations

import threading
import time
import logging
from typing import Callable

from .backends import get_backend, BaseBackend, RawState
from .profiles import ControllerProfile, detect_profile, get_profile, build_generic_profile
from .filters import apply_deadzone_2d, apply_deadzone, apply_expo, ExponentialSmoother
from .exceptions import ControllerDisconnected, NoControllerFound, UnknownProfile
from .session import Session, Snapshot

logger = logging.getLogger(__name__)

# Pairs of axes that form 2D sticks for radial deadzone calculation
_STICK_PAIRS: dict[str, tuple[str, str]] = {
    "left":  ("left_x", "left_y"),
    "right": ("right_x", "right_y"),
}


class ControllerState:
    """
    A processed snapshot of controller state.

    Returned by :meth:`Gamepad.read`. Values are already normalised,
    inverted, deadzoned, and smoothed according to Gamepad configuration.
    """

    def __init__(
        self,
        axes:    dict[str, float],
        buttons: dict[str, bool],
        dpad:    tuple[int, int],
        connected: bool,
    ) -> None:
        self._axes    = axes
        self._buttons = buttons
        self._dpad    = dpad
        self.connected = connected

    def axis(self, name: str, default: float = 0.0) -> float:
        """Return the named axis value, or *default* if unknown."""
        return self._axes.get(name, default)

    def button(self, name: str) -> bool:
        """Return True if the named button is currently pressed."""
        return self._buttons.get(name, False)

    @property
    def dpad(self) -> tuple[int, int]:
        """D-pad state as (x, y) where x/y are -1, 0, or +1."""
        return self._dpad

    @property
    def axes(self) -> dict[str, float]:
        """All axis values as a dict."""
        return dict(self._axes)

    @property
    def buttons(self) -> dict[str, bool]:
        """All button states as a dict."""
        return dict(self._buttons)

    def __repr__(self) -> str:
        pressed = [k for k, v in self._buttons.items() if v]
        active = {k: f"{v:+.2f}" for k, v in self._axes.items() if abs(v) > 0.01}
        return f"<ControllerState axes={active} buttons={pressed} dpad={self._dpad}>"


class Gamepad:
    """
    A high-level interface to a game controller.

    Args:
        profile:    Controller profile. Pass a profile name string (e.g.
                    ``"dualsense"``), a :class:`ControllerProfile` instance,
                    or ``None`` to auto-detect.
        index:      Which controller to open if multiple are connected (0-based).
        deadzone:   Stick deadzone radius [0.0, 1.0). Default 0.05.
        expo:       Exponential curve strength [0.0, 1.0). Default 0.0 (linear).
        smoothing:  EMA smoothing factor (0, 1]. Lower = smoother. Default 1.0 (off).
        backend:    Backend name: ``"auto"``, ``"pygame"``, or ``"evdev"``.
        headless:   If True, force SDL into dummy video mode (no display needed).
        reconnect:  If True, automatically reconnect when controller is lost.
        poll_rate:  Polling frequency in Hz when using :meth:`run`. Default 60.

    Example::

        gp = Gamepad(profile="dualsense", deadzone=0.08, expo=0.2)
    """

    def __init__(
        self,
        profile:   str | ControllerProfile | None = None,
        index:     int   = 0,
        deadzone:  float = 0.05,
        expo:      float = 0.0,
        smoothing: float = 1.0,
        backend:   str   = "auto",
        headless:  bool  = False,
        reconnect: bool  = True,
        poll_rate: int   = 60,
    ) -> None:
        self._index     = index
        self._deadzone  = deadzone
        self._expo      = expo
        self._reconnect = reconnect
        self._poll_rate = poll_rate
        self._profile_arg = profile

        if headless:
            import os
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

        self._backend: BaseBackend = get_backend(backend)
        self._profile: ControllerProfile | None = None
        self._smoothers: dict[str, ExponentialSmoother] = {}
        self._smoothing_alpha = smoothing

        # Event callbacks
        self._axis_callbacks:         list[tuple[tuple[str, ...], Callable]] = []
        self._button_press_callbacks:   dict[str, list[Callable]] = {}
        self._button_release_callbacks: dict[str, list[Callable]] = {}
        self._connect_callbacks:    list[Callable] = []
        self._disconnect_callbacks: list[Callable] = []

        # State tracking for edge detection
        self._prev_buttons: dict[str, bool] = {}

        self._connected = False
        self._running   = False   # Initialised here so stop() is safe before run()
        self._lock = threading.Lock()

        # The name reported by the OS/driver after connect() succeeds.
        # Stored so start_recording() can embed it in the Session metadata
        # without reaching into backend internals.
        self._controller_name: str = ""

        # Recording state — all False/None until start_recording() is called.
        self._recording:      bool            = False
        self._record_start:   float | None    = None
        self._record_session: Session | None  = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> str:
        """
        Open the controller.

        Returns:
            The name string reported by the OS/driver.

        Raises:
            NoControllerFound: If no controller is available.
        """
        name = self._backend.open(self._index)
        self._resolve_profile(name)
        self._connected = True
        self._controller_name = name   # stored for recording metadata
        logger.info("Connected: %s  (profile: %s)", name, self._profile.name)
        for cb in self._connect_callbacks:
            cb(name)
        return name

    def disconnect(self) -> None:
        """Close the controller and release resources."""
        self._backend.close()
        self._connected = False

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """
        Begin capturing controller input as a recording session.

        Recording captures the raw hardware state on every call to
        :meth:`read` — at the same rate as your ``poll_rate`` setting
        (default 60 Hz). The raw state (before profile mapping, deadzone,
        and filtering) is stored so that sessions can be replayed with
        different filter settings later.

        Call :meth:`stop_recording` to end the session and retrieve the
        :class:`~controlpad.session.Session` object.

        Raises:
            RuntimeError: If called before :meth:`connect`, or if a recording
                is already in progress.

        Example::

            gp.connect()
            gp.start_recording()
            gp.run()                          # use controller normally
            session = gp.stop_recording()
            session.save("my_flight.json")
        """
        if not self._connected:
            raise RuntimeError(
                "Cannot start recording on a disconnected gamepad. "
                "Call gp.connect() first."
            )
        if self._recording:
            raise RuntimeError(
                "Already recording. Call gp.stop_recording() to end the "
                "current session before starting a new one."
            )

        profile_name = self._profile.name.lower() if self._profile else "generic"

        self._record_session = Session._new_recording(
            controller_name = self._controller_name,
            profile_name    = profile_name,
        )
        self._record_start = time.monotonic()
        self._recording    = True
        logger.info("Recording started (profile: %s).", profile_name)

    def stop_recording(self) -> Session:
        """
        Stop the current recording and return the captured session.

        The returned :class:`~controlpad.session.Session` object contains
        all snapshots captured since :meth:`start_recording` was called,
        along with the duration and metadata. It can be saved immediately
        with :meth:`~controlpad.session.Session.save` or used directly
        with :meth:`playback`.

        Returns:
            The completed recording session.

        Raises:
            RuntimeError: If not currently recording.

        Example::

            session = gp.stop_recording()
            print(f"Captured {session.snapshot_count} snapshots")
            session.save("flight.json")
        """
        if not self._recording:
            raise RuntimeError(
                "Not currently recording. Call gp.start_recording() first."
            )

        duration = time.monotonic() - self._record_start

        self._recording    = False
        session            = self._record_session
        session.duration   = duration

        # Clear recording state — the session now belongs to the caller.
        self._record_session = None
        self._record_start   = None

        logger.info(
            "Recording stopped: %d snapshots over %.2fs (%.1f Hz avg).",
            session.snapshot_count,
            session.duration,
            session.average_poll_rate,
        )
        return session

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def playback(
        self,
        session: Session,
        *,
        speed:   float                            = 1.0,
        profile: str | ControllerProfile | None  = None,
    ) -> None:
        """
        Replay a recorded session, firing all registered callbacks as if a
        human were holding the controller.

        No hardware connection is required. Each snapshot from the session
        is fed through the complete processing pipeline — profile mapping,
        deadzone, expo curve, and smoothing — and the results are delivered
        to all registered callbacks exactly as :meth:`run` would for live input.

        This is particularly powerful for testing: register your callbacks on
        a :class:`Gamepad`, load a recorded session, call ``playback(session,
        speed=0)``, and your entire callback logic is exercised without any
        hardware present and without waiting for real-world time to pass.

        The connect and disconnect lifecycle callbacks also fire: ``on_connect``
        fires at the start of playback (with the session's controller name),
        and ``on_disconnect`` fires when the last snapshot has been delivered.

        Args:
            session: The recorded session to replay.
            speed:   Playback speed multiplier. ``1.0`` is real-time. ``2.0``
                is double speed (half the elapsed time). ``0`` replays all
                snapshots instantly with no sleeping — ideal for tests.
                Must be >= 0.
            profile: Override the profile to use during playback. If ``None``
                (default), the profile name stored in the session is used.
                Pass a string name or :class:`ControllerProfile` instance to
                use a different profile.

        Raises:
            ValueError: If *speed* is negative.
            ValueError: If the session's profile is not registered and no
                *profile* override is provided.

        Example — real-time replay::

            session = Session.load("patrol_route.json")
            gp = Gamepad(profile="dualsense")

            @gp.on_axis("left_x", "left_y")
            def steer(x, y): drone.set_velocity(x, y)

            gp.playback(session)

        Example — instantaneous replay for tests::

            gp = Gamepad(profile="dualsense")
            # ... register callbacks ...
            gp.playback(session, speed=0)
        """
        if speed < 0:
            raise ValueError(
                f"speed must be >= 0 (use 0 for instantaneous), got {speed!r}"
            )

        # ── Resolve the profile for this playback ────────────────────────
        # Priority: explicit override → already set on this Gamepad →
        # session's stored profile name → generic fallback.
        if profile is not None:
            if isinstance(profile, str):
                self._profile = get_profile(profile)
            else:
                self._profile = profile

        elif self._profile is None:
            try:
                self._profile = get_profile(session.profile_name)
            except UnknownProfile:
                if session.snapshots:
                    s = session.snapshots[0]
                    self._profile = build_generic_profile(
                        len(s.axes), len(s.buttons)
                    )
                    logger.warning(
                        "Profile '%s' not registered; using generic fallback "
                        "for playback.", session.profile_name
                    )
                else:
                    raise ValueError(
                        f"Cannot determine profile for playback: "
                        f"session uses '{session.profile_name}' which is not "
                        f"registered. Pass profile= to playback() to specify one."
                    )

        # ── Reset state for a clean playback start ───────────────────────
        # Clear edge-detection state so we don't carry over stale button
        # states from a previous session or from live hardware use.
        self._prev_buttons = {}

        # Reset smoothers so playback begins with fresh filter state rather
        # than carrying forward momentum from a previous recording.
        self._smoothers = {}

        # ── Lifecycle: signal that playback is starting ───────────────────
        for cb in self._connect_callbacks:
            try:
                cb(session.controller_name)
            except Exception as exc:
                logger.error("Error in on_connect callback during playback: %s", exc)

        # ── Main playback loop ────────────────────────────────────────────
        playback_start = time.monotonic()

        for snapshot in session.snapshots:
            # Timing: sleep until it is time to deliver this snapshot.
            # speed=0 means instantaneous — we skip all sleep calls,
            # which is what makes test suites run fast.
            if speed > 0:
                target_elapsed = snapshot.t / speed
                actual_elapsed = time.monotonic() - playback_start
                remaining      = target_elapsed - actual_elapsed
                if remaining > 0.0:
                    time.sleep(remaining)

            # Feed the snapshot through the full processing pipeline,
            # exactly as a RawState from real hardware would be processed.
            raw = RawState(
                axes    = snapshot.axes,
                buttons = snapshot.buttons,
                hats    = snapshot.hats,
                name    = session.controller_name,
            )
            state = self._process(raw)
            self._fire_callbacks(state)

        # ── Lifecycle: signal that playback is complete ───────────────────
        for cb in self._disconnect_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Error in on_disconnect callback during playback: %s", exc)

        logger.info(
            "Playback complete: %d snapshots over %.2fs.",
            session.snapshot_count,
            session.duration,
        )

    def playback_async(
        self,
        session: Session,
        *,
        speed:   float                           = 1.0,
        profile: str | ControllerProfile | None = None,
    ) -> threading.Thread:
        """
        Start playback in a background daemon thread.

        Returns immediately. The returned thread can be joined to wait for
        completion, or ignored if fire-and-forget behaviour is desired.

        Args:
            session: The recorded session to replay.
            speed:   Playback speed multiplier (see :meth:`playback`).
            profile: Optional profile override (see :meth:`playback`).

        Returns:
            The :class:`threading.Thread` running the playback.

        Example::

            thread = gp.playback_async(session, speed=2.0)
            do_other_work()
            thread.join()           # wait for playback to finish
        """
        thread = threading.Thread(
            target  = self.playback,
            kwargs  = {"session": session, "speed": speed, "profile": profile},
            daemon  = True,
            name    = "controlpad-playback",
        )
        thread.start()
        return thread


    # ------------------------------------------------------------------
    # Polling API
    # ------------------------------------------------------------------

    def read(self) -> ControllerState:
        """
        Poll the controller and return a processed :class:`ControllerState`.

        Call this in your own loop for manual polling::

            gp.connect()
            while True:
                state = gp.read()
                send_to_drone(state.axis("left_x"), state.axis("left_y"))
                time.sleep(1/60)

        Raises:
            ControllerDisconnected: If the controller has been unplugged
                                    and *reconnect* is False.
        """
        try:
            raw = self._backend.poll()
        except ControllerDisconnected:
            self._connected = False
            for cb in self._disconnect_callbacks:
                cb()
            if self._reconnect:
                logger.warning("Controller disconnected. Waiting to reconnect...")
                self._wait_for_reconnect()
                raw = self._backend.poll()
            else:
                raise

        # Capture a snapshot if a recording session is active.
        # We record raw state (before the processing pipeline) so that
        # playback can be replayed with different filter settings later.
        if self._recording and self._record_session is not None:
            t = time.monotonic() - self._record_start
            self._record_session.snapshots.append(
                Snapshot(
                    t       = t,
                    axes    = list(raw.axes),
                    buttons = list(raw.buttons),
                    hats    = [tuple(h) for h in raw.hats],
                )
            )

        return self._process(raw)

    # ------------------------------------------------------------------
    # Event-driven API
    # ------------------------------------------------------------------

    def on_axis(self, *axis_names: str, threshold: float = 0.01):
        """
        Decorator: call *func* whenever any of the named axes change.

        The callback receives one argument per axis name, in order::

            @gp.on_axis("left_x", "left_y")
            def on_left_stick(x, y):
                ...

            @gp.on_axis("l2")
            def on_throttle(value):
                ...
        """
        def decorator(func: Callable) -> Callable:
            self._axis_callbacks.append((axis_names, func))
            return func
        return decorator

    def on_button_press(self, *button_names: str):
        """
        Decorator: call *func* once when any of the named buttons are pressed.

        The callback receives no arguments::

            @gp.on_button_press("cross")
            def fire():
                weapon.shoot()
        """
        def decorator(func: Callable) -> Callable:
            for name in button_names:
                self._button_press_callbacks.setdefault(name, []).append(func)
            return func
        return decorator

    def on_button_release(self, *button_names: str):
        """
        Decorator: call *func* once when any of the named buttons are released.
        """
        def decorator(func: Callable) -> Callable:
            for name in button_names:
                self._button_release_callbacks.setdefault(name, []).append(func)
            return func
        return decorator

    def on_connect(self):
        """Decorator: call *func*(controller_name) when a controller connects."""
        def decorator(func: Callable) -> Callable:
            self._connect_callbacks.append(func)
            return func
        return decorator

    def on_disconnect(self):
        """Decorator: call *func*() when the controller disconnects."""
        def decorator(func: Callable) -> Callable:
            self._disconnect_callbacks.append(func)
            return func
        return decorator

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def run(self, auto_connect: bool = True) -> None:
        """
        Start the blocking event loop.

        Connects (if not already connected), then polls at *poll_rate* Hz,
        firing registered callbacks on every tick.

        Stop by raising KeyboardInterrupt (Ctrl-C) or calling
        :meth:`stop` from another thread.

        Args:
            auto_connect: If True (default), call :meth:`connect` automatically.
        """
        if auto_connect and not self._connected:
            self.connect()

        self._running = True
        interval = 1.0 / self._poll_rate

        try:
            while self._running:
                t0 = time.monotonic()

                state = self.read()
                self._fire_callbacks(state)

                elapsed = time.monotonic() - t0
                sleep_for = interval - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()

    def run_async(self, auto_connect: bool = True) -> threading.Thread:
        """
        Start the event loop in a background daemon thread.

        Returns:
            The :class:`threading.Thread` running the loop.
        """
        thread = threading.Thread(
            target=self.run,
            kwargs={"auto_connect": auto_connect},
            daemon=True,
            name="controlpad-loop",
        )
        thread.start()
        return thread

    def stop(self) -> None:
        """Signal the run loop to stop cleanly."""
        self._running = False

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    @property
    def profile(self) -> ControllerProfile | None:
        """The active controller profile."""
        return self._profile

    @property
    def connected(self) -> bool:
        """True if the controller is currently open and responding."""
        return self._connected and self._backend.is_connected()

    def set_deadzone(self, value: float) -> None:
        """Update deadzone at runtime. Range [0.0, 1.0)."""
        self._deadzone = value

    def set_expo(self, value: float) -> None:
        """Update expo curve at runtime. Range [0.0, 1.0)."""
        self._expo = value

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_profile(self, sdl_name: str) -> None:
        if self._profile_arg is None:
            self._profile = detect_profile(sdl_name)
            if self._profile is None:
                raw = self._backend.poll()
                self._profile = build_generic_profile(len(raw.axes), len(raw.buttons))
                logger.warning(
                    "Unknown controller '%s'. Using generic profile.", sdl_name
                )
            else:
                logger.info("Auto-detected profile: %s", self._profile.name)
        elif isinstance(self._profile_arg, str):
            self._profile = get_profile(self._profile_arg)
        else:
            self._profile = self._profile_arg

    def _process(self, raw: RawState) -> ControllerState:
        """Transform a RawState into a ControllerState using the active profile."""
        profile = self._profile
        axes: dict[str, float] = {}

        # Process stick pairs with radial deadzone
        processed_axis_indices: set[str] = set()

        for stick_name, (ax_name, ay_name) in _STICK_PAIRS.items():
            xi = profile.get_axis_index(ax_name)
            yi = profile.get_axis_index(ay_name)
            if xi is None or yi is None:
                continue
            if xi >= len(raw.axes) or yi >= len(raw.axes):
                continue

            x = raw.axes[xi]
            y = raw.axes[yi]

            # Invert Y so up = +1
            if ax_name in profile.invert_axes:
                x = -x
            if ay_name in profile.invert_axes:
                y = -y

            x, y = apply_deadzone_2d(x, y, self._deadzone)
            x = apply_expo(x, self._expo)
            y = apply_expo(y, self._expo)

            axes[ax_name] = self._smooth(ax_name, x)
            axes[ay_name] = self._smooth(ay_name, y)
            processed_axis_indices.add(ax_name)
            processed_axis_indices.add(ay_name)

        # Process remaining axes (triggers, any extras)
        for name, idx in profile.axis_map.items():
            if name in processed_axis_indices:
                continue
            if idx >= len(raw.axes):
                continue

            val = raw.axes[idx]

            if name in profile.invert_axes:
                val = -val

            # Normalise triggers from [-1, +1] → [0, +1]
            if name in profile.trigger_axes:
                val = (val + 1.0) / 2.0
            else:
                val = apply_deadzone(val, self._deadzone)
                val = apply_expo(val, self._expo)

            axes[name] = self._smooth(name, val)

        # Buttons
        buttons: dict[str, bool] = {}
        for name, idx in profile.button_map.items():
            if idx < len(raw.buttons):
                buttons[name] = raw.buttons[idx]

        # D-pad
        dpad: tuple[int, int] = (0, 0)
        hat_idx = profile.hat_map.get("dpad", 0)
        if hat_idx < len(raw.hats):
            dpad = raw.hats[hat_idx]

        return ControllerState(
            axes=axes,
            buttons=buttons,
            dpad=dpad,
            connected=True,
        )

    def _smooth(self, name: str, value: float) -> float:
        if self._smoothing_alpha >= 1.0:
            return value
        if name not in self._smoothers:
            self._smoothers[name] = ExponentialSmoother(self._smoothing_alpha)
        return self._smoothers[name].update(value)

    def _fire_callbacks(self, state: ControllerState) -> None:
        # Axis callbacks
        for axis_names, func in self._axis_callbacks:
            values = tuple(state.axis(n) for n in axis_names)
            try:
                func(*values)
            except Exception as exc:
                logger.error("Error in axis callback %s: %s", func.__name__, exc)

        # Button edge detection
        for name, pressed in state.buttons.items():
            was_pressed = self._prev_buttons.get(name, False)

            if pressed and not was_pressed:
                for cb in self._button_press_callbacks.get(name, []):
                    try:
                        cb()
                    except Exception as exc:
                        logger.error("Error in button_press callback: %s", exc)

            elif not pressed and was_pressed:
                for cb in self._button_release_callbacks.get(name, []):
                    try:
                        cb()
                    except Exception as exc:
                        logger.error("Error in button_release callback: %s", exc)

        self._prev_buttons = dict(state.buttons)

    def _wait_for_reconnect(self, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self._backend.close()
                name = self._backend.open(self._index)
                self._connected = True
                logger.info("Reconnected: %s", name)
                for cb in self._connect_callbacks:
                    cb(name)
                return
            except NoControllerFound:
                time.sleep(1.0)
        raise ControllerDisconnected(
            f"Could not reconnect within {timeout:.0f} seconds."
        )
