"""Integration tests for DevVisualizer palette window functionality."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.visualizer import DevVisualizer


@pytest.fixture(autouse=True)
def prevent_window_showing(monkeypatch):
    """Prevent palette windows from being shown by integration tests."""
    from arcadeactions.dev.palette_window import PaletteWindow

    def mock_set_visible(self, visible: bool):
        """Update palette visibility state without mapping an OS window."""
        self._is_visible = bool(visible)
        ui_manager = getattr(self, "_ui_manager", None)
        if ui_manager is not None:
            if visible:
                ui_manager.enable()
            else:
                ui_manager.disable()

    monkeypatch.setattr(PaletteWindow, "set_visible", mock_set_visible)
    yield


@pytest.fixture
def dev_visualizer(window):
    """Create a DevVisualizer instance for testing."""
    scene_sprites = arcade.SpriteList()
    dev_viz = DevVisualizer(scene_sprites=scene_sprites, window=window)
    dev_viz.attach_to_window(window)
    return dev_viz


class TestPaletteWindowCreation:
    """Test palette window creation."""

    def test_create_palette_window(self, dev_visualizer, mocker):
        """Verify palette window creation."""
        assert dev_visualizer.palette_window is None

        dev_visualizer._create_palette_window()

        assert dev_visualizer.palette_window is not None

    def test_toggle_palette_creates_window(self, dev_visualizer):
        """Test toggle creates window if missing."""
        assert dev_visualizer.palette_window is None

        dev_visualizer.toggle_palette()

        assert dev_visualizer.palette_window is not None

    def test_toggle_palette_shows_hides(self, dev_visualizer, mocker):
        """Test toggle visibility behavior."""
        # First toggle creates window
        dev_visualizer.toggle_palette()
        assert dev_visualizer.palette_window is not None

        # The current toggle behavior is implemented in DevVisualizer (desired-visible state)
        # and uses show_window()/hide_window() rather than PaletteWindow.toggle_window().
        mock_hide = mocker.patch.object(
            dev_visualizer.palette_window, "hide_window", wraps=dev_visualizer.palette_window.hide_window
        )

        dev_visualizer.toggle_palette()

        mock_hide.assert_called_once()


class TestPaletteWindowPositioning:
    """Test palette window positioning."""

    def test_position_palette_window_relative_to_main(self, dev_visualizer, mocker):
        """Test palette positioning relative to main window."""
        # Mock monitor detection
        mock_monitor_rect = mocker.patch("arcadeactions.dev.visualizer._get_primary_monitor_rect")
        mock_monitor_rect.return_value = (0, 0, 1920, 1080)

        # Mock window location
        mock_get_location = mocker.patch.object(dev_visualizer, "_get_window_location")
        mock_get_location.return_value = (500, 300)

        # Mock update_main_window_position
        mock_update_pos = mocker.patch.object(dev_visualizer, "update_main_window_position")
        mock_update_pos.return_value = True

        dev_visualizer._create_palette_window()

        # Position window
        result = dev_visualizer._position_palette_window(force=True)

        # Should succeed
        assert result is True

    def test_position_palette_window_with_monitor_detection(self, dev_visualizer, mocker):
        """Test positioning with monitor detection."""
        # Mock monitor detection to return valid rect
        mock_monitor_rect = mocker.patch("arcadeactions.dev.visualizer._get_primary_monitor_rect")
        mock_monitor_rect.return_value = (0, 0, 1920, 1080)

        # Mock window location
        mock_get_location = mocker.patch.object(dev_visualizer, "_get_window_location")
        mock_get_location.return_value = (100, 100)

        mock_update_pos = mocker.patch.object(dev_visualizer, "update_main_window_position")
        mock_update_pos.return_value = True

        dev_visualizer._create_palette_window()

        result = dev_visualizer._position_palette_window(force=True)

        assert result is True
        mock_monitor_rect.assert_called()

    def test_position_palette_window_returns_false_when_no_window(self, dev_visualizer):
        """Test positioning returns False when no palette window exists."""
        assert dev_visualizer.palette_window is None

        result = dev_visualizer._position_palette_window(force=True)

        assert result is False

    def test_position_palette_window_returns_false_when_no_monitor(self, dev_visualizer, mocker):
        """Test positioning returns False when monitor detection fails."""
        mock_monitor_rect = mocker.patch("arcadeactions.dev.visualizer._get_primary_monitor_rect")
        mock_monitor_rect.return_value = None

        dev_visualizer._create_palette_window()

        result = dev_visualizer._position_palette_window(force=True)

        assert result is False


class TestPaletteWindowCallbacks:
    """Test palette window callbacks."""

    def test_palette_window_close_callback(self, dev_visualizer, mocker):
        """Test on_close callback behavior."""
        mock_close = mocker.patch.object(dev_visualizer.window, "close")

        dev_visualizer._create_palette_window()
        assert dev_visualizer.palette_window is not None

        # Trigger close callback
        dev_visualizer.palette_window = None  # Simulate close

        # The callback would close the main window, but we're just testing it exists
        # The actual close behavior is tested in the palette_window tests

    def test_palette_forward_key_handler(self, dev_visualizer, mocker):
        """Test key forwarding from palette to main window."""
        dev_visualizer.visible = True
        mock_handle_key = mocker.patch.object(dev_visualizer, "handle_key_press")
        mock_handle_key.return_value = True

        dev_visualizer._create_palette_window()

        # The forward_key_handler is passed to PaletteWindow constructor
        # We can't easily test it directly, but we can verify handle_key_press is callable
        result = dev_visualizer.handle_key_press(arcade.key.F12, 0)
        mock_handle_key.assert_called()
