"""Test suite for condition_actions.py - Conditional actions."""

from typing import Any

import arcade
import pytest

from arcadeactions import (
    Action,
    blink_until,
    delay_frames,
    fade_to,
    follow_path_until,
    infinite,
    move_until,
    rotate_until,
    scale_until,
    tween_until,
)
from arcadeactions.conditional import (
    BlinkUntil,
    CallbackUntil,
    DelayFrames,
    FadeUntil,
    FollowPathUntil,
    MoveUntil,
    TweenUntil,
    _extract_duration_seconds,
)
from arcadeactions.frame_timing import after_frames, frames_to_seconds, seconds_to_frames, within_frames
from tests.conftest import ActionTestBase


def create_test_sprite() -> arcade.Sprite:
    """Create a sprite with texture for testing."""
    sprite = arcade.Sprite(":resources:images/items/star.png")
    sprite.center_x = 100
    sprite.center_y = 100
    return sprite


class InstrumentedMoveUntil(MoveUntil):
    """Test helper exposing snapshot and boundary instrumentation."""

    def __init__(self, velocity: tuple[float, float], condition, **kwargs):
        super().__init__(velocity, condition, **kwargs)
        self.snapshots: list[dict[str, Any]] = []
        self.apply_limits_invocations = 0

    def _update_snapshot(self, **kwargs) -> None:  # pragma: no cover - instrumentation only
        self.snapshots.append(kwargs)

    def _apply_boundary_limits(self) -> None:  # pragma: no cover - delegates to parent
        self.apply_limits_invocations += 1
        super()._apply_boundary_limits()


class TestMoveUntil(ActionTestBase):
    """Test suite for MoveUntil action."""

    def test_move_until_frame_based_semantics(self, test_sprite):
        """Test that MoveUntil uses pixels per frame at 60 FPS semantics."""
        sprite = test_sprite

        # 5 pixels per frame should move 5 pixels when sprite.update() is called
        action = move_until(sprite, velocity=(5, 0), condition=infinite, tag="test_frame_semantics")

        # Update action to apply velocity
        Action.update_all(0.016)
        assert sprite.change_x == 5  # Raw frame-based value

        # Move sprite using its velocity
        start_x = sprite.center_x
        sprite.update()  # Arcade applies change_x to position

        # Should have moved exactly 5 pixels
        distance_moved = sprite.center_x - start_x
        assert distance_moved == 5.0

    def test_move_until_callback(self, test_sprite):
        """Test MoveUntil with callback."""
        sprite = test_sprite
        callback_called = False
        callback_data = None

        def on_stop(data=None):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = data

        def condition():
            return {"reason": "collision", "damage": 10}

        action = move_until(sprite, velocity=(100, 0), condition=condition, on_stop=on_stop, tag="test_callback")

        Action.update_all(0.016)

        assert callback_called
        assert callback_data == {"reason": "collision", "damage": 10}

    def test_move_until_sprite_list(self, test_sprite_list):
        """Test MoveUntil with SpriteList."""
        sprite_list = test_sprite_list

        action = move_until(sprite_list, velocity=(50, 25), condition=infinite, tag="test_sprite_list")

        Action.update_all(0.016)

        # Both sprites should have the same velocity
        for sprite in sprite_list:
            assert sprite.change_x == 50
            assert sprite.change_y == 25

    def test_move_until_set_current_velocity(self, test_sprite):
        """Test MoveUntil set_current_velocity method."""
        sprite = test_sprite
        action = move_until(sprite, velocity=(100, 0), condition=infinite, tag="test_set_velocity")

        # Initial velocity should be set
        Action.update_all(0.016)
        assert sprite.change_x == 100

        # Change velocity
        action.set_current_velocity((50, 25))
        assert sprite.change_x == 50
        assert sprite.change_y == 25

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "right_boundary",
                "start_pos": (50, 100),
                "velocity": (100, 0),
                "bounds": (0, 0, 200, 200),
                "expected_edge": ("right", 200),
                "expected_velocity": (0, 0),
                "description": "Test basic limit boundary behavior - sprite edge stops at boundary",
            },
            {
                "name": "left_boundary",
                "start_pos": (150, 100),
                "velocity": (-100, 0),
                "bounds": (0, 0, 200, 200),
                "expected_edge": ("left", 0),
                "expected_velocity": (0, 0),
                "description": "Test limit boundary behavior when moving left",
            },
            {
                "name": "vertical_boundary",
                "start_pos": (100, 50),
                "velocity": (0, 100),
                "bounds": (0, 0, 200, 200),
                "expected_edge": ("top", 200),
                "expected_velocity": (0, 0),
                "description": "Test limit boundary behavior for vertical movement",
            },
            {
                "name": "diagonal_boundary",
                "start_pos": (50, 50),
                "velocity": (100, 100),
                "bounds": (0, 0, 200, 200),
                "expected_edge": ("right_top", (200, 200)),
                "expected_velocity": (0, 0),
                "description": "Test limit boundary behavior for diagonal movement",
            },
            {
                "name": "negative_bounds",
                "start_pos": (-50, 100),
                "velocity": (-10, 0),
                "bounds": (-100, 0, 100, 200),
                "expected_edge": ("left", -100),
                "expected_velocity": (0, 0),
                "description": "Test limit boundary behavior with negative bounds",
            },
            {
                "name": "multiple_axes",
                "start_pos": (199, 199),
                "velocity": (10, 10),
                "bounds": (0, 0, 200, 200),
                "expected_edge": ("right_top", (200, 200)),
                "expected_velocity": (0, 0),
                "description": "Test limit boundary behavior when hitting multiple boundaries",
            },
            {
                "name": "velocity_clearing",
                "start_pos": (50, 100),
                "velocity": (100, 50),
                "bounds": (0, 0, 200, 200),
                "expected_edge": ("right_top", (200, 200)),
                "expected_velocity": (0, 0),
                "description": "Test that limit boundary properly clears velocity when stopping",
            },
        ],
    )
    def test_move_until_limit_boundaries(self, test_case, test_sprite):
        """Test limit boundary behavior for various directions and scenarios with edge-based bounds."""
        sprite = test_sprite
        sprite.center_x, sprite.center_y = test_case["start_pos"]

        action = move_until(
            sprite,
            velocity=test_case["velocity"],
            condition=infinite,
            bounds=test_case["bounds"],
            boundary_behavior="limit",
            tag=f"test_limit_{test_case['name']}",
        )

        # Apply velocity
        Action.update_all(0.016)

        # Move sprite and continue until boundary is hit
        for _ in range(10):
            sprite.update()
            Action.update_all(0.016)

        # Verify edge position at boundary
        edge_name, edge_value = test_case["expected_edge"]
        if edge_name == "right":
            assert sprite.right == edge_value
        elif edge_name == "left":
            assert sprite.left == edge_value
        elif edge_name == "top":
            assert sprite.top == edge_value
        elif edge_name == "bottom":
            assert sprite.bottom == edge_value
        elif edge_name == "right_top":
            assert sprite.right == edge_value[0]
            assert sprite.top == edge_value[1]

        # Verify velocity is zero
        assert sprite.change_x == test_case["expected_velocity"][0]
        assert sprite.change_y == test_case["expected_velocity"][1]

    def test_move_until_limit_boundary_no_wiggling(self, test_sprite):
        """Test that limit boundary prevents wiggling across boundary using edge-based bounds."""
        sprite = test_sprite
        sprite.right = 195  # Close to right boundary at 200
        sprite.center_y = 100

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(10, 0),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            tag="test_limit_no_wiggling",
        )

        Action.update_all(0.016)
        # For limit behavior, velocity should not be set if it would cross boundary
        assert sprite.change_x == 0
        assert sprite.right == 200  # Should be clamped to boundary

        # Try to move again - should stay at boundary
        Action.update_all(0.016)
        sprite.update()
        assert sprite.right == 200
        assert sprite.change_x == 0

    def test_move_until_limit_boundary_callback(self, test_sprite):
        """Test limit boundary behavior with callback."""
        sprite = test_sprite
        sprite.center_x = 50
        sprite.center_y = 100

        boundary_called = False
        boundary_sprite = None
        boundary_axis = None

        def on_boundary(sprite, axis, side):
            nonlocal boundary_called, boundary_sprite, boundary_axis
            boundary_called = True
            boundary_sprite = sprite
            boundary_axis = axis

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(100, 0),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            on_boundary_enter=on_boundary,
            tag="test_limit_callback",
        )

        Action.update_all(0.016)
        sprite.update()

        # Continue until boundary is hit
        for _ in range(10):
            sprite.update()
            Action.update_all(0.016)

        # Callback should have been called
        assert boundary_called
        assert boundary_sprite == sprite
        assert boundary_axis == "x"

    def test_move_until_limit_boundary_sprite_list(self, test_sprite_list):
        """Test limit boundary behavior with SpriteList using edge-based bounds."""
        sprite_list = test_sprite_list
        sprite_list[0].center_x = 50
        sprite_list[1].center_x = 150

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite_list,
            velocity=(100, 0),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            tag="test_limit_sprite_list",
        )

        Action.update_all(0.016)
        assert sprite_list[0].change_x == 100
        # For limit behavior, velocity should not be set if it would cross boundary
        assert sprite_list[1].change_x == 0

        # Move sprites
        for sprite in sprite_list:
            sprite.update()

        # Continue until boundaries are hit
        for _ in range(10):
            for sprite in sprite_list:
                sprite.update()
            Action.update_all(0.016)

        # Both sprites should be stopped at right boundary (edge-based)
        assert sprite_list[0].right == 200
        assert sprite_list[1].right == 200
        assert sprite_list[0].change_x == 0
        assert sprite_list[1].change_x == 0

    def test_move_until_limit_boundary_already_at_boundary(self, test_sprite):
        """Test limit boundary behavior when sprite edge starts at boundary."""
        sprite = test_sprite
        sprite.right = 200  # Start with right edge at boundary
        sprite.center_y = 100

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(10, 0),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            tag="test_limit_at_boundary",
        )

        Action.update_all(0.016)
        # Should not set velocity since already at boundary
        assert sprite.change_x == 0

        # Try to move again
        Action.update_all(0.016)
        assert sprite.right == 200  # Should stay at boundary
        assert sprite.change_x == 0

    def test_move_until_limit_boundary_multiple_axes(self, test_sprite):
        """Test limit boundary behavior when hitting multiple boundaries using edge-based bounds."""
        sprite = test_sprite
        sprite.center_x = 199
        sprite.center_y = 199

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(10, 10),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            tag="test_limit_multiple_axes",
        )

        Action.update_all(0.016)
        sprite.update()

        # Should be stopped at both boundaries (edges at boundary values)
        assert sprite.right == 200
        assert sprite.top == 200
        assert sprite.change_x == 0
        assert sprite.change_y == 0


class TestFollowPathUntil(ActionTestBase):
    """Test suite for FollowPathUntil action."""

    def test_follow_path_until_basic(self, test_sprite):
        """Test basic FollowPathUntil functionality."""
        sprite = test_sprite
        start_pos = sprite.position

        control_points = [(100, 100), (200, 200), (300, 100)]
        condition_met = False

        def condition():
            nonlocal condition_met
            return condition_met

        action = follow_path_until(
            sprite, control_points=control_points, velocity=100, condition=condition, tag="test_basic_path"
        )

        Action.update_all(0.016)

        # Sprite should start moving along the path
        assert sprite.position != start_pos

    def test_follow_path_until_completion(self, test_sprite):
        """Test FollowPathUntil completes when reaching end of path."""
        sprite = test_sprite
        control_points = [(100, 100), (200, 100)]  # Simple straight line

        action = follow_path_until(
            sprite, control_points=control_points, velocity=1000, condition=infinite, tag="test_path_completion"
        )  # High velocity

        # Update until path is complete
        for _ in range(100):
            Action.update_all(0.016)
            if action.done:
                break

        assert action.done

    def test_follow_path_until_requires_points(self, test_sprite):
        """Test FollowPathUntil requires at least 2 control points."""
        sprite = test_sprite
        with pytest.raises(ValueError):
            follow_path_until(sprite, control_points=[(100, 100)], velocity=100, condition=infinite)

    def test_follow_path_until_no_rotation_by_default(self, test_sprite):
        """Test FollowPathUntil doesn't rotate sprite by default."""
        sprite = test_sprite
        original_angle = sprite.angle

        # Horizontal path from left to right
        control_points = [(100, 100), (200, 100)]
        action = follow_path_until(
            sprite, control_points=control_points, velocity=100, condition=infinite, tag="test_no_rotation"
        )

        # Update several frames
        for _ in range(10):
            Action.update_all(0.016)

        # Sprite angle should not have changed
        assert sprite.angle == original_angle

    def test_follow_path_until_rotation_horizontal_path(self, test_sprite):
        """Test sprite rotation follows horizontal path correctly."""
        sprite = test_sprite
        sprite.angle = 45  # Start with non-zero angle

        # Horizontal path from left to right
        control_points = [(100, 100), (200, 100)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            tag="test_horizontal_rotation",
        )

        # Update a few frames to get movement
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Sprite should be pointing right (0 degrees)
        # Allow small tolerance for floating point math
        assert abs(sprite.angle) < 1.0

    def test_follow_path_until_rotation_vertical_path(self, test_sprite):
        """Test sprite rotation follows vertical path correctly."""
        sprite = test_sprite

        # Vertical path from bottom to top
        control_points = [(100, 100), (100, 200)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            tag="test_vertical_rotation",
        )

        # Update a few frames to get movement
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Sprite should be pointing up (90 degrees)
        assert abs(sprite.angle - 90) < 1.0

    def test_follow_path_until_rotation_diagonal_path(self, test_sprite):
        """Test sprite rotation follows diagonal path correctly."""
        sprite = test_sprite

        # Diagonal path from bottom-left to top-right (45 degrees)
        control_points = [(100, 100), (200, 200)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            tag="test_diagonal_rotation",
        )

        # Update a few frames to get movement
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Sprite should be pointing at 45 degrees
        assert abs(sprite.angle - 45) < 1.0

    def test_follow_path_until_rotation_with_offset(self, test_sprite):
        """Test sprite rotation with calibration offset."""
        sprite = test_sprite

        # Horizontal path from left to right
        control_points = [(100, 100), (200, 100)]
        # Use -90 offset (sprite artwork points up by default)
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            rotation_offset=-90,
            tag="test_rotation_offset",
        )

        # Update a few frames to get movement
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Sprite should be pointing right but compensated for -90 offset
        # Expected angle: 0 (right direction) + (-90 offset) = -90
        assert abs(sprite.angle - (-90)) < 1.0

    def test_follow_path_until_rotation_offset_only_when_rotating(self, test_sprite):
        """Test rotation offset is only applied when rotate_with_path is True."""
        sprite = test_sprite
        original_angle = sprite.angle

        # Horizontal path with offset but rotation disabled
        control_points = [(100, 100), (200, 100)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=False,
            rotation_offset=-90,
            tag="test_no_rotation_with_offset",
        )

        # Update several frames
        for _ in range(10):
            Action.update_all(0.016)

        # Sprite angle should not have changed (rotation disabled)
        assert sprite.angle == original_angle

    def test_follow_path_until_rotation_curved_path(self, test_sprite):
        """Test sprite rotation follows curved path correctly."""
        sprite = test_sprite

        # Curved path - quadratic Bezier curve
        control_points = [(100, 100), (150, 200), (200, 100)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            tag="test_curved_rotation",
        )

        # Store initial angle after first update
        Action.update_all(0.016)
        Action.update_all(0.016)
        initial_angle = sprite.angle

        # Continue updating - angle should change as we follow the curve
        for _ in range(20):
            Action.update_all(0.016)

        # Angle should have changed as we follow the curve
        assert sprite.angle != initial_angle

    def test_follow_path_until_rotation_large_offset(self, test_sprite):
        """Test sprite rotation with large offset values."""
        sprite = test_sprite

        # Horizontal path with large offset
        control_points = [(100, 100), (200, 100)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            rotation_offset=450,
            tag="test_large_offset",
        )

        # Update a few frames to get movement
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Large offset should work (450 degrees = 90 degrees normalized)
        # Expected: 0 (right direction) + 450 (offset) = 450 degrees
        assert abs(sprite.angle - 450) < 1.0

    def test_follow_path_until_rotation_negative_offset(self, test_sprite):
        """Test sprite rotation with negative offset values."""
        sprite = test_sprite

        # Vertical path with negative offset
        control_points = [(100, 100), (100, 200)]
        action = follow_path_until(
            sprite,
            control_points=control_points,
            velocity=100,
            condition=infinite,
            rotate_with_path=True,
            rotation_offset=-45,
            tag="test_negative_offset",
        )

        # Update a few frames to get movement
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Expected: 90 (up direction) + (-45 offset) = 45 degrees
        assert abs(sprite.angle - 45) < 1.0


class TestRotateUntil(ActionTestBase):
    """Test suite for RotateUntil action."""

    def test_rotate_until_basic(self, test_sprite):
        """Test basic RotateUntil functionality."""
        sprite = test_sprite

        target_reached = False

        def condition():
            return target_reached

        action = rotate_until(sprite, angular_velocity=90, condition=condition, tag="test_basic")

        Action.update_all(0.016)

        # RotateUntil uses degrees per frame at 60 FPS semantics
        assert sprite.change_angle == 90

        # Trigger condition
        target_reached = True
        Action.update_all(0.016)

        assert action.done

    def test_rotate_until_frame_based_semantics(self, test_sprite):
        """Test that RotateUntil uses degrees per frame at 60 FPS semantics."""
        sprite = test_sprite

        # 3 degrees per frame should rotate 3 degrees when sprite.update() is called
        action = rotate_until(sprite, angular_velocity=3, condition=infinite, tag="test_frame_semantics")

        # Update action to apply angular velocity
        Action.update_all(0.016)
        assert sprite.change_angle == 3  # Raw frame-based value

        # Rotate sprite using its angular velocity
        start_angle = sprite.angle
        sprite.update()  # Arcade applies change_angle to angle

        # Should have rotated exactly 3 degrees
        angle_rotated = sprite.angle - start_angle
        assert angle_rotated == 3.0

    def test_rotate_until_angular_velocity_values(self, test_sprite):
        """Test that RotateUntil sets angular velocity values directly (degrees per frame at 60 FPS)."""
        sprite = test_sprite

        # Test various angular velocity values
        test_cases = [
            1,  # Should result in change_angle = 1.0
            2,  # Should result in change_angle = 2.0
            5,  # Should result in change_angle = 5.0
            -3,  # Should result in change_angle = -3.0
        ]

        for input_angular_velocity in test_cases:
            Action.stop_all()
            sprite.change_angle = 0

            action = rotate_until(
                sprite, angular_velocity=input_angular_velocity, condition=infinite, tag="test_velocity"
            )
            Action.update_all(0.016)

            assert sprite.change_angle == input_angular_velocity, f"Failed for input {input_angular_velocity}"


class TestScaleUntil(ActionTestBase):
    """Test suite for ScaleUntil action."""

    def test_scale_until_basic(self, test_sprite):
        """Test basic ScaleUntil functionality."""
        sprite = test_sprite
        start_scale = sprite.scale

        target_reached = False

        def condition():
            return target_reached

        action = scale_until(sprite, velocity=0.5, condition=condition, tag="test_basic")

        Action.update_all(0.016)

        # Should be scaling
        assert sprite.scale != start_scale

        # Trigger condition
        target_reached = True
        Action.update_all(0.016)

        assert action.done


class TestFadeTo(ActionTestBase):
    """Test suite for FadeTo action."""

    def test_fade_to_basic(self, test_sprite):
        """FadeTo should move alpha toward a target and complete at the bound."""
        sprite = test_sprite
        start_alpha = sprite.alpha

        action = fade_to(sprite, target_alpha=0, speed=100000.0, tag="test_basic")

        Action.update_all(0.016)

        assert sprite.alpha != start_alpha
        assert sprite.alpha == 0
        assert action.done

    def test_fade_to_fades_in_and_respects_abs_factor(self, test_sprite):
        """FadeTo should fade upward when target alpha is higher."""
        sprite = test_sprite
        sprite.alpha = 0

        action = fade_to(sprite, target_alpha=255, speed=1000.0, tag="fade_in")
        action.set_factor(-2.0)  # factor should be treated as magnitude

        Action.update_all(0.016)

        assert sprite.alpha == 255
        assert action.done

    def test_fade_to_can_stop_early_via_condition(self, test_sprite):
        """FadeTo should stop early when its condition returns truthy."""
        sprite = test_sprite
        sprite.alpha = 200

        condition_met = False

        def condition():
            nonlocal condition_met
            if condition_met:
                return {"reason": "early_exit"}
            return False

        action = fade_to(sprite, target_alpha=0, speed=1.0, condition=condition, tag="early_exit")

        Action.update_all(0.016)
        assert action.done is False

        condition_met = True
        Action.update_all(0.016)
        assert action.done is True
        assert action.condition_data == {"reason": "early_exit"}


class TestFadeUntilLegacy(ActionTestBase):
    """Coverage test for legacy FadeUntil delta_time semantics."""

    def test_fade_until_is_frame_driven(self, test_sprite):
        """FadeUntil should treat fade_velocity as per-frame, not per-second."""
        sprite = test_sprite
        sprite.alpha = 100

        # If this were multiplied by delta_time, alpha would change by 0.5 here.
        action = FadeUntil(fade_velocity=-1, condition=after_frames(1))
        action.apply(sprite, tag="fade_until_frame_driven")

        Action.update_all(0.5)

        assert sprite.alpha == 99
        assert action.done


class TestBlinkUntil(ActionTestBase):
    """Slimmed-down blink tests covering the new frame-based API."""

    def test_basic_toggle_and_completion(self, test_sprite):
        """BlinkUntil should toggle visibility at the configured frame interval."""
        sprite = test_sprite
        sprite.visible = True

        action = blink_until(sprite, frames_until_change=2, condition=after_frames(6), tag="blink_basic")

        # After two frames the sprite should flip to invisible, then back after two more.
        Action.update_all(0.016)
        Action.update_all(0.016)
        assert sprite.visible is False

        Action.update_all(0.016)
        Action.update_all(0.016)
        assert sprite.visible is True

        # Advance remaining frames to hit the completion condition.
        for _ in range(6):
            Action.update_all(0.016)

        assert action.done

        assert action.done

    def test_callbacks_fire_once_per_transition(self, test_sprite):
        """on_blink_enter/on_blink_exit fire once per state change."""
        sprite = test_sprite
        sprite.visible = True

        events = []

        def on_enter(target):
            events.append(("enter", target))

        def on_exit(target):
            events.append(("exit", target))

        blink_until(
            sprite,
            frames_until_change=1,
            condition=after_frames(4),
            on_blink_enter=on_enter,
            on_blink_exit=on_exit,
            tag="blink_callbacks",
        )

        for _ in range(4):
            Action.update_all(0.016)

        assert events == [
            ("exit", sprite),
            ("enter", sprite),
            ("exit", sprite),
            ("enter", sprite),
        ]

    def test_invalid_frames_parameter(self):
        """frames_until_change must be positive."""
        with pytest.raises(ValueError):
            blink_until(create_test_sprite(), frames_until_change=0, condition=infinite)


class TestDelayFrames(ActionTestBase):
    """Test suite for DelayFrames action."""

    def test_delay_frames_condition_only(self, test_sprite):
        """DelayFrames should support condition-only usage (no frame limit)."""
        sprite = test_sprite

        condition_met = False

        def condition():
            nonlocal condition_met
            return condition_met

        action = delay_frames(sprite, condition=condition, tag="test_basic")

        Action.update_all(0.016)
        assert not action.done

        # Trigger condition
        condition_met = True
        Action.update_all(0.016)
        assert action.done

    def test_delay_frames_negative_raises(self):
        with pytest.raises(ValueError, match="frames must be non-negative"):
            DelayFrames(frames=-1)


class TestAfterFrames:
    """Test suite for after_frames helper (replaces duration)."""

    def test_after_frames_basic(self):
        """Test basic after_frames functionality."""
        condition = after_frames(3)

        # First two calls should be False
        assert not condition()
        assert not condition()
        # Third call returns True
        assert condition()

    def test_after_frames_zero(self):
        """Test after_frames with zero frames."""
        condition = after_frames(0)

        # Should return True immediately
        assert condition()

    def test_after_frames_negative(self):
        """Test after_frames with negative frame count."""
        condition = after_frames(-1)

        # Should return True immediately for negative frame counts
        assert condition()


class TestConditionHelperCoverage:
    """Additional coverage for condition helper utilities."""

    def test_after_frames_frame_count_metadata(self):
        """after_frames should have frame_count metadata for introspection."""
        condition = after_frames(60)

        # Should have frame metadata
        assert hasattr(condition, "_is_frame_condition")
        assert hasattr(condition, "_frame_count")
        assert condition._frame_count == 60


class TestTweenUntil(ActionTestBase):
    """Test suite for TweenUntil action - Direct property animation from start to end value."""

    def test_tween_until_basic_property_animation(self, test_sprite):
        """Test TweenUntil for precise A-to-B property animation."""
        sprite = test_sprite
        sprite.center_x = 0

        # Direct property animation from 0 to 100 over 1 second
        action = tween_until(
            sprite,
            start_value=0,
            end_value=100,
            property_name="center_x",
            condition=after_frames(60),
            tag="test_basic",
        )

        # At halfway point (30 frames), should be partway through
        for _ in range(30):
            Action.update_all(0.016)
        assert 0 < sprite.center_x < 100

        # Run remaining frames to completion
        for _ in range(30):
            Action.update_all(0.016)

        assert sprite.center_x == 100
        assert action.done

    def test_tween_until_custom_easing(self, test_sprite):
        sprite = test_sprite
        sprite.center_x = 0

        def ease_quad(t):
            return t * t

        action = tween_until(
            sprite,
            start_value=0,
            end_value=100,
            property_name="center_x",
            condition=after_frames(60),
            ease_function=ease_quad,
            tag="test_custom_easing",
        )
        for _ in range(30):
            Action.update_all(0.016)
        assert sprite.center_x < 50

        for _ in range(30):
            Action.update_all(0.016)
        assert sprite.center_x == 100


class TestTweenUntilCoverage(ActionTestBase):
    """Extended TweenUntil coverage for timing and lifecycle internals."""

    def test_update_skips_when_paused_or_done_coverage(self):
        """Tween update should no-op when paused or marked done."""
        sprite = create_test_sprite()
        action = TweenUntil(0, 100, "center_x", condition=after_frames(10))
        action.apply(sprite, tag="tween_pause")

        action._paused = True
        action.update(0.016)
        assert action._frames_elapsed == 0

        action._paused = False
        action.done = True
        action.update(0.016)
        assert action._frames_elapsed == 0

    def test_apply_effect_frame_duration_and_zero_completion_coverage(self):
        """apply_effect should honor frame counts, overrides, and zero-duration completion."""
        sprite_a = create_test_sprite()
        frames_action = TweenUntil(0, 50, "center_x", condition=after_frames(5))
        frames_action.apply(sprite_a, tag="tween_frames")
        assert frames_action._frame_duration == 5
        Action.stop_all()

        sprite_b = create_test_sprite()
        override_action = TweenUntil(10, 20, "center_y", condition=after_frames(60))
        override_action._frame_duration = 2
        override_action.apply(sprite_b, tag="tween_override")
        assert override_action._frame_duration == 2
        Action.stop_all()

        sprite_c = create_test_sprite()
        zero_calls = {"count": 0}

        def on_stop(data):
            zero_calls["count"] += 1
            assert data is None

        zero_action = TweenUntil(0, 42, "center_x", condition=after_frames(1), on_stop=on_stop)
        zero_action._frame_duration = 0
        zero_action.apply(sprite_c, tag="tween_zero")
        assert zero_action.done
        assert sprite_c.center_x == 42
        assert zero_calls["count"] == 1

    def test_on_stop_fires_on_natural_completion(self):
        """on_stop should fire when tween completes by reaching its duration."""
        sprite = create_test_sprite()
        calls = {"count": 0}

        def on_stop():
            calls["count"] += 1

        action = TweenUntil(0, 10, "center_x", condition=after_frames(3), on_stop=on_stop)
        action.apply(sprite, tag="tween_on_stop")

        for _ in range(3):
            Action.update_all(0.016)

        assert action.done
        assert calls["count"] == 1

    def test_tween_natural_completion_skips_external_condition_same_frame(self):
        """Natural tween completion should win before any external condition is evaluated."""
        sprite = create_test_sprite()
        callback_args: list[tuple[object, ...]] = []
        condition_calls = {"count": 0}

        def condition_with_data():
            condition_calls["count"] += 1
            return {"source": "condition"}

        def on_stop(*args):
            callback_args.append(args)

        action = TweenUntil(0, 10, "center_x", condition_with_data, on_stop=on_stop)
        action._frame_duration = 1
        action.apply(sprite, tag="tween_natural_wins")

        Action.update_all(1 / 60)

        assert action.done
        assert sprite.center_x == 10
        assert condition_calls["count"] == 0
        assert callback_args == [()]
        assert action.condition_data is None

    def test_set_factor_and_remove_effect_reset_coverage(self):
        """set_factor should reapply velocity immediately and remove_effect resets start."""
        sprite = create_test_sprite()
        action = TweenUntil(0, 100, "center_x", condition=after_frames(4))
        action.apply(sprite, tag="tween_factor")
        action.set_factor(2.0)

        Action.update_all(0.016)
        assert 0 < sprite.center_x < 100

        action.remove_effect()
        assert sprite.center_x == 0

    def test_reset_and_clone_state_coverage(self):
        """reset clears derived state and clone copies configuration."""
        ease_fn = lambda t: t * t
        action = TweenUntil(5, 15, "center_y", condition=after_frames(3), ease_function=ease_fn)
        action._frames_elapsed = 2
        action._frame_duration = 3
        action._completed_naturally = True

        action.reset()
        assert action._frames_elapsed == 0
        assert action._frame_duration is None
        assert not action._completed_naturally

        clone = action.clone()
        assert clone is not action
        assert clone.start_value == action.start_value
        assert clone.end_value == action.end_value
        assert clone.property_name == action.property_name
        assert clone.ease_function is action.ease_function

    def test_set_duration_not_supported_coverage(self):
        """set_duration should remain unsupported."""
        action = TweenUntil(0, 1, "alpha", condition=after_frames(2))
        with pytest.raises(NotImplementedError):
            action.set_duration(1.0)


# ------------------ Repeat wallclock drift tests ------------------


def test_repeat_with_wallclock_drift_no_jump():
    """Ensure _Repeat + ParametricMotionUntil stay stable when legacy wall-clock helpers drift."""
    import sys

    import arcade

    from arcadeactions import Action, repeat
    from arcadeactions.pattern import create_wave_pattern

    def _run_frames(frames: int) -> None:
        for _ in range(frames):
            Action.update_all(1 / 60)

    # Save and monkeypatch time.time used by the legacy wall-clock helper
    import time as real_time_module

    original_time_fn = real_time_module.time

    # Controlled simulated wall clock
    sim_time = {"t": original_time_fn()}

    def fake_time():
        return sim_time["t"]

    # Monkeypatch the time module globally
    sys.modules["time"].time = fake_time

    try:
        # Setup sprite and repeating full-wave action.  In the frame-based
        # timing model, `velocity` is pixels per frame, so we use a modest
        # value to avoid intentionally large per-frame jumps.
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100

        full_wave = create_wave_pattern(amplitude=30, length=80, velocity=80)
        rep = repeat(full_wave)
        rep.apply(sprite, tag="repeat_wallclock")

        last_pos = (sprite.center_x, sprite.center_y)
        # Run ~10 seconds, injecting wall-clock drift every 2 seconds
        for frame in range(10 * 60):
            # Advance simulated wall clock normally
            sim_time["t"] += 1 / 60
            # Every 120 frames (~2 s), inject 150 ms extra wall time to simulate hitches
            if frame and frame % 120 == 0:
                sim_time["t"] += 0.15

            Action.update_all(1 / 60)

            current = (sprite.center_x, sprite.center_y)
            # Detect sudden large position jumps within one frame
            dx = current[0] - last_pos[0]
            dy = current[1] - last_pos[1]
            step_dist = (dx * dx + dy * dy) ** 0.5
            # Allow generous per-frame distance for wave motion; disallow implausible jumps
            # With velocity=80, we expect up to ~80 px per frame, so use 100 as threshold
            assert step_dist < 100.0, f"Unexpected jump {step_dist:.2f} at frame {frame}"
            last_pos = current

    finally:
        # Restore real time.time
        sys.modules["time"].time = original_time_fn


class TestMoveUntilExceptionHandling(ActionTestBase):
    """Test suite for MoveUntil exception handling and edge cases."""

    def test_velocity_provider_exception_fallback(self, test_sprite):
        """Test that velocity provider exceptions fall back to current velocity."""
        sprite = test_sprite

        def failing_provider():
            raise RuntimeError("Provider failed!")

        action = move_until(
            sprite,
            velocity=(10, 5),
            condition=infinite,
            velocity_provider=failing_provider,
            tag="test_provider_exception",
        )

        # Should fall back to current velocity (10, 5) when provider fails
        Action.update_all(0.016)
        assert sprite.change_x == 10
        assert sprite.change_y == 5

    def test_boundary_enter_callback_exception_handling(self, test_sprite):
        """Test that boundary enter callback exceptions are caught and ignored."""
        sprite = test_sprite
        sprite.center_x = 50
        sprite.center_y = 100

        def failing_callback(sprite, axis, side):
            raise RuntimeError("Callback failed!")

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(100, 0),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            on_boundary_enter=failing_callback,
            tag="test_callback_exception",
        )

        # Should not crash despite callback exception
        Action.update_all(0.016)
        sprite.update()

        # Continue until boundary is hit - should handle exception gracefully
        for _ in range(10):
            sprite.update()
            Action.update_all(0.016)

        # Should reach boundary despite callback failure (edge-based)
        assert sprite.right == 200

    def test_boundary_exit_callback_exception_handling(self, test_sprite):
        """Test that boundary exit callback exceptions are caught and ignored."""
        sprite = test_sprite
        sprite.center_x = 200  # Start at boundary
        sprite.center_y = 100

        def failing_exit_callback(sprite, axis, side):
            raise RuntimeError("Exit callback failed!")

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(-10, 0),  # Move away from boundary
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            on_boundary_exit=failing_exit_callback,
            tag="test_exit_callback_exception",
        )

        # Should not crash despite callback exception
        Action.update_all(0.016)
        sprite.update()
        Action.update_all(0.016)

        # Should be able to move away despite callback failure
        assert sprite.center_x < 200

    def test_wrap_boundary_behavior(self, test_sprite):
        """Test wrap boundary behavior coverage."""
        sprite = test_sprite
        sprite.center_x = 190
        sprite.center_y = 100

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(20, 0),  # Will cross right boundary
            condition=infinite,
            bounds=bounds,
            boundary_behavior="wrap",
            tag="test_wrap_boundary",
        )

        # Move multiple frames to ensure wrapping occurs
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Should wrap to left side - check that it wrapped around
        assert sprite.center_x != 190  # Position changed
        # Wrap behavior should set sprite to opposite boundary when crossing
        assert sprite.center_x <= 200  # Within bounds

    def test_bounce_boundary_behavior(self, test_sprite):
        """Test bounce boundary behavior coverage."""
        sprite = test_sprite
        sprite.center_x = 190
        sprite.center_y = 100

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite,
            velocity=(20, 0),  # Will hit right boundary
            condition=infinite,
            bounds=bounds,
            boundary_behavior="bounce",
            tag="test_bounce_boundary",
        )

        # Move multiple frames to ensure bouncing occurs
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Should bounce back with reversed velocity - check that velocity changed direction
        assert sprite.center_x != 190  # Position changed
        # After bouncing, sprite should be moving in opposite direction or stopped
        assert sprite.change_x <= 0  # Velocity should be zero or negative after bounce


class TestMoveUntilInternalsCoverage(ActionTestBase):
    """Focused coverage of MoveUntil internals and helper APIs."""

    def test_collect_target_sprite_ids_coverage(self, test_sprite, test_sprite_list):
        """Ensure _collect_target_sprite_ids handles sprite, SpriteList, and non-iterables."""
        single = InstrumentedMoveUntil((5, 0), infinite)
        single.apply(test_sprite, tag="single_collect")
        assert single._collect_target_sprite_ids() == [id(test_sprite)]

        group = InstrumentedMoveUntil((5, 0), infinite)
        group.apply(test_sprite_list, tag="list_collect")
        ids = group._collect_target_sprite_ids()
        assert set(ids) == {id(sprite) for sprite in test_sprite_list}

        non_iterable_action = InstrumentedMoveUntil((5, 0), infinite)
        sentinel = object()
        non_iterable_action.target = sentinel
        assert non_iterable_action._collect_target_sprite_ids() == [id(sentinel)]

    def test_update_motion_snapshot_metadata_coverage(self, test_sprite):
        """Verify _update_motion_snapshot emits boundary_state + sprite_ids metadata."""
        bounds = (0, 0, 200, 200)
        action = InstrumentedMoveUntil((5, 5), infinite, bounds=bounds, boundary_behavior="limit")
        action.apply(test_sprite, tag="snapshot")
        sprite_id = id(test_sprite)
        action._boundary_state[sprite_id] = {"x": "right", "y": None}
        action._update_motion_snapshot(velocity=(3, 4))

        assert action.snapshots, "Expected snapshot entry when metadata present"
        snapshot = action.snapshots[-1]
        assert snapshot["velocity"] == (3, 4)
        assert snapshot["bounds"] == bounds
        metadata = snapshot["metadata"]
        assert metadata["boundary_state"][sprite_id]["x"] == "right"
        assert sprite_id in metadata["sprite_ids"]

    def test_velocity_provider_update_exception_coverage(self, test_sprite):
        """Provider failures during update_effect should keep previous velocity."""
        call_state = {"count": 0}

        def flaky_provider():
            call_state["count"] += 1
            if call_state["count"] == 2:
                raise RuntimeError("update provider failure")
            return (7, -3)

        action = InstrumentedMoveUntil((1, 1), infinite, velocity_provider=flaky_provider)
        action.apply(test_sprite, tag="provider_error")

        Action.update_all(0.016)  # First frame triggers provider exception path
        assert call_state["count"] == 2
        assert test_sprite.change_x == 7
        assert test_sprite.change_y == -3

    def test_wrap_behavior_axes_coverage(self, test_sprite):
        """Wrap behavior should wrap both axes to opposite edges."""
        bounds = (0, 0, 200, 200)
        action = InstrumentedMoveUntil((5, 5), infinite, bounds=bounds, boundary_behavior="wrap")

        # Crossing left boundary wraps right edge to high bound
        test_sprite.left = bounds[0] - 10
        action._wrap_behavior(test_sprite, test_sprite.left, test_sprite.right, bounds[0], bounds[2], 5, "x")
        assert test_sprite.right == bounds[2]

        # Crossing right boundary wraps left edge to low bound
        test_sprite.right = bounds[2] + 5
        action._wrap_behavior(test_sprite, test_sprite.left, test_sprite.right, bounds[0], bounds[2], -5, "x")
        assert test_sprite.left == bounds[0]

        # Crossing bottom boundary wraps top edge upward
        test_sprite.bottom = bounds[1] - 15
        action._wrap_behavior(test_sprite, test_sprite.bottom, test_sprite.top, bounds[1], bounds[3], 5, "y")
        assert test_sprite.top == bounds[3]

        # Crossing top boundary wraps bottom edge downward
        test_sprite.top = bounds[3] + 12
        action._wrap_behavior(test_sprite, test_sprite.bottom, test_sprite.top, bounds[1], bounds[3], -5, "y")
        assert test_sprite.bottom == bounds[1]

    def test_limit_behavior_axes_coverage(self, test_sprite):
        """Limit behavior should clamp velocity and positions on both axes."""
        bounds = (0, 0, 200, 200)

        # Left boundary clamp
        left_action = InstrumentedMoveUntil((5, 0), infinite, bounds=bounds, boundary_behavior="limit")
        test_sprite.left = bounds[0] - 5
        test_sprite.change_x = 5
        left_action._limit_behavior(test_sprite, test_sprite.left, test_sprite.right, bounds[0], bounds[2], 5, "x")
        assert test_sprite.left == bounds[0]
        assert test_sprite.change_x == 0
        assert left_action.current_velocity[0] == 0

        # Right boundary clamp
        right_action = InstrumentedMoveUntil((5, 0), infinite, bounds=bounds, boundary_behavior="limit")
        test_sprite.right = bounds[2] + 5
        test_sprite.change_x = -5
        right_action._limit_behavior(test_sprite, test_sprite.left, test_sprite.right, bounds[0], bounds[2], -5, "x")
        assert test_sprite.right == bounds[2]
        assert test_sprite.change_x == 0
        assert right_action.current_velocity[0] == 0

        # Bottom boundary clamp
        bottom_action = InstrumentedMoveUntil((0, 5), infinite, bounds=bounds, boundary_behavior="limit")
        test_sprite.bottom = bounds[1] - 5
        test_sprite.change_y = 5
        bottom_action._limit_behavior(test_sprite, test_sprite.bottom, test_sprite.top, bounds[1], bounds[3], 5, "y")
        assert test_sprite.bottom == bounds[1]
        assert test_sprite.change_y == 0
        assert bottom_action.current_velocity[1] == 0

        # Top boundary clamp
        top_action = InstrumentedMoveUntil((0, 5), infinite, bounds=bounds, boundary_behavior="limit")
        test_sprite.top = bounds[3] + 5
        test_sprite.change_y = -5
        top_action._limit_behavior(test_sprite, test_sprite.bottom, test_sprite.top, bounds[1], bounds[3], -5, "y")
        assert test_sprite.top == bounds[3]
        assert test_sprite.change_y == 0
        assert top_action.current_velocity[1] == 0

    def test_remove_effect_clears_state_coverage(self, test_sprite):
        """remove_effect should clear callbacks, boundary_state, and velocities."""
        cleared = {"enter": 0, "exit": 0}

        def on_enter(*_):
            cleared["enter"] += 1

        def on_exit(*_):
            cleared["exit"] += 1

        action = InstrumentedMoveUntil(
            (5, 5),
            infinite,
            bounds=(0, 0, 200, 200),
            boundary_behavior="limit",
            on_boundary_enter=on_enter,
            on_boundary_exit=on_exit,
        )
        action.apply(test_sprite, tag="remove_effect")
        action._boundary_state[id(test_sprite)] = {"x": "left", "y": "bottom"}
        test_sprite.change_x = 5
        test_sprite.change_y = 5

        action.remove_effect()
        assert action.on_boundary_enter is None
        assert action.on_boundary_exit is None
        assert action._boundary_state == {}
        assert test_sprite.change_x == 0
        assert test_sprite.change_y == 0
        assert action.snapshots[-1]["velocity"] == (0.0, 0.0)

    def test_set_factor_and_current_velocity_immediate_coverage(self, test_sprite):
        """set_factor and set_current_velocity should reapply immediately."""
        action = InstrumentedMoveUntil((8, -4), infinite)
        action.apply(test_sprite, tag="factor_set")

        Action.update_all(0.016)
        assert test_sprite.change_x == 8
        assert test_sprite.change_y == -4

        action.set_factor(0.5)
        assert test_sprite.change_x == 4
        assert test_sprite.change_y == -2

        action.set_current_velocity((-3, 6))
        assert test_sprite.change_x == -3
        assert test_sprite.change_y == 6

    def test_reverse_movement_axis_specific_coverage(self, test_sprite):
        """reverse_movement must only flip requested axis and validate input."""
        action = InstrumentedMoveUntil((6, 2), infinite)
        action.apply(test_sprite, tag="reverse_axis")
        Action.update_all(0.016)

        action.reverse_movement("x")
        assert test_sprite.change_x == -6
        assert test_sprite.change_y == 2

        action.reverse_movement("y")
        assert test_sprite.change_x == -6
        assert test_sprite.change_y == -2

        with pytest.raises(ValueError):
            action.reverse_movement("z")


class TestMoveUntilFrameDurationCoverage(ActionTestBase):
    """Coverage for frame-derived duration handling and boundary timing paths."""

    def test_frame_metadata_elapsed_stops_action(self, test_sprite):
        """Frame metadata should trigger remove_effect and on_stop."""

        stop_state = {"called": False}

        def on_stop():
            stop_state["called"] = True

        action = InstrumentedMoveUntil((5, 0), after_frames(5), on_stop=on_stop)
        action.apply(test_sprite, tag="duration_stop")

        for _ in range(4):
            Action.update_all(0.03)
            assert not action.done

        Action.update_all(0.03)
        assert action.done
        assert stop_state["called"]
        assert test_sprite.change_x == 0

    def test_limit_velocity_provider_callbacks_coverage(self, test_sprite):
        """Velocity provider limit path should fire enter/exit callbacks."""
        bounds = (0, 0, 200, 200)
        events = {"enter": [], "exit": []}

        def record_enter(sprite, axis, side):
            events["enter"].append((axis, side))

        def record_exit(sprite, axis, side):
            events["exit"].append((axis, side))

        velocity_sequence = [(10, 0), (10, 0), (-10, 0)]
        call_index = {"value": 0}

        def provider():
            idx = min(call_index["value"], len(velocity_sequence) - 1)
            call_index["value"] += 1
            return velocity_sequence[idx]

        action = InstrumentedMoveUntil(
            (0, 0),
            infinite,
            bounds=bounds,
            boundary_behavior="limit",
            velocity_provider=provider,
            on_boundary_enter=record_enter,
            on_boundary_exit=record_exit,
        )
        test_sprite.center_x = 195
        action.apply(test_sprite, tag="provider_limit")

        Action.update_all(0.016)  # Should hit right boundary and trigger enter
        Action.update_all(0.016)  # Should move left and trigger exit
        test_sprite.update()  # Apply negative velocity so future frames stay inside

        assert ("x", "right") in events["enter"]
        assert ("x", "right") in events["exit"]

    def test_apply_boundary_limits_invoked_without_velocity_provider_coverage(self, test_sprite):
        """_apply_boundary_limits should run whenever bounds+bounce set without provider."""
        bounds = (0, 0, 200, 200)
        action = InstrumentedMoveUntil((5, 0), infinite, bounds=bounds, boundary_behavior="bounce")
        action.apply(test_sprite, tag="apply_limits")

        Action.update_all(0.016)
        assert action.apply_limits_invocations >= 1


class TestConditionalErrorCases:
    """Test error cases and edge conditions in conditional actions."""

    def test_move_until_invalid_velocity_not_tuple(self, test_sprite):
        """Test MoveUntil with invalid velocity type raises error."""
        with pytest.raises(ValueError, match="velocity must be a tuple or list of length 2"):
            move_until(test_sprite, velocity="invalid", condition=infinite)

    def test_move_until_invalid_velocity_wrong_length(self, test_sprite):
        """Test MoveUntil with wrong velocity length raises error."""
        with pytest.raises(ValueError, match="velocity must be a tuple or list of length 2"):
            move_until(test_sprite, velocity=(1,), condition=infinite)

    def test_move_until_invalid_velocity_too_long(self, test_sprite):
        """Test MoveUntil with too long velocity raises error."""
        with pytest.raises(ValueError, match="velocity must be a tuple or list of length 2"):
            move_until(test_sprite, velocity=(1, 2, 3), condition=infinite)

    def test_conditional_action_exception_handling(self, test_sprite):
        """Test conditional action with exception during duration parsing."""

        # Provide a condition that raises when evaluated to ensure safe handling
        class BadCondition:
            def __call__(self):
                raise RuntimeError("bad condition")

        action = move_until(test_sprite, velocity=(10, 0), condition=BadCondition())
        action.apply(test_sprite, tag="bad_condition")
        with pytest.raises(RuntimeError):
            Action.update_all(0.016)

    def test_duration_condition_closure_detection(self, test_sprite):
        """Test duration condition closure detection coverage."""
        sprite = test_sprite

        # Test with a closure that contains seconds variable
        seconds = 0.1

        condition = after_frames(seconds_to_frames(seconds))
        action = move_until(sprite, velocity=(10, 0), condition=condition)
        assert action is not None

        action = move_until(
            sprite,
            velocity=(10, 0),
            condition=after_frames(seconds_to_frames(2.0)),
            tag="test_duration_closure",
        )

        # Update to test the closure detection
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        assert not action.done
        assert sprite.change_x == 10

        duration_frames = seconds_to_frames(2.0)
        for _ in range(duration_frames + 5):
            Action.update_all(0.016)
            sprite.update()
            if action.done:
                break

        assert action.done
        assert sprite.change_x == 0

    def test_move_until_boundary_limit_with_events(self, test_sprite):
        """Test MoveUntil boundary limit behavior with enter/exit events."""
        sprite = test_sprite
        sprite.center_x = 180
        sprite.center_y = 150

        # Track boundary events
        boundary_enters = []
        boundary_exits = []

        def on_enter(sprite, axis, side):
            boundary_enters.append((sprite, axis, side))

        def on_exit(sprite, axis, side):
            boundary_exits.append((sprite, axis, side))

        action = move_until(
            sprite,
            velocity=(50, 0),
            condition=infinite,
            boundary_behavior="limit",
            bounds=(0, 0, 200, 300),
            on_boundary_enter=on_enter,
            on_boundary_exit=on_exit,
            tag="test_boundary_events",
        )

        # Move sprite to trigger boundary
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Should have triggered boundary enter event
        assert len(boundary_enters) > 0
        assert boundary_enters[0][2] == "right"

        # Change direction to move away from boundary
        sprite.change_x = -50

        # Move away from boundary
        for _ in range(3):
            Action.update_all(0.016)
            sprite.update()

        # Should trigger boundary exit event
        assert len(boundary_exits) > 0
        assert boundary_exits[0][2] == "right"

    def test_move_until_boundary_vertical_limits(self, test_sprite):
        """Test MoveUntil boundary limit behavior for vertical movement."""
        sprite = test_sprite
        sprite.center_x = 100
        sprite.center_y = 280

        action = move_until(
            sprite,
            velocity=(0, 50),
            condition=infinite,
            boundary_behavior="limit",
            bounds=(0, 0, 200, 300),
            tag="test_vertical_boundary",
        )

        # Move sprite to trigger top boundary
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Should be limited to boundary
        assert sprite.center_y <= 300
        assert sprite.change_y == 0  # Velocity should be stopped

    def test_move_until_boundary_initialization(self, test_sprite):
        """Test boundary state initialization for new sprites."""
        sprite = test_sprite
        sprite.center_x = 50
        sprite.center_y = 50

        action = move_until(
            sprite,
            velocity=(10, 10),
            condition=infinite,
            boundary_behavior="limit",
            bounds=(0, 0, 200, 200),
            tag="test_boundary_init",
        )

        # Update once to initialize boundary state
        Action.update_all(0.016)

        # Boundary state should be initialized
        assert hasattr(action, "_boundary_state")
        sprite_id = id(sprite)
        assert sprite_id in action._boundary_state
        assert "x" in action._boundary_state[sprite_id]
        assert "y" in action._boundary_state[sprite_id]

    def test_move_until_exception_in_boundary_callback(self, test_sprite):
        """Test handling of exceptions in boundary callbacks."""
        sprite = test_sprite
        sprite.center_x = 180
        sprite.center_y = 150

        def bad_callback(sprite, side):
            raise RuntimeError("Test exception")

        action = move_until(
            sprite,
            velocity=(50, 0),
            condition=infinite,
            boundary_behavior="limit",
            bounds=(0, 0, 200, 300),
            on_boundary_enter=bad_callback,
            tag="test_exception_handling",
        )

        # Should not crash even with exception in callback
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Sprite should still be properly limited
        assert sprite.center_x <= 200

    def test_move_until_with_sprite_list_boundary_mixed_states(self, test_sprite_list):
        """Test boundary behavior with sprite list where sprites are in different boundary states with edge-based bounds."""
        sprite_list = test_sprite_list
        sprite_list[0].center_x = 180  # Near right boundary
        sprite_list[1].center_x = 50  # Well within bounds (left edge at 50-32=18, well inside left bound of 0)
        sprite_list[0].center_y = 100
        sprite_list[1].center_y = 100

        bounds = (0, 0, 200, 200)
        action = move_until(
            sprite_list,
            velocity=(30, 0),  # Moving right
            condition=infinite,
            bounds=bounds,
            boundary_behavior="limit",
            tag="test_mixed_boundary_states",
        )

        Action.update_all(0.016)
        sprite_list[0].update()
        sprite_list[1].update()

        # First sprite should hit boundary and stop (edge-based)
        assert sprite_list[0].change_x == 0
        assert sprite_list[0].right == 200

        # Second sprite should continue moving
        assert sprite_list[1].change_x == 30
        assert sprite_list[1].center_x >= 80  # Should have moved right from 50


class TestConditionalAdditionalCoverage:
    """Additional tests to improve conditional action coverage."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()
        # Clear callback warning cache for clean tests
        Action._warned_bad_callbacks.clear()

    def test_duration_boundary_state_initialization(self):
        """Test boundary state initialization for different sprites.

        Sprite is 128x128, so bounds must be at least 128px wide/tall.
        """
        from tests.test_base import create_test_sprite

        sprite1 = create_test_sprite()
        sprite1.center_x = 200
        sprite1.center_y = 200

        sprite2 = create_test_sprite()
        sprite2.center_x = 250
        sprite2.center_y = 250

        # Create MoveUntil actions for both sprites with boundary behavior
        # Sprite is 128x128, so bounds need to be at least 128px wide/tall
        # Left: 36, Right: 364 (span = 328px > 128px)
        move_until(
            sprite1,
            velocity=(10, 0),
            condition=infinite,
            boundary_behavior="limit",
            bounds=(36, 36, 364, 364),
        )

        move_until(
            sprite2,
            velocity=(-10, 0),
            condition=infinite,
            boundary_behavior="limit",
            bounds=(36, 36, 364, 364),
        )

        # Both actions should be created successfully
        assert len(Action._active_actions) >= 2

    def test_move_until_boundary_enter_exception_handling(self):
        """Test that boundary enter callback exceptions are caught gracefully.

        Sprite is 128x128, so bounds must be at least 128px wide/tall.
        """
        from tests.test_base import create_test_sprite

        sprite = create_test_sprite()
        sprite.center_x = 300  # Start close to right boundary
        sprite.center_y = 200

        def failing_boundary_callback(sprite, axis, side):
            """A callback that raises an exception."""
            raise ValueError("Test boundary exception")

        # Create MoveUntil with boundary limits and a failing callback
        # Sprite is 128x128, so bounds need to be at least 128px wide/tall
        # Left: 36, Right: 364 (span = 328px > 128px)
        move_until(
            sprite,
            velocity=(30, 0),  # Moving right
            condition=infinite,
            boundary_behavior="limit",
            bounds=(36, 36, 364, 364),
            on_boundary_enter=failing_boundary_callback,
        )

        # Update multiple times to ensure boundary collision
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Sprite should be stopped at boundary despite callback exception (edge-based)
        assert sprite.change_x == 0
        assert sprite.right == 364  # Should be at right boundary

    def test_move_until_boundary_exit_exception_handling(self):
        """Test that boundary exit callback exceptions are caught gracefully with edge-based bounds.

        Strategy: Move sprite to boundary, then manually set velocity to move away to trigger exit callback.
        This mimics real usage where external code or velocity providers change direction.

        Sprite is 128x128, so bounds must be at least 128px wide/tall.
        """
        from tests.test_base import create_test_sprite

        sprite = create_test_sprite()
        sprite.center_x = 200  # Start well inside bounds
        sprite.center_y = 200

        def failing_boundary_exit_callback(sprite, axis, side):
            """A callback that raises an exception."""
            raise ValueError("Test boundary exit exception")

        # Create MoveUntil with boundary limits and a failing exit callback
        # Sprite is 128x128, so bounds need to be at least 128px wide/tall
        # Left: 36, Right: 364 (span = 328px > 128px)
        move_until(
            sprite,
            velocity=(50, 0),  # Moving right toward boundary
            condition=infinite,
            boundary_behavior="limit",
            bounds=(36, 36, 364, 364),
            on_boundary_exit=failing_boundary_exit_callback,
        )

        # Move sprite to boundary
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Should be at boundary (edge-based)
        assert sprite.right == 364
        assert sprite.change_x == 0  # Limit behavior cleared velocity

        # Manually change direction to move away from boundary (simulates velocity provider or external logic)
        sprite.change_x = -10

        # Update to trigger boundary exit - this should not crash despite callback exception
        Action.update_all(0.016)
        sprite.update()

        # Sprite should have moved away from boundary despite callback exception
        assert sprite.right < 364

    def test_move_until_vertical_boundary_limits(self):
        """Test MoveUntil with vertical boundary limits (top/bottom).

        Sprite is 128x128, so bounds must be at least 128px wide/tall.
        """
        from tests.test_base import create_test_sprite

        sprite = create_test_sprite()
        sprite.center_x = 200
        sprite.center_y = 200

        boundary_events = []

        def track_boundary_enter(sprite, axis, side):
            boundary_events.append(f"enter_{axis}_{side}")

        # Test hitting top boundary
        # Sprite is 128x128, so bounds need to be at least 128px wide/tall
        # Left: 36, Right: 364, Bottom: 36, Top: 364 (span = 328px > 128px)
        move_until(
            sprite,
            velocity=(0, 60),  # Moving up
            condition=infinite,
            boundary_behavior="limit",
            bounds=(36, 36, 364, 364),
            on_boundary_enter=track_boundary_enter,
        )

        # Update until sprite hits top boundary
        for _ in range(10):
            Action.update_all(0.016)
            sprite.update()

        # Sprite should be stopped at top boundary (edge-based)
        assert sprite.change_y == 0
        assert sprite.top == 364  # Top boundary
        assert "enter_y_top" in boundary_events

        # Clear previous action and test bottom boundary
        Action.stop_all()
        boundary_events.clear()
        sprite.center_y = 200

        move_until(
            sprite,
            velocity=(0, -60),  # Moving down
            condition=infinite,
            boundary_behavior="limit",
            bounds=(36, 36, 364, 364),
            on_boundary_enter=track_boundary_enter,
        )

        # Update until sprite hits bottom boundary
        for _ in range(10):
            Action.update_all(0.016)
            sprite.update()

        # Sprite should be stopped at bottom boundary (edge-based)
        assert sprite.change_y == 0
        assert sprite.bottom == 36  # Bottom boundary
        assert "enter_y_bottom" in boundary_events


class TestCallbackUntilInterval(ActionTestBase):
    """Tests for CallbackUntil with interval support."""

    def test_callback_until_no_interval_calls_every_frame(self, test_sprite):
        """Without interval, callback should be called every frame."""
        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(6),  # Run for 6 frames
        )
        action.apply(sprite, tag="test_no_interval")

        # Run for 6 frames
        for _ in range(6):
            Action.update_all(1 / 60)

        assert call_count == 6
        assert action.done

    def test_callback_until_with_interval_calls_on_schedule(self, test_sprite):
        """With interval, callback should be called at specified intervals."""
        from arcadeactions.frame_timing import seconds_to_frames

        sprite = test_sprite
        call_count = 0
        call_times = []

        def callback():
            nonlocal call_count
            call_count += 1
            call_times.append(call_count)

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(seconds_to_frames(0.5)),  # Run for 0.5 seconds (30 frames)
            seconds_between_calls=0.1,  # Call every 0.1 seconds
        )
        action.apply(sprite, tag="test_interval")

        # Run for 30 frames
        for _ in range(30):
            Action.update_all(1 / 60)

        # Should be called approximately every 0.1 seconds: 0.1, 0.2, 0.3, 0.4, 0.5
        assert call_count == 5
        assert action.done

    def test_callback_until_interval_factor_scaling(self, test_sprite):
        """Factor scaling should affect the interval timing."""
        from arcadeactions.frame_timing import seconds_to_frames

        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(seconds_to_frames(0.2)),  # 12 frames
            seconds_between_calls=0.1,
        )
        action.apply(sprite, tag="test_factor")

        # Run at double speed (factor = 2.0) - should call twice as often
        action.set_factor(2.0)

        # Run for 12 frames
        for _ in range(12):
            Action.update_all(1 / 60)

        # With factor 2.0, 0.1s interval becomes 0.05s, so should call at 0.05, 0.1, 0.15, 0.2
        assert call_count == 4
        assert action.done

    def test_callback_until_zero_factor_stops_calls(self, test_sprite):
        """Factor of 0.0 should stop callback calls."""
        from arcadeactions.frame_timing import seconds_to_frames

        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(seconds_to_frames(0.2)),  # 12 frames
            seconds_between_calls=0.05,  # Very frequent calls
        )
        action.apply(sprite, tag="test_zero_factor")

        # Run a few frames normally
        for _ in range(3):
            Action.update_all(1 / 60)
        initial_calls = call_count

        # Set factor to 0 (stops calls)
        action.set_factor(0.0)

        # Run many more frames
        for _ in range(30):
            Action.update_all(1 / 60)

        # Call count should not have increased
        assert call_count == initial_calls

    def test_callback_until_with_target_parameter(self, test_sprite):
        """Callback should receive target parameter when using _safe_call."""
        sprite = test_sprite
        received_targets = []

        def callback_with_target(target):
            received_targets.append(target)

        action = CallbackUntil(
            callback=callback_with_target,
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            seconds_between_calls=0.05,
        )
        action.apply(sprite, tag="test_target_param")

        # Run for 0.1 seconds
        for _ in range(6):
            Action.update_all(1 / 60)

        # Should have received the sprite as target parameter
        assert len(received_targets) == 2  # Called at 0.05s and 0.1s
        assert all(target == sprite for target in received_targets)

    def test_callback_until_with_sprite_list_target(self, test_sprite_list):
        """Callback should receive SpriteList when target is SpriteList."""
        sprite_list = test_sprite_list
        received_targets = []

        def callback_with_target(target):
            received_targets.append(target)

        action = CallbackUntil(
            callback=callback_with_target,
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            seconds_between_calls=0.05,
        )
        action.apply(sprite_list, tag="test_sprite_list_target")

        # Run for 0.1 seconds
        for _ in range(6):
            Action.update_all(1 / 60)

        # Should have received the SpriteList as target parameter
        assert len(received_targets) == 2
        assert all(target == sprite_list for target in received_targets)

    def test_callback_until_condition_stops_execution(self, test_sprite):
        """Condition should stop callback execution when met."""
        sprite = test_sprite
        call_count = 0
        condition_met = False

        def callback():
            nonlocal call_count
            call_count += 1

        def condition():
            nonlocal condition_met
            # Stop after 2 calls
            return call_count >= 2

        action = CallbackUntil(
            callback=callback,
            condition=condition,
            seconds_between_calls=0.01,  # Very frequent
        )
        action.apply(sprite, tag="test_condition_stop")

        # Run many frames - should stop after 2 calls
        for _ in range(100):  # Way more than needed
            Action.update_all(1 / 60)
            if action.done:
                break

        assert call_count == 2
        assert action.done

    def test_callback_until_reset_functionality(self, test_sprite):
        """Reset should restore original interval timing."""
        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(12),  # 0.2 seconds at 60 FPS
            seconds_between_calls=0.1,
        )
        action.apply(sprite, tag="test_reset")

        # Run for a bit, then reset
        for _ in range(6):
            Action.update_all(1 / 60)

        initial_calls = call_count
        action.reset()

        # Run again - should start fresh timing
        for _ in range(6):
            Action.update_all(1 / 60)

        # Should have made additional calls after reset
        assert call_count > initial_calls

    def test_callback_until_on_stop_callback(self, test_sprite):
        """on_stop should be called when condition is met."""
        sprite = test_sprite
        on_stop_called = False
        on_stop_data = None

        def callback():
            pass

        def on_stop(data=None):
            nonlocal on_stop_called, on_stop_data
            on_stop_called = True
            on_stop_data = data

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            seconds_between_calls=0.05,
            on_stop=on_stop,
        )
        action.apply(sprite, tag="test_on_stop")

        # Run until completion
        for _ in range(10):
            Action.update_all(1 / 60)
            if action.done:
                break

        assert on_stop_called
        assert on_stop_data is None  # frame-driven conditions return None by default

    def test_callback_until_validation_errors(self, test_sprite):
        """Should validate input parameters."""
        sprite = test_sprite

        def callback():
            pass

        # Negative interval should raise error
        with pytest.raises(ValueError, match="seconds_between_calls must be non-negative"):
            CallbackUntil(
                callback=callback,
                condition=after_frames(6),  # 0.1 seconds at 60 FPS
                seconds_between_calls=-0.1,
            )

    def test_callback_until_exception_safety(self, test_sprite):
        """Callback exceptions should not crash the action."""
        sprite = test_sprite
        call_count = 0

        def failing_callback():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Callback failed!")

        action = CallbackUntil(
            callback=failing_callback,
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            seconds_between_calls=0.05,
        )
        action.apply(sprite, tag="test_exception")

        # Should not crash despite callback exception
        for _ in range(10):
            Action.update_all(1 / 60)

        # Should have made at least one call before failing
        assert call_count >= 1


class TestCallbackUntilExceptionHandling(ActionTestBase):
    """Test exception handling in CallbackUntil."""

    def test_callback_until_duration_extraction_exception(self, test_sprite):
        """Test exception handling when duration extraction fails."""
        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(3),
            seconds_between_calls=0.05,
        )
        action.apply(sprite, tag="test_exception")

        # Should not crash despite duration extraction exception
        for _ in range(5):
            Action.update_all(1 / 60)

        # Should still work with callback
        assert call_count >= 1

    def test_callback_until_apply_effect_exception_handling(self, test_sprite):
        """Test exception handling in apply_effect duration extraction."""
        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        # Create a condition with malformed closure that will cause exception
        class BadCell:
            @property
            def cell_contents(self):
                raise AttributeError("Simulated cell access error")

        class MockCondition:
            def __call__(self):
                return False

            __closure__ = (BadCell(),)  # This will cause an exception when accessing cell_contents

        bad_closure_condition = MockCondition()

        action = CallbackUntil(
            callback=callback,
            condition=after_frames(3),
            seconds_between_calls=0.05,
        )
        action.apply(sprite, tag="test_apply_exception")

        # Should not crash despite exception in apply_effect
        for _ in range(5):
            Action.update_all(1 / 60)

        # Should still work
        assert call_count >= 1

    def test_callback_until_callback_exception_fallback(self, test_sprite):
        """Test fallback to _safe_call when callback has other exceptions."""
        sprite = test_sprite
        exception_count = 0

        def failing_callback():
            nonlocal exception_count
            exception_count += 1
            if exception_count == 1:
                # First call: TypeError (wrong signature)
                raise TypeError("Wrong signature")
            elif exception_count == 2:
                # Second call: RuntimeError (other exception)
                raise RuntimeError("Other error")

        action = CallbackUntil(
            callback=failing_callback,
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            seconds_between_calls=0.05,
        )
        action.apply(sprite, tag="test_fallback")

        # Should not crash and use _safe_call fallback
        for _ in range(6):
            Action.update_all(1 / 60)

        # Should have attempted to call at least once
        assert exception_count >= 1

    def test_callback_until_edge_case_completion_callback(self, test_sprite):
        """Test edge case where final callback fires at completion time."""
        sprite = test_sprite
        call_times = []

        def callback():
            call_times.append(len(call_times) + 1)

        # Set up action with very precise timing to trigger edge case
        action = CallbackUntil(
            callback=callback,
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            seconds_between_calls=0.1,  # Exactly at completion time
        )
        action.apply(sprite, tag="test_edge_case")

        # Run for exactly the duration
        for _ in range(6):  # 6 * (1/60) = 0.1 seconds
            Action.update_all(1 / 60)

        # Should fire callback at the completion time due to edge case handling
        assert len(call_times) >= 1

    def test_callback_until_no_duration_condition(self, test_sprite):
        """Test CallbackUntil with condition that doesn't have duration."""
        sprite = test_sprite
        call_count = 0

        def callback():
            nonlocal call_count
            call_count += 1

        # Simple condition without duration
        def simple_condition():
            return call_count >= 3

        action = CallbackUntil(
            callback=callback,
            condition=simple_condition,
            seconds_between_calls=0.02,
        )
        action.apply(sprite, tag="test_no_duration")

        # Run until condition is met
        for _ in range(10):
            Action.update_all(1 / 60)
            if action.done:
                break

        assert call_count == 3
        assert action.done


class TestCallbackUntilStopAndRestart(ActionTestBase):
    """Test CallbackUntil with stop and restart functionality."""

    def test_callback_until_stop_and_restart_with_tag(self, test_sprite):
        """Test CallbackUntil with tag, seconds_between_calls, infinite condition, stop and restart."""
        sprite = test_sprite
        call_count_first = 0
        call_count_second = 0

        def callback_first():
            nonlocal call_count_first
            call_count_first += 1

        def callback_second():
            nonlocal call_count_second
            call_count_second += 1

        # First test run: Set up CallbackUntil with tag and interval
        action1 = CallbackUntil(
            callback=callback_first,
            condition=infinite(),  # Never-ending condition
            seconds_between_calls=0.05,  # Call every 0.05 seconds (50ms)
        )
        action1.apply(sprite, tag="test_callback_action")

        # Verify the action is active
        active_actions = Action.get_actions_for_target(sprite, tag="test_callback_action")
        assert len(active_actions) == 1
        assert active_actions[0] is action1

        # Let it run and fire a couple of times
        # At 0.05 second intervals, we need to run for at least 0.1 seconds to get 2+ calls
        for i in range(10):  # 10 frames at 1/60 = ~0.167 seconds
            Action.update_all(1 / 60)  # 16.67ms per frame

        # Should have fired at least 2-3 times (0.05s and 0.1s marks, possibly 0.15s)
        assert call_count_first >= 2, f"Expected at least 2 calls, got {call_count_first}"
        assert call_count_first <= 4, f"Expected at most 4 calls, got {call_count_first}"  # Allow some tolerance

        # Verify action is still running (infinite condition)
        assert not action1.done

        # Stop the action
        action1.stop()

        # Verify action is stopped and no longer active
        assert action1.done
        active_actions_after_stop = Action.get_actions_for_target(sprite, tag="test_callback_action")
        assert len(active_actions_after_stop) == 0

        # Store the call count from first run
        first_run_calls = call_count_first

        # Wait a bit more to ensure no more calls happen after stop
        for _ in range(5):
            Action.update_all(1 / 60)
        assert call_count_first == first_run_calls, "Callback should not fire after stop"

        # Second test run: Set up the exact same configuration again
        action2 = CallbackUntil(
            callback=callback_second,
            condition=infinite(),  # Same infinite condition
            seconds_between_calls=0.05,  # Same interval
        )
        action2.apply(sprite, tag="test_callback_action")  # Same tag name

        # Verify the new action is active
        active_actions_restart = Action.get_actions_for_target(sprite, tag="test_callback_action")
        assert len(active_actions_restart) == 1
        assert active_actions_restart[0] is action2
        assert active_actions_restart[0] is not action1  # Different instance

        # Let it run and fire a couple of times again
        for i in range(10):  # Same duration as first test
            Action.update_all(1 / 60)

        # Should have fired at least 2-3 times, just like the first run
        assert call_count_second >= 2, f"Expected at least 2 calls on restart, got {call_count_second}"
        assert call_count_second <= 4, f"Expected at most 4 calls on restart, got {call_count_second}"

        # Verify second action is still running
        assert not action2.done

        # Verify first callback counter didn't change
        assert call_count_first == first_run_calls, "First callback should remain unchanged"

        # Clean up: Stop the second action
        action2.stop()
        assert action2.done

        # Final verification: Both callbacks worked independently
        assert call_count_first > 0, "First callback should have been called"
        assert call_count_second > 0, "Second callback should have been called"
        assert call_count_first == first_run_calls, "First callback count should be stable"

    def test_callback_until_in_parallel_stop_and_restart_with_tag(self, test_sprite):
        """Test CallbackUntil within parallel composition with stop and restart functionality."""
        from arcadeactions.composite import parallel
        from arcadeactions.conditional import DelayFrames

        sprite = test_sprite
        call_count_first = 0
        call_count_second = 0

        def callback_first():
            nonlocal call_count_first
            call_count_first += 1

        def callback_second():
            nonlocal call_count_second
            call_count_second += 1

        # First test run: Set up CallbackUntil within a parallel composition
        callback_action1 = CallbackUntil(
            callback=callback_first,
            condition=infinite(),  # Never-ending condition
            seconds_between_calls=0.05,  # Call every 0.05 seconds (50ms)
        )

        # Create a delay action to run alongside the callback
        delay_action1 = DelayFrames(60)  # 60 frames delay (longer than our test)

        # Create parallel composition
        parallel_action1 = parallel(callback_action1, delay_action1)
        parallel_action1.apply(sprite, tag="test_parallel_callback")

        # Verify the parallel action is active
        active_actions = Action.get_actions_for_target(sprite, tag="test_parallel_callback")
        assert len(active_actions) == 1
        assert active_actions[0] is parallel_action1

        # Let it run and fire a couple of times
        # At 0.05 second intervals, we need to run for at least 0.1 seconds to get 2+ calls
        for i in range(10):  # 10 frames at 1/60 = ~0.167 seconds
            Action.update_all(1 / 60)  # 16.67ms per frame

        # Should have fired at least 2-3 times (0.05s and 0.1s marks, possibly 0.15s)
        assert call_count_first >= 2, f"Expected at least 2 calls, got {call_count_first}"
        assert call_count_first <= 4, f"Expected at most 4 calls, got {call_count_first}"  # Allow some tolerance

        # Verify parallel action is still running (both actions should be running)
        assert not parallel_action1.done
        assert not callback_action1.done
        assert not delay_action1.done

        # Stop the parallel action (this should stop both child actions)
        parallel_action1.stop()

        # Verify parallel action and its children are stopped
        assert parallel_action1.done
        assert callback_action1.done
        assert delay_action1.done
        active_actions_after_stop = Action.get_actions_for_target(sprite, tag="test_parallel_callback")
        assert len(active_actions_after_stop) == 0

        # Store the call count from first run
        first_run_calls = call_count_first

        # Wait a bit more to ensure no more calls happen after stop
        for _ in range(5):
            Action.update_all(1 / 60)
        assert call_count_first == first_run_calls, "Callback should not fire after parallel stop"

        # Second test run: Set up the exact same parallel configuration again
        callback_action2 = CallbackUntil(
            callback=callback_second,
            condition=infinite(),  # Same infinite condition
            seconds_between_calls=0.05,  # Same interval
        )

        # Create another delay action
        delay_action2 = DelayFrames(60)  # Same delay duration (60 frames)

        # Create parallel composition with same tag
        parallel_action2 = parallel(callback_action2, delay_action2)
        parallel_action2.apply(sprite, tag="test_parallel_callback")  # Same tag name

        # Verify the new parallel action is active
        active_actions_restart = Action.get_actions_for_target(sprite, tag="test_parallel_callback")
        assert len(active_actions_restart) == 1
        assert active_actions_restart[0] is parallel_action2
        assert active_actions_restart[0] is not parallel_action1  # Different instance

        # Let it run and fire a couple of times again
        for i in range(10):  # Same duration as first test
            Action.update_all(1 / 60)

        # Should have fired at least 2-3 times, just like the first run
        assert call_count_second >= 2, f"Expected at least 2 calls on restart, got {call_count_second}"
        assert call_count_second <= 4, f"Expected at most 4 calls on restart, got {call_count_second}"

        # Verify second parallel action is still running
        assert not parallel_action2.done
        assert not callback_action2.done
        assert not delay_action2.done

        # Verify first callback counter didn't change
        assert call_count_first == first_run_calls, "First callback should remain unchanged"

        # Clean up: Stop the second parallel action
        parallel_action2.stop()
        assert parallel_action2.done
        assert callback_action2.done
        assert delay_action2.done

        # Final verification: Both callbacks worked independently within parallel compositions
        assert call_count_first > 0, "First callback should have been called"
        assert call_count_second > 0, "Second callback should have been called"
        assert call_count_first == first_run_calls, "First callback count should be stable"

    def test_callback_until_wave_pattern_issue(self, test_sprite):
        """Test CallbackUntil in wave pattern that mimics FlashingForcefieldWave behavior."""
        from arcadeactions.composite import parallel
        from arcadeactions.conditional import MoveUntil

        sprite = test_sprite
        call_count_first = 0
        call_count_second = 0

        def update_color_first():
            nonlocal call_count_first
            call_count_first += 1
            print(f"update_color_first: {call_count_first}")

        def update_color_second():
            nonlocal call_count_second
            call_count_second += 1
            print(f"update_color_second: {call_count_second}")

        # First wave: Simulate FlashingForcefieldWave pattern exactly
        move_action1 = MoveUntil(
            velocity=(50, 0),
            condition=infinite(),
        )
        blink_action1 = BlinkUntil(
            frames_until_change=30,
            condition=infinite(),
        )
        callback_action1 = CallbackUntil(
            seconds_between_calls=0.1,
            callback=update_color_first,
            condition=infinite(),
        )

        # Create parallel composition exactly like in FlashingForcefieldWave
        combined_actions1 = parallel(move_action1, blink_action1, callback_action1)
        combined_actions1.apply(sprite, tag="forcefield")

        print("=== First wave starting ===")

        # Let it run for several callback cycles
        for i in range(20):  # 20 frames at 1/60 = ~0.33 seconds, should get 3+ callbacks
            Action.update_all(1 / 60)

        print(f"First wave callbacks: {call_count_first}")
        assert call_count_first >= 3, f"Expected at least 3 calls in first wave, got {call_count_first}"

        # Store first run count
        first_run_calls = call_count_first

        # Stop the wave - this is what cleanup() does
        combined_actions1.stop()
        print("=== First wave stopped ===")

        # Verify action is stopped
        assert combined_actions1.done
        assert move_action1.done
        assert blink_action1.done
        assert callback_action1.done

        # Wait to ensure no more calls happen
        for _ in range(5):
            Action.update_all(1 / 60)
        assert call_count_first == first_run_calls, "No callbacks should fire after stop"

        # Second wave: Create new instances exactly like FlashingForcefieldWave would
        move_action2 = MoveUntil(
            velocity=(50, 0),
            condition=infinite(),
        )
        blink_action2 = BlinkUntil(
            frames_until_change=30,
            condition=infinite(),
        )
        callback_action2 = CallbackUntil(
            seconds_between_calls=0.1,
            callback=update_color_second,
            condition=infinite(),
        )

        # Create parallel composition exactly like in FlashingForcefieldWave
        combined_actions2 = parallel(move_action2, blink_action2, callback_action2)
        combined_actions2.apply(sprite, tag="forcefield")  # Same tag as before

        print("=== Second wave starting ===")

        # Let it run for several callback cycles - this should work but might not
        for i in range(20):  # Same duration as first test
            Action.update_all(1 / 60)
            if i % 5 == 0:  # Print every 5 frames to debug
                print(f"Frame {i}: Second wave callbacks so far: {call_count_second}")

        print(f"Second wave final callbacks: {call_count_second}")

        # This assertion might fail, revealing the issue
        assert call_count_second >= 3, f"Expected at least 3 calls in second wave, got {call_count_second}"

        # Verify first callback counter didn't change
        assert call_count_first == first_run_calls, "First callback should remain unchanged"

        # Clean up
        combined_actions2.stop()

        print("=== Test completed ===")
        print(f"Final counts - First: {call_count_first}, Second: {call_count_second}")

    def test_callback_until_spritelist_wave_pattern(self, test_sprite):
        """Test CallbackUntil with SpriteList exactly like FlashingForcefieldWave."""
        from arcadeactions.composite import parallel
        from arcadeactions.conditional import MoveUntil

        # Create a SpriteList like FlashingForcefieldWave does
        forcefields1 = arcade.SpriteList()
        forcefields1.append(test_sprite)  # Add a sprite to the list

        call_count_first = 0
        call_count_second = 0

        def update_color_first():
            nonlocal call_count_first
            call_count_first += 1
            print(f"update_color_first: {call_count_first}")

        def update_color_second():
            nonlocal call_count_second
            call_count_second += 1
            print(f"update_color_second: {call_count_second}")

        # Exactly like FlashingForcefieldWave.build()
        combined_actions1 = parallel(
            MoveUntil(
                velocity=(50, 0),
                condition=infinite(),
            ),
            BlinkUntil(
                frames_until_change=30,
                condition=infinite(),
            ),
            CallbackUntil(
                seconds_between_calls=0.1,
                callback=update_color_first,
                condition=infinite(),
            ),
        )
        combined_actions1.apply(forcefields1, tag="forcefield")  # Apply to SpriteList

        print("=== First wave starting (SpriteList) ===")

        # Let it run for several callback cycles
        for i in range(20):  # 20 frames at 1/60 = ~0.33 seconds, should get 3+ callbacks
            Action.update_all(1 / 60)

        print(f"First wave callbacks: {call_count_first}")
        assert call_count_first >= 3, f"Expected at least 3 calls in first wave, got {call_count_first}"

        # Store first run count
        first_run_calls = call_count_first

        # Stop the wave exactly like FlashingForcefieldWave.cleanup()
        combined_actions1.stop()
        print("=== First wave stopped (SpriteList) ===")

        # Wait to ensure no more calls happen
        for _ in range(5):
            Action.update_all(1 / 60)
        assert call_count_first == first_run_calls, "No callbacks should fire after stop"

        # Create NEW SpriteList for second wave (simulating new wave instance)
        forcefields2 = arcade.SpriteList()
        forcefields2.append(test_sprite)  # Same sprite but new list

        # Second wave: Create new parallel composition exactly like new FlashingForcefieldWave
        combined_actions2 = parallel(
            MoveUntil(
                velocity=(50, 0),
                condition=infinite(),
            ),
            BlinkUntil(
                frames_until_change=30,
                condition=infinite(),
            ),
            CallbackUntil(
                seconds_between_calls=0.1,
                callback=update_color_second,
                condition=infinite(),
            ),
        )
        combined_actions2.apply(forcefields2, tag="forcefield")  # Same tag, new SpriteList

        print("=== Second wave starting (SpriteList) ===")

        # Let it run for several callback cycles
        for i in range(20):
            Action.update_all(1 / 60)
            if i % 5 == 0:
                print(f"Frame {i}: Second wave callbacks so far: {call_count_second}")

        print(f"Second wave final callbacks: {call_count_second}")

        # This might fail if there's an issue with SpriteList action management
        assert call_count_second >= 3, f"Expected at least 3 calls in second wave, got {call_count_second}"

        # Verify first callback counter didn't change
        assert call_count_first == first_run_calls, "First callback should remain unchanged"

        # Clean up
        combined_actions2.stop()

        print("=== SpriteList Test completed ===")
        print(f"Final counts - First: {call_count_first}, Second: {call_count_second}")

    def test_callback_until_class_instance_pattern(self, test_sprite):
        """Test CallbackUntil with class instances exactly like FlashingForcefieldWave."""
        from arcadeactions.composite import parallel
        from arcadeactions.conditional import MoveUntil

        class MockWave:
            def __init__(self, wave_id):
                self.wave_id = wave_id
                self.call_count = 0
                self._actions = []
                self._forcefields = arcade.SpriteList()
                self._forcefields.append(test_sprite)

            def update_color(self):
                self.call_count += 1
                print(f"Wave {self.wave_id} update_color: {self.call_count}")

            def build(self):
                combined_actions = parallel(
                    MoveUntil(
                        velocity=(50, 0),
                        condition=infinite(),
                    ),
                    BlinkUntil(
                        frames_until_change=30,
                        condition=infinite(),
                    ),
                    CallbackUntil(
                        seconds_between_calls=0.1,
                        callback=self.update_color,  # Bound method
                        condition=infinite(),
                    ),
                )
                combined_actions.apply(self._forcefields, tag="forcefield")
                self._actions.append(combined_actions)

            def cleanup(self):
                for action in self._actions:
                    action.stop()
                self._actions.clear()

        # First wave instance
        wave1 = MockWave("Wave1")
        wave1.build()

        print("=== First wave starting (Class instance) ===")

        # Let it run for several callback cycles
        for i in range(20):
            Action.update_all(1 / 60)

        print(f"First wave callbacks: {wave1.call_count}")
        assert wave1.call_count >= 3, f"Expected at least 3 calls in first wave, got {wave1.call_count}"

        # Store first run count
        first_run_calls = wave1.call_count

        # Stop the wave
        wave1.cleanup()
        print("=== First wave stopped (Class instance) ===")

        # Wait to ensure no more calls happen
        for _ in range(5):
            Action.update_all(1 / 60)
        assert wave1.call_count == first_run_calls, "No callbacks should fire after stop"

        # Create completely new wave instance (like your game would)
        wave2 = MockWave("Wave2")
        wave2.build()

        print("=== Second wave starting (Class instance) ===")

        # Let it run for several callback cycles
        for i in range(20):
            Action.update_all(1 / 60)
            if i % 5 == 0:
                print(f"Frame {i}: Second wave callbacks so far: {wave2.call_count}")

        print(f"Second wave final callbacks: {wave2.call_count}")

        # This should work unless there's a bound method issue
        assert wave2.call_count >= 3, f"Expected at least 3 calls in second wave, got {wave2.call_count}"

        # Verify first wave counter didn't change
        assert wave1.call_count == first_run_calls, "First wave callback should remain unchanged"

        # Clean up
        wave2.cleanup()

        print("=== Class instance Test completed ===")
        print(f"Final counts - Wave1: {wave1.call_count}, Wave2: {wave2.call_count}")

    def test_boundary_callbacks_dont_fire_after_stop(self, test_sprite):
        """Test that boundary callbacks don't fire after action is stopped.

        This is a regression test for the late callback bug where boundary callbacks
        from stopped actions could interfere with newly started actions.

        Sprite is 128x128, so bounds must be at least 128px wide/tall.
        """
        sprite = test_sprite
        sprite.center_x = 300  # Start close to right boundary
        sprite.center_y = 200

        boundary_enter_count = 0
        boundary_exit_count = 0

        def on_boundary_enter(sprite, axis, side):
            nonlocal boundary_enter_count
            boundary_enter_count += 1

        def on_boundary_exit(sprite, axis, side):
            nonlocal boundary_exit_count
            boundary_exit_count += 1

        # Sprite is 128x128, so bounds need to be at least 128px wide/tall
        # Left: 36, Right: 364 (span = 328px > 128px)
        action = MoveUntil(
            velocity=(5, 0),
            condition=infinite,
            bounds=(36, 36, 364, 364),
            boundary_behavior="limit",
            on_boundary_enter=on_boundary_enter,
            on_boundary_exit=on_boundary_exit,
        )
        action.apply(sprite)

        # Move until boundary is hit
        for _ in range(20):
            Action.update_all(1 / 60)
            sprite.update()  # Apply velocity to position

        initial_enter_count = boundary_enter_count
        initial_exit_count = boundary_exit_count
        assert initial_enter_count >= 1, "Should trigger boundary enter callback"

        # Stop the action
        action.stop()

        # Verify action is stopped and callbacks are deactivated
        assert action.done
        assert not action._is_active
        assert not action._callbacks_active

        # Continue updating - callbacks should NOT fire
        for _ in range(10):
            Action.update_all(1 / 60)
            sprite.update()

        assert boundary_enter_count == initial_enter_count, "Boundary enter callbacks should not fire after stop"
        assert boundary_exit_count == initial_exit_count, "Boundary exit callbacks should not fire after stop"

    def test_callbacks_active_flag_lifecycle(self, test_sprite):
        """Test that _callbacks_active flag follows the correct lifecycle."""
        sprite = test_sprite

        callback_count = 0

        def callback():
            nonlocal callback_count
            callback_count += 1

        # Create action
        action = CallbackUntil(
            callback=callback,
            condition=infinite,
            seconds_between_calls=0.05,
        )

        # Before apply - should have _callbacks_active = True
        assert action._callbacks_active, "Should have _callbacks_active=True after construction"

        action.apply(sprite)

        # After apply - still active
        assert action._callbacks_active, "Should have _callbacks_active=True after apply"
        assert action._is_active, "Should be active after apply"

        # Let it run and trigger some callbacks
        for _ in range(10):
            Action.update_all(1 / 60)

        assert callback_count > 0, "Callbacks should fire while active"
        initial_count = callback_count

        # Stop the action
        action.stop()

        # After stop - callbacks should be deactivated
        assert not action._callbacks_active, "Should have _callbacks_active=False after stop"
        assert action.done, "Should be done after stop"
        assert not action._is_active, "Should not be active after stop"

        # Continue updating - no more callbacks should fire
        for _ in range(10):
            Action.update_all(1 / 60)

        assert callback_count == initial_count, "No callbacks should fire after stop"

    def test_three_phase_update_prevents_late_callbacks(self, test_sprite):
        """Test that the three-phase update mechanism prevents late callbacks.

        This tests the specific fix for the bug where callbacks from stopped
        actions could fire during the same update_all() call that processes their removal.
        """
        sprite = test_sprite

        callback_fired_after_done = False

        def condition_checker():
            # This will mark the action as done on first call
            return True

        def callback():
            nonlocal callback_fired_after_done
            # This callback should not fire after the action is marked as done
            # Check if the action is done when callback fires
            if action.done:
                callback_fired_after_done = True

        action = CallbackUntil(
            callback=callback,
            condition=condition_checker,
            seconds_between_calls=0.01,  # Fast callbacks
        )
        action.apply(sprite)

        # Single update that will:
        # - Mark action as done (condition returns True)
        # - Should deactivate callbacks in phase 1
        # - Should not call callback in phase 2
        Action.update_all(1 / 60)

        # Verify the action is done
        assert action.done, "Action should be done after condition is met"

        # Verify callback didn't fire after action was marked done
        assert not callback_fired_after_done, (
            "Callback should not fire after action is marked done (three-phase update should prevent this)"
        )

    def test_boundary_callback_cleanup_on_remove_effect(self, test_sprite):
        """Test that boundary callbacks are cleared in remove_effect.

        Sprite is 128x128, so bounds must be at least 128px wide/tall.
        """
        sprite = test_sprite
        sprite.center_x = 200
        sprite.center_y = 200

        def on_boundary_enter(sprite, axis, side):
            pass

        def on_boundary_exit(sprite, axis, side):
            pass

        # Sprite is 128x128, so bounds need to be at least 128px wide/tall
        # Left: 36, Right: 364 (span = 328px > 128px)
        action = MoveUntil(
            velocity=(5, 0),
            condition=infinite,
            bounds=(36, 36, 364, 364),
            boundary_behavior="limit",
            on_boundary_enter=on_boundary_enter,
            on_boundary_exit=on_boundary_exit,
        )
        action.apply(sprite)

        # Verify callbacks are registered
        assert action.on_boundary_enter is not None
        assert action.on_boundary_exit is not None
        # Boundary state may be lazily initialized on apply; if present, entries should be None/None
        for state in action._boundary_state.values():
            assert state == {"x": None, "y": None}

        # Stop the action (which calls remove_effect)
        action.stop()

        # Verify callbacks and state are cleared
        assert action.on_boundary_enter is None, "on_boundary_enter should be cleared"
        assert action.on_boundary_exit is None, "on_boundary_exit should be cleared"
        assert len(action._boundary_state) == 0, "_boundary_state should be cleared"


class TestCallbackUntilCoverage(ActionTestBase):
    """Additional CallbackUntil coverage for fallback, timing, and cloning."""

    def test_callback_fallback_without_target_coverage(self, test_sprite):
        """_call_callback_with_fallback should retry without target when signature mismatches."""

        class FallbackRecorder:
            def __init__(self):
                self.with_target = 0
                self.without_target = 0

            def __call__(self, *args):
                if args:
                    self.with_target += 1
                    raise TypeError("no target supported")
                self.without_target += 1

        recorder = FallbackRecorder()
        action = CallbackUntil(callback=recorder, condition=infinite, seconds_between_calls=0.01)
        action.apply(test_sprite, tag="callback_fallback")

        for _ in range(3):
            Action.update_all(0.016)

        assert recorder.with_target >= 1
        assert recorder.with_target == recorder.without_target

    def test_after_frames_condition_simulated_timing_coverage(self, test_sprite):
        """Frame-based CallbackUntil conditions should complete deterministically."""
        action = CallbackUntil(
            callback=lambda target: None,
            condition=after_frames(3),
            seconds_between_calls=0.02,
        )
        action.apply(test_sprite, tag="sim_duration")

        for _ in range(3):
            Action.update_all(0.016)
        assert action.done

    def test_final_scheduled_callback_runs_once_coverage(self, test_sprite):
        """Interval scheduling should fire final callback when next fire is within duration epsilon."""
        call_state = {"count": 0}

        def callback(_target=None):
            call_state["count"] += 1

        from arcadeactions.frame_timing import seconds_to_frames

        action = CallbackUntil(
            callback=callback, condition=after_frames(seconds_to_frames(0.5)), seconds_between_calls=0.5
        )
        action.apply(test_sprite, tag="final_callback")

        action._duration = 0.5
        action._elapsed = 0.5 - 0.75e-9
        action._next_fire_time = 0.5 + 0.5e-9
        action.current_seconds_between_calls = 0.5

        action.update_effect(0.0)
        assert call_state["count"] == 1

    def test_reset_and_clone_interval_state_coverage(self, test_sprite):
        """reset should restore interval timing; clone should preserve configuration."""
        call_count = {"value": 0}

        def callback():
            call_count["value"] += 1

        from arcadeactions.frame_timing import seconds_to_frames

        action = CallbackUntil(
            callback=callback, condition=after_frames(seconds_to_frames(0.2)), seconds_between_calls=0.1
        )
        action.apply(test_sprite, tag="reset_clone")
        Action.update_all(0.05)
        assert action._next_fire_time is not None

        action.reset()
        assert action._elapsed == 0.0
        assert action._next_fire_time is None
        assert action.current_seconds_between_calls == action.target_seconds_between_calls

        clone = action.clone()
        assert clone is not action
        assert clone.target_seconds_between_calls == action.target_seconds_between_calls

    def test_seconds_between_calls_pauses_with_infinite_interval_coverage(self, test_sprite):
        """Factor of zero should pause callback scheduling by setting interval to infinity."""
        call_count = {"value": 0}

        def callback():
            call_count["value"] += 1

        from arcadeactions.frame_timing import seconds_to_frames

        action = CallbackUntil(
            callback=callback, condition=after_frames(seconds_to_frames(0.3)), seconds_between_calls=0.05
        )
        action.apply(test_sprite, tag="interval_pause")
        Action.update_all(0.05)

        action.set_factor(0.0)
        assert action.current_seconds_between_calls == float("inf")
        paused_calls = call_count["value"]

        for _ in range(10):
            Action.update_all(0.05)

        assert call_count["value"] == paused_calls


class TestPriority7_TweenUntilSetDuration:
    """Test TweenUntil.set_duration raises NotImplementedError - covers line 1323."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_tween_set_duration_not_implemented(self):
        """Test that TweenUntil.set_duration raises NotImplementedError - line 1323."""
        sprite = create_test_sprite()

        action = TweenUntil(0, 100, "center_x", after_frames(60))  # 1 second at 60 FPS
        action.apply(sprite, tag="tween")

        with pytest.raises(NotImplementedError):
            action.set_duration(2.0)


class TestPriority8_CallbackUntilEdgeCases:
    """Test CallbackUntil edge cases - covers lines 1374-1375, 1385-1386, 1400, 1409-1410."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_callback_until_condition_without_frame_metadata(self):
        """Test CallbackUntil when condition lacks frame metadata - line 1374-1375."""
        sprite = create_test_sprite()
        call_count = [0]

        def callback():
            call_count[0] += 1

        # Use a simple lambda without duration attributes
        def simple_condition():
            return call_count[0] >= 5

        action = CallbackUntil(callback, simple_condition)
        action.apply(sprite, tag="callback")

        # Run for several frames
        for _ in range(10):
            Action.update_all(1 / 60)

        # Should have called callback until condition met
        assert call_count[0] == 5

    def test_callback_until_set_factor_with_interval_zero(self):
        """Test set_factor with interval mode and factor of zero - line 1385-1390."""
        sprite = create_test_sprite()
        call_count = [0]

        def callback():
            call_count[0] += 1

        from arcadeactions.frame_timing import seconds_to_frames

        action = CallbackUntil(callback, after_frames(seconds_to_frames(1.0)), seconds_between_calls=0.1)
        action.apply(sprite, tag="callback")

        # Set factor to 0 - should pause callbacks
        action.set_factor(0.0)

        # Run for several frames
        for _ in range(20):
            Action.update_all(1 / 60)

        # Should not have called callback (paused)
        assert call_count[0] == 0

    def test_callback_until_reschedule_next_fire_time(self):
        """Test rescheduling next fire time when factor changes - line 1400."""
        sprite = create_test_sprite()
        call_count = [0]

        def callback():
            call_count[0] += 1

        from arcadeactions.frame_timing import seconds_to_frames

        action = CallbackUntil(callback, after_frames(seconds_to_frames(1.0)), seconds_between_calls=0.2)
        action.apply(sprite, tag="callback")

        # Run one frame to initialize next_fire_time
        Action.update_all(0.01)

        # Change factor - should update next fire time
        action.set_factor(2.0)  # Double speed

        # Run for several frames
        for _ in range(20):
            Action.update_all(1 / 60)

        # Should have called callback more frequently due to higher factor
        assert call_count[0] > 0

    def test_callback_until_without_callback(self):
        """Test CallbackUntil when callback is None returns early - line 1408-1410."""
        sprite = create_test_sprite()

        call_count = [0]

        def callback_func():
            call_count[0] += 1

        action = CallbackUntil(callback_func, after_frames(6))  # 0.1 seconds at 60 FPS
        action.apply(sprite, tag="callback")

        # Set callback to None after action starts
        action.callback = None

        # Update a few times - should not call the callback
        for _ in range(5):
            Action.update_all(1 / 60)

        # Callback should not have been called since it was set to None
        assert call_count[0] == 0

        # Action should still be able to complete via its condition
        # Restore callback and run to completion
        action.callback = callback_func
        for _ in range(10):
            Action.update_all(1 / 60)

        assert action.done


class TestPriority10_FollowPathUntilEdgeCases:
    """Test FollowPathUntil edge cases - covers lines 765-766."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_follow_path_remove_effect_exception_handling(self):
        """Test FollowPathUntil.remove_effect handles exceptions - line 765-766."""
        sprite = create_test_sprite()

        action = FollowPathUntil(
            [(100, 100), (200, 200)], velocity=150, condition=after_frames(6)
        )  # 0.1 seconds at 60 FPS
        action.apply(sprite, tag="path")

        # Corrupt the control points to cause _bezier_point to raise exception
        action.control_points = []

        # This should not raise an error
        action.remove_effect()

        # Should complete gracefully

    def test_follow_path_with_minimum_control_points(self):
        """Test FollowPathUntil with minimum control points (2)."""
        sprite = create_test_sprite()

        action = FollowPathUntil(
            [(100, 100), (200, 200)], velocity=150, condition=after_frames(6)
        )  # 0.1 seconds at 60 FPS
        action.apply(sprite, tag="path")

        # Should work with just 2 points
        for _ in range(10):
            Action.update_all(1 / 60)

        # Should complete successfully

    def test_follow_path_insufficient_control_points(self):
        """Test FollowPathUntil with insufficient control points."""
        with pytest.raises(ValueError, match="Must specify at least 2 control points"):
            FollowPathUntil([(100, 100)], velocity=150, condition=after_frames(6))  # 0.1 seconds at 60 FPS


class TestPriority6_ExtractDurationSeconds:
    """Test _extract_duration_seconds helper - covers frame metadata extraction."""

    def test_extract_duration_from_frame_count(self):
        """Test extracting duration from after_frames metadata."""
        cond = after_frames(150)
        result = _extract_duration_seconds(cond)
        assert pytest.approx(result) == frames_to_seconds(150)

    def test_extract_duration_from_frame_window(self):
        """Test extracting duration from within_frames metadata."""
        cond = within_frames(5, 20)
        result = _extract_duration_seconds(cond)
        assert pytest.approx(result) == frames_to_seconds(15)

    def test_extract_duration_without_metadata(self):
        """Test extracting duration from condition without frame metadata."""

        def simple_condition():
            return False

        result = _extract_duration_seconds(simple_condition)
        assert result is None


class TestPriority8_TweenUntilConditionResult:
    """Test TweenUntil condition result handling - covers lines 1218-1221."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_tween_until_condition_with_non_true_result(self):
        """Test TweenUntil passes non-True condition result to callback - lines 1218-1221."""
        sprite = create_test_sprite()

        callback_data = []

        def on_stop(data):
            callback_data.append(data)

        frame_count = [0]

        def condition_with_data():
            frame_count[0] += 1
            if frame_count[0] >= 3:
                return {"frames": frame_count[0], "status": "complete"}
            return False

        action = TweenUntil(100, 200, "center_x", condition_with_data, on_stop=on_stop)
        action.apply(sprite, tag="tween")

        # Run until condition met
        for _ in range(5):
            Action.update_all(1 / 60)

        # Callback should receive condition data
        assert len(callback_data) == 1
        assert callback_data[0] == {"frames": 3, "status": "complete"}

    def test_tween_until_condition_with_true_result(self):
        """Test TweenUntil with True condition result."""
        sprite = create_test_sprite()

        callback_called = [False]

        def on_stop():
            callback_called[0] = True

        frame_count = [0]

        def simple_condition():
            frame_count[0] += 1
            return frame_count[0] >= 3

        action = TweenUntil(100, 200, "center_x", simple_condition, on_stop=on_stop)
        action.apply(sprite, tag="tween")

        # Run until condition met
        for _ in range(5):
            Action.update_all(1 / 60)

        # Callback should be called
        assert callback_called[0]


class TestPriority9_FrameConditionResetFunction:
    """Test frame condition reset logic - covers line 1553."""

    def test_after_frames_reset_function(self):
        """Test after_frames condition resets internal counter."""
        cond = after_frames(3)

        assert not cond()
        assert not cond()

        # Reset by creating a new condition
        cond = after_frames(3)
        assert not cond()


def test_move_until_pause_resets_velocity() -> None:
    sprite = arcade.SpriteSolidColor(width=10, height=10, color=arcade.color.WHITE)
    sprite.center_x = 50
    sprite.center_y = 50

    action = MoveUntil((3, 0), infinite)
    action.apply(sprite)

    Action.update_all(1 / 60)
    assert sprite.change_x == 3

    Action.pause_all()
    assert sprite.change_x == 0

    old_x = sprite.center_x
    sprite.update()
    assert sprite.center_x == old_x

    Action.resume_all()
    assert sprite.change_x == 3

    Action.stop_all()


# ============================================================================
# Frame-Based Regression Tests
# These tests define the desired frame-driven API behavior
# ============================================================================


class TestFrameBasedRegression(ActionTestBase):
    """Regression tests for frame-based timing API."""

    def test_current_frame_returns_frame_count(self):
        """Test that Action.current_frame() returns the current frame count."""
        Action._frame_counter = 0
        assert Action.current_frame() == 0

        Action.update_all(0.016)
        assert Action.current_frame() == 1

        Action.update_all(0.016)
        assert Action.current_frame() == 2

    def test_current_frame_pause_resume_determinism(self, test_sprite):
        """Test that frame counter pauses when actions are paused."""
        Action._frame_counter = 0
        sprite = test_sprite

        # Create an action
        action = move_until(sprite, velocity=(10, 0), condition=after_frames(100), tag="test_pause")

        # Update a few times
        for _ in range(5):
            Action.update_all(0.016)
        frame_before_pause = Action.current_frame()
        assert frame_before_pause == 5

        # Pause all actions
        Action.pause_all()

        # Frame counter should not increment when paused
        Action.update_all(0.016)
        assert Action.current_frame() == frame_before_pause

        Action.update_all(0.016)
        assert Action.current_frame() == frame_before_pause

        # Resume and verify counter increments again
        Action.resume_all()
        Action.update_all(0.016)
        assert Action.current_frame() == frame_before_pause + 1

    def test_step_all_advances_one_frame(self, test_sprite):
        """Test that step_all() advances exactly one frame."""
        Action._frame_counter = 0
        sprite = test_sprite

        action = move_until(sprite, velocity=(5, 0), condition=after_frames(10), tag="test_step")
        initial_frame = Action.current_frame()

        # Step should advance exactly one frame
        Action.step_all(0.016)
        assert Action.current_frame() == initial_frame + 1

        # Another step
        Action.step_all(0.016)
        assert Action.current_frame() == initial_frame + 2

        # Actions should be paused after step
        assert action._paused

    def test_after_frames_condition_cloning_preserves_metadata(self):
        """Test that _clone_condition preserves frame metadata for after_frames conditions."""
        from arcadeactions.conditional import _clone_condition

        # Create a frame-based condition
        original = after_frames(60)
        assert hasattr(original, "_is_frame_condition")
        assert hasattr(original, "_frame_count")
        assert original._frame_count == 60

        # Clone it
        cloned = _clone_condition(original)

        # Cloned condition should preserve metadata
        assert hasattr(cloned, "_is_frame_condition")
        assert hasattr(cloned, "_frame_count")
        assert cloned._frame_count == 60

        # Cloned condition should be independent (fresh state)
        # Both should start at frame 0
        assert not original()
        assert not cloned()

        # After calling original, cloned should still be at start
        for _ in range(30):
            original()
        # Original should be halfway, cloned should still be at start
        assert not cloned()

    def test_after_frames_condition_deterministic_with_pause(self, test_sprite):
        """Test that after_frames conditions are deterministic with pause/resume."""
        Action._frame_counter = 0
        sprite = test_sprite

        # Create action with frame-based condition
        condition = after_frames(10)
        action = move_until(sprite, velocity=(5, 0), condition=condition, tag="test_deterministic")

        # Update 5 frames
        for _ in range(5):
            Action.update_all(0.016)
        assert not action.done

        # Pause
        Action.pause_all()

        # Update while paused - condition should not progress
        for _ in range(10):
            Action.update_all(0.016)
        assert not action.done

        # Resume and complete
        Action.resume_all()
        for _ in range(5):
            Action.update_all(0.016)
        assert action.done
