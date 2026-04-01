from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arcadeactions.base import Action as _Action
from arcadeactions.frame_conditions import _clone_condition, infinite


class ScaleUntil(_Action):
    """Scale a sprite or sprite list until a condition is satisfied.

    Args:
        scale_velocity: The scale velocity per frame
        condition: Function that returns truthy value when scaling should stop
        on_stop: Optional callback called when condition is satisfied
    """

    def __init__(
        self,
        scale_velocity: float,
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    ):
        super().__init__(condition, on_stop)
        # Normalize scale_velocity to always be a tuple
        if isinstance(scale_velocity, int | float):
            self.target_scale_velocity = (scale_velocity, scale_velocity)
        else:
            self.target_scale_velocity = scale_velocity
        self.current_scale_velocity = self.target_scale_velocity  # Current rate (can be scaled)
        self._original_scales = {}

    def set_factor(self, factor: float) -> None:
        """Scale the scale velocity by the given factor.

        Args:
            factor: Scaling factor for scale velocity (0.0 = stopped, 1.0 = full speed)
        """
        self.current_scale_velocity = (self.target_scale_velocity[0] * factor, self.target_scale_velocity[1] * factor)
        # No immediate apply needed - scaling happens in update_effect

    def apply_effect(self) -> None:
        """Start scaling - store original scales for velocity calculation."""

        def store_original_scale(sprite):
            self._original_scales[id(sprite)] = (sprite.scale, sprite.scale)

        self.for_each_sprite(store_original_scale)

    def update_effect(self, delta_time: float) -> None:
        """Apply scaling based on velocity."""
        sx, sy = self.current_scale_velocity
        scale_delta_x = sx * delta_time
        scale_delta_y = sy * delta_time

        def apply_scale(sprite):
            # Get current scale (which is a tuple in arcade)
            current_scale = sprite.scale
            if isinstance(current_scale, tuple):
                current_scale_x, current_scale_y = current_scale
            else:
                # Handle case where scale might be a single value
                current_scale_x = current_scale_y = current_scale

            # Apply scale velocity (avoiding negative scales)
            new_scale_x = max(0.01, current_scale_x + scale_delta_x)
            new_scale_y = max(0.01, current_scale_y + scale_delta_y)
            sprite.scale = (new_scale_x, new_scale_y)

        self.for_each_sprite(apply_scale)

    def clone(self) -> ScaleUntil:
        """Create a copy of this action."""
        return ScaleUntil(self.target_scale_velocity, _clone_condition(self.condition), self.on_stop)


class FadeUntil(_Action):
    """Fade sprites until a condition is satisfied.

    Args:
        fade_velocity: The fade velocity per frame (change in alpha)
        condition: Function that returns truthy value when fading should stop
        on_stop: Optional callback called when condition is satisfied
    """

    _conflicts_with = ("alpha",)

    def __init__(
        self,
        fade_velocity: float,
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    ):
        super().__init__(condition, on_stop)
        self.target_fade_velocity = fade_velocity  # Immutable target velocity
        self.current_fade_velocity = fade_velocity  # Current velocity (can be scaled)

    def set_factor(self, factor: float) -> None:
        """Scale the fade velocity by the given factor.

        Args:
            factor: Scaling factor for fade velocity (0.0 = stopped, 1.0 = full speed)
        """
        self.current_fade_velocity = self.target_fade_velocity * factor
        # No immediate apply needed - fading happens in update_effect

    def update_effect(self, delta_time: float) -> None:
        """Apply fading based on velocity."""
        # Alpha velocity is frame-driven (like Arcade's change_x/change_angle).
        alpha_delta = self.current_fade_velocity

        def apply_fade(sprite):
            new_alpha = sprite.alpha + alpha_delta
            sprite.alpha = max(0, min(255, new_alpha))  # Clamp to valid range

        self.for_each_sprite(apply_fade)

    def clone(self) -> FadeUntil:
        """Create a copy of this action."""
        return FadeUntil(self.target_fade_velocity, _clone_condition(self.condition), self.on_stop)


class FadeTo(_Action):
    """Fade sprites to a target alpha.

    FadeTo computes fade direction automatically based on the current alpha
    and the requested target alpha. The action completes when all target
    sprites reach the target alpha, or earlier if the provided condition
    returns truthy.

    Args:
        target_alpha: Alpha value to reach (clamped to [0, 255])
        speed: Alpha change rate magnitude (direction is derived automatically)
        condition: Optional early-exit condition. Defaults to infinite (never).
        on_stop: Optional callback called when stopped. When stopping due to reaching
            target alpha, on_stop receives a dict with reason metadata.
    """

    _conflicts_with = ("alpha",)

    def __init__(
        self,
        target_alpha: float,
        speed: float,
        condition: Callable[[], Any] = infinite,
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    ):
        self._user_condition = condition
        self.target_alpha = max(0.0, min(255.0, float(target_alpha)))
        self.target_speed = abs(float(speed))
        self.current_speed = self.target_speed

        def combined_condition() -> Any:
            user_result = self._user_condition()
            if user_result:
                return user_result
            if self.all_sprites(lambda sprite: sprite.alpha == self.target_alpha):
                return {"reason": "target_alpha", "target_alpha": self.target_alpha}
            return False

        super().__init__(combined_condition, on_stop)

    def set_factor(self, factor: float) -> None:
        self.current_speed = self.target_speed * abs(factor)

    def update_effect(self, delta_time: float) -> None:
        # Speed is frame-driven; FadeTo computes direction per sprite.
        alpha_delta = self.current_speed

        def apply_fade(sprite):
            if sprite.alpha < self.target_alpha:
                new_alpha = sprite.alpha + alpha_delta
                sprite.alpha = min(self.target_alpha, max(0, min(255, new_alpha)))
            elif sprite.alpha > self.target_alpha:
                new_alpha = sprite.alpha - alpha_delta
                sprite.alpha = max(self.target_alpha, max(0, min(255, new_alpha)))

        self.for_each_sprite(apply_fade)

    def clone(self) -> FadeTo:
        return FadeTo(self.target_alpha, self.target_speed, _clone_condition(self._user_condition), self.on_stop)


class TweenUntil(_Action):
    """Directly animate a sprite property from start to end value with precise control.

    TweenUntil is perfect for A-to-B property animations like UI elements sliding into position,
    health bars updating, button feedback, or fade effects. Unlike Ease (which modulates continuous
    actions), TweenUntil directly sets property values and completes when the end value is reached.

    Use TweenUntil when you need:
    - Precise property animation (position, scale, alpha, etc.)
    - UI element animations (panels, buttons, menus)
    - Value transitions (health bars, progress indicators)
    - Simple A-to-B movements that should stop at the target

    Use Ease instead when you need:
    - Smooth acceleration/deceleration of continuous movement
    - Complex path following with smooth transitions
    - Actions that should continue after the easing completes

    Args:
        start_value: Starting value for the property being tweened. Can be a float or a callable
            that takes a sprite and returns a float (evaluated when tween starts).
        end_value: Ending value for the property being tweened
        property_name: Name of the sprite property to tween ('center_x', 'center_y', 'angle', 'scale', 'alpha')
        condition: Function that returns truthy value when tweening should stop
        on_stop: Optional callback called when condition is satisfied
        ease_function: Easing function to use for tweening (default: linear)

    Examples:
        # UI panel slide-in animation
        from arcadeactions.frame_timing import after_frames, seconds_to_frames
        slide_in = TweenUntil(-200, 100, "center_x", after_frames(seconds_to_frames(0.8)), ease_function=easing.ease_out)
        slide_in.apply(ui_panel, tag="show_panel")

        # Health bar update
        health_change = TweenUntil(old_health, new_health, "width", after_frames(seconds_to_frames(0.5)))
        health_change.apply(health_bar, tag="health_update")

        # Button press feedback
        button_press = TweenUntil(1.0, 1.2, "scale", after_frames(seconds_to_frames(0.1)))
        button_press.apply(button, tag="press_feedback")

        # Fade effect
        fade_out = TweenUntil(255, 0, "alpha", after_frames(seconds_to_frames(1.0)))
        fade_out.apply(sprite, tag="disappear")
    """

    def __init__(
        self,
        start_value: float | Callable[[Any], float],
        end_value: float,
        property_name: str,
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
        ease_function: Callable[[float], float] | None = None,
    ):
        super().__init__(condition=condition, on_stop=on_stop)
        self.start_value = start_value
        self.end_value = end_value
        self.property_name = property_name
        self.ease_function = ease_function or (lambda t: t)
        self._frame_duration = None
        self._frames_elapsed = 0
        self._completed_naturally = False  # Track if action completed vs was stopped
        self._evaluated_start_values: dict[int, float] = {}  # sprite_id -> evaluated start value

    def update(self, delta_time: float) -> None:
        """
        Override update to ensure tween logic runs before condition check.
        This prevents race conditions where condition is met before _completed_naturally is set.
        """
        if self._should_skip_update():
            return

        # Update the tween effect first - this may set _completed_naturally and self.done
        self.update_effect(delta_time)

        # If tween completed naturally during update_effect, we're done
        if self.done:
            return

        # Now check external condition
        self._check_condition_for_completion(safe_callback=False)

    def set_factor(self, factor: float) -> None:
        """Scale the tween speed by the given factor.

        Args:
            factor: Scaling factor for tween speed (0.0 = stopped, 1.0 = normal speed)
        """
        self._factor = factor

    def apply_effect(self):
        # Extract frame count from explicit attribute
        frame_count = 60  # Default: 1 second at 60 FPS
        if hasattr(self.condition, "_frame_count"):
            frames = self.condition._frame_count
            if isinstance(frames, int):
                frame_count = frames

        # An explicitly set duration should override the one from the condition.
        if self._frame_duration is not None:
            frame_count = self._frame_duration

        self._frame_duration = frame_count
        if self._frame_duration < 0:
            raise ValueError("Frame duration must be non-negative")

        # Define a helper to set the initial value.
        def set_initial_value(sprite):
            """Set the initial value of the property on a single sprite."""
            # If start_value is callable, evaluate it for this sprite
            if callable(self.start_value):
                evaluated_start = self.start_value(sprite)
                self._evaluated_start_values[id(sprite)] = evaluated_start
                setattr(sprite, self.property_name, evaluated_start)
            else:
                self._evaluated_start_values[id(sprite)] = self.start_value
                setattr(sprite, self.property_name, self.start_value)

        if self._frame_duration == 0:
            # If duration is zero, immediately set to the end value.
            self.for_each_sprite(lambda sprite: setattr(sprite, self.property_name, self.end_value))
            self._complete_action(callback_payload=None, safe_callback=False)
            return

        # For positive duration, set the initial value on all sprites.
        self.for_each_sprite(set_initial_value)
        self._frames_elapsed = 0

    def update_effect(self, delta_time: float):
        if self.done:
            return

        # Update elapsed frames with factor applied
        self._frames_elapsed += self._factor

        # Calculate progress (0 to 1)
        t = min(self._frames_elapsed / self._frame_duration, 1.0)
        eased_t = self.ease_function(t)

        # Apply the value to all target sprites (using per-sprite start values if callable)
        def update_sprite(sprite):
            sprite_id = id(sprite)
            # Get the evaluated start value for this sprite (or use the fixed start_value)
            if sprite_id in self._evaluated_start_values:
                sprite_start = self._evaluated_start_values[sprite_id]
            elif callable(self.start_value):
                # Evaluate callable if not cached (e.g., sprite added after action started)
                sprite_start = self.start_value(sprite)
                self._evaluated_start_values[sprite_id] = sprite_start
            else:
                sprite_start = self.start_value
            # Calculate current value for this sprite
            value = sprite_start + (self.end_value - sprite_start) * eased_t
            setattr(sprite, self.property_name, value)

        self.for_each_sprite(update_sprite)

        # Check for completion
        if t >= 1.0:
            # Ensure we set the exact end value

            self.for_each_sprite(lambda sprite: setattr(sprite, self.property_name, self.end_value))
            self._completed_naturally = True  # Mark as naturally completed
            self._complete_action(safe_callback=False)

    def remove_effect(self) -> None:
        """Clean up the tween effect.

        If the action completed naturally or reached its full duration, leave the property at its final value.
        If the action was stopped prematurely, reset to start value.
        """
        # Check if tween reached its natural end, even if condition was met first
        reached_natural_end = self._frame_duration is not None and self._frames_elapsed >= self._frame_duration

        if not self._completed_naturally and not reached_natural_end:
            # Action was stopped before completion - reset to start value
            def reset_sprite(sprite):
                sprite_id = id(sprite)
                # Get the evaluated start value for this sprite (or use the fixed start_value)
                if sprite_id in self._evaluated_start_values:
                    sprite_start = self._evaluated_start_values[sprite_id]
                elif callable(self.start_value):
                    # Evaluate callable if not cached (e.g., sprite added after action started)
                    sprite_start = self.start_value(sprite)
                    self._evaluated_start_values[sprite_id] = sprite_start
                else:
                    sprite_start = self.start_value
                setattr(sprite, self.property_name, sprite_start)

            self.for_each_sprite(reset_sprite)
        # If action completed naturally or reached full duration, leave property at end value

    def reset(self) -> None:
        """Reset the action to its initial state."""
        self._frames_elapsed = 0
        self._frame_duration = None
        self._completed_naturally = False
        self._evaluated_start_values.clear()

    def clone(self) -> TweenUntil:
        return TweenUntil(
            self.start_value,
            self.end_value,
            self.property_name,
            _clone_condition(self.condition),
            self.on_stop,
            self.ease_function,
        )

    def set_duration(self, duration: float) -> None:
        raise NotImplementedError
