"""Unit tests for DevShell input routing and layered Esc behavior."""

from __future__ import annotations

import arcade

from arcadeactions.dev.devshell_focus import DevShellFocusManager
from arcadeactions.dev.devshell_input_router import DevShellInputRouter


class _PanelStub:
    def __init__(self) -> None:
        self.keys: list[tuple[int, int]] = []
        self.text: list[str] = []
        self.motion: list[int] = []
        self.consume_keys = True

    def on_key_press(self, key: int, modifiers: int) -> bool:
        self.keys.append((key, modifiers))
        return self.consume_keys

    def on_text(self, text: str) -> bool:
        self.text.append(text)
        return True

    def on_text_motion(self, motion: int) -> bool:
        self.motion.append(motion)
        return True


class _GameStub:
    def __init__(self) -> None:
        self.keys: list[tuple[int, int]] = []
        self.text: list[str] = []
        self.motion: list[int] = []

    def on_key_press(self, key: int, modifiers: int) -> bool:
        self.keys.append((key, modifiers))
        return True

    def on_text(self, text: str) -> bool:
        self.text.append(text)
        return True

    def on_text_motion(self, motion: int) -> bool:
        self.motion.append(motion)
        return True


def test_tab_cycles_focus_to_next_panel():
    """Tab should cycle focus forward across currently open panels."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    focus.set_active_panel("palette")
    game = _GameStub()
    router = DevShellInputRouter(focus_manager=focus, game_target=game, panel_targets={})

    handled = router.route_key_press(arcade.key.TAB, 0)

    assert handled is True
    assert focus.active_panel == "inspector"
    assert game.keys == []


def test_shift_tab_cycles_focus_to_previous_panel():
    """Shift+Tab should cycle focus backward across currently open panels."""
    focus = DevShellFocusManager(open_panels=["palette", "inspector", "llm"])
    focus.set_active_panel("inspector")
    game = _GameStub()
    router = DevShellInputRouter(focus_manager=focus, game_target=game, panel_targets={})

    handled = router.route_key_press(arcade.key.TAB, arcade.key.MOD_SHIFT)

    assert handled is True
    assert focus.active_panel == "palette"
    assert game.keys == []


def test_esc_exits_text_edit_before_other_actions():
    """Esc should exit text-edit mode first when a panel is actively editing text."""
    focus = DevShellFocusManager(open_panels=["inspector"])
    focus.set_active_panel("inspector")
    focus.begin_text_edit("inspector")
    game = _GameStub()
    router = DevShellInputRouter(focus_manager=focus, game_target=game, panel_targets={})

    handled = router.route_key_press(arcade.key.ESCAPE, 0)

    assert handled is True
    assert focus.is_text_edit_active() is False
    assert focus.active_panel == "inspector"
    assert game.keys == []


def test_esc_closes_transient_panel_when_not_text_editing():
    """Esc should close focused transient panels before clearing stage focus."""
    closed: list[str] = []
    focus = DevShellFocusManager(open_panels=["palette", "inspector"])
    focus.set_active_panel("palette")
    game = _GameStub()
    router = DevShellInputRouter(
        focus_manager=focus,
        game_target=game,
        panel_targets={},
        transient_panels={"palette"},
        close_panel=closed.append,
    )

    handled = router.route_key_press(arcade.key.ESCAPE, 0)

    assert handled is True
    assert closed == ["palette"]
    assert focus.active_panel is None
    assert game.keys == []


def test_esc_clears_focus_to_stage_when_no_text_edit_or_transient_panel():
    """Esc should clear panel focus back to stage when nothing else should close."""
    focus = DevShellFocusManager(open_panels=["inspector"])
    focus.set_active_panel("inspector")
    game = _GameStub()
    router = DevShellInputRouter(focus_manager=focus, game_target=game, panel_targets={})

    handled = router.route_key_press(arcade.key.ESCAPE, 0)

    assert handled is True
    assert focus.active_panel is None
    assert game.keys == []


def test_text_and_motion_route_only_to_focused_text_edit_panel():
    """Text events should route to focused editing panel and not to game input."""
    inspector = _PanelStub()
    focus = DevShellFocusManager(open_panels=["inspector"])
    focus.set_active_panel("inspector")
    focus.begin_text_edit("inspector")
    game = _GameStub()
    router = DevShellInputRouter(
        focus_manager=focus,
        game_target=game,
        panel_targets={"inspector": inspector},
    )

    assert router.route_text("a") is True
    assert router.route_text_motion(arcade.key.MOTION_BACKSPACE) is True

    assert inspector.text == ["a"]
    assert inspector.motion == [arcade.key.MOTION_BACKSPACE]
    assert game.text == []
    assert game.motion == []


def test_preview_clean_routes_to_game_input():
    """Preview-Clean mode should route input directly to game target."""
    inspector = _PanelStub()
    focus = DevShellFocusManager(open_panels=["inspector"])
    focus.set_active_panel("inspector")
    focus.begin_text_edit("inspector")
    game = _GameStub()
    router = DevShellInputRouter(
        focus_manager=focus,
        game_target=game,
        panel_targets={"inspector": inspector},
    )
    router.set_preview_clean(True)

    assert router.route_key_press(arcade.key.A, 0) is True
    assert router.route_text("x") is True
    assert router.route_text_motion(arcade.key.MOTION_DELETE) is True

    assert game.keys == [(arcade.key.A, 0)]
    assert game.text == ["x"]
    assert game.motion == [arcade.key.MOTION_DELETE]
    assert inspector.keys == []
    assert inspector.text == []
    assert inspector.motion == []
