"""Registry and execution context for dev command palette commands."""

from __future__ import annotations

from collections.abc import Callable

import arcade


class CommandExecutionContext:
    """Context passed to command handlers."""

    def __init__(
        self,
        *,
        window: arcade.Window | None,
        scene_sprites: arcade.SpriteList,
        selection: list[arcade.Sprite],
    ) -> None:
        self.window = window
        self.scene_sprites = scene_sprites
        self.selection = selection


class DevCommand:
    """Registered command metadata and callbacks."""

    def __init__(
        self,
        *,
        key: int,
        name: str,
        category: str,
        handler: Callable[[CommandExecutionContext], bool],
        enabled_check: Callable[[CommandExecutionContext], bool] | None = None,
    ) -> None:
        self.key = int(key)
        self.name = name
        self.category = category
        self.handler = handler
        self.enabled_check = enabled_check

    def is_enabled(self, context: CommandExecutionContext) -> bool:
        """Return whether this command is currently enabled."""
        if self.enabled_check is None:
            return True
        try:
            return bool(self.enabled_check(context))
        except Exception:
            return False


class CommandRegistry:
    """Extensible command registry used by the dev command palette."""

    def __init__(self) -> None:
        self._commands: list[DevCommand] = []

    def register_command(
        self,
        *,
        key: int,
        name: str,
        category: str,
        handler: Callable[[CommandExecutionContext], bool],
        enabled_check: Callable[[CommandExecutionContext], bool] | None = None,
    ) -> DevCommand:
        """Register and return a command."""
        command = DevCommand(
            key=key,
            name=name,
            category=category,
            handler=handler,
            enabled_check=enabled_check,
        )
        self._commands.append(command)
        return command

    def get_commands_with_enabled_state(self, context: CommandExecutionContext) -> list[tuple[DevCommand, bool]]:
        """Return sorted commands with enabled/disabled state for rendering."""
        entries = [(command, command.is_enabled(context)) for command in self._commands]
        entries.sort(key=lambda item: (item[0].category, item[0].name))
        return entries

    def get_enabled_commands(self, context: CommandExecutionContext) -> list[DevCommand]:
        """Return enabled commands sorted for keyboard navigation."""
        return [command for command, enabled in self.get_commands_with_enabled_state(context) if enabled]

    def find_enabled_command_for_key(self, key: int, context: CommandExecutionContext) -> DevCommand | None:
        """Return enabled command bound to key, if any."""
        for command in self.get_enabled_commands(context):
            if command.key == key:
                return command
        return None

    def execute_key(self, key: int, context: CommandExecutionContext) -> bool:
        """Execute key-bound command if available."""
        command = self.find_enabled_command_for_key(key, context)
        if command is None:
            return False
        try:
            return bool(command.handler(context))
        except Exception:
            return False
