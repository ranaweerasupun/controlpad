"""
controlpad.backends
~~~~~~~~~~~~~~~~~~~
Backend selection and auto-detection.
"""

from __future__ import annotations
import sys
from .base import BaseBackend, RawState
from .pygame_backend import PygameBackend

__all__ = ["BaseBackend", "RawState", "PygameBackend", "get_backend"]


def get_backend(name: str = "auto") -> BaseBackend:
    """
    Instantiate a backend by name.

    Args:
        name: ``"auto"``, ``"pygame"``, or ``"evdev"``.
              ``"auto"`` prefers evdev on Linux when pygame is unavailable
              or when no display is found, otherwise uses pygame.

    Returns:
        An uninitialised :class:`BaseBackend` instance.
    """
    import os

    if name == "pygame":
        return PygameBackend()

    if name == "evdev":
        from .evdev_backend import EvdevBackend
        return EvdevBackend()

    # auto: use evdev on Linux headless, pygame everywhere else
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        try:
            from .evdev_backend import EvdevBackend
            return EvdevBackend()
        except Exception:
            pass  # Fall through to pygame

    return PygameBackend()
