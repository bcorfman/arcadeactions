"""Unit tests for EventInspectorWindow helper behaviors."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.visualizer.event_window import EventInspectorWindow


class StubTimeline:
    def __init__(self, _store: object) -> None:
        self.update_calls = 0

    def update(self) -> None:
        self.update_calls += 1


class StubTimelineRenderer:
    def __init__(self, timeline: StubTimeline, **_kwargs: object) -> None:
        self.timeline = timeline
        self.width = 0
        self.height = 0
        self.update_calls = 0
        self.draw_calls = 0
        self.font_sizes: list[float] = []

    def set_font_size(self, size: float) -> None:
        self.font_sizes.append(size)

    def update(self) -> None:
        self.update_calls += 1

    def draw(self) -> None:
        self.draw_calls += 1


class StubWindow:
    def __init__(self) -> None:
        self.dispatch_calls: list[tuple[str, int, int]] = []
        self.handler_calls: list[tuple[int, int]] = []

    def dispatch_event(self, handler: str, symbol: int, modifiers: int) -> None:
        self.dispatch_calls.append((handler, symbol, modifiers))

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        self.handler_calls.append((symbol, modifiers))


@pytest.fixture
def window(require_opengl) -> EventInspectorWindow:
    window = EventInspectorWindow(
        debug_store=object(),
        timeline_cls=StubTimeline,
        timeline_renderer_cls=StubTimelineRenderer,
    )
    window._should_draw = True
    return window


def test_on_draw_updates_renderer_geometry(monkeypatch, window: EventInspectorWindow) -> None:
    renderer = window._timeline_renderer
    assert isinstance(renderer, StubTimelineRenderer)

    monkeypatch.setattr(window, "_has_active_context", lambda: True)
    monkeypatch.setattr("arcadeactions.visualizer.event_window.window_commands.get_window", lambda: window)
    monkeypatch.setattr("arcadeactions.visualizer.event_window.window_commands.set_window", lambda _win: None)
    monkeypatch.setattr(window, "switch_to", lambda: None)
    monkeypatch.setattr(window, "clear", lambda: None)
    monkeypatch.setattr(window, "_draw_background", lambda: None)
    monkeypatch.setattr(window, "_draw_timeline", lambda: None)

    window.width = 500
    window.height = 400
    window.on_draw()

    assert renderer.update_calls == 1
    assert renderer.width == window.width - 2 * window.MARGIN
    assert renderer.height < window.height


def test_forward_to_main_window_dispatches(monkeypatch, window: EventInspectorWindow) -> None:
    stub_main = StubWindow()
    window._main_window = stub_main

    window._forward_to_main_window("on_key_press", arcade.key.F5, 0)

    assert stub_main.dispatch_calls == [("on_key_press", arcade.key.F5, 0)]
    assert stub_main.handler_calls == []


def test_forward_to_main_window_fallback(monkeypatch, window: EventInspectorWindow) -> None:
    stub_main = StubWindow()
    window._main_window = stub_main

    def fail_dispatch(_handler: str, _symbol: int, _modifiers: int) -> None:
        raise RuntimeError("no dispatch")

    stub_main.dispatch_event = fail_dispatch  # type: ignore[assignment]

    window._forward_to_main_window("on_key_press", arcade.key.F5, 0)

    assert stub_main.handler_calls == [(arcade.key.F5, 0)]


def test_request_main_window_focus_schedules(monkeypatch, window: EventInspectorWindow) -> None:
    calls: list[float] = []

    def record_schedule(func, delay: float) -> None:
        calls.append(delay)

    monkeypatch.setattr(arcade, "schedule_once", record_schedule)
    window._main_window = StubWindow()

    window.request_main_window_focus()

    assert calls == [0.0, 0.01, 0.05]


def test_on_key_press_forward_handler_handles(monkeypatch, window: EventInspectorWindow) -> None:
    handled: list[tuple[int, int]] = []

    def forward(symbol: int, modifiers: int) -> bool:
        handled.append((symbol, modifiers))
        return True

    window._forward_key_handler = forward
    window.close = lambda: None  # type: ignore[assignment]

    window.on_key_press(arcade.key.F4, 0)

    assert handled == [(arcade.key.F4, 0)]


def test_on_key_press_f4_closes(monkeypatch, window: EventInspectorWindow) -> None:
    closed = []

    def close() -> None:
        closed.append(True)

    window.close = close  # type: ignore[assignment]

    window.on_key_press(arcade.key.F4, 0)

    assert closed == [True]


def test_on_key_press_non_f4_forwards_to_main(window: EventInspectorWindow) -> None:
    stub_main = StubWindow()
    window._main_window = stub_main

    window.on_key_press(arcade.key.A, 0)

    assert stub_main.dispatch_calls == [("on_key_press", arcade.key.A, 0)]


def test_on_key_release_forwards(window: EventInspectorWindow) -> None:
    stub_main = StubWindow()
    window._main_window = stub_main

    window.on_key_release(arcade.key.A, 0)

    assert stub_main.dispatch_calls == [("on_key_release", arcade.key.A, 0)]


def test_schedule_focus_restore_no_main_window(window: EventInspectorWindow) -> None:
    window._main_window = None
    window._schedule_focus_restore(0.0)


def test_schedule_focus_restore_handles_activation_errors(monkeypatch, window: EventInspectorWindow) -> None:
    class _BadMain:
        def activate(self) -> None:
            raise RuntimeError("no focus")

    scheduled = []

    def schedule_once(fn, _delay: float) -> None:
        scheduled.append(fn)

    monkeypatch.setattr(arcade, "schedule_once", schedule_once)
    monkeypatch.setattr("arcadeactions.visualizer.event_window.window_commands.set_window", lambda _win: None)
    window._main_window = _BadMain()

    window._schedule_focus_restore(0.01)
    assert len(scheduled) == 1
    scheduled[0](0.0)


def test_set_visible_and_resize_paths(monkeypatch, window: EventInspectorWindow) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(arcade.Window, "set_visible", lambda self, visible: calls.append(bool(visible)))
    focus_calls: list[bool] = []
    monkeypatch.setattr(window, "request_main_window_focus", lambda: focus_calls.append(True))

    window.set_visible(True)
    window.set_visible(False)

    assert calls == [True, False]
    assert focus_calls == [True]

    resize_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(arcade.Window, "on_resize", lambda self, w, h: resize_calls.append((w, h)))
    monkeypatch.setattr(window, "_enforce_minimum_size", lambda _w, _h: True)
    window.on_resize(100, 100)
    assert resize_calls == []

    monkeypatch.setattr(window, "_enforce_minimum_size", lambda _w, _h: False)
    window.on_resize(700, 500)
    assert resize_calls == [(700, 500)]


def test_draw_background_and_skip_draw_helpers(monkeypatch, window: EventInspectorWindow) -> None:
    calls: list[tuple[float, ...]] = []
    monkeypatch.setattr(
        "arcadeactions.visualizer.event_window.arcade.draw_lbwh_rectangle_filled",
        lambda *args: calls.append(tuple(float(v) for v in args[:4])),
    )
    monkeypatch.setattr(window, "_has_active_context", lambda: True)
    window._draw_background()
    assert len(calls) == 1

    monkeypatch.setattr(window, "_has_active_context", lambda: False)
    window._draw_background()
    assert len(calls) == 1

    window._should_draw = False
    assert window._should_skip_draw() is True
    window._should_draw = True
    monkeypatch.setattr(window, "_has_active_context", lambda: False)
    assert window._should_skip_draw() is True


def test_prepare_and_restore_draw_context_paths(monkeypatch, window: EventInspectorWindow) -> None:
    class _WindowCommands:
        def __init__(self) -> None:
            self.current = None
            self.set_calls: list[object] = []

        def get_window(self):
            return self.current

        def set_window(self, window_obj):
            self.set_calls.append(window_obj)
            self.current = window_obj

    wc = _WindowCommands()
    monkeypatch.setattr("arcadeactions.visualizer.event_window.window_commands", wc)
    monkeypatch.setattr(window, "switch_to", lambda: None)

    ready, restore = window._prepare_draw_context()
    assert ready is True
    assert restore is None
    window._restore_draw_context(restore)

    wc.current = object()

    def bad_switch() -> None:
        raise RuntimeError("switch")

    monkeypatch.setattr(window, "switch_to", bad_switch)
    ready, restore = window._prepare_draw_context()
    assert ready is False
    window._restore_draw_context(restore)


def test_misc_helpers_and_close_callback(monkeypatch, window: EventInspectorWindow) -> None:
    calls: list[tuple[int, int]] = []
    window._forward_key_handler = lambda symbol, modifiers: calls.append((symbol, modifiers)) or True
    assert window._forward_debug_key(arcade.key.F5, 0) is True

    window._forward_key_handler = lambda _symbol, _modifiers: (_ for _ in ()).throw(RuntimeError("err"))
    assert window._forward_debug_key(arcade.key.F5, 0) is False

    class _SizeRecorder:
        def __init__(self) -> None:
            self.calls: list[tuple[int, int]] = []

        def __call__(self, w: int, h: int) -> None:
            self.calls.append((w, h))

    recorder = _SizeRecorder()
    monkeypatch.setattr(arcade.Window, "on_resize", recorder)
    monkeypatch.setattr(window, "set_size", lambda w, h: recorder.calls.append((w, h)))
    monkeypatch.setattr(window, "_update_font_size_for_window", lambda w, h: recorder.calls.append((w, h)))
    assert window._enforce_minimum_size(10, 10) is True
    assert window._enforce_minimum_size(window._base_width, window._base_height) is False

    closed: list[bool] = []
    window._on_close_callback = lambda: closed.append(True)
    monkeypatch.setattr(arcade.Window, "on_close", lambda _self: closed.append(True))
    window.on_close()
    assert closed == [True, True]

    window._on_close_callback = lambda: (_ for _ in ()).throw(RuntimeError("bad close"))
    window.on_close()
