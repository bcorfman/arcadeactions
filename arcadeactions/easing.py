"""
Easing wrapper for ArcadeActions.

This module provides easing functionality that wraps conditional actions
and modulates their intensity over time using easing curves.
"""

from __future__ import annotations

from collections.abc import Callable
from math import cos, pi, sin

from arcadeactions import Action


def linear(percent: float) -> float:
    """Return an unchanged progress value."""
    return percent


def ease_in(percent: float) -> float:
    """Return quadratic ease-in progress."""
    return percent**2


def ease_out(percent: float) -> float:
    """Return quadratic ease-out progress."""
    return 1 - (1 - percent) ** 2


def ease_in_out(percent: float) -> float:
    """Return quadratic ease-in/out progress."""
    return 2 * percent**2 if percent < 0.5 else 1 - (-2 * percent + 2) ** 2 / 2


def smoothstep(percent: float) -> float:
    """Return smoothstep progress."""
    return percent**2 * (3.0 - 2.0 * percent)


def ease_out_elastic(percent: float) -> float:
    """Return elastic ease-out progress."""
    c4 = 2 * pi / 3
    if percent == 1:
        return 1
    if percent > 0:
        return 2 ** (-10 * percent) * sin((percent * 10 - 0.75) * c4) + 1
    return 0.0


def ease_in_back(percent: float) -> float:
    """Return ease-in progress that briefly moves backward."""
    c1 = 1.70158
    c3 = c1 + 1
    return c3 * percent**3 - c1 * percent**2


def ease_out_back(percent: float) -> float:
    """Return ease-out progress that briefly overshoots."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (percent - 1) ** 3 + c1 * (percent - 1) ** 2


def ease_in_sin(percent: float) -> float:
    """Return sine ease-in progress."""
    return 1 - cos((percent * pi) / 2)


def ease_out_sin(percent: float) -> float:
    """Return sine ease-out progress."""
    return sin((percent * pi) / 2)


def ease_in_out_sin(percent: float) -> float:
    """Return sine ease-in/out progress."""
    return -cos(percent * pi) * 0.5 + 0.5


class Ease(Action):
    """
    Wraps continuous actions to create smooth acceleration and deceleration effects.

    Ease is perfect for creating natural-feeling movement by smoothly transitioning into
    and out of continuous actions like movement, rotation, or path following. After the easing
    frame ramp completes, the wrapped action continues running at full intensity until its own
    condition is met.

    Use Ease when you need:
    - Smooth acceleration into constant movement (missiles, vehicles)
    - Natural deceleration when stopping continuous actions
    - Cinematic effects for formations or complex movements
    - Realistic physics-like acceleration curves

    Use TweenUntil instead when you need:
    - Precise A-to-B property animation (UI elements, health bars)
    - Simple movements that should stop at a target position
    - Direct control over specific property values

    The wrapped action must implement set_factor(float) to respond to intensity changes.
    All conditional actions in ArcadeActions support this interface.

    Parameters:
        action: The conditional action to be wrapped and time-warped
        frames: Number of frames over which to apply the easing ramp
        ease_function: Easing function taking t ∈ [0, 1] and returning eased factor
        on_complete: Optional callback when easing completes
        tag: Optional tag for identifying this action

    Examples:
        # Smooth missile launch - accelerates to cruise speed, then continues
        from arcadeactions.frame_timing import seconds_to_frames

        missile_move = MoveUntil((300, 0), lambda: False)
        smooth_launch = Ease(missile_move, frames=seconds_to_frames(1.5), ease_function=easing.ease_out)
        smooth_launch.apply(missile, tag="launch")

        # Formation movement with smooth acceleration
        formation_move = MoveUntil((100, 0), lambda: False)
        smooth_formation = Ease(formation_move, frames=seconds_to_frames(2.0), ease_function=easing.ease_in_out)
        smooth_formation.apply(enemy_formation, tag="advance")

        # Smooth curved path following with rotation
        path_points = [(100, 100), (200, 200), (300, 100)]
        path_action = FollowPathUntil(path_points, 250, lambda: False, rotate_with_path=True)
        eased_path = Ease(path_action, frames=seconds_to_frames(1.5), ease_function=easing.ease_in_out)
        eased_path.apply(sprite, tag="patrol")
    """

    def __init__(
        self,
        action: Action,
        frames: int,
        ease_function: Callable[[float], float] | None = None,
        on_complete: Callable[[], None] | None = None,
        tag: str | None = None,
    ):
        if frames <= 0:
            raise ValueError("frames must be positive")

        # No external condition - easing manages its own completion
        super().__init__(condition=None, on_stop=None, tag=tag)

        self.wrapped_action = action
        self.easing_frames = frames

        # Set default easing function if None provided
        if ease_function is None:
            ease_function = ease_in_out
        self.ease_function = ease_function
        self.on_complete = on_complete

        # Easing state
        self._frames_elapsed = 0
        self._easing_complete = False

    def apply(self, target, tag: str = "default") -> Action:
        """Apply both this easing wrapper and the wrapped action to the target."""
        # Apply the wrapped action first
        self.wrapped_action.apply(target, tag=f"{tag}_wrapped")

        # Then apply this easing wrapper
        return super().apply(target, tag)

    def apply_effect(self) -> None:
        """Initialize easing - start with factor 0."""
        self.wrapped_action.set_factor(0.0)

    def update_effect(self, delta_time: float) -> None:
        """Update easing factor and apply to wrapped action."""
        if self._easing_complete:
            return

        self._frames_elapsed += 1

        # Calculate easing progress (0 to 1)
        t = min(self._frames_elapsed / self.easing_frames, 1.0)

        # Apply easing function to get factor
        factor = self.ease_function(t)

        # Update wrapped action's intensity
        self.wrapped_action.set_factor(factor)

        # Check if easing is complete
        if t >= 1.0:
            self._easing_complete = True
            self.done = True

            if self.on_complete:
                self._safe_call(self.on_complete)

    def remove_effect(self) -> None:
        """Clean up easing - leave wrapped action at final factor."""
        # Deactivate callback to prevent late execution
        self.on_complete = None
        # The wrapped action continues running at its final factor
        # This allows the underlying action to continue until its own condition is met
        pass

    def stop(self) -> None:
        """Stop both this easing wrapper and the wrapped action."""
        # Stop the wrapped action
        self.wrapped_action.stop()

        # Stop this wrapper
        super().stop()

    def set_factor(self, factor: float) -> None:
        """Forward factor changes to the wrapped action.

        This allows easing actions to be nested or chained.
        """
        self.wrapped_action.set_factor(factor)

    def clone(self) -> Ease:
        """Create a copy of this Ease action."""
        return Ease(
            self.wrapped_action.clone(),
            self.easing_frames,
            self.ease_function,
            self.on_complete,
            self.tag,
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Ease(frames={self.easing_frames}, "
            f"ease_function={self.ease_function.__name__}, "
            f"wrapped={repr(self.wrapped_action)})"
        )
