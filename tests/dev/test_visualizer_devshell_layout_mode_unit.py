"""Unit tests for DevShell runtime mode and layout integration in DevVisualizer."""

from __future__ import annotations

import arcade

from arcadeactions.dev.devshell_state import DevShellMode
from arcadeactions.dev.visualizer import DevVisualizer


def _window_stub(mocker, *, width: int = 800, height: int = 600):
    window = mocker.MagicMock()
    window._context = mocker.MagicMock()
    window.width = width
    window.height = height
    window.set_minimum_size = mocker.MagicMock()
    return window


def test_preview_clean_hotkey_toggles_mode_when_devshell_enabled(monkeypatch, mocker):
    """F10 should toggle coordinator mode between Edit-Live and Preview-Clean."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=_window_stub(mocker))

    assert viz.devshell_coordinator is not None
    assert viz.devshell_coordinator.state.mode == DevShellMode.EDIT_LIVE

    handled = viz.handle_key_press(arcade.key.F10, 0)
    assert handled is True
    assert viz.devshell_coordinator.state.mode == DevShellMode.PREVIEW_CLEAN

    handled = viz.handle_key_press(arcade.key.F10, 0)
    assert handled is True
    assert viz.devshell_coordinator.state.mode == DevShellMode.EDIT_LIVE


def test_show_enforces_min_window_contract_in_devshell_mode(monkeypatch, mocker):
    """DevShell show should enforce the minimum stage+rail window contract."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    window = _window_stub(mocker, width=640, height=480)
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)

    viz.show()

    assert window.set_minimum_size.call_count >= 1
    min_w, min_h = window.set_minimum_size.call_args.args
    assert min_w >= 1280
    assert min_h >= 720


def test_draw_renders_rails_only_in_edit_live(monkeypatch, mocker):
    """Edit-Live should draw DevShell rails while Preview-Clean should not."""
    monkeypatch.setenv("ARCADEACTIONS_DEVVIZ", "1")
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", return_value=mocker.MagicMock())
    viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=_window_stub(mocker, width=1920, height=1080))
    viz.visible = True
    mocker.patch.object(viz._indicator_text, "draw")
    mocker.patch.object(viz.selection_manager, "draw")
    draw_rect = mocker.patch("arcadeactions.dev.visualizer_draw.arcade.draw_lbwh_rectangle_filled", create=True)

    viz.draw()
    edit_live_calls = draw_rect.call_count
    assert edit_live_calls > 0

    assert viz.devshell_coordinator is not None
    viz.devshell_coordinator.set_preview_clean(True)
    viz.draw()

    # Preview-Clean should not add new rail draws.
    assert draw_rect.call_count == edit_live_calls
