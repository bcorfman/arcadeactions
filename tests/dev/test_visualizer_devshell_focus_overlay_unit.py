"""Unit tests for DevShell focus overlay drawing in visualizer_draw."""

from __future__ import annotations

import arcade

from arcadeactions.dev.visualizer import DevVisualizer


def _make_window_stub(mocker):
    window = mocker.MagicMock()
    window._context = mocker.MagicMock()
    window.width = 1280
    window.height = 720
    return window


def test_draw_shows_focus_overlay_with_active_panel(monkeypatch, mocker):
    """Edit-Live mode should render a focus label and active panel marker."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _make_window_stub(mocker)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    viz.visible = True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_text = mocker.patch("arcadeactions.dev.visualizer_draw._draw_text_obj")
    mocker.patch("arcadeactions.dev.visualizer_draw.arcade.draw_lbwh_rectangle_filled", create=True)

    assert viz._devshell_command_palette_panel is not None
    viz._devshell_command_palette_panel.set_visible(True)
    viz._sync_devshell_panel_order()
    assert viz.devshell_coordinator is not None
    viz.devshell_coordinator.set_active_panel("command_palette")

    viz.draw()

    labels = [call.args[0] for call in draw_text.call_args_list if call.args]
    assert "Focus: command_palette" in labels
    assert any("[ACTIVE]" in label for label in labels)


def test_draw_hides_focus_overlay_in_preview_clean(monkeypatch, mocker):
    """Preview-Clean mode should suppress focus overlay text."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _make_window_stub(mocker)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    viz.visible = True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_text = mocker.patch("arcadeactions.dev.visualizer_draw._draw_text_obj")

    assert viz.devshell_coordinator is not None
    viz.devshell_coordinator.set_preview_clean(True)
    viz.draw()

    labels = [call.args[0] for call in draw_text.call_args_list if call.args]
    assert "Focus: game-stage" not in labels


def test_draw_renders_command_palette_panel_overlay_when_visible(monkeypatch, mocker):
    """Visible DevShell command palette panel should render an in-window panel header."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _make_window_stub(mocker)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    viz.visible = True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_text = mocker.patch("arcadeactions.dev.visualizer_draw._draw_text_obj")
    mocker.patch("arcadeactions.dev.visualizer_draw.arcade.draw_lbwh_rectangle_filled", create=True)

    assert viz._devshell_command_palette_panel is not None
    viz._devshell_command_palette_panel.set_visible(True)
    viz._sync_devshell_panel_order()
    viz.draw()

    labels = [call.args[0] for call in draw_text.call_args_list if call.args]
    assert any("Command Palette" in label for label in labels)


def test_draw_renders_property_inspector_panel_overlay_when_visible(monkeypatch, mocker):
    """Visible DevShell inspector panel should render an in-window panel header."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _make_window_stub(mocker)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    viz.visible = True
    sprite = arcade.Sprite()
    viz.scene_sprites.append(sprite)
    viz.selection_manager._selected.add(sprite)
    assert viz.open_property_inspector_for_current_selection() is True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_text = mocker.patch("arcadeactions.dev.visualizer_draw._draw_text_obj")
    mocker.patch("arcadeactions.dev.visualizer_draw.arcade.draw_lbwh_rectangle_filled", create=True)
    viz.draw()

    labels = [call.args[0] for call in draw_text.call_args_list if call.args]
    assert any("Inspector" in label for label in labels)


def test_draw_shows_transient_focus_pulse_badge_on_focus_change(monkeypatch, mocker):
    """Focus change should briefly render a pulse badge on the active panel row."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _make_window_stub(mocker)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    viz.visible = True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_text = mocker.patch("arcadeactions.dev.visualizer_draw._draw_text_obj")
    mocker.patch("arcadeactions.dev.visualizer_draw.arcade.draw_lbwh_rectangle_filled", create=True)
    mocker.patch("arcadeactions.dev.visualizer_draw.time.monotonic", return_value=100.0)

    assert viz._devshell_command_palette_panel is not None
    viz._devshell_command_palette_panel.set_visible(True)
    viz._sync_devshell_panel_order()
    assert viz.devshell_coordinator is not None
    viz.devshell_coordinator.set_active_panel("command_palette")

    viz.draw()

    labels = [call.args[0] for call in draw_text.call_args_list if call.args]
    assert any("[PULSE]" in label for label in labels)


def test_draw_clears_focus_pulse_badge_after_timeout(monkeypatch, mocker):
    """Pulse badge should disappear when focus-pulse timeout elapses."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _make_window_stub(mocker)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    viz.visible = True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_text = mocker.patch("arcadeactions.dev.visualizer_draw._draw_text_obj")
    mocker.patch("arcadeactions.dev.visualizer_draw.arcade.draw_lbwh_rectangle_filled", create=True)

    assert viz._devshell_command_palette_panel is not None
    viz._devshell_command_palette_panel.set_visible(True)
    viz._sync_devshell_panel_order()
    assert viz.devshell_coordinator is not None

    mocker.patch("arcadeactions.dev.visualizer_draw.time.monotonic", side_effect=[100.0, 101.0])
    viz.devshell_coordinator.set_active_panel("command_palette")
    viz.draw()
    draw_text.reset_mock()
    viz.draw()

    labels = [call.args[0] for call in draw_text.call_args_list if call.args]
    assert not any("[PULSE]" in label for label in labels)
