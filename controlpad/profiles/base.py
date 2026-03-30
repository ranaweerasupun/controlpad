"""
controlpad.profiles.base
~~~~~~~~~~~~~~~~~~~~~~~~
Base class for controller profiles.

A profile maps raw pygame axis/button indices to human-readable names,
and declares which axes need their sign flipped (some controllers report
Y-up as negative, others as positive).
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ControllerProfile:
    """
    Describes the axis and button layout of a specific controller model.

    Attributes:
        name:          Human-readable profile name (e.g. "DualSense").
        axis_map:      Maps semantic name → axis index.
                       e.g. {"left_x": 0, "left_y": 1, ...}
        button_map:    Maps semantic name → button index.
                       e.g. {"cross": 0, "circle": 1, ...}
        invert_axes:   Set of axis names whose raw values should be negated.
                       Typically {"left_y", "right_y"} so that up = +1.
        trigger_axes:  Set of axis names that are triggers (range -1 → +1,
                       normalised internally to 0 → 1).
        hat_map:       Maps semantic hat name → hat index (D-pad).
    """

    name: str
    axis_map: dict[str, int] = field(default_factory=dict)
    button_map: dict[str, int] = field(default_factory=dict)
    invert_axes: set[str] = field(default_factory=set)
    trigger_axes: set[str] = field(default_factory=set)
    hat_map: dict[str, int] = field(default_factory=dict)

    def get_axis_index(self, name: str) -> int | None:
        return self.axis_map.get(name)

    def get_button_index(self, name: str) -> int | None:
        return self.button_map.get(name)

    def axis_names(self) -> list[str]:
        return list(self.axis_map.keys())

    def button_names(self) -> list[str]:
        return list(self.button_map.keys())
