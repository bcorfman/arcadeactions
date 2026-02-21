"""Unit tests for one-window DevShell command palette panel logic."""

from __future__ import annotations

import arcade

from arcadeactions.dev.command_registry import CommandExecutionContext, CommandRegistry
from arcadeactions.dev.devshell_command_palette_panel import DevShellCommandPalettePanel


def _context() -> CommandExecutionContext:
    return CommandExecutionContext(window=None, scene_sprites=arcade.SpriteList(), selection=[])


def test_toggle_visibility_and_escape_close():
    """Panel should open/close via toggle and close on Esc/F8 while open."""
    registry = CommandRegistry()
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)

    assert panel.visible is False
    panel.toggle_visible()
    assert panel.visible is True

    assert panel.handle_key_press(arcade.key.ESCAPE, 0) is True
    assert panel.visible is False

    panel.set_visible(True)
    assert panel.handle_key_press(arcade.key.F8, 0) is True
    assert panel.visible is False


def test_arrow_navigation_cycles_enabled_commands_only():
    """Up/down should cycle selected index across enabled command list."""
    registry = CommandRegistry()
    registry.register_command(
        key=arcade.key.E,
        name="Export",
        category="Export/Import",
        handler=lambda _ctx: True,
    )
    registry.register_command(
        key=arcade.key.G,
        name="Grid",
        category="Visualization",
        handler=lambda _ctx: True,
        enabled_check=lambda _ctx: False,
    )
    registry.register_command(
        key=arcade.key.I,
        name="Import",
        category="Export/Import",
        handler=lambda _ctx: True,
    )
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)
    panel.set_visible(True)

    assert panel.selected_index == 0
    assert panel.handle_key_press(arcade.key.DOWN, 0) is True
    assert panel.selected_index == 1
    assert panel.handle_key_press(arcade.key.DOWN, 0) is True
    assert panel.selected_index == 0
    assert panel.handle_key_press(arcade.key.UP, 0) is True
    assert panel.selected_index == 1


def test_enter_executes_selected_enabled_command():
    """Enter should execute currently selected enabled command."""
    called: list[str] = []
    registry = CommandRegistry()
    registry.register_command(
        key=arcade.key.E,
        name="Export",
        category="Export/Import",
        handler=lambda _ctx: called.append("export") or True,
    )
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)
    panel.set_visible(True)

    assert panel.handle_key_press(arcade.key.ENTER, 0) is True
    assert called == ["export"]


def test_quick_key_executes_enabled_command():
    """Quick keys should execute enabled command without requiring Enter."""
    called: list[str] = []
    registry = CommandRegistry()
    registry.register_command(
        key=arcade.key.E,
        name="Export",
        category="Export/Import",
        handler=lambda _ctx: called.append("export") or True,
    )
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)
    panel.set_visible(True)

    assert panel.handle_key_press(arcade.key.E, 0) is True
    assert called == ["export"]


def test_unhandled_key_returns_false_and_does_not_forward_anywhere():
    """Unhandled keys should return False for router fallback handling."""
    registry = CommandRegistry()
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)
    panel.set_visible(True)

    assert panel.handle_key_press(arcade.key.A, 0) is False


def test_hidden_panel_does_not_consume_input():
    """When hidden, panel should not consume key events."""
    registry = CommandRegistry()
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)

    assert panel.visible is False
    assert panel.handle_key_press(arcade.key.DOWN, 0) is False
    assert panel.handle_key_press(arcade.key.ENTER, 0) is False


def test_router_adapter_methods_delegate_to_panel_handlers():
    """Panel should expose router-compatible on_* methods."""
    registry = CommandRegistry()
    panel = DevShellCommandPalettePanel(registry=registry, context_provider=_context)
    panel.set_visible(True)

    assert panel.on_key_press(arcade.key.A, 0) is False
    assert panel.on_text("x") is False
    assert panel.on_text_motion(arcade.key.MOTION_LEFT) is False
