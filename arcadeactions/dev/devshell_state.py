"""Runtime mode and focus-visibility state for one-window DevShell."""

from __future__ import annotations

from enum import Enum

from arcadeactions.dev.devshell_focus import DevShellFocusManager


class DevShellMode(str, Enum):
    """Supported runtime modes for the one-window DevShell."""

    EDIT_LIVE = "edit_live"
    PREVIEW_CLEAN = "preview_clean"
    PRODUCTION = "production"


class DevShellPanelVisualState:
    """Visual flags for a single DevShell panel."""

    __slots__ = ("is_active", "show_caret")

    def __init__(self, *, is_active: bool, show_caret: bool) -> None:
        self.is_active = bool(is_active)
        self.show_caret = bool(show_caret)


class DevShellFocusVisualState:
    """Computed focus-visible state for top rail and panels."""

    __slots__ = ("focus_label", "panel_states", "pulse_token")

    def __init__(
        self,
        *,
        focus_label: str,
        panel_states: dict[str, DevShellPanelVisualState],
        pulse_token: int,
    ) -> None:
        self.focus_label = str(focus_label)
        self.panel_states = dict(panel_states)
        self.pulse_token = int(pulse_token)


class DevShellStateController:
    """Coordinates runtime mode and focus-visibility state transitions."""

    def __init__(self, *, focus_manager: DevShellFocusManager) -> None:
        self._focus = focus_manager
        self.mode = DevShellMode.EDIT_LIVE
        self.focus_pulse_token = 0

    def is_preview_clean(self) -> bool:
        """Return True when routing/rendering should use Preview-Clean behavior."""
        return self.mode == DevShellMode.PREVIEW_CLEAN

    def set_mode(self, mode: DevShellMode) -> DevShellMode:
        """Set mode and normalize focus ownership when entering production."""
        self.mode = DevShellMode(mode)
        if self.mode == DevShellMode.PRODUCTION:
            self._focus.end_text_edit()
            self._focus.clear_active_panel()
        return self.mode

    def toggle_preview_clean(self) -> DevShellMode:
        """Toggle between Edit-Live and Preview-Clean (no-op in Production)."""
        if self.mode == DevShellMode.PRODUCTION:
            return self.mode
        if self.mode == DevShellMode.EDIT_LIVE:
            self.mode = DevShellMode.PREVIEW_CLEAN
            return self.mode
        self.mode = DevShellMode.EDIT_LIVE
        return self.mode

    def set_active_panel(self, panel: str | None) -> None:
        """Set focused panel and bump pulse token when focus changes."""
        before = self._focus.active_panel
        self._focus.set_active_panel(panel)
        after = self._focus.active_panel
        if before != after:
            self.focus_pulse_token += 1

    def clear_active_panel(self) -> None:
        """Clear focused panel and bump pulse token when focus changes."""
        before = self._focus.active_panel
        self._focus.clear_active_panel()
        after = self._focus.active_panel
        if before != after:
            self.focus_pulse_token += 1

    def focus_visual_state(self, *, panel_ids: list[str]) -> DevShellFocusVisualState:
        """Build visibility state used by panel/title focus UI indicators."""
        active_panel = self._focus.active_panel
        if active_panel is None:
            focus_label = "Focus: game-stage"
        else:
            focus_label = f"Focus: {active_panel}"

        panel_states: dict[str, DevShellPanelVisualState] = {}
        text_edit_panel = self._focus.text_edit_panel
        for panel_id in panel_ids:
            panel_name = str(panel_id)
            is_active = panel_name == active_panel
            show_caret = panel_name == active_panel and panel_name == text_edit_panel
            panel_states[panel_name] = DevShellPanelVisualState(is_active=is_active, show_caret=show_caret)

        return DevShellFocusVisualState(
            focus_label=focus_label,
            panel_states=panel_states,
            pulse_token=self.focus_pulse_token,
        )
