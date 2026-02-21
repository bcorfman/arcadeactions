"""Testing Guide for arcadeactions

This guide describes how to exercise the frame-driven ArcadeActions test suite.
"""

Testing patterns to follow:
* Individual actions: Use arcade.Sprite fixtures, test with action.apply() and Action.update_all()
* Group actions: Use arcade.SpriteList fixtures, verify actions applied to all sprites in list
* AttackGroup tests: Test formations, lifecycle management, and breakaway behaviors
* Boundary actions: Test edge detection, callback coordination, and movement reversal

# Testing Guide

## Philosophy

ArcadeActions treats `Action.update_all()` as the single metronome. Tests never depend
on wall-clock time; they advance discrete frames and assert on deterministic state.
The suite intentionally stays lean (≈700 tests) so every case either proves core frame
math or provides a smoke/regression check for a helper. When a behavior involves many
permutations (patterns, easing, visualizers) we keep one focused smoke test per
scenario instead of entire matrices.

## Core Fixtures

`tests/conftest.py` exposes shared helpers that keep the global frame counter
consistent:

```python
import pytest
import arcade

from arcadeactions import Action
from arcadeactions.frame_timing import after_frames

class ActionTestBase:
    """Base class for action tests with common setup and teardown."""
    
    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()
        Action._frame_counter = 0  # Keep global frame timer deterministic

@pytest.fixture
def test_sprite() -> arcade.Sprite:
    sprite = arcade.Sprite(":resources:images/items/star.png")
    sprite.center_x = 100
    sprite.center_y = 100
    return sprite

@pytest.fixture
def test_sprite_list() -> arcade.SpriteList:
    """Create a SpriteList with test sprites."""
    sprite_list = arcade.SpriteList()
    sprite1 = arcade.Sprite(":resources:images/items/star.png")
    sprite2 = arcade.Sprite(":resources:images/items/star.png")
    sprite_list.append(sprite1)
    sprite_list.append(sprite2)
    return sprite_list
```

## Basic Action Testing

Test basic action functionality using the global action update system:

```python
from arcadeactions import Action, move_until, rotate_until, infinite
from arcadeactions.frame_timing import after_frames

class TestMoveUntil(ActionTestBase):
    """Test suite for MoveUntil action."""

    def test_move_until_basic(self, test_sprite):
        """Test basic MoveUntil functionality."""
        sprite = test_sprite
        start_x = sprite.center_x

        condition_met = False

        def condition():
            nonlocal condition_met
            return condition_met

        action = move_until(sprite, velocity=(100, 0), condition=condition, tag="test_basic")

        # Update for one frame - sprite should have velocity applied
        Action.update_all(0.016)
        assert sprite.change_x == 100
        assert sprite.change_y == 0

        # Let it move for a bit
        for _ in range(10):
            sprite.update()  # Apply velocity to position
            Action.update_all(0.016)

        assert sprite.center_x > start_x

        # Trigger condition
        condition_met = True
        Action.update_all(0.016)

        # Velocity should be zeroed
        assert sprite.change_x == 0
        assert sprite.change_y == 0
        assert action.done

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
```

## Testing Easing Actions

Test easing functionality that provides smooth acceleration/deceleration for continuous actions:

```python
from arcadeactions import Action, MoveUntil, Ease, infinite
from arcadeactions.frame_timing import seconds_to_frames
from arcade import easing

class TestEase(ActionTestBase):
    """Test suite for Ease wrapper."""

    def test_ease_continuous_movement(self, test_sprite):
        """Test Ease wrapper with continuous movement action."""
        sprite = test_sprite
        
        # Create continuous movement action (never stops on its own)
        continuous_move = MoveUntil((100, 0), infinite)
        easing_wrapper = Ease(continuous_move, frames=seconds_to_frames(2.0), ease_function=easing.ease_in_out)
        
        easing_wrapper.apply(sprite, tag="test_ease")
        
        # Test initial state (should start with reduced velocity)
        Action.update_all(0.016)
        assert 0 < sprite.change_x < 100  # Eased start
        
        # Test mid-easing (should reach full velocity)
        easing_wrapper._elapsed = 1.0  # Halfway through easing
        Action.update_all(0.016)
        assert sprite.change_x == 100  # Full velocity at midpoint
        
        # Test easing completion (action continues at full velocity)
        easing_wrapper._elapsed = 2.0  # Easing complete
        Action.update_all(0.016)
        assert sprite.change_x == 100  # Continues at full velocity
        assert easing_wrapper._easing_complete

    def test_ease_factor_scaling(self, test_sprite):
        """Test that Ease properly scales wrapped action velocity."""
        sprite = test_sprite
        move = MoveUntil((100, 0), infinite)
        ease_action = Ease(move, frames=seconds_to_frames(1.0))
        
        ease_action.apply(sprite, tag="test")
        
        # Test various easing factors
        ease_action.set_factor(0.5)  # Half speed
        Action.update_all(0.016)
        assert sprite.change_x == 50
        
        ease_action.set_factor(1.0)  # Full speed
        Action.update_all(0.016)
        assert sprite.change_x == 100
```

## Testing Action Composition

Test sequences and parallel actions using the current API:

```python
from arcadeactions import Action, sequence, parallel, DelayFrames, MoveUntil, RotateUntil
from arcadeactions.frame_timing import after_frames, seconds_to_frames

class TestSequenceFunction:
    """Test suite for sequence() function."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_sequence_execution_order(self, test_sprite):
        """Test that sequence executes actions in order."""
        sprite = test_sprite
        
        action1 = DelayFrames(frames=seconds_to_frames(0.1))
        action2 = MoveUntil((100, 0), condition=after_frames(seconds_to_frames(0.1)))
        seq = sequence(action1, action2)
        
        seq.apply(sprite, tag="test_sequence")
        
        # First action should be active
        assert seq.current_index == 0
        assert seq.current_action == action1
        
        # After first action completes, second should start
        Action.update_all(0.11)  # Complete first action (frame-driven)
        Action.update_all(0.016) # Start second action
        
        assert seq.current_index == 1
        assert seq.current_action == action2
        assert sprite.change_x == 100

class TestParallelFunction:
    """Test suite for parallel() function."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_parallel_simultaneous_execution(self, test_sprite):
        """Test that parallel actions execute simultaneously."""
        sprite = test_sprite
        
        move_action = MoveUntil((50, 0), condition=after_frames(seconds_to_frames(1.0)))
        rotate_action = RotateUntil(180, condition=after_frames(seconds_to_frames(1.0)))
        par = parallel(move_action, rotate_action)
        
        par.apply(sprite, tag="test_parallel")
        Action.update_all(0.016)
        
        # Both actions should be active simultaneously
        assert sprite.change_x == 50
        assert sprite.change_angle == 180
        assert len(par.sub_actions) == 2
        assert all(action._is_active for action in par.sub_actions)
```

## Testing Axis-Specific Movement Actions

When testing `MoveXUntil` and `MoveYUntil`, it's critical to verify that each action only affects its designated axis and that boundary behaviors work independently:

```python
from arcadeactions import Action, MoveXUntil, MoveYUntil, parallel, infinite

class TestAxisBoundaryBehaviors:
    """Test boundary behaviors for axis-specific actions."""
    
    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()
    
    def test_move_x_until_bounce_behavior(self):
        """Test that MoveXUntil correctly bounces off X-axis boundaries."""
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 300
        
        action = MoveXUntil(
            velocity=(5, 0),
            condition=infinite,
            bounds=(0, 0, 200, 600),
            boundary_behavior="bounce",
        )
        action.apply(sprite)
        
        # Move right towards boundary
        for _ in range(25):
            Action.update_all(1/60)
        
        # Should have bounced and be moving left
        assert sprite.change_x < 0
        assert 0 < sprite.center_x <= 200
    
    def test_move_x_until_preserves_y_velocity(self):
        """Test that MoveXUntil with bounce doesn't affect Y velocity."""
        sprite = arcade.Sprite()
        sprite.center_x = 180
        sprite.center_y = 300
        sprite.change_y = 3  # Pre-existing Y velocity
        
        action = MoveXUntil(
            velocity=(5, 0),
            condition=infinite,
            bounds=(0, 0, 200, 600),
            boundary_behavior="bounce",
        )
        action.apply(sprite)
        
        # Move and bounce
        for _ in range(30):
            Action.update_all(1/60)
        
        # Y velocity should be preserved
        assert sprite.change_y == 3
    
    def test_composed_bounce_behavior(self):
        """Test independent boundary handling in parallel composition."""
        sprite = arcade.Sprite()
        sprite.center_x = 180
        sprite.center_y = 180
        
        x_action = MoveXUntil(
            velocity=(5, 0),
            condition=infinite,
            bounds=(0, 0, 200, 200),
            boundary_behavior="bounce",
        )
        
        y_action = MoveYUntil(
            velocity=(0, 3),
            condition=infinite,
            bounds=(0, 0, 200, 200),
            boundary_behavior="bounce",
        )
        
        composed = parallel(x_action, y_action)
        composed.apply(sprite)
        
        # Run for several bounces
        for _ in range(100):
            Action.update_all(1/60)
        
        # Both axes should bounce independently
        assert 0 <= sprite.center_x <= 200
        assert 0 <= sprite.center_y <= 200
        assert sprite.change_x != 0
        assert sprite.change_y != 0
```

**Key Testing Points for Axis-Specific Actions:**
- Test all boundary behaviors: "bounce", "wrap", "limit"
- Verify that each action only affects its designated axis
- Test composition with `parallel()` to ensure independent boundary handling
- Verify that boundary callbacks only trigger for the correct axis
- Confirm that pre-existing velocities on the non-affected axis are preserved

## Testing Boundary Interactions

Test boundary detection and callbacks using the current edge-triggered API:

```python
from arcadeactions import Action, MoveUntil, infinite

class TestBoundaryCallbacks:
    """Test boundary enter/exit callbacks."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_boundary_enter_callback(self, test_sprite):
        """Test boundary enter event for right boundary."""
        sprite = test_sprite
        sprite.center_x = 195  # Near right boundary
        events = []

        def on_boundary_enter(sprite_obj, axis, side):
            events.append(("enter", axis, side))

        action = MoveUntil(
            velocity=(10, 0),
            condition=infinite,
            bounds=(0, 0, 200, 200),
            boundary_behavior="limit",
            on_boundary_enter=on_boundary_enter,
        )
        action.apply(sprite, tag="test")

        Action.update_all(0.016)
        sprite.update()

        assert len(events) == 1
        assert events[0] == ("enter", "x", "right")

    def test_boundary_enter_exit_cycle(self, test_sprite):
        """Test complete enter/exit cycle."""
        sprite = test_sprite
        sprite.center_x = 195
        events = []
        state = {"velocity": 10}

## Frame Helpers

Every timing assertion uses the primitives from `arcadeactions.frame_timing`:

- `after_frames(n)` returns a condition that completes once at frame `n`.
- `every_frames(n, callback)` wraps a callback that fires on frame multiples.
- `within_frames(start, end)` guards logic that must run only inside a band of frames.

Example assertions from `tests/test_frame_timing.py`:

```python
from arcadeactions import Action, move_until
from arcadeactions.frame_timing import after_frames

        assert len(velocity_calls) == 2  # Called in apply_effect and update_effect
        assert sprite.change_x == 5
        assert sprite.change_y == 0

    def test_velocity_provider_prevents_action_loops(self, test_sprite):
        """Test that velocity_provider prevents per-frame action creation loops."""
        sprite = test_sprite
        call_count = 0

        def velocity_provider():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                return (10, 0)
            else:
                return (0, 0)  # Stop after a few frames

        action = MoveUntil(
            velocity=(0, 0),
            condition=infinite,
            velocity_provider=velocity_provider,
        )
        action.apply(sprite, tag="test")

        initial_action_count = len(Action._active_actions)

        # Run multiple frames
        for _ in range(10):
            Action.update_all(0.016)

        # Should not create additional actions
        assert len(Action._active_actions) == initial_action_count
        assert call_count == 11  # 1 from apply + 10 from updates
```

## Testing Shader and Particle Actions

## OpenGL and Headless CI

Some tests require a real OpenGL context (e.g., windowed rendering). On Windows/macOS CI,
the suite runs in headless mode and stubs `arcade.Window`/`arcade.Text` to avoid GL calls.
Use the shared `require_opengl` fixture (defined in `tests/conftest.py`) to skip tests that
must create real windows or call OpenGL APIs. For OpenGL draw paths in integration tests,
wrap the draw with `_try_opengl_draw` (see `tests/integration/test_visualizer_renderer.py`).

### Testing GlowUntil with Fake Shadertoy

Test shader effects without OpenGL dependencies using fakes:

```python
from arcadeactions import Action, GlowUntil
from arcadeactions.frame_timing import after_frames, seconds_to_frames

class FakeShadertoy:
    """Minimal stand-in for arcade.experimental.Shadertoy."""
    
    def __init__(self, size=(800, 600)):
        self.size = size
        self.program = {}  # Dict-like for uniforms
        self.resize_calls = []
        self.render_calls = 0
    
    def resize(self, size):
        self.size = size
        self.resize_calls.append(size)
    
    def render(self):
        self.render_calls += 1


def test_glow_renders_and_sets_uniforms(test_sprite):
    """Test GlowUntil renders and sets uniforms correctly."""
    fake = FakeShadertoy()
    
    def shader_factory(size):
        return fake
    
    def uniforms_provider(shader, target):
        return {"time": 1.5, "intensity": 0.8}
    
    action = GlowUntil(
        shadertoy_factory=shader_factory,
        condition=after_frames(seconds_to_frames(0.05)),
        uniforms_provider=uniforms_provider,
    )

def test_glow_camera_offset_correction(test_sprite):
    """Test GlowUntil corrects world coords to screen coords."""
    fake = FakeShadertoy()
    
    camera_x, camera_y = 100.0, 50.0
    
    def shader_factory(size):
        return fake
    
    def uniforms_provider(shader, target):
        return {"lightPosition": (400.0, 300.0)}  # World coords
    
    def get_camera_pos():
        return (camera_x, camera_y)
    
    action = GlowUntil(
        shadertoy_factory=shader_factory,
        condition=after_frames(seconds_to_frames(0.05)),
        uniforms_provider=uniforms_provider,
        get_camera_bottom_left=get_camera_pos,
    )
    action.apply(test_sprite)
    
    Action.update_all(0.016)
    
    # Camera offset should be subtracted from world coords
    assert fake.program["lightPosition"] == (300.0, 250.0)  # (400-100, 300-50)
```

### Testing EmitParticlesUntil with Fake Emitters

Test particle emitters without Arcade's particle system:

```python
from arcadeactions import Action, EmitParticlesUntil
from arcadeactions.frame_timing import after_frames, seconds_to_frames

class FakeEmitter:
    """Minimal stand-in for arcade particle emitters."""
    
    def __init__(self):
        self.center_x = 0.0
        self.center_y = 0.0
        self.angle = 0.0
        self.update_calls = 0
        self.destroy_calls = 0
    
    def update(self):
        self.update_calls += 1
    
    def destroy(self):
        self.destroy_calls += 1

    assert not action.done
    assert test_sprite.center_x == 140  # 4 frames of motion

def test_emitter_per_sprite_follows_position(test_sprite_list):
    """Test EmitParticlesUntil creates and updates emitters per sprite."""
    
    def emitter_factory(sprite):
        return FakeEmitter()
    
    action = EmitParticlesUntil(
        emitter_factory=emitter_factory,
        condition=after_frames(seconds_to_frames(0.05)),
        anchor="center",
        follow_rotation=False,
    )
    action.apply(test_sprite_list)
    
    # Verify one emitter per sprite
    assert len(action._emitters) == len(test_sprite_list)
    
    # Update a few times
    Action.update_all(0.016)
    Action.update_all(0.016)
    
    # Verify emitters follow sprite positions
    for sprite in test_sprite_list:
        emitter = action._emitters[id(sprite)]
        assert emitter.center_x == sprite.center_x
        assert emitter.center_y == sprite.center_y
        assert emitter.update_calls >= 1
    
    # Complete and verify cleanup
    Action.update_all(0.06)
    for sprite in test_sprite_list:
        emitter = action._emitters_snapshot[id(sprite)]
        assert emitter.destroy_calls == 1
    assert action.done


def test_emitter_follows_rotation(test_sprite):
    """Test EmitParticlesUntil updates emitter angle when follow_rotation=True."""
    test_sprite.angle = 45.0
    
    def emitter_factory(sprite):
        return FakeEmitter()
    
    action = EmitParticlesUntil(
        emitter_factory=emitter_factory,
        condition=after_frames(seconds_to_frames(0.05)),
        anchor="center",
        follow_rotation=True,
    )
    action.apply(test_sprite)
    
    Action.update_all(0.016)
    
    emitter = next(iter(action._emitters.values()))
    assert emitter.angle == 45.0
    
    # Change sprite angle
    test_sprite.angle = 90.0
    Action.update_all(0.016)
    
    assert emitter.angle == 90.0


def test_custom_anchor_offset(test_sprite):
    """Test EmitParticlesUntil with custom anchor offset."""
    test_sprite.center_x = 200
    test_sprite.center_y = 300
    
    offset = (5.0, -3.0)
    
    def emitter_factory(sprite):
        return FakeEmitter()
    
    action = EmitParticlesUntil(
        emitter_factory=emitter_factory,
        condition=after_frames(seconds_to_frames(0.02)),
        anchor=offset,
    )
    action.apply(test_sprite)
    
    Action.update_all(0.016)
    
    emitter = next(iter(action._emitters.values()))
    assert emitter.center_x == test_sprite.center_x + offset[0]
    assert emitter.center_y == test_sprite.center_y + offset[1]
```

## Composition Tests

Sequence and parallel helpers are validated with the same primitives.
`tests/test_composite.py` uses short frame windows to prove ordering rather than
sleeping:

```python
from arcadeactions import Action, blink_until, infinite
from arcadeactions.frame_timing import after_frames, seconds_to_frames

class TestBlinkUntilCallbacks:
    """Test BlinkUntil visibility callback functionality."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()

    def test_blink_visibility_callbacks_basic(self, test_sprite):
        """Test basic on_blink_enter and on_blink_exit callback functionality."""
        sprite = test_sprite
        sprite.visible = True  # Start visible
        
        enter_calls = []
        exit_calls = []
        
        def on_enter(sprite_arg):
            enter_calls.append(sprite_arg)
            
        def on_exit(sprite_arg):
            exit_calls.append(sprite_arg)

        action = blink_until(
            sprite,
            seconds_until_change=0.05,
            condition=infinite,
            on_blink_enter=on_enter,
            on_blink_exit=on_exit,
            tag="test_callbacks"
        )

        # Initial state - sprite visible, no callbacks yet
        assert sprite.visible
        assert len(enter_calls) == 0
        assert len(exit_calls) == 0

        # First blink (to invisible) - exit callback
        Action.update_all(0.06)  # More than 0.05 seconds
        assert not sprite.visible
        assert len(exit_calls) == 1
        assert exit_calls[0] == sprite
        assert len(enter_calls) == 0

        # Second blink (back to visible) - enter callback
        Action.update_all(0.06)
        assert sprite.visible
        assert len(enter_calls) == 1
        assert enter_calls[0] == sprite
        assert len(exit_calls) == 1

    def test_blink_edge_triggered_callbacks(self, test_sprite):
        """Test that callbacks are edge-triggered (only fire on state changes)."""
        sprite = test_sprite
        sprite.visible = True
        
        callback_count = {"enter": 0, "exit": 0}
        
        def count_enter(sprite_arg):
            callback_count["enter"] += 1
            
        def count_exit(sprite_arg):
            callback_count["exit"] += 1

        action = blink_until(
            sprite,
            seconds_until_change=0.05,
            condition=infinite,
            on_blink_enter=count_enter,
            on_blink_exit=count_exit,
            tag="test_edge_triggered"
        )

        # Multiple updates within same blink period - no callbacks
        for _ in range(3):
            Action.update_all(0.01)  # Less than 0.05 threshold
        
        assert callback_count["enter"] == 0
        assert callback_count["exit"] == 0
        assert sprite.visible  # Still visible

        # Cross threshold to invisible - one exit callback
        Action.update_all(0.03)  # Total now > 0.05
        assert callback_count["exit"] == 1
        assert callback_count["enter"] == 0
        assert not sprite.visible

        # Multiple updates while invisible - no additional callbacks
        for _ in range(3):
            Action.update_all(0.01)
        assert callback_count["exit"] == 1  # Still just one
        assert callback_count["enter"] == 0

    def test_blink_callback_exception_safety(self, test_sprite):
        """Test that callback exceptions don't break blinking system."""
        sprite = test_sprite
        sprite.visible = True
        
        def failing_enter(sprite_arg):
            raise RuntimeError("Enter callback failed!")
            
        def failing_exit(sprite_arg):
            raise RuntimeError("Exit callback failed!")

        action = blink_until(
            sprite,
            seconds_until_change=0.05,
            condition=infinite,
            on_blink_enter=failing_enter,
            on_blink_exit=failing_exit,
            tag="test_exception_handling"
        )

        # Should not crash despite callback exceptions
        Action.update_all(0.06)  # Trigger exit callback exception
        assert not sprite.visible
        
        Action.update_all(0.06)  # Trigger enter callback exception  
        assert sprite.visible
        
        # Blinking should continue working normally
        Action.update_all(0.06)
        assert not sprite.visible

    def test_blink_sprite_list_callbacks(self, test_sprite_list):
        """Test BlinkUntil callbacks work with sprite lists."""
        sprite_list = test_sprite_list
        for sprite in sprite_list:
            sprite.visible = True
            
        callback_sprites = {"enter": [], "exit": []}
        
        def track_enter(sprite_arg):
            callback_sprites["enter"].append(sprite_arg)
            
        def track_exit(sprite_arg):
            callback_sprites["exit"].append(sprite_arg)

        action = blink_until(
            sprite_list,
            seconds_until_change=0.05,
            condition=infinite,
            on_blink_enter=track_enter,
            on_blink_exit=track_exit,
            tag="test_sprite_list_callbacks"
        )

        # First blink (all go invisible) - exit callbacks for each sprite
        Action.update_all(0.06)
        for sprite in sprite_list:
            assert not sprite.visible
            assert sprite in callback_sprites["exit"]
        assert len(callback_sprites["exit"]) == len(sprite_list)
        assert len(callback_sprites["enter"]) == 0

        # Second blink (all go visible) - enter callbacks for each sprite
        Action.update_all(0.06)
        for sprite in sprite_list:
            assert sprite.visible
            assert sprite in callback_sprites["enter"]
        assert len(callback_sprites["enter"]) == len(sprite_list)

    def test_blink_collision_management_pattern(self, test_sprite):
        """Test real-world collision management pattern with BlinkUntil."""
        sprite = test_sprite
        sprite.visible = True
        
        # Simulate collision sprite list
        collision_sprites = []
        
        def enable_collisions(sprite_obj):
            """Add sprite to collision detection when visible."""
            if sprite_obj not in collision_sprites:
                collision_sprites.append(sprite_obj)
                sprite_obj.can_collide = True
                
        def disable_collisions(sprite_obj):
            """Remove sprite from collision detection when invisible."""
            if sprite_obj in collision_sprites:
                collision_sprites.remove(sprite_obj)
                sprite_obj.can_collide = False

        action = blink_until(
            sprite,
            seconds_until_change=0.1,
            condition=after_frames(seconds_to_frames(1.0)),
            on_blink_enter=enable_collisions,
            on_blink_exit=disable_collisions,
            tag="invulnerability_blink"
        )

        # Initially visible - should be in collision detection
        assert sprite.visible
        assert sprite in collision_sprites
        assert sprite.can_collide

        # Blink to invisible - should be removed from collision detection
        Action.update_all(0.11)
        assert not sprite.visible
        assert sprite not in collision_sprites
        assert not sprite.can_collide

        # Blink back to visible - should be re-added to collision detection
        Action.update_all(0.11)
        assert sprite.visible
        assert sprite in collision_sprites
        assert sprite.can_collide

    def test_blink_partial_callbacks(self, test_sprite):
        """Test BlinkUntil with only one callback (enter or exit)."""
        sprite = test_sprite
        sprite.visible = True
        
        enter_calls = []
        
        def on_enter(sprite_arg):
            enter_calls.append(sprite_arg)

        # Test with only enter callback
        action = blink_until(
            sprite,
            seconds_until_change=0.05,
            condition=infinite,
            on_blink_enter=on_enter,  # Only enter callback
            tag="test_only_enter"
        )

        # Go invisible (no callback)
        Action.update_all(0.06)
        assert not sprite.visible
        assert len(enter_calls) == 0
        
        # Go visible (enter callback)
        Action.update_all(0.06)
        assert sprite.visible
        assert len(enter_calls) == 1
```

## Testing Formation Functions

Test formation functions for proper sprite positioning:

```python
from arcadeactions import arrange_triangle, arrange_hexagonal_grid, arrange_arc, arrange_concentric_rings, arrange_cross, arrange_arrow

def test_formation_positioning():
    # Test triangle formation
    triangle = arrange_triangle(count=6, apex_x=400, apex_y=500, row_spacing=50, lateral_spacing=60)
    assert len(triangle) == 6
    assert triangle[0].center_x == 400  # Apex
    assert triangle[0].center_y == 500
    
    # Test hexagonal grid
    hex_grid = arrange_hexagonal_grid(rows=2, cols=3, start_x=100, start_y=200, spacing=50)
    assert len(hex_grid) == 6
    assert hex_grid[0].center_x == 100  # First sprite
    
    # Test arc formation
    arc = arrange_arc(count=5, center_x=400, center_y=300, radius=100, start_angle=0, end_angle=180)
    assert len(arc) == 5
    # Verify sprites are at correct distance from center
    for sprite in arc:
        distance = math.hypot(sprite.center_x - 400, sprite.center_y - 300)
        assert abs(distance - 100) < 0.1
    
    # Test concentric rings
    rings = arrange_concentric_rings(radii=[50, 100], sprites_per_ring=[4, 8], center_x=300, center_y=300)
    assert len(rings) == 12  # 4 + 8
    
    # Test cross formation
    cross = arrange_cross(count=9, center_x=400, center_y=300, arm_length=80, spacing=40)
    assert len(cross) == 9
    assert cross[0].center_x == 400  # Center sprite
    assert cross[0].center_y == 300
    
    # Test arrow formation
    arrow = arrange_arrow(count=7, tip_x=400, tip_y=500, rows=3, spacing_along=50, spacing_outward=40)
    assert len(arrow) == 7
    assert arrow[0].center_x == 400  # Tip sprite
    assert arrow[0].center_y == 500

    # Zero-allocation: arrange existing sprites
    sprites = [arcade.Sprite(":resources:images/items/star.png") for _ in range(9)]
    v_formation = arrange_v_formation(sprites, apex_x=400, apex_y=300, spacing=50)
    assert len(v_formation) == 9

    # Grid rule: len(sprites) must equal rows * cols
    sprites = [arcade.Sprite(":resources:images/items/star.png") for _ in range(6)]
    grid = arrange_grid(sprites, rows=2, cols=3, start_x=100, start_y=100)
    assert len(grid) == 6

def test_formation_visibility():
    # Test that formations respect visibility parameter
    invisible_triangle = arrange_triangle(count=6, apex_x=100, apex_y=100, visible=False)
    for sprite in invisible_triangle:
        assert not sprite.visible
    
    visible_triangle = arrange_triangle(count=6, apex_x=100, apex_y=100, visible=True)
    for sprite in visible_triangle:
        assert sprite.visible

def test_formation_parameter_validation():
    # Test parameter validation
    with pytest.raises(ValueError):
        arrange_triangle(count=-1, apex_x=100, apex_y=100)
    
    with pytest.raises(ValueError):
        arrange_arc(count=5, center_x=100, center_y=100, radius=50, start_angle=180, end_angle=90)
    
    with pytest.raises(ValueError):
        arrange_concentric_rings(radii=[50, 100], sprites_per_ring=[4])  # Mismatched lengths
```

## Testing Best Practices

    seq.apply(test_sprite, tag="sequence-smoke")
    for _ in range(3):  # finish delay
        Action.update_all(1 / 60)

    assert seq.current_index == 1
    assert test_sprite.change_x == 5
```

2. **Test action lifecycle with global update system:**
```python
def test_action_lifecycle(self, test_sprite):
    sprite = test_sprite
    action = move_until(
        sprite,
        velocity=(5, 0),
        condition=after_frames(seconds_to_frames(1.0)),
        tag="test",
    )
    
    # Test initial state
    assert not action.done
    assert sprite.change_x == 0
    
    # Test after global update
    Action.update_all(0.016)
    assert sprite.change_x == 5
    assert action._is_active
    
    # Test completion
    action.stop()
    assert action.done
    assert sprite.change_x == 0  # Cleaned up
```

3. **Test edge cases and error handling:**
```python
def test_invalid_parameters(self, test_sprite):
    sprite = test_sprite
    
    # Test invalid velocity tuple
    with pytest.raises(ValueError):
        MoveUntil(velocity=(1,), condition=infinite)  # Wrong length
    
    # Test invalid frame count
    with pytest.raises(ValueError):
        Ease(MoveUntil((5, 0), infinite), frames=0)
```

- `tests/test_frame_actions.py` covers `BlinkUntil`, `CallbackUntil`, `DelayFrames`,
  `Ease`, `TweenUntil`, and `CycleTexturesUntil` using explicit frame counts.
- `tests/test_frame_timing.py` exercises the primitives themselves along with
  `Action.current_frame()` semantics, including pause behavior.
- `tests/test_pattern_smoke.py` keeps a single regression test per pattern factory
  (`create_zigzag_pattern`, `create_wave_pattern`, `create_spiral_pattern`,
  `create_bounce_pattern`). These smoke tests verify the frame-first parameters
  (`velocity`, `width`, `height`, `after_frames`) without re-running the large matrix
  from the legacy suite.
- `tests/test_ease_smoke.py` replaces the legacy easing battery with a minimal check
  that guarantees easing curves read `frames_completed / total_frames`.

## Testing DevVisualizer Components

DevVisualizer components follow the same testing patterns as core actions, with emphasis on edit mode behavior and data flow validation.

### Testing Prototype Registry

Test prototype registration and instantiation:

```python
from arcadeactions.dev.prototype_registry import SpritePrototypeRegistry, DevContext
import arcade

def test_prototype_registry():
    registry = SpritePrototypeRegistry()
    ctx = DevContext()
    
    @registry.register("test_sprite")
    def make_test(ctx):
        sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.RED)
        sprite._prototype_id = "test_sprite"
        return sprite
    
    assert registry.has("test_sprite")
    sprite = registry.create("test_sprite", ctx)
    assert sprite._prototype_id == "test_sprite"
```

### Testing Selection Manager

Test multi-selection behavior:

```python
from arcadeactions.dev.selection import SelectionManager
import arcade

def test_marquee_selection(window):
    scene_sprites = arcade.SpriteList()
    # Create sprites in a grid
    for i in range(3):
        sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.WHITE)
        sprite.center_x = 100 + i * 50
        sprite.center_y = 100
        scene_sprites.append(sprite)
    
    manager = SelectionManager(scene_sprites)
    
    # Drag marquee
    manager.handle_mouse_press(75, 75, False)
    manager.handle_mouse_drag(175, 175)
    manager.handle_mouse_release(175, 175)
    
    selected = manager.get_selected()
    assert len(selected) >= 2  # Should select multiple sprites
```

### Testing Preset Library

Test preset registration and action creation:

```python
from arcadeactions.dev.presets import ActionPresetRegistry
from arcadeactions.conditional import infinite

def test_preset_creation():
    registry = ActionPresetRegistry()
    
    @registry.register("test_preset", category="Movement", params={"speed": 3})
    def make_preset(ctx, speed):
        from arcadeactions.helpers import move_until
        return move_until(None, velocity=(-speed, 0), condition=infinite)
    
    ctx = type("Context", (), {})()  # Mock context
    action = registry.create("test_preset", ctx, speed=3)
    
    assert action.target_velocity == (-3, 0)
```

### Testing Boundary Gizmos

Test gizmo detection and bounds editing:

```python
from arcadeactions.dev.boundary_overlay import BoundaryGizmo
from arcadeactions.conditional import MoveUntil, infinite

def test_gizmo_bounds_editing(window):
    sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.RED)
    
    action = MoveUntil(
        velocity=(5, 0),
        condition=infinite,
        bounds=(0, 0, 800, 600),
        boundary_behavior="limit",
    )
    action.apply(sprite, tag="movement")
    
    gizmo = BoundaryGizmo(sprite)
    assert gizmo.has_bounded_action()
    
    # Find top handle and drag it
    handles = gizmo.get_handles()
    top_handle = next(h for h in handles if "top" in h.handle_type)
    
    original_top = action.bounds[3]
    gizmo.handle_drag(top_handle, 0, -20)
    
    assert action.bounds[3] == original_top - 20
```

### Testing YAML Round-Trip

Test export/import maintains all data:

```python
from arcadeactions.dev import export_template, load_scene_template, DevContext
import tempfile
import os

def test_yaml_roundtrip(window):
    scene_sprites = arcade.SpriteList()
    
    # Register prototype
    @register_prototype("test_sprite")
    def make_test(ctx):
        sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.GREEN)
        sprite._prototype_id = "test_sprite"
        return sprite
    
    # Create sprite with action config
    ctx = DevContext(scene_sprites=scene_sprites)
    sprite = get_registry().create("test_sprite", ctx)
    sprite.center_x = 500
    sprite.center_y = 600
    sprite._action_configs = [{"preset": "test_preset", "params": {"speed": 7}}]
    scene_sprites.append(sprite)
    
    # Export
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = f.name
    
    try:
        export_template(scene_sprites, temp_path, prompt_user=False)
        
        # Clear and reimport
        scene_sprites.clear()
        load_scene_template(temp_path, ctx)
        
        # Verify round-trip
        assert len(scene_sprites) == 1
        loaded = scene_sprites[0]
        assert loaded._prototype_id == "test_sprite"
        assert loaded.center_x == 500
        assert loaded.center_y == 600
        assert len(loaded._action_configs) == 1
        assert loaded._action_configs[0]["params"]["speed"] == 7
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
```

### Testing Code Sync and Position Tagging

Test code sync functionality for updating source files:

```python
from arcadeactions.dev import sync
from arcadeactions.dev.position_tag import tag_sprite, get_sprites_for
from pathlib import Path
import tempfile

def test_position_tagging():
    sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.RED)
    tag_sprite(sprite, "test_sprite")
    
    # Verify sprite is in registry
    sprites = get_sprites_for("test_sprite")
    assert sprite in sprites
    
    # Verify sprite has _position_id attribute
    assert hasattr(sprite, "_position_id")
    assert sprite._position_id == "test_sprite"

def test_sync_position_assignment():
    # Create temporary source file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("sprite.left = 100\n")
        temp_path = Path(f.name)
    
    try:
        # Update assignment
        result = sync.update_position_assignment(
            temp_path, "sprite", "left", "200"
        )
        
        assert result.changed
        assert result.backup is not None
        
        # Verify source updated
        updated = temp_path.read_text()
        assert "sprite.left = 200" in updated
    finally:
        temp_path.unlink(missing_ok=True)
        if result.backup:
            result.backup.unlink(missing_ok=True)

def test_sync_arrange_call():
    # Create temporary source file with arrange_grid call
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("arrange_grid(rows=3, cols=5, start_x=100, start_y=200)\n")
        temp_path = Path(f.name)
    
    try:
        # Update start_x parameter
        result = sync.update_arrange_call(temp_path, 1, "start_x", "150")
        
        assert result.changed
        updated = temp_path.read_text()
        assert "start_x=150" in updated
    finally:
        temp_path.unlink(missing_ok=True)
        if result.backup:
            result.backup.unlink(missing_ok=True)
```

### Testing Code Parser

Test code parsing for position assignments and arrange calls:

```python
from arcadeactions.dev.code_parser import parse_source, PositionAssignment, ArrangeCall

def test_code_parser():
    source = """
sprite.left = 100
sprite.center_x = 200
arrange_grid(rows=3, cols=5, start_x=100, start_y=200)
"""
    
    assignments, arrange_calls = parse_source(source, "test.py")
    
    # Verify position assignments
    assert len(assignments) == 2
    assert assignments[0].attr == "left"
    assert assignments[0].value_src == "100"
    assert assignments[1].attr == "center_x"
    assert assignments[1].value_src == "200"
    
    # Verify arrange calls
    assert len(arrange_calls) == 1
    assert arrange_calls[0].kwargs["rows"] == "3"
    assert arrange_calls[0].kwargs["cols"] == "5"
    assert arrange_calls[0].kwargs["start_x"] == "100"
    assert arrange_calls[0].kwargs["start_y"] == "200"
```

### Key Testing Principles for DevVisualizer

1. **Edit Mode Validation**: Always verify actions are stored as metadata (`_action_configs`), not running
2. **Dependency Injection**: Test components with injected dependencies (registries, contexts)
3. **Round-Trip Testing**: Export → import → verify for serialization components
4. **Isolation**: Each component test should be independent and fast
5. **No Action Execution**: DevVisualizer tests should never call `Action.update_all()` - actions are metadata only
6. **Code Sync Testing**: Use temporary files for code sync tests, clean up backups
7. **Position Tagging**: Verify registry consistency and attribute presence

## Writing New Tests

1. **Drive behavior with frames.** Iteratively call `Action.update_all(1/60)` (or
   `Action.update_all(0)` if you only need to advance bookkeeping) and assert when the
   boundary frame hits.
2. **Favor smoke coverage for helpers.** If a helper accepts multiple optional flags,
   choose the most representative combination. Public API samples cover the rest, so
   the suite remains lean.
3. **Reset external state.** Any test that mutates globals beyond the Action system
   should patch or monkeypatch within the test and restore the previous value.
4. **Validate pause safety.** When testing pause/resume, wrap `Action.pause_all()` and
   `Action.resume_all()` inside the frame loop and assert `Action.current_frame()`
   advances only when updates run.

## Running the Suite

Always invoke tests through uv to ensure the managed environment is active:

5. **Testing action cleanup:**
```python
def test_action_cleanup(self, test_sprite):
    sprite = test_sprite
    action = MoveUntil((5, 0), condition=after_frames(seconds_to_frames(0.1)))
    action.apply(sprite, tag="test")
    
    initial_count = len(Action._active_actions)
    
    # Run until completion
    Action.update_all(0.11)  # Exceed target frame window
    
    # Action should be automatically removed
    assert len(Action._active_actions) < initial_count
    assert action.done
    assert sprite.change_x == 0  # Velocity cleared
```

Use `-k` filters or direct paths for faster iterations:

```bash
uv run python -m pytest tests/test_frame_timing.py -k after_frames
```

### Coverage Gate (CI)

Coverage on historical code paths is still being raised incrementally. To prevent new
refactors from regressing test quality, CI enforces **>=90% diff coverage** on pull
requests (changed lines only):

```bash
uv run pytest tests/ --cov=arcadeactions --cov-report=xml
uv run diff-cover coverage.xml --compare-branch=origin/main --fail-under=90
```

This gives an immediate quality floor for new code while the legacy baseline is
improved in parallel.

## Troubleshooting

- **Action counter drift:** confirm your test or fixture resets `Action._frame_counter`
  before and after execution.
- **Arcade resources:** when instantiating sprites in tight loops, create them with
  `arcade.SpriteSolidColor` to bypass texture IO.
- **Long-running sequences:** prefer `after_frames` conditions instead of explicit
  loops inside actions. This keeps assertions readable and gives the debugger
  deterministic stepping behavior.

The suite must remain deterministic under debugger pause/step. When adding new tests,
verify they complete successfully when breakpoints interrupt `Action.update_all()` so
the frame-based API remains intuitive during debugging.
