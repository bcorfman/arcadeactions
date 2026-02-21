"""Panel renderers for ACE visualizer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade
from pyglet.gl.lib import GLException

from arcadeactions.visualizer._text_rendering import _TextSpec, _sync_text_objects

if TYPE_CHECKING:
    from arcadeactions.visualizer.condition_panel import ConditionDebugger, ConditionEntry
    from arcadeactions.visualizer.guides import GuideManager
    from arcadeactions.visualizer.overlay import InspectorOverlay
    from arcadeactions.visualizer.timeline import TimelineEntry, TimelineStrip


class ConditionPanelRenderer:
    """Render the condition debugger panel."""

    def __init__(
        self,
        debugger: ConditionDebugger,
        *,
        width: int = 320,
        max_rows: int = 14,
        font_size: int = 10,
        line_height: int = 16,
        margin: int = 8,
    ) -> None:
        self.debugger = debugger
        self.width = width
        self.max_rows = max_rows
        self.font_size = font_size
        self.line_height = line_height
        self.margin = margin

        self.text_objects: list[arcade.Text] = []
        self._text_specs: list[_TextSpec] = []
        self._last_text_specs: list[_TextSpec] = []
        self._background_rect: tuple[float, float, float, float, arcade.Color] | None = None
        self._border_rect: tuple[float, float, float, float, arcade.Color] | None = None
        self._visible: bool = False

    def update(self, visible: bool) -> None:
        self._visible = visible
        self._reset_frame_state()

        if not visible:
            self.text_objects = []
            self._last_text_specs = []
            return

        top, left = self._compute_panel_origin()
        display_entries = self._get_display_entries()

        current_y = top - self.margin
        self._text_specs.append(self._build_title_spec(left, current_y))
        current_y -= self.line_height

        if display_entries is None:
            self._text_specs.append(self._build_empty_spec(left, current_y))
            current_y -= self.line_height
        else:
            for entry in display_entries:
                self._text_specs.append(self._build_entry_spec(entry, left, current_y))
                current_y -= self.line_height

        self._background_rect, self._border_rect = self._build_panel_rects(left, top, current_y)

    def draw(self) -> None:
        if not self._visible:
            return

        _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)

        if self._background_rect is not None:
            arcade.draw_lbwh_rectangle_filled(*self._background_rect)
        if self._border_rect is not None:
            left, bottom, right, top, color = self._border_rect
            arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, color, border_width=1)
        try:
            for text_obj in self.text_objects:
                text_obj.draw()
        except GLException:
            self.text_objects = []
            self._last_text_specs = []
            _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)
            for text_obj in self.text_objects:
                text_obj.draw()

    def _reset_frame_state(self) -> None:
        self._text_specs = []
        self._background_rect = None
        self._border_rect = None

    def _compute_panel_origin(self) -> tuple[float, float]:
        try:
            window = arcade.get_window()
            top = window.height - self.margin
            left = window.width - self.width - self.margin
        except RuntimeError:
            top = 720 - self.margin
            left = 1280 - self.width - self.margin
        return top, left

    def _get_display_entries(self) -> Iterable[ConditionEntry] | None:
        entries = self.debugger.entries
        rows = min(len(entries), self.max_rows)
        if rows == 0:
            return None
        return entries[:rows]

    def _build_title_spec(self, left: float, current_y: float) -> _TextSpec:
        return _TextSpec(
            "Condition Debugger",
            left + self.margin,
            current_y,
            arcade.color.WHITE,
            self.font_size + 1,
            True,
        )

    def _build_empty_spec(self, left: float, current_y: float) -> _TextSpec:
        return _TextSpec(
            "No condition evaluations yet",
            left + self.margin,
            current_y,
            arcade.color.LIGHT_GRAY,
            self.font_size,
        )

    def _build_entry_spec(self, entry: ConditionEntry, left: float, current_y: float) -> _TextSpec:
        tag = entry.tag or "-"
        result = self._truncate_result(str(entry.result))
        line = f"{entry.action_type} [{tag}] -> {result}"
        return _TextSpec(
            line,
            left + self.margin,
            current_y,
            arcade.color.LIGHT_GRAY,
            self.font_size,
        )

    def _truncate_result(self, result: str) -> str:
        if len(result) <= 60:
            return result
        return result[:57] + "..."

    def _build_panel_rects(
        self, left: float, top: float, current_y: float
    ) -> tuple[
        tuple[float, float, float, float, arcade.Color],
        tuple[float, float, float, float, arcade.Color],
    ]:
        height = top - current_y + self.margin
        bottom = top - height
        background = (left, bottom, self.width, height, (20, 24, 38, 200))
        border = (left, bottom, left + self.width, bottom + height, (90, 105, 135, 220))
        return background, border


class TimelineRenderer:
    """Render the timeline strip."""

    def __init__(
        self,
        timeline: TimelineStrip,
        *,
        width: int = 420,
        height: int = 90,
        margin: int = 8,
        row_height: int = 18,
        font_size: int = 9,
        target_names_provider: Callable[[], dict[int, str]] | None = None,
        highlighted_target_provider: Callable[[], int | None] | None = None,
    ) -> None:
        self.timeline = timeline
        self.width = width
        self.height = height
        self.margin = margin
        self.row_height = row_height
        self.font_size = font_size
        self.target_names_provider = target_names_provider
        self.highlighted_target_provider = highlighted_target_provider

        self._background_rect: tuple[float, float, float, float, arcade.Color] | None = None
        self._bars: list[tuple[float, float, float, float, arcade.Color]] = []
        self._highlight_outlines: list[tuple[float, float, float, float]] = []  # Bars to outline in green
        self.text_objects: list[arcade.Text] = []
        self._text_specs: list[_TextSpec] = []
        self._last_text_specs: list[_TextSpec] = []

    def set_font_size(self, font_size: float) -> None:
        """Set the font size used for timeline labels."""
        if font_size <= 0:
            raise ValueError("font_size must be positive")
        self.font_size = font_size
        # Force regeneration of text objects on next draw
        self._text_specs = []
        self._last_text_specs = []
        self.text_objects = []

    def update(self) -> None:
        self._reset_frame_state()

        highlighted_target_id = self._resolve_highlighted_target()
        entries = self._get_entries()
        if not entries:
            self.text_objects = []
            self._last_text_specs = []
            return

        base_left, base_bottom, base_width, base_height = self._compute_base_geometry()
        frame_min, frame_span, current_frame = self._compute_frame_span(entries)
        rows, row_height = self._compute_rows(base_height, len(entries))

        self._background_rect = (
            base_left,
            base_bottom,
            base_width,
            base_height,
            (15, 18, 30, 200),
        )

        self._build_rows(
            entries,
            rows,
            base_left,
            base_bottom,
            base_width,
            base_height,
            row_height,
            frame_min,
            frame_span,
            current_frame,
            highlighted_target_id,
        )

    def _reset_frame_state(self) -> None:
        self._background_rect = None
        self._bars = []
        self._highlight_outlines = []
        self._text_specs = []

    def _resolve_highlighted_target(self) -> int | None:
        if self.highlighted_target_provider is None:
            return None
        try:
            return self.highlighted_target_provider()
        except Exception:
            return None

    def _get_entries(self) -> list[TimelineEntry]:
        return [entry for entry in self.timeline.entries if entry.start_frame is not None]

    def _compute_base_geometry(self) -> tuple[float, float, float, float]:
        try:
            window = arcade.get_window()
            base_width = min(self.width, window.width - 2 * self.margin)
        except RuntimeError:
            base_width = self.width
        return self.margin, self.margin, base_width, self.height

    def _compute_frame_span(self, entries: list[TimelineEntry]) -> tuple[int, int, int]:
        frame_min = min(entry.start_frame or 0 for entry in entries)
        current_frame = self.timeline.debug_store.current_frame
        frame_max = max(max(entry.end_frame or current_frame, entry.start_frame or frame_min) for entry in entries)
        if frame_max == frame_min:
            frame_max += 1
        return frame_min, frame_max - frame_min, current_frame

    def _compute_rows(self, base_height: float, entry_count: int) -> tuple[int, float]:
        max_rows = max(1, int(base_height // self.row_height)) if self.row_height else 1
        rows = min(entry_count, max_rows)
        row_height = base_height / rows if rows else base_height
        return rows, row_height

    def _build_rows(
        self,
        entries: list[TimelineEntry],
        rows: int,
        base_left: float,
        base_bottom: float,
        base_width: float,
        base_height: float,
        row_height: float,
        frame_min: int,
        frame_span: int,
        current_frame: int,
        highlighted_target_id: int | None,
    ) -> None:
        for index, entry in enumerate(entries[:rows]):
            left, right, bottom, top = self._compute_bar_geometry(
                entry,
                index,
                base_left,
                base_bottom,
                base_width,
                base_height,
                row_height,
                frame_min,
                frame_span,
                current_frame,
            )
            color = self._select_bar_color(entry)
            self._bars.append((left, bottom, right, top, color))
            if highlighted_target_id is not None and entry.target_id == highlighted_target_id:
                self._highlight_outlines.append((left, bottom, right, top))

            label_text, label_color, label_x, label_y = self._build_label(entry, left, right, bottom, row_height)
            self._text_specs.append(_TextSpec(label_text, label_x, label_y, label_color, self.font_size))

    def _compute_bar_geometry(
        self,
        entry: TimelineEntry,
        index: int,
        base_left: float,
        base_bottom: float,
        base_width: float,
        base_height: float,
        row_height: float,
        frame_min: int,
        frame_span: int,
        current_frame: int,
    ) -> tuple[float, float, float, float]:
        start = entry.start_frame or frame_min
        end = entry.end_frame if entry.end_frame is not None else current_frame
        if end < start:
            end = start
        left = base_left + ((start - frame_min) / frame_span) * base_width
        right = base_left + ((end - frame_min) / frame_span) * base_width
        if right - left < 2:
            right = left + 2
        top = base_bottom + base_height - index * row_height
        bottom = top - row_height
        return left, right, bottom, top

    def _select_bar_color(self, entry: TimelineEntry) -> arcade.Color:
        if entry.target_type == "SpriteList":
            return arcade.color.CYAN if entry.is_active else arcade.color.TEAL
        return arcade.color.ORANGE if entry.is_active else arcade.color.DARK_ORANGE

    def _build_label(
        self,
        entry: TimelineEntry,
        left: float,
        right: float,
        bottom: float,
        row_height: float,
    ) -> tuple[str, arcade.Color, float, float]:
        target_label = self._get_target_label(entry)
        if entry.tag is not None:
            label_text = f"{entry.action_type}[{entry.tag}]: {target_label}"
        else:
            label_text = f"{entry.action_type}: {target_label}"

        label_y = bottom + max(2.0, (row_height - self.font_size) / 2)
        label_x, label_color = self._compute_label_position(label_text, left, right)
        return label_text, label_color, label_x, label_y

    def _get_target_label(self, entry: TimelineEntry) -> str:
        target_name = None
        if entry.target_id is not None and self.target_names_provider is not None:
            try:
                names = self.target_names_provider()
                if names:
                    target_name = names.get(entry.target_id)
            except Exception:
                target_name = None

        if target_name:
            return target_name
        if entry.target_id is not None:
            hex_id = hex(entry.target_id)[-4:]
            target_type_label = entry.target_type or "Unknown"
            return f"{target_type_label}#{hex_id}"
        return entry.target_type or "Unknown"

    def _compute_label_position(self, label_text: str, left: float, right: float) -> tuple[float, arcade.Color]:
        bar_width = right - left
        temp_text = arcade.Text(label_text, 0, 0, arcade.color.BLACK, self.font_size)
        actual_text_width = temp_text.content_width
        text_padding = 8
        if actual_text_width + text_padding < bar_width:
            return left + 4, arcade.color.BLACK
        return left - actual_text_width - 8, arcade.color.WHITE

    def draw(self) -> None:
        if self._background_rect is None:
            return
        try:
            arcade.draw_lbwh_rectangle_filled(*self._background_rect)
            for left, bottom, right, top, color in self._bars:
                arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)

            # Draw green outlines for highlighted bars
            for left, bottom, right, top in self._highlight_outlines:
                arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.LIME_GREEN, border_width=3)
        except GLException:
            pass

        _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)
        try:
            for label in self.text_objects:
                label.draw()
        except GLException:
            self.text_objects = []
            self._last_text_specs = []
            _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)
            try:
                for label in self.text_objects:
                    label.draw()
            except GLException:
                return


class GuideRenderer:
    """Render velocity, bounds, and path guides."""

    def __init__(self, guide_manager: GuideManager) -> None:
        self.guide_manager = guide_manager

    def update(self) -> None:
        # Guides operate on live data; no cached state necessary.
        return

    def draw(self) -> None:
        velocity = self.guide_manager.velocity_guide
        if velocity.enabled:
            for x1, y1, x2, y2 in velocity.arrows:
                arcade.draw_line(x1, y1, x2, y2, velocity.color, 2)

        bounds = self.guide_manager.bounds_guide
        if bounds.enabled:
            for left, bottom, right, top in bounds.rectangles:
                arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, bounds.color, border_width=2)

        path = self.guide_manager.path_guide
        if path.enabled:
            for points in path.paths:
                if len(points) >= 2:
                    arcade.draw_line_strip(points, path.color, 2)

        highlight = self.guide_manager.highlight_guide
        if highlight.enabled:
            for left, bottom, right, top in highlight.rectangles:
                arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, highlight.color, border_width=3)
