"""Unit tests for PropertyInspectorWindow keyboard and lifecycle behaviors."""

from __future__ import annotations

import arcade
import pytest

import arcadeactions.dev.property_inspector as inspector_module
from arcadeactions.dev.property_inspector import PropertyInspectorWindow


class _InspectorStub:
    def __init__(self) -> None:
        self._selection: list[arcade.Sprite] = []
        self._moves: list[int] = []
        self._applied: list[tuple[str, str]] = []
        self._copied_current = False
        self._pasted = False
        self._undo_count = 0
        self._redo_count = 0
        self._property_values: dict[str, object] = {"is_collidable": True}

    def set_selection(self, selection):
        self._selection = list(selection)

    def selection(self):
        return list(self._selection)

    def move_active_property(self, delta: int):
        self._moves.append(delta)

    def current_property(self):
        class _Prop:
            name = "is_collidable"
            editor_type = "bool"

        return _Prop()

    def apply_property_text(self, property_name: str, text: str):
        self._applied.append((property_name, text))
        self._property_values[property_name] = text
        return True

    def property_value(self, property_name: str):
        if not self._selection:
            return None
        return self._property_values.get(property_name, None)

    def current_property_value_text(self):
        return str(self._property_values.get("is_collidable", ""))

    def copy_current_property(self):
        self._copied_current = True
        return "sprite.center_x = 100"

    def undo(self):
        self._undo_count += 1
        return True

    def redo(self):
        self._redo_count += 1
        return True

    def copy_selection_as_python(self, _property_names=None):
        return "sprite.center_x = 123"

    def visible_properties(self):
        class _Prop:
            def __init__(self, category: str, name: str):
                self.category = category
                self.name = name

        return [_Prop("Position", "center_x"), _Prop("Transform", "angle")]


@pytest.fixture(autouse=True)
def _patch_window_and_text(mocker):
    mocker.patch.object(inspector_module.arcade.Window, "__init__", return_value=None)
    mocker.patch.object(inspector_module.arcade.Window, "set_visible", return_value=None)
    mocker.patch.object(inspector_module.arcade.Window, "on_close", return_value=None)

    def make_text(*args, **kwargs):
        text = mocker.MagicMock()
        text.y = kwargs.get("y", 0)
        text.draw = mocker.MagicMock()
        return text

    mocker.patch("arcadeactions.dev.property_inspector.arcade.Text", side_effect=make_text)

    class _UIManagerStub:
        def __init__(self, window=None):
            self.window = window
            self.widgets: list[object] = []
            self.enabled = False

        def add(self, widget, **_kwargs):
            self.widgets.append(widget)
            return widget

        def draw(self):
            return None

        def enable(self):
            self.enabled = True

        def disable(self):
            self.enabled = False

    class _UIAnchorLayoutStub:
        def __init__(self):
            self.children: list[object] = []
            self.add_calls: list[dict[str, object]] = []

        def add(self, child, **_kwargs):
            self.children.append(child)
            self.add_calls.append(dict(_kwargs))
            return child

    class _UIInputTextStub:
        def __init__(self, *, width=100, height=24, text="", **_kwargs):
            self.width = width
            self.height = height
            self.text = text
            self.text_color = _kwargs.get("text_color")
            self.caret_color = _kwargs.get("caret_color")
            self.visible = True
            self.focused = False
            self.active = False
            self.caret = mocker.MagicMock()
            self.doc = mocker.MagicMock()
            self.doc.text = text

        def activate(self):
            self.active = True

        def deactivate(self):
            self.active = False

        def trigger_full_render(self):
            return None

    mocker.patch("arcadeactions.dev.property_inspector.gui.UIManager", side_effect=_UIManagerStub)
    mocker.patch("arcadeactions.dev.property_inspector.gui.UIAnchorLayout", side_effect=_UIAnchorLayoutStub)
    mocker.patch("arcadeactions.dev.property_inspector.gui.UIInputText", side_effect=_UIInputTextStub)


def _create_window(*, main_window=None, on_close_callback=None) -> tuple[PropertyInspectorWindow, _InspectorStub]:
    inspector = _InspectorStub()
    window = PropertyInspectorWindow(
        inspector=inspector,
        main_window=main_window,
        on_close_callback=on_close_callback,
    )
    window._is_headless = True
    window._headless_width = 360
    window._headless_height = 420
    window._is_visible = False
    window._width = 360
    window._height = 420
    window.clear = lambda: None
    return window, inspector


def test_set_visible_handles_missing_ui_manager_attribute(mocker):
    """set_visible should not fail if backend callbacks fire before _ui_manager exists."""
    window = object.__new__(PropertyInspectorWindow)
    window._is_headless = False
    window._is_visible = False

    window.set_visible(False)

    assert window._is_visible is False


def test_editor_widget_is_taller_and_positioned_below_value_line():
    """Editor input should be below preview text and tall enough for readable input."""
    window, _ = _create_window()
    window._is_headless = False
    if window._editor_input is None:
        window._init_editor_widget(window.width)

    assert window._editor_input is not None
    assert window._root_layout is not None
    assert window._editor_input.height == 34
    assert window._root_layout.add_calls
    add_kwargs = window._root_layout.add_calls[-1]
    assert add_kwargs["anchor_y"] == "top"
    assert add_kwargs["align_y"] == -(window.MARGIN + 68)


def test_editor_widget_uses_contrasting_text_and_caret_colors():
    """Editor input should use light text/caret on a dark input background."""
    window, _ = _create_window()
    window._is_headless = False
    if window._editor_input is None:
        window._init_editor_widget(window.width)

    assert window._editor_input is not None
    assert window._editor_input.text_color == arcade.color.WHITE
    assert window._editor_input.caret_color == arcade.color.WHITE


def test_show_and_hide_window_track_visibility():
    """Window visibility helpers should update tracked state."""
    window, _ = _create_window()

    window.show_window()
    assert window.visible is True

    window.hide_window()
    assert window.visible is False


def test_init_headless_mode_sets_expected_state():
    """Headless initialization helper should set deterministic fallback state."""
    window, _ = _create_window()

    window._init_headless_mode(320, 240, "Headless Inspector")

    assert window._is_headless is True
    assert window._headless_width == 320
    assert window._headless_height == 240
    assert window._title == "Headless Inspector"


def test_set_selection_delegates_to_inspector(test_sprite):
    """Selection updates should be delegated to the inspector model."""
    window, inspector = _create_window()

    window.set_selection([test_sprite])

    assert inspector.selection() == [test_sprite]


def test_set_selection_preserves_active_editor_text_for_same_selection(test_sprite):
    """Selection re-sync with same sprites should not overwrite in-progress edits."""
    window, inspector = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window.set_selection([test_sprite])
    window.on_key_press(arcade.key.ENTER, 0)
    window._editor_input.text = "333"

    window.set_selection([test_sprite])

    assert window._editing is True
    assert window._editor_input.text == "333"


def test_set_selection_cancels_edit_when_selection_changes(test_sprite):
    """Changing selected sprites during edit should cancel edit to prevent stale commits."""
    window, _ = _create_window()
    other_sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window.set_selection([test_sprite])
    window.on_key_press(arcade.key.ENTER, 0)
    assert window._editing is True

    window.set_selection([other_sprite])

    assert window._editing is False
    assert window._editor_input.visible is False


def test_wrapper_methods_delegate_to_inspector(test_sprite):
    """Window convenience methods should call underlying inspector methods."""
    window, inspector = _create_window()
    inspector.set_selection([test_sprite])

    assert window.apply_property_text("center_x", "123") is True
    assert window.undo() is True
    assert window.redo() is True
    snippet = window.copy_selection_as_python(["center_x"])
    assert "sprite.center_x" in snippet


def test_key_navigation_handles_up_down_and_tab():
    """Arrow/tab keys should cycle active property index."""
    window, inspector = _create_window()

    window.on_key_press(arcade.key.DOWN, 0)
    window.on_key_press(arcade.key.UP, 0)
    window.on_key_press(arcade.key.TAB, 0)
    window.on_key_press(arcade.key.TAB, arcade.key.MOD_SHIFT)

    assert inspector._moves == [1, -1, 1, -1]


def test_space_toggles_boolean_property(test_sprite):
    """Space should toggle active boolean property."""
    window, inspector = _create_window()
    test_sprite.is_collidable = True
    inspector.set_selection([test_sprite])

    window.on_key_press(arcade.key.SPACE, 0)

    assert inspector._applied == [("is_collidable", "false")]


def test_space_does_nothing_without_property_or_selection(mocker):
    """Space should no-op when current property is missing/non-bool or selection is empty."""
    window, inspector = _create_window()
    inspector.current_property = lambda: None
    window.on_key_press(arcade.key.SPACE, 0)
    assert inspector._applied == []

    class _NonBoolProp:
        name = "center_x"
        editor_type = "number"

    inspector.current_property = lambda: _NonBoolProp()
    window.on_key_press(arcade.key.SPACE, 0)
    assert inspector._applied == []

    class _BoolProp:
        name = "is_collidable"
        editor_type = "bool"

    inspector.current_property = lambda: _BoolProp()
    inspector.set_selection([])
    window.on_key_press(arcade.key.SPACE, 0)
    assert inspector._applied == []


def test_ctrl_shortcuts_delegate_to_inspector(mocker):
    """Ctrl+Z and Ctrl+Shift+Z should invoke undo/redo and not forward."""
    window, inspector = _create_window()
    forward = mocker.patch.object(window, "_forward_to_main_window")

    window.on_key_press(arcade.key.Z, arcade.key.MOD_CTRL)
    window.on_key_press(arcade.key.Z, arcade.key.MOD_CTRL | arcade.key.MOD_SHIFT)

    assert inspector._undo_count == 1
    assert inspector._redo_count == 1
    forward.assert_not_called()


def test_escape_hides_window():
    """Escape should hide the inspector window."""
    window, _ = _create_window()
    window.show_window()

    window.on_key_press(arcade.key.ESCAPE, 0)

    assert window.visible is False


def test_unhandled_key_forwards_to_main_window(mocker):
    """Unhandled keys should be forwarded to the main window."""
    main_window = mocker.MagicMock()
    window, _ = _create_window(main_window=main_window)

    window.on_key_press(arcade.key.A, 0)

    main_window.dispatch_event.assert_called_once_with("on_key_press", arcade.key.A, 0)


def test_forward_falls_back_to_main_window_handler(mocker):
    """Forwarding should fallback when dispatch_event fails."""
    main_window = mocker.MagicMock()
    main_window.dispatch_event.side_effect = RuntimeError("boom")
    window, _ = _create_window(main_window=main_window)

    window._forward_to_main_window(arcade.key.B, 0)

    main_window.on_key_press.assert_called_once_with(arcade.key.B, 0)


def test_forward_swallows_dispatch_and_fallback_failures(mocker):
    """Forward helper should swallow errors if both dispatch and fallback fail."""
    main_window = mocker.MagicMock()
    main_window.dispatch_event.side_effect = RuntimeError("dispatch boom")
    main_window.on_key_press.side_effect = RuntimeError("fallback boom")
    window, _ = _create_window(main_window=main_window)

    window._forward_to_main_window(arcade.key.C, 0)


def test_on_draw_returns_early_in_headless(mocker):
    """Headless mode should skip draw operations."""
    window, _ = _create_window()
    clear = mocker.patch.object(window, "clear")

    window.on_draw()

    clear.assert_not_called()


def test_on_draw_renders_text_rows(mocker):
    """Non-headless draw should render title and property rows."""
    window, inspector = _create_window()
    window._is_headless = False
    window._title_text = mocker.MagicMock()
    clear = mocker.patch.object(window, "clear")

    window.on_draw()

    clear.assert_called_once()
    assert window._title_text.draw.called
    assert len(inspector.visible_properties()) == 2


def test_on_draw_restores_previous_window_after_widget_draw(mocker):
    """Draw should temporarily bind inspector window and then restore prior window."""
    window, _ = _create_window()
    window._is_headless = False
    window._title_text = mocker.MagicMock()
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    manager = mocker.MagicMock()
    window._ui_manager = manager
    prior_window = mocker.MagicMock()
    mocker.patch("arcadeactions.dev.property_inspector.window_commands.get_window", return_value=prior_window)
    set_window = mocker.patch("arcadeactions.dev.property_inspector.window_commands.set_window")

    window.on_draw()

    assert set_window.call_count == 2
    assert set_window.call_args_list[0].args == (window,)
    assert set_window.call_args_list[1].args == (prior_window,)
    manager.draw.assert_called_once_with()


def test_on_draw_stops_when_rows_reach_bottom_margin(mocker):
    """Draw should stop rendering rows once bottom margin is reached."""
    window, inspector = _create_window()
    window._is_headless = False
    window._title_text = mocker.MagicMock()
    window._height = 90

    class _Prop:
        def __init__(self, i: int):
            self.category = "Category"
            self.name = f"prop_{i}"

    inspector.visible_properties = lambda: [_Prop(i) for i in range(20)]
    inspector.current_property = lambda: None
    clear = mocker.patch.object(window, "clear")

    window.on_draw()

    clear.assert_called_once()


def test_on_draw_keeps_widget_state_on_gl_error(mocker):
    """Single GL draw failures should be treated as transient and keep editing state."""
    window, _ = _create_window()
    window._is_headless = False
    window._title_text = mocker.MagicMock()
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editor_input.visible = False
    window._editing = False
    manager = mocker.MagicMock()
    manager.draw.side_effect = inspector_module.GLException("invalid operation")
    window._ui_manager = manager

    window.on_draw()

    assert window._editing is False
    assert window._ui_manager is manager
    assert window._editor_input is not None
    assert window._input_error == ""


def test_on_draw_editing_uses_widget_render_path(mocker):
    """Editing mode should still use widget render path (textbox + caret)."""
    window, _ = _create_window()
    window._is_headless = False
    window._title_text = mocker.MagicMock()
    window._value_text = mocker.MagicMock()
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="123")
    window._editor_input.visible = True
    window._editing = True
    window._ui_manager = mocker.MagicMock()
    window._ui_manager.draw.return_value = None

    window.on_draw()

    window._ui_manager.draw.assert_called_once()


def test_on_draw_keeps_ui_manager_render_while_editing(mocker):
    """Editing should still draw UI manager so widget frame remains visible."""
    window, _ = _create_window()
    window._is_headless = False
    window._title_text = mocker.MagicMock()
    window._value_text = mocker.MagicMock()
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="123")
    window._editor_input.visible = True
    window._editing = True
    window._ui_manager = mocker.MagicMock()
    window._ui_manager.draw.return_value = None

    window.on_draw()

    window._ui_manager.draw.assert_called_once()


def test_enter_reinitializes_widget_when_missing(test_sprite):
    """Enter should rebuild UI widgets if a prior draw failure removed them."""
    window, inspector = _create_window()
    window._is_headless = False
    window._ui_manager = None
    window._root_layout = None
    window._editor_input = None
    inspector.set_selection([test_sprite])

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editor_input is not None
    assert window._editing is True


def test_start_edit_reports_error_when_widget_caret_is_unavailable(test_sprite):
    """Start edit should fail gracefully if widget caret internals are unavailable."""
    window, inspector = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editor_input.caret = None
    inspector.set_selection([test_sprite])

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editing is False
    assert "Widget editing unavailable" in window._input_error


def test_on_close_invokes_callback():
    """Close should notify callback before delegating to base close."""
    called = {"value": False}

    def on_close():
        called["value"] = True

    window, _ = _create_window(on_close_callback=on_close)

    window.on_close()

    assert called["value"] is True
    assert window.is_closed is True
    assert window.visible is False


def test_set_visible_swallows_super_errors(mocker):
    """set_visible should swallow backend visibility errors."""
    window, _ = _create_window()
    window._is_headless = False
    mocker.patch.object(inspector_module.arcade.Window, "set_visible", side_effect=RuntimeError("boom"))

    window.set_visible(True)
    assert window.visible is True


def test_set_visible_enables_and_disables_ui_manager(mocker):
    """set_visible should forward enabled/disabled state to UI manager when present."""
    window, _ = _create_window()
    window._is_headless = False
    window._ui_manager = mocker.MagicMock()
    mocker.patch.object(inspector_module.arcade.Window, "set_visible", return_value=None)

    window.set_visible(True)
    window.set_visible(False)

    window._ui_manager.enable.assert_called_once_with()
    window._ui_manager.disable.assert_called_once_with()


def test_enter_starts_and_commits_edit_flow(test_sprite):
    """Enter should start editing, then commit typed text on second Enter."""
    window, inspector = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    inspector.set_selection([test_sprite])

    window.on_key_press(arcade.key.ENTER, 0)
    assert window._editing is True
    assert window._editor_input.visible is True
    assert window._editor_input.active is True
    window._editor_input.text = "456"

    window.on_key_press(arcade.key.ENTER, 0)
    assert window._editing is False
    assert window._editor_input.visible is False
    assert window._editor_input.active is False
    assert inspector._applied[-1] == ("is_collidable", "456")


def test_escape_cancels_edit_mode():
    """Escape should cancel edit mode instead of hiding window."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editing = True
    window._editor_input.visible = True

    window.on_key_press(arcade.key.ESCAPE, 0)

    assert window._editing is False
    assert window._editor_input.visible is False


class _ArrangeEditorStub:
    def __init__(self) -> None:
        self._settings = [
            ("rows", "2"),
            ("cols", "3"),
            ("start_x", "100"),
            ("start_y", "200"),
            ("spacing_x", "60"),
            ("spacing_y", "50"),
        ]
        self.set_calls: list[tuple[str, str]] = []

    def list_settings(self):
        return list(self._settings)

    def set_setting(self, name: str, value_text: str) -> bool:
        self.set_calls.append((name, value_text))
        updated: list[tuple[str, str]] = []
        for setting_name, current in self._settings:
            if setting_name == name:
                updated.append((setting_name, value_text))
            else:
                updated.append((setting_name, current))
        self._settings = updated
        return True

    def current_layout_kwargs(self):
        return {
            "rows": int(dict(self._settings)["rows"]),
            "cols": int(dict(self._settings)["cols"]),
            "start_x": float(dict(self._settings)["start_x"]),
            "start_y": float(dict(self._settings)["start_y"]),
            "spacing_x": float(dict(self._settings)["spacing_x"]),
            "spacing_y": float(dict(self._settings)["spacing_y"]),
        }


def test_arrange_mode_enter_commits_selected_setting_value():
    """Arrange mode should commit current setting text via arrange editor."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)
    window._editor_input.text = "4"
    window.on_key_press(arcade.key.ENTER, 0)

    assert editor.set_calls == [("rows", "4")]


def test_arrange_mode_enter_prefills_existing_setting_text():
    """Starting arrange edit should preload current setting value into the input widget."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editing is True
    assert window._editor_input.text == "2"


def test_arrange_mode_prefill_reapplies_widget_document_text_style():
    """Prefill should reapply readable text style to input document content."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)

    window._editor_input.doc.set_style.assert_called()


def test_prefill_styles_current_document_text_range():
    """Prefill styling should cover the full current document text range."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)

    set_style_call = window._editor_input.doc.set_style.call_args
    assert set_style_call is not None
    assert set_style_call.args[0] == 0
    assert set_style_call.args[1] == len(window._editor_input.text)


def test_set_editor_text_styles_empty_string_and_primes_caret_style():
    """Empty prefill should still prime caret style for readable newly typed text."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")

    window._set_editor_text("")

    set_style_call = window._editor_input.doc.set_style.call_args
    assert set_style_call is not None
    assert set_style_call.args[0] == 0
    assert set_style_call.args[1] == 0
    window._editor_input.caret.set_style.assert_called()


def test_set_editor_text_uses_explicit_rgba_color_in_document_style():
    """Document style should use explicit RGBA tuple for backend-consistent text color."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")

    window._set_editor_text("160")

    set_style_call = window._editor_input.doc.set_style.call_args
    assert set_style_call is not None
    style_payload = set_style_call.args[2]
    assert style_payload["color"] == (255, 255, 255, 255)
    window._editor_input.caret.set_style.assert_called_with(style_payload)


def test_set_editor_text_strips_control_characters():
    """Prefill should strip control characters from the widget text."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")

    window._set_editor_text("939.0\x00\n")

    assert window._editor_input.text == "939.0"


def test_editor_on_change_sanitizes_and_restyles_text():
    """Widget on_change hook should sanitize text and reapply readable style."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editor_input.text = "12\x00\n"

    window._on_editor_input_change(None)

    assert window._editor_input.text == "12"
    set_style_call = window._editor_input.doc.set_style.call_args
    assert set_style_call is not None
    assert set_style_call.args[1] == 2


def test_on_text_reapplies_editor_text_style_for_typed_characters(mocker):
    """Typed characters should be restyled so they stay readable on dark background."""
    window, _ = _create_window()
    window._is_headless = False
    window._editing = True
    window._mode = "properties"
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editor_input.text = "9"

    window.on_text("9")

    set_style_call = window._editor_input.doc.set_style.call_args
    assert set_style_call is not None
    assert set_style_call.args[0] == 0
    assert set_style_call.args[1] == 1


def test_start_edit_reapplies_text_style_after_widget_activation():
    """Start edit should restyle text after activation resets backend text style."""
    window, _ = _create_window()
    window._is_headless = False
    window._mode = "arrange"
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    original_activate = window._editor_input.activate

    def activate_with_style_reset():
        original_activate()
        window._editor_input.doc.set_style.reset_mock()

    window._editor_input.activate = activate_with_style_reset

    started = window._start_edit()

    assert started is True
    set_style_call = window._editor_input.doc.set_style.call_args
    assert set_style_call is not None
    assert set_style_call.args[0] == 0
    assert set_style_call.args[1] == len(window._editor_input.text)
    window._editor_input.caret.set_style.assert_called()


def test_on_text_ignores_control_character_events_during_edit():
    """Control-only text events (like Enter) should not mutate editor text/caret."""
    window, _ = _create_window()
    window._is_headless = False
    window._editing = True
    window._mode = "arrange"
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editor_input.text = "1"
    window._editor_input.caret.position = 1
    window._editor_input.caret.mark = 1

    window.on_text("\r")

    assert window._editor_input.text == "1"
    assert window._editor_input.caret.position == 1
    assert window._editor_input.caret.mark == 1


def test_start_edit_defers_caret_position_enforcement_until_draw():
    """Draw cycle should re-assert caret-at-end shortly after edit starts."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)
    assert window._editor_input.text == "2"
    assert window._pending_caret_enforce_frames == 2

    # Simulate backend/layout resetting caret to front right after start-edit.
    window._editor_input.caret.position = 0
    window._editor_input.caret.mark = 0
    window.on_draw()

    assert window._editor_input.caret.position == 1
    assert window._editor_input.caret.mark is None
    assert window._pending_caret_enforce_frames == 1


def test_arrange_mode_start_edit_places_caret_at_end_without_select_all():
    """Start edit should position caret at end without selecting entire value text."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editor_input.caret.position == len(window._editor_input.text)
    assert window._editor_input.caret.mark is None


def test_start_edit_clears_selection_anchor_to_avoid_double_backspace():
    """Caret mark should be cleared so first Backspace deletes character immediately."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editor_input.caret.position == len(window._editor_input.text)
    assert window._editor_input.caret.mark is None


def test_arrange_mode_up_down_changes_selected_setting():
    """Arrange mode navigation should move between arrange settings rows."""
    window, _ = _create_window()
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)

    window.on_key_press(arcade.key.DOWN, 0)
    window.on_key_press(arcade.key.DOWN, 0)
    window.on_key_press(arcade.key.UP, 0)

    assert window._arrange_setting_index == 1


def test_arrange_mode_commit_surfaces_apply_layout_errors():
    """Arrange mode commit should keep window alive and show apply-layout errors."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(
        editor, on_apply_layout=lambda _kwargs: (_ for _ in ()).throw(RuntimeError("layout failed"))
    )

    window.on_key_press(arcade.key.ENTER, 0)
    window._editor_input.text = "6"
    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editing is True
    assert "layout failed" in window._input_error


def test_arrange_mode_commit_ignores_widget_deactivate_errors():
    """Commit should not crash if widget deactivate fails on backend teardown."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    editor = _ArrangeEditorStub()
    window.show_arrange_mode(editor)
    window.on_key_press(arcade.key.ENTER, 0)
    window._editor_input.text = "7"

    def _raise_deactivate():
        raise RuntimeError("deactivate failed")

    window._editor_input.deactivate = _raise_deactivate

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editing is False
    assert editor.set_calls == [("rows", "7")]


def test_arrange_mode_start_edit_handles_settings_load_errors():
    """Enter should not crash when arrange settings cannot be loaded."""

    class _BrokenArrangeEditor:
        def list_settings(self):
            raise RuntimeError("arrange settings unavailable")

    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window.show_arrange_mode(_BrokenArrangeEditor())

    window.on_key_press(arcade.key.ENTER, 0)

    assert window._editing is False
    assert "arrange settings unavailable" in window._input_error


def test_arrange_mode_draw_handles_settings_load_errors():
    """Draw should keep the window alive when arrange settings fail to load."""

    class _BrokenArrangeEditor:
        def list_settings(self):
            raise RuntimeError("arrange settings unavailable")

    window, _ = _create_window()
    window._is_headless = False
    window.show_arrange_mode(_BrokenArrangeEditor())

    window.on_draw()

    assert "arrange settings unavailable" in window._input_error


def test_show_properties_mode_resets_title_and_value_text(mocker):
    """Switching back to properties mode should restore title/value labels."""
    window, _ = _create_window()
    window._title_text = mocker.MagicMock()
    window._value_text = mocker.MagicMock()
    window._mode = "arrange"
    window._arrange_editor = _ArrangeEditorStub()

    window.show_properties_mode()

    assert window._mode == "properties"
    assert window._arrange_editor is None
    assert window._title_text.text == "Sprite Properties"
    assert window._value_text.text == ""


def test_safe_arrange_settings_returns_empty_without_editor():
    """safe arrange settings should return empty list when no editor is attached."""
    window, _ = _create_window()
    window._arrange_editor = None

    assert window._safe_arrange_settings() == []


def test_enforce_pending_caret_position_resets_when_not_editing():
    """Pending caret enforcement should clear itself when editor is no longer active."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="12")
    window._editing = False
    window._pending_caret_enforce_frames = 2

    window._enforce_pending_caret_position()

    assert window._pending_caret_enforce_frames == 0


def test_start_edit_fails_when_editor_widget_missing_in_headless_mode():
    """Start edit should report unavailable-widget error when no input widget exists."""
    window, _ = _create_window()
    window._is_headless = True
    window._editor_input = None

    started = window._start_edit()

    assert started is False
    assert "Widget editing unavailable" in window._input_error


def test_start_edit_properties_mode_returns_false_without_current_property():
    """Properties mode should not enter edit state without an active property."""
    window, inspector = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    inspector.current_property = lambda: None

    assert window._start_edit() is False
    assert window._editing is False


def test_start_edit_handles_sync_exceptions():
    """Sync exceptions should surface as input_error and abort editing."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._sync_editor_text_from_selection = lambda: (_ for _ in ()).throw(RuntimeError("sync failed"))

    assert window._start_edit() is False
    assert window._editing is False
    assert "sync failed" in window._input_error


def test_start_edit_handles_activation_exceptions(test_sprite):
    """Widget activation errors should abort editing with backend-unavailable message."""
    window, inspector = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    inspector.set_selection([test_sprite])

    def _raise_activate():
        raise RuntimeError("activation failed")

    window._editor_input.activate = _raise_activate

    assert window._start_edit() is False
    assert "Widget editing unavailable" in window._input_error


def test_cancel_edit_without_editor_input_is_noop():
    """Cancel edit should no-op when widget was never initialized."""
    window, _ = _create_window()
    window._editor_input = None
    window._editing = True

    window._cancel_edit()

    assert window._editing is True


def test_commit_edit_returns_false_when_editor_widget_missing():
    """Commit should return False when no editor widget exists."""
    window, _ = _create_window()
    window._editor_input = None

    assert window._commit_edit() is False


def test_commit_edit_arrange_handles_missing_editor_and_empty_settings():
    """Arrange commit should gracefully handle missing editor or settings."""
    window, _ = _create_window()
    window._is_headless = False
    window._mode = "arrange"
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="9")
    window._arrange_editor = None
    window._editing = True
    assert window._commit_edit() is False
    assert window._editing is False

    editor = _ArrangeEditorStub()
    window._arrange_editor = editor
    window._safe_arrange_settings = lambda: []
    window._editing = True
    assert window._commit_edit() is False
    assert window._editing is False


def test_commit_edit_properties_handles_missing_current_and_apply_errors():
    """Properties commit should handle missing active property and parse/apply exceptions."""
    window, inspector = _create_window()
    window._is_headless = False
    window._mode = "properties"
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="x")
    window._editing = True
    inspector.current_property = lambda: None
    assert window._commit_edit() is False
    assert window._editing is False

    class _Prop:
        name = "is_collidable"
        editor_type = "bool"

    inspector.current_property = lambda: _Prop()
    inspector.apply_property_text = lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad value"))
    window._editing = True
    assert window._commit_edit() is False
    assert "bad value" in window._input_error


def test_deactivate_editor_widget_swallows_widget_errors():
    """Deactivation should swallow backend-specific deactivate/focus/visible errors."""
    window, _ = _create_window()
    window._is_headless = False
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")
    window._editor_input.deactivate = lambda: (_ for _ in ()).throw(RuntimeError("deactivate"))

    class _FocusRaise:
        def __setattr__(self, name, value):
            if name in ("focused", "visible"):
                raise RuntimeError("setattr fail")
            super().__setattr__(name, value)

    bad_widget = _FocusRaise()
    bad_widget.deactivate = window._editor_input.deactivate
    window._editor_input = bad_widget

    window._deactivate_editor_widget()


def test_on_text_early_returns_for_headless_and_non_editing_paths(mocker):
    """on_text should early-return in headless and non-editing routed states."""
    window, _ = _create_window(main_window=mocker.MagicMock())
    window._is_headless = True
    window.on_text("1")

    window._is_headless = False
    window._mode = "properties"
    window._editing = False
    window.on_text("2")


def test_handle_widget_draw_failure_resets_error_and_state():
    """Repeated draw failures should switch to backend failure message."""
    window, _ = _create_window()
    window._is_headless = False
    window._editing = True
    window._widget_draw_failures = 10
    window._editor_input = inspector_module.gui.UIInputText(width=120, height=24, text="")

    window._handle_widget_draw_failure()

    assert window._editing is False
    assert window._widget_draw_failures == 0
    assert "Widget draw failed" in window._input_error
