"""Secondary-window sprite property inspector with live editing."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import arcade
import arcade.gui as gui
from arcade import window_commands

from arcadeactions.dev.arrange_editor import ArrangeGridEditor
from arcadeactions.dev.property_history import PropertyHistory
from arcadeactions.dev.property_registry import PropertyDefinition, SpritePropertyRegistry
from arcadeactions.dev.property_widgets import parse_property_text

try:
    from pyglet.gl.lib import GLException, MissingFunctionException
except ImportError:  # pragma: no cover
    GLException = Exception
    MissingFunctionException = Exception


class SpritePropertyInspector:
    """Core property inspector model independent from window rendering."""

    def __init__(
        self,
        *,
        property_registry: SpritePropertyRegistry,
        history: PropertyHistory,
        window: arcade.Window | None,
    ) -> None:
        self._registry = property_registry
        self._history = history
        self._window = window
        self._selection: list[arcade.Sprite] = []
        self._last_non_empty_selection: list[arcade.Sprite] = []
        self._properties: list[PropertyDefinition] = []
        self._active_index = 0

    def set_selection(self, selection: Sequence[arcade.Sprite]) -> None:
        self._selection = list(selection)
        if self._selection:
            self._last_non_empty_selection = list(self._selection)
        self._properties = self._registry.properties_for_selection(self._selection)
        if self._active_index >= len(self._properties):
            self._active_index = max(0, len(self._properties) - 1)

    def selection(self) -> list[arcade.Sprite]:
        return list(self._selection)

    def visible_properties(self) -> list[PropertyDefinition]:
        return list(self._properties)

    def current_property(self) -> PropertyDefinition | None:
        if not self._properties:
            return None
        return self._properties[self._active_index]

    def move_active_property(self, delta: int) -> None:
        if not self._properties:
            self._active_index = 0
            return
        self._active_index = (self._active_index + delta) % len(self._properties)

    def _expression_names(self, property_name: str) -> dict[str, float]:
        width = 0.0
        height = 0.0
        if self._window is not None:
            width = float(self._window.width)
            height = float(self._window.height)

        axis_center = width / 2.0
        if property_name in ("center_y", "top", "bottom"):
            axis_center = height / 2.0

        return {
            "SCREEN_WIDTH": width,
            "SCREEN_HEIGHT": height,
            "SCREEN_CENTER": axis_center,
            "SCREEN_CENTER_X": width / 2.0,
            "SCREEN_CENTER_Y": height / 2.0,
        }

    def apply_property_text(self, property_name: str, text: str) -> bool:
        if not self._selection:
            return False

        parsed = parse_property_text(property_name, text, self._expression_names(property_name))
        for sprite in self._selection:
            old_value = self._registry.get_value(sprite, property_name)
            self._registry.set_value(sprite, property_name, parsed)
            new_value = self._registry.get_value(sprite, property_name)
            if old_value != new_value:
                self._history.record_change(sprite, property_name, old_value, new_value)
        return True

    def property_value(self, property_name: str) -> object | None:
        if not self._selection:
            return None
        return self._registry.get_value(self._selection[0], property_name)

    def current_property_value_text(self) -> str:
        current = self.current_property()
        if current is None:
            return ""
        value = self.property_value(current.name)
        if value is None:
            return ""
        return self._format_python_value(value)

    def undo(self) -> bool:
        targets = self._selection if self._selection else self._last_non_empty_selection
        changed = False
        for sprite in targets:
            if self._history.undo(sprite) is not None:
                changed = True
        return changed

    def redo(self) -> bool:
        targets = self._selection if self._selection else self._last_non_empty_selection
        changed = False
        for sprite in targets:
            if self._history.redo(sprite) is not None:
                changed = True
        return changed

    def copy_selection_as_python(self, property_names: Sequence[str] | None = None) -> str:
        if not self._selection:
            return ""

        names = list(property_names) if property_names is not None else [prop.name for prop in self._properties]
        lines: list[str] = []
        sprite = self._selection[0]
        for property_name in names:
            value = self._registry.get_value(sprite, property_name)
            lines.append(f"sprite.{property_name} = {self._format_python_value(value)}")
        return "\n".join(lines)

    def copy_current_property(self) -> str:
        current = self.current_property()
        if current is None or not self._selection:
            return ""
        value = self._registry.get_value(self._selection[0], current.name)
        return f"sprite.{current.name} = {self._format_python_value(value)}"

    @staticmethod
    def _format_python_value(value: object) -> str:
        if type(value) is str:
            return repr(value)
        return str(value)


class PropertyInspectorWindow(arcade.Window):
    """Secondary window wrapper for SpritePropertyInspector interactions."""

    MARGIN = 12
    LINE_HEIGHT = 20
    EDITOR_HEIGHT = 34
    EDITOR_TOP_OFFSET = 68
    EDITOR_TEXT_PADDING_X = 6
    EDITOR_TEXT_PADDING_Y = 9
    EDITOR_FONT_NAME = ("Arial",)
    EDITOR_FONT_SIZE = 12
    EDITOR_TEXT_COLOR = arcade.color.WHITE
    EDITOR_BG_COLOR = (32, 34, 44, 255)

    def __init__(
        self,
        *,
        inspector: SpritePropertyInspector,
        main_window: arcade.Window | None = None,
        on_close_callback: Callable[[], None] | None = None,
        width: int = 360,
        height: int = 420,
        title: str = "Sprite Property Inspector",
    ) -> None:
        # Pyglet/Arcade can trigger set_visible during native window creation.
        # Define visibility/UI fields up-front so visibility hooks are safe.
        self._is_headless = False
        self._is_visible = False
        self._is_closed = False
        self._ui_manager: gui.UIManager | None = None
        self._root_layout: gui.UIAnchorLayout | None = None
        self._editor_input: gui.UIInputText | None = None
        try:
            super().__init__(width=width, height=height, title=title, resizable=True, visible=False)
        except (GLException, MissingFunctionException, RuntimeError, OSError):
            self._init_headless_mode(width, height, title)
        else:
            self._is_headless = False

        self._inspector = inspector
        self._main_window = main_window
        self._on_close_callback = on_close_callback
        self._editing = False
        self._input_error = ""
        self._mode = "properties"
        self._arrange_editor: ArrangeGridEditor | None = None
        self._arrange_setting_index = 0
        self._arrange_on_apply_layout: Callable[[dict[str, float | int]], None] | None = None
        self._widget_draw_failures = 0
        self._pending_caret_enforce_frames = 0

        self.background_color = (26, 26, 34)
        self._title_text = None
        self._value_text = None
        if not self._is_headless:
            self._title_text = arcade.Text(
                "Sprite Properties",
                self.MARGIN,
                height - self.MARGIN - 20,
                arcade.color.WHITE,
                14,
                bold=True,
            )
            self._value_text = arcade.Text("", self.MARGIN, height - self.MARGIN - 52, arcade.color.LIGHT_GRAY, 11)
            self._init_editor_widget(width)

    def _init_headless_mode(self, width: int, height: int, title: str) -> None:
        self._headless_width = int(width)
        self._headless_height = int(height)
        self._headless_scale = 1.0
        self._is_visible = False
        self.location = (0, 0)
        self.has_exit = False
        self.handlers = {}
        self._title = title
        self._view = None
        self._is_headless = True

    def _init_editor_widget(self, width: int) -> None:
        self._ui_manager = gui.UIManager(window=self)
        self._root_layout = gui.UIAnchorLayout()
        self._ui_manager.add(self._root_layout)

        self._editor_input = gui.UIInputText(
            width=max(140, width - (self.MARGIN * 2)),
            height=self.EDITOR_HEIGHT,
            text="",
            text_color=self.EDITOR_TEXT_COLOR,
            caret_color=self.EDITOR_TEXT_COLOR,
            style={
                "normal": gui.UIInputText.UIStyle(bg=self.EDITOR_BG_COLOR, border=arcade.color.WHITE, border_width=2),
                "hover": gui.UIInputText.UIStyle(bg=self.EDITOR_BG_COLOR, border=arcade.color.WHITE, border_width=2),
                "press": gui.UIInputText.UIStyle(bg=self.EDITOR_BG_COLOR, border=arcade.color.WHITE, border_width=2),
                "disabled": gui.UIInputText.UIStyle(bg=self.EDITOR_BG_COLOR, border=arcade.color.WHITE, border_width=2),
                "invalid": gui.UIInputText.UIStyle(bg=self.EDITOR_BG_COLOR, border=arcade.color.WHITE, border_width=2),
            },
        )
        self._editor_input.on_change = self._on_editor_input_change
        self._editor_input.visible = False
        self._root_layout.add(
            self._editor_input,
            anchor_x="left",
            align_x=self.MARGIN,
            anchor_y="top",
            align_y=-(self.MARGIN + self.EDITOR_TOP_OFFSET),
        )

    @property
    def visible(self) -> bool:
        return self._is_visible

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    def set_visible(self, visible: bool) -> None:
        self._is_visible = bool(visible)
        if self._is_headless:
            return
        ui_manager = getattr(self, "_ui_manager", None)
        if ui_manager is not None:
            if visible:
                ui_manager.enable()
            else:
                ui_manager.disable()
        try:
            super().set_visible(visible)
        except Exception:
            return

    def show_window(self) -> None:
        self.set_visible(True)

    def hide_window(self) -> None:
        self.set_visible(False)

    def set_selection(self, selection: Sequence[arcade.Sprite]) -> None:
        if self._mode == "arrange":
            return
        previous_selection = self._inspector.selection()
        self._inspector.set_selection(selection)
        if not self._editing:
            return
        if self._selection_signature(previous_selection) == self._selection_signature(selection):
            return
        self._cancel_edit()

    def apply_property_text(self, property_name: str, text: str) -> bool:
        return self._inspector.apply_property_text(property_name, text)

    def undo(self) -> bool:
        changed = self._inspector.undo()
        if changed and self._editing:
            self._sync_editor_text_from_selection()
        return changed

    def redo(self) -> bool:
        changed = self._inspector.redo()
        if changed and self._editing:
            self._sync_editor_text_from_selection()
        return changed

    def copy_selection_as_python(self, property_names: Sequence[str] | None = None) -> str:
        return self._inspector.copy_selection_as_python(property_names)

    def show_properties_mode(self) -> None:
        self._mode = "properties"
        self._arrange_editor = None
        self._arrange_setting_index = 0
        self._arrange_on_apply_layout = None
        if self._title_text is not None:
            self._title_text.text = "Sprite Properties"
        if self._value_text is not None:
            self._value_text.text = ""

    def show_arrange_mode(
        self,
        editor: ArrangeGridEditor,
        *,
        on_apply_layout: Callable[[dict[str, float | int]], None] | None = None,
    ) -> None:
        self._mode = "arrange"
        self._arrange_editor = editor
        self._arrange_setting_index = 0
        self._arrange_on_apply_layout = on_apply_layout
        self._cancel_edit()
        if self._title_text is not None:
            self._title_text.text = "Arrange Grid Settings"
        if self._value_text is not None:
            self._value_text.text = ""

    def _sync_editor_text_from_selection(self) -> None:
        if self._editor_input is None:
            return
        if self._mode == "arrange":
            if self._arrange_editor is None:
                self._set_editor_text("")
                return
            settings = self._safe_arrange_settings()
            if settings is None:
                self._set_editor_text("")
                return
            if not settings:
                self._set_editor_text("")
                return
            self._arrange_setting_index = min(self._arrange_setting_index, len(settings) - 1)
            self._set_editor_text(settings[self._arrange_setting_index][1])
            return
        self._set_editor_text(self._inspector.current_property_value_text())

    def _set_editor_text(self, text: str) -> None:
        if self._editor_input is None:
            return
        clean_text = self._sanitize_editor_text(text)
        self._editor_input.text = clean_text
        self._apply_editor_text_style(clean_text)

    def _on_editor_input_change(self, _event: object) -> None:
        if self._editor_input is None:
            return
        clean = self._sanitize_editor_text(self._editor_input.text)
        if clean != self._editor_input.text:
            self._editor_input.text = clean
        self._apply_editor_text_style(clean)

    def _apply_editor_text_style(self, text: str) -> None:
        if self._editor_input is None:
            return
        # Include one trailing position so newly inserted characters at the
        # caret boundary inherit the same readable style.
        style_end = max(1, len(text) + 1)
        self._editor_input.doc.set_style(
            0,
            style_end,
            {
                "font_name": self.EDITOR_FONT_NAME,
                "font_size": self.EDITOR_FONT_SIZE,
                "color": self.EDITOR_TEXT_COLOR,
            },
        )

    def _start_edit(self) -> bool:
        if self._editor_input is None and not self._is_headless:
            self._init_editor_widget(int(self.width))
        if self._editor_input is None:
            self._input_error = "Widget editing unavailable on this graphics backend."
            return False
        if self._mode == "properties":
            current = self._inspector.current_property()
            if current is None:
                return False

        self._editing = True
        self._input_error = ""
        self._editor_input.visible = True
        try:
            self._sync_editor_text_from_selection()
        except Exception as exc:
            self._editing = False
            self._editor_input.visible = False
            self._input_error = str(exc)
            return False
        if self._mode == "arrange" and self._input_error:
            self._editing = False
            self._editor_input.visible = False
            return False
        try:
            try:
                self.activate()
            except Exception:
                pass
            self._editor_input.activate()
            self._editor_input.focused = True
            caret = self._editor_input.caret
            text_len = len(self._editor_input.text)
            caret.position = text_len
            caret.mark = text_len
            self._pending_caret_enforce_frames = 2
            return True
        except Exception as exc:
            self._editing = False
            self._editor_input.visible = False
            self._input_error = f"Widget editing unavailable: {exc}"
            return False

    def _cancel_edit(self) -> None:
        if self._editor_input is None:
            return
        self._editing = False
        self._pending_caret_enforce_frames = 0
        self._input_error = ""
        self._deactivate_editor_widget()

    def _handle_widget_draw_failure(self) -> None:
        self._editing = False
        self._widget_draw_failures = 0
        if self._editor_input is not None:
            self._deactivate_editor_widget()
        self._input_error = "Widget draw failed on this graphics backend."

    def _commit_edit(self) -> bool:
        if self._editor_input is None:
            return False
        changed = False
        if self._mode == "arrange":
            if self._arrange_editor is None:
                self._cancel_edit()
                return False
            settings = self._safe_arrange_settings()
            if settings is None:
                return False
            if not settings:
                self._cancel_edit()
                return False
            self._arrange_setting_index = min(self._arrange_setting_index, len(settings) - 1)
            setting_name = settings[self._arrange_setting_index][0]
            try:
                changed = self._arrange_editor.set_setting(setting_name, self._editor_input.text)
                if changed and self._arrange_on_apply_layout is not None:
                    self._arrange_on_apply_layout(self._arrange_editor.current_layout_kwargs())
            except Exception as exc:
                self._input_error = str(exc)
                return False
        else:
            current = self._inspector.current_property()
            if current is None:
                self._cancel_edit()
                return False

            try:
                changed = self._inspector.apply_property_text(current.name, self._editor_input.text)
            except (ValueError, KeyError, TypeError) as exc:
                self._input_error = str(exc)
                return False

        self._editing = False
        self._input_error = ""
        self._deactivate_editor_widget()
        return changed

    def _deactivate_editor_widget(self) -> None:
        if self._editor_input is None:
            return
        try:
            self._editor_input.deactivate()
        except Exception:
            pass
        try:
            self._editor_input.focused = False
        except Exception:
            pass
        try:
            self._editor_input.visible = False
        except Exception:
            pass

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self._mode == "arrange":
            self._on_key_press_arrange(symbol, modifiers)
            return

        if symbol == arcade.key.ESCAPE:
            if self._editing:
                self._cancel_edit()
                return
            self.hide_window()
            return

        if symbol == arcade.key.ENTER:
            if self._editing:
                self._commit_edit()
                return
            self._start_edit()
            return

        if modifiers & arcade.key.MOD_CTRL:
            if symbol == arcade.key.Z and modifiers & arcade.key.MOD_SHIFT:
                self.redo()
                return
            if symbol == arcade.key.Z:
                self.undo()
                return

        if self._editing:
            return

        if symbol == arcade.key.DOWN:
            self._inspector.move_active_property(1)
            return

        if symbol == arcade.key.UP:
            self._inspector.move_active_property(-1)
            return

        if symbol == arcade.key.TAB:
            direction = -1 if modifiers & arcade.key.MOD_SHIFT else 1
            self._inspector.move_active_property(direction)
            return

        if symbol == arcade.key.SPACE:
            current = self._inspector.current_property()
            if current is None:
                return
            if current.editor_type != "bool":
                return
            value = self._inspector.property_value(current.name)
            if value is None:
                return
            current_value = bool(value)
            self._inspector.apply_property_text(current.name, "false" if current_value else "true")
            return

        self._forward_to_main_window(symbol, modifiers)

    def _on_key_press_arrange(self, symbol: int, modifiers: int) -> None:
        editor = self._arrange_editor
        if editor is None:
            self.hide_window()
            return

        if symbol == arcade.key.ESCAPE:
            if self._editing:
                self._cancel_edit()
                return
            self.hide_window()
            return

        if modifiers & arcade.key.MOD_CTRL and symbol == arcade.key.Z and modifiers & arcade.key.MOD_SHIFT:
            self.redo()
            return
        if modifiers & arcade.key.MOD_CTRL and symbol == arcade.key.Z:
            self.undo()
            return

        if symbol == arcade.key.ENTER:
            if self._editing:
                self._commit_edit()
            else:
                self._start_edit()
            return

        settings = self._safe_arrange_settings()
        if settings is None:
            return
        if symbol == arcade.key.UP and settings:
            self._arrange_setting_index = max(0, self._arrange_setting_index - 1)
            self._sync_editor_text_from_selection()
            return
        if symbol == arcade.key.DOWN and settings:
            self._arrange_setting_index = min(len(settings) - 1, self._arrange_setting_index + 1)
            self._sync_editor_text_from_selection()
            return

    def on_text(self, text: str) -> None:
        if self._is_headless:
            return
        if self._main_window is not None and self._mode == "properties" and not self._editing:
            return
        if text and not all(ch.isprintable() for ch in text):
            # Ignore control-key text events (for example Enter's '\r') so
            # start-edit caret placement is not disturbed by sanitization.
            return
        try:
            super().on_text(text)
        except Exception:
            pass
        if not self._editing or self._editor_input is None:
            return
        clean = self._sanitize_editor_text(self._editor_input.text)
        if clean != self._editor_input.text:
            self._editor_input.text = clean
        self._apply_editor_text_style(clean)

    def _forward_to_main_window(self, symbol: int, modifiers: int) -> None:
        if self._main_window is None:
            return
        try:
            self._main_window.dispatch_event("on_key_press", symbol, modifiers)
        except Exception:
            try:
                self._main_window.on_key_press(symbol, modifiers)
            except Exception:
                return

    def on_draw(self) -> None:
        if self._is_headless:
            return

        prior_window: arcade.Window | None = None
        try:
            prior_window = window_commands.get_window()
        except RuntimeError:
            prior_window = None

        if prior_window is not self:
            try:
                window_commands.set_window(self)
            except Exception:
                prior_window = None

        try:
            self.clear()
            height = self.height
            if self._title_text is not None:
                self._title_text.y = height - self.MARGIN - 20
                self._title_text.draw()

            if self._value_text is not None:
                if self._mode == "arrange":
                    if self._arrange_editor is None:
                        self._value_text.text = ""
                    else:
                        settings = self._safe_arrange_settings()
                        if settings is None:
                            settings = []
                        if not settings:
                            self._value_text.text = ""
                        else:
                            self._arrange_setting_index = min(self._arrange_setting_index, len(settings) - 1)
                            current_name, current_value = settings[self._arrange_setting_index]
                            self._value_text.text = f"{current_name} = {current_value}"
                else:
                    current = self._inspector.current_property()
                    if current is None:
                        self._value_text.text = ""
                    else:
                        preview = self._inspector.current_property_value_text()
                        self._value_text.text = f"{current.name} = {preview}"
                self._value_text.y = height - self.MARGIN - 52
                self._value_text.draw()

            if self._input_error:
                error_text = arcade.Text(
                    self._input_error, self.MARGIN, height - self.MARGIN - 84, arcade.color.RED, 10
                )
                error_text.draw()

            if self._ui_manager is not None:
                try:
                    self._ui_manager.draw()
                    self._widget_draw_failures = 0
                except (GLException, MissingFunctionException):
                    # Some backends can produce transient GL/context failures on
                    # secondary windows when focus changes between frames.
                    self._widget_draw_failures += 1
                    if self._widget_draw_failures == 1:
                        try:
                            self.activate()
                            self._ui_manager.draw()
                            self._widget_draw_failures = 0
                        except (GLException, MissingFunctionException):
                            pass
                    if self._widget_draw_failures >= 5:
                        self._handle_widget_draw_failure()
            self._enforce_pending_caret_position()

            y = height - self.MARGIN - 124
            if self._mode == "arrange":
                self._draw_arrange_rows(y)
            else:
                properties = self._inspector.visible_properties()
                current = self._inspector.current_property()
                for prop in properties:
                    prefix = "> " if current is not None and current.name == prop.name else "  "
                    text = arcade.Text(f"{prefix}{prop.category}: {prop.name}", self.MARGIN, y, arcade.color.WHITE, 11)
                    text.draw()
                    y -= self.LINE_HEIGHT
                    if y < self.MARGIN:
                        break
        finally:
            if prior_window is not None and prior_window is not self:
                try:
                    window_commands.set_window(prior_window)
                except Exception:
                    pass

    def on_close(self) -> None:
        self._is_closed = True
        self._is_visible = False
        if self._on_close_callback is not None:
            self._on_close_callback()
        super().on_close()

    @staticmethod
    def _selection_signature(selection: Sequence[arcade.Sprite]) -> frozenset[int]:
        return frozenset(id(sprite) for sprite in selection)

    def _draw_arrange_rows(self, y: int) -> None:
        if self._arrange_editor is None:
            return
        settings = self._safe_arrange_settings()
        if settings is None:
            return
        if not settings:
            message = arcade.Text("No arrange settings available", self.MARGIN, y, arcade.color.LIGHT_GRAY, 11)
            message.draw()
            return
        self._arrange_setting_index = min(self._arrange_setting_index, len(settings) - 1)
        for index, (name, value) in enumerate(settings):
            prefix = "> " if index == self._arrange_setting_index else "  "
            text = arcade.Text(
                f"{prefix}{name}: {value}",
                self.MARGIN,
                y,
                arcade.color.WHITE,
                11,
            )
            text.draw()
            y -= self.LINE_HEIGHT
            if y < self.MARGIN:
                break

    def _safe_arrange_settings(self) -> list[tuple[str, str]] | None:
        editor = self._arrange_editor
        if editor is None:
            return []
        try:
            return editor.list_settings()
        except Exception as exc:
            self._input_error = str(exc)
            return None

    @staticmethod
    def _sanitize_editor_text(text: str) -> str:
        return "".join(ch for ch in text if ch.isprintable())

    def _enforce_pending_caret_position(self) -> None:
        if self._pending_caret_enforce_frames <= 0:
            return
        if not self._editing or self._editor_input is None:
            self._pending_caret_enforce_frames = 0
            return
        text_len = len(self._editor_input.text)
        self._editor_input.caret.position = text_len
        self._editor_input.caret.mark = text_len
        self._pending_caret_enforce_frames -= 1
