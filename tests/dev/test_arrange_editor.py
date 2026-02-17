"""Unit tests for arrange-grid editor model."""

from __future__ import annotations

from pathlib import Path

import pytest

from arcadeactions.dev.arrange_editor import ArrangeGridEditor


def _write_arrange_file(tmp_path: Path, call_src: str) -> tuple[Path, int]:
    file_path = tmp_path / "scene.py"
    source = f"from arcadeactions import arrange_grid\n{call_src}\n"
    file_path.write_text(source, encoding="utf-8")
    return file_path, 2


def test_list_settings_reads_kwargs_from_arrange_call(tmp_path: Path):
    file_path, lineno = _write_arrange_file(
        tmp_path,
        "arrange_grid(sprites=s, rows=2, cols=3, start_x=10, start_y=20, spacing_x=30, spacing_y=40)",
    )
    editor = ArrangeGridEditor(file_path, lineno)

    settings = dict(editor.list_settings())

    assert settings["rows"] == "2"
    assert settings["cols"] == "3"
    assert settings["start_x"] == "10"
    assert settings["start_y"] == "20"
    assert settings["spacing_x"] == "30"
    assert settings["spacing_y"] == "40"


def test_set_setting_updates_source_and_exposes_new_value(tmp_path: Path):
    file_path, lineno = _write_arrange_file(
        tmp_path,
        "arrange_grid(sprites=s, rows=2, cols=3, start_x=10, start_y=20, spacing_x=30, spacing_y=40)",
    )
    editor = ArrangeGridEditor(file_path, lineno)

    assert editor.set_setting("start_x", "125") is True
    settings = dict(editor.list_settings())
    assert settings["start_x"] == "125"
    assert "start_x=125" in file_path.read_text(encoding="utf-8")


def test_set_setting_validates_rows_and_cols_as_positive_int(tmp_path: Path):
    file_path, lineno = _write_arrange_file(
        tmp_path,
        "arrange_grid(sprites=s, rows=2, cols=3, start_x=10, start_y=20, spacing_x=30, spacing_y=40)",
    )
    editor = ArrangeGridEditor(file_path, lineno)

    with pytest.raises(ValueError, match="rows must be a positive integer"):
        editor.set_setting("rows", "0")
    with pytest.raises(ValueError, match="cols must be a positive integer"):
        editor.set_setting("cols", "-4")


def test_list_settings_falls_back_to_defaults_when_parse_fails(tmp_path: Path, mocker):
    file_path, lineno = _write_arrange_file(
        tmp_path,
        "arrange_grid(sprites=s, rows=2, cols=3, start_x=10, start_y=20, spacing_x=30, spacing_y=40)",
    )
    editor = ArrangeGridEditor(file_path, lineno)
    mocker.patch("arcadeactions.dev.arrange_editor.code_parser.parse_file", side_effect=RuntimeError("parse failed"))

    settings = dict(editor.list_settings())

    assert settings["rows"] == "5"
    assert settings["cols"] == "10"
