"""Drawing helpers for DevVisualizer overlays."""

from __future__ import annotations

from typing import Any

import arcade

from arcadeactions.dev.visualizer_protocols import SpriteWithSourceMarkers
from arcadeactions.dev.window_utils import has_window_context


def draw_visualizer(dev_viz: Any) -> None:
    if not dev_viz.visible:
        return

    if dev_viz.window is None:
        return

    if not has_window_context(dev_viz.window):
        return

    try:
        _draw_indicator(dev_viz)
        if not _draw_selection(dev_viz):
            return
        _draw_gizmos(dev_viz)
        _draw_source_markers(dev_viz)
    except Exception as exc:
        import sys

        print(f"[DevVisualizer] Draw error: {exc!r}", file=sys.stderr)


def _draw_indicator(dev_viz: Any) -> None:
    window_height = 600
    if dev_viz.window:
        window_height = dev_viz.window.height
    dev_viz._indicator_text.y = window_height - 30
    dev_viz._indicator_text.draw()


def _draw_selection(dev_viz: Any) -> bool:
    try:
        dev_viz.selection_manager.draw()
    except Exception as exc:
        error_str = str(exc)
        is_context_switch_error = "GLException" in type(exc).__name__ and (
            "Invalid operation" in error_str or "current state" in error_str
        )
        if not is_context_switch_error:
            import sys

            print(f"[DevVisualizer] Selection draw error (skipping): {exc!r}", file=sys.stderr)
        return False
    return True


def _draw_gizmos(dev_viz: Any) -> None:
    selected = dev_viz.selection_manager.get_selected()
    for sprite in selected:
        try:
            gizmo = dev_viz._get_gizmo(sprite)
            if gizmo:
                gizmo.draw()
        except Exception:
            pass


def _draw_source_markers(dev_viz: Any) -> None:
    try:
        for sprite in dev_viz.scene_sprites:
            if not isinstance(sprite, SpriteWithSourceMarkers):
                continue
            markers = sprite._source_markers
            if not markers:
                continue
            for marker in markers:
                _draw_marker(sprite, marker)
    except Exception:
        pass


def _draw_marker(sprite: Any, marker: dict) -> None:
    sx = sprite.center_x
    sy = sprite.center_y + (getattr(sprite, "height", 16) / 2) + 8
    lineno = marker.get("lineno")
    status = marker.get("status", "yellow")
    text = f"L{lineno}"

    if status == "green":
        bg = arcade.color.GREEN
        fg = arcade.color.BLACK
    elif status == "red":
        bg = arcade.color.RED
        fg = arcade.color.WHITE
    else:
        bg = arcade.color.YELLOW
        fg = arcade.color.BLACK

    arcade.draw_rectangle_filled(sx, sy, 36, 18, bg)
    text_obj = arcade.Text(text, sx - 16, sy - 6, fg, 12)
    text_obj.draw()
