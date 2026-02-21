"""Unit tests for deterministic DevShell text buffer editing behavior."""

from __future__ import annotations

from arcadeactions.dev.devshell_text_buffer import DevShellTextBuffer


def test_insert_text_appends_once_at_caret():
    """Single insert should mutate text exactly once and move caret accordingly."""
    buf = DevShellTextBuffer(text="1", caret=1, anchor=None)

    buf.insert_text("2")

    assert buf.text == "12"
    assert buf.caret == 2
    assert buf.anchor is None


def test_insert_text_replaces_active_selection():
    """Typing while selection is active should replace selected range."""
    buf = DevShellTextBuffer(text="1234", caret=4, anchor=2)

    buf.insert_text("x")

    assert buf.text == "12x"
    assert buf.caret == 3
    assert buf.anchor is None


def test_backspace_deletes_left_character_without_selection():
    """Backspace should remove one character left of caret when no selection exists."""
    buf = DevShellTextBuffer(text="123", caret=3, anchor=None)

    changed = buf.backspace()

    assert changed is True
    assert buf.text == "12"
    assert buf.caret == 2
    assert buf.anchor is None


def test_backspace_deletes_selection_range_when_present():
    """Backspace should delete selected range rather than a single character."""
    buf = DevShellTextBuffer(text="12345", caret=5, anchor=2)

    changed = buf.backspace()

    assert changed is True
    assert buf.text == "12"
    assert buf.caret == 2
    assert buf.anchor is None


def test_delete_removes_character_at_caret_without_selection():
    """Delete should remove one character at caret when no selection exists."""
    buf = DevShellTextBuffer(text="123", caret=1, anchor=None)

    changed = buf.delete()

    assert changed is True
    assert buf.text == "13"
    assert buf.caret == 1
    assert buf.anchor is None


def test_delete_removes_selection_when_present():
    """Delete should remove selected range and collapse caret."""
    buf = DevShellTextBuffer(text="12345", caret=4, anchor=1)

    changed = buf.delete()

    assert changed is True
    assert buf.text == "15"
    assert buf.caret == 1
    assert buf.anchor is None


def test_move_left_and_right_clamp_to_bounds():
    """Caret movement should clamp to valid text bounds."""
    buf = DevShellTextBuffer(text="123", caret=3, anchor=None)

    buf.move_right()
    assert buf.caret == 3

    buf.move_left()
    buf.move_left()
    buf.move_left()
    buf.move_left()
    assert buf.caret == 0
    assert buf.anchor is None


def test_move_to_line_edges():
    """Home/End moves should place caret at beginning/end and clear selection."""
    buf = DevShellTextBuffer(text="123", caret=1, anchor=0)

    buf.move_to_end()
    assert buf.caret == 3
    assert buf.anchor is None

    buf.move_to_start()
    assert buf.caret == 0
    assert buf.anchor is None


def test_set_text_resets_caret_to_end_and_clears_selection():
    """Setting text should normalize caret to end and clear any anchor."""
    buf = DevShellTextBuffer(text="abc", caret=1, anchor=0)

    buf.set_text("xyz")

    assert buf.text == "xyz"
    assert buf.caret == 3
    assert buf.anchor is None
