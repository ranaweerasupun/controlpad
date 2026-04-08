"""
controlpad.exceptions
~~~~~~~~~~~~~~~~~~~~~
Custom exceptions for the controlpad library.
"""


class ControlpadError(Exception):
    """Base exception for all controlpad errors."""


class NoControllerFound(ControlpadError):
    """Raised when no controller is detected and one is required."""


class ControllerDisconnected(ControlpadError):
    """Raised when a previously connected controller is lost."""


class BackendNotAvailable(ControlpadError):
    """Raised when the requested backend cannot be initialised."""


class UnknownProfile(ControlpadError):
    """Raised when a profile name cannot be resolved."""
