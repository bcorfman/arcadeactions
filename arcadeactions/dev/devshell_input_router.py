"""Input routing for one-window DevShell panel focus and modes."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from typing import Protocol

import arcade

from arcadeactions.dev.devshell_focus import DevShellFocusManager


class PanelInputTarget(Protocol):
    """Protocol for panel input handlers inside DevShell rails."""

    def on_key_press(self, key: int, modifiers: int) -> bool: ...
    def on_text(self, text: str) -> bool: ...
    def on_text_motion(self, motion: int) -> bool: ...


class GameInputTarget(Protocol):
    """Protocol for game-stage input target."""

    def on_key_press(self, key: int, modifiers: int) -> bool: ...
    def on_text(self, text: str) -> bool: ...
    def on_text_motion(self, motion: int) -> bool: ...


class DevShellInputRouter:
    """Routes events deterministically to focused panel or game stage."""

    def __init__(
        self,
        *,
        focus_manager: DevShellFocusManager,
        game_target: GameInputTarget,
        panel_targets: Mapping[str, PanelInputTarget],
        transient_panels: Set[str] | None = None,
        close_panel: Callable[[str], None] | None = None,
    ) -> None:
        self._focus = focus_manager
        self._game = game_target
        self._panel_targets = dict(panel_targets)
        self._transient_panels = set(transient_panels) if transient_panels is not None else set()
        self._close_panel = close_panel
        self._preview_clean = False

    def set_preview_clean(self, value: bool) -> None:
        """Set Preview-Clean mode where inputs route directly to game stage."""
        self._preview_clean = bool(value)

    def route_key_press(self, key: int, modifiers: int) -> bool:
        """Route key press based on mode and focus ownership."""
        if self._preview_clean:
            return self._game.on_key_press(key, modifiers)

        if key == arcade.key.TAB:
            if bool(modifiers & arcade.key.MOD_SHIFT):
                self._focus.cycle_previous_panel()
            else:
                self._focus.cycle_next_panel()
            return True

        if key == arcade.key.ESCAPE:
            return self._handle_escape()

        active_panel = self._focus.active_panel
        if active_panel is not None:
            panel_target = self._panel_targets.get(active_panel)
            if panel_target is not None:
                handled = panel_target.on_key_press(key, modifiers)
                if handled:
                    return True

        return self._game.on_key_press(key, modifiers)

    def route_text(self, text: str) -> bool:
        """Route text to focused editing panel or game stage."""
        if self._preview_clean:
            return self._game.on_text(text)

        panel_target = self._active_text_panel_target()
        if panel_target is not None:
            return panel_target.on_text(text)
        return self._game.on_text(text)

    def route_text_motion(self, motion: int) -> bool:
        """Route text-motion to focused editing panel or game stage."""
        if self._preview_clean:
            return self._game.on_text_motion(motion)

        panel_target = self._active_text_panel_target()
        if panel_target is not None:
            return panel_target.on_text_motion(motion)
        return self._game.on_text_motion(motion)

    def _active_text_panel_target(self) -> PanelInputTarget | None:
        if not self._focus.is_text_edit_active():
            return None
        active_panel = self._focus.active_panel
        if active_panel is None:
            return None
        if self._focus.text_edit_panel != active_panel:
            return None
        return self._panel_targets.get(active_panel)

    def _handle_escape(self) -> bool:
        if self._focus.is_text_edit_active():
            self._focus.end_text_edit()
            return True

        active_panel = self._focus.active_panel
        if active_panel is not None and active_panel in self._transient_panels:
            if self._close_panel is not None:
                self._close_panel(active_panel)
            self._focus.clear_active_panel()
            return True

        if active_panel is not None:
            self._focus.clear_active_panel()
            return True

        return self._game.on_key_press(arcade.key.ESCAPE, 0)
