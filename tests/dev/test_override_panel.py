"""Tests for OverridesPanel to improve coverage."""

from __future__ import annotations

import pytest

from arcadeactions.dev.visualizer import DevVisualizer


@pytest.fixture
def override_panel(dev_visualizer):
    """Create an OverridesPanel instance."""
    return dev_visualizer.overrides_panel


@pytest.mark.integration
class TestOverridesPanel:
    """Test OverridesPanel class."""

    def test_override_panel_creation(self, window):
        """Test OverridesPanel can be created."""
        dev_viz = DevVisualizer()

        panel = dev_viz.overrides_panel

        assert panel is not None

    def test_override_panel_open(self, window, test_sprite):
        """Test OverridesPanel.open method."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel

        # Test opening panel with a sprite
        result = panel.open(test_sprite)

        # Should return True if opened successfully
        assert isinstance(result, bool)

    def test_override_panel_open_none(self, window):
        """Test OverridesPanel.open with None sprite."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel

        result = panel.open(None)

        assert isinstance(result, bool)

    def test_override_panel_close(self, window, test_sprite):
        """Test OverridesPanel.close method."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel

        # Open then close
        panel.open(test_sprite)
        panel.close()

        # Should not crash

    def test_override_panel_toggle(self, window, test_sprite):
        """Test OverridesPanel.toggle method."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel

        # Toggle on
        result1 = panel.toggle(test_sprite)

        # Toggle off
        result2 = panel.toggle(test_sprite)

        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_override_panel_toggle_none(self, window):
        """Test OverridesPanel.toggle with None sprite."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel

        result = panel.toggle(None)

        assert isinstance(result, bool)


@pytest.mark.integration
class TestOverridePanelIntegration:
    """Integration tests for OverridesPanel with DevVisualizer."""

    def test_override_panel_via_visualizer_open(self, window, test_sprite):
        """Test opening override panel via DevVisualizer."""
        dev_viz = DevVisualizer()
        dev_viz.attach_to_window(window)

        result = dev_viz.open_overrides_panel_for_sprite(test_sprite)

        assert isinstance(result, bool)

    def test_override_panel_via_visualizer_toggle(self, window, test_sprite):
        """Test toggling override panel via DevVisualizer."""
        dev_viz = DevVisualizer()
        dev_viz.attach_to_window(window)

        result1 = dev_viz.toggle_overrides_panel_for_sprite(test_sprite)
        result2 = dev_viz.toggle_overrides_panel_for_sprite(test_sprite)

        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_override_panel_via_visualizer_toggle_none(self, window):
        """Test toggling override panel with None sprite."""
        dev_viz = DevVisualizer()
        dev_viz.attach_to_window(window)

        result = dev_viz.toggle_overrides_panel_for_sprite(None)

        assert isinstance(result, bool)


@pytest.mark.integration
class TestOverridePanelSelection:
    """Test OverridesPanel selection and navigation."""

    @pytest.fixture
    def mock_inspector(self, mocker):
        """Create a mock ArrangeOverrideInspector."""
        inspector = mocker.Mock()
        inspector.list_overrides.return_value = [
            {"row": 0, "col": 0, "x": 100, "y": 100},
            {"row": 0, "col": 1, "x": 150, "y": 200},
            {"row": 1, "col": 0, "x": 200, "y": 300},
        ]
        return inspector

    @pytest.fixture
    def panel_with_inspector(self, window, mock_inspector):
        """Create panel with mock inspector."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        panel.inspector = mock_inspector
        panel.visible = True
        return panel

    def test_select_next_with_overrides(self, panel_with_inspector):
        """Test select_next with multiple overrides."""
        panel = panel_with_inspector
        panel._selected_index = None

        panel.select_next()

        assert panel._selected_index == 0

    def test_select_next_at_end(self, panel_with_inspector):
        """Test select_next at the end stays at end."""
        panel = panel_with_inspector
        panel._selected_index = 2  # Last index

        panel.select_next()

        assert panel._selected_index == 2  # Still at end

    def test_select_next_empty_list(self, window, mocker):
        """Test select_next with empty overrides list."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        mock_inspector = mocker.Mock()
        mock_inspector.list_overrides.return_value = []
        panel.inspector = mock_inspector

        panel.select_next()

        assert panel._selected_index is None

    def test_select_prev_with_overrides(self, panel_with_inspector):
        """Test select_prev with multiple overrides."""
        panel = panel_with_inspector
        panel._selected_index = 2

        panel.select_prev()

        assert panel._selected_index == 1

    def test_select_prev_at_start(self, panel_with_inspector):
        """Test select_prev at start stays at start."""
        panel = panel_with_inspector
        panel._selected_index = 0

        panel.select_prev()

        assert panel._selected_index == 0  # Still at start

    def test_select_prev_empty_list(self, window, mocker):
        """Test select_prev with empty overrides list."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        mock_inspector = mocker.Mock()
        mock_inspector.list_overrides.return_value = []
        panel.inspector = mock_inspector

        panel.select_prev()

        assert panel._selected_index is None

    def test_get_selected_with_valid_index(self, panel_with_inspector):
        """Test get_selected with valid selection."""
        panel = panel_with_inspector
        panel._selected_index = 1

        result = panel.get_selected()

        assert result is not None
        assert result["row"] == 0
        assert result["col"] == 1

    def test_get_selected_with_invalid_index(self, panel_with_inspector):
        """Test get_selected with invalid index."""
        panel = panel_with_inspector
        panel._selected_index = 99  # Out of range

        result = panel.get_selected()

        assert result is None

    def test_get_selected_empty_list(self, window, mocker):
        """Test get_selected with empty overrides list."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        mock_inspector = mocker.Mock()
        mock_inspector.list_overrides.return_value = []
        panel.inspector = mock_inspector

        result = panel.get_selected()

        assert result is None

    def test_get_selected_none_index(self, panel_with_inspector):
        """Test get_selected with None index."""
        panel = panel_with_inspector
        panel._selected_index = None

        result = panel.get_selected()

        assert result is None

    def test_increment_selected_x(self, panel_with_inspector, mocker):
        """Test increment_selected increments x value."""
        panel = panel_with_inspector
        panel._selected_index = 0
        mock_set = mocker.patch.object(panel, "set_override")

        panel.increment_selected(10, 0)

        mock_set.assert_called_once_with(0, 0, 110, 100)

    def test_increment_selected_y(self, panel_with_inspector, mocker):
        """Test increment_selected increments y value."""
        panel = panel_with_inspector
        panel._selected_index = 1
        mock_set = mocker.patch.object(panel, "set_override")

        panel.increment_selected(0, 20)

        mock_set.assert_called_once_with(0, 1, 150, 220)

    def test_increment_selected_no_selection(self, window, mocker):
        """Test increment_selected with no selection does nothing."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        mock_inspector = mocker.Mock()
        mock_inspector.list_overrides.return_value = []
        panel.inspector = mock_inspector
        mock_set = mocker.patch.object(panel, "set_override")

        panel.increment_selected(10, 20)

        mock_set.assert_not_called()


@pytest.mark.integration
class TestOverridePanelEditing:
    """Test OverridesPanel editing functionality."""

    @pytest.fixture
    def mock_inspector(self, mocker):
        """Create a mock ArrangeOverrideInspector."""
        inspector = mocker.Mock()
        inspector.list_overrides.return_value = [
            {"row": 0, "col": 0, "x": 100, "y": 100},
        ]
        return inspector

    @pytest.fixture
    def panel_with_inspector(self, window, mock_inspector):
        """Create panel with mock inspector."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        panel.inspector = mock_inspector
        panel.visible = True
        return panel

    def test_start_edit_with_field_validation(self, panel_with_inspector):
        """Test start_edit validates field parameter."""
        panel = panel_with_inspector
        panel._selected_index = 0

        # Valid field should work
        panel.start_edit("x")
        assert panel.editing
        assert panel._editing_field == "x"

        panel.editing = False
        panel.start_edit("y")
        assert panel.editing
        assert panel._editing_field == "y"

        # Invalid field should raise
        panel.editing = False
        with pytest.raises(ValueError, match="field must be 'x' or 'y'"):
            panel.start_edit("z")

    def test_start_edit_auto_selects_first_if_none(self, panel_with_inspector):
        """Test start_edit auto-selects first item if no selection."""
        panel = panel_with_inspector
        panel._selected_index = None

        panel.start_edit("x")

        assert panel._selected_index == 0
        assert panel.editing

    def test_start_edit_initializes_buffer_empty(self, panel_with_inspector):
        """Test start_edit initializes input buffer empty."""
        panel = panel_with_inspector
        panel._selected_index = 0

        panel.start_edit("x")

        assert panel._input_buffer == ""
        assert panel.editing

    def test_start_edit_no_overrides(self, window, mocker):
        """Test start_edit with no overrides does nothing."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        mock_inspector = mocker.Mock()
        mock_inspector.list_overrides.return_value = []
        panel.inspector = mock_inspector

        panel.start_edit("x")

        assert not panel.editing

    def test_handle_input_char_digits(self, panel_with_inspector):
        """Test handle_input_char accepts digits."""
        panel = panel_with_inspector
        panel.editing = True

        panel.handle_input_char("1")
        panel.handle_input_char("2")
        panel.handle_input_char("3")

        assert panel._input_buffer == "123"

    def test_handle_input_char_comma_minus(self, panel_with_inspector):
        """Test handle_input_char accepts comma and minus."""
        panel = panel_with_inspector
        panel.editing = True

        panel.handle_input_char("-")
        panel.handle_input_char("5")
        panel.handle_input_char(",")
        panel.handle_input_char("1")
        panel.handle_input_char("0")

        assert panel._input_buffer == "-5,10"

    def test_handle_input_char_backspace(self, panel_with_inspector):
        """Test handle_input_char handles backspace."""
        panel = panel_with_inspector
        panel.editing = True
        panel._input_buffer = "123"

        panel.handle_input_char("\b")

        assert panel._input_buffer == "12"

    def test_handle_input_char_not_editing(self, panel_with_inspector):
        """Test handle_input_char does nothing when not editing."""
        panel = panel_with_inspector
        panel.editing = False

        panel.handle_input_char("5")

        assert panel._input_buffer == ""

    def test_handle_input_char_filters_invalid(self, panel_with_inspector):
        """Test handle_input_char filters invalid characters."""
        panel = panel_with_inspector
        panel.editing = True

        panel.handle_input_char("a")  # Should be ignored
        panel.handle_input_char("5")  # Should be accepted
        panel.handle_input_char("!")  # Should be ignored
        panel.handle_input_char(",")  # Should be accepted

        assert panel._input_buffer == "5,"

    def test_commit_edit_single_value_x(self, panel_with_inspector, mocker):
        """Test commit_edit with single value (x only)."""
        panel = panel_with_inspector
        panel._selected_index = 0
        panel.editing = True
        panel._editing_field = "x"
        panel._input_buffer = "250"
        mock_set = mocker.patch.object(panel, "set_override")

        panel.commit_edit()

        # Should keep existing y, set new x
        mock_set.assert_called_once_with(0, 0, 250, 100)
        assert not panel.editing
        assert panel._input_buffer == ""

    def test_commit_edit_two_values_xy(self, panel_with_inspector, mocker):
        """Test commit_edit with two values (x,y)."""
        panel = panel_with_inspector
        panel._selected_index = 0
        panel.editing = True
        panel._input_buffer = "300,400"
        mock_set = mocker.patch.object(panel, "set_override")

        panel.commit_edit()

        mock_set.assert_called_once_with(0, 0, 300, 400)
        assert not panel.editing

    def test_commit_edit_empty_buffer(self, panel_with_inspector, mocker):
        """Test commit_edit with empty buffer."""
        panel = panel_with_inspector
        panel._selected_index = 0
        panel.editing = True
        panel._input_buffer = ""
        mock_set = mocker.patch.object(panel, "set_override")

        panel.commit_edit()

        # Empty buffer causes ValueError, so set_override should not be called
        mock_set.assert_not_called()
        assert not panel.editing
        assert panel._input_buffer == ""

    def test_commit_edit_parse_error(self, panel_with_inspector, mocker):
        """Test commit_edit handles parse errors gracefully."""
        panel = panel_with_inspector
        panel._selected_index = 0
        panel.editing = True
        panel._input_buffer = "not_a_number"
        mock_set = mocker.patch.object(panel, "set_override")

        panel.commit_edit()

        # Should cancel edit without calling set_override
        mock_set.assert_not_called()
        assert not panel.editing
        assert panel._input_buffer == ""

    def test_commit_edit_partial_comma(self, panel_with_inspector, mocker):
        """Test commit_edit with partial comma (x,)."""
        panel = panel_with_inspector
        panel._selected_index = 0
        panel.editing = True
        panel._input_buffer = "250,"
        mock_set = mocker.patch.object(panel, "set_override")

        panel.commit_edit()

        # Should set x=250, y=0
        mock_set.assert_called_once_with(0, 0, 250, 0)
        assert not panel.editing

    def test_cancel_edit(self, panel_with_inspector):
        """Test cancel_edit resets editing state."""
        panel = panel_with_inspector
        panel.editing = True
        panel._input_buffer = "123"
        panel._editing_field = "x"

        panel.cancel_edit()

        assert not panel.editing
        assert panel._input_buffer == ""

    def test_commit_edit_not_editing(self, panel_with_inspector, mocker):
        """Test commit_edit does nothing when not editing."""
        panel = panel_with_inspector
        panel.editing = False
        mock_set = mocker.patch.object(panel, "set_override")

        panel.commit_edit()

        mock_set.assert_not_called()


@pytest.mark.integration
class TestOverridePanelDrawing:
    """Test OverridesPanel drawing functionality."""

    @pytest.fixture
    def mock_inspector(self, mocker):
        """Create a mock ArrangeOverrideInspector."""
        inspector = mocker.Mock()
        inspector.list_overrides.return_value = [
            {"row": 0, "col": 0, "x": 100, "y": 100},
            {"row": 0, "col": 1, "x": 150, "y": 200},
        ]
        return inspector

    @pytest.fixture
    def mock_window(self, mocker):
        """Create a mock window."""
        win = mocker.Mock()
        win.width = 800
        win.height = 600
        return win

    def test_draw_not_visible(self, window, mock_inspector, mock_window, mocker):
        """Test draw does nothing when not visible."""
        mock_draw_rect = mocker.patch("arcade.draw_lbwh_rectangle_filled", create=True)
        mock_draw_text = mocker.patch("arcade.draw_text", create=True)

        dev_viz = DevVisualizer()
        dev_viz.window = mock_window
        panel = dev_viz.overrides_panel
        panel.inspector = mock_inspector
        panel.visible = False

        # Should return early without drawing
        panel.draw()

        mock_draw_rect.assert_not_called()
        mock_draw_text.assert_not_called()

    def test_draw_no_inspector(self, window, mock_window, mocker):
        """Test draw does nothing when no inspector."""
        mock_draw_rect = mocker.patch("arcade.draw_lbwh_rectangle_filled", create=True)
        mock_draw_text = mocker.patch("arcade.draw_text", create=True)

        dev_viz = DevVisualizer()
        dev_viz.window = mock_window
        panel = dev_viz.overrides_panel
        panel.inspector = None
        panel.visible = True

        # Should return early without drawing
        panel.draw()

        mock_draw_rect.assert_not_called()
        mock_draw_text.assert_not_called()

    def test_draw_visible_renders_rows_and_edit_state(self, window, mock_inspector, mock_window, mocker):
        """Test draw renders rows and edit buffer when panel is visible."""
        mock_draw_rect = mocker.patch("arcade.draw_lbwh_rectangle_filled", create=True)
        mock_draw_text = mocker.patch("arcade.draw_text", create=True)

        dev_viz = DevVisualizer()
        dev_viz.window = mock_window
        panel = dev_viz.overrides_panel
        panel.inspector = mock_inspector
        panel.visible = True
        panel._selected_index = 0
        panel.editing = True
        panel._editing_field = "x"
        panel._input_buffer = "123,456"

        panel.draw()

        assert mock_draw_rect.called
        assert mock_draw_text.called
        draw_calls = [call.args[0] for call in mock_draw_text.call_args_list if call.args]
        assert "Overrides" in draw_calls[0]
        assert any("Edit:" in text for text in draw_calls)


@pytest.mark.integration
class TestOverridePanelKeyboard:
    """Test OverridesPanel keyboard handling."""

    @pytest.fixture
    def mock_inspector(self, mocker):
        """Create a mock ArrangeOverrideInspector with undo."""
        inspector = mocker.Mock()
        inspector.list_overrides.return_value = [
            {"row": 0, "col": 0, "x": 100, "y": 100},
        ]
        inspector.undo.return_value = True
        return inspector

    @pytest.fixture
    def panel_with_inspector(self, window, mock_inspector):
        """Create panel with mock inspector."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        panel.inspector = mock_inspector
        panel.visible = True
        panel._selected_index = 1  # Set to index that will need adjustment
        return panel

    def test_handle_key_ctrl_z_with_undo(self, panel_with_inspector):
        """Test handle_key with Ctrl+Z calls undo."""
        panel = panel_with_inspector

        panel.handle_key("CTRL+Z")

        panel.inspector.undo.assert_called_once()

    def test_handle_key_ctrl_z_no_inspector(self, window):
        """Test handle_key with Ctrl+Z when no inspector."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        panel.inspector = None

        # Should not crash
        panel.handle_key("CTRL+Z")

    def test_handle_key_ctrl_z_selection_adjustment(self, panel_with_inspector):
        """Test handle_key adjusts selection after undo."""
        panel = panel_with_inspector
        panel._selected_index = 2  # Out of bounds after undo removes items

        panel.handle_key("CTRL+Z")

        # Selection should be adjusted to valid range
        assert panel._selected_index is not None
        assert panel._selected_index <= 0  # Should be clamped to available items

    def test_handle_key_other_key(self, panel_with_inspector):
        """Test handle_key with other key does nothing."""
        panel = panel_with_inspector
        initial_selection = panel._selected_index

        panel.handle_key("SPACE")

        # Should not change selection
        assert panel._selected_index == initial_selection


@pytest.mark.integration
class TestOverridePanelErrors:
    """Test OverridesPanel error handling."""

    def test_set_override_when_not_open(self, window):
        """Test set_override raises RuntimeError when not open."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        panel.inspector = None

        with pytest.raises(RuntimeError, match="OverridesPanel is not open"):
            panel.set_override(0, 0, 100, 200)

    def test_remove_override_when_not_open(self, window):
        """Test remove_override raises RuntimeError when not open."""
        dev_viz = DevVisualizer()
        panel = dev_viz.overrides_panel
        panel.inspector = None

        with pytest.raises(RuntimeError, match="OverridesPanel is not open"):
            panel.remove_override(0, 0)
