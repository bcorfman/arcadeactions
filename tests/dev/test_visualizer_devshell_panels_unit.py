"""Unit tests for feature-flagged DevShell panel integration in DevVisualizer."""

from __future__ import annotations

import arcade

from arcadeactions.dev.prototype_registry import get_registry
from arcadeactions.dev.visualizer import DevVisualizer


def test_visualizer_initializes_devshell_coordinator_when_flag_enabled(monkeypatch, mocker):
    """Feature flag should initialize coordinator + panel models at startup."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())

    viz = DevVisualizer(scene_sprites=arcade.SpriteList())

    assert viz.devshell_coordinator is not None
    assert viz._devshell_command_palette_panel is not None
    assert viz._devshell_property_inspector_panel is not None
    assert viz._devshell_prototype_palette_panel is not None


def test_toggle_command_palette_uses_devshell_panel_when_enabled(monkeypatch, mocker):
    """With DevShell enabled, F8 toggle path should use panel model instead of window."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    viz.command_palette_window = mocker.MagicMock()

    panel = viz._devshell_command_palette_panel
    assert panel is not None
    assert panel.visible is False

    viz.toggle_command_palette()
    assert panel.visible is True
    assert viz.devshell_coordinator is not None
    assert viz.devshell_coordinator.focus_manager.active_panel == "command_palette"

    viz.toggle_command_palette()
    assert panel.visible is False


def test_open_property_inspector_uses_devshell_panel_when_enabled(monkeypatch, mocker):
    """open_property_inspector_for_current_selection should surface DevShell panel in flagged mode."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    sprite = arcade.Sprite()
    viz.scene_sprites.append(sprite)
    viz.selection_manager._selected.add(sprite)

    opened = viz.open_property_inspector_for_current_selection()

    panel = viz._devshell_property_inspector_panel
    assert opened is True
    assert panel is not None
    assert panel.visible is True
    assert viz.devshell_coordinator is not None
    assert viz.devshell_coordinator.focus_manager.active_panel == "property_inspector"


def test_property_inspector_text_routes_once_in_devshell_mode(monkeypatch, mocker):
    """One routed text event should append one character in DevShell inspector edit mode."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    sprite = arcade.Sprite()
    viz.scene_sprites.append(sprite)
    viz.selection_manager._selected.add(sprite)

    assert viz.open_property_inspector_for_current_selection() is True
    assert viz.devshell_coordinator is not None
    panel = viz._devshell_property_inspector_panel
    assert panel is not None
    assert viz.devshell_coordinator.route_key_press(arcade.key.ENTER, 0) is True
    before = panel.text_buffer.text
    assert viz.devshell_coordinator.route_text("1") is True

    assert panel.text_buffer.text == f"{before}1"


def test_toggle_prototype_palette_uses_devshell_panel_when_enabled(monkeypatch, mocker):
    """F11 toggle path should use DevShell prototype panel model."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    viz = DevVisualizer(scene_sprites=arcade.SpriteList())

    panel = viz._devshell_prototype_palette_panel
    assert panel is not None
    assert panel.visible is False

    viz.toggle_palette()
    assert panel.visible is True
    assert viz.devshell_coordinator is not None
    assert viz.devshell_coordinator.focus_manager.active_panel == "prototype_palette"

    viz.toggle_palette()
    assert panel.visible is False


def test_open_overrides_editor_uses_devshell_inspector_arrange_mode(monkeypatch, mocker, tmp_path):
    """Arrange editor open path should run through DevShell inspector panel arrange mode."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    source_path = tmp_path / "scene.py"
    source_path.write_text(
        "arrange_grid(sprites=s, rows=1, cols=2, start_x=10, start_y=20, spacing_x=5, spacing_y=5)\n",
        encoding="utf-8",
    )
    viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    sprite = arcade.Sprite()
    sprite._source_markers = [{"file": str(source_path), "lineno": 1, "type": "arrange"}]
    viz.scene_sprites.append(sprite)

    opened = viz.open_overrides_editor_for_sprite(sprite)

    panel = viz._devshell_property_inspector_panel
    assert opened is True
    assert panel is not None
    assert panel.visible is True
    assert panel.mode == "arrange"


def test_clicking_devshell_prototype_panel_spawns_selected_prototype(monkeypatch, mocker):
    """Click on a prototype row in DevShell palette should spawn into scene_sprites."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = mocker.MagicMock()
    window._context = mocker.MagicMock()
    window.width = 1920
    window.height = 1080
    window.set_minimum_size = mocker.MagicMock()
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    panel = viz._devshell_prototype_palette_panel
    assert panel is not None
    registry = get_registry()
    if not registry.all():
        registry.register("test_spawn_proto")(lambda _ctx: arcade.Sprite())
    panel.set_visible(True)
    viz._sync_devshell_panel_order()

    before_count = len(viz.scene_sprites)
    geometry = viz._devshell_prototype_panel_geometry()
    assert geometry is not None
    left, bottom, _width, height = geometry
    click_x = left + 10
    click_y = bottom + height - 46

    handled = viz.handle_mouse_press(int(click_x), int(click_y), arcade.MOUSE_BUTTON_LEFT, 0)

    assert handled is True
    assert len(viz.scene_sprites) == before_count + 1
