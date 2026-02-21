"""Unit tests for DevVisualizer event handler wrapping."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.visualizer import DevVisualizer


@pytest.mark.integration
class TestWindowKeyHandling:
    """Tests for wrapped window key handling."""

    def test_f12_toggles_dev_visualizer(self, window, mocker):
        """F12 should toggle DevVisualizer without calling the original handler."""
        dev_viz = DevVisualizer(window=window)
        original_handler = mocker.MagicMock()
        window.on_key_press = original_handler

        dev_viz.attach_to_window(window)
        toggle = mocker.patch.object(dev_viz, "toggle")

        window.on_key_press(arcade.key.F12, 0)

        toggle.assert_called_once()
        original_handler.assert_not_called()

    def test_escape_closes_palette_in_edit_mode(self, window, mocker):
        """ESC should route through normal key path (no legacy palette-window close)."""
        dev_viz = DevVisualizer(window=window)
        original_handler = mocker.MagicMock()
        window.on_key_press = original_handler

        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        handle_key_press = mocker.patch.object(dev_viz, "handle_key_press", return_value=False)

        window.on_key_press(arcade.key.ESCAPE, 0)

        handle_key_press.assert_called_once_with(arcade.key.ESCAPE, 0)
        original_handler.assert_called_once_with(arcade.key.ESCAPE, 0)

    def test_escape_calls_original_when_not_visible(self, window, mocker):
        """ESC should fall back to original handler when not in edit mode."""
        dev_viz = DevVisualizer(window=window)
        original_handler = mocker.MagicMock()
        window.on_key_press = original_handler

        dev_viz.attach_to_window(window)
        dev_viz.visible = False

        window.on_key_press(arcade.key.ESCAPE, 0)

        original_handler.assert_called_once_with(arcade.key.ESCAPE, 0)

    def test_mouse_release_schedules_delayed_inspector_focus_when_handled(self, window, mocker):
        """Handled mouse-release should not schedule legacy inspector-window focus retries."""
        dev_viz = DevVisualizer(window=window)
        original_release = mocker.MagicMock()
        window.on_mouse_release = original_release
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        mocker.patch.object(dev_viz, "handle_mouse_release", return_value=True)

        scheduled: list[tuple[callable, float]] = []

        def schedule_once(fn, delay: float):
            scheduled.append((fn, float(delay)))

        mocker.patch("arcadeactions.dev.event_handlers.arcade.schedule_once", side_effect=schedule_once)

        window.on_mouse_release(10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert scheduled == []
        original_release.assert_not_called()

    def test_mouse_release_skips_delayed_focus_for_closed_inspector(self, window, mocker):
        """Handled mouse-release should not schedule focus retries for closed inspector windows."""
        dev_viz = DevVisualizer(window=window)
        window.on_mouse_release = mocker.MagicMock()
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        inspector_window = mocker.MagicMock()
        inspector_window.visible = True
        inspector_window.is_closed = True
        dev_viz.property_inspector_window = inspector_window
        mocker.patch.object(dev_viz, "handle_mouse_release", return_value=True)
        schedule_once = mocker.patch("arcadeactions.dev.event_handlers.arcade.schedule_once")

        window.on_mouse_release(10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        schedule_once.assert_not_called()

    def test_key_press_routes_to_inspector_when_inspector_accepts(self, window, mocker):
        """Legacy inspector-window forwarding should no longer run in wrapped key path."""
        dev_viz = DevVisualizer(window=window)
        original_handler = mocker.MagicMock()
        window.on_key_press = original_handler
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        inspector_window = mocker.MagicMock()
        inspector_window.accepts_forwarded_key.return_value = True
        dev_viz.property_inspector_window = inspector_window
        handle_key_press = mocker.patch.object(dev_viz, "handle_key_press", return_value=False)
        schedule_once = mocker.patch("arcadeactions.dev.event_handlers.arcade.schedule_once")

        window.on_key_press(arcade.key.ENTER, 0)

        inspector_window.mark_forwarded_input_activity.assert_not_called()
        inspector_window.on_key_press.assert_not_called()
        assert schedule_once.call_count == 0
        handle_key_press.assert_called_once_with(arcade.key.ENTER, 0)
        original_handler.assert_called_once_with(arcade.key.ENTER, 0)

    def test_key_press_falls_back_when_inspector_does_not_accept(self, window, mocker):
        """If inspector declines a key, normal host/original key flow should continue."""
        dev_viz = DevVisualizer(window=window)
        original_handler = mocker.MagicMock()
        window.on_key_press = original_handler
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        inspector_window = mocker.MagicMock()
        inspector_window.visible = True
        inspector_window.is_closed = False
        inspector_window.accepts_forwarded_key.return_value = False
        dev_viz.property_inspector_window = inspector_window
        handle_key_press = mocker.patch.object(dev_viz, "handle_key_press", return_value=False)

        window.on_key_press(arcade.key.ENTER, 0)

        inspector_window.mark_forwarded_input_activity.assert_not_called()
        inspector_window.on_key_press.assert_not_called()
        inspector_window.refresh_editor_style.assert_not_called()
        handle_key_press.assert_called_once_with(arcade.key.ENTER, 0)
        original_handler.assert_called_once_with(arcade.key.ENTER, 0)

    def test_mouse_press_schedules_delayed_inspector_focus_when_handled(self, window, mocker):
        """Handled mouse-press should not schedule legacy inspector-window focus retries."""
        dev_viz = DevVisualizer(window=window)
        original_press = mocker.MagicMock()
        window.on_mouse_press = original_press
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        mocker.patch.object(dev_viz, "handle_mouse_press", return_value=True)

        scheduled: list[tuple[callable, float]] = []

        def schedule_once(fn, delay: float):
            scheduled.append((fn, float(delay)))

        mocker.patch("arcadeactions.dev.event_handlers.arcade.schedule_once", side_effect=schedule_once)

        window.on_mouse_press(10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert scheduled == []
        original_press.assert_not_called()

    def test_window_text_motion_falls_back_to_original_handler(self, window, mocker):
        """Text-motion is routed via wrapped view handlers, not window-level handlers."""
        dev_viz = DevVisualizer(window=window)
        original_text_motion = mocker.MagicMock()
        window.on_text_motion = original_text_motion
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        inspector_window = mocker.MagicMock()
        inspector_window.visible = True
        inspector_window.is_closed = False
        inspector_window.accepts_forwarded_text_motion.return_value = True
        dev_viz.property_inspector_window = inspector_window

        window.on_text_motion(arcade.key.MOTION_BACKSPACE)

        inspector_window.on_text_motion.assert_not_called()
        inspector_window.mark_forwarded_input_activity.assert_not_called()
        inspector_window.refresh_editor_style.assert_not_called()
        original_text_motion.assert_called_once_with(arcade.key.MOTION_BACKSPACE)

    def test_window_key_routing_swallow_inspector_exceptions(self, window, mocker):
        """Legacy inspector-window exceptions should be irrelevant in key routing."""
        dev_viz = DevVisualizer(window=window)
        original_handler = mocker.MagicMock()
        window.on_key_press = original_handler
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        inspector_window = mocker.MagicMock()
        inspector_window.accepts_forwarded_key.return_value = True
        inspector_window.refresh_editor_style.side_effect = RuntimeError("style refresh failed")
        dev_viz.property_inspector_window = inspector_window
        handle_key_press = mocker.patch.object(dev_viz, "handle_key_press", return_value=False)

        window.on_key_press(arcade.key.A, 0)

        inspector_window.on_key_press.assert_not_called()
        handle_key_press.assert_called_once_with(arcade.key.A, 0)
        original_handler.assert_called_once_with(arcade.key.A, 0)

    def test_window_enter_routing_schedules_style_refresh_retries(self, window, mocker):
        """Enter should not schedule legacy inspector-window style refresh retries."""
        dev_viz = DevVisualizer(window=window)
        window.on_key_press = mocker.MagicMock()
        dev_viz.attach_to_window(window)
        dev_viz.visible = True
        inspector_window = mocker.MagicMock()
        inspector_window.accepts_forwarded_key.return_value = True
        dev_viz.property_inspector_window = inspector_window
        handle_key_press = mocker.patch.object(dev_viz, "handle_key_press", return_value=False)

        scheduled: list[tuple[callable, float]] = []

        def schedule_once(fn, delay: float):
            scheduled.append((fn, float(delay)))

        mocker.patch("arcadeactions.dev.event_handlers.arcade.schedule_once", side_effect=schedule_once)

        window.on_key_press(arcade.key.ENTER, 0)

        assert scheduled == []
        handle_key_press.assert_called_once_with(arcade.key.ENTER, 0)
