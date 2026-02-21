"""Unit tests for DevShellPrototypePalettePanel."""

from __future__ import annotations

import arcade

from arcadeactions.dev.devshell_prototype_palette_panel import DevShellPrototypePalettePanel


class _Registry:
    def __init__(self) -> None:
        self._items: dict[str, callable] = {}

    def all(self) -> dict[str, callable]:
        return self._items

    def has(self, prototype_id: str) -> bool:
        return prototype_id in self._items

    def create(self, prototype_id: str, _ctx):
        return self._items[prototype_id]()


class _Scene:
    def __init__(self) -> None:
        self.items: list[object] = []

    def append(self, sprite: object) -> None:
        self.items.append(sprite)


class _Ctx:
    def __init__(self, scene_sprites) -> None:
        self.scene_sprites = scene_sprites


def test_panel_visibility_selection_and_empty_spawn():
    """Visibility toggle and empty spawn should preserve safe defaults."""
    panel = DevShellPrototypePalettePanel(registry=_Registry(), dev_context=_Ctx(_Scene()))
    assert panel.visible is False
    assert panel.on_key_press(arcade.key.DOWN, 0) is False
    panel.toggle_visible()
    assert panel.visible is True
    assert panel.spawn_selected() is False
    assert panel.selected_index == 0


def test_panel_spawn_and_navigation_paths():
    """Navigation should wrap selected index; enter should spawn selected prototype."""
    registry = _Registry()
    registry._items["a"] = arcade.Sprite
    registry._items["b"] = arcade.Sprite
    scene = _Scene()
    panel = DevShellPrototypePalettePanel(registry=registry, dev_context=_Ctx(scene))
    panel.set_visible(True)

    assert panel.on_key_press(arcade.key.DOWN, 0) is True
    assert panel.selected_index == 1
    assert panel.on_key_press(arcade.key.DOWN, 0) is True
    assert panel.selected_index == 0
    assert panel.on_key_press(arcade.key.UP, 0) is True
    assert panel.selected_index == 1

    assert panel.on_key_press(arcade.key.ENTER, 0) is True
    assert len(scene.items) == 1
    sprite = scene.items[0]
    assert sprite.center_x == 640
    assert sprite.center_y == 360


def test_panel_spawn_by_id_missing_and_no_scene_list():
    """Spawn-by-id should fail when id is unknown or scene list is unavailable."""
    registry = _Registry()
    registry._items["a"] = arcade.Sprite
    panel = DevShellPrototypePalettePanel(registry=registry, dev_context=_Ctx(None))
    panel.set_visible(True)

    assert panel.spawn_by_id("missing") is False
    assert panel.spawn_by_id("a") is False


def test_panel_escape_and_f11_close_and_text_handlers():
    """Escape/F11 should hide panel; text handlers should return False."""
    registry = _Registry()
    registry._items["a"] = arcade.Sprite
    panel = DevShellPrototypePalettePanel(registry=registry, dev_context=_Ctx(_Scene()))
    panel.set_visible(True)

    assert panel.on_text("x") is False
    assert panel.on_text_motion(arcade.key.MOTION_BACKSPACE) is False
    assert panel.on_key_press(arcade.key.ESCAPE, 0) is True
    assert panel.visible is False
    panel.set_visible(True)
    assert panel.on_key_press(arcade.key.F11, 0) is True
    assert panel.visible is False
