"""Detailed tests for movement pattern helpers."""

from __future__ import annotations

import math
from types import SimpleNamespace

import arcade
import pytest

from arcadeactions import Action
from arcadeactions.pattern import (
    _calculate_velocity_to_target,
    _clone_formation_sprites,
    _create_precision_condition_and_callback,
    _determine_min_spacing,
    _find_nearest,
    _generate_arc_spawn_positions,
    _min_conflicts_sprite_assignment,
    _validate_entry_kwargs,
    create_bounce_pattern,
    create_figure_eight_pattern,
    create_formation_entry_from_sprites,
    create_orbit_pattern,
    create_patrol_pattern,
    create_wave_pattern,
    create_zigzag_pattern,
    sprite_count,
)


class DummySprite:
    def __init__(self, x: float, y: float):
        self.center_x = x
        self.center_y = y
        self.change_x = 0.0
        self.change_y = 0.0


def test_zigzag_pattern_final_segment_clamps_progress():
    pattern = create_zigzag_pattern(width=12, height=6, velocity=3, segments=3)

    dx, dy = pattern._offset_fn(1.0)

    assert pytest.approx(dx, abs=1e-6) == 12  # Ends on right side
    assert pytest.approx(dy, abs=1e-6) == 18  # 3 segments * height


def test_wave_pattern_full_cycle_snaps_to_origin():
    pattern = create_wave_pattern(amplitude=20, length=60, velocity=5)

    dx, dy = pattern._offset_fn(1.0)
    assert dx == pytest.approx(0.0)
    assert dy == pytest.approx(0.0)


def test_wave_pattern_partial_cycle_preserves_offset():
    pattern = create_wave_pattern(
        amplitude=15,
        length=40,
        velocity=4,
        start_progress=0.5,
        end_progress=0.75,
    )

    dx, dy = pattern._offset_fn(1.0)
    assert dx != pytest.approx(0.0) or dy != pytest.approx(0.0)


def test_figure_eight_pattern_validates_velocity():
    with pytest.raises(ValueError):
        create_figure_eight_pattern((0, 0), width=100, height=50, velocity=0)


def test_figure_eight_pattern_exposes_control_points():
    pattern = create_figure_eight_pattern((0, 0), width=100, height=50, velocity=5)
    control_points = pattern.control_points
    assert len(control_points) == 17
    start_x, start_y = control_points[0]
    end_x, end_y = control_points[-1]
    assert math.isclose(start_x, end_x, abs_tol=1e-12)
    assert math.isclose(start_y, end_y, abs_tol=1e-12)


def test_orbit_pattern_completes_cycle(cleanup_actions):
    action = create_orbit_pattern((0, 0), radius=20, velocity=5, clockwise=True)
    sprite = arcade.Sprite(":resources:images/items/star.png")
    sprite.center_x = 20
    sprite.center_y = 0

    action.apply(sprite, tag="orbit_full")

    for _ in range(600):
        Action.update_all(1 / 60)
        if action.done:
            break

    assert action.done
    assert pytest.approx(sprite.center_x, abs=1e-1) == 20
    assert pytest.approx(sprite.center_y, abs=1e-1) == 0


def test_orbit_pattern_handles_centered_sprite(cleanup_actions):
    action = create_orbit_pattern((0, 0), radius=15, velocity=4, clockwise=False)
    sprite = arcade.Sprite(":resources:images/items/star.png")
    sprite.center_x = 0
    sprite.center_y = 0

    action.apply(sprite, tag="orbit_center")
    assert pytest.approx(sprite.center_x, abs=1e-6) == 15
    assert pytest.approx(sprite.center_y, abs=1e-6) == 0


def test_orbit_pattern_reset_and_clone():
    action = create_orbit_pattern((0, 0), radius=10, velocity=3, clockwise=True)
    sprite = arcade.Sprite(":resources:images/items/star.png")
    sprite.center_x = 10
    sprite.center_y = 0
    action.apply(sprite, tag="orbit_reset")
    Action.update_all(1 / 60)
    assert action._states  # type: ignore[attr-defined]

    action.reset()
    assert action._states == {}  # type: ignore[attr-defined]

    clone = action.clone()
    assert clone is not action


def test_orbit_pattern_marks_condition_met_on_completion(cleanup_actions):
    action = create_orbit_pattern((0, 0), radius=12, velocity=4, clockwise=True)
    sprite = arcade.Sprite(":resources:images/items/star.png")
    sprite.center_x = 12
    sprite.center_y = 0

    action.apply(sprite, tag="orbit_condition_met")

    for _ in range(600):
        Action.update_all(1 / 60)
        if action.done:
            break

    assert action.done
    assert action._condition_met
    assert pytest.approx(sprite.center_x, abs=1e-1) == 12
    assert pytest.approx(sprite.center_y, abs=1e-1) == 0


def test_create_bounce_pattern_validates_axis():
    with pytest.raises(ValueError):
        create_bounce_pattern((5, 0), (0, 0, 100, 100), axis="z")


def test_create_patrol_pattern_returns_axis_specific_class():
    action = create_patrol_pattern((5, 0), (0, 0, 100, 100), axis="x")
    assert action.boundary_behavior == "bounce"


@pytest.mark.parametrize(
    ("comparison", "current", "target", "expected"),
    [
        ("<=", 3, 5, True),
        (">=", 5, 3, True),
        ("<", 2, 3, True),
        (">", 4, 3, True),
        ("==", 4, 4, True),
        ("!=", 5, 4, True),
    ],
)
def test_sprite_count_comparisons(comparison, current, target, expected):
    sprite_list = arcade.SpriteList()
    for _ in range(current):
        sprite_list.append(arcade.Sprite(":resources:images/items/star.png"))
    condition = sprite_count(sprite_list, target, comparison=comparison)
    assert condition() is expected


def test_sprite_count_invalid_operator():
    with pytest.raises(ValueError):
        condition = sprite_count(arcade.SpriteList(), 1, comparison="??")
        condition()


def test_precision_condition_slows_and_snaps():
    sprite = DummySprite(0, 0)
    sprite.change_x = 10
    sprite.change_y = 0
    condition = _create_precision_condition_and_callback((20, 0), sprite)

    assert condition() is False
    sprite.center_x = 5
    assert condition() is False
    assert sprite.change_x < 10

    sprite.center_x = 19.1
    assert condition() is True
    assert sprite.change_x == 0
    assert sprite.center_x == 20


def test_generate_arc_spawn_positions_rebalances_spacing():
    formation = arcade.SpriteList()
    for _ in range(12):
        spr = arcade.Sprite(":resources:images/items/star.png")
        spr.center_x = 100
        spr.center_y = 100
        formation.append(spr)

    positions = _generate_arc_spawn_positions(formation, (0, 0, 200, 200), min_spacing=5.0)
    assert len(positions) == len(formation)
    assert all(math.isfinite(x) and math.isfinite(y) for x, y in positions)


def test_find_nearest_handles_extra_spawn_positions():
    spawn_positions = [(0, 0), (100, 0), (200, 0)]
    target_positions = [(10, 0), (190, 0)]

    assignments = _find_nearest(spawn_positions, target_positions)
    assert len(assignments) == len(target_positions)


def test_validate_entry_kwargs_requires_window_bounds():
    with pytest.raises(ValueError):
        _validate_entry_kwargs({})

    validated = _validate_entry_kwargs({"window_bounds": (0, 0, 100, 100)})
    assert validated["velocity"] == 5.0
    assert validated["stagger_delay_frames"] == 30


def test_determine_min_spacing_uses_sprite_dimensions():
    """Test min spacing uses sprite width/height when available."""
    dummy = SimpleNamespace(width=80, height=40)
    spacing = _determine_min_spacing([dummy])
    assert spacing == 120  # 1.5 * width


def test_determine_min_spacing_uses_texture_dimensions():
    """Test min spacing uses texture size when width/height are missing."""
    dummy = SimpleNamespace(texture=SimpleNamespace(width=40, height=20))
    spacing = _determine_min_spacing([dummy])
    assert spacing == 60  # 1.5 * texture width


def test_determine_min_spacing_uses_default_when_missing_dimensions():
    """Test min spacing falls back to default when no dimensions are available."""
    dummy = SimpleNamespace()
    spacing = _determine_min_spacing([dummy])
    assert spacing == 96  # 1.5 * default 64


def test_clone_formation_sprites_handles_missing_texture():
    dummy = SimpleNamespace(texture=None)
    clones = _clone_formation_sprites([dummy])
    assert len(clones) == 1


def test_clone_formation_sprites_defaults_scale_when_missing():
    template = arcade.Sprite(":resources:images/items/star.png")
    dummy = SimpleNamespace(texture=template.texture)
    clones = _clone_formation_sprites([dummy])
    assert len(clones) == 1
    assert clones[0].scale in (1.0, (1.0, 1.0))


def test_calculate_velocity_to_target_handles_zero_distance():
    assert _calculate_velocity_to_target((0, 0), (0, 0), 5) == (0, 0)


def test_min_conflicts_assignment_returns_mapping(monkeypatch):
    target = arcade.SpriteList()
    for x in (0, 100):
        spr = arcade.Sprite(":resources:images/items/star.png")
        spr.center_x = x
        spr.center_y = 0
        target.append(spr)

    spawn_positions = [(0, 100), (100, 100)]
    assignments = _min_conflicts_sprite_assignment(target, spawn_positions, max_iterations=10, time_limit=0.01)
    assert assignments
    assert set(assignments.keys()) <= {0, 1}


def test_create_formation_entry_from_sprites_uses_helper_monkeypatched(monkeypatch):
    import arcadeactions.pattern as pattern_module

    target = arcade.SpriteList()
    for x in (100, 200):
        spr = arcade.Sprite(":resources:images/items/star.png")
        spr.center_x = x
        spr.center_y = 300
        target.append(spr)

    clones = arcade.SpriteList()
    for _ in range(len(target)):
        clone = arcade.Sprite(":resources:images/items/star.png")
        clones.append(clone)

    monkeypatch.setattr(
        pattern_module,
        "_validate_entry_kwargs",
        lambda kwargs: {"window_bounds": (0, 0, 800, 600), "velocity": 5.0, "stagger_delay_frames": 10},
    )
    monkeypatch.setattr(pattern_module, "_clone_formation_sprites", lambda tf: clones)
    monkeypatch.setattr(pattern_module, "_determine_min_spacing", lambda tf: 10.0)
    monkeypatch.setattr(
        pattern_module,
        "_generate_arc_spawn_positions",
        lambda tf, window_bounds, spacing: [(0, 600), (800, 600)],
    )
    monkeypatch.setattr(
        pattern_module,
        "_find_nearest",
        lambda spawn_positions, target_positions: [(10.0, 0, 0), (20.0, 1, 1)],
    )
    monkeypatch.setattr(
        pattern_module,
        "_min_conflicts_sprite_assignment",
        lambda *_, **__: {0: 0, 1: 1},
    )

    entries = create_formation_entry_from_sprites(target, window_bounds=(0, 0, 800, 600))
    assert len(entries) == 2
    for sprite, action, idx in entries:
        assert isinstance(sprite, arcade.Sprite)
        assert action is not None
        assert idx in {0, 1}


def test_create_formation_entry_from_sprites_supports_multiple_waves_with_delay(monkeypatch):
    import arcadeactions.pattern as pattern_module

    target = arcade.SpriteList()
    for x in (100, 200):
        spr = arcade.Sprite(":resources:images/items/star.png")
        spr.center_x = x
        spr.center_y = 300
        target.append(spr)

    clones = arcade.SpriteList()
    for _ in range(len(target)):
        clone = arcade.Sprite(":resources:images/items/star.png")
        clones.append(clone)

    monkeypatch.setattr(
        pattern_module,
        "_validate_entry_kwargs",
        lambda kwargs: {"window_bounds": (0, 0, 800, 600), "velocity": 5.0, "stagger_delay_frames": 10},
    )
    monkeypatch.setattr(pattern_module, "_clone_formation_sprites", lambda tf: clones)
    monkeypatch.setattr(pattern_module, "_determine_min_spacing", lambda tf: 10.0)
    monkeypatch.setattr(
        pattern_module,
        "_generate_arc_spawn_positions",
        lambda tf, window_bounds, spacing: [(0, 600), (800, 600)],
    )
    monkeypatch.setattr(
        pattern_module,
        "_find_nearest",
        lambda spawn_positions, target_positions: [(10.0, 0, 0), (20.0, 1, 1)],
    )
    # Return two waves so wave_idx=1 triggers DelayFrames(...) and sequence(delay, move).
    monkeypatch.setattr(
        pattern_module,
        "_min_conflicts_sprite_assignment",
        lambda *_, **__: [{0: 0}, {1: 1}],
    )

    entries = create_formation_entry_from_sprites(target, window_bounds=(0, 0, 800, 600))
    assert len(entries) == 2

    delayed = [action for _sprite, action, _idx in entries if hasattr(action, "actions")]
    assert delayed, "Expected at least one sequence action for delayed waves"
