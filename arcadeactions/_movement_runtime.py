from __future__ import annotations

from typing import Any

from . import physics_adapter as _pa
from ._shared_logging import _debug_log


class _MoveUntilRuntimeMixin:
    def _snapshot_boundary_state(self) -> dict[int, dict[str, str | None]]:
        if not self._boundary_state:
            return {}
        return {key: value.copy() for key, value in self._boundary_state.items()}

    def _collect_target_sprite_ids(self) -> list[int]:
        """Return a list of sprite identifiers associated with the current target."""
        if self.target is None:
            return []

        sprite_ids: list[int] = []

        try:
            iterator = iter(self.target)  # type: ignore[arg-type]
        except TypeError:
            sprite_ids.append(id(self.target))
            return sprite_ids

        for sprite in iterator:
            try:
                sprite_ids.append(id(sprite))
            except Exception:
                continue

        if not sprite_ids:
            sprite_ids.append(id(self.target))
        return sprite_ids

    def _update_motion_snapshot(self, *, velocity: tuple[float, float]) -> None:
        metadata: dict[str, Any] = {}
        boundary_state = self._snapshot_boundary_state()
        if boundary_state:
            metadata["boundary_state"] = boundary_state
        sprite_ids = self._collect_target_sprite_ids()
        if sprite_ids:
            metadata["sprite_ids"] = sprite_ids

        kwargs: dict[str, Any] = {
            "velocity": velocity,
            "bounds": self.bounds,
        }
        if metadata:
            kwargs["metadata"] = metadata
        self._update_snapshot(**kwargs)

    def apply_effect(self) -> None:
        """Apply velocity to all sprites."""

        _debug_log(
            f"apply_effect: id={id(self)}, target={self.target}, velocity_provider={bool(self.velocity_provider)}",
            action="MoveUntil",
        )

        # Validate edge-based bounds against sprite dimensions
        if self.bounds and self.boundary_behavior in ("bounce", "wrap", "limit"):
            self._validate_bounds_for_sprite_dimensions()

        # Only legacy wall-clock helpers used duration metadata; default to None for frame-based conditions
        self._duration = None
        self._elapsed = 0.0

        # Get velocity from provider or use current velocity
        if self.velocity_provider:
            try:
                dx, dy = self.velocity_provider()
                _debug_log(
                    f"apply_effect: id={id(self)}, velocity_provider returned {(dx, dy)}",
                    action="MoveUntil",
                )
                self.current_velocity = (dx, dy)
            except Exception as error:
                _debug_log(
                    f"apply_effect: id={id(self)}, velocity_provider exception={error!r} - using current_velocity",
                    action="MoveUntil",
                )
                dx, dy = self.current_velocity  # Fallback on provider error
        else:
            dx, dy = self.current_velocity

        _debug_log(
            f"apply_effect: id={id(self)}, applying velocity {(dx, dy)}",
            action="MoveUntil",
        )

        def set_velocity(sprite):
            # For limit boundary behavior, check if velocity would cross boundary
            if self.boundary_behavior == "limit" and self.bounds:
                left, bottom, right, top = self.bounds
                sprite_id = id(sprite)
                # Initialize boundary state if needed (robust against concurrent clears)
                state = self._boundary_state.setdefault(sprite_id, {"x": None, "y": None})

                # Check if applying velocity would cross horizontal boundary
                if dx > 0 and sprite.center_x + dx > right:
                    # Would cross right boundary - don't apply velocity
                    sprite.change_x = 0
                    sprite.center_x = right  # Set to boundary
                    # Trigger boundary enter event if not already at boundary
                    if state["x"] != "right":
                        if self.on_boundary_enter:
                            self._safe_call(self.on_boundary_enter, sprite, "x", "right")
                        state["x"] = "right"
                elif dx < 0 and sprite.center_x + dx < left:
                    # Would cross left boundary - don't apply velocity
                    sprite.change_x = 0
                    sprite.center_x = left  # Set to boundary
                    # Trigger boundary enter event if not already at boundary
                    if state["x"] != "left":
                        if self.on_boundary_enter:
                            self._safe_call(self.on_boundary_enter, sprite, "x", "left")
                        state["x"] = "left"
                else:
                    # Safe to apply velocity
                    sprite.change_x = dx

                # Check if applying velocity would cross vertical boundary
                if dy > 0 and sprite.center_y + dy > top:
                    # Would cross top boundary - don't apply velocity
                    sprite.change_y = 0
                    sprite.center_y = top  # Set to boundary
                    # Trigger boundary enter event if not already at boundary
                    if state["y"] != "top":
                        if self.on_boundary_enter:
                            self._safe_call(self.on_boundary_enter, sprite, "y", "top")
                        state["y"] = "top"
                elif dy < 0 and sprite.center_y + dy < bottom:
                    # Would cross bottom boundary - don't apply velocity
                    sprite.change_y = 0
                    sprite.center_y = bottom  # Set to boundary
                    # Trigger boundary enter event if not already at boundary
                    if state["y"] != "bottom":
                        if self.on_boundary_enter:
                            self._safe_call(self.on_boundary_enter, sprite, "y", "bottom")
                        state["y"] = "bottom"
                else:
                    # Safe to apply velocity
                    sprite.change_y = dy
            else:
                # Normal behavior for other boundary types or no boundaries
                _pa.set_velocity(sprite, (dx, dy))

        self.for_each_sprite(set_velocity)
        self._update_motion_snapshot(velocity=self.current_velocity)

    def update_effect(self, delta_time: float) -> None:
        """Update movement and handle boundary checking if enabled."""
        _debug_log(
            f"update_effect: id={id(self)}, delta_time={delta_time:.4f}, done={self.done}, "
            f"velocity_provider={bool(self.velocity_provider)}",
            action="MoveUntil",
        )
        # Handle duration-based conditions using simulation time
        if self._duration is not None:
            self._elapsed += delta_time

            # Check if duration has elapsed
            if self._elapsed >= self._duration:
                # End immediately and clear velocities to avoid carryover into next actions
                _debug_log(
                    f"update_effect: id={id(self)}, duration elapsed ({self._duration:.4f}s) - stopping",
                    action="MoveUntil",
                )
                self._complete_action(remove_effect=True, mark_condition_met=True, safe_callback=False)
                return

        # Default to using current_velocity for dx/dy so update_effect works even when
        # no velocity_provider is present (prevents referencing undefined locals).
        dx, dy = self.current_velocity

        # Re-apply velocity from provider if available
        if self.velocity_provider:
            try:
                dx, dy = self.velocity_provider()
                _debug_log(
                    f"update_effect: id={id(self)}, velocity_provider returned {(dx, dy)}",
                    action="MoveUntil",
                )
                self.current_velocity = (dx, dy)

                # Apply velocity to all sprites (with boundary limits if needed)
                def set_velocity(sprite):
                    if self.boundary_behavior == "limit" and self.bounds:
                        left, bottom, right, top = self.bounds
                        sprite_id = id(sprite)

                        # Initialize boundary state and get reference
                        state = self._boundary_state.setdefault(sprite_id, {"x": None, "y": None})

                        # Horizontal velocity with boundary limits and events
                        if dx > 0 and sprite.center_x + dx > right:
                            sprite.change_x = 0
                            sprite.center_x = right
                            # Trigger boundary enter event if not already at boundary
                            if state["x"] != "right":
                                if self.on_boundary_enter:
                                    self._safe_call(self.on_boundary_enter, sprite, "x", "right")
                                state["x"] = "right"
                        elif dx < 0 and sprite.center_x + dx < left:
                            sprite.change_x = 0
                            sprite.center_x = left
                            # Trigger boundary enter event if not already at boundary
                            if state["x"] != "left":
                                if self.on_boundary_enter:
                                    self._safe_call(self.on_boundary_enter, sprite, "x", "left")
                                state["x"] = "left"
                        else:
                            sprite.change_x = dx
                            # Check if we're exiting a boundary
                            if state["x"] is not None:
                                old_side = state["x"]
                                if self.on_boundary_exit:
                                    self._safe_call(self.on_boundary_exit, sprite, "x", old_side)
                                state["x"] = None

                        # Vertical velocity with boundary limits and events
                        if dy > 0 and sprite.center_y + dy > top:
                            sprite.change_y = 0
                            sprite.center_y = top
                            # Trigger boundary enter event if not already at boundary
                            if state["y"] != "top":
                                if self.on_boundary_enter:
                                    self._safe_call(self.on_boundary_enter, sprite, "y", "top")
                                state["y"] = "top"
                        elif dy < 0 and sprite.center_y + dy < bottom:
                            sprite.change_y = 0
                            sprite.center_y = bottom
                            # Trigger boundary enter event if not already at boundary
                            if state["y"] != "bottom":
                                if self.on_boundary_enter:
                                    self._safe_call(self.on_boundary_enter, sprite, "y", "bottom")
                                state["y"] = "bottom"
                        else:
                            sprite.change_y = dy
                            # Check if we're exiting a boundary
                            if state["y"] is not None:
                                old_side = state["y"]
                                if self.on_boundary_exit:
                                    self._safe_call(self.on_boundary_exit, sprite, "y", old_side)
                                state["y"] = None
                    else:
                        sprite.change_x = dx
                        sprite.change_y = dy

                self.for_each_sprite(set_velocity)
            except Exception as error:
                _debug_log(
                    f"update_effect: id={id(self)}, velocity_provider exception={error!r} - keeping current velocity",
                    action="MoveUntil",
                )
                pass

        # Re-apply velocity if not using velocity_provider (to handle resume after pause)
        # This ensures velocity is set on sprites during step_all() cycles
        if not self.velocity_provider:
            # Apply current velocity to all sprites
            # But preserve manually set velocity if sprite is at boundary and moving away
            # (only if velocity is different from action's velocity, indicating it was manually set)
            def set_velocity(sprite):
                sprite_id = id(sprite)
                # For wrap/bounce behaviors with zero velocity, preserve manually set velocity
                # (common pattern: action handles boundaries, external code sets velocity)
                if self.boundary_behavior in ("wrap", "bounce"):
                    action_has_zero_velocity = (
                        abs(self.current_velocity[0]) < 0.001 and abs(self.current_velocity[1]) < 0.001
                    )
                    if action_has_zero_velocity:
                        # Check if velocity was manually set (different from action's velocity)
                        manually_set_x = abs(sprite.change_x - self.current_velocity[0]) > 0.001
                        manually_set_y = abs(sprite.change_y - self.current_velocity[1]) > 0.001
                        # Preserve manually set velocity - action is only for boundary handling
                        if not manually_set_x:
                            sprite.change_x = self.current_velocity[0]
                        if not manually_set_y:
                            sprite.change_y = self.current_velocity[1]
                        # If both velocities are manually set, don't override anything
                        if manually_set_x and manually_set_y:
                            return
                        # If only one is manually set, apply the other from action
                        if manually_set_x:
                            sprite.change_y = self.current_velocity[1]
                        elif manually_set_y:
                            sprite.change_x = self.current_velocity[0]
                        return

                if self.boundary_behavior == "limit" and self.bounds:
                    state = self._boundary_state.get(sprite_id, {"x": None, "y": None})
                    left, bottom, right, top = self.bounds

                    # Check if sprite is at boundary (by position) and moving away
                    # Only preserve if velocity is different from action's velocity (manually set)
                    at_right_boundary = abs(sprite.right - right) < 0.1  # Allow small floating point differences
                    at_left_boundary = abs(sprite.left - left) < 0.1
                    at_top_boundary = abs(sprite.top - top) < 0.1
                    at_bottom_boundary = abs(sprite.bottom - bottom) < 0.1

                    # Check if velocity was manually set (different from action's velocity)
                    manually_set_x = abs(sprite.change_x - self.current_velocity[0]) > 0.001
                    manually_set_y = abs(sprite.change_y - self.current_velocity[1]) > 0.001

                    moving_away_x = False
                    if at_right_boundary and sprite.change_x < 0 and manually_set_x:
                        # At right boundary, moving left (away), and velocity was manually set
                        moving_away_x = True
                    elif at_left_boundary and sprite.change_x > 0 and manually_set_x:
                        # At left boundary, moving right (away), and velocity was manually set
                        moving_away_x = True

                    moving_away_y = False
                    if at_top_boundary and sprite.change_y < 0 and manually_set_y:
                        # At top boundary, moving down (away), and velocity was manually set
                        moving_away_y = True
                    elif at_bottom_boundary and sprite.change_y > 0 and manually_set_y:
                        # At bottom boundary, moving up (away), and velocity was manually set
                        moving_away_y = True

                    # Preserve manually set velocity if moving away from boundary
                    if moving_away_x:
                        # Keep current change_x (manually set)
                        sprite.change_y = self.current_velocity[1]
                    elif moving_away_y:
                        # Keep current change_y (manually set)
                        sprite.change_x = self.current_velocity[0]
                    else:
                        # Normal case: apply action's velocity
                        sprite.change_x = self.current_velocity[0]
                        sprite.change_y = self.current_velocity[1]
                else:
                    # Normal case: apply action's velocity
                    sprite.change_x = self.current_velocity[0]
                    sprite.change_y = self.current_velocity[1]

            self.for_each_sprite(set_velocity)

        # Check boundaries if configured
        # For "limit" behavior with velocity_provider, boundaries are already handled above.
        # For "bounce" and "wrap" behaviors, we need to check boundaries every frame.
        if self.bounds and self.boundary_behavior:
            # Skip boundary checking only if we have velocity_provider AND limit behavior
            # (since limit behavior is handled in the velocity_provider path above)
            if not (self.velocity_provider and self.boundary_behavior == "limit"):
                _debug_log(
                    f"update_effect: id={id(self)}, applying boundary limits behavior={self.boundary_behavior}",
                    action="MoveUntil",
                )
                self._apply_boundary_limits()

        self._update_motion_snapshot(velocity=self.current_velocity)

    def remove_effect(self) -> None:
        """Clear velocities and deactivate callbacks when the action finishes."""

        _debug_log(f"remove_effect: id={id(self)}", action="MoveUntil")

        # Deactivate boundary callbacks to prevent late execution
        self.on_boundary_enter = None
        self.on_boundary_exit = None
        self._boundary_state.clear()

        def clear_velocity(sprite):
            sprite.change_x = 0
            sprite.change_y = 0

        self.for_each_sprite(clear_velocity)
        self._update_motion_snapshot(velocity=(0.0, 0.0))

    def set_current_velocity(self, velocity: tuple[float, float]) -> None:
        """Allow external code to modify current velocity (for easing wrapper compatibility).

        This enables easing wrappers to gradually modify the velocity over time,
        such as for startup acceleration from zero to target velocity.

        Args:
            velocity: (dx, dy) velocity tuple to apply
        """
        self.current_velocity = velocity
        if not self.done:
            self.apply_effect()  # Immediately apply velocity to sprites
        _debug_log(
            f"set_current_velocity: id={id(self)}, velocity={velocity}",
            action="MoveUntil",
        )
