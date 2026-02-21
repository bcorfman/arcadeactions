"""Window-free command palette panel model for one-window DevShell migration."""

from __future__ import annotations

from collections.abc import Callable

import arcade

from arcadeactions.dev.command_registry import CommandExecutionContext, CommandRegistry, DevCommand


class DevShellCommandPalettePanel:
    """UI-agnostic command-palette panel state and key-handling logic."""

    def __init__(
        self,
        *,
        registry: CommandRegistry,
        context_provider: Callable[[], CommandExecutionContext],
    ) -> None:
        self._registry = registry
        self._context_provider = context_provider
        self.visible = False
        self.selected_index = 0

    def set_visible(self, value: bool) -> None:
        """Set panel visibility and normalize selection for current enabled set."""
        self.visible = bool(value)
        if self.visible:
            self._clamp_selected_index()

    def toggle_visible(self) -> None:
        """Toggle panel visibility."""
        self.set_visible(not self.visible)

    def handle_key_press(self, key: int, modifiers: int) -> bool:
        """Handle key press; return True when consumed by this panel."""
        del modifiers
        if not self.visible:
            return False

        if key in (arcade.key.ESCAPE, arcade.key.F8):
            self.set_visible(False)
            return True

        if key == arcade.key.DOWN:
            self._move_selection(1)
            return True
        if key == arcade.key.UP:
            self._move_selection(-1)
            return True
        if key == arcade.key.ENTER:
            return self._execute_selected()

        context = self._context_provider()
        if self._registry.execute_key(key, context):
            return True

        return False

    def on_key_press(self, key: int, modifiers: int) -> bool:
        """Router adapter for key events."""
        return self.handle_key_press(key, modifiers)

    def on_text(self, text: str) -> bool:
        """Router adapter for text input (unused by command palette)."""
        del text
        return False

    def on_text_motion(self, motion: int) -> bool:
        """Router adapter for text-motion input (unused by command palette)."""
        del motion
        return False

    def _enabled_commands(self) -> list[DevCommand]:
        context = self._context_provider()
        return self._registry.get_enabled_commands(context)

    def _clamp_selected_index(self) -> None:
        commands = self._enabled_commands()
        if not commands:
            self.selected_index = 0
            return
        if self.selected_index >= len(commands):
            self.selected_index = len(commands) - 1
        if self.selected_index < 0:
            self.selected_index = 0

    def _move_selection(self, direction: int) -> None:
        commands = self._enabled_commands()
        if not commands:
            self.selected_index = 0
            return
        self.selected_index = (self.selected_index + int(direction)) % len(commands)

    def _execute_selected(self) -> bool:
        commands = self._enabled_commands()
        if not commands:
            self.selected_index = 0
            return True
        self._clamp_selected_index()
        command = commands[self.selected_index]
        context = self._context_provider()
        try:
            return bool(command.handler(context))
        except Exception:
            return False
