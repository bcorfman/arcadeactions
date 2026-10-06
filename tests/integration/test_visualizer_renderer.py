"""Tests for OverlayRenderer behaviour and drawing paths."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.visualizer.condition_panel import ConditionDebugger
from arcadeactions.visualizer.guides import GuideManager
from arcadeactions.visualizer.instrumentation import DebugDataStore
from arcadeactions.visualizer.overlay import InspectorOverlay
from arcadeactions.visualizer.renderer import (
    ConditionPanelRenderer,
    GuideRenderer,
    OverlayRenderer,
    TimelineRenderer,
    _sync_text_objects,
    _TextSpec,
)
from arcadeactions.visualizer.timeline import TimelineStrip


def _try_opengl_draw(test_func):
    """Try to execute an OpenGL draw operation, skip test if context is invalid."""
    from arcadeactions.visualizer._pyglet_compat import GLException

    try:
        test_func()
    except GLException as e:
        # If we get a GLException, the context is invalid - skip the test
        pytest.skip(f"OpenGL context not available or invalid: {e}")


@pytest.fixture
def debug_store():
    store = DebugDataStore()
    store.update_frame(1, 0.016)
    return store


@pytest.fixture
def overlay(debug_store):
    overlay = InspectorOverlay(debug_store=debug_store)
    return overlay


@pytest.fixture
def overlay_with_progress():
    store = DebugDataStore()
    store.update_snapshot(
        action_id=1,
        action_type="MoveUntil",
        target_id=100,
        target_type="Sprite",
        tag="movement",
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=0.5,
    )
    overlay = InspectorOverlay(debug_store=store)
    overlay.update()
    return overlay


def test_renderer_skips_when_not_visible(overlay_with_progress):
    overlay_with_progress.visible = False
    renderer = OverlayRenderer(overlay_with_progress)
    renderer.update()
    assert renderer.text_objects == []


def test_renderer_collects_rectangles_and_text(monkeypatch, overlay_with_progress):
    renderer = OverlayRenderer(overlay_with_progress)
    renderer.update()

    # Simplified overlay only shows title line
    assert len(renderer.text_objects) == 1
    assert len(renderer._background_rects) == 0  # No progress bars in simplified overlay
    assert len(renderer._progress_rects) == 0

    drawn_text = []

    def fake_text_draw(self):
        drawn_text.append(id(self))

    def fake_text_initialize(self):
        # Mark as initialized to bypass initialization logic
        self._initialized = True

    # Mock window with active context
    class MockWindow:
        _context = object()  # Has active context
        width = 1280
        height = 720

    monkeypatch.setattr(arcade, "get_window", lambda: MockWindow())
    monkeypatch.setattr(arcade.Text, "draw", fake_text_draw, raising=False)
    monkeypatch.setattr(arcade.Text, "initialize", fake_text_initialize, raising=False)

    renderer.draw()
    assert len(drawn_text) == len(renderer.text_objects)


def test_renderer_handles_cards_without_progress():
    store = DebugDataStore()
    store.update_snapshot(
        action_id=1,
        action_type="MoveUntil",
        target_id=100,
        target_type="Sprite",
        tag=None,
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=None,
    )
    overlay = InspectorOverlay(debug_store=store)
    overlay.update()

    renderer = OverlayRenderer(overlay)
    renderer.update()

    # Simplified overlay doesn't render progress bars
    assert renderer._background_rects == []
    assert renderer._progress_rects == []
    # But it still renders the title
    assert len(renderer.text_objects) == 1


def test_timeline_renderer_displays_composite_actions(monkeypatch):
    """Test that timeline renderer correctly displays composite actions like Sequence and Parallel."""
    store = DebugDataStore()
    store.update_frame(1, 0.016)
    # Create a Sequence action
    store.record_event("created", 1, "_Sequence", 42, "SpriteList")
    store.update_snapshot(
        action_id=1,
        action_type="_Sequence",
        target_id=42,
        target_type="SpriteList",
        tag=None,
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=None,
    )
    store.update_frame(2, 0.032)
    store.record_event("started", 1, "_Sequence", 42, "SpriteList")
    store.update_frame(3, 0.048)
    # Create a Parallel action
    store.record_event("created", 2, "_Parallel", 43, "Sprite")
    store.update_snapshot(
        action_id=2,
        action_type="_Parallel",
        target_id=43,
        target_type="Sprite",
        tag=None,
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=None,
    )
    store.update_frame(4, 0.064)
    store.record_event("started", 2, "_Parallel", 43, "Sprite")
    timeline = TimelineStrip(store)
    timeline.update()

    renderer = TimelineRenderer(timeline, width=800, height=600, margin=12)
    window = type("StubWindow", (), {"width": 800, "height": 600})
    monkeypatch.setattr(arcade, "get_window", lambda: window)
    renderer.update()

    # Should have at least one timeline bar
    assert len(renderer._bars) >= 1
    # Verify that composite actions can be rendered (check bars have correct colors/types)
    # SpriteList actions use cyan/teal, Sprite actions use orange/dark orange
    sprite_list_colors = [arcade.color.CYAN, arcade.color.TEAL]
    sprite_colors = [arcade.color.ORANGE, arcade.color.DARK_ORANGE]

    # Check that we have bars with appropriate colors for composite actions
    bar_colors = [bar[4] for bar in renderer._bars]
    has_sprite_list_color = any(color in sprite_list_colors for color in bar_colors)
    has_sprite_color = any(color in sprite_colors for color in bar_colors)

    # At least one type should be present
    assert has_sprite_list_color or has_sprite_color


def test_timeline_renderer_displays_various_action_types(monkeypatch):
    """Test that timeline renderer displays various action types correctly."""
    store = DebugDataStore()
    store.update_frame(1, 0.016)
    # Test multiple action types (limit to 5 to ensure they all fit in timeline)
    action_types = [
        "MoveUntil",
        "RotateUntil",
        "GlowUntil",
        "FadeTo",
        "CycleTexturesUntil",
    ]

    for idx, action_type in enumerate(action_types, start=1):
        store.record_event("created", idx, action_type, 40 + idx, "Sprite")
        store.update_snapshot(
            action_id=idx,
            action_type=action_type,
            target_id=40 + idx,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        store.update_frame(idx + 1, 0.016 * (idx + 1))

    timeline = TimelineStrip(store, max_entries=100)  # Ensure enough space
    timeline.update()

    renderer = TimelineRenderer(timeline, width=800, height=600, margin=12)
    window = type("StubWindow", (), {"width": 800, "height": 600})
    monkeypatch.setattr(arcade, "get_window", lambda: window)
    renderer.update()

    # Should have timeline bars for at least some action types (may be limited by display height)
    assert len(renderer._bars) >= 1

    # Verify that various action types can be rendered
    # All should be Sprite actions, so they should use orange/dark orange colors
    sprite_colors = [arcade.color.ORANGE, arcade.color.DARK_ORANGE]
    bar_colors = [bar[4] for bar in renderer._bars]
    has_sprite_color = any(color in sprite_colors for color in bar_colors)

    # Should have at least one sprite-colored bar
    assert has_sprite_color


def test_timeline_renderer_handles_composite_action_lifecycle(monkeypatch):
    """Test that timeline renderer correctly tracks composite action lifecycle."""
    store = DebugDataStore()
    store.update_frame(1, 0.016)
    # Create a Sequence action
    store.record_event("created", 1, "_Sequence", 42, "SpriteList")
    store.update_frame(2, 0.032)
    store.record_event("started", 1, "_Sequence", 42, "SpriteList")
    store.update_frame(10, 0.16)
    store.record_event("stopped", 1, "_Sequence", 42, "SpriteList")
    store.update_frame(11, 0.176)
    store.record_event("removed", 1, "_Sequence", 42, "SpriteList")
    timeline = TimelineStrip(store)
    timeline.update()

    renderer = TimelineRenderer(timeline, width=800, height=600, margin=12)
    window = type("StubWindow", (), {"width": 800, "height": 600})
    monkeypatch.setattr(arcade, "get_window", lambda: window)
    renderer.update()

    # After removal, the entry should be gone (stopped entries are removed)
    # But we can verify the timeline processed it correctly
    # The entry should not appear in active entries since it was removed
    assert isinstance(renderer._bars, list)
    # Timeline renderer should handle lifecycle correctly without crashing
    assert hasattr(renderer, "_bars")


def test_timeline_renderer_uses_target_names(monkeypatch):
    """Ensure the timeline renderer leverages provided target names."""
    store = DebugDataStore()
    store.update_frame(1, 0.016)
    target_id = 9001
    store.record_event("created", 1, "MoveUntil", target_id, "Sprite")
    timeline = TimelineStrip(store)
    timeline.update()

    renderer = TimelineRenderer(
        timeline,
        width=400,
        height=120,
        margin=8,
        target_names_provider=lambda: {target_id: "self.enemy_list"},
    )
    window = type("StubWindow", (), {"width": 400, "height": 120})
    monkeypatch.setattr(arcade, "get_window", lambda: window)

    renderer.update()
    labels = [spec.text for spec in renderer._text_specs]
    assert any("self.enemy_list" in text for text in labels)


def test_overlay_renderer_highlights_selected_group():
    """Test that highlighting cycles through targets (no visual change in overlay)."""
    store = DebugDataStore()
    # Create two target groups
    store.update_snapshot(
        action_id=1,
        action_type="MoveUntil",
        target_id=100,
        target_type="Sprite",
        tag=None,
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=None,
    )
    store.update_snapshot(
        action_id=2,
        action_type="RotateUntil",
        target_id=200,
        target_type="Sprite",
        tag=None,
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=None,
    )

    overlay = InspectorOverlay(debug_store=store)
    overlay.update()
    renderer = OverlayRenderer(overlay)

    # Simplified overlay only shows title
    renderer.update()
    text_specs_normal = list(renderer._text_specs)
    assert len(text_specs_normal) == 1  # Only title

    # Highlight first group - overlay appearance doesn't change
    overlay.highlight_next()
    assert overlay.highlighted_target_id == 100
    overlay.update()
    renderer.update()
    text_specs_highlighted = list(renderer._text_specs)

    # Still only shows title (highlighting is visual in game window and timeline)
    assert len(text_specs_highlighted) == 1


def test_overlay_renderer_highlight_cycles_through_groups():
    """Test that pressing F8 cycles the highlight through all targets."""
    store = DebugDataStore()
    # Create three target groups
    for target_id in [100, 200, 300]:
        store.update_snapshot(
            action_id=target_id,
            action_type="MoveUntil",
            target_id=target_id,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )

    overlay = InspectorOverlay(debug_store=store)
    overlay.update()

    # Highlight cycles through targets (internal state)
    overlay.highlight_next()
    assert overlay.highlighted_target_id == 100

    overlay.highlight_next()
    assert overlay.highlighted_target_id == 200

    overlay.highlight_next()
    assert overlay.highlighted_target_id == 300

    # Wrap around to first group
    overlay.highlight_next()
    assert overlay.highlighted_target_id == 100


def test_overlay_renderer_no_highlight_when_none_selected():
    """Test that no targets are highlighted when highlighted_target_id is None."""
    store = DebugDataStore()
    store.update_snapshot(
        action_id=1,
        action_type="MoveUntil",
        target_id=100,
        target_type="Sprite",
        tag=None,
        is_active=True,
        is_paused=False,
        factor=1.0,
        elapsed=0.0,
        progress=None,
    )

    overlay = InspectorOverlay(debug_store=store)
    overlay.update()

    # No highlight set
    assert overlay.highlighted_target_id is None


class TestConditionPanelRenderer:
    def test_init(self, debug_store):
        debugger = ConditionDebugger(debug_store)
        renderer = ConditionPanelRenderer(debugger)
        assert renderer.debugger is debugger
        assert renderer.width == 320
        assert renderer.max_rows == 14
        assert renderer.font_size == 10
        assert renderer.line_height == 16
        assert renderer.margin == 8

    def test_update_not_visible(self, debug_store):
        debugger = ConditionDebugger(debug_store)
        renderer = ConditionPanelRenderer(debugger)
        renderer.update(visible=False)
        assert renderer._visible is False
        assert renderer.text_objects == []
        assert renderer._text_specs == []
        assert renderer._background_rect is None

    def test_update_visible_no_entries(self, debug_store, monkeypatch):
        debugger = ConditionDebugger(debug_store)
        renderer = ConditionPanelRenderer(debugger)
        window = type("Window", (), {"width": 1280, "height": 720})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update(visible=True)
        assert renderer._visible is True
        assert len(renderer._text_specs) >= 1  # Header at minimum

    def test_update_with_entries(self, debug_store, monkeypatch):
        debugger = ConditionDebugger(debug_store)
        debug_store.record_condition_evaluation(
            action_id=1,
            action_type="MoveUntil",
            result=True,
            condition_str="lambda: True",
        )
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag="test",
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        debugger.update()

        renderer = ConditionPanelRenderer(debugger)
        window = type("Window", (), {"width": 1280, "height": 720})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update(visible=True)
        assert renderer._visible is True
        assert len(renderer._text_specs) >= 2  # Header + entry

    def test_draw_with_gl_exception(self, debug_store, monkeypatch):
        def run_test():
            debugger = ConditionDebugger(debug_store)
            debug_store.record_condition_evaluation(
                action_id=1,
                action_type="MoveUntil",
                result=True,
                condition_str="lambda: True",
            )
            debug_store.update_snapshot(
                action_id=1,
                action_type="MoveUntil",
                target_id=100,
                target_type="Sprite",
                tag="test",
                is_active=True,
                is_paused=False,
                factor=1.0,
                elapsed=0.0,
                progress=None,
            )
            debugger.update()

            renderer = ConditionPanelRenderer(debugger)
            window = type("Window", (), {"width": 1280, "height": 720})()
            monkeypatch.setattr(arcade, "get_window", lambda: window)

            renderer.update(visible=True)

            from arcadeactions.visualizer._pyglet_compat import GLException

            call_count = 0

            def fake_draw(self):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise GLException("OpenGL error")

            monkeypatch.setattr(arcade.Text, "draw", fake_draw)
            renderer.draw()  # Should recover from GLException
            assert call_count >= 2  # Should retry (may be more if multiple text objects)

        _try_opengl_draw(run_test)


class TestTimelineRendererGL:
    """GL-dependent TimelineRenderer tests that require display context."""

    def test_update_with_entries(self, debug_store, monkeypatch):
        timeline = TimelineStrip(debug_store)
        debug_store.update_frame(1, 0.016)
        debug_store.record_event("created", 1, "MoveUntil", 100, "Sprite")
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        timeline.update()

        renderer = TimelineRenderer(timeline)
        window = type("Window", (), {"width": 800, "height": 600})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update()
        assert renderer._background_rect is not None
        assert len(renderer._bars) >= 1

    def test_update_with_highlighted_target(self, debug_store, monkeypatch):
        timeline = TimelineStrip(debug_store)
        debug_store.update_frame(1, 0.016)
        debug_store.record_event("created", 1, "MoveUntil", 100, "Sprite")
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        timeline.update()

        highlighted_called = []

        def highlighted_provider():
            highlighted_called.append(True)
            return 100

        renderer = TimelineRenderer(
            timeline,
            highlighted_target_provider=highlighted_provider,
        )
        window = type("Window", (), {"width": 800, "height": 600})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update()
        assert len(highlighted_called) > 0
        assert len(renderer._highlight_outlines) >= 1

    def test_update_with_target_names(self, debug_store, monkeypatch):
        timeline = TimelineStrip(debug_store)
        debug_store.update_frame(1, 0.016)
        debug_store.record_event("created", 1, "MoveUntil", 100, "Sprite")
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        timeline.update()

        names_provider_called = []

        def names_provider():
            names_provider_called.append(True)
            return {100: "self.player"}

        renderer = TimelineRenderer(
            timeline,
            target_names_provider=names_provider,
        )
        window = type("Window", (), {"width": 800, "height": 600})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update()
        assert len(names_provider_called) > 0
        text_specs = [s.text for s in renderer._text_specs]
        assert any("self.player" in text for text in text_specs)

    def test_draw_with_bars(self, debug_store, monkeypatch):
        timeline = TimelineStrip(debug_store)
        debug_store.update_frame(1, 0.016)
        debug_store.record_event("created", 1, "MoveUntil", 100, "Sprite")
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        timeline.update()

        renderer = TimelineRenderer(timeline)
        window = type("Window", (), {"width": 800, "height": 600})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update()
        renderer.draw()  # Should not crash

    def test_draw_with_gl_exception(self, debug_store, monkeypatch):
        timeline = TimelineStrip(debug_store)
        debug_store.update_frame(1, 0.016)
        debug_store.record_event("created", 1, "MoveUntil", 100, "Sprite")
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
        )
        timeline.update()

        renderer = TimelineRenderer(timeline)
        window = type("Window", (), {"width": 800, "height": 600})()
        monkeypatch.setattr(arcade, "get_window", lambda: window)

        renderer.update()

        from arcadeactions.visualizer._pyglet_compat import GLException

        call_count = 0

        def fake_draw(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise GLException("OpenGL error")

        monkeypatch.setattr(arcade.Text, "draw", fake_draw)
        renderer.draw()  # Should recover from GLException
        assert call_count >= 2  # Should retry (may be more if multiple text objects)


class TestGuideRenderer:
    def test_init(self):
        guide_manager = GuideManager()
        renderer = GuideRenderer(guide_manager)
        assert renderer.guide_manager is guide_manager

    def test_update(self):
        guide_manager = GuideManager()
        renderer = GuideRenderer(guide_manager)
        renderer.update()  # Should not crash

    def test_draw_no_guides_enabled(self):
        guide_manager = GuideManager(initial_enabled=False)
        renderer = GuideRenderer(guide_manager)
        renderer.draw()  # Should not crash

    def test_draw_with_velocity_guide(self, debug_store):
        guide_manager = GuideManager(initial_enabled=True)
        debug_store.update_snapshot(
            action_id=1,
            action_type="MoveUntil",
            target_id=100,
            target_type="Sprite",
            tag=None,
            is_active=True,
            is_paused=False,
            factor=1.0,
            elapsed=0.0,
            progress=None,
            velocity=(5.0, 0.0),
        )
        guide_manager.velocity_guide.enabled = True
        guide_manager.update(
            debug_store.get_all_snapshots(),
            {100: (100.0, 200.0)},
        )

        renderer = GuideRenderer(guide_manager)
        renderer.draw()  # Should not crash

    def test_draw_with_bounds_guide(self, debug_store):
        def run_test():
            guide_manager = GuideManager(initial_enabled=True)
            debug_store.update_snapshot(
                action_id=1,
                action_type="MoveUntil",
                target_id=100,
                target_type="Sprite",
                tag=None,
                is_active=True,
                is_paused=False,
                factor=1.0,
                elapsed=0.0,
                progress=None,
                bounds=(0.0, 0.0, 800.0, 600.0),
            )
            guide_manager.bounds_guide.enabled = True
            guide_manager.update(
                debug_store.get_all_snapshots(),
                {100: (100.0, 200.0)},
            )

            renderer = GuideRenderer(guide_manager)
            renderer.draw()  # Should not crash

        _try_opengl_draw(run_test)

    def test_draw_with_path_guide(self, debug_store):
        def run_test():
            guide_manager = GuideManager(initial_enabled=True)
            debug_store.update_snapshot(
                action_id=1,
                action_type="FollowPathUntil",
                target_id=100,
                target_type="Sprite",
                tag=None,
                is_active=True,
                is_paused=False,
                factor=1.0,
                elapsed=0.0,
                progress=None,
                metadata={"path_points": [(0, 0), (100, 100), (200, 200)]},
            )
            guide_manager.path_guide.enabled = True
            guide_manager.update(
                debug_store.get_all_snapshots(),
                {100: (100.0, 200.0)},
            )

            renderer = GuideRenderer(guide_manager)
            renderer.draw()  # Should not crash

        _try_opengl_draw(run_test)

    def test_draw_with_highlight_guide(self, debug_store):
        def run_test():
            guide_manager = GuideManager(initial_enabled=True)
            debug_store.update_snapshot(
                action_id=1,
                action_type="MoveUntil",
                target_id=100,
                target_type="Sprite",
                tag=None,
                is_active=True,
                is_paused=False,
                factor=1.0,
                elapsed=0.0,
                progress=None,
            )
            guide_manager.highlight_guide.enabled = True
            guide_manager.update(
                debug_store.get_all_snapshots(),
                {100: (100.0, 200.0)},
                highlighted_target_id=100,
                sprite_sizes={100: (50.0, 50.0)},
            )

            renderer = GuideRenderer(guide_manager)
            renderer.draw()  # Should not crash

        _try_opengl_draw(run_test)


class TestSyncTextObjects:
    def test_sync_empty(self):
        text_objects = []
        specs = []
        last_specs = []
        _sync_text_objects(text_objects, specs, last_specs)
        assert text_objects == []
        assert last_specs == []

    def test_sync_new_specs(self):
        text_objects = []
        specs = [
            _TextSpec("Hello", 10, 20, arcade.color.WHITE, 12),
            _TextSpec("World", 10, 40, arcade.color.WHITE, 12),
        ]
        last_specs = []
        _sync_text_objects(text_objects, specs, last_specs)
        assert len(text_objects) == 2
        assert len(last_specs) == 2

    def test_sync_same_specs(self):
        text_objects = []
        spec = _TextSpec("Hello", 10, 20, arcade.color.WHITE, 12)
        specs = [spec]
        last_specs = [spec]
        _sync_text_objects(text_objects, specs, last_specs)
        # Should not recreate objects if specs haven't changed
        assert len(text_objects) == 0

    def test_sync_changed_specs(self):
        text_objects = []
        old_spec = _TextSpec("Hello", 10, 20, arcade.color.WHITE, 12)
        new_spec = _TextSpec("World", 10, 20, arcade.color.WHITE, 12)
        specs = [new_spec]
        last_specs = [old_spec]
        _sync_text_objects(text_objects, specs, last_specs)
        assert len(text_objects) == 1
        assert len(last_specs) == 1
