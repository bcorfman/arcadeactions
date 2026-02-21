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
