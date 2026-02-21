"""Window-free property inspector panel model for one-window DevShell migration."""

from __future__ import annotations

import arcade

from arcadeactions.dev.devshell_text_buffer import DevShellTextBuffer


class DevShellPropertyInspectorPanel:
    """Panel controller for property navigation and text-buffer editing."""

    def __init__(self, *, inspector, on_edit_start=None, on_edit_end=None) -> None:
        self._inspector = inspector
        self._on_edit_start = on_edit_start
        self._on_edit_end = on_edit_end
        self.visible = False
        self.editing = False
        self.mode = "properties"
        self._arrange_editor = None
        self._arrange_setting_index = 0
        self._arrange_on_apply_layout = None
        self.text_buffer = DevShellTextBuffer()
        self.input_error = ""

    def set_visible(self, value: bool) -> None:
        """Set visibility and clear active edit state when hiding panel."""
        was_editing = self.editing
        self.visible = bool(value)
        if not self.visible:
            self.editing = False
            self.input_error = ""
            if was_editing:
                self._notify_edit_end()

    def set_selection(self, selection) -> None:
        """Delegate selection updates to underlying inspector model."""
        if self.mode == "arrange":
            return
        self._inspector.set_selection(selection)

    def show_properties_mode(self) -> None:
        self.mode = "properties"
        self._arrange_editor = None
        self._arrange_setting_index = 0
        self._arrange_on_apply_layout = None
        if self.editing:
            self._cancel_edit()

    def show_arrange_mode(self, editor, *, on_apply_layout=None) -> None:
        self.mode = "arrange"
        self._arrange_editor = editor
        self._arrange_setting_index = 0
        self._arrange_on_apply_layout = on_apply_layout
        if self.editing:
            self._cancel_edit()

    def handle_key_press(self, key: int, modifiers: int) -> bool:
        """Handle property panel key input and return True when consumed."""
        if not self.visible:
            return False

        if key == arcade.key.ESCAPE:
            if self.editing:
                self._cancel_edit()
            else:
                self.set_visible(False)
            return True

        if modifiers & arcade.key.MOD_CTRL:
            if key == arcade.key.Z and modifiers & arcade.key.MOD_SHIFT:
                self._inspector.redo()
                return True
            if key == arcade.key.Z:
                self._inspector.undo()
                return True

        if key == arcade.key.ENTER:
            if self.editing:
                self._commit_edit()
            else:
                self._start_edit()
            return True

        if self.editing:
            return self._handle_editing_key(key)

        if key == arcade.key.DOWN:
            self._move_active_row(1)
            return True
        if key == arcade.key.UP:
            self._move_active_row(-1)
            return True
        if key == arcade.key.TAB:
            direction = -1 if modifiers & arcade.key.MOD_SHIFT else 1
            self._move_active_row(direction)
            return True
        if key == arcade.key.SPACE:
            if self.mode == "arrange":
                return False
            current = self._inspector.current_property()
            if current.editor_type != "bool":
                return False
            value = self._inspector.property_value(current.name)
            current_value = bool(value)
            self._inspector.apply_property_text(current.name, "false" if current_value else "true")
            return True

        return False

    def handle_text(self, text: str) -> bool:
        """Apply printable text insertion while editing."""
        if not self.visible or not self.editing:
            return False
        if not text:
            return False
        if not all(ch.isprintable() for ch in text):
            return False
        self.text_buffer.insert_text(text)
        return True

    def on_key_press(self, key: int, modifiers: int) -> bool:
        """Router adapter for key events."""
        return self.handle_key_press(key, modifiers)

    def on_text(self, text: str) -> bool:
        """Router adapter for text input."""
        return self.handle_text(text)

    def on_text_motion(self, motion: int) -> bool:
        """Router adapter for text-motion input while editing."""
        if not self.visible or not self.editing:
            return False
        if motion == arcade.key.MOTION_BACKSPACE:
            self.text_buffer.backspace()
            return True
        if motion == arcade.key.MOTION_DELETE:
            self.text_buffer.delete()
            return True
        if motion == arcade.key.MOTION_LEFT:
            self.text_buffer.move_left()
            return True
        if motion == arcade.key.MOTION_RIGHT:
            self.text_buffer.move_right()
            return True
        if motion == arcade.key.MOTION_BEGINNING_OF_LINE:
            self.text_buffer.move_to_start()
            return True
        if motion == arcade.key.MOTION_END_OF_LINE:
            self.text_buffer.move_to_end()
            return True
        return False

    def _start_edit(self) -> None:
        if self.mode == "arrange":
            settings = self._arrange_settings()
            if not settings:
                return
            self._arrange_setting_index = min(self._arrange_setting_index, len(settings) - 1)
            value_text = settings[self._arrange_setting_index][1]
        else:
            current = self._inspector.current_property()
            if current is None:
                return
            value_text = self._inspector.current_property_value_text()
        self.editing = True
        self.input_error = ""
        self.text_buffer.set_text(value_text)
        self._notify_edit_start()

    def _cancel_edit(self) -> None:
        self.editing = False
        self.input_error = ""
        self._notify_edit_end()

    def _commit_edit(self) -> bool:
        if self.mode == "arrange":
            settings = self._arrange_settings()
            if not settings:
                self._cancel_edit()
                return False
            self._arrange_setting_index = min(self._arrange_setting_index, len(settings) - 1)
            setting_name = settings[self._arrange_setting_index][0]
            try:
                changed = self._arrange_editor.set_setting(setting_name, self.text_buffer.text)
                if changed and self._arrange_on_apply_layout is not None:
                    self._arrange_on_apply_layout(self._arrange_editor.current_layout_kwargs())
            except (ValueError, KeyError, TypeError) as exc:
                self.input_error = str(exc)
                return False
        else:
            current = self._inspector.current_property()
            if current is None:
                self._cancel_edit()
                return False
            try:
                changed = self._inspector.apply_property_text(current.name, self.text_buffer.text)
            except (ValueError, KeyError, TypeError) as exc:
                self.input_error = str(exc)
                return False
        self.editing = False
        self.input_error = ""
        self._notify_edit_end()
        return bool(changed)

    def _handle_editing_key(self, key: int) -> bool:
        if key == arcade.key.BACKSPACE:
            self.text_buffer.backspace()
            return True
        if key == arcade.key.DELETE:
            self.text_buffer.delete()
            return True
        if key == arcade.key.LEFT:
            self.text_buffer.move_left()
            return True
        if key == arcade.key.RIGHT:
            self.text_buffer.move_right()
            return True
        if key == arcade.key.HOME:
            self.text_buffer.move_to_start()
            return True
        if key == arcade.key.END:
            self.text_buffer.move_to_end()
            return True
        return False

    def _notify_edit_start(self) -> None:
        if self._on_edit_start is not None:
            self._on_edit_start()

    def _notify_edit_end(self) -> None:
        if self._on_edit_end is not None:
            self._on_edit_end()

    def _move_active_row(self, delta: int) -> None:
        if self.mode == "arrange":
            settings = self._arrange_settings()
            if not settings:
                self._arrange_setting_index = 0
                return
            index = self._arrange_setting_index + int(delta)
            if index < 0:
                index = 0
            if index >= len(settings):
                index = len(settings) - 1
            self._arrange_setting_index = index
            return
        self._inspector.move_active_property(int(delta))

    def _arrange_settings(self) -> list[tuple[str, str]]:
        if self._arrange_editor is None:
            return []
        return list(self._arrange_editor.list_settings())
