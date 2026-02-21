"""Unit tests for overrides panel input helpers."""

from __future__ import annotations

import arcade

from arcadeactions.dev import overrides_input


class StubPanel:
    def __init__(self) -> None:
        self._open = True
        self.editing = False
        self._editing_field = "x"
        self.calls: list[tuple[str, object]] = []

    def is_open(self) -> bool:
        return self._open

    def handle_key(self, key: str) -> None:
        self.calls.append(("handle_key", key))

    def commit_edit(self) -> None:
        self.calls.append(("commit_edit", None))

    def start_edit(self, field: str | None = None) -> None:
        self.calls.append(("start_edit", field))

    def cancel_edit(self) -> None:
        self.calls.append(("cancel_edit", None))

    def handle_input_char(self, text: str) -> None:
        self.calls.append(("handle_input_char", text))

    def select_prev(self) -> None:
        self.calls.append(("select_prev", None))

    def select_next(self) -> None:
        self.calls.append(("select_next", None))

    def increment_selected(self, dx: int, dy: int) -> None:
        self.calls.append(("increment_selected", (dx, dy)))

    def get_selected(self) -> dict | None:
        return {"row": 1, "col": 2}

    def remove_override(self, row: int | None, col: int | None) -> None:
        self.calls.append(("remove_override", (row, col)))


def test_handle_overrides_panel_key_ctrl_z():
    panel = StubPanel()

    handled = overrides_input.handle_overrides_panel_key(panel, arcade.key.Z, arcade.key.MOD_CTRL)

    assert handled is True
    assert ("handle_key", "CTRL+Z") in panel.calls


def test_handle_overrides_panel_key_enter_starts_edit():
    panel = StubPanel()

    handled = overrides_input.handle_overrides_panel_key(panel, arcade.key.ENTER, 0)

    assert handled is True
    assert ("start_edit", None) in panel.calls


def test_handle_overrides_panel_text_routes_chars():
    panel = StubPanel()
    panel.editing = True

    handled = overrides_input.handle_overrides_panel_text(panel, "12")

    assert handled is True
    assert ("handle_input_char", "1") in panel.calls
    assert ("handle_input_char", "2") in panel.calls


def test_handle_overrides_panel_key_up_returns_false():
    panel = StubPanel()

    handled = overrides_input.handle_overrides_panel_key(panel, arcade.key.UP, 0)

    assert handled is False
    assert ("select_prev", None) not in panel.calls


def test_handle_overrides_panel_key_down_selects_next():
    panel = StubPanel()

    handled = overrides_input.handle_overrides_panel_key(panel, arcade.key.DOWN, 0)

    assert handled is True
    assert ("select_next", None) in panel.calls


def test_handle_overrides_panel_key_non_open_or_none_returns_false():
    panel = StubPanel()
    panel._open = False

    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.ENTER, 0) is False
    assert overrides_input.handle_overrides_panel_key(None, arcade.key.ENTER, 0) is False


def test_handle_overrides_panel_key_editing_and_navigation_variants():
    panel = StubPanel()
    panel.editing = True

    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.ENTER, 0) is True
    assert ("commit_edit", None) in panel.calls
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.ESCAPE, 0) is True
    assert ("cancel_edit", None) in panel.calls
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.BACKSPACE, 0) is True
    assert ("handle_input_char", "\b") in panel.calls
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.TAB, 0) is True
    assert panel._editing_field == "y"

    panel.editing = False
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.X, 0) is True
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.Y, 0) is True
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.LEFT, 0) is True
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.RIGHT, 0) is True
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.PAGEUP, 0) is True
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.PAGEDOWN, 0) is True
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.DELETE, 0) is True


def test_handle_overrides_panel_key_undo_and_text_exception_paths():
    panel = StubPanel()

    def raise_key(_key: str) -> None:
        raise RuntimeError("boom")

    panel.handle_key = raise_key
    assert overrides_input.handle_overrides_panel_key(panel, arcade.key.Z, arcade.key.MOD_CTRL) is True

    panel.editing = True

    def raise_input(_text: str) -> None:
        raise RuntimeError("boom")

    panel.handle_input_char = raise_input
    assert overrides_input.handle_overrides_panel_text(panel, "abc") is True


def test_handle_overrides_panel_text_requires_open_and_editing():
    panel = StubPanel()

    assert overrides_input.handle_overrides_panel_text(panel, "x") is False
    panel.editing = True
    panel._open = False
    assert overrides_input.handle_overrides_panel_text(panel, "x") is False
    assert overrides_input.handle_overrides_panel_text(None, "x") is False
