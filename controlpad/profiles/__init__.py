"""
controlpad.profiles
~~~~~~~~~~~~~~~~~~~
Built-in controller profiles and profile registry.
"""

from __future__ import annotations
from .base import ControllerProfile
from .dualsense import DUALSENSE
from .xbox import XBOX
from .generic import build_generic_profile
from ..exceptions import UnknownProfile

__all__ = [
    "ControllerProfile",
    "DUALSENSE",
    "XBOX",
    "build_generic_profile",
    "get_profile",
    "register_profile",
    "list_profiles",
]

# Built-in registry: name (lowercase) → profile
_REGISTRY: dict[str, ControllerProfile] = {
    "dualsense": DUALSENSE,
    "xbox":      XBOX,
}

# SDL controller name substrings → profile (order matters: most specific first)
_SDL_HINTS: list[tuple[str, ControllerProfile]] = [
    ("dualsense",    DUALSENSE),
    ("dualshock",    DUALSENSE),
    ("wireless controller", DUALSENSE),
    ("xbox",         XBOX),
    ("x-box",        XBOX),
    ("xinput",       XBOX),
]


def get_profile(name: str) -> ControllerProfile:
    """
    Retrieve a profile by name (case-insensitive).

    Args:
        name: Profile name, e.g. "dualsense", "xbox".

    Raises:
        UnknownProfile: If name is not found in the registry.
    """
    key = name.lower().strip()
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise UnknownProfile(
            f"No profile named '{name}'. Available: {available}"
        )
    return _REGISTRY[key]


def register_profile(profile: ControllerProfile) -> None:
    """
    Register a custom profile so it can be retrieved by name.

    Args:
        profile: A :class:`ControllerProfile` instance.
                 Its ``name`` attribute (lowercased) becomes the registry key.
    """
    _REGISTRY[profile.name.lower()] = profile


def list_profiles() -> list[str]:
    """Return the names of all registered profiles."""
    return sorted(_REGISTRY.keys())


def detect_profile(sdl_name: str) -> ControllerProfile | None:
    """
    Attempt to auto-detect a profile from the SDL controller name string.

    Args:
        sdl_name: The string returned by ``pygame.joystick.Joystick.get_name()``.

    Returns:
        A matching :class:`ControllerProfile`, or ``None`` if unrecognised.
    """
    lower = sdl_name.lower()
    for hint, profile in _SDL_HINTS:
        if hint in lower:
            return profile
    return None
