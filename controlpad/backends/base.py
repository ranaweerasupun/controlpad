"""
controlpad.backends.base
~~~~~~~~~~~~~~~~~~~~~~~~
Abstract base class for controller backends.

A backend is responsible for polling the OS for raw controller data.
Concrete implementations wrap pygame (all platforms) or evdev (Linux headless).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawState:
    """Raw snapshot of controller hardware state."""
    axes:    list[float]
    buttons: list[bool]
    hats:    list[tuple[int, int]]
    name:    str


class BaseBackend(ABC):
    """
    Abstract controller backend.

    Subclasses must implement :meth:`open`, :meth:`close`,
    :meth:`poll`, and :meth:`is_connected`.
    """

    @abstractmethod
    def open(self, index: int = 0) -> str:
        """
        Open the controller at *index*.

        Returns:
            The SDL/OS name of the connected controller.

        Raises:
            NoControllerFound: If no controller is available.
        """

    @abstractmethod
    def close(self) -> None:
        """Release all resources held by this backend."""

    @abstractmethod
    def poll(self) -> RawState:
        """
        Read the current controller state.

        Returns:
            A :class:`RawState` snapshot.

        Raises:
            ControllerDisconnected: If the controller has been unplugged.
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the controller is currently accessible."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of controllers visible to this backend."""
