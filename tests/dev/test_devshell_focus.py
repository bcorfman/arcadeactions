"""Unit tests for DevShell panel focus state and keyboard focus transitions."""

from __future__ import annotations

from arcadeactions.dev.devshell_focus import DevShellFocusManager


def test_focus_cycle_uses_open_panel_order():
    """Tab/Shift+Tab cycles should follow the current open-panel order."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    focus.set_active_panel("inspector")

    assert focus.cycle_next_panel() == "llm"
    assert focus.active_panel == "llm"

    assert focus.cycle_previous_panel() == "inspector"
    assert focus.active_panel == "inspector"


def test_focus_cycle_wraps_when_at_end():
    """Forward cycling should wrap from final panel back to first."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    focus.set_active_panel("llm")

    assert focus.cycle_next_panel() == "palette"
    assert focus.active_panel == "palette"


def test_focus_can_be_cleared_back_to_game_stage():
    """Clearing focus should return active panel to game-stage ownership."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    focus.set_active_panel("inspector")

    focus.clear_active_panel()

    assert focus.active_panel is None


def test_text_edit_mode_tracks_active_panel():
    """Text-edit state should be associated with the panel that owns editing."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    focus.set_active_panel("inspector")
    focus.begin_text_edit("inspector")

    assert focus.is_text_edit_active() is True
    assert focus.text_edit_panel == "inspector"

    focus.end_text_edit()
    assert focus.is_text_edit_active() is False
    assert focus.text_edit_panel is None


def test_updating_open_panels_drops_invalid_focus():
    """When an active panel is removed from open panels, focus should be cleared."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    focus.set_active_panel("inspector")

    focus.set_open_panels(["palette"])

    assert focus.active_panel is None
