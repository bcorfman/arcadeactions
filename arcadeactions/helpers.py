"""
This module provides thin convenience wrappers for the main Action classes,
making the API more intuitive by prioritizing the target of the action first.

For example, instead of:
    action = MoveUntil(velocity=(5, 0), condition=lambda: False)
    action.apply(sprite)

You can write:
    move_until(sprite, velocity=(5, 0), condition=lambda: False)

This improves readability while still returning the action instance for
potential chaining or modification.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import arcade

    SpriteTarget = arcade.Sprite | arcade.SpriteList
else:
    SpriteTarget = Any  # Runtime fallback

from arcadeactions import (
    Action,
    BlinkUntil,
    CallbackUntil,
    CycleTexturesUntil,
    DelayFrames,
    Ease,
    EmitParticlesUntil,
    FadeTo,
    FadeUntil,
    FollowPathUntil,
    GlowUntil,
    MoveUntil,
    RotateUntil,
    ScaleUntil,
    TweenUntil,
    infinite,
)
from arcadeactions.axis_move import MoveXUntil, MoveYUntil


def move_by(target: SpriteTarget, dx_or_offset, dy=None, *, on_stop: Any | None = None):
    """Instantly offset a sprite or all sprites in a sprite list by (dx, dy).

    Usage:
        move_by(sprite, (dx, dy))
        move_by(sprite_list, dx, dy)      # Also accepts separate arguments for convenience
    """
    from arcadeactions.instant import MoveBy

    action = MoveBy(dx_or_offset, dy, on_stop=on_stop)
    action.apply(target)
    return action


def move_to(target: SpriteTarget, x_or_position, y=None, *, on_stop: Any | None = None):
    """Instantly move a sprite or all sprites in a sprite list to an absolute position.
    Probably not useful for a sprite list. but there you go.

    Usage:
        move_to(sprite, (x, y))
        move_to(sprite, x, y)      # Also accepts separate arguments for convenience
    """
    from arcadeactions.instant import MoveTo

    action = MoveTo(x_or_position, y, on_stop=on_stop)
    action.apply(target)
    return action


def move_until(
    target: SpriteTarget,
    *,
    velocity: tuple[float, float],
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
    velocity_provider: Callable[[], tuple[float, float]] | None = None,
    on_boundary_enter: Callable[[Any, str, str], None] | None = None,
    on_boundary_exit: Callable[[Any, str, str], None] | None = None,
    **kwargs,
) -> MoveUntil:
    """
    Creates and applies a MoveUntil action to the target.

    This is a convenience wrapper for the MoveUntil class that immediately applies
    the action to the target sprite or sprite list.

    Args:
        target: The sprite (arcade.Sprite) or sprite list (arcade.SpriteList) to move.
        velocity: The (dx, dy) velocity.
        condition: The condition to stop moving.
        on_stop: An optional callback to run when the condition is met.
        tag: An optional tag for the action.
        velocity_provider: Optional function returning (dx, dy) velocity each frame.
        on_boundary_enter: Optional callback(sprite, axis, side) for boundary enter events.
        on_boundary_exit: Optional callback(sprite, axis, side) for boundary exit events.
        **kwargs: Additional arguments passed to MoveUntil (bounds, boundary_behavior, etc.)

    Returns:
        The created MoveUntil action instance.

    Example:
        # Basic movement
        move_until(sprite, velocity=(5, 0), condition=lambda: sprite.center_x > 500)

        # With boundary callbacks
        move_until(
            sprite,
            velocity=(10, 0),
            condition=infinite,
            bounds=(0, 0, 800, 600),
            boundary_behavior="bounce",
            on_boundary_enter=lambda s, axis, side: print(f"Hit {side} {axis} boundary"),
            on_boundary_exit=lambda s, axis, side: print(f"Left {side} {axis} boundary")
        )
    """
    action = MoveUntil(
        velocity=velocity,
        condition=condition,
        on_stop=on_stop,
        velocity_provider=velocity_provider,
        on_boundary_enter=on_boundary_enter,
        on_boundary_exit=on_boundary_exit,
        **kwargs,
    )
    action.apply(target, tag=tag)
    return action


def rotate_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    angular_velocity: float,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
    **kwargs,
) -> RotateUntil:
    """
    Creates and applies a RotateUntil action to the target.

    This is a convenience wrapper for the RotateUntil class that immediately applies
    the action to the target sprite or sprite list.

    Args:
        target: The sprite (arcade.Sprite) or sprite list (arcade.SpriteList) to rotate.
        angular_velocity: The angular velocity.
        condition: The condition to stop rotating.
        on_stop: An optional callback.
        tag: An optional tag.

    Returns:
        The created RotateUntil action instance.

    Example:
        from arcadeactions.frame_timing import after_frames, seconds_to_frames
        rotate_until(sprite, angular_velocity=180, condition=after_frames(seconds_to_frames(1.0)))
    """
    action = RotateUntil(angular_velocity=angular_velocity, condition=condition, on_stop=on_stop, **kwargs)
    action.apply(target, tag=tag)
    return action


def follow_path_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    control_points: list[tuple[float, float]],
    velocity: float,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
    **kwargs,
) -> FollowPathUntil:
    """
    Creates and applies a FollowPathUntil action to the target.

    This is a convenience wrapper for the FollowPathUntil class that immediately applies
    the action to the target sprite or sprite list.

    Args:
        target: The sprite (arcade.Sprite) or sprite list (arcade.SpriteList) to follow the path.
        control_points: The control points defining the path.
        velocity: The velocity along the path.
        condition: The condition to stop following the path.
        on_stop: An optional callback.
        tag: An optional tag.
        **kwargs: Additional parameters passed to FollowPathUntil:
            - rotate_with_path (bool): Enable automatic sprite rotation (default: False)
            - rotation_offset (float): Rotation offset in degrees (default: 0.0)
            - use_physics (bool): Enable physics-based steering with impulses (default: False)
            - steering_gain (float): Steering responsiveness for physics mode (default: 5.0)

    Returns:
        The created FollowPathUntil action instance.

    Examples:
        # Basic path following
        from arcadeactions.frame_timing import after_frames, seconds_to_frames
        path_points = [(100, 100), (200, 200), (300, 100)]
        follow_path_until(sprite, control_points=path_points, velocity=200, condition=after_frames(seconds_to_frames(3.0)))

        # Path following with rotation
        follow_path_until(
            sprite, control_points=path_points, velocity=200,
            condition=after_frames(seconds_to_frames(3.0)), rotate_with_path=True
        )

        # Physics-based path following with steering
        follow_path_until(
            sprite, control_points=path_points, velocity=200,
            condition=infinite, use_physics=True, steering_gain=5.0
        )
    """
    action = FollowPathUntil(
        control_points=control_points,
        velocity=velocity,
        condition=condition,
        on_stop=on_stop,
        **kwargs,
    )
    action.apply(target, tag=tag)
    return action


def blink_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    frames_until_change: int,
    condition: Callable[[], Any],
    on_stop: Callable = None,
    on_blink_enter: Callable[[Any], None] | None = None,
    on_blink_exit: Callable[[Any], None] | None = None,
    tag: str | None = None,
) -> BlinkUntil:
    """Creates and applies a BlinkUntil action with optional visibility callbacks.

    Args:
        target: Sprite or SpriteList to apply blinking to
        frames_until_change: Number of frames to wait before toggling visibility
        condition: Function that returns truthy value when blinking should stop
        on_stop: Optional callback called when condition is satisfied
        on_blink_enter: Optional callback(target) when visibility toggles to True
        on_blink_exit: Optional callback(target) when visibility toggles to False
        tag: Optional tag for the action

    Returns:
        The BlinkUntil action that was created and applied
    """
    action = BlinkUntil(
        frames_until_change=frames_until_change,
        condition=condition,
        on_stop=on_stop,
        on_blink_enter=on_blink_enter,
        on_blink_exit=on_blink_exit,
    )
    action.apply(target, tag=tag)
    return action


def delay_frames(
    target: arcade.Sprite | arcade.SpriteList,
    frames: int | None = None,
    *,
    condition: Callable[[], Any] = infinite,
    on_stop: Callable = None,
    tag: str | None = None,
) -> DelayFrames:
    """Creates and applies a DelayFrames action."""
    action = DelayFrames(frames=frames, condition=condition, on_stop=on_stop)
    action.apply(target, tag=tag)
    return action


def tween_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    start_value: float,
    end_value: float,
    property_name: str,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
    **kwargs,
) -> TweenUntil:
    """Creates and applies a TweenUntil action."""
    action = TweenUntil(
        start_value=start_value,
        end_value=end_value,
        property_name=property_name,
        condition=condition,
        on_stop=on_stop,
        **kwargs,
    )
    action.apply(target, tag=tag)
    return action


def scale_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    velocity: tuple[float, float] | float,
    condition: Callable[[], Any],
    on_stop: Callable = None,
    tag: str | None = None,
) -> ScaleUntil:
    """Creates and applies a ScaleUntil action."""
    action = ScaleUntil(scale_velocity=velocity, condition=condition, on_stop=on_stop)
    action.apply(target, tag=tag)
    return action


def fade_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    velocity: float,
    condition: Callable[[], Any],
    on_stop: Callable = None,
    tag: str | None = None,
) -> FadeUntil:
    """Creates and applies a FadeUntil action."""
    action = FadeUntil(fade_velocity=velocity, condition=condition, on_stop=on_stop)
    action.apply(target, tag=tag)
    return action


def fade_to(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    target_alpha: float,
    speed: float,
    condition: Callable[[], Any] = infinite,
    on_stop: Callable = None,
    tag: str | None = None,
) -> FadeTo:
    """Creates and applies a FadeTo action."""
    action = FadeTo(target_alpha=target_alpha, speed=speed, condition=condition, on_stop=on_stop)
    action.apply(target, tag=tag)
    return action


def callback_until(
    target: SpriteTarget,
    *,
    callback: Callable[..., None],
    condition: Callable[[], Any],
    seconds_between_calls: float | None = None,
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
) -> CallbackUntil:
    """Creates and applies a CallbackUntil action to the target.

    Args:
        target: Sprite or SpriteList the callback pertains to (passed as argument)
        callback: Function called per frame or per interval; receives target when signature allows
        condition: Function that returns truthy value when callbacks should stop
        seconds_between_calls: Optional seconds between calls; None → every frame
        on_stop: Optional callback called when condition is satisfied
        tag: Optional tag for the action

    Returns:
        The CallbackUntil action that was created and applied
    """
    action = CallbackUntil(
        callback=callback,
        condition=condition,
        seconds_between_calls=seconds_between_calls,
        on_stop=on_stop,
    )
    action.apply(target, tag=tag)
    return action


def ease(
    target: arcade.Sprite | arcade.SpriteList,
    action: Action,
    frames: int,
    *,
    ease_function: Callable[[float], float] | None = None,
    on_complete: Callable[[], Any] | None = None,
    tag: str | None = None,
) -> Ease:
    """Creates and applies an Ease action."""
    if ease_function is None:
        from arcadeactions import easing

        ease_function = easing.ease_in_out
    ease_action = Ease(action, frames=frames, ease_function=ease_function, on_complete=on_complete, tag=tag)
    ease_action.apply(target, tag=tag)
    return ease_action


def cycle_textures_until(
    target: arcade.Sprite | arcade.SpriteList,
    *,
    textures: list,
    frames_per_texture: int = 1,
    direction: int = 1,
    condition: Callable[[], Any] = None,
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
) -> CycleTexturesUntil:
    """Creates and applies a CycleTexturesUntil action to the target.

    This is a convenience wrapper for the CycleTexturesUntil class that immediately applies
    the action to the target sprite or sprite list.

    Args:
        target: The sprite (arcade.Sprite) or sprite list (arcade.SpriteList) to animate.
        textures: List of arcade.Texture objects to cycle through.
        frames_per_texture: Number of frames to display each texture (default: 1).
        direction: Direction of cycling - 1 for forward, -1 for backward (default: 1).
        condition: The condition to stop cycling. If None, cycles infinitely.
        on_stop: An optional callback to run when the condition is met.
        tag: An optional tag for the action.

    Returns:
        The created CycleTexturesUntil action instance.

    Example:
        # Simple infinite texture cycling (change texture every frame)
        cycle_textures_until(sprite, textures=texture_list)

        # Cycle backward, changing texture every 5 frames
        cycle_textures_until(
            sprite,
            textures=texture_list,
            frames_per_texture=5,
            direction=-1,
            condition=after_frames(180)
        )
    """
    from arcadeactions.conditional import infinite

    if condition is None:
        condition = infinite

    action = CycleTexturesUntil(
        textures=textures,
        frames_per_texture=frames_per_texture,
        direction=direction,
        condition=condition,
        on_stop=on_stop,
    )
    action.apply(target, tag=tag)
    return action


def glow_until(
    target: SpriteTarget,
    *,
    shadertoy_factory,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    uniforms_provider: Callable[[Any, Any], dict[str, Any]] | None = None,
    get_camera_bottom_left: Callable[[], tuple[float, float]] | None = None,
    auto_resize: bool = True,
    draw_order: str = "after",
    tag: str | None = None,
) -> GlowUntil:
    """Creates and applies a GlowUntil action to the target.

    All dependencies are provided via callables for testability.
    """
    action = GlowUntil(
        shadertoy_factory=shadertoy_factory,
        condition=condition,
        on_stop=on_stop,
        uniforms_provider=uniforms_provider,
        get_camera_bottom_left=get_camera_bottom_left,
        auto_resize=auto_resize,
        draw_order=draw_order,
    )
    action.apply(target, tag=tag)
    return action


def emit_particles_until(
    target: SpriteTarget,
    *,
    emitter_factory,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    anchor: str | tuple[float, float] = "center",
    follow_rotation: bool = False,
    start_paused: bool = False,
    destroy_on_stop: bool = True,
    tag: str | None = None,
) -> EmitParticlesUntil:
    """Creates and applies an EmitParticlesUntil action to the target.

    One emitter per sprite when target is a SpriteList; emitter follows sprite
    position (optionally rotation) until the condition is met.
    """
    action = EmitParticlesUntil(
        emitter_factory=emitter_factory,
        condition=condition,
        on_stop=on_stop,
        anchor=anchor,
        follow_rotation=follow_rotation,
        start_paused=start_paused,
        destroy_on_stop=destroy_on_stop,
    )
    action.apply(target, tag=tag)
    return action


def move_x_until(
    target: SpriteTarget,
    *,
    dx: float,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
    velocity_provider: Callable[[], tuple[float, float]] | None = None,
    on_boundary_enter: Callable[[Any, str, str], None] | None = None,
    on_boundary_exit: Callable[[Any, str, str], None] | None = None,
    **kwargs,
) -> MoveXUntil:
    """
    Creates and applies a MoveXUntil action to the target.

    This is a convenience wrapper for the MoveXUntil class that immediately applies
    the action to the target sprite or sprite list. Only affects the X axis (change_x),
    leaving Y-axis movement untouched for safe composition.

    Args:
        target: The sprite (arcade.Sprite) or sprite list (arcade.SpriteList) to move.
        dx: The X-axis velocity (dy component is ignored).
        condition: The condition to stop moving.
        on_stop: An optional callback to run when the condition is met.
        tag: An optional tag for the action.
        velocity_provider: Optional function returning (dx, dy) velocity each frame.
        on_boundary_enter: Optional callback(sprite, axis, side) for boundary enter events.
        on_boundary_exit: Optional callback(sprite, axis, side) for boundary exit events.
        **kwargs: Additional arguments passed to MoveXUntil (bounds, boundary_behavior, etc.)

    Returns:
        The created MoveXUntil action instance.

    Example:
        # Basic X-axis movement
        move_x_until(sprite, dx=5, condition=lambda: sprite.center_x > 500)

        # With boundary callbacks
        move_x_until(
            sprite,
            dx=-4,
            condition=infinite,
            bounds=(0, 0, 800, 600),
            boundary_behavior="limit",
            on_boundary_enter=lambda s, axis, side: print(f"Hit {side} {axis} boundary")
        )
    """
    action = MoveXUntil(
        velocity=(dx, 0),
        condition=condition,
        on_stop=on_stop,
        velocity_provider=velocity_provider,
        on_boundary_enter=on_boundary_enter,
        on_boundary_exit=on_boundary_exit,
        **kwargs,
    )
    action.apply(target, tag=tag)
    return action


def move_y_until(
    target: SpriteTarget,
    *,
    dy: float,
    condition: Callable[[], Any],
    on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    tag: str | None = None,
    velocity_provider: Callable[[], tuple[float, float]] | None = None,
    on_boundary_enter: Callable[[Any, str, str], None] | None = None,
    on_boundary_exit: Callable[[Any, str, str], None] | None = None,
    **kwargs,
) -> MoveYUntil:
    """
    Creates and applies a MoveYUntil action to the target.

    This is a convenience wrapper for the MoveYUntil class that immediately applies
    the action to the target sprite or sprite list. Only affects the Y axis (change_y),
    leaving X-axis movement untouched for safe composition.

    Args:
        target: The sprite (arcade.Sprite) or sprite list (arcade.SpriteList) to move.
        dy: The Y-axis velocity (dx component is ignored).
        condition: The condition to stop moving.
        on_stop: An optional callback to run when the condition is met.
        tag: An optional tag for the action.
        velocity_provider: Optional function returning (dx, dy) velocity each frame.
        on_boundary_enter: Optional callback(sprite, axis, side) for boundary enter events.
        on_boundary_exit: Optional callback(sprite, axis, side) for boundary exit events.
        **kwargs: Additional arguments passed to MoveYUntil (bounds, boundary_behavior, etc.)

    Returns:
        The created MoveYUntil action instance.

    Example:
        # Basic Y-axis movement
        move_y_until(sprite, dy=5, condition=lambda: sprite.center_y > 500)

        # With boundary callbacks
        move_y_until(
            sprite,
            dy=2,
            condition=infinite,
            bounds=(0, 0, 800, 600),
            boundary_behavior="bounce",
            on_boundary_enter=lambda s, axis, side: print(f"Hit {side} {axis} boundary")
        )
    """
    action = MoveYUntil(
        velocity=(0, dy),
        condition=condition,
        on_stop=on_stop,
        velocity_provider=velocity_provider,
        on_boundary_enter=on_boundary_enter,
        on_boundary_exit=on_boundary_exit,
        **kwargs,
    )
    action.apply(target, tag=tag)
    return action
