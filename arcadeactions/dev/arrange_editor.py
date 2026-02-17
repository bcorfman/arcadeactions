"""Helpers for editing arrange_grid call parameters from DevVisualizer."""

from __future__ import annotations

from pathlib import Path

from arcadeactions.dev import code_parser, sync


class ArrangeGridEditor:
    """Model for reading/updating one arrange_grid call in source code."""

    SETTING_ORDER = ("rows", "cols", "start_x", "start_y", "spacing_x", "spacing_y")

    def __init__(self, file_path: str | Path, lineno: int) -> None:
        self.file_path = Path(file_path)
        self.lineno = int(lineno)
        self._settings_cache: list[tuple[str, str]] | None = None

    def list_settings(self) -> list[tuple[str, str]]:
        if self._settings_cache is None:
            self._settings_cache = self._load_settings()
        return list(self._settings_cache)

    def current_layout_kwargs(self) -> dict[str, float | int]:
        settings = dict(self.list_settings())
        return {
            "rows": self._parse_int_setting("rows", settings["rows"]),
            "cols": self._parse_int_setting("cols", settings["cols"]),
            "start_x": self._parse_float_setting("start_x", settings["start_x"]),
            "start_y": self._parse_float_setting("start_y", settings["start_y"]),
            "spacing_x": self._parse_float_setting("spacing_x", settings["spacing_x"]),
            "spacing_y": self._parse_float_setting("spacing_y", settings["spacing_y"]),
        }

    def set_setting(self, name: str, value_text: str) -> bool:
        if name not in self.SETTING_ORDER:
            raise KeyError(f"Unsupported arrange setting: {name}")
        normalized = self._normalize_setting(name, value_text)
        result = sync.update_arrange_call(self.file_path, self.lineno, name, normalized)
        if self._settings_cache is None:
            self._settings_cache = self._load_settings()
        updated: list[tuple[str, str]] = []
        for setting_name, current_value in self._settings_cache:
            if setting_name == name:
                updated.append((setting_name, normalized))
            else:
                updated.append((setting_name, current_value))
        self._settings_cache = updated
        return bool(result.changed)

    def _load_settings(self) -> list[tuple[str, str]]:
        kwargs = self._current_kwargs()
        settings: list[tuple[str, str]] = []
        for name in self.SETTING_ORDER:
            default_value = self._default_value(name)
            settings.append((name, kwargs.get(name, default_value)))
        return settings

    def _current_kwargs(self) -> dict[str, str]:
        try:
            _assignments, arrange_calls = code_parser.parse_file(str(self.file_path))
        except Exception:
            return {}
        for call in arrange_calls:
            if int(call.lineno) == self.lineno:
                return {str(key): str(value) for key, value in call.kwargs.items()}
        return {}

    @staticmethod
    def _default_value(name: str) -> str:
        defaults = {
            "rows": "5",
            "cols": "10",
            "start_x": "100",
            "start_y": "500",
            "spacing_x": "60.0",
            "spacing_y": "50.0",
        }
        return defaults[name]

    def _normalize_setting(self, name: str, value_text: str) -> str:
        if name in ("rows", "cols"):
            return str(self._parse_int_setting(name, value_text))
        parsed = self._parse_float_setting(name, value_text)
        if parsed.is_integer():
            return str(int(parsed))
        return str(parsed)

    @staticmethod
    def _parse_int_setting(name: str, value_text: str) -> int:
        try:
            parsed = int(value_text.strip())
        except ValueError as exc:
            raise ValueError(f"{name} must be a positive integer") from exc
        if parsed <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return parsed

    @staticmethod
    def _parse_float_setting(name: str, value_text: str) -> float:
        try:
            return float(value_text.strip())
        except ValueError as exc:
            raise ValueError(f"{name} must be a number") from exc
