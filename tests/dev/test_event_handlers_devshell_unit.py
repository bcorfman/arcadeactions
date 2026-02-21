"""Unit tests for DevShell coordinator routing in event handler wrappers."""

from __future__ import annotations

import arcade

from arcadeactions.dev import event_handlers


class _CoordinatorStub:
    def __init__(self) -> None:
        self.keys: list[tuple[int, int]] = []
        self.text: list[str] = []
        self.motion: list[int] = []
        self.key_result = False
        self.text_result = False
        self.motion_result = False

    def route_key_press(self, key: int, modifiers: int) -> bool:
        self.keys.append((key, modifiers))
        return self.key_result

    def route_text(self, text: str) -> bool:
        self.text.append(text)
        return self.text_result

    def route_text_motion(self, motion: int) -> bool:
        self.motion.append(motion)
        return self.motion_result


class _Host:
    def __init__(self) -> None:
        self.visible = True
        self.devshell_panels_enabled = True
        self.window = None
        self.palette_window = None
        self.command_palette_window = None
        self.property_inspector_window = None
        self.scene_sprites = type("_Sprites", (), {"draw": lambda self: None})()
        self._is_detaching = False
        self._position_tracker = type("_Tracker", (), {"track_known_position": lambda *args, **kwargs: None})()
        self._original_on_draw = None
        self._original_on_key_press = None
        self._original_on_mouse_press = None
        self._original_on_mouse_drag = None
        self._original_on_mouse_release = None
        self._original_on_text = None
        self._original_on_text_motion = None
        self._original_on_close = None
        self._original_show_view = None
        self._original_set_location = None
        self.overrides_panel = None
        self.devshell_coordinator = _CoordinatorStub()

    def toggle(self) -> None:
        return None

    def toggle_palette(self) -> None:
        return None

    def toggle_command_palette(self) -> None:
        return None

    def toggle_property_inspector(self) -> None:
        return None

    def handle_key_press(self, _key: int, _modifiers: int) -> bool:
        return False

    def handle_mouse_press(self, _x: int, _y: int, _button: int, _modifiers: int) -> bool:
        return False

    def handle_mouse_drag(self, _x: int, _y: int, _dx: int, _dy: int, _buttons: int, _modifiers: int) -> bool:
        return False

    def handle_mouse_release(self, _x: int, _y: int, _button: int, _modifiers: int) -> bool:
        return False

    def draw(self) -> None:
        return None

    def hide(self) -> None:
        return None

    def _wrap_view_on_draw(self, view: arcade.View) -> None:
        event_handlers.wrap_view_handlers(self, view)


def test_view_key_press_prefers_devshell_coordinator_when_handled():
    """View key presses should short-circuit when coordinator handles the event."""
    host = _Host()
    host.devshell_coordinator.key_result = True
    view = arcade.View()
    called = {"original": False}
    view.on_draw = lambda: None
    view.on_key_press = lambda *_args: called.__setitem__("original", True)
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda _text: None
    view.on_text_motion = lambda _motion: None

    event_handlers.wrap_view_handlers(host, view)
    view.on_key_press(arcade.key.K, 0)

    assert host.devshell_coordinator.keys == [(arcade.key.K, 0)]
    assert called["original"] is False


def test_view_key_press_falls_back_when_coordinator_declines():
    """If coordinator declines key event, wrapped handler should continue normal flow."""
    host = _Host()
    host.devshell_coordinator.key_result = False
    view = arcade.View()
    original_calls: list[tuple[int, int]] = []
    view.on_draw = lambda: None
    view.on_key_press = lambda key, modifiers: original_calls.append((key, modifiers))
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda _text: None
    view.on_text_motion = lambda _motion: None

    event_handlers.wrap_view_handlers(host, view)
    view.on_key_press(arcade.key.K, 0)

    assert host.devshell_coordinator.keys == [(arcade.key.K, 0)]
    assert original_calls == [(arcade.key.K, 0)]


def test_view_text_prefers_devshell_coordinator_when_handled():
    """View text events should short-circuit when coordinator handles them."""
    host = _Host()
    host.devshell_coordinator.text_result = True
    view = arcade.View()
    called = {"original": False}
    view.on_draw = lambda: None
    view.on_key_press = lambda *_args: None
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda _text: called.__setitem__("original", True)
    view.on_text_motion = lambda _motion: None

    event_handlers.wrap_view_handlers(host, view)
    view.on_text("x")

    assert host.devshell_coordinator.text == ["x"]
    assert called["original"] is False


def test_view_text_motion_prefers_devshell_coordinator_when_handled():
    """View text-motion events should short-circuit when coordinator handles them."""
    host = _Host()
    host.devshell_coordinator.motion_result = True
    view = arcade.View()
    called = {"original": False}
    view.on_draw = lambda: None
    view.on_key_press = lambda *_args: None
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda _text: None
    view.on_text_motion = lambda _motion: called.__setitem__("original", True)

    event_handlers.wrap_view_handlers(host, view)
    view.on_text_motion(arcade.key.MOTION_BACKSPACE)

    assert host.devshell_coordinator.motion == [arcade.key.MOTION_BACKSPACE]
    assert called["original"] is False


def test_view_key_press_does_not_fall_back_to_legacy_property_inspector_in_devshell_mode():
    """DevShell mode should bypass legacy inspector key forwarding when coordinator declines."""
    host = _Host()
    host.devshell_coordinator.key_result = False
    inspector_window = type("_Inspector", (), {})()
    inspector_window.visible = True
    inspector_window.is_closed = False
    inspector_window.accepts_forwarded_key = lambda *_args: True
    inspector_window.on_key_press = lambda *_args: (_ for _ in ()).throw(AssertionError("legacy key path used"))
    inspector_window.mark_forwarded_input_activity = lambda: None
    inspector_window.refresh_editor_style = lambda: None
    host.property_inspector_window = inspector_window
    view = arcade.View()
    calls: list[tuple[int, int]] = []
    view.on_draw = lambda: None
    view.on_key_press = lambda key, modifiers: calls.append((key, modifiers))
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda _text: None
    view.on_text_motion = lambda _motion: None

    event_handlers.wrap_view_handlers(host, view)
    view.on_key_press(arcade.key.A, 0)

    assert host.devshell_coordinator.keys == [(arcade.key.A, 0)]
    assert calls == [(arcade.key.A, 0)]


def test_view_text_does_not_fall_back_to_legacy_property_inspector_in_devshell_mode():
    """DevShell mode should bypass legacy inspector text forwarding when coordinator declines."""
    host = _Host()
    host.devshell_coordinator.text_result = False
    inspector_window = type("_Inspector", (), {})()
    inspector_window.visible = True
    inspector_window.is_closed = False
    inspector_window.accepts_forwarded_text = lambda *_args: True
    inspector_window.on_text = lambda *_args: (_ for _ in ()).throw(AssertionError("legacy text path used"))
    inspector_window.mark_forwarded_input_activity = lambda: None
    inspector_window.refresh_editor_style = lambda: None
    host.property_inspector_window = inspector_window
    view = arcade.View()
    calls: list[str] = []
    view.on_draw = lambda: None
    view.on_key_press = lambda *_args: None
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda text: calls.append(text)
    view.on_text_motion = lambda _motion: None

    event_handlers.wrap_view_handlers(host, view)
    view.on_text("1")

    assert host.devshell_coordinator.text == ["1"]
    assert calls == ["1"]


def test_view_escape_does_not_close_window_via_legacy_path_in_devshell_mode():
    """DevShell mode should bypass legacy ESC close-window behavior."""
    host = _Host()
    host.devshell_coordinator.key_result = False
    host.window = type("_Window", (), {})()
    host.window.closed = False
    close_calls = {"count": 0}

    def _close():
        close_calls["count"] += 1

    host.window.close = _close
    view = arcade.View()
    called = {"original": False}
    view.on_draw = lambda: None
    view.on_key_press = lambda *_args: called.__setitem__("original", True)
    view.on_mouse_press = lambda *_args: None
    view.on_mouse_drag = lambda *_args: None
    view.on_mouse_release = lambda *_args: None
    view.on_text = lambda _text: None
    view.on_text_motion = lambda _motion: None

    event_handlers.wrap_view_handlers(host, view)
    view.on_key_press(arcade.key.ESCAPE, 0)

    assert close_calls["count"] == 0
    assert called["original"] is True


def test_route_devshell_text_motion_returns_false_without_coordinator():
    """Text-motion routing should fail closed when coordinator is missing."""
    host = _Host()
    host.devshell_coordinator = None

    assert event_handlers._route_devshell_text_motion_input(host, arcade.key.MOTION_BACKSPACE) is False


def test_wrap_view_handlers_captures_text_handlers_and_routes_text_motion():
    """First-time view wrapping should capture text handlers and route text motion."""

    class _ViewStub:
        def __init__(self) -> None:
            self.motion_calls: list[int] = []

        def on_draw(self) -> None:
            return None

        def on_key_press(self, _key: int, _modifiers: int) -> None:
            return None

        def on_mouse_press(self, *_args) -> None:
            return None

        def on_mouse_drag(self, *_args) -> None:
            return None

        def on_mouse_release(self, *_args) -> None:
            return None

        def on_text(self, _text: str) -> None:
            return None

        def on_text_motion(self, motion: int) -> None:
            self.motion_calls.append(motion)

    host = _Host()
    host.devshell_coordinator.motion_result = False
    view = _ViewStub()

    event_handlers.wrap_view_handlers(host, view)

    assert view._dev_viz_original_on_text is not None
    assert view._dev_viz_original_on_text_motion is not None
    view.on_text_motion(arcade.key.MOTION_BACKSPACE)
    assert host.devshell_coordinator.motion == [arcade.key.MOTION_BACKSPACE]
    assert view.motion_calls == [arcade.key.MOTION_BACKSPACE]


def test_wrap_view_handlers_short_circuits_text_motion_when_coordinator_handles():
    """Handled text-motion should not fall through to original text-motion handler."""

    class _ViewStub:
        def __init__(self) -> None:
            self.motion_calls: list[int] = []

        def on_draw(self) -> None:
            return None

        def on_key_press(self, _key: int, _modifiers: int) -> None:
            return None

        def on_mouse_press(self, *_args) -> None:
            return None

        def on_mouse_drag(self, *_args) -> None:
            return None

        def on_mouse_release(self, *_args) -> None:
            return None

        def on_text(self, _text: str) -> None:
            return None

        def on_text_motion(self, motion: int) -> None:
            self.motion_calls.append(motion)

    host = _Host()
    host.devshell_coordinator.motion_result = True
    view = _ViewStub()

    event_handlers.wrap_view_handlers(host, view)
    view.on_text_motion(arcade.key.MOTION_BACKSPACE)

    assert host.devshell_coordinator.motion == [arcade.key.MOTION_BACKSPACE]
    assert view.motion_calls == []


class _CameraViewport:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height


class _Camera:
    def __init__(self, width: int, height: int) -> None:
        self.viewport = _CameraViewport(width, height)
        self.used = 0

    def use(self) -> None:
        self.used += 1


class _Screen:
    def __init__(self) -> None:
        self.used = 0

    def use(self) -> None:
        self.used += 1


class _Ctx:
    def __init__(self) -> None:
        self.screen = _Screen()
        self.scissor = object()
        self.current_camera = None


class _WindowStub:
    def __init__(self) -> None:
        self.width = 640
        self.height = 480
        self.viewport = (5, 5, 10, 10)
        self.current_camera = _Camera(10, 10)
        self.ctx = _Ctx()
        self._context = object()
        self.on_draw_calls = 0
        self.on_key_calls: list[tuple[int, int]] = []
        self.on_mouse_press_calls: list[tuple[int, int, int, int]] = []
        self.on_mouse_drag_calls: list[tuple[int, int, int, int, int, int]] = []
        self.on_mouse_release_calls: list[tuple[int, int, int, int]] = []
        self.close_calls = 0
        self.show_view_calls: list[object] = []
        self.switched = 0
        self.current_view = None
        self.set_location_calls: list[tuple[int, int]] = []
        self.on_draw = self._on_draw
        self.on_key_press = self._on_key_press
        self.on_mouse_press = self._on_mouse_press
        self.on_mouse_drag = self._on_mouse_drag
        self.on_mouse_release = self._on_mouse_release
        self.on_close = self._on_close
        self.show_view = self._show_view
        self.set_location = self._set_location

    def _on_draw(self) -> None:
        self.on_draw_calls += 1

    def _on_key_press(self, key: int, modifiers: int) -> None:
        self.on_key_calls.append((key, modifiers))

    def _on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        self.on_mouse_press_calls.append((x, y, button, modifiers))

    def _on_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> None:
        self.on_mouse_drag_calls.append((x, y, dx, dy, buttons, modifiers))

    def _on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        self.on_mouse_release_calls.append((x, y, button, modifiers))

    def _on_close(self) -> None:
        self.close_calls += 1

    def _show_view(self, view: object) -> None:
        self.show_view_calls.append(view)

    def _set_location(self, x: int, y: int) -> None:
        self.set_location_calls.append((x, y))

    def switch_to(self) -> None:
        self.switched += 1


def test_prepare_main_window_render_state_updates_viewport_and_camera():
    """Render-state helper should normalize viewport/scissor/camera usage."""
    window = _WindowStub()

    event_handlers._prepare_main_window_render_state(window)

    assert window.ctx.screen.used == 1
    assert window.ctx.scissor is None
    assert window.viewport == (0, 0, 640, 480)
    assert window.current_camera.viewport.width == 640
    assert window.current_camera.viewport.height == 480
    assert window.current_camera.used == 1


def test_wrap_window_handlers_draw_and_input_flow(monkeypatch):
    """Window wrapper should route draw/input and preserve original fallbacks."""
    host = _Host()
    window = _WindowStub()

    class _WindowCommands:
        def __init__(self) -> None:
            self.current = None

        def get_window(self):
            return self.current

        def set_window(self, win):
            self.current = win

    commands = _WindowCommands()
    monkeypatch.setattr(event_handlers._window_hooks, "window_commands_module", commands)

    event_handlers.wrap_window_handlers(host, window, has_window_context=lambda win: win._context is not None)

    # Draw path should call original on_draw and host draw when visible.
    window.on_draw()
    assert window.on_draw_calls == 1

    # Key toggles.
    toggles: list[str] = []
    host.toggle = lambda: toggles.append("toggle")
    host.toggle_palette = lambda: toggles.append("palette")
    host.toggle_command_palette = lambda: toggles.append("cmd")
    host.toggle_property_inspector = lambda: toggles.append("inspect")
    window.on_key_press(arcade.key.F12, 0)
    window.on_key_press(arcade.key.F11, 0)
    window.on_key_press(arcade.key.F8, 0)
    window.on_key_press(arcade.key.I, arcade.key.MOD_ALT)
    assert toggles == ["toggle", "palette", "cmd", "inspect"]

    # Mouse fallback path.
    window.on_mouse_press(1, 2, 3, 4)
    window.on_mouse_drag(1, 2, 3, 4, 5, 6)
    window.on_mouse_release(7, 8, 9, 10)
    assert window.on_mouse_press_calls == [(1, 2, 3, 4)]
    assert window.on_mouse_drag_calls == [(1, 2, 3, 4, 5, 6)]
    assert window.on_mouse_release_calls == [(7, 8, 9, 10)]

    # set_location wrapper tracks known location.
    tracked: list[tuple[int, int]] = []
    host._position_tracker.track_known_position = lambda _w, x, y: tracked.append((x, y))
    window.set_location(20, 30)
    assert tracked == [(20, 30)]


def test_wrap_window_handlers_handles_switch_to_failure(monkeypatch):
    """Draw wrapper should return early when switch_to raises."""
    host = _Host()
    window = _WindowStub()

    class _WindowCommands:
        def __init__(self) -> None:
            self.current = None

        def get_window(self):
            return None

        def set_window(self, win):
            self.current = win

    monkeypatch.setattr(event_handlers._window_hooks, "window_commands_module", _WindowCommands())

    def fail_switch() -> None:
        raise RuntimeError("switch failure")

    window.switch_to = fail_switch
    event_handlers.wrap_window_handlers(host, window, has_window_context=lambda _win: True)
    window.on_draw()
    assert window.on_draw_calls == 0
