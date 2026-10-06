"""Unit tests for OverlayRenderer behavior."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.visualizer._pyglet_compat import GLException
from arcadeactions.visualizer.overlay_renderer import OverlayRenderer


class DummySnapshot:
    def __init__(self, progress: float | None = None) -> None:
        self.progress = progress


class DummyCard:
    def __init__(self, text: str, *, progress: float | None = None, width: float = 120.0) -> None:
        self._text = text
        self.snapshot = DummySnapshot(progress)
        self.width = width

    def get_display_text(self) -> str:
        return self._text

    def get_progress_bar_width(self) -> float:
        if self.snapshot.progress is None:
            return 0.0
        return max(0.0, min(self.width, self.width * float(self.snapshot.progress)))


class DummyGroup:
    def __init__(self, target_id: int, header: str, cards: list[DummyCard]) -> None:
        self.target_id = target_id
        self.cards = cards
        self._header = header

    def get_header_text(self) -> str:
        return self._header


class DummyOverlay:
    def __init__(self) -> None:
        self.visible = True
        self.position = "upper_left"
        self.highlighted_target_id: int | None = None
        self.x = 0

    def get_total_action_count(self) -> int:
        return 3


@pytest.fixture
def overlay() -> DummyOverlay:
    return DummyOverlay()


def test_update_clears_when_hidden(overlay: DummyOverlay) -> None:
    renderer = OverlayRenderer(overlay)
    overlay.visible = False

    renderer.update()

    assert renderer.text_objects == []
    assert renderer._text_specs == []
    assert renderer._background_rects == []
    assert renderer._progress_rects == []


def test_update_builds_title(monkeypatch, overlay: DummyOverlay) -> None:
    renderer = OverlayRenderer(overlay)

    class StubWindow:
        width = 800
        height = 600

    monkeypatch.setattr(arcade, "get_window", lambda: StubWindow())

    renderer.update()

    assert len(renderer._text_specs) == 1
    assert "ACE Visualizer" in renderer._text_specs[0].text


def test_render_group_and_card_builds_specs(overlay: DummyOverlay) -> None:
    renderer = OverlayRenderer(overlay)
    overlay.x = 10
    overlay.highlighted_target_id = 42

    card = DummyCard("Line1\nLine2", progress=0.5)
    group = DummyGroup(42, "Target #42", [card])

    end_y = renderer._render_group(group, 100)

    assert end_y < 100
    assert any("Target #42" in spec.text for spec in renderer._text_specs)
    assert any(spec.text == "Line1" for spec in renderer._text_specs)
    assert renderer._background_rects
    assert renderer._progress_rects


def test_draw_resyncs_on_gl_exception(monkeypatch, overlay: DummyOverlay) -> None:
    renderer = OverlayRenderer(overlay)
    overlay.visible = True
    renderer._text_specs = []
    renderer._last_text_specs = []
    renderer.text_objects = []

    called = {"count": 0}

    def boom() -> None:
        called["count"] += 1
        raise GLException()

    class StubText:
        def draw(self) -> None:
            boom()

    renderer.text_objects = [StubText()]

    monkeypatch.setattr(
        "arcadeactions.visualizer.overlay_renderer._sync_text_objects",
        lambda *_args, **_kwargs: None,
    )

    renderer.draw()

    assert called["count"] == 1
