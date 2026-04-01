from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arcadeactions._shared_logging import _debug_log
from arcadeactions.base import Action as _Action
from arcadeactions.frame_conditions import _clone_condition, infinite


class BlinkUntil(_Action):
    """Blink sprites (toggle visibility) until a condition is satisfied.

    Args:
        frames_until_change: Number of frames to wait before toggling visibility
        condition: Function that returns truthy value when blinking should stop
        on_stop: Optional callback called when condition is satisfied
        on_blink_enter: Optional callback(sprite) when visibility toggles to True
        on_blink_exit: Optional callback(sprite) when visibility toggles to False
    """

    def __init__(
        self,
        frames_until_change: int,
        condition: Callable[[], Any],
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
        on_blink_enter: Callable[[Any], None] | None = None,
        on_blink_exit: Callable[[Any], None] | None = None,
    ):
        if frames_until_change <= 0:
            raise ValueError("frames_until_change must be positive")

        super().__init__(condition, on_stop)
        self.target_frames_until_change = frames_until_change  # Immutable target rate
        self.current_frames_until_change = frames_until_change  # Current rate (can be scaled)
        self._frames_elapsed = 0
        self._original_visibility = {}
        self._last_visible: dict[int, bool] = {}

        self.on_blink_enter = on_blink_enter
        self.on_blink_exit = on_blink_exit

    def set_factor(self, factor: float) -> None:
        """Scale the blink rate by the given factor.

        Factor affects the frames between blinks - higher factor = faster blinking.
        A factor of 0.0 stops blinking (sprites stay in current visibility state).

        Args:
            factor: Scaling factor for blink rate (0.0 = stopped, 1.0 = normal speed, 2.0 = double speed)
        """
        if factor <= 0:
            # Stop blinking - set to a very large value
            self.current_frames_until_change = 999999
        else:
            # Faster factor = fewer frames between changes
            self.current_frames_until_change = max(1, int(self.target_frames_until_change / factor))

    def apply_effect(self) -> None:
        """Store original visibility for all sprites."""

        def store_visibility(sprite):
            vid = id(sprite)
            visible = sprite.visible
            self._original_visibility[vid] = visible
            self._last_visible[vid] = visible

        self.for_each_sprite(store_visibility)

    def remove_effect(self) -> None:
        """Restore original visibility for all sprites."""

        def restore_visibility(sprite):
            vid = id(sprite)
            original_visible = self._original_visibility.get(vid, True)
            sprite.visible = original_visible
            self._last_visible.pop(vid, None)
            self._original_visibility.pop(vid, None)

        self.for_each_sprite(restore_visibility)

    def update_effect(self, delta_time: float) -> None:
        """Apply blinking effect based on the configured interval."""
        self._frames_elapsed += 1
        # Determine how many intervals have passed to know whether we should show or hide.
        cycles = int(self._frames_elapsed / self.current_frames_until_change)

        # Track if any sprites changed visibility this frame
        any_entered = False
        any_exited = False

        def apply_blink(sprite):
            nonlocal any_entered, any_exited
            vid = id(sprite)
            # Get the starting visibility state for this sprite
            original_visible = self._original_visibility.get(vid, True)

            # Calculate new visibility: if original was visible, even cycles = visible
            # If original was invisible, odd cycles = visible (invert the pattern)
            if original_visible:
                new_visible = cycles % 2 == 0
            else:
                new_visible = cycles % 2 == 1

            last_visible = self._last_visible.get(vid, original_visible)  # Use original visibility as default

            if new_visible != last_visible:
                if new_visible:
                    any_entered = True
                else:
                    any_exited = True

            sprite.visible = new_visible
            self._last_visible[vid] = new_visible

        self.for_each_sprite(apply_blink)

        # Call callbacks once per frame with the target (Sprite or SpriteList)
        if any_entered and self.on_blink_enter:
            self._safe_call(self.on_blink_enter, self.target)
        if any_exited and self.on_blink_exit:
            self._safe_call(self.on_blink_exit, self.target)

    def reset(self) -> None:
        """Reset blinking rate to original target rate."""
        self.current_frames_until_change = self.target_frames_until_change

    def clone(self) -> BlinkUntil:
        """Create a copy of this action."""
        return BlinkUntil(
            self.target_frames_until_change,
            _clone_condition(self.condition),
            self.on_stop,
            on_blink_enter=self.on_blink_enter,
            on_blink_exit=self.on_blink_exit,
        )


class CycleTexturesUntil(_Action):
    """Continuously cycle through a list of textures until a condition is met.

    This action animates sprite textures by cycling through a provided list at a
    specified frame interval. The cycling can go forward or backward, and the action
    runs until the specified condition is satisfied.

    Args:
        textures: List of arcade.Texture objects to cycle through
        frames_per_texture: Number of frames to display each texture
        direction: Direction of cycling (1 for forward, -1 for backward)
        condition: Function that returns truthy value when cycling should stop
        on_stop: Optional callback called when condition is satisfied
    """

    _conflicts_with = ("texture",)

    def __init__(
        self,
        textures: list,
        frames_per_texture: int = 1,
        direction: int = 1,
        condition: Callable[[], Any] = infinite,
        on_stop: Callable[[Any], None] | Callable[[], None] | None = None,
    ):
        if not textures:
            raise ValueError("textures list cannot be empty")
        if direction not in (1, -1):
            raise ValueError("direction must be 1 or -1")
        if frames_per_texture < 1:
            raise ValueError("frames_per_texture must be at least 1")

        super().__init__(condition, on_stop)
        self._textures = textures
        self._frames_per_texture = frames_per_texture
        self._direction = direction
        self._count = len(textures)
        self._current_texture_index = 0
        self._frames_on_current_texture = 0

    def apply_effect(self) -> None:
        """Initialize textures on the target sprite(s)."""
        # Reset state
        self._current_texture_index = 0
        self._frames_on_current_texture = 0

        def set_initial_texture(sprite):
            sprite.textures = self._textures
            sprite.texture = self._textures[0]

        self.for_each_sprite(set_initial_texture)

    def update_effect(self, dt: float) -> None:
        """Update texture cycling."""
        # Check if it's time to advance to next texture
        # We check BEFORE incrementing so that:
        # - frames_per_texture=3 means: frame 0,1,2 show texture 0, then frame 3,4,5 show texture 1
        if self._frames_on_current_texture >= self._frames_per_texture:
            # Advance to next texture
            self._current_texture_index = (self._current_texture_index + self._direction) % self._count
            self._frames_on_current_texture = 0

            # Apply new texture
            current_texture = self._textures[self._current_texture_index]

            def set_texture(sprite):
                sprite.texture = current_texture

            self.for_each_sprite(set_texture)

        # Increment frame counter AFTER checking/switching
        self._frames_on_current_texture += 1

    def set_factor(self, factor: float) -> None:
        """Scale both texture cycling speed and duration timing by the given factor.

        Args:
            factor: Scaling factor (0.0 = stopped, 1.0 = normal speed)
        """
        self._factor = factor

    def reset(self) -> None:
        """Reset the action to its initial state."""
        self._elapsed = 0.0
        self._cursor = 0.0
        self.done = False

    def clone(self) -> CycleTexturesUntil:
        """Create a copy of this action."""
        cloned = CycleTexturesUntil(
            textures=self._textures,
            frames_per_texture=self._frames_per_texture,
            direction=self._direction,
            condition=self.condition,
            on_stop=self.on_stop,
        )
        return cloned


class GlowUntil(_Action):
    """Render a Shadertoy-style full-screen effect until a condition is met.

    Dependencies are injected via factory callables for testability.

    Args:
        shadertoy_factory: Callable that receives an (width, height) tuple and
            returns a Shadertoy-like object exposing `program` (dict-like),
            `resize((w, h))` and `render()`.
        condition: Stop condition (see after_frames(), infinite, etc.)
        on_stop: Optional callback when stopping
        uniforms_provider: Optional callable (shader, target) -> dict of uniforms
        get_camera_bottom_left: Optional callable returning (x, y) used to
            convert world-space points such as "lightPosition" into screen-space
        auto_resize: Whether on_resize(width, height) should resize the shader
        draw_order: Placeholder for future composition (not used internally)
    """

    _requires_sprite_target = False

    def __init__(
        self,
        *,
        shadertoy_factory,
        condition,
        on_stop=None,
        uniforms_provider=None,
        get_camera_bottom_left=None,
        auto_resize: bool = True,
        draw_order: str = "after",
    ):
        super().__init__(condition, on_stop)
        self._factory = shadertoy_factory
        self._shader = None
        self._uniforms_provider = uniforms_provider
        self._camera_bottom_left_provider = get_camera_bottom_left
        self._auto_resize = auto_resize
        self._draw_order = draw_order
        self._elapsed = 0.0
        self._duration: float | None = None

    def apply_effect(self) -> None:
        # Initial size is unknown here; pass a sentinel, factory may ignore.
        try:
            self._shader = self._factory((0, 0))
        except Exception as e:
            _debug_log(f"GlowUntil factory failed: {e!r}", action="GlowUntil")
            self._shader = None

        self._duration = None
        self._elapsed = 0.0

    def update_effect(self, delta_time: float) -> None:
        if not self._shader:
            return

        # Simulation-time duration handling first
        if self._duration is not None:
            self._elapsed += delta_time
            if self._elapsed >= self._duration - 1e-9:
                # Stop without rendering this frame
                try:
                    self._complete_action(mark_condition_met=True, callback_payload=None, safe_callback=False)
                except Exception:
                    pass
                return

        # Prepare uniforms
        if self._uniforms_provider:
            try:
                uniforms = self._uniforms_provider(self._shader, self.target)
            except Exception as e:
                _debug_log(f"GlowUntil uniforms_provider failed: {e!r}", action="GlowUntil")
                uniforms = None
            if isinstance(uniforms, dict):
                # Camera correction for common uniform key names
                if self._camera_bottom_left_provider and "lightPosition" in uniforms:
                    try:
                        cam_left, cam_bottom = self._camera_bottom_left_provider()
                        px, py = uniforms["lightPosition"]
                        uniforms["lightPosition"] = (px - cam_left, py - cam_bottom)
                    except Exception:
                        # Best-effort only; leave as-is on failure
                        pass

                for key, value in uniforms.items():
                    self._shader.program[key] = value

        # Render once per update
        try:
            self._shader.render()
        except Exception as e:
            _debug_log(f"GlowUntil render failed: {e!r}", action="GlowUntil")

    # Optional hook from window to propagate resize
    def on_resize(self, width: int, height: int) -> None:
        if self._auto_resize and self._shader and hasattr(self._shader, "resize"):
            try:
                self._shader.resize((width, height))
            except Exception as e:
                _debug_log(f"GlowUntil resize failed: {e!r}", action="GlowUntil")

    def clone(self) -> GlowUntil:
        return GlowUntil(
            shadertoy_factory=self._factory,
            condition=_clone_condition(self.condition),
            on_stop=self.on_stop,
            uniforms_provider=self._uniforms_provider,
            get_camera_bottom_left=self._camera_bottom_left_provider,
            auto_resize=self._auto_resize,
            draw_order=self._draw_order,
        )


class EmitParticlesUntil(_Action):
    """Manage one emitter per sprite, updating position/rotation until a condition.

    Args:
        emitter_factory: Callable receiving the sprite and returning an emitter
            with attributes center_x/center_y/angle and methods update(), destroy().
        anchor: "center" or (dx, dy) offset relative to sprite center.
        follow_rotation: If True, set emitter.angle from sprite.angle each frame.
        start_paused: Reserved for future usage (no-op for now).
        destroy_on_stop: If True, call destroy() on all emitters at stop.
    """

    def __init__(
        self,
        *,
        emitter_factory,
        condition,
        on_stop=None,
        anchor="center",
        follow_rotation: bool = False,
        start_paused: bool = False,
        destroy_on_stop: bool = True,
    ):
        super().__init__(condition, on_stop)
        self._factory = emitter_factory
        self._anchor = anchor
        self._follow_rotation = follow_rotation
        self._start_paused = start_paused
        self._destroy_on_stop = destroy_on_stop

        self._emitters: dict[int, object] = {}
        self._emitters_snapshot: dict[int, object] = {}
        self._elapsed = 0.0
        self._duration: float | None = None

    def apply_effect(self) -> None:
        self._emitters.clear()

        def create_for_sprite(sprite):
            emitter = self._factory(sprite)
            self._emitters[id(sprite)] = emitter

        self.for_each_sprite(create_for_sprite)

        self._duration = None
        self._duration = None
        self._elapsed = 0.0

    def _resolve_anchor(self, sprite) -> tuple[float, float]:
        if isinstance(self._anchor, tuple):
            dx, dy = self._anchor
            return (sprite.center_x + dx, sprite.center_y + dy)
        # Default and string anchors: implement center only for now
        return (sprite.center_x, sprite.center_y)

    def update_effect(self, delta_time: float) -> None:
        # Track elapsed time for duration-based conditions
        if self._duration is not None:
            self._elapsed += delta_time

            # Check if duration has elapsed
            if self._elapsed >= self._duration:
                self._complete_action(remove_effect=True, mark_condition_met=True)
                return

        def update_for_sprite(sprite):
            emitter = self._emitters.get(id(sprite))
            if not emitter:
                return
            x, y = self._resolve_anchor(sprite)
            try:
                emitter.center_x = x
                emitter.center_y = y
                if self._follow_rotation:
                    emitter.angle = sprite.angle
                if hasattr(emitter, "update"):
                    emitter.update()
            except Exception as e:
                _debug_log(f"EmitParticlesUntil update failed: {e!r}", action="EmitParticlesUntil")

        self.for_each_sprite(update_for_sprite)

    def remove_effect(self) -> None:
        # Preserve emitters for tests/diagnostics before cleanup
        self._emitters_snapshot = dict(self._emitters)

        if self._destroy_on_stop:
            for emitter in list(self._emitters.values()):
                try:
                    if hasattr(emitter, "destroy"):
                        emitter.destroy()
                except Exception as e:
                    _debug_log(f"EmitParticlesUntil destroy failed: {e!r}", action="EmitParticlesUntil")
        self._emitters.clear()

    def clone(self) -> EmitParticlesUntil:
        return EmitParticlesUntil(
            emitter_factory=self._factory,
            condition=_clone_condition(self.condition),
            on_stop=self.on_stop,
            anchor=self._anchor,
            follow_rotation=self._follow_rotation,
            start_paused=self._start_paused,
            destroy_on_stop=self._destroy_on_stop,
        )
