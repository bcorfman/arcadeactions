"""Drawing helpers for DevVisualizer overlays."""

from __future__ import annotations

import time
from typing import Any

import arcade

from arcadeactions.dev.devshell_state import DevShellMode
from arcadeactions.dev.visualizer_protocols import SpriteWithSourceMarkers
from arcadeactions.dev.window_utils import has_window_context

_TEXT_CACHE_LIMIT = 512
_TEXT_CACHE: dict[tuple[str, int, bool, tuple[int, ...]], arcade.Text] = {}


def draw_visualizer(dev_viz: Any) -> None:
    if not dev_viz.visible:
        return

    if dev_viz.window is None:
        return

    if not has_window_context(dev_viz.window):
        return

    _run_draw_step(_draw_devshell_layout, dev_viz)
    _run_draw_step(_draw_indicator, dev_viz)
    _run_draw_step(_draw_devshell_focus_overlay, dev_viz)
    _run_draw_step(_draw_devshell_panels, dev_viz)
    if not _run_selection_draw_step(dev_viz):
        return
    _run_draw_step(_draw_gizmos, dev_viz)
    _run_draw_step(_draw_source_markers, dev_viz)


def _run_draw_step(step: Any, dev_viz: Any) -> None:
    """Run one draw step while isolating backend-specific OpenGL failures."""
    try:
        step(dev_viz)
    except RuntimeError as exc:
        if "No OpenGL context available" in str(exc):
            return
        _log_draw_error(exc)
        return
    except Exception as exc:
        _log_draw_error(exc)
        return


def _run_selection_draw_step(dev_viz: Any) -> bool:
    """Run selection draw step while preserving existing early-return semantics."""
    try:
        return bool(_draw_selection(dev_viz))
    except RuntimeError as exc:
        if "No OpenGL context available" in str(exc):
            return True
        _log_draw_error(exc)
        return True
    except Exception as exc:
        _log_draw_error(exc)
        return True


def _log_draw_error(exc: Exception) -> None:
    import sys

    print(f"[DevVisualizer] Draw error: {exc!r}", file=sys.stderr)


def _draw_text_obj(
    text: str,
    x: float,
    y: float,
    color: tuple[int, ...] | arcade.types.Color,
    font_size: int,
    *,
    bold: bool = False,
) -> None:
    """Draw text via cached arcade.Text objects (avoids draw_text performance warnings)."""
    color_tuple = tuple(int(value) for value in color)
    key = (str(text), int(font_size), bool(bold), color_tuple)
    text_obj = _TEXT_CACHE.get(key)
    if text_obj is None:
        if len(_TEXT_CACHE) >= _TEXT_CACHE_LIMIT:
            _TEXT_CACHE.clear()
        text_obj = arcade.Text(
            str(text),
            float(x),
            float(y),
            color_tuple,
            int(font_size),
            bold=bool(bold),
        )
        _TEXT_CACHE[key] = text_obj
    else:
        text_obj.x = float(x)
        text_obj.y = float(y)
    text_obj.draw()


def _draw_indicator(dev_viz: Any) -> None:
    window_height = 600
    if dev_viz.window:
        window_height = dev_viz.window.height
    dev_viz._indicator_text.y = window_height - 30
    dev_viz._indicator_text.draw()


def _draw_devshell_layout(dev_viz: Any) -> None:
    regions = dev_viz.devshell_regions()
    if regions is None:
        return
    stage_border = (70, 90, 102, 220)
    if regions.left.width > 0 and regions.left.height > 0:
        _draw_overlay_background(
            left=regions.left.x, bottom=regions.left.y, width=regions.left.width, height=regions.left.height
        )
    if regions.right.width > 0 and regions.right.height > 0:
        _draw_overlay_background(
            left=regions.right.x, bottom=regions.right.y, width=regions.right.width, height=regions.right.height
        )
    if regions.top.width > 0 and regions.top.height > 0:
        _draw_overlay_background(left=regions.top.x, bottom=regions.top.y, width=regions.top.width, height=regions.top.height)
    if regions.bottom.width > 0 and regions.bottom.height > 0:
        _draw_overlay_background(
            left=regions.bottom.x, bottom=regions.bottom.y, width=regions.bottom.width, height=regions.bottom.height
        )
    try:
        arcade.draw_lbwh_rectangle_outline(
            regions.stage.x,
            regions.stage.y,
            regions.stage.width,
            regions.stage.height,
            stage_border,
            2,
        )
    except AttributeError:
        # Keep fallback simple for versions lacking lbwh outline helper.
        arcade.draw_rect_outline(
            arcade.rect.XYWH(
                regions.stage.x + (regions.stage.width / 2),
                regions.stage.y + (regions.stage.height / 2),
                regions.stage.width,
                regions.stage.height,
            ),
            stage_border,
            2,
        )


def _draw_devshell_focus_overlay(dev_viz: Any) -> None:
    if not dev_viz._devshell_panels_enabled:
        return
    coordinator = dev_viz.devshell_coordinator
    if coordinator is None:
        return
    if coordinator.state.mode != DevShellMode.EDIT_LIVE:
        return
    if dev_viz.window is None:
        return

    panel_ids: list[str] = []
    if dev_viz._devshell_prototype_palette_panel is not None and dev_viz._devshell_prototype_palette_panel.visible:
        panel_ids.append("prototype_palette")
    if dev_viz._devshell_command_palette_panel is not None and dev_viz._devshell_command_palette_panel.visible:
        panel_ids.append("command_palette")
    if dev_viz._devshell_property_inspector_panel is not None and dev_viz._devshell_property_inspector_panel.visible:
        panel_ids.append("property_inspector")

    focus = coordinator.state.focus_visual_state(panel_ids=panel_ids)
    now = time.monotonic()
    if int(focus.pulse_token) != int(dev_viz._devshell_focus_last_pulse_token):
        dev_viz._devshell_focus_last_pulse_token = int(focus.pulse_token)
        dev_viz._devshell_focus_pulse_until = float(now + 0.35)
    pulse_active = now <= float(dev_viz._devshell_focus_pulse_until)

    overlay_width = 320
    row_height = 20
    overlay_height = 36 + (len(panel_ids) * row_height)
    left = int(dev_viz.window.width) - overlay_width - 12
    bottom = int(dev_viz.window.height) - overlay_height - 8

    _draw_overlay_background(left=left, bottom=bottom, width=overlay_width, height=overlay_height)
    _draw_text_obj(focus.focus_label, left + 8, bottom + overlay_height - 24, arcade.color.WHITE, 12, bold=True)

    cursor_y = bottom + overlay_height - 46
    for panel_id in panel_ids:
        panel_state = focus.panel_states[panel_id]
        label = panel_id
        if panel_state.is_active:
            label = f"{label} [ACTIVE]"
        if panel_state.is_active and pulse_active:
            label = f"{label} [PULSE]"
        if panel_state.show_caret:
            label = f"{label} [TEXT]"
        text_color = arcade.color.WHITE if panel_state.is_active else arcade.color.LIGHT_GRAY
        _draw_text_obj(label, left + 12, cursor_y, text_color, 11)
        cursor_y -= row_height


def _draw_overlay_background(*, left: int, bottom: int, width: int, height: int) -> None:
    color = (30, 36, 40, 215)
    try:
        arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, color)
    except AttributeError:
        arcade.draw_rect_filled(arcade.rect.XYWH(left + (width / 2), bottom + (height / 2), width, height), color)


def _draw_devshell_panels(dev_viz: Any) -> None:
    if not dev_viz._devshell_panels_enabled:
        return
    coordinator = dev_viz.devshell_coordinator
    if coordinator is None:
        return
    if coordinator.state.mode != DevShellMode.EDIT_LIVE:
        return
    if dev_viz.window is None:
        return
    active_panel = coordinator.focus_manager.active_panel
    if dev_viz._devshell_prototype_palette_panel is not None and dev_viz._devshell_prototype_palette_panel.visible:
        _draw_prototype_palette_panel_overlay(
            dev_viz=dev_viz,
            panel=dev_viz._devshell_prototype_palette_panel,
            is_active=active_panel == "prototype_palette",
        )
    if dev_viz._devshell_command_palette_panel is not None and dev_viz._devshell_command_palette_panel.visible:
        _draw_command_palette_panel_overlay(
            panel=dev_viz._devshell_command_palette_panel,
            window_width=int(dev_viz.window.width),
            window_height=int(dev_viz.window.height),
            is_active=active_panel == "command_palette",
        )
    if dev_viz._devshell_property_inspector_panel is not None and dev_viz._devshell_property_inspector_panel.visible:
        _draw_property_inspector_panel_overlay(
            panel=dev_viz._devshell_property_inspector_panel,
            window_width=int(dev_viz.window.width),
            window_height=int(dev_viz.window.height),
            is_active=active_panel == "property_inspector",
        )


def _draw_prototype_palette_panel_overlay(*, dev_viz: Any, panel: Any, is_active: bool) -> None:
    geometry = dev_viz._devshell_prototype_panel_geometry()
    if geometry is None:
        return
    left, bottom, width, height = geometry
    _draw_overlay_background(left=left, bottom=bottom, width=width, height=height)
    title = "Prototype Palette"
    if is_active:
        title = f"{title} [ACTIVE]"
    _draw_text_obj(title, left + 8, bottom + height - 24, arcade.color.WHITE, 12, bold=True)
    prototypes = panel.prototype_ids()
    row_y = bottom + height - 46
    for index, prototype_id in enumerate(prototypes[:20]):
        prefix = ">" if index == int(panel.selected_index) else " "
        color = arcade.color.WHITE if index == int(panel.selected_index) else arcade.color.LIGHT_GRAY
        _draw_text_obj(f"{prefix} {prototype_id}", left + 10, row_y, color, 11)
        row_y -= 20


def _draw_command_palette_panel_overlay(*, panel: Any, window_width: int, window_height: int, is_active: bool) -> None:
    width = 320
    height = 220
    left = 12
    bottom = window_height - height - 56
    _draw_overlay_background(left=left, bottom=bottom, width=width, height=height)
    title = "Command Palette"
    if is_active:
        title = f"{title} [ACTIVE]"
    _draw_text_obj(title, left + 8, bottom + height - 24, arcade.color.WHITE, 12, bold=True)

    try:
        commands = panel._enabled_commands()
    except Exception:
        commands = []
    selected_index = int(panel.selected_index)
    row_y = bottom + height - 46
    for index, command in enumerate(commands[:8]):
        prefix = ">" if index == selected_index else " "
        color = arcade.color.WHITE if index == selected_index else arcade.color.LIGHT_GRAY
        _draw_text_obj(f"{prefix} {command.name}", left + 10, row_y, color, 11)
        row_y -= 20


def _draw_property_inspector_panel_overlay(*, panel: Any, window_width: int, window_height: int, is_active: bool) -> None:
    width = 340
    height = 220
    left = window_width - width - 12
    bottom = window_height - height - 56
    _draw_overlay_background(left=left, bottom=bottom, width=width, height=height)
    title = "Inspector"
    if is_active:
        title = f"{title} [ACTIVE]"
    _draw_text_obj(title, left + 8, bottom + height - 24, arcade.color.WHITE, 12, bold=True)

    if panel.mode == "arrange":
        try:
            settings = panel._arrange_settings()
        except Exception:
            settings = []
        if not settings:
            _draw_text_obj("No arrange settings", left + 10, bottom + height - 48, arcade.color.LIGHT_GRAY, 11)
            return
        index = min(int(panel._arrange_setting_index), len(settings) - 1)
        setting_name, setting_value = settings[index]
        _draw_text_obj(f"Arrange: {setting_name}", left + 10, bottom + height - 48, arcade.color.LIGHT_GRAY, 11)
        value_text = panel.text_buffer.text if panel.editing else setting_value
        _draw_text_obj(f"Value: {value_text}", left + 10, bottom + height - 68, arcade.color.WHITE, 11)
    else:
        try:
            current = panel._inspector.current_property()
        except Exception:
            current = None
        if current is None:
            _draw_text_obj("No selection", left + 10, bottom + height - 48, arcade.color.LIGHT_GRAY, 11)
            return

        _draw_text_obj(f"Property: {current.name}", left + 10, bottom + height - 48, arcade.color.LIGHT_GRAY, 11)
        if panel.editing:
            value_text = panel.text_buffer.text
        else:
            try:
                value_text = panel._inspector.current_property_value_text()
            except Exception:
                value_text = ""
        _draw_text_obj(f"Value: {value_text}", left + 10, bottom + height - 68, arcade.color.WHITE, 11)
    if panel.input_error:
        _draw_text_obj(f"Error: {panel.input_error}", left + 10, bottom + 16, arcade.color.RED, 10)


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
