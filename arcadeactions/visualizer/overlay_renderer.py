"""Overlay renderer for ACE visualizer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import arcade

from arcadeactions.visualizer._pyglet_compat import GLException
from arcadeactions.visualizer._text_rendering import _sync_text_objects, _TextSpec

if TYPE_CHECKING:
    from arcadeactions.visualizer.overlay import ActionCard, InspectorOverlay, TargetGroup


class OverlayRenderer:
    """
    Renders inspector overlay to screen using Arcade primitives.

    Uses arcade.Text objects for text rendering and ShapeElementList for
    progress bars and backgrounds. Follows dependency injection by receiving
    the overlay as a parameter.
    """

    def __init__(
        self,
        overlay: InspectorOverlay,
        font_size: int = 10,
        line_height: int = 14,
    ):
        """
        Initialize the overlay renderer.

        Args:
            overlay: Injected InspectorOverlay dependency
            font_size: Font size for text rendering
            line_height: Line height for text spacing
        """
        self.overlay = overlay
        self.font_size = font_size
        self.line_height = line_height

        # Text objects for rendering (created once, reused)
        self.text_objects: list[arcade.Text] = []
        self._text_specs: list[_TextSpec] = []
        self._last_text_specs: list[_TextSpec] = []

        # Store rectangle parameters for backgrounds and progress bars
        self._background_rects: list[tuple[float, float, float, float, arcade.Color]] = []
        self._progress_rects: list[tuple[float, float, float, float, arcade.Color]] = []

        # Cache measured text widths: text -> (width, is_exact)
        self._text_width_cache: dict[str, tuple[float, bool]] = {}

    def update(self) -> None:
        """
        Update rendering elements from overlay data.

        Recreates text objects and shapes based on current overlay state.
        """
        if not self.overlay.visible:
            self.text_objects = []
            self._text_specs = []
            self._last_text_specs = []
            self._background_rects = []
            self._progress_rects = []
            return

        # Clear existing renderables
        self._text_specs = []
        self._background_rects = []
        self._progress_rects = []

        window_width, window_height = self._get_window_size()
        title_text = self._build_title_text()
        text_width = self._get_title_width(title_text)
        x, y = self._compute_title_position(
            title_text,
            text_width,
            window_width,
            window_height,
        )
        self._text_specs.append(self._build_title_spec(title_text, x, y))
        _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)

    def _render_group(self, group: TargetGroup, start_y: int) -> int:
        """
        Render a target group.

        Args:
            group: Target group to render
            start_y: Starting Y position

        Returns:
            New Y position after rendering
        """
        current_y = start_y

        # Check if this group is highlighted
        is_highlighted = self.overlay.highlighted_target_id == group.target_id
        header_color = arcade.color.CYAN if is_highlighted else arcade.color.YELLOW

        # Render group header
        self._text_specs.append(
            _TextSpec(
                group.get_header_text(),
                self.overlay.x + 5,
                current_y,
                header_color,
                self.font_size,
                True,
            )
        )
        current_y -= self.line_height

        # Render cards
        for card in group.cards:
            current_y = self._render_card(card, current_y)

        return current_y

    def _render_card(self, card: ActionCard, start_y: int) -> int:
        """
        Render an action card.

        Args:
            card: Action card to render
            start_y: Starting Y position

        Returns:
            New Y position after rendering
        """
        current_y = start_y

        # Render card text
        display_text = card.get_display_text()
        for line in display_text.split("\n"):
            self._text_specs.append(
                _TextSpec(
                    line,
                    self.overlay.x + 15,
                    current_y,
                    arcade.color.LIGHT_GRAY,
                    self.font_size,
                )
            )
            current_y -= self.line_height

        # Render progress bar if available
        if card.snapshot.progress is not None:
            bar_width = card.get_progress_bar_width()
            bar_height = 4
            bar_x = self.overlay.x + 15
            bar_y = current_y - 2

            left = bar_x
            bottom = bar_y - bar_height / 2
            self._background_rects.append((left, bottom, card.width, bar_height, arcade.color.DARK_GRAY))

            if bar_width > 0:
                left = bar_x
                bottom = bar_y - bar_height / 2
                self._progress_rects.append((left, bottom, bar_width, bar_height, arcade.color.GREEN))

            current_y -= 10  # Space after progress bar

        return current_y

    def draw(self) -> None:
        """Draw all overlay elements to the screen."""
        if not self.overlay.visible:
            return

        # Only sync text objects if specs changed (optimization)
        if self._text_specs != self._last_text_specs:
            _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)

        # Draw shapes first (backgrounds, progress bars)
        for rect in self._background_rects:
            arcade.draw_lbwh_rectangle_filled(*rect)
        for rect in self._progress_rects:
            arcade.draw_lbwh_rectangle_filled(*rect)

        # Draw text on top
        try:
            for text_obj in self.text_objects:
                text_obj.draw()
        except GLException:
            self.text_objects = []
            self._last_text_specs = []
            _sync_text_objects(self.text_objects, self._text_specs, self._last_text_specs)
            for text_obj in self.text_objects:
                text_obj.draw()

    def _get_window_size(self) -> tuple[int, int]:
        try:
            window = arcade.get_window()
            return window.width, window.height
        except RuntimeError:
            return 1280, 720

    def _build_title_text(self) -> str:
        return f"ACE Visualizer - {self.overlay.get_total_action_count()} action(s)"

    def _get_title_width(self, title_text: str) -> float:
        font_size = self.font_size + 2
        cached_width = self._text_width_cache.get(title_text)
        if cached_width and cached_width[1]:
            return cached_width[0]

        measured_width: float | None = None
        measured_exactly = False
        try:
            temp_text = arcade.Text(
                title_text,
                0,
                0,
                arcade.color.WHITE,
                font_size,
                bold=True,
            )
            measured_width = temp_text.content_width
            measured_exactly = True
        except (AttributeError, RuntimeError, Exception):
            measured_width = None

        if measured_width is None:
            measured_width = self._estimate_text_width(title_text, font_size)

        self._text_width_cache[title_text] = (measured_width, measured_exactly)
        return measured_width

    def _estimate_text_width(self, text: str, font_size: int) -> float:
        char_width = font_size * 0.723
        return len(text) * char_width

    def _compute_title_position(
        self,
        title_text: str,
        text_width: float,
        window_width: int,
        window_height: int,
    ) -> tuple[float, float]:
        buffer = 20
        text_height = self.font_size + 2
        position = self.overlay.position
        if position == "upper_left":
            return buffer, window_height - buffer - text_height
        if position == "upper_right":
            return window_width - buffer - text_width, window_height - buffer - text_height
        if position == "lower_right":
            return window_width - buffer - text_width, buffer
        return buffer, buffer

    def _build_title_spec(self, title_text: str, x: float, y: float) -> _TextSpec:
        return _TextSpec(
            title_text,
            x,
            y,
            arcade.color.WHITE,
            self.font_size + 2,
            True,
        )
