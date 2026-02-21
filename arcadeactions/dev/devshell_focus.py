"""Panel focus state helpers for one-window DevShell mode."""

from __future__ import annotations

from collections.abc import Sequence


class DevShellFocusManager:
    """Tracks open panel order, active panel, and text-edit ownership."""

    def __init__(self, *, open_panels: Sequence[str]) -> None:
        self._open_panels: list[str] = [str(panel) for panel in open_panels]
        self.active_panel: str | None = None
        self.text_edit_panel: str | None = None

    def set_open_panels(self, open_panels: Sequence[str]) -> None:
        """Replace ordered open-panel list and normalize active states."""
        self._open_panels = [str(panel) for panel in open_panels]
        if self.active_panel not in self._open_panels:
            self.active_panel = None
        if self.text_edit_panel not in self._open_panels:
            self.text_edit_panel = None

    def set_active_panel(self, panel: str | None) -> None:
        """Set current panel focus if panel exists in open list."""
        if panel is None:
            self.active_panel = None
            return
        panel_name = str(panel)
        if panel_name not in self._open_panels:
            return
        self.active_panel = panel_name

    def clear_active_panel(self) -> None:
        """Clear panel focus back to game-stage ownership."""
        self.active_panel = None

    def cycle_next_panel(self) -> str | None:
        """Move focus forward and return new active panel."""
        if not self._open_panels:
            self.active_panel = None
            return None
        if self.active_panel not in self._open_panels:
            self.active_panel = self._open_panels[0]
            return self.active_panel
        index = self._open_panels.index(self.active_panel)
        self.active_panel = self._open_panels[(index + 1) % len(self._open_panels)]
        return self.active_panel

    def cycle_previous_panel(self) -> str | None:
        """Move focus backward and return new active panel."""
        if not self._open_panels:
            self.active_panel = None
            return None
        if self.active_panel not in self._open_panels:
            self.active_panel = self._open_panels[-1]
            return self.active_panel
        index = self._open_panels.index(self.active_panel)
        self.active_panel = self._open_panels[(index - 1) % len(self._open_panels)]
        return self.active_panel

    def begin_text_edit(self, panel: str) -> bool:
        """Start text-edit mode owned by a currently open panel."""
        panel_name = str(panel)
        if panel_name not in self._open_panels:
            return False
        self.text_edit_panel = panel_name
        return True

    def end_text_edit(self) -> None:
        """End current text-edit mode."""
        self.text_edit_panel = None

    def is_text_edit_active(self) -> bool:
        """Return True when any panel currently owns text-edit mode."""
        return self.text_edit_panel is not None
