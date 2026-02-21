"""Composition layer for one-window DevShell foundations."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence, Set

from arcadeactions.dev.devshell_focus import DevShellFocusManager
from arcadeactions.dev.devshell_input_router import DevShellInputRouter
from arcadeactions.dev.devshell_state import DevShellMode, DevShellStateController


class DevShellCoordinator:
    """Coordinates focus, mode, and input-router behavior for DevShell."""

    def __init__(
        self,
        *,
        game_target,
        panel_targets: Mapping[str, object],
        panel_order: Sequence[str],
        transient_panels: Set[str] | None = None,
        close_panel: Callable[[str], None] | None = None,
    ) -> None:
        self.focus_manager = DevShellFocusManager(open_panels=panel_order)
        self.state = DevShellStateController(focus_manager=self.focus_manager)
        self.router = DevShellInputRouter(
            focus_manager=self.focus_manager,
            game_target=game_target,
            panel_targets=panel_targets,
            transient_panels=transient_panels,
            close_panel=close_panel,
        )

    def set_panel_order(self, panel_order: Sequence[str]) -> None:
        """Update open panel order for focus cycling."""
        self.focus_manager.set_open_panels(panel_order)

    def set_active_panel(self, panel: str | None) -> None:
        """Set active panel focus using state controller semantics."""
        self.state.set_active_panel(panel)

    def set_preview_clean(self, enabled: bool) -> DevShellMode:
        """Set preview-clean routing behavior."""
        if enabled:
            mode = self.state.set_mode(DevShellMode.PREVIEW_CLEAN)
            self.router.set_preview_clean(True)
            return mode
        mode = self.state.set_mode(DevShellMode.EDIT_LIVE)
        self.router.set_preview_clean(False)
        return mode

    def set_mode(self, mode: DevShellMode) -> DevShellMode:
        """Set explicit DevShell mode and synchronize router behavior."""
        next_mode = self.state.set_mode(mode)
        self.router.set_preview_clean(next_mode != DevShellMode.EDIT_LIVE)
        return next_mode

    def route_key_press(self, key: int, modifiers: int) -> bool:
        """Route key press through deterministic DevShell router."""
        return self.router.route_key_press(key, modifiers)

    def route_text(self, text: str) -> bool:
        """Route text input through deterministic DevShell router."""
        return self.router.route_text(text)

    def route_text_motion(self, motion: int) -> bool:
        """Route text motion through deterministic DevShell router."""
        return self.router.route_text_motion(motion)
