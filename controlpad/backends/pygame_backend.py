"""
controlpad.backends.pygame_backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
pygame-based backend. Works on Linux (with display or headless via SDL_VIDEODRIVER=dummy),
macOS, and Windows.
"""

from __future__ import annotations
import os
from .base import BaseBackend, RawState
from ..exceptions import NoControllerFound, ControllerDisconnected, BackendNotAvailable


class PygameBackend(BaseBackend):
    """
    Controller backend built on top of pygame's joystick module.

    On headless Linux systems (Raspberry Pi without a display), set the
    environment variable before importing controlpad::

        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        import controlpad

    Or pass ``headless=True`` to :class:`Gamepad`.
    """

    def __init__(self) -> None:
        try:
            import pygame  # noqa: F401
        except ImportError as exc:
            raise BackendNotAvailable(
                "pygame is required for the pygame backend. "
                "Install it with: pip install pygame"
            ) from exc

        self._pygame = None
        self._joystick = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self, index: int = 0) -> str:
        import pygame

        # Allow headless operation (no display required)
        if not os.environ.get("DISPLAY") and os.name != "nt":
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

        if not pygame.get_init():
            pygame.init()

        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise NoControllerFound(
                "No controller detected. "
                "Check your USB/Bluetooth connection and try again."
            )

        self._pygame = pygame
        self._joystick = pygame.joystick.Joystick(index)
        self._joystick.init()
        return self._joystick.get_name()

    def close(self) -> None:
        if self._joystick is not None:
            try:
                self._joystick.quit()
            except Exception:
                pass
            self._joystick = None

        if self._pygame is not None:
            try:
                self._pygame.joystick.quit()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def poll(self) -> RawState:
        if self._joystick is None or not self.is_connected():
            raise ControllerDisconnected("Controller disconnected.")

        # Pump the event queue so pygame updates its internal state.
        # We discard the events — callers use the polling API, not events.
        self._pygame.event.pump()

        axes = [
            self._joystick.get_axis(i)
            for i in range(self._joystick.get_numaxes())
        ]
        buttons = [
            bool(self._joystick.get_button(i))
            for i in range(self._joystick.get_numbuttons())
        ]
        hats = [
            self._joystick.get_hat(i)
            for i in range(self._joystick.get_numhats())
        ]

        return RawState(
            axes=axes,
            buttons=buttons,
            hats=hats,
            name=self._joystick.get_name(),
        )

    def is_connected(self) -> bool:
        if self._joystick is None:
            return False
        try:
            # Joystick.get_init() returns False after it's been removed
            return self._joystick.get_init()
        except Exception:
            return False

    def count(self) -> int:
        if self._pygame is None:
            import pygame
            pygame.joystick.init()
            return pygame.joystick.get_count()
        return self._pygame.joystick.get_count()
