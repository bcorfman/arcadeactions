"""Unit tests for DevShell runtime mode and focus-visibility state."""

from __future__ import annotations

from arcadeactions.dev.devshell_focus import DevShellFocusManager
from arcadeactions.dev.devshell_state import DevShellMode, DevShellStateController


def test_mode_defaults_to_edit_live():
    """State controller should default to Edit-Live mode."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    state = DevShellStateController(focus_manager=focus)

    assert state.mode == DevShellMode.EDIT_LIVE
    assert state.is_preview_clean() is False


def test_toggle_preview_clean_switches_between_edit_and_preview_modes():
    """Preview toggle should switch between Edit-Live and Preview-Clean."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    state = DevShellStateController(focus_manager=focus)

    assert state.toggle_preview_clean() == DevShellMode.PREVIEW_CLEAN
    assert state.is_preview_clean() is True

    assert state.toggle_preview_clean() == DevShellMode.EDIT_LIVE
    assert state.is_preview_clean() is False


def test_toggle_preview_clean_is_noop_in_production_mode():
    """Preview toggle should not alter mode once in Production."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    state = DevShellStateController(focus_manager=focus)
    state.set_mode(DevShellMode.PRODUCTION)

    assert state.toggle_preview_clean() == DevShellMode.PRODUCTION
    assert state.mode == DevShellMode.PRODUCTION


def test_entering_production_clears_focus_and_text_edit():
    """Production mode should clear panel focus ownership and text-edit state."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    focus.set_active_panel("inspector")
    focus.begin_text_edit("inspector")
    state = DevShellStateController(focus_manager=focus)

    state.set_mode(DevShellMode.PRODUCTION)

    assert focus.active_panel is None
    assert focus.text_edit_panel is None


def test_focus_visual_state_marks_active_panel_and_focus_label():
    """Focus state should expose top-rail label and active panel flags."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    state = DevShellStateController(focus_manager=focus)
    state.set_active_panel("inspector")

    visual = state.focus_visual_state(panel_ids=["palette", "inspector", "llm"])

    assert visual.focus_label == "Focus: inspector"
    assert visual.panel_states["palette"].is_active is False
    assert visual.panel_states["inspector"].is_active is True
    assert visual.panel_states["llm"].is_active is False


def test_focus_visual_state_exposes_caret_only_for_text_edit_owner():
    """Caret-visibility flag should be true only for active text-edit panel."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    state = DevShellStateController(focus_manager=focus)
    state.set_active_panel("inspector")
    focus.begin_text_edit("inspector")

    visual = state.focus_visual_state(panel_ids=["palette", "inspector", "llm"])

    assert visual.panel_states["inspector"].show_caret is True
    assert visual.panel_states["palette"].show_caret is False
    assert visual.panel_states["llm"].show_caret is False


def test_focus_pulse_token_increments_on_focus_change():
    """Focus-change token should increment whenever active focus changes."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    state = DevShellStateController(focus_manager=focus)
    before = state.focus_pulse_token

    state.set_active_panel("palette")
    after_first = state.focus_pulse_token
    state.set_active_panel("llm")
    after_second = state.focus_pulse_token

    assert after_first > before
    assert after_second > after_first
