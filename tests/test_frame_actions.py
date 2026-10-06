"""Test suite for frame-based action implementations.

This module tests actions that have been converted to use frame-based timing
instead of wall-clock timing (BlinkUntil, CallbackUntil, TweenUntil, DelayFrames, etc.).
"""

import arcade

from arcadeactions import Action
from tests.conftest import ActionTestBase


class TestBlinkUntilFrames(ActionTestBase):
    """Test suite for frame-based BlinkUntil action."""

    def test_blink_until_frames_basic(self, test_sprite):
        """Test BlinkUntil with frame-based timing."""
        from arcadeactions import blink_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        sprite.visible = True

        # Blink every 3 frames for 10 frames total
        action = blink_until(sprite, frames_until_change=3, condition=after_frames(10), tag="test_blink_frames")

        # Frame 0: visible=True
        assert sprite.visible is True

        # Frames 1-2: still visible
        Action.update_all(0.016)
        assert sprite.visible is True
        Action.update_all(0.016)
        assert sprite.visible is True

        # Frame 3: should toggle to invisible
        Action.update_all(0.016)
        assert sprite.visible is False

        # Frames 4-5: still invisible
        Action.update_all(0.016)
        assert sprite.visible is False
        Action.update_all(0.016)
        assert sprite.visible is False

        # Frame 6: should toggle back to visible
        Action.update_all(0.016)
        assert sprite.visible is True

        # Frames 7-9: continue pattern
        Action.update_all(0.016)  # Frame 7
        assert sprite.visible is True
        Action.update_all(0.016)  # Frame 8
        assert sprite.visible is True
        Action.update_all(0.016)  # Frame 9
        assert sprite.visible is False

        # Frame 10: action should complete
        Action.update_all(0.016)
        assert action.done

    def test_blink_until_frames_with_callbacks(self, test_sprite):
        """Test BlinkUntil frame-based timing with enter/exit callbacks."""
        from arcadeactions import blink_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        sprite.visible = True

        enter_calls = []
        exit_calls = []

        def on_enter(target):
            enter_calls.append(Action.current_frame())

        def on_exit(target):
            exit_calls.append(Action.current_frame())

        action = blink_until(
            sprite,
            frames_until_change=2,
            condition=after_frames(8),
            on_blink_enter=on_enter,
            on_blink_exit=on_exit,
            tag="test_blink_callbacks",
        )

        # Run for 8 frames
        for _ in range(8):
            Action.update_all(0.016)

        # Should have toggled at frames: 2, 4, 6, 8
        # Starting visible, so: exit@2, enter@4, exit@6, enter@8
        assert len(exit_calls) == 2  # Frames 2, 6
        assert len(enter_calls) == 2  # Frames 4, 8
        assert exit_calls == [2, 6]
        assert enter_calls == [4, 8]

    def test_blink_until_frames_sprite_list(self, test_sprite_list):
        """Test BlinkUntil with frame timing on SpriteList."""
        from arcadeactions import blink_until
        from arcadeactions.frame_timing import after_frames

        sprites = test_sprite_list
        for sprite in sprites:
            sprite.visible = True

        action = blink_until(sprites, frames_until_change=2, condition=after_frames(6), tag="test_blink_list")

        # All should start visible
        assert all(s.visible for s in sprites)

        # After 2 frames, all should be invisible
        Action.update_all(0.016)
        Action.update_all(0.016)
        assert all(not s.visible for s in sprites)

        # After 2 more frames, all should be visible again
        Action.update_all(0.016)
        Action.update_all(0.016)
        assert all(s.visible for s in sprites)


class TestCallbackUntilFrames(ActionTestBase):
    """Test suite for frame-based CallbackUntil action."""

    def test_callback_until_every_frame(self, test_sprite):
        """Test CallbackUntil that fires every frame."""
        from arcadeactions import callback_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        call_frames = []

        def record_frame():
            call_frames.append(Action.current_frame())

        action = callback_until(sprite, callback=record_frame, condition=after_frames(5), tag="test_every_frame")

        # Run for 5 frames
        for _ in range(5):
            Action.update_all(0.016)

        # Should have been called every frame (frames 1-5, since callback fires during update)
        assert call_frames == [1, 2, 3, 4, 5]
        assert action.done

    def test_callback_until_frame_interval(self, test_sprite):
        """Test CallbackUntil with frame-based interval."""
        from arcadeactions import callback_until
        from arcadeactions.frame_timing import after_frames, every_frames

        sprite = test_sprite
        call_frames = []

        def record_frame():
            call_frames.append(Action.current_frame())

        # Use every_frames to create interval callback
        interval_callback = every_frames(3, record_frame)

        action = callback_until(
            sprite, callback=interval_callback, condition=after_frames(10), tag="test_frame_interval"
        )

        # Run for 10 frames
        for _ in range(10):
            Action.update_all(0.016)

        # Should have been called at frames: 1, 4, 7, 10 (every_frames fires immediately, then every 3)
        assert call_frames == [1, 4, 7, 10]
        assert action.done

    def test_callback_until_with_target_parameter(self, test_sprite):
        """Test CallbackUntil callback receives target parameter."""
        from arcadeactions import callback_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        received_targets = []

        def callback_with_target(target):
            received_targets.append(target)

        action = callback_until(
            sprite, callback=callback_with_target, condition=after_frames(3), tag="test_target_param"
        )

        # Run for 3 frames
        for _ in range(3):
            Action.update_all(0.016)

        # Should have received sprite 3 times
        assert len(received_targets) == 3
        assert all(t is sprite for t in received_targets)


class TestDelayFrames(ActionTestBase):
    """Test suite for DelayFrames action."""

    def test_delay_frames_stops_after_frames(self, test_sprite):
        """DelayFrames should complete after the configured frame count."""
        from arcadeactions import DelayFrames

        sprite = test_sprite

        callback_called = False

        def on_complete(_info=None):
            nonlocal callback_called
            callback_called = True

        action = DelayFrames(frames=5, on_stop=on_complete)
        action.apply(sprite, tag="test_delay_frames")

        # Run for 4 frames - should not complete
        for _ in range(4):
            Action.update_all(0.016)

        assert not action.done
        assert not callback_called

        # Frame 5 should complete
        Action.update_all(0.016)

        assert action.done
        assert callback_called

    def test_delay_frames_in_sequence(self, test_sprite):
        """DelayFrames should compose cleanly inside sequence()."""
        from arcadeactions import DelayFrames, MoveUntil, sequence
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        sprite.center_x = 100

        # Delay 3 frames, then move for 5 frames
        seq = sequence(DelayFrames(3), MoveUntil(velocity=(10, 0), condition=after_frames(5)))
        seq.apply(sprite, tag="test_delay_sequence")

        # After 3 frames, delay completes and move starts
        # But the move action applies velocity immediately when it starts
        for _ in range(3):
            Action.update_all(0.016)
            sprite.update()

        # Sprite has moved slightly because move action started
        # (delay completes, move starts and applies velocity in same frame)
        assert sprite.center_x >= 100  # Has started moving

        # After 5 more frames of movement (8 total), should have moved ~5 frames worth
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Total movement: ~5-6 frames * 10 px/frame = 50-60 px
        assert 145 <= sprite.center_x <= 165
        assert seq.done


class TestTweenUntilFrames(ActionTestBase):
    """Test suite for frame-based TweenUntil action."""

    def test_tween_until_frames_basic(self, test_sprite):
        """Test TweenUntil with frame-based duration."""
        from arcadeactions import tween_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        sprite.center_x = 0

        # Tween from 0 to 100 over 10 frames
        action = tween_until(
            sprite,
            start_value=0,
            end_value=100,
            property_name="center_x",
            condition=after_frames(10),
            tag="test_tween_frames",
        )

        # After 5 frames, should be at 50 (linear interpolation)
        for _ in range(5):
            Action.update_all(0.016)

        assert 49 <= sprite.center_x <= 51

        # After 10 frames total, should be at 100
        for _ in range(5):
            Action.update_all(0.016)

        assert sprite.center_x == 100
        assert action.done

    def test_tween_until_frames_with_easing(self, test_sprite):
        """Test TweenUntil with frame-based duration and easing."""
        from arcadeactions import easing

        from arcadeactions import tween_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        sprite.center_x = 0

        action = tween_until(
            sprite,
            start_value=0,
            end_value=100,
            property_name="center_x",
            condition=after_frames(10),
            ease_function=easing.ease_in_out,
            tag="test_tween_easing",
        )

        # Run for 10 frames
        for _ in range(10):
            Action.update_all(0.016)

        # Should end at exactly 100 regardless of easing
        assert sprite.center_x == 100
        assert action.done

    def test_tween_until_frames_deterministic(self, test_sprite):
        """Test that TweenUntil is deterministic with varying delta_time."""
        from arcadeactions import tween_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite
        sprite.center_x = 0

        action = tween_until(
            sprite,
            start_value=0,
            end_value=100,
            property_name="center_x",
            condition=after_frames(5),
            tag="test_tween_deterministic",
        )

        # Simulate varying frame times
        delta_times = [0.016, 0.050, 0.016, 0.100, 0.016]

        for dt in delta_times:
            Action.update_all(dt)

        # Should complete after exactly 5 frames and be at 100
        assert action.done
        assert sprite.center_x == 100


class TestEaseFrames(ActionTestBase):
    """Test suite for frame-based Ease wrapper."""

    def test_ease_frames_basic(self, test_sprite):
        """Test Ease wrapper with frame-based duration."""
        from arcadeactions import easing

        from arcadeactions import MoveUntil, ease

        sprite = test_sprite
        sprite.center_x = 100

        # Create move action that runs indefinitely
        from arcadeactions.conditional import infinite

        move = MoveUntil(velocity=(10, 0), condition=infinite)

        # Wrap with ease that lasts 10 frames
        ease_action = ease(sprite, move, frames=10, ease_function=easing.ease_in_out, tag="test_ease_frames")

        # After 5 frames, velocity should be at ~50% (middle of ease_in_out)
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Velocity should be around 5 (50% of 10 px/frame)
        assert 4 <= sprite.change_x <= 6

        # After 10 frames total, easing should complete and move continues at full strength
        for _ in range(5):
            Action.update_all(0.016)
            sprite.update()

        # Velocity should be at full strength now
        assert sprite.change_x == 10

    def test_ease_frames_with_completion_callback(self, test_sprite):
        """Test Ease wrapper completion callback with frames."""
        from arcadeactions import easing

        from arcadeactions import MoveUntil, ease
        from arcadeactions.conditional import infinite

        sprite = test_sprite

        callback_called = False
        callback_frame = None

        def on_complete():
            nonlocal callback_called, callback_frame
            callback_called = True
            callback_frame = Action.current_frame()

        move = MoveUntil(velocity=(10, 0), condition=infinite)
        ease_action = ease(
            sprite, move, frames=5, ease_function=easing.ease_in, on_complete=on_complete, tag="test_ease_callback"
        )

        # Run for 5 frames
        for _ in range(5):
            Action.update_all(0.016)

        # Callback should have been called at frame 5
        assert callback_called
        assert callback_frame == 5


class TestCycleTexturesFrames(ActionTestBase):
    """Test suite for frame-based CycleTexturesUntil action."""

    def test_cycle_textures_frames_basic(self, test_sprite):
        """Test CycleTexturesUntil with frame-based timing."""
        from arcadeactions import cycle_textures_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite

        # Create dummy textures
        textures = [
            arcade.load_texture(":resources:images/items/star.png"),
            arcade.load_texture(":resources:images/items/coinGold.png"),
            arcade.load_texture(":resources:images/items/coinSilver.png"),
        ]

        # Cycle textures every 2 frames for 10 frames
        action = cycle_textures_until(
            sprite, textures=textures, frames_per_texture=2, condition=after_frames(10), tag="test_cycle_frames"
        )

        # Frame 0-1: texture 0
        initial_texture = sprite.texture
        Action.update_all(0.016)
        assert sprite.texture == initial_texture

        # Frame 2-3: texture 1
        Action.update_all(0.016)
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Frame 4-5: texture 2
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Frame 6-7: texture 0 again (wraps)
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Frame 8-9: texture 1
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Frame 10: done
        Action.update_all(0.016)
        assert action.done

    def test_cycle_textures_frames_deterministic(self, test_sprite):
        """Test that texture cycling is deterministic regardless of delta_time."""
        from arcadeactions import cycle_textures_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite

        textures = [
            arcade.load_texture(":resources:images/items/star.png"),
            arcade.load_texture(":resources:images/items/coinGold.png"),
        ]

        action = cycle_textures_until(
            sprite, textures=textures, frames_per_texture=3, condition=after_frames(6), tag="test_cycle_deterministic"
        )

        # Simulate varying frame times
        delta_times = [0.016, 0.050, 0.016, 0.100, 0.016, 0.016]

        texture_sequence = []
        for dt in delta_times:
            Action.update_all(dt)
            texture_sequence.append(sprite.texture)

        # Should have switched textures at frame 3 regardless of delta_time
        assert texture_sequence[0] == texture_sequence[1] == texture_sequence[2]
        assert texture_sequence[3] == texture_sequence[4] == texture_sequence[5]
        assert texture_sequence[0] != texture_sequence[3]


class TestFrameBasedPatterns(ActionTestBase):
    """Test suite for frame-based movement patterns."""

    def test_zigzag_pattern_frames(self, test_sprite):
        """Test zigzag pattern with frame-based timing."""
        from arcadeactions.frame_timing import after_frames
        from arcadeactions.pattern import create_zigzag_pattern

        sprite = test_sprite
        sprite.center_x = 100
        sprite.center_y = 100

        # Create zigzag that completes in specific frame count
        pattern = create_zigzag_pattern(
            width=50,
            height=30,
            velocity=5,  # px per frame
            segments=4,
            condition=after_frames(20),
        )
        pattern.apply(sprite, tag="test_zigzag")

        # Run for 20 frames
        for _ in range(20):
            Action.update_all(0.016)
            sprite.update()

        # Pattern should complete
        assert pattern.done

    def test_bounce_pattern_frames(self, test_sprite):
        """Test bounce pattern with frame-based boundary detection."""
        from arcadeactions.pattern import create_bounce_pattern

        sprite = test_sprite
        sprite.center_x = 100
        sprite.center_y = 300

        bounce_count = 0

        def on_bounce(s, axis, side):
            nonlocal bounce_count
            bounce_count += 1

        # Bounce pattern with frame-based velocity
        pattern = create_bounce_pattern(
            velocity=(10, 0),  # 10 px per frame
            bounds=(0, 0, 400, 600),
            on_boundary_enter=on_bounce,
        )
        pattern.apply(sprite, tag="test_bounce")

        # Run until first bounce (should hit right boundary)
        for _ in range(50):  # Enough frames to hit boundary
            Action.update_all(0.016)
            sprite.update()
            if bounce_count > 0:
                break

        # Should have bounced at least once
        assert bounce_count >= 1
        # Velocity should have reversed
        assert sprite.change_x < 0


class TestFrameTimingEdgeCases(ActionTestBase):
    """Test edge cases for frame-based timing."""

    def test_zero_frame_condition(self, test_sprite):
        """Test action with zero-frame condition completes immediately."""
        from arcadeactions import move_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite

        action = move_until(sprite, velocity=(10, 0), condition=after_frames(0), tag="test_zero_frames")

        # Should complete on first update
        Action.update_all(0.016)
        assert action.done

    def test_negative_frame_condition(self, test_sprite):
        """Test action with negative frame condition completes immediately."""
        from arcadeactions import move_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite

        action = move_until(sprite, velocity=(10, 0), condition=after_frames(-5), tag="test_negative_frames")

        # Should complete on first update
        Action.update_all(0.016)
        assert action.done

    def test_very_large_frame_count(self, test_sprite):
        """Test action with very large frame count."""
        from arcadeactions import move_until
        from arcadeactions.frame_timing import after_frames

        sprite = test_sprite

        action = move_until(sprite, velocity=(1, 0), condition=after_frames(10000), tag="test_large_frames")

        # Run for 100 frames
        for _ in range(100):
            Action.update_all(0.016)

        # Should still be running
        assert not action.done

        # Stop it manually
        action.stop()
        assert action.done
