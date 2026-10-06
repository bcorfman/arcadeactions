"""Unit tests for visualizer panel renderers."""

from __future__ import annotations

import arcade

from arcadeactions.visualizer._pyglet_compat import GLException
from arcadeactions.visualizer.panel_renderers import ConditionPanelRenderer, TimelineRenderer


class StubEntry:
    def __init__(self, action_type: str, tag: str | None, result: object) -> None:
        self.action_type = action_type
        self.tag = tag
        self.result = result


class StubDebugger:
    def __init__(self, entries: list[StubEntry]) -> None:
        self.entries = entries


class StubSnapshotStore:
    def __init__(self, current_frame: int) -> None:
        self.current_frame = current_frame


class StubTimelineEntry:
    def __init__(
        self,
        *,
        action_type: str,
        target_id: int | None,
        target_type: str | None,
        tag: str | None,
        start_frame: int | None,
        end_frame: int | None,
        is_active: bool,
    ) -> None:
        self.action_type = action_type
        self.target_id = target_id
        self.target_type = target_type
        self.tag = tag
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.is_active = is_active


class StubTimeline:
    def __init__(self, entries: list[StubTimelineEntry], current_frame: int = 10) -> None:
        self.entries = entries
        self.debug_store = StubSnapshotStore(current_frame)


def test_condition_panel_hidden_clears_text() -> None:
    renderer = ConditionPanelRenderer(StubDebugger(entries=[]))
    renderer.update(visible=False)

    assert renderer.text_objects == []
    assert renderer._text_specs == []


def test_condition_panel_no_entries_message(monkeypatch) -> None:
    renderer = ConditionPanelRenderer(StubDebugger(entries=[]))

    class StubWindow:
        width = 800
        height = 600

    monkeypatch.setattr(arcade, "get_window", lambda: StubWindow())

    renderer.update(visible=True)

    assert any("No condition evaluations yet" in spec.text for spec in renderer._text_specs)


def test_condition_panel_truncates_long_result(monkeypatch) -> None:
    long_text = "x" * 100
    renderer = ConditionPanelRenderer(StubDebugger(entries=[StubEntry("Move", None, long_text)]))

    class StubWindow:
        width = 800
        height = 600

    monkeypatch.setattr(arcade, "get_window", lambda: StubWindow())

    renderer.update(visible=True)

    assert any(spec.text.endswith("...") for spec in renderer._text_specs)


def test_timeline_renderer_updates_and_highlight(monkeypatch) -> None:
    entries = [
        StubTimelineEntry(
            action_type="Move",
            target_id=5,
            target_type="Sprite",
            tag=None,
            start_frame=1,
            end_frame=None,
            is_active=True,
        )
    ]
    timeline = StubTimeline(entries)
    renderer = TimelineRenderer(timeline, highlighted_target_provider=lambda: 5)

    class StubWindow:
        width = 800
        height = 600

    monkeypatch.setattr(arcade, "get_window", lambda: StubWindow())

    renderer.update()

    assert renderer._bars
    assert renderer._highlight_outlines
    assert renderer._text_specs


def test_timeline_renderer_target_names(monkeypatch) -> None:
    entries = [
        StubTimelineEntry(
            action_type="Move",
            target_id=7,
            target_type="Sprite",
            tag="t",
            start_frame=1,
            end_frame=5,
            is_active=True,
        )
    ]
    timeline = StubTimeline(entries)
    renderer = TimelineRenderer(timeline, target_names_provider=lambda: {7: "Hero"})

    class StubWindow:
        width = 800
        height = 600

    monkeypatch.setattr(arcade, "get_window", lambda: StubWindow())

    renderer.update()

    assert any("Hero" in spec.text for spec in renderer._text_specs)


def test_timeline_set_font_size_invalid() -> None:
    timeline = StubTimeline(entries=[])
    renderer = TimelineRenderer(timeline)

    try:
        renderer.set_font_size(0)
    except ValueError as exc:
        assert "font_size" in str(exc)
    else:
        assert False, "expected ValueError"


def test_timeline_draw_resyncs_on_gl_exception(monkeypatch) -> None:
    entries = [
        StubTimelineEntry(
            action_type="Move",
            target_id=1,
            target_type="Sprite",
            tag=None,
            start_frame=1,
            end_frame=2,
            is_active=True,
        )
    ]
    timeline = StubTimeline(entries)
    renderer = TimelineRenderer(timeline)

    class StubWindow:
        width = 800
        height = 600

    monkeypatch.setattr(arcade, "get_window", lambda: StubWindow())
    monkeypatch.setattr(arcade, "draw_lbwh_rectangle_filled", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(arcade, "draw_lrbt_rectangle_filled", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(arcade, "draw_lrbt_rectangle_outline", lambda *_args, **_kwargs: None)
    renderer.update()

    class GlFailText:
        def draw(self) -> None:
            raise GLException()

    renderer.text_objects = [GlFailText()]
    monkeypatch.setattr(
        "arcadeactions.visualizer.panel_renderers._sync_text_objects",
        lambda *_args, **_kwargs: None,
    )
    renderer.draw()
