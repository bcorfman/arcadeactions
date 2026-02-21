"""Window/view event handler wrapping for DevVisualizer."""

from __future__ import annotations

import types
from collections.abc import Callable
from typing import Any, Protocol

import arcade
from arcade.types import LBWH

from arcadeactions.dev import overrides_input
from arcadeactions.dev import window_hooks as _window_hooks


class EventHandlerHost(Protocol):
    """Protocol for the DevVisualizer event handler host."""

    visible: bool
    window: arcade.Window | None
    scene_sprites: arcade.SpriteList
    _position_tracker: Any

    _original_on_draw: Callable[..., Any] | None
    _original_on_key_press: Callable[..., Any] | None
    _original_on_mouse_press: Callable[..., Any] | None
    _original_on_mouse_drag: Callable[..., Any] | None
    _original_on_mouse_release: Callable[..., Any] | None
    _original_on_text: Callable[..., Any] | None
    _original_on_text_motion: Callable[..., Any] | None
    _original_on_close: Callable[..., Any] | None
    _original_show_view: Callable[..., Any] | None
    _original_set_location: Callable[..., Any] | None
    def toggle(self) -> None: ...

    def toggle_palette(self) -> None: ...
    def toggle_command_palette(self) -> None: ...
    def toggle_property_inspector(self) -> None: ...

    def handle_key_press(self, key: int, modifiers: int) -> bool: ...

    def handle_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool: ...

    def handle_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> bool: ...

    def handle_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> bool: ...

    def draw(self) -> None: ...

    def hide(self) -> None: ...

    def _wrap_view_on_draw(self, view: arcade.View) -> None: ...

    overrides_panel: overrides_input.OverridesPanelInput | None
    devshell_coordinator: Any | None


def _route_devshell_key_input(host: EventHandlerHost, key: int, modifiers: int) -> bool:
    coordinator = host.devshell_coordinator
    if coordinator is None:
        return False
    try:
        return bool(coordinator.route_key_press(key, modifiers))
    except Exception:
        return False


def _route_devshell_text_input(host: EventHandlerHost, text: str) -> bool:
    coordinator = host.devshell_coordinator
    if coordinator is None:
        return False
    try:
        return bool(coordinator.route_text(text))
    except Exception:
        return False


def _route_devshell_text_motion_input(host: EventHandlerHost, motion: int) -> bool:
    coordinator = host.devshell_coordinator
    if coordinator is None:
        return False
    try:
        return bool(coordinator.route_text_motion(motion))
    except Exception:
        return False


def _prepare_main_window_render_state(window: arcade.Window) -> None:
    """Normalize shared GL state that can be corrupted by other windows.

    This keeps draw state deterministic even if external tooling creates
    additional OpenGL windows that share context with the main Arcade window.
    """
    window.ctx.screen.use()
    # Secondary windows can enable scissoring; ensure the main window isn't clipped.
    window.ctx.scissor = None

    # Normalize viewport + projection. With multiple windows (palette + main),
    # the *shared* GL context can end up with a camera/projector configured for
    # the palette's small viewport, which makes the main scene appear zoomed.
    #
    # Restore the window viewport, then ensure the active camera's viewport
    # matches the window size before calling .use() (which applies matrices).
    window.viewport = (0, 0, window.width, window.height)

    active_camera = window.current_camera
    cam_viewport = active_camera.viewport
    if int(cam_viewport.width) != int(window.width) or int(cam_viewport.height) != int(window.height):
        # Defensive: DefaultProjector can "learn" the wrong viewport when it sees ctx.viewport.
        # Other projectors can also get stuck with the palette viewport. Overwrite to window size.
        active_camera.viewport = LBWH(0, 0, window.width, window.height)

    # Arcade's DefaultProjector has an early-return optimization that assumes the
    # underlying GPU state already matches ctx.viewport/current_camera. With multiple
    # windows sharing an OpenGL context, that assumption can be false (the palette draw
    # can change GPU state without updating this window's ctx bookkeeping). Force a
    # refresh by temporarily setting current_camera to a sentinel before calling use().
    window.ctx.current_camera = object()  # type: ignore[assignment]
    active_camera.use()


def wrap_window_handlers(
    host: EventHandlerHost,
    window: arcade.Window,
    *,
    has_window_context: Callable[[Any], bool],
) -> None:
    """Wrap a window's event handlers to integrate DevVisualizer."""
    host._original_on_draw = window.on_draw
    host._original_on_key_press = getattr(window, "on_key_press", None)
    host._original_on_mouse_press = getattr(window, "on_mouse_press", None)
    host._original_on_mouse_drag = getattr(window, "on_mouse_drag", None)
    host._original_on_mouse_release = getattr(window, "on_mouse_release", None)
    host._original_on_close = getattr(window, "on_close", None)

    def wrapped_on_draw():
        try:
            if not has_window_context(window):
                return

            # Ensure arcade.get_window() and other window_commands-based APIs refer to the
            # window currently being drawn. We intentionally do NOT restore to a prior
            # window after drawing: other windows (like the palette) should set themselves
            # current during their draw. This avoids timing-based "global window" churn.
            if _window_hooks.window_commands_module is not None:
                try:
                    current_window = _window_hooks.window_commands_module.get_window()
                except RuntimeError:
                    current_window = None

                if current_window is not window:
                    _window_hooks.window_commands_module.set_window(window)
                    try:
                        window.switch_to()
                    except Exception:
                        return

            if not has_window_context(window):
                return

            _prepare_main_window_render_state(window)

            if host._original_on_draw:
                host._original_on_draw()

            host.scene_sprites.draw()

            if host.visible:
                try:
                    if has_window_context(window):
                        if _window_hooks.window_commands_module is not None:
                            try:
                                active_window = _window_hooks.window_commands_module.get_window()
                                if active_window is not window:
                                    return
                            except RuntimeError:
                                pass
                        host.draw()
                except Exception as draw_error:
                    import sys

                    print(f"[DevVisualizer] Draw error (skipping): {draw_error!r}", file=sys.stderr)
        except Exception as e:
            import sys

            print(f"[DevVisualizer] Error in draw (context issue?): {e!r}", file=sys.stderr)
            return

    window.on_draw = wrapped_on_draw

    def wrapped_on_key_press(key: int, modifiers: int):
        if key == arcade.key.F12:
            host.toggle()
            return

        if key == arcade.key.F11:
            host.toggle_palette()
            return

        if key == arcade.key.F8:
            host.toggle_command_palette()
            return

        if key == arcade.key.I and modifiers & arcade.key.MOD_ALT:
            host.toggle_property_inspector()
            return

        if host.visible and _route_devshell_key_input(host, key, modifiers):
            return

        if host.visible and host.handle_key_press(key, modifiers):
            return

        if host._original_on_key_press:
            host._original_on_key_press(key, modifiers)

    window.on_key_press = wrapped_on_key_press

    def wrapped_on_mouse_press(x: int, y: int, button: int, modifiers: int):
        if host.visible and host.handle_mouse_press(x, y, button, modifiers):
            return
        if host._original_on_mouse_press:
            host._original_on_mouse_press(x, y, button, modifiers)

    def wrapped_on_mouse_drag(x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int):
        if host.visible and host.handle_mouse_drag(x, y, dx, dy, buttons, modifiers):
            return
        if host._original_on_mouse_drag:
            host._original_on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def wrapped_on_mouse_release(x: int, y: int, button: int, modifiers: int):
        if host.visible and host.handle_mouse_release(x, y, button, modifiers):
            return
        if host._original_on_mouse_release:
            host._original_on_mouse_release(x, y, button, modifiers)

    window.on_mouse_press = wrapped_on_mouse_press
    window.on_mouse_drag = wrapped_on_mouse_drag
    window.on_mouse_release = wrapped_on_mouse_release

    def wrapped_on_close():
        if host.visible:
            host.hide()
        if host._original_on_close:
            host._original_on_close()

    window.on_close = wrapped_on_close

    host._original_show_view = getattr(window, "show_view", None)
    host._original_set_location = getattr(window, "set_location", None)

    if host._original_set_location is not None:
        original_set_location = host._original_set_location

        def wrapped_set_location(this: arcade.Window, x: int, y: int, *args: Any, **kwargs: Any) -> None:
            original_set_location(x, y, *args, **kwargs)
            try:
                host._position_tracker.track_known_position(window, int(x), int(y))
            except Exception:
                return

        window.set_location = types.MethodType(wrapped_set_location, window)

    def wrapped_show_view(view: arcade.View) -> None:
        if host._original_show_view:
            host._original_show_view(view)
        host._wrap_view_on_draw(view)

    if host._original_show_view:
        window.show_view = wrapped_show_view  # type: ignore[assignment]

    current_view = getattr(window, "current_view", None)
    if current_view is not None:
        host._wrap_view_on_draw(current_view)


def wrap_view_handlers(host: EventHandlerHost, view: arcade.View) -> None:
    """Wrap a View's on_draw and event handlers to integrate DevVisualizer."""
    if not hasattr(view, "_dev_viz_original_on_draw"):
        view._dev_viz_original_on_draw = view.on_draw
        view._dev_viz_original_on_key_press = getattr(view, "on_key_press", None)
        view._dev_viz_original_on_mouse_press = getattr(view, "on_mouse_press", None)
        view._dev_viz_original_on_mouse_drag = getattr(view, "on_mouse_drag", None)
        view._dev_viz_original_on_mouse_release = getattr(view, "on_mouse_release", None)
        view._dev_viz_original_on_text = getattr(view, "on_text", None)
        view._dev_viz_original_on_text_motion = getattr(view, "on_text_motion", None)

    original_on_draw = view._dev_viz_original_on_draw

    def wrapped_view_on_draw():
        if original_on_draw:
            original_on_draw()
        host.scene_sprites.draw()
        if host.visible:
            host.draw()

    view.on_draw = wrapped_view_on_draw  # type: ignore[assignment]

    original_on_key_press = view._dev_viz_original_on_key_press

    def wrapped_view_on_key_press(key: int, modifiers: int):
        if key == arcade.key.F12:
            host.toggle()
            return

        if key == arcade.key.F11:
            host.toggle_palette()
            return

        if key == arcade.key.F8:
            host.toggle_command_palette()
            return

        if key == arcade.key.I and modifiers & arcade.key.MOD_ALT:
            host.toggle_property_inspector()
            return

        if host.visible and _route_devshell_key_input(host, key, modifiers):
            return

        if host.visible and host.handle_key_press(key, modifiers):
            return

        if original_on_key_press:
            original_on_key_press(key, modifiers)

    view.on_key_press = wrapped_view_on_key_press  # type: ignore[assignment]

    original_on_mouse_press = view._dev_viz_original_on_mouse_press
    original_on_mouse_drag = view._dev_viz_original_on_mouse_drag
    original_on_mouse_release = view._dev_viz_original_on_mouse_release

    original_on_text = view._dev_viz_original_on_text
    original_on_text_motion = view._dev_viz_original_on_text_motion

    def wrapped_view_on_text(text: str):
        if host.visible and _route_devshell_text_input(host, text):
            return
        if overrides_input.handle_overrides_panel_text(host.overrides_panel, text):
            return
        if original_on_text:
            original_on_text(text)

    view.on_text = wrapped_view_on_text  # type: ignore[assignment]

    def wrapped_view_on_text_motion(motion: int):
        if host.visible and _route_devshell_text_motion_input(host, motion):
            return
        if original_on_text_motion:
            original_on_text_motion(motion)

    view.on_text_motion = wrapped_view_on_text_motion  # type: ignore[assignment]

    def wrapped_view_on_mouse_press(x: int, y: int, button: int, modifiers: int):
        if host.visible and host.handle_mouse_press(x, y, button, modifiers):
            return
        if original_on_mouse_press:
            original_on_mouse_press(x, y, button, modifiers)

    def wrapped_view_on_mouse_drag(x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int):
        if host.visible and host.handle_mouse_drag(x, y, dx, dy, buttons, modifiers):
            return
        if original_on_mouse_drag:
            original_on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def wrapped_view_on_mouse_release(x: int, y: int, button: int, modifiers: int):
        if host.visible and host.handle_mouse_release(x, y, button, modifiers):
            return
        if original_on_mouse_release:
            original_on_mouse_release(x, y, button, modifiers)

    view.on_mouse_press = wrapped_view_on_mouse_press  # type: ignore[assignment]
    view.on_mouse_drag = wrapped_view_on_mouse_drag  # type: ignore[assignment]
    view.on_mouse_release = wrapped_view_on_mouse_release  # type: ignore[assignment]
