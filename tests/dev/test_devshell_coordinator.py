"""Unit tests for DevShell coordinator composition behavior."""

from __future__ import annotations

import arcade

from arcadeactions.dev.devshell_coordinator import DevShellCoordinator


class _GameTarget:
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


class _PanelTarget:
    def __init__(self) -> None:
        self.keys: list[tuple[int, int]] = []
        self.text: list[str] = []
        self.motion: list[int] = []
        self.visible = True

    def on_key_press(self, key: int, modifiers: int) -> bool:
        self.keys.append((key, modifiers))
        return True

    def on_text(self, text: str) -> bool:
        self.text.append(text)
        return True

    def on_text_motion(self, motion: int) -> bool:
        self.motion.append(motion)
        return True


def test_coordinator_routes_to_active_panel_in_edit_live_mode():
    """With active panel focus, key/text/motion should route to that panel."""
    game = _GameTarget()
    inspector = _PanelTarget()
    coordinator = DevShellCoordinator(
        game_target=game,
        panel_targets={"inspector": inspector},
        panel_order=["inspector"],
        transient_panels=set(),
    )
    coordinator.set_active_panel("inspector")
    coordinator.focus_manager.begin_text_edit("inspector")

    assert coordinator.route_key_press(arcade.key.A, 0) is True
    assert coordinator.route_text("x") is True
    assert coordinator.route_text_motion(arcade.key.MOTION_DELETE) is True

    assert inspector.keys == [(arcade.key.A, 0)]
    assert inspector.text == ["x"]
    assert inspector.motion == [arcade.key.MOTION_DELETE]
    assert game.keys == []
    assert game.text == []
    assert game.motion == []


def test_coordinator_routes_to_game_in_preview_clean_mode():
    """Preview-Clean mode should bypass panel routing and hit game target directly."""
    game = _GameTarget()
    inspector = _PanelTarget()
    coordinator = DevShellCoordinator(
        game_target=game,
        panel_targets={"inspector": inspector},
        panel_order=["inspector"],
        transient_panels=set(),
    )
    coordinator.set_active_panel("inspector")
    coordinator.focus_manager.begin_text_edit("inspector")
    coordinator.set_preview_clean(True)

    assert coordinator.route_key_press(arcade.key.A, 0) is True
    assert coordinator.route_text("x") is True
    assert coordinator.route_text_motion(arcade.key.MOTION_DELETE) is True

    assert game.keys == [(arcade.key.A, 0)]
    assert game.text == ["x"]
    assert game.motion == [arcade.key.MOTION_DELETE]
    assert inspector.keys == []
    assert inspector.text == []
    assert inspector.motion == []


def test_coordinator_handles_tab_focus_cycling():
    """Tab/Shift+Tab should cycle coordinator focus across panel order."""
    game = _GameTarget()
    palette = _PanelTarget()
    inspector = _PanelTarget()
    coordinator = DevShellCoordinator(
        game_target=game,
        panel_targets={"palette": palette, "inspector": inspector},
        panel_order=["palette", "inspector"],
        transient_panels=set(),
    )
    coordinator.set_active_panel("palette")

    coordinator.route_key_press(arcade.key.TAB, 0)
    assert coordinator.focus_manager.active_panel == "inspector"

    coordinator.route_key_press(arcade.key.TAB, arcade.key.MOD_SHIFT)
    assert coordinator.focus_manager.active_panel == "palette"


def test_coordinator_closes_transient_panel_on_escape():
    """Esc should close transient panel before routing to game-stage ownership."""
    game = _GameTarget()
    palette = _PanelTarget()
    closed: list[str] = []
    coordinator = DevShellCoordinator(
        game_target=game,
        panel_targets={"palette": palette},
        panel_order=["palette"],
        transient_panels={"palette"},
        close_panel=closed.append,
    )
    coordinator.set_active_panel("palette")

    assert coordinator.route_key_press(arcade.key.ESCAPE, 0) is True
    assert closed == ["palette"]
    assert coordinator.focus_manager.active_panel is None
