from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arcadeactions.base import Action as _Action
from arcadeactions.frame_conditions import _clone_condition

from . import physics_adapter as _pa


class FollowPathUntil(_Action):
    """Follow a Bezier curve path at constant velocity until a condition is satisfied.

    Unlike duration-based Bezier actions, this maintains constant speed along the curve
    and can be interrupted by any condition (collision, position, time, etc.).

    The action supports automatic sprite rotation to face the movement direction, with
    calibration offset for sprites that aren't naturally drawn pointing to the right.

    Optional physics integration: When use_physics=True and a PymunkPhysicsEngine is
    available, the action uses steering impulses to follow the path, allowing natural
    interaction with other physics forces and collisions.

    Args:
        control_points: List of (x, y) points defining the Bezier curve (minimum 2 points)
        velocity: Speed in pixels per second along the curve
        condition: Function that returns truthy value when path following should stop
        on_stop: Optional callback called when condition is satisfied
        rotate_with_path: When True, automatically rotates sprite to face movement direction.
            When False (default), sprite maintains its original orientation.
        rotation_offset: Rotation offset in degrees to calibrate sprite's natural orientation.
            Use this when sprite artwork doesn't point to the right by default:
            - 0.0 (default): Sprite artwork points right
            - -90.0: Sprite artwork points up
            - 180.0: Sprite artwork points left
            - 90.0: Sprite artwork points down
        use_physics: When True, uses physics steering with impulses instead of kinematic
            movement. Requires a PymunkPhysicsEngine. Default: False.
        steering_gain: Tunable gain parameter for physics steering responsiveness.
            Higher values = more responsive but may overshoot. Lower values = smoother
            but may lag behind path. Default: 5.0. Only used when use_physics=True.

    Examples:
        from arcadeactions.frame_timing import after_frames, seconds_to_frames

        # Basic path following without rotation
        action = FollowPathUntil([(100, 100), (200, 200)], velocity=150, condition=after_frames(seconds_to_frames(3.0)))

        # Path following with automatic rotation (sprite artwork points right)
        action = FollowPathUntil(
            [(100, 100), (200, 200)], velocity=150, condition=after_frames(seconds_to_frames(3.0)),
            rotate_with_path=True
        )

        # Path following with rotation for sprite artwork that points up by default
        action = FollowPathUntil(
            [(100, 100), (200, 200)], velocity=150, condition=after_frames(seconds_to_frames(3.0)),
            rotate_with_path=True, rotation_offset=-90.0
        )

        # Complex curved path with rotation
        bezier_points = [(100, 100), (150, 200), (250, 150), (300, 100)]
        action = FollowPathUntil(
            bezier_points, velocity=200, condition=lambda: sprite.center_x > 400,
            rotate_with_path=True
        )

        # Physics-based path following with steering
        action = FollowPathUntil(
            [(100, 100), (300, 200), (500, 100)], velocity=150, condition=infinite,
            use_physics=True, steering_gain=5.0, rotate_with_path=True
        )
    """

    def __init__(
        self,
        control_points: list[tuple[float, float]],
        velocity: float,
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
        rotate_with_path: bool = False,
        rotation_offset: float = 0.0,
        use_physics: bool = False,
        steering_gain: float = 5.0,
    ):
        super().__init__(condition, on_stop)
        if len(control_points) < 2:
            raise ValueError("Must specify at least 2 control points")

        self.control_points = control_points
        self.target_velocity = velocity  # Immutable target velocity
        self.current_velocity = velocity  # Current velocity (can be scaled)
        self.rotate_with_path = rotate_with_path  # Enable automatic sprite rotation
        self.rotation_offset = rotation_offset  # Degrees to offset for sprite artwork orientation
        self.use_physics = use_physics  # Enable physics-based steering
        self.steering_gain = steering_gain  # Steering force multiplier for physics mode

        # Track last applied movement angle to smooth out rotations when
        # the incremental movement vector becomes (nearly) zero – e.g. when
        # a path repeats and the sprite is momentarily stationary.
        self._prev_movement_angle: float | None = None

        # Path traversal state
        self._curve_progress = 0.0  # Progress along curve: 0.0 (start) to 1.0 (end)
        self._curve_length = 0.0  # Total length of the curve in pixels
        self._last_position = None  # Previous position for calculating movement delta
        self._update_path_snapshot()

    def set_factor(self, factor: float) -> None:
        """Scale the path velocity by the given factor.

        Args:
            factor: Scaling factor for path velocity (0.0 = stopped, 1.0 = full speed)
        """
        self.current_velocity = self.target_velocity * factor
        # No immediate apply needed - velocity is used in update_effect

    def _bezier_point(self, t: float) -> tuple[float, float]:
        """Calculate point on Bezier curve at parameter t (0-1)."""
        from math import comb

        n = len(self.control_points) - 1
        x = y = 0
        for i, point in enumerate(self.control_points):
            # Binomial coefficient * (1-t)^(n-i) * t^i
            coef = comb(n, i) * (1 - t) ** (n - i) * t**i
            x += point[0] * coef
            y += point[1] * coef
        return (x, y)

    def _calculate_curve_length(self, samples: int = 100) -> float:
        """Approximate curve length by sampling points."""
        from math import sqrt

        length = 0.0
        prev_point = self._bezier_point(0.0)

        for i in range(1, samples + 1):
            t = i / samples
            current_point = self._bezier_point(t)
            dx = current_point[0] - prev_point[0]
            dy = current_point[1] - prev_point[1]
            length += sqrt(dx * dx + dy * dy)
            prev_point = current_point

        return length

    def apply_effect(self) -> None:
        """Initialize path following and rotation state."""
        # Calculate curve length for constant velocity movement
        self._curve_length = self._calculate_curve_length()
        self._curve_progress = 0.0

        # Set initial position on the curve
        start_point = self._bezier_point(0.0)
        self._last_position = start_point

        # Snap target(s) to the exact start point to guarantee continuity across repeats
        def snap_to_start(sprite):
            sprite.center_x = start_point[0]
            sprite.center_y = start_point[1]

        self.for_each_sprite(snap_to_start)
        self._update_path_snapshot()

    def update_effect(self, delta_time: float) -> None:
        """Update path following with constant velocity and optional rotation."""
        from math import atan2, degrees, sqrt

        if self._curve_length <= 0:
            self._update_path_snapshot()
            return

        # Calculate how far to move along curve based on velocity
        distance_per_frame = self.current_velocity * delta_time
        progress_delta = distance_per_frame / self._curve_length
        self._curve_progress = min(1.0, self._curve_progress + progress_delta)

        # Calculate new position on curve
        current_point = self._bezier_point(self._curve_progress)

        # Check if physics engine is available for steering mode
        engine = None
        if self.use_physics and self.target is not None:
            # Check if any sprite in target has physics
            def check_engine(sprite):
                nonlocal engine
                if engine is None:
                    engine = _pa.detect_engine(sprite)

            self.for_each_sprite(check_engine)

        # Apply movement using physics steering or kinematic mode
        if self._last_position:
            dx = current_point[0] - self._last_position[0]
            dy = current_point[1] - self._last_position[1]

            # Calculate movement angle for rotation (skip if no movement)
            if self.rotate_with_path and (dx != 0 or dy != 0):
                movement_angle = degrees(atan2(dy, dx))
                self._prev_movement_angle = movement_angle
            else:
                # If no movement, reuse the last angle to avoid jitter
                movement_angle = self._prev_movement_angle

            if engine and self.use_physics:
                # Physics steering mode
                def apply_steering(sprite):
                    # Calculate target velocity vector
                    distance = sqrt(dx * dx + dy * dy)
                    if distance > 0:
                        target_vx = (dx / distance) * self.current_velocity
                        target_vy = (dy / distance) * self.current_velocity
                    else:
                        target_vx = target_vy = 0

                    # Apply steering impulse to move toward target velocity
                    _pa.apply_impulse(sprite, (target_vx * self.steering_gain, target_vy * self.steering_gain))

                    # Apply rotation if enabled
                    if self.rotate_with_path and movement_angle is not None:
                        target_angle = movement_angle + self.rotation_offset
                        delta = target_angle - sprite.angle
                        while delta <= -180:
                            delta += 360
                        while delta > 180:
                            delta -= 360
                        _pa.set_angular_velocity(sprite, delta)

                self.for_each_sprite(apply_steering)
            else:
                # Kinematic mode (direct position updates)
                def apply_movement(sprite):
                    sprite.center_x = current_point[0]
                    sprite.center_y = current_point[1]

                    # Apply rotation if enabled
                    if self.rotate_with_path and movement_angle is not None:
                        sprite.angle = movement_angle + self.rotation_offset

                self.for_each_sprite(apply_movement)

            # Update last position for next frame
            self._last_position = current_point

        # Update path snapshot for debugging
        self._update_path_snapshot()

        if self._curve_progress >= 1.0 and not self.done:
            self._complete_action(remove_effect=True, mark_condition_met=True, callback_payload=None)

    def _update_path_snapshot(self) -> None:
        self._update_snapshot(
            control_points=self.control_points,
            velocity=self.current_velocity,
            progress=self._curve_progress,
            metadata={"path_points": self.control_points},
        )

    def clone(self) -> FollowPathUntil:
        return FollowPathUntil(
            self.control_points,
            self.target_velocity,
            _clone_condition(self.condition),
            self.on_stop,
            self.rotate_with_path,
            self.rotation_offset,
            self.use_physics,
            self.steering_gain,
        )

    def reset(self) -> None:
        self._curve_progress = 0.0
        self._last_position = None
        self._prev_movement_angle = None
        self._update_path_snapshot()

    def set_duration(self, duration: float) -> None:
        raise NotImplementedError
