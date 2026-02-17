"""Tests for DevVisualizer key handling.

Tests handle_key_press method which handles keyboard input for DevVisualizer.
This is a complex function (F complexity) with many branches.
"""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.visualizer import DevVisualizer
from tests.conftest import ActionTestBase

pytestmark = pytest.mark.integration


class TestHandleKeyPressBasic(ActionTestBase):
    """Test suite for basic key handling in handle_key_press."""

    def test_f11_toggles_palette(self, window, mocker):
        """Test that F11 toggles palette window."""
        dev_viz = DevVisualizer()

        # Mock toggle_palette method
        mock_toggle = mocker.patch.object(dev_viz, "toggle_palette")

        result = dev_viz.handle_key_press(arcade.key.F11, 0)

        assert result is True
        mock_toggle.assert_called_once()

    def test_f8_toggles_command_palette(self, window, test_sprite, mocker):
        """Test that F8 toggles command palette window."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        dev_viz.selection_manager._selected.add(test_sprite)

        mock_toggle = mocker.patch.object(dev_viz, "toggle_command_palette")

        result = dev_viz.handle_key_press(arcade.key.F8, 0)

        assert result is True
        mock_toggle.assert_called_once_with()

    def test_f8_handles_empty_scene(self, window, mocker):
        """Test that F8 still toggles command palette when scene is empty."""
        dev_viz = DevVisualizer()
        mock_toggle = mocker.patch.object(dev_viz, "toggle_command_palette")

        result = dev_viz.handle_key_press(arcade.key.F8, 0)

        assert result is True
        mock_toggle.assert_called_once_with()

    def test_e_key_exports_to_yaml(self, window, test_sprite_list, mocker, tmp_path):
        """Test that E key exports scene to YAML."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # Mock export_template (imported inside the function, so patch the module)
        mock_export = mocker.patch("arcadeactions.dev.templates.export_template")

        result = dev_viz.handle_key_press(arcade.key.E, 0)

        assert result is True
        mock_export.assert_called_once()

    def test_i_key_imports_from_yaml(self, window, test_sprite_list, mocker, tmp_path):
        """Test that I key imports scene from YAML."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # Mock load_scene_template (imported inside the function, so patch the module)
        mock_load = mocker.patch("arcadeactions.dev.templates.load_scene_template")

        result = dev_viz.handle_key_press(arcade.key.I, 0)

        assert result is True
        # Should try to load from files (even if they don't exist, returns True)
        # The actual import logic would be called if files exist

    def test_delete_key_removes_selected_sprites(self, window, test_sprite_list, mocker):
        """Test that Delete key removes selected sprites."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # Select all sprites
        for sprite in test_sprite_list:
            dev_viz.selection_manager._selected.add(sprite)

        result = dev_viz.handle_key_press(arcade.key.DELETE, 0)

        assert result is True
        # Sprites should be removed from scene
        assert len(dev_viz.scene_sprites) == 0
        # Selection should be cleared
        assert len(dev_viz.selection_manager.get_selected()) == 0

    def test_backspace_key_removes_selected_sprites(self, window, test_sprite_list, mocker):
        """Test that Backspace key removes selected sprites (same as Delete)."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # Select all sprites
        for sprite in test_sprite_list:
            dev_viz.selection_manager._selected.add(sprite)

        result = dev_viz.handle_key_press(arcade.key.BACKSPACE, 0)

        assert result is True
        # Sprites should be removed from scene
        assert len(dev_viz.scene_sprites) == 0

    def test_delete_key_returns_false_with_no_selection(self, window, test_sprite_list):
        """Test that Delete key returns False when no sprites are selected."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # No sprites selected
        assert len(dev_viz.selection_manager.get_selected()) == 0

        initial_count = len(dev_viz.scene_sprites)

        result = dev_viz.handle_key_press(arcade.key.DELETE, 0)

        # Should return False (key not handled) when no selection
        assert result is False
        assert len(dev_viz.scene_sprites) == initial_count

    def test_unhandled_key_returns_false(self, window):
        """Test that unhandled keys return False."""
        dev_viz = DevVisualizer()

        result = dev_viz.handle_key_press(arcade.key.A, 0)

        assert result is False

    def test_o_key_is_unhandled(self, window):
        """O key should no longer be reserved for arrange-grid editing."""
        dev_viz = DevVisualizer()

        result = dev_viz.handle_key_press(arcade.key.O, 0)

        assert result is False
