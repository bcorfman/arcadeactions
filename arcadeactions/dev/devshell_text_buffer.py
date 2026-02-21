"""Deterministic text-buffer editing model for DevShell panels."""

from __future__ import annotations


class DevShellTextBuffer:
    """Simple text/caret/selection buffer with explicit mutation operations."""

    def __init__(self, *, text: str = "", caret: int = 0, anchor: int | None = None) -> None:
        self.text = str(text)
        self.caret = self._clamp_index(int(caret))
        if anchor is None:
            self.anchor: int | None = None
        else:
            self.anchor = self._clamp_index(int(anchor))

    def _clamp_index(self, index: int) -> int:
        text_len = len(self.text)
        if index < 0:
            return 0
        if index > text_len:
            return text_len
        return index

    def _selection_bounds(self) -> tuple[int, int]:
        if self.anchor is None:
            return (self.caret, self.caret)
        left = min(self.anchor, self.caret)
        right = max(self.anchor, self.caret)
        return (left, right)

    def _replace_selection(self, inserted: str) -> None:
        left, right = self._selection_bounds()
        self.text = self.text[:left] + inserted + self.text[right:]
        self.caret = left + len(inserted)
        self.anchor = None

    def set_text(self, text: str) -> None:
        """Replace full text and normalize caret to end."""
        self.text = str(text)
        self.caret = len(self.text)
        self.anchor = None

    def insert_text(self, inserted: str) -> None:
        """Insert text at caret, replacing current selection if present."""
        self._replace_selection(str(inserted))

    def backspace(self) -> bool:
        """Delete one character left of caret, or current selection."""
        left, right = self._selection_bounds()
        if left != right:
            self._replace_selection("")
            return True
        if self.caret <= 0:
            return False
        self.text = self.text[: self.caret - 1] + self.text[self.caret :]
        self.caret -= 1
        self.anchor = None
        return True

    def delete(self) -> bool:
        """Delete one character at caret, or current selection."""
        left, right = self._selection_bounds()
        if left != right:
            self._replace_selection("")
            return True
        if self.caret >= len(self.text):
            return False
        self.text = self.text[: self.caret] + self.text[self.caret + 1 :]
        self.anchor = None
        return True

    def move_left(self) -> None:
        """Move caret left by one and clear selection."""
        self.caret = self._clamp_index(self.caret - 1)
        self.anchor = None

    def move_right(self) -> None:
        """Move caret right by one and clear selection."""
        self.caret = self._clamp_index(self.caret + 1)
        self.anchor = None

    def move_to_start(self) -> None:
        """Move caret to beginning of text and clear selection."""
        self.caret = 0
        self.anchor = None

    def move_to_end(self) -> None:
        """Move caret to end of text and clear selection."""
        self.caret = len(self.text)
        self.anchor = None
