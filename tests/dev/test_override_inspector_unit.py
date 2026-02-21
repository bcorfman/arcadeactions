"""Unit tests for ArrangeOverrideInspector branch behavior."""

from __future__ import annotations

from pathlib import Path

from arcadeactions.dev.override_inspector import ArrangeOverrideInspector


class _Result:
    def __init__(self, changed: bool) -> None:
        self.changed = changed


def test_override_inspector_set_remove_and_undo(monkeypatch, tmp_path):
    """Set/remove operations should record inverse operations for undo."""
    path = tmp_path / "scene.py"
    inspector = ArrangeOverrideInspector(path, 10)

    overrides = [{"row": 0, "col": 1, "x": 20, "y": 30}]
    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.list_arrange_overrides", lambda *_args: list(overrides))

    calls: list[tuple[str, tuple[int, ...]]] = []

    def update_arrange_cell(_path: Path, _lineno: int, row: int, col: int, x: int, y: int):
        calls.append(("set", (row, col, x, y)))
        return _Result(True)

    def delete_arrange_override(_path: Path, _lineno: int, row: int, col: int):
        calls.append(("delete", (row, col)))
        return _Result(True)

    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.update_arrange_cell", update_arrange_cell)
    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.delete_arrange_override", delete_arrange_override)

    result_set = inspector.set_override(0, 1, 40, 50)
    assert result_set.changed is True
    assert inspector.can_undo() is True

    # Undo set should restore prior value.
    assert inspector.undo() is True
    assert calls[-1] == ("set", (0, 1, 20, 30))

    result_remove = inspector.remove_override(0, 1)
    assert result_remove.changed is True
    assert inspector.can_undo() is True
    assert inspector.undo() is True
    assert calls[-1] == ("set", (0, 1, 20, 30))


def test_override_inspector_handles_no_previous_entry_and_unknown_undo(monkeypatch, tmp_path):
    """New-cell set should undo via delete; unknown undo op should return False."""
    inspector = ArrangeOverrideInspector(tmp_path / "scene.py", 1)
    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.list_arrange_overrides", lambda *_args: [])
    monkeypatch.setattr(
        "arcadeactions.dev.override_inspector.sync.update_arrange_cell",
        lambda *_args: _Result(True),
    )
    delete_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "arcadeactions.dev.override_inspector.sync.delete_arrange_override",
        lambda _path, _lineno, row, col: (delete_calls.append((row, col)), _Result(True))[1],
    )

    assert inspector.set_override(2, 3, 100, 200).changed is True
    assert inspector.undo() is True
    assert delete_calls[-1] == (2, 3)

    inspector._undo_stack.append({"op": "unknown"})
    assert inspector.undo() is False


def test_override_inspector_no_change_and_empty_undo(monkeypatch, tmp_path):
    """No-change operations should not push undo entries; empty undo should return False."""
    inspector = ArrangeOverrideInspector(tmp_path / "scene.py", 3)
    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.list_arrange_overrides", lambda *_args: [])
    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.update_arrange_cell", lambda *_args: _Result(False))
    monkeypatch.setattr("arcadeactions.dev.override_inspector.sync.delete_arrange_override", lambda *_args: _Result(False))

    assert inspector.set_override(1, 1, 1, 1).changed is False
    assert inspector.remove_override(1, 1).changed is False
    assert inspector.can_undo() is False
    assert inspector.undo() is False
