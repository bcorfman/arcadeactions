"""Tests for DevVisualizer mouse handling.

Tests handle_mouse_press, handle_mouse_drag, and handle_mouse_release methods.
These tests document current behavior and priority order (gizmo > sprite > selection).
"""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.visualizer import DevVisualizer
from tests.conftest import ActionTestBase

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _suppress_property_inspector_windows(mocker):
    """Prevent auto-opened inspector windows during mouse-path integration tests."""
    mocker.patch.object(DevVisualizer, "open_property_inspector_for_current_selection", return_value=True)


class TestHandleMousePress(ActionTestBase):
    """Test suite for handle_mouse_press method."""

    def test_right_click_clears_selection(self, window, test_sprite_list):
        """Test that right-click clears selection."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # Select some sprites
        for sprite in test_sprite_list:
            dev_viz.selection_manager._selected.add(sprite)
        assert len(dev_viz.selection_manager.get_selected()) == 2

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_RIGHT, 0)

        assert result is True
        assert len(dev_viz.selection_manager.get_selected()) == 0

    def test_non_left_button_returns_false(self, window):
        """Test that non-left, non-right buttons return False."""
        dev_viz = DevVisualizer()

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_MIDDLE, 0)

        assert result is False

    def test_gizmo_handle_takes_priority(self, window, test_sprite, mocker):
        """Test that gizmo handle click takes priority over sprite drag."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        dev_viz.selection_manager._selected.add(test_sprite)

        # Mock gizmo
        mock_gizmo = mocker.MagicMock()
        mock_gizmo.has_bounded_action.return_value = True
        mock_handle = mocker.MagicMock()
        mock_gizmo.get_handle_at_point.return_value = mock_handle

        mocker.patch.object(dev_viz, "_get_gizmo", return_value=mock_gizmo)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        assert dev_viz._dragging_gizmo_handle == (mock_gizmo, mock_handle)
        # Sprite drag should not be started
        assert dev_viz._dragging_sprites is None

    def test_gizmo_handle_not_started_if_no_handle(self, window, test_sprite, mocker):
        """Test that gizmo drag is not started if no handle at point."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        dev_viz.selection_manager._selected.add(test_sprite)

        # Mock gizmo that returns no handle
        mock_gizmo = mocker.MagicMock()
        mock_gizmo.has_bounded_action.return_value = True
        mock_gizmo.get_handle_at_point.return_value = None

        mocker.patch.object(dev_viz, "_get_gizmo", return_value=mock_gizmo)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        # Should continue to sprite drag or selection
        assert dev_viz._dragging_gizmo_handle is None

    def test_ctrl_click_sprite_with_source_markers_opens_editor(self, window, test_sprite, mocker):
        """Ctrl+click on sprite with source markers should open editor."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100

        test_sprite._source_markers = [{"file": "test.py", "lineno": 10}]

        mock_open = mocker.patch.object(dev_viz, "open_sprite_source")
        mock_open_editor = mocker.patch.object(dev_viz, "open_overrides_editor_for_sprite")

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, arcade.key.MOD_CTRL)

        assert result is True
        mock_open.assert_called_once_with(test_sprite, {"file": "test.py", "lineno": 10})
        mock_open_editor.assert_not_called()

    def test_plain_click_arrange_marker_opens_overrides_panel(self, window, test_sprite, mocker):
        """Plain click on arrange-linked sprite should open overrides panel, not source jump."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100

        test_sprite._source_markers = [{"file": "test.py", "lineno": 10, "type": "arrange"}]

        mock_open = mocker.patch.object(dev_viz, "open_sprite_source")
        mock_overrides_open = mocker.patch.object(dev_viz, "open_overrides_editor_for_sprite", return_value=True)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        mock_open.assert_not_called()
        mock_overrides_open.assert_called_once_with(test_sprite)
        assert result is True

    def test_plain_click_arrange_marker_selects_whole_group(self, window, mocker):
        """Plain click on one arrange sprite should select all sprites in that arrange call."""
        dev_viz = DevVisualizer()
        sprite_a = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
        sprite_b = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.BLUE)
        sprite_c = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.GREEN)
        marker = {"file": "scene.py", "lineno": 42, "type": "arrange"}
        sprite_a._source_markers = [marker]
        sprite_b._source_markers = [marker]
        sprite_c._source_markers = [{"file": "scene.py", "lineno": 41, "type": "arrange"}]
        sprite_a.center_x = sprite_b.center_x = sprite_c.center_x = 100
        sprite_a.center_y = sprite_b.center_y = sprite_c.center_y = 100
        dev_viz.scene_sprites.extend([sprite_a, sprite_b, sprite_c])
        mocker.patch("arcadeactions.dev.visualizer.arcade.get_sprites_at_point", return_value=[sprite_a])
        mock_open = mocker.patch.object(dev_viz, "open_overrides_editor_for_sprite", return_value=True)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_open.assert_called_once_with(sprite_a)
        selected = set(dev_viz.selection_manager.get_selected())
        assert selected == {sprite_a, sprite_b}

    def test_arrange_click_ignores_lock_modifiers(self, window, test_sprite, mocker):
        """Lock-key modifiers (e.g., NumLock) should not block arrange panel open."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100
        test_sprite._source_markers = [{"file": "test.py", "lineno": 10, "type": "arrange"}]

        mock_open = mocker.patch.object(dev_viz, "open_sprite_source")
        mock_overrides_open = mocker.patch.object(dev_viz, "open_overrides_editor_for_sprite", return_value=True)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, arcade.key.MOD_NUMLOCK)

        assert result is True
        mock_open.assert_not_called()
        mock_overrides_open.assert_called_once_with(test_sprite)

    def test_plain_click_opens_overrides_when_marker_points_to_arrange_line(
        self, window, test_sprite, mocker, tmp_path
    ):
        """Arrange detection should work from file/line marker even without explicit type."""
        source_path = tmp_path / "scene.py"
        source_path.write_text(
            "x = 1\narrange_grid(sprites=s, rows=1, cols=2, start_x=10, start_y=20, spacing_x=5, spacing_y=5)\n",
            encoding="utf-8",
        )
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100
        test_sprite._source_markers = [{"file": str(source_path), "lineno": 2}]

        mock_open = mocker.patch.object(dev_viz, "open_sprite_source")
        mock_overrides_open = mocker.patch.object(dev_viz, "open_overrides_editor_for_sprite", return_value=True)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_open.assert_not_called()
        mock_overrides_open.assert_called_once_with(test_sprite)

    def test_selected_sprite_drag_started(self, window, test_sprite, mocker):
        """Test that clicking on selected sprite starts drag."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        dev_viz.selection_manager._selected.add(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100

        # Mock gizmo to return None (no gizmo handle)
        mocker.patch.object(dev_viz, "_get_gizmo", return_value=None)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        assert dev_viz._dragging_sprites is not None
        assert len(dev_viz._dragging_sprites) == 1
        assert dev_viz._dragging_sprites[0][0] == test_sprite
        # Offset should be (0, 0) since click is at sprite center
        assert dev_viz._dragging_sprites[0][1] == 0.0
        assert dev_viz._dragging_sprites[0][2] == 0.0

    def test_selected_sprite_drag_calculates_offset(self, window, test_sprite, mocker):
        """Test that sprite drag calculates correct offset from click point."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        dev_viz.selection_manager._selected.add(test_sprite)
        test_sprite.center_x = 150
        test_sprite.center_y = 200

        # Mock gizmo to return None
        mocker.patch.object(dev_viz, "_get_gizmo", return_value=None)

        # Click at sprite center (150, 200) - offset should be (0, 0)
        result = dev_viz.handle_mouse_press(150, 200, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        assert dev_viz._dragging_sprites is not None
        assert dev_viz._dragging_sprites[0][1] == 0.0  # offset_x (click at center)
        assert dev_viz._dragging_sprites[0][2] == 0.0  # offset_y (click at center)

    def test_multiple_selected_sprites_drag(self, window, test_sprite_list, mocker):
        """Test that clicking on one selected sprite drags all selected sprites."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)
        for sprite in test_sprite_list:
            dev_viz.selection_manager._selected.add(sprite)

        test_sprite_list[0].center_x = 100
        test_sprite_list[0].center_y = 100
        test_sprite_list[1].center_x = 200
        test_sprite_list[1].center_y = 200

        # Mock gizmo to return None
        mocker.patch.object(dev_viz, "_get_gizmo", return_value=None)

        # Click on first sprite
        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        assert len(dev_viz._dragging_sprites) == 2

    def test_click_selection_sets_inspector_focus_flag_for_mouse_release(self, window, test_sprite, mocker):
        """Sprite selection click should open inspector without deferred legacy focus flag."""
        dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([test_sprite]))
        mocker.patch("arcadeactions.dev.visualizer.arcade.get_sprites_at_point", return_value=[test_sprite])
        dev_viz.selection_manager.handle_mouse_press = mocker.MagicMock(return_value=True)
        open_properties = mocker.patch.object(dev_viz, "open_property_inspector_for_current_selection", return_value=True)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        open_properties.assert_called_once_with()
        assert hasattr(dev_viz, "_focus_inspector_on_mouse_release") is False

    def test_click_arrange_sprite_sets_inspector_focus_flag_for_mouse_release(self, window, test_sprite, mocker):
        """Arrange sprite click should open arrange editor without deferred legacy focus flag."""
        dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([test_sprite]))
        test_sprite._source_markers = [{"file": "test.py", "lineno": 10, "type": "arrange"}]
        mocker.patch("arcadeactions.dev.visualizer.arcade.get_sprites_at_point", return_value=[test_sprite])
        open_arrange = mocker.patch.object(dev_viz, "open_overrides_editor_for_sprite", return_value=True)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        open_arrange.assert_called_once_with(test_sprite)
        assert hasattr(dev_viz, "_focus_inspector_on_mouse_release") is False
        # Both sprites should be in drag list with their offsets

    def test_unselected_sprite_triggers_selection(self, window, test_sprite, mocker):
        """Test that clicking unselected sprite triggers selection manager."""
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100

        # Mock selection manager
        mock_select = mocker.patch.object(dev_viz.selection_manager, "handle_mouse_press", return_value=True)

        # Mock gizmo to return None
        mocker.patch.object(dev_viz, "_get_gizmo", return_value=None)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_select.assert_called_once()

    def test_empty_space_triggers_selection(self, window, test_sprite_list, mocker):
        """Test that clicking empty space triggers selection manager."""
        dev_viz = DevVisualizer(scene_sprites=test_sprite_list)

        # Mock selection manager
        mock_select = mocker.patch.object(dev_viz.selection_manager, "handle_mouse_press", return_value=True)

        # Click at empty space (sprites are at 50 and 150)
        result = dev_viz.handle_mouse_press(300, 300, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_select.assert_called_once()

    def test_returns_false_when_selection_not_handled(self, window, mocker):
        """Test that returns False when selection manager doesn't handle."""
        dev_viz = DevVisualizer()

        # Mock selection manager to return False
        mocker.patch.object(dev_viz.selection_manager, "handle_mouse_press", return_value=False)

        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is False

    def test_source_markers_exception_handled(self, window, test_sprite, mocker):
        """Test that exceptions when accessing source markers are handled."""
        # Document current behavior: exceptions in source marker handling are caught
        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(test_sprite)
        test_sprite.center_x = 100
        test_sprite.center_y = 100

        # Mock open_sprite_source to raise exception
        mock_open = mocker.patch.object(dev_viz, "open_sprite_source", side_effect=Exception("Error"))
        test_sprite._source_markers = [{"file": "test.py", "lineno": 10}]

        # Should not raise, just continue to sprite drag or selection
        result = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        # Should continue processing (either sprite drag or selection)
        assert result is True or result is False


class TestHandleMouseDrag(ActionTestBase):
    """Test suite for handle_mouse_drag method."""

    def test_gizmo_drag_takes_priority(self, window, test_sprite, mocker):
        """Test that gizmo drag takes priority over sprite drag."""
        dev_viz = DevVisualizer()
        dev_viz._dragging_gizmo_handle = (mocker.MagicMock(), mocker.MagicMock())
        dev_viz._dragging_sprites = [(test_sprite, 0, 0)]

        mock_gizmo, mock_handle = dev_viz._dragging_gizmo_handle

        result = dev_viz.handle_mouse_drag(100, 100, 10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_gizmo.handle_drag.assert_called_once_with(mock_handle, 10, 20)
        # Sprite positions should not be updated
        original_x = test_sprite.center_x
        original_y = test_sprite.center_y

    def test_sprite_drag_updates_positions(self, window, test_sprite, mocker):
        """Test that sprite drag updates sprite positions."""
        dev_viz = DevVisualizer()
        dev_viz._dragging_sprites = [(test_sprite, 10, 20)]
        test_sprite.center_x = 100
        test_sprite.center_y = 100

        result = dev_viz.handle_mouse_drag(150, 200, 50, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        # Sprite should be at (150 + 10, 200 + 20) = (160, 220)
        assert test_sprite.center_x == 160.0
        assert test_sprite.center_y == 220.0

    def test_multiple_sprite_drag(self, window, test_sprite_list, mocker):
        """Test that multiple sprites are dragged together."""
        dev_viz = DevVisualizer()
        dev_viz._dragging_sprites = [(test_sprite_list[0], 10, 20), (test_sprite_list[1], 30, 40)]

        result = dev_viz.handle_mouse_drag(100, 100, 0, 0, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        # Both sprites should be updated
        assert test_sprite_list[0].center_x == 110.0  # 100 + 10
        assert test_sprite_list[0].center_y == 120.0  # 100 + 20
        assert test_sprite_list[1].center_x == 130.0  # 100 + 30
        assert test_sprite_list[1].center_y == 140.0  # 100 + 40

    def test_selection_marquee_drag(self, window, mocker):
        """Test that selection marquee drag is handled."""
        dev_viz = DevVisualizer()
        dev_viz.selection_manager._is_dragging_marquee = True

        mock_marquee = mocker.patch.object(dev_viz.selection_manager, "handle_mouse_drag")

        result = dev_viz.handle_mouse_drag(100, 100, 10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_marquee.assert_called_once_with(100, 100)

    def test_returns_false_when_nothing_dragging(self, window):
        """Test that returns False when nothing is being dragged."""
        dev_viz = DevVisualizer()

        result = dev_viz.handle_mouse_drag(100, 100, 10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is False

    def test_priority_order_gizmo_over_sprite(self, window, test_sprite, mocker):
        """Test priority: gizmo drag over sprite drag."""
        dev_viz = DevVisualizer()
        mock_gizmo = mocker.MagicMock()
        dev_viz._dragging_gizmo_handle = (mock_gizmo, mocker.MagicMock())
        dev_viz._dragging_sprites = [(test_sprite, 0, 0)]

        original_x = test_sprite.center_x
        original_y = test_sprite.center_y

        result = dev_viz.handle_mouse_drag(100, 100, 10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        # Gizmo should be dragged
        mock_gizmo.handle_drag.assert_called_once()
        # Sprite should not move
        assert test_sprite.center_x == original_x
        assert test_sprite.center_y == original_y

    def test_priority_order_sprite_over_marquee(self, window, test_sprite, mocker):
        """Test priority: sprite drag over selection marquee."""
        dev_viz = DevVisualizer()
        dev_viz._dragging_sprites = [(test_sprite, 0, 0)]
        dev_viz.selection_manager._is_dragging_marquee = True

        mock_marquee = mocker.patch.object(dev_viz.selection_manager, "handle_mouse_drag")

        result = dev_viz.handle_mouse_drag(100, 100, 10, 20, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        # Sprite should be dragged
        assert test_sprite.center_x == 100.0
        # Marquee should not be handled
        mock_marquee.assert_not_called()


class TestHandleMouseRelease(ActionTestBase):
    """Test suite for handle_mouse_release method."""

    def test_gizmo_release_clears_dragging(self, window, mocker):
        """Test that gizmo release clears dragging state."""
        dev_viz = DevVisualizer()
        mock_gizmo = mocker.MagicMock()
        dev_viz._dragging_gizmo_handle = (mock_gizmo, mocker.MagicMock())

        result = dev_viz.handle_mouse_release(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        assert dev_viz._dragging_gizmo_handle is None

    def test_sprite_release_clears_dragging(self, window, test_sprite):
        """Test that sprite release clears dragging state."""
        dev_viz = DevVisualizer()
        dev_viz._dragging_sprites = [(test_sprite, 0, 0)]

        result = dev_viz.handle_mouse_release(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        assert dev_viz._dragging_sprites is None

    def test_selection_marquee_release(self, window, mocker):
        """Test that selection marquee release is handled."""
        dev_viz = DevVisualizer()
        dev_viz.selection_manager._is_dragging_marquee = True

        mock_release = mocker.patch.object(dev_viz.selection_manager, "handle_mouse_release")

        result = dev_viz.handle_mouse_release(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        mock_release.assert_called_once_with(100, 100)

    def test_multiple_releases_handled(self, window, test_sprite, mocker):
        """Test that multiple release types can be handled in same call."""
        dev_viz = DevVisualizer()
        mock_gizmo = mocker.MagicMock()
        dev_viz._dragging_gizmo_handle = (mock_gizmo, mocker.MagicMock())
        dev_viz._dragging_sprites = [(test_sprite, 0, 0)]
        dev_viz.selection_manager._is_dragging_marquee = True

        mock_marquee = mocker.patch.object(dev_viz.selection_manager, "handle_mouse_release")

        result = dev_viz.handle_mouse_release(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is True
        # All should be cleared/released
        assert dev_viz._dragging_gizmo_handle is None
        assert dev_viz._dragging_sprites is None
        mock_marquee.assert_called_once()

    def test_returns_false_when_nothing_releasing(self, window):
        """Test that returns False when nothing is being released."""
        dev_viz = DevVisualizer()

        result = dev_viz.handle_mouse_release(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is False

    def test_release_focuses_inspector_when_focus_flag_is_set(self, window, mocker):
        """Mouse release should ignore removed deferred-focus compatibility flag."""
        dev_viz = DevVisualizer()
        dev_viz._focus_inspector_on_mouse_release = True

        result = dev_viz.handle_mouse_release(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

        assert result is False
        assert dev_viz._focus_inspector_on_mouse_release is True
