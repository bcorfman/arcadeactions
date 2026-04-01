"""Tests for physics-based FollowPathUntil steering.

These tests verify that FollowPathUntil can optionally use physics steering
when use_physics=True and a PymunkPhysicsEngine is present.
"""

from __future__ import annotations

from typing import Any

import arcade
import pytest

from arcadeactions import Action
from arcadeactions import physics_adapter as pa
from arcadeactions.conditional import FollowPathUntil, infinite


class _StubPhysicsEngine:
    """Minimal stub mimicking the subset of PymunkPhysicsEngine we need."""

    def __init__(self) -> None:
        self._sprites: dict[int, arcade.Sprite] = {}
        self._velocities: dict[int, tuple[float, float]] = {}
        # Track calls for assertions
        self.calls: list[tuple[str, tuple[Any, ...], dict]] = []

    # API -----------------------------------------------------------------
    def add_sprite(self, sprite: arcade.Sprite, mass: float = 1.0) -> None:
        self._sprites[id(sprite)] = sprite
        self._velocities[id(sprite)] = (0.0, 0.0)

    def has_sprite(self, sprite: arcade.Sprite) -> bool:
        return id(sprite) in self._sprites

    def get_velocity(self, sprite: arcade.Sprite) -> tuple[float, float]:
        self.calls.append(("get_velocity", (sprite,), {}))
        return self._velocities.get(id(sprite), (0.0, 0.0))

    def set_velocity(self, sprite: arcade.Sprite, velocity: tuple[float, float]) -> None:
        self.calls.append(("set_velocity", (sprite, velocity), {}))
        self._velocities[id(sprite)] = velocity

    def apply_force(self, sprite: arcade.Sprite, force: tuple[float, float]) -> None:
        self.calls.append(("apply_force", (sprite, force), {}))

    def apply_impulse(self, sprite: arcade.Sprite, impulse: tuple[float, float]) -> None:
        self.calls.append(("apply_impulse", (sprite, impulse), {}))

    def set_angular_velocity(self, sprite: arcade.Sprite, omega: float) -> None:
        self.calls.append(("set_angular_velocity", (sprite, omega), {}))


@pytest.fixture()
def stub_engine(monkeypatch: pytest.MonkeyPatch) -> _StubPhysicsEngine:  # noqa: PT004
    """Provide a stub physics engine & patch adapter.detect_engine to use it."""

    engine = _StubPhysicsEngine()

    # Patch detect_engine to return our stub when sprite registered
    original_detect = pa.detect_engine

    def _fake_detect(sprite: Any, *, provided: Any | None = None):  # noqa: ANN401
        if engine.has_sprite(sprite):  # type: ignore[attr-defined]
            return engine  # type: ignore[return-value]
        return original_detect(sprite, provided=provided)

    monkeypatch.setattr(pa, "detect_engine", _fake_detect, raising=True)
    return engine


def test_followpath_uses_physics_steering(stub_engine: _StubPhysicsEngine) -> None:
    """When use_physics=True and sprite is in engine, FollowPathUntil applies steering impulses."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    stub_engine.add_sprite(sprite, mass=1.0)

    # Simple straight path
    path = [(100, 100), (200, 100)]
    action = FollowPathUntil(
        control_points=path,
        velocity=100,  # pixels per second
        condition=infinite,
        use_physics=True,
        steering_gain=5.0,
    )
    action.apply(sprite)

    # Update once - should compute steering and apply impulse
    Action.update_all(1 / 60)

    # Verify impulse was applied (steering toward path)
    assert any(call[0] == "apply_impulse" for call in stub_engine.calls), (
        "FollowPathUntil with use_physics=True should apply steering impulses"
    )


def test_followpath_physics_with_rotation(stub_engine: _StubPhysicsEngine) -> None:
    """When use_physics=True with rotate_with_path, angular velocity is set via physics."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    stub_engine.add_sprite(sprite, mass=1.0)

    path = [(100, 100), (200, 200)]
    action = FollowPathUntil(
        control_points=path,
        velocity=100,
        condition=infinite,
        use_physics=True,
        rotate_with_path=True,
    )
    action.apply(sprite)

    Action.update_all(1 / 60)

    # Should call set_angular_velocity for rotation
    assert any(call[0] == "set_angular_velocity" for call in stub_engine.calls), (
        "FollowPathUntil with use_physics=True and rotate_with_path should set angular velocity"
    )


def test_followpath_kinematic_without_physics_flag() -> None:
    """When use_physics=False (default), position is updated directly (kinematic)."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    initial_x = sprite.center_x

    path = [(100, 100), (200, 100)]
    action = FollowPathUntil(
        control_points=path,
        velocity=100,
        condition=infinite,
        use_physics=False,  # Explicit default
    )
    action.apply(sprite)

    Action.update_all(1 / 60)

    # Position should be updated directly (kinematic movement)
    assert sprite.center_x > initial_x, "FollowPathUntil without physics should update position directly"


def test_followpath_ignores_physics_without_engine() -> None:
    """When use_physics=True but no engine, fallback to kinematic."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    initial_x = sprite.center_x

    path = [(100, 100), (200, 100)]
    action = FollowPathUntil(
        control_points=path,
        velocity=100,
        condition=infinite,
        use_physics=True,  # Flag enabled but no engine
    )
    action.apply(sprite)

    Action.update_all(1 / 60)

    # Should fall back to kinematic movement
    assert sprite.center_x > initial_x, (
        "FollowPathUntil with use_physics=True but no engine should fall back to kinematic"
    )


def test_followpath_physics_angle_normalization(stub_engine: _StubPhysicsEngine) -> None:
    """Test angle normalization in physics mode when sprite needs large rotation."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    sprite.angle = 270  # Facing down
    stub_engine.add_sprite(sprite, mass=1.0)

    # Path that requires rotation (moving right, sprite should rotate to 0 degrees)
    path = [(100, 100), (200, 100)]
    action = FollowPathUntil(
        control_points=path,
        velocity=100,
        condition=infinite,
        use_physics=True,
        rotate_with_path=True,
        rotation_offset=0,
    )
    action.apply(sprite)

    # Update multiple times to trigger angle normalization
    for _ in range(5):
        Action.update_all(1 / 60)

    # Verify angular velocity was set (angle normalization happened)
    assert any(call[0] == "set_angular_velocity" for call in stub_engine.calls)


def test_followpath_completion_with_callback() -> None:
    """Test path completion triggers on_stop callback."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100

    callback_triggered = []

    def on_complete(data):
        callback_triggered.append(True)

    # Very short path that completes quickly
    path = [(100, 100), (101, 100)]
    action = FollowPathUntil(
        control_points=path,
        velocity=1000,  # High velocity to complete quickly
        condition=infinite,
        on_stop=on_complete,
    )
    action.apply(sprite)

    # Update multiple times to ensure completion
    for _ in range(10):
        Action.update_all(1 / 60)

    # Callback should have been triggered
    assert len(callback_triggered) > 0, "on_stop callback should be triggered on path completion"


def test_followpath_natural_completion_skips_external_condition_same_frame() -> None:
    """Natural path completion should win before an external condition is consulted."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    callback_args: list[tuple[object, ...]] = []
    condition_calls = {"count": 0}

    def condition_with_data():
        condition_calls["count"] += 1
        return {"source": "condition"}

    def on_stop(*args):
        callback_args.append(args)

    action = FollowPathUntil(
        control_points=[(100, 100), (101, 100)],
        velocity=1000,
        condition=condition_with_data,
        on_stop=on_stop,
    )
    action.apply(sprite)

    Action.update_all(1 / 60)

    assert action.done
    assert condition_calls["count"] == 0
    assert callback_args == [()]
    assert action.condition_data is None
    assert sprite.center_x == pytest.approx(101.0)
    assert sprite.center_y == pytest.approx(100.0)


def test_followpath_external_condition_data_stops_before_path_completion() -> None:
    """External stop data should propagate unchanged when the path has not completed yet."""
    sprite = arcade.Sprite()
    sprite.center_x = 0
    sprite.center_y = 0
    callback_args: list[tuple[object, ...]] = []
    condition_calls = {"count": 0}

    def condition_with_data():
        condition_calls["count"] += 1
        if condition_calls["count"] >= 2:
            return {"reason": "interrupt", "frame": condition_calls["count"]}
        return False

    def on_stop(*args):
        callback_args.append(args)

    action = FollowPathUntil(
        control_points=[(0, 0), (1000, 0)],
        velocity=30,
        condition=condition_with_data,
        on_stop=on_stop,
    )
    action.apply(sprite)

    for _ in range(5):
        Action.update_all(1 / 60)
        if action.done:
            break

    assert action.done
    assert callback_args == [({"reason": "interrupt", "frame": 2},)]
    assert action.condition_data == {"reason": "interrupt", "frame": 2}
    assert sprite.center_x < 1000


def test_followpath_small_movement_with_rotation() -> None:
    """Test rotation handling when movement vector is very small."""
    sprite = arcade.Sprite()
    sprite.center_x = 100
    sprite.center_y = 100
    initial_angle = 45
    sprite.angle = initial_angle

    # Path with very close points (small movement vectors)
    path = [(100, 100), (100.0001, 100.0001)]
    action = FollowPathUntil(
        control_points=path,
        velocity=0.01,  # Very slow
        condition=infinite,
        rotate_with_path=True,
    )
    action.apply(sprite)

    # Update - should handle small vectors gracefully
    Action.update_all(1 / 60)

    # Should not crash and should maintain angle continuity
    # (angle should be set, either to new direction or preserved from previous)
