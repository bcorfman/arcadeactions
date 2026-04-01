"""
Axis-specific movement actions for safe composition of orthogonal motion.

This module provides MoveXUntil and MoveYUntil classes that only affect
their respective axes, enabling safe composition via parallel() for
orthogonal movement patterns.
"""

from collections.abc import Callable
from typing import Any

from arcadeactions._shared_logging import _debug_log
from arcadeactions.conditional import MoveUntil


class MoveXUntil(MoveUntil):
    """Axis-specific MoveUntil for safe composition via parallel(); affects only X axis.

    This class extends MoveUntil but only modifies sprite.change_x and never
    writes to sprite.change_y. Boundary behavior is applied only on the X axis,
    leaving Y-axis movement untouched.

    Args:
        velocity: (dx, dy) velocity vector to apply to sprites (dy is ignored)
        condition: Function that returns truthy value when movement should stop
        on_stop: Optional callback called when condition is satisfied
        bounds: Optional (left, bottom, right, top) boundary box using edge-based coordinates.
            Only left and right bounds are checked. When sprite.left hits left bound or
            sprite.right hits right bound, the X-axis boundary behavior is triggered.
        boundary_behavior: "bounce", "wrap", "limit", or None (default: None)
        velocity_provider: Optional function returning (dx, dy) to dynamically provide velocity
        on_boundary_enter: Optional callback(sprite, axis, side) called when sprite enters a boundary
        on_boundary_exit: Optional callback(sprite, axis, side) called when sprite exits a boundary
    """

    def __init__(
        self,
        velocity: tuple[float, float],
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
        bounds: tuple[float, float, float, float] | None = None,
        boundary_behavior: str | None = None,
        velocity_provider: Callable[[], tuple[float, float]] | None = None,
        on_boundary_enter: Callable[[Any, str, str], None] | None = None,
        on_boundary_exit: Callable[[Any, str, str], None] | None = None,
    ):
        super().__init__(
            velocity,
            condition,
            on_stop,
            bounds,
            boundary_behavior,
            velocity_provider,
            on_boundary_enter,
            on_boundary_exit,
        )

        _debug_log(
            f"MoveXUntil.__init__: id={id(self)}, velocity={velocity}, bounds={bounds}, "
            f"boundary_behavior={boundary_behavior}",
            action="MoveXUntil",
        )

    def apply_effect(self) -> None:
        """Apply X-axis only movement to sprites."""

        # Validate edge-based bounds against sprite dimensions
        if self.bounds and self.boundary_behavior in ("bounce", "wrap", "limit"):
            self._validate_bounds_for_sprite_dimensions()

        # Extract duration from condition if present (for duration-based conditions)
        self._duration = None
        try:
            seconds = self.condition._duration_seconds
        except AttributeError:
            seconds = None
        if isinstance(seconds, (int, float)) and seconds > 0:
            self._duration = seconds

        self._elapsed = 0.0

        def apply_to_sprite(sprite):
            # Get current velocity (from provider or current)
            if self.velocity_provider:
                current_velocity = self.velocity_provider()
                self.current_velocity = (current_velocity[0], self.current_velocity[1])
            else:
                current_velocity = self.current_velocity

            # Only set change_x, preserve change_y
            sprite.change_x = current_velocity[0]
            # change_y is intentionally not modified

            _debug_log(
                f"MoveXUntil.apply_effect: sprite={id(sprite)}, change_x={sprite.change_x}, "
                f"change_y={sprite.change_y} (preserved)",
                action="MoveXUntil",
            )

        self.for_each_sprite(apply_to_sprite)
        self._update_motion_snapshot(velocity=self.current_velocity)

    def update_effect(self, delta_time: float) -> None:
        """Update X-axis movement and handle X-axis boundary behavior only."""
        _debug_log(
            f"MoveXUntil.update_effect: id={id(self)}, delta_time={delta_time:.4f}, done={self.done}",
            action="MoveXUntil",
        )

        # Handle duration-based conditions using simulation time
        if self._duration is not None:
            self._elapsed += delta_time
            if self._elapsed >= self._duration:
                _debug_log(
                    f"MoveXUntil.update_effect: duration elapsed ({self._duration:.4f}s) - stopping",
                    action="MoveXUntil",
                )
                self._complete_action(remove_effect=True, mark_condition_met=True, safe_callback=False)
                return

        # Re-apply velocity from provider if available (X-axis only)
        if self.velocity_provider:
            try:
                dx, dy = self.velocity_provider()
                _debug_log(
                    f"MoveXUntil.update_effect: velocity_provider returned dx={dx}",
                    action="MoveXUntil",
                )
                self.current_velocity = (dx, self.current_velocity[1])

                def set_velocity(sprite):
                    sprite.change_x = dx  # Only set X, preserve Y

                self.for_each_sprite(set_velocity)
            except Exception as error:
                _debug_log(
                    f"MoveXUntil.update_effect: velocity_provider exception={error!r} - keeping current velocity",
                    action="MoveXUntil",
                )

        # Handle X-axis boundaries only
        if self.bounds and self.boundary_behavior:
            self._handle_x_boundaries()

        self._update_motion_snapshot(velocity=self.current_velocity)

    def _handle_x_boundaries(self) -> None:
        """Handle boundary behavior only for X axis using edge-based coordinates."""

        def handle_sprite_boundaries(sprite):
            left, bottom, right, top = self.bounds

            # Only check X boundaries using edge positions
            if sprite.left <= left:
                if self.boundary_behavior == "bounce":
                    sprite.change_x = abs(sprite.change_x)
                    sprite.left = left
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "x", "left")
                elif self.boundary_behavior == "wrap":
                    sprite.right = right
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "x", "left")
                elif self.boundary_behavior == "limit":
                    sprite.left = left
                    sprite.change_x = 0
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "x", "left")

            elif sprite.right >= right:
                if self.boundary_behavior == "bounce":
                    sprite.change_x = -abs(sprite.change_x)
                    sprite.right = right
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "x", "right")
                elif self.boundary_behavior == "wrap":
                    sprite.left = left
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "x", "right")
                elif self.boundary_behavior == "limit":
                    sprite.right = right
                    sprite.change_x = 0
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "x", "right")

        self.for_each_sprite(handle_sprite_boundaries)

    def clone(self) -> "MoveXUntil":
        """Create a copy of this MoveXUntil action."""
        _debug_log(f"MoveXUntil.clone: id={id(self)}", action="MoveXUntil")
        return MoveXUntil(
            self.target_velocity,
            self.condition,  # Use condition directly, not _clone_condition
            self.on_stop,
            self.bounds,
            self.boundary_behavior,
            self.velocity_provider,
            self.on_boundary_enter,
            self.on_boundary_exit,
        )


class MoveYUntil(MoveUntil):
    """Axis-specific MoveUntil for safe composition via parallel(); affects only Y axis.

    This class extends MoveUntil but only modifies sprite.change_y and never
    writes to sprite.change_x. Boundary behavior is applied only on the Y axis,
    leaving X-axis movement untouched.

    Args:
        velocity: (dx, dy) velocity vector to apply to sprites (dx is ignored)
        condition: Function that returns truthy value when movement should stop
        on_stop: Optional callback called when condition is satisfied
        bounds: Optional (left, bottom, right, top) boundary box using edge-based coordinates.
            Only bottom and top bounds are checked. When sprite.bottom hits bottom bound or
            sprite.top hits top bound, the Y-axis boundary behavior is triggered.
        boundary_behavior: "bounce", "wrap", "limit", or None (default: None)
        velocity_provider: Optional function returning (dx, dy) to dynamically provide velocity
        on_boundary_enter: Optional callback(sprite, axis, side) called when sprite enters a boundary
        on_boundary_exit: Optional callback(sprite, axis, side) called when sprite exits a boundary
    """

    def __init__(
        self,
        velocity: tuple[float, float],
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
        bounds: tuple[float, float, float, float] | None = None,
        boundary_behavior: str | None = None,
        velocity_provider: Callable[[], tuple[float, float]] | None = None,
        on_boundary_enter: Callable[[Any, str, str], None] | None = None,
        on_boundary_exit: Callable[[Any, str, str], None] | None = None,
    ):
        super().__init__(
            velocity,
            condition,
            on_stop,
            bounds,
            boundary_behavior,
            velocity_provider,
            on_boundary_enter,
            on_boundary_exit,
        )

        _debug_log(
            f"MoveYUntil.__init__: id={id(self)}, velocity={velocity}, bounds={bounds}, "
            f"boundary_behavior={boundary_behavior}",
            action="MoveYUntil",
        )

    def apply_effect(self) -> None:
        """Apply Y-axis only movement to sprites."""

        # Validate edge-based bounds against sprite dimensions
        if self.bounds and self.boundary_behavior in ("bounce", "wrap", "limit"):
            self._validate_bounds_for_sprite_dimensions()

        # Extract duration from condition if present (for duration-based conditions)
        self._duration = None
        try:
            seconds = self.condition._duration_seconds
        except AttributeError:
            seconds = None
        if isinstance(seconds, (int, float)) and seconds > 0:
            self._duration = seconds

        self._elapsed = 0.0

        def apply_to_sprite(sprite):
            # Get current velocity (from provider or current)
            if self.velocity_provider:
                current_velocity = self.velocity_provider()
                self.current_velocity = (self.current_velocity[0], current_velocity[1])
            else:
                current_velocity = self.current_velocity

            # Only set change_y, preserve change_x
            sprite.change_y = current_velocity[1]
            # change_x is intentionally not modified

            _debug_log(
                f"MoveYUntil.apply_effect: sprite={id(sprite)}, change_x={sprite.change_x} (preserved), "
                f"change_y={sprite.change_y}",
                action="MoveYUntil",
            )

        self.for_each_sprite(apply_to_sprite)
        self._update_motion_snapshot(velocity=self.current_velocity)

    def update_effect(self, delta_time: float) -> None:
        """Update Y-axis movement and handle Y-axis boundary behavior only."""
        _debug_log(
            f"MoveYUntil.update_effect: id={id(self)}, delta_time={delta_time:.4f}, done={self.done}",
            action="MoveYUntil",
        )

        # Handle duration-based conditions using simulation time
        if self._duration is not None:
            self._elapsed += delta_time
            if self._elapsed >= self._duration:
                _debug_log(
                    f"MoveYUntil.update_effect: duration elapsed ({self._duration:.4f}s) - stopping",
                    action="MoveYUntil",
                )
                self._complete_action(remove_effect=True, mark_condition_met=True, safe_callback=False)
                return

        # Re-apply velocity from provider if available (Y-axis only)
        if self.velocity_provider:
            try:
                dx, dy = self.velocity_provider()
                _debug_log(
                    f"MoveYUntil.update_effect: velocity_provider returned dy={dy}",
                    action="MoveYUntil",
                )
                self.current_velocity = (self.current_velocity[0], dy)

                def set_velocity(sprite):
                    sprite.change_y = dy  # Only set Y, preserve X

                self.for_each_sprite(set_velocity)
            except Exception as error:
                _debug_log(
                    f"MoveYUntil.update_effect: velocity_provider exception={error!r} - keeping current velocity",
                    action="MoveYUntil",
                )

        # Handle Y-axis boundaries only
        if self.bounds and self.boundary_behavior:
            self._handle_y_boundaries()

        self._update_motion_snapshot(velocity=self.current_velocity)

    def _handle_y_boundaries(self) -> None:
        """Handle boundary behavior only for Y axis using edge-based coordinates."""

        def handle_sprite_boundaries(sprite):
            left, bottom, right, top = self.bounds

            # Only check Y boundaries using edge positions
            if sprite.bottom <= bottom:
                if self.boundary_behavior == "bounce":
                    sprite.change_y = abs(sprite.change_y)
                    sprite.bottom = bottom
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "y", "bottom")
                elif self.boundary_behavior == "wrap":
                    sprite.top = top
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "y", "bottom")
                elif self.boundary_behavior == "limit":
                    sprite.bottom = bottom
                    sprite.change_y = 0
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "y", "bottom")

            elif sprite.top >= top:
                if self.boundary_behavior == "bounce":
                    sprite.change_y = -abs(sprite.change_y)
                    sprite.top = top
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "y", "top")
                elif self.boundary_behavior == "wrap":
                    sprite.bottom = bottom
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "y", "top")
                elif self.boundary_behavior == "limit":
                    sprite.top = top
                    sprite.change_y = 0
                    if self.on_boundary_enter:
                        self._safe_call(self.on_boundary_enter, sprite, "y", "top")

        self.for_each_sprite(handle_sprite_boundaries)

    def clone(self) -> "MoveYUntil":
        """Create a copy of this MoveYUntil action."""
        _debug_log(f"MoveYUntil.clone: id={id(self)}", action="MoveYUntil")
        return MoveYUntil(
            self.target_velocity,
            self.condition,  # Use condition directly, not _clone_condition
            self.on_stop,
            self.bounds,
            self.boundary_behavior,
            self.velocity_provider,
            self.on_boundary_enter,
            self.on_boundary_exit,
        )
