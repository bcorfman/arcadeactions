"""Unit tests for window-free DevShell property inspector panel behavior."""

from __future__ import annotations

import arcade

from arcadeactions.dev.devshell_property_inspector_panel import DevShellPropertyInspectorPanel


class _Prop:
    def __init__(self, name: str, editor_type: str) -> None:
        self.name = name
        self.editor_type = editor_type
        self.category = "Test"


class _InspectorStub:
    def __init__(self) -> None:
        self._selection: list[arcade.Sprite] = []
        self._props = [_Prop("center_x", "number"), _Prop("is_collidable", "bool")]
        self._index = 0
        self.applied: list[tuple[str, str]] = []
        self.undo_calls = 0
        self.redo_calls = 0
        self.values = {"center_x": "100", "is_collidable": True}

    def set_selection(self, selection):
        self._selection = list(selection)

    def current_property(self):
        return self._props[self._index]

    def current_property_value_text(self) -> str:
        current = self.current_property()
        value = self.values[current.name]
        return str(value)

    def move_active_property(self, delta: int):
        self._index = (self._index + delta) % len(self._props)

    def apply_property_text(self, property_name: str, text: str) -> bool:
        self.applied.append((property_name, text))
        self.values[property_name] = text
        return True

    def property_value(self, property_name: str):
        return self.values[property_name]

    def undo(self) -> bool:
        self.undo_calls += 1
        return True

    def redo(self) -> bool:
        self.redo_calls += 1
        return True


class _ArrangeEditorStub:
    def __init__(self) -> None:
        self.settings = [
            ("rows", "1"),
            ("cols", "2"),
            ("start_x", "10"),
            ("start_y", "20"),
            ("spacing_x", "5"),
            ("spacing_y", "5"),
        ]
        self.applied: list[tuple[str, str]] = []

    def list_settings(self):
        return list(self.settings)

    def set_setting(self, name: str, value_text: str) -> bool:
        self.applied.append((name, value_text))
        self.settings = [(setting, value_text if setting == name else value) for setting, value in self.settings]
        return True

    def current_layout_kwargs(self):
        values = dict(self.settings)
        return {
            "rows": int(values["rows"]),
            "cols": int(values["cols"]),
            "start_x": float(values["start_x"]),
            "start_y": float(values["start_y"]),
            "spacing_x": float(values["spacing_x"]),
            "spacing_y": float(values["spacing_y"]),
        }


def test_enter_starts_and_commits_edit():
    """Enter should start edit mode, then commit buffered text on second Enter."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)

    assert panel.handle_key_press(arcade.key.ENTER, 0) is True
    assert panel.editing is True
    assert panel.text_buffer.text == "100"

    panel.handle_text("2")
    assert panel.text_buffer.text == "1002"

    assert panel.handle_key_press(arcade.key.ENTER, 0) is True
    assert panel.editing is False
    assert inspector.applied[-1] == ("center_x", "1002")


def test_escape_cancels_edit_before_hiding_panel():
    """Esc should cancel active edit first, then hide when not editing."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)
    panel.handle_key_press(arcade.key.ENTER, 0)

    assert panel.editing is True
    assert panel.handle_key_press(arcade.key.ESCAPE, 0) is True
    assert panel.editing is False
    assert panel.visible is True

    assert panel.handle_key_press(arcade.key.ESCAPE, 0) is True
    assert panel.visible is False


def test_ctrl_z_and_ctrl_shift_z_delegate_to_history():
    """Undo/redo shortcuts should delegate to inspector history methods."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)

    assert panel.handle_key_press(arcade.key.Z, arcade.key.MOD_CTRL) is True
    assert panel.handle_key_press(arcade.key.Z, arcade.key.MOD_CTRL | arcade.key.MOD_SHIFT) is True

    assert inspector.undo_calls == 1
    assert inspector.redo_calls == 1


def test_navigation_keys_move_active_property_when_not_editing():
    """Up/Down/Tab should navigate property selection outside text-edit mode."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)

    assert inspector.current_property().name == "center_x"
    panel.handle_key_press(arcade.key.DOWN, 0)
    assert inspector.current_property().name == "is_collidable"
    panel.handle_key_press(arcade.key.UP, 0)
    assert inspector.current_property().name == "center_x"
    panel.handle_key_press(arcade.key.TAB, 0)
    assert inspector.current_property().name == "is_collidable"


def test_space_toggles_boolean_property():
    """Space should toggle bool properties when active property is bool."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)
    inspector._index = 1  # is_collidable

    assert panel.handle_key_press(arcade.key.SPACE, 0) is True
    assert inspector.applied[-1] == ("is_collidable", "false")


def test_text_is_ignored_when_not_editing():
    """Panel text input should only apply while in editing mode."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)

    assert panel.handle_text("9") is False

    panel.handle_key_press(arcade.key.ENTER, 0)
    assert panel.handle_text("9") is True
    assert panel.text_buffer.text.endswith("9")


def test_editing_motion_keys_mutate_text_buffer():
    """Backspace/delete/home/end/left/right should mutate buffer in edit mode."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)
    panel.handle_key_press(arcade.key.ENTER, 0)

    before = panel.text_buffer.text
    panel.handle_key_press(arcade.key.LEFT, 0)
    panel.handle_key_press(arcade.key.BACKSPACE, 0)
    panel.handle_key_press(arcade.key.END, 0)
    panel.handle_key_press(arcade.key.DELETE, 0)

    assert panel.text_buffer.text != before


def test_hidden_panel_does_not_consume_input():
    """When hidden, panel should not consume key or text events."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)

    assert panel.handle_key_press(arcade.key.ENTER, 0) is False
    assert panel.handle_text("1") is False


def test_router_adapter_methods_delegate_to_panel_handlers():
    """Panel should expose router-compatible on_* methods."""
    inspector = _InspectorStub()
    panel = DevShellPropertyInspectorPanel(inspector=inspector)
    panel.set_visible(True)
    panel.on_key_press(arcade.key.ENTER, 0)

    assert panel.on_text("7") is True
    assert panel.on_text_motion(arcade.key.MOTION_LEFT) is True
    assert panel.on_text_motion(arcade.key.MOTION_BACKSPACE) is True


def test_edit_state_callbacks_fire_on_enter_and_exit():
    """Panel should notify coordinator focus ownership on edit start/end."""
    inspector = _InspectorStub()
    events: list[str] = []
    panel = DevShellPropertyInspectorPanel(
        inspector=inspector,
        on_edit_start=lambda: events.append("start"),
        on_edit_end=lambda: events.append("end"),
    )
    panel.set_visible(True)

    assert panel.handle_key_press(arcade.key.ENTER, 0) is True
    assert events == ["start"]

    assert panel.handle_key_press(arcade.key.ESCAPE, 0) is True
    assert events == ["start", "end"]


def test_hiding_panel_ends_edit_ownership_when_editing():
    """Visibility off should end edit ownership when panel was editing."""
    inspector = _InspectorStub()
    events: list[str] = []
    panel = DevShellPropertyInspectorPanel(
        inspector=inspector,
        on_edit_start=lambda: events.append("start"),
        on_edit_end=lambda: events.append("end"),
    )
    panel.set_visible(True)
    panel.handle_key_press(arcade.key.ENTER, 0)
    assert panel.editing is True

    panel.set_visible(False)

    assert panel.editing is False
    assert events == ["start", "end"]


def test_arrange_mode_enter_commits_through_arrange_editor():
    """Arrange mode should commit to ArrangeGridEditor and call on-apply callback."""
    inspector = _InspectorStub()
    arrange_editor = _ArrangeEditorStub()
    applied_layouts: list[dict[str, float | int]] = []
    panel = DevShellPropertyInspectorPanel(
        inspector=inspector,
        on_edit_start=lambda: None,
        on_edit_end=lambda: None,
    )
    panel.set_visible(True)
    panel.show_arrange_mode(arrange_editor, on_apply_layout=lambda kwargs: applied_layouts.append(dict(kwargs)))

    assert panel.handle_key_press(arcade.key.ENTER, 0) is True
    assert panel.editing is True
    assert panel.text_buffer.text == "1"

    panel.text_buffer.set_text("3")
    assert panel.handle_key_press(arcade.key.ENTER, 0) is True
    assert panel.editing is False
    assert arrange_editor.applied[-1] == ("rows", "3")
    assert applied_layouts[-1]["rows"] == 3
