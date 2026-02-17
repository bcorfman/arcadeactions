"""Focused unit tests for arcadeactions.dev.visualizer_keys helpers."""

from __future__ import annotations

import arcade

from arcadeactions.dev import visualizer_keys


class _StubSelectionManager:
    def __init__(self, selected: list[object] | None = None) -> None:
        self._selected = selected or []

    def get_selected(self) -> list[object]:
        return list(self._selected)


class _StubDevViz:
    def __init__(self, *, selected: list[object] | None = None, toggle_result: bool = False) -> None:
        self.selection_manager = _StubSelectionManager(selected=selected)
        self.scene_sprites = []
        self.overrides_panel = None

    def toggle_palette(self) -> None:
        return None

    def toggle_command_palette(self) -> None:
        return None


def test_handle_key_press_o_is_unhandled():
    """Pressing O should return False (no reserved behavior)."""
    dev_viz = _StubDevViz()

    handled = visualizer_keys.handle_key_press(dev_viz, arcade.key.O, 0)

    assert handled is False
