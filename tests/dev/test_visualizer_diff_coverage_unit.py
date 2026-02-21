"""Additional DevVisualizer unit tests to close branch coverage gaps."""

from __future__ import annotations

import arcade

from arcadeactions.dev.visualizer import DevVisualizer


def _make_viz(monkeypatch, mocker, *, with_window: bool = False) -> DevVisualizer:
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    if with_window:
        window = mocker.MagicMock()
        window.width = 1280
        window.height = 720
        window.set_minimum_size = mocker.MagicMock()
        return DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    return DevVisualizer(scene_sprites=arcade.SpriteList())


def test_init_devshell_panels_disabled_clears_all_handles(monkeypatch, mocker):
    """Disabled DevShell flag should clear panel/coordinator state."""
    viz = _make_viz(monkeypatch, mocker)
    viz._devshell_panels_enabled = False

    viz._init_devshell_panels_if_enabled()

    assert viz.devshell_coordinator is None
    assert viz.devshell_layout is None
    assert viz._devshell_prototype_palette_panel is None
    assert viz._devshell_command_palette_panel is None
    assert viz._devshell_property_inspector_panel is None


def test_ensure_devshell_window_contract_early_return_and_exception_paths(monkeypatch, mocker):
    """Window contract helper should safely return on missing prerequisites and exceptions."""
    viz = _make_viz(monkeypatch, mocker, with_window=True)
    assert viz.window is not None

    viz._devshell_panels_enabled = False
    viz._ensure_devshell_window_contract()
    viz._devshell_panels_enabled = True

    window = viz.window
    viz.window = None
    viz._ensure_devshell_window_contract()
    viz.window = window

    layout = viz.devshell_layout
    viz.devshell_layout = None
    viz._ensure_devshell_window_contract()
    viz.devshell_layout = layout

    window.set_minimum_size.side_effect = RuntimeError("backend refused minimum size")
    viz._ensure_devshell_window_contract()


def test_toggle_and_open_helpers_return_early_when_panels_missing(monkeypatch, mocker):
    """Panel toggle/open helpers should fail closed when panel models are unavailable."""
    viz = _make_viz(monkeypatch, mocker)
    viz._devshell_prototype_palette_panel = None
    viz._devshell_command_palette_panel = None
    viz._devshell_property_inspector_panel = None

    viz.toggle_palette()
    viz.toggle_command_palette()
    viz.toggle_property_inspector()
    assert viz.open_property_inspector_for_current_selection() is False


def test_toggle_command_palette_and_property_inspector_update_focus_state(monkeypatch, mocker):
    """Opening/closing command palette and inspector should update active panel focus."""
    viz = _make_viz(monkeypatch, mocker)
    assert viz.devshell_coordinator is not None
    assert viz._devshell_command_palette_panel is not None
    assert viz._devshell_property_inspector_panel is not None

    viz.toggle_command_palette()
    assert viz.devshell_coordinator.focus_manager.active_panel == "command_palette"
    viz.toggle_command_palette()
    assert viz.devshell_coordinator.focus_manager.active_panel is None

    sprite = arcade.Sprite()
    viz.scene_sprites.append(sprite)
    viz.selection_manager._selected.add(sprite)
    viz.toggle_property_inspector()
    assert viz.devshell_coordinator.focus_manager.active_panel == "property_inspector"
    viz.toggle_property_inspector()
    assert viz.devshell_coordinator.focus_manager.active_panel is None


def test_open_property_inspector_sets_selection_and_visibility(monkeypatch, mocker):
    """Opening inspector should set mode, selection, visibility, and active focus."""
    viz = _make_viz(monkeypatch, mocker)
    assert viz._devshell_property_inspector_panel is not None
    assert viz.devshell_coordinator is not None
    sprite = arcade.Sprite()
    viz.scene_sprites.append(sprite)
    viz.selection_manager._selected.add(sprite)

    assert viz.open_property_inspector_for_current_selection() is True
    assert viz._devshell_property_inspector_panel.visible is True
    assert viz.devshell_coordinator.focus_manager.active_panel == "property_inspector"


def test_sync_panel_order_tracks_visible_panels(monkeypatch, mocker):
    """Visible panel set should be mirrored into coordinator panel-order state."""
    viz = _make_viz(monkeypatch, mocker)
    assert viz.devshell_coordinator is not None
    assert viz._devshell_prototype_palette_panel is not None
    assert viz._devshell_command_palette_panel is not None
    assert viz._devshell_property_inspector_panel is not None

    viz._devshell_prototype_palette_panel.set_visible(True)
    viz._devshell_command_palette_panel.set_visible(True)
    viz._devshell_property_inspector_panel.set_visible(True)
    viz._sync_devshell_panel_order()

    viz.devshell_coordinator.set_active_panel("property_inspector")
    assert viz.devshell_coordinator.focus_manager.active_panel == "property_inspector"


def test_window_location_validation_and_fallbacks(monkeypatch, mocker):
    """Window-location helpers should handle None/Wayland/invalid and tracked fallback."""
    viz = _make_viz(monkeypatch, mocker)
    assert viz._is_valid_window_location(None) is False
    assert viz._is_valid_window_location((0, 0)) is False
    assert viz._is_valid_window_location((-50000, 10)) is False
    assert viz._is_valid_window_location((200, 300)) is True
    assert viz._get_window_location(None) is None

    window = mocker.MagicMock()
    window.get_location.return_value = (200, 300)
    assert viz._get_window_location(window) == (200, 300)

    window.get_location.return_value = (0, 0)
    viz._position_tracker.track_known_position(window, 150, 250)
    assert viz._get_window_location(window) == (150, 250)

    window.get_location.side_effect = RuntimeError("unmapped")
    assert viz._get_window_location(window) == (150, 250)


def test_update_main_window_position_handles_missing_requested_location(monkeypatch, mocker):
    """Main-window position update should handle absent requested location attribute."""
    viz = _make_viz(monkeypatch, mocker, with_window=True)
    assert viz.window is not None
    window = viz.window
    window.get_location.return_value = (310, 410)
    window._arcadeactions_last_set_location = None
    mock_track = mocker.patch.object(viz._position_tracker, "track_window_position", return_value=True)

    result = viz.update_main_window_position()

    assert result is True
    mock_track.assert_called_once_with(window)
    assert viz._window_decoration_dx is None
    assert viz._window_decoration_dy is None
