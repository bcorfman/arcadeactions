from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arcadeactions._shared_logging import _agent_debug_log
from arcadeactions.base import Action as _Action
from arcadeactions.frame_conditions import _clone_condition


def _apply_offset(sprite, dx: float, dy: float, origins: dict[int, tuple[float, float]]):
    ox, oy = origins[id(sprite)]
    sprite.center_x = ox + dx
    sprite.center_y = oy + dy


class ParametricMotionUntil(_Action):
    """Move sprites along a relative parametric curve.

    The *offset_fn* receives progress *t* (0→1) and returns (dx, dy) offsets that
    are **added** to each sprite's origin captured at *apply* time.  Completion is
    governed by the *condition* parameter (typically ``after_frames()``).

    Frame-based timing only: Use ``after_frames(N)`` to specify duration in frames.
    If you have a duration in seconds, convert it first using ``seconds_to_frames()``.
    """

    def __init__(
        self,
        offset_fn: Callable[[float], tuple[float, float]],
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
        *,
        rotate_with_path: bool = False,
        rotation_offset: float = 0.0,
        # --- debug ---
        debug: bool = False,
        debug_threshold: float | None = None,
    ):
        super().__init__(condition=condition, on_stop=on_stop)
        self._offset_fn = offset_fn
        self._origins: dict[int, tuple[float, float]] = {}
        self._elapsed_frames = 0.0
        self._frame_duration: float | None = None  # extracted from after_frames() condition
        self.rotate_with_path = rotate_with_path
        self.rotation_offset = rotation_offset
        self._prev_offset = None  # Track previous offset for rotation calculation

        # Debug helpers
        self._debug = debug
        self._debug_threshold = debug_threshold if debug_threshold is not None else 120.0  # px / frame

    # --------------------- Action hooks --------------------
    def apply_effect(self) -> None:  # noqa: D401 – imperative style
        """Memorise origins and determine duration."""

        def capture_origin(sprite):
            self._origins[id(sprite)] = (sprite.center_x, sprite.center_y)

        self.for_each_sprite(capture_origin)

        if not getattr(self, "_agent_logged_apply", False):
            # region agent log
            _agent_debug_log(
                hypothesis_id="H3",
                location="conditional.ParametricMotionUntil.apply_effect",
                message="param_motion_apply",
                data={"action_id": id(self), "sprite_count": len(self._origins)},
            )
            # endregion agent log
            self._agent_logged_apply = True

        # Reset timing state
        self._elapsed_frames = 0.0
        self._frame_duration = None

        # Extract frame count from after_frames() condition
        frame_count = getattr(self.condition, "_frame_count", None)
        precise_duration = getattr(self.condition, "_frame_duration_precise", None)
        if isinstance(frame_count, int) and frame_count > 0:
            if isinstance(precise_duration, (int, float)) and precise_duration > 0:
                self._frame_duration = float(precise_duration)
            else:
                self._frame_duration = float(frame_count)
        else:
            # No frame count metadata – complete immediately
            self._frame_duration = 0.0

        # Do not pre-position sprites; offsets are relative to captured origins
        self._prev_offset = self._offset_fn(0.0)

    def update_effect(self, delta_time: float) -> None:  # noqa: D401
        from math import atan2, degrees, hypot

        # Frame-based timing: advance by one frame per update, scaled by factor
        self._elapsed_frames += self._factor
        total = self._frame_duration or 0.0
        progress = min(1.0, self._elapsed_frames / total) if total > 0 else 1.0

        # Clamp progress to 1.0 for offset calculation to ensure exact endpoint positioning
        clamped_progress = min(1.0, progress)
        current_offset = self._offset_fn(clamped_progress)
        dx, dy = current_offset

        # Calculate rotation if enabled
        sprite_angle = None
        if self.rotate_with_path and self._prev_offset is not None:
            # Calculate movement vector from previous to current offset
            movement_dx = dx - self._prev_offset[0]
            movement_dy = dy - self._prev_offset[1]

            # Debug: detect large single-frame jumps in relative space
            if self._debug:
                import time as _t

                jump_mag = hypot(movement_dx, movement_dy)
                if jump_mag > self._debug_threshold:
                    stamp = f"{_t.time():.3f}"
                    print(
                        f"[ParametricMotionUntil:jump] t={stamp} Δ={jump_mag:.2f}px (thr={self._debug_threshold})"
                        f" prev_offset={self._prev_offset} new_offset={(dx, dy)}"
                    )
            # Only calculate angle if there's significant movement
            if abs(movement_dx) > 1e-6 or abs(movement_dy) > 1e-6:
                angle = degrees(atan2(movement_dy, movement_dx))
                sprite_angle = angle + self.rotation_offset

        # Apply movement and rotation
        def apply_transform(sprite):
            _apply_offset(sprite, dx, dy, self._origins)
            if sprite_angle is not None:
                sprite.angle = sprite_angle

        self.for_each_sprite(apply_transform)

        # Store current offset for next frame's rotation calculation
        self._prev_offset = current_offset

        if not getattr(self, "_agent_logged_update", False):
            sample_pos = None
            try:
                iterator = iter(self.target)
                sample_sprite = next(iterator)
                sample_pos = (sample_sprite.center_x, sample_sprite.center_y)
            except Exception:
                sample_pos = None
            # region agent log
            _agent_debug_log(
                hypothesis_id="H4",
                location="conditional.ParametricMotionUntil.update_effect",
                message="param_motion_update",
                data={
                    "action_id": id(self),
                    "progress": clamped_progress,
                    "dx": dx,
                    "dy": dy,
                    "sample_pos": sample_pos,
                },
            )
            # endregion agent log
            self._agent_logged_update = True

        if progress >= 1.0 and self._frame_duration == 0.0:
            # No frame-based condition is driving completion; mark done ourselves.
            self._complete_action(mark_condition_met=True, callback_payload=None, safe_callback=False)

    def remove_effect(self) -> None:
        """
        Skip position snapping to prevent jumps in repeated wave patterns.

        Originally this would snap sprites to exact endpoints for seamless
        repetition, but when sprite counts change (enemies destroyed) or
        multiple actions overlap, this causes visible position jumps.
        """
        # Disabled to prevent jumps - let patterns complete naturally
        _agent_debug_log(
            hypothesis_id="H7",
            location="conditional.ParametricMotionUntil.remove_effect",
            message="param_motion_removed",
            data={"action_id": id(self)},
        )

    def clone(self) -> ParametricMotionUntil:  # type: ignore[name-defined]
        return ParametricMotionUntil(
            self._offset_fn,
            _clone_condition(self.condition),
            self.on_stop,
            rotate_with_path=self.rotate_with_path,
            rotation_offset=self.rotation_offset,
            debug=self._debug,
            debug_threshold=self._debug_threshold,
        )

    def reset(self) -> None:
        """Reset the action to its initial state."""
        self._elapsed_frames = 0.0
        self._origins.clear()
        self._prev_offset = None
        self._condition_met = False
        self.done = False
        # Keep duration configuration (seconds or frames) so a reused action
        # instance behaves consistently after reset.

    def set_factor(self, factor: float) -> None:
        """Scale the motion speed by the given factor.

        Args:
            factor: Scaling factor for motion speed (0.0 = stopped, 1.0 = normal speed)
        """
        self._factor = factor
