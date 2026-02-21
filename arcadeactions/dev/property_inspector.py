"""Sprite property inspection model (window-free)."""

from __future__ import annotations

from collections.abc import Sequence

import arcade

from arcadeactions.dev.property_history import PropertyHistory
from arcadeactions.dev.property_registry import PropertyDefinition, SpritePropertyRegistry
from arcadeactions.dev.property_widgets import parse_property_text


class SpritePropertyInspector:
    """Core property inspector model independent from window rendering."""

    def __init__(
        self,
        *,
        property_registry: SpritePropertyRegistry,
        history: PropertyHistory,
        window: arcade.Window | None,
    ) -> None:
        self._registry = property_registry
        self._history = history
        self._window = window
        self._selection: list[arcade.Sprite] = []
        self._last_non_empty_selection: list[arcade.Sprite] = []
        self._properties: list[PropertyDefinition] = []
        self._active_index = 0

    def set_selection(self, selection: Sequence[arcade.Sprite]) -> None:
        self._selection = list(selection)
        if self._selection:
            self._last_non_empty_selection = list(self._selection)
        self._properties = self._registry.properties_for_selection(self._selection)
        if self._active_index >= len(self._properties):
            self._active_index = max(0, len(self._properties) - 1)

    def selection(self) -> list[arcade.Sprite]:
        return list(self._selection)

    def visible_properties(self) -> list[PropertyDefinition]:
        return list(self._properties)

    def current_property(self) -> PropertyDefinition | None:
        if not self._properties:
            return None
        return self._properties[self._active_index]

    def move_active_property(self, delta: int) -> None:
        if not self._properties:
            self._active_index = 0
            return
        self._active_index = (self._active_index + delta) % len(self._properties)

    def _expression_names(self, property_name: str) -> dict[str, float]:
        width = 0.0
        height = 0.0
        if self._window is not None:
            width = float(self._window.width)
            height = float(self._window.height)

        axis_center = width / 2.0
        if property_name in ("center_y", "top", "bottom"):
            axis_center = height / 2.0

        return {
            "SCREEN_WIDTH": width,
            "SCREEN_HEIGHT": height,
            "SCREEN_CENTER": axis_center,
            "SCREEN_CENTER_X": width / 2.0,
            "SCREEN_CENTER_Y": height / 2.0,
        }

    def apply_property_text(self, property_name: str, text: str) -> bool:
        if not self._selection:
            return False

        parsed = parse_property_text(property_name, text, self._expression_names(property_name))
        for sprite in self._selection:
            old_value = self._registry.get_value(sprite, property_name)
            self._registry.set_value(sprite, property_name, parsed)
            new_value = self._registry.get_value(sprite, property_name)
            if old_value != new_value:
                self._history.record_change(sprite, property_name, old_value, new_value)
        return True

    def property_value(self, property_name: str) -> object | None:
        if not self._selection:
            return None
        return self._registry.get_value(self._selection[0], property_name)

    def current_property_value_text(self) -> str:
        current = self.current_property()
        if current is None:
            return ""
        value = self.property_value(current.name)
        if value is None:
            return ""
        return self._format_python_value(value)

    def undo(self) -> bool:
        targets = self._selection if self._selection else self._last_non_empty_selection
        changed = False
        for sprite in targets:
            if self._history.undo(sprite) is not None:
                changed = True
        return changed

    def redo(self) -> bool:
        targets = self._selection if self._selection else self._last_non_empty_selection
        changed = False
        for sprite in targets:
            if self._history.redo(sprite) is not None:
                changed = True
        return changed

    def copy_selection_as_python(self, property_names: Sequence[str] | None = None) -> str:
        if not self._selection:
            return ""

        names = list(property_names) if property_names is not None else [prop.name for prop in self._properties]
        lines: list[str] = []
        sprite = self._selection[0]
        for property_name in names:
            value = self._registry.get_value(sprite, property_name)
            lines.append(f"sprite.{property_name} = {self._format_python_value(value)}")
        return "\n".join(lines)

    def copy_current_property(self) -> str:
        current = self.current_property()
        if current is None or not self._selection:
            return ""
        value = self._registry.get_value(self._selection[0], current.name)
        return f"sprite.{current.name} = {self._format_python_value(value)}"

    @staticmethod
    def _format_python_value(value: object) -> str:
        if type(value) is str:
            return repr(value)
        return str(value)
