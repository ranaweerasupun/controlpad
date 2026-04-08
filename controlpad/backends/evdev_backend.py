"""
controlpad.backends.evdev_backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
evdev-based backend for Linux — no display, no pygame required.

Ideal for headless Raspberry Pi deployments inside ROS nodes,
drone autopilots, or any service running without a desktop.

Requires: pip install evdev  (Linux only)
"""

from __future__ import annotations
from .base import BaseBackend, RawState
from ..exceptions import NoControllerFound, ControllerDisconnected, BackendNotAvailable

# evdev absolute axis codes for standard gamepad layout
_ABS_AXIS_CODES = [
    0x00,  # ABS_X       → left_x
    0x01,  # ABS_Y       → left_y
    0x02,  # ABS_Z       → lt / l2
    0x03,  # ABS_RX      → right_x
    0x04,  # ABS_RY      → right_y
    0x05,  # ABS_RZ      → rt / r2
    0x10,  # ABS_HAT0X   → dpad x
    0x11,  # ABS_HAT0Y   → dpad y
]

_BTN_GAMEPAD_BASE = 0x130   # BTN_SOUTH
_BTN_GAMEPAD_END  = 0x13F


class EvdevBackend(BaseBackend):
    """
    Controller backend using Linux evdev (no display required).

    The evdev backend reads from ``/dev/input/eventN`` directly via the
    ``evdev`` package. It does not require pygame or an X11 display,
    making it suitable for headless Raspberry Pi and Docker containers.

    Limitations:
    - Linux only.
    - Requires read permission on /dev/input/event* (add user to ``input`` group).
    - Hat/D-pad is synthesised from ABS_HAT0X / ABS_HAT0Y events.
    """

    def __init__(self) -> None:
        try:
            import evdev  # noqa: F401
        except ImportError as exc:
            raise BackendNotAvailable(
                "evdev is required for the evdev backend. "
                "Install it with: pip install evdev  (Linux only)"
            ) from exc

        self._evdev = None
        self._device = None
        self._gamecontrollers: list = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self, index: int = 0) -> str:
        import evdev

        self._evdev = evdev
        self._gamecontrollers = self._find_gamepads()

        if not self._gamecontrollers:
            raise NoControllerFound(
                "No gamepad found in /dev/input/. "
                "Check USB/Bluetooth connection and ensure user is in 'input' group."
            )

        if index >= len(self._gamecontrollers):
            raise NoControllerFound(
                f"Controller index {index} out of range "
                f"({len(self._gamecontrollers)} found)."
            )

        self._device = evdev.InputDevice(self._gamecontrollers[index])
        self._device.grab()  # Exclusive access
        return self._device.name

    def close(self) -> None:
        if self._device is not None:
            try:
                self._device.ungrab()
                self._device.close()
            except Exception:
                pass
            self._device = None

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def poll(self) -> RawState:
        if self._device is None:
            raise ControllerDisconnected("No device open.")

        try:
            # Read all pending events (non-blocking)
            for event in self._device.read_many():
                self._handle_event(event)
        except OSError as exc:
            raise ControllerDisconnected(f"Controller disconnected: {exc}") from exc

        return RawState(
            axes=list(self._axes),
            buttons=list(self._buttons),
            hats=[self._hat],
            name=self._device.name,
        )

    def is_connected(self) -> bool:
        if self._device is None:
            return False
        try:
            self._device.fd  # Will raise if device is gone
            return True
        except Exception:
            return False

    def count(self) -> int:
        return len(self._find_gamepads())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_gamepads(self) -> list[str]:
        """Return /dev/input paths for devices that look like gamepads."""
        import evdev
        gamepads = []
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                # Must have absolute axes and gamepad buttons
                if (
                    self._evdev.ecodes.EV_ABS in caps
                    and self._evdev.ecodes.EV_KEY in caps
                ):
                    keys = caps[self._evdev.ecodes.EV_KEY]
                    if any(_BTN_GAMEPAD_BASE <= k <= _BTN_GAMEPAD_END for k in keys):
                        gamepads.append(path)
                dev.close()
            except Exception:
                continue
        return gamepads

    def _handle_event(self, event) -> None:
        ec = self._evdev.ecodes
        if event.type == ec.EV_ABS:
            # Map ABS code → axis slot
            if event.code in _ABS_AXIS_CODES[:6]:
                idx = _ABS_AXIS_CODES.index(event.code)
                info = self._device.absinfo(event.code)
                self._axes[idx] = self._normalise(event.value, info.min, info.max)
            elif event.code == ec.ABS_HAT0X:
                self._hat = (event.value, self._hat[1])
            elif event.code == ec.ABS_HAT0Y:
                self._hat = (self._hat[0], -event.value)  # evdev Y is inverted vs pygame
        elif event.type == ec.EV_KEY:
            if _BTN_GAMEPAD_BASE <= event.code <= _BTN_GAMEPAD_END:
                idx = event.code - _BTN_GAMEPAD_BASE
                if idx < len(self._buttons):
                    self._buttons[idx] = bool(event.value)

    @staticmethod
    def _normalise(value: int, min_val: int, max_val: int) -> float:
        """Normalise an absolute axis value to [-1.0, +1.0]."""
        span = max_val - min_val
        if span == 0:
            return 0.0
        return 2.0 * (value - min_val) / span - 1.0

    # State storage (initialised lazily after open)
    _axes:    list[float]         = [0.0] * 8
    _buttons: list[bool]          = [False] * 16
    _hat:     tuple[int, int]     = (0, 0)
