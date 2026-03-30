"""
controlpad
~~~~~~~~~~
A cross-platform Python library for integrating game controllers into
robotics, drone, and edge computing projects.

Quick start::

    from controlpad import Gamepad

    gp = Gamepad()

    @gp.on_axis("left_x", "left_y")
    def on_left_stick(x, y):
        print(f"Left stick: x={x:.2f}  y={y:.2f}")

    @gp.on_button_press("cross")
    def on_cross():
        print("Cross pressed!")

    gp.run()
"""

from .gamepad import Gamepad, ControllerState
from .profiles import (
    ControllerProfile,
    DUALSENSE,
    XBOX,
    get_profile,
    register_profile,
    list_profiles,
)
from .filters import apply_deadzone, apply_deadzone_2d, apply_expo, ExponentialSmoother
from .exceptions import (
    ControlpadError,
    NoControllerFound,
    ControllerDisconnected,
    BackendNotAvailable,
    UnknownProfile,
)

# Read the version from the installed package metadata (set in pyproject.toml).
#
# The try/except handles the case where the package hasn't been installed yet
# (e.g. someone is running directly from the cloned source without `pip install -e .`).
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("controlpad")
except PackageNotFoundError:
    # Running from source, not installed — version is genuinely unknown.
    __version__ = "unknown"

__author__  = "Supun Sriyananda"
__email__   = "supunsriyananda@gmail.com"
__license__ = "MIT"

__all__ = [
    # Core
    "Gamepad",
    "ControllerState",
    # Profiles
    "ControllerProfile",
    "DUALSENSE",
    "XBOX",
    "get_profile",
    "register_profile",
    "list_profiles",
    # Filters
    "apply_deadzone",
    "apply_deadzone_2d",
    "apply_expo",
    "ExponentialSmoother",
    # Exceptions
    "ControlpadError",
    "NoControllerFound",
    "ControllerDisconnected",
    "BackendNotAvailable",
    "UnknownProfile",
]