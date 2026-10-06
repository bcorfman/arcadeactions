"""
Unit tests for space clutter path caching functionality.

This test suite verifies that cached entry paths produce the same behavior
as the original formation entry system.
"""

from __future__ import annotations

import arcade
import pytest

# Import the required functions and classes
from arcadeactions import (
    arrange_grid,
    create_formation_entry_from_sprites,
)


class MockStarfieldView:
    """Mock version of StarfieldView for testing path caching."""

    def __init__(self):
        self.enemy_list = arcade.SpriteList(lazy=True)
        self.enemy_formation = None
        self.cached_entry_paths = None
        self.background_color = arcade.color.BLACK

        # Constants from space_clutter.py
        self.WINDOW_WIDTH = 720
        self.WINDOW_HEIGHT = 1024
        self.ENEMY_SCALE = 0.5
        self.ENEMY_WIDTH = 128 * self.ENEMY_SCALE
        self.ENEMY_HEIGHT = 128 * self.ENEMY_SCALE
        self.ENEMY_GRID_MARGIN = 80.0

        self.enemy_textures = [
            ":resources:/images/enemies/bee.png",
            ":resources:/images/enemies/fishPink.png",
            ":resources:/images/enemies/fly.png",
            ":resources:/images/enemies/mouse.png",
            ":resources:/images/enemies/slimeBlue.png",
            ":resources:/images/enemies/fishGreen.png",
        ]

    def calculate_centered_grid_layout(
        self, window_width: float, cols: int, sprite_width: float, desired_margin: float
    ) -> tuple[float, float]:
        """Calculate start_x and spacing_x to center a grid with specified margins."""
        if desired_margin <= 0:
            raise ValueError("desired_margin must be greater than 0")

        leftmost_center = desired_margin + sprite_width / 2
        rightmost_center = window_width - desired_margin - sprite_width / 2
        total_center_distance = rightmost_center - leftmost_center

        spacing_x = total_center_distance / (cols - 1)

        if spacing_x < 0:
            spacing_x = (window_width - sprite_width) / (cols - 1)

        start_x = leftmost_center
        return start_x, spacing_x

    def create_enemy_formation(self):
        """Create the enemy formation similar to space_clutter.py."""
        import random

        start_x, spacing_x = self.calculate_centered_grid_layout(
            window_width=self.WINDOW_WIDTH,
            cols=4,
            sprite_width=self.ENEMY_WIDTH,
            desired_margin=self.ENEMY_GRID_MARGIN,
        )

        target_sprites = [arcade.Sprite(random.choice(self.enemy_textures), scale=0.5) for i in range(16)]
        self.enemy_formation = arrange_grid(
            sprites=target_sprites,
            rows=4,
            cols=4,
            start_x=start_x,
            start_y=self.WINDOW_HEIGHT - 400,
            spacing_x=spacing_x,
            spacing_y=self.ENEMY_HEIGHT * 1.5,
            visible=False,
        )
        return self.enemy_formation

    def generate_original_entry_actions(self):
        """Generate original entry actions without caching."""
        formation = self.create_enemy_formation()

        entry_actions = create_formation_entry_from_sprites(
            formation,
            speed=5.0,
            stagger_delay=0.5,
            window_bounds=(0, 0, self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
        )

        return entry_actions

    def cache_entry_paths(self, entry_actions):
        """Cache the entry path data from the first wave."""
        self.cached_entry_paths = []

        for sprite, action, target_index in entry_actions:
            # Extract path data that needs to be cached
            path_data = {
                "spawn_position": (sprite.center_x, sprite.center_y),
                "target_position": (
                    self.enemy_formation[target_index].center_x,
                    self.enemy_formation[target_index].center_y,
                ),
                "target_index": target_index,
                "texture": sprite.texture,
                "scale": sprite.scale,
            }
            self.cached_entry_paths.append(path_data)

    def create_entry_actions_from_cached_paths(self):
        """Create new entry actions using cached path data."""
        if not self.cached_entry_paths:
            raise ValueError("No cached paths available")

        entry_actions = []

        for path_data in self.cached_entry_paths:
            # Create new sprite using cached data
            new_sprite = arcade.Sprite(path_data["texture"], scale=path_data["scale"])
            new_sprite.center_x, new_sprite.center_y = path_data["spawn_position"]
            new_sprite.visible = True
            new_sprite.alpha = 255

            # Calculate velocity to target using the same logic as the original
            spawn_pos = path_data["spawn_position"]
            target_pos = path_data["target_position"]
            speed = 5.0  # Same as original

            # Calculate velocity components
            distance = ((target_pos[0] - spawn_pos[0]) ** 2 + (target_pos[1] - spawn_pos[1]) ** 2) ** 0.5
            if distance > 0:
                velocity_x = (target_pos[0] - spawn_pos[0]) * speed / distance
                velocity_y = (target_pos[1] - spawn_pos[1]) * speed / distance
            else:
                velocity_x = velocity_y = 0

            # Create movement action using the exact same precision condition as the real implementation
            from arcadeactions import MoveUntil
            from arcadeactions.pattern import _create_precision_condition_and_callback

            movement_action = MoveUntil(
                velocity=(velocity_x, velocity_y),
                condition=_create_precision_condition_and_callback(target_pos, new_sprite),
            )

            entry_actions.append((new_sprite, movement_action, path_data["target_index"]))

        return entry_actions


class TestSpaceClutterPathCaching:
    """Test suite for space clutter path caching functionality."""

    def test_path_caching_preserves_spawn_positions(self):
        """Test that cached paths preserve original spawn positions."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Create new actions from cached paths
        cached_actions = view.create_entry_actions_from_cached_paths()

        # Verify same number of sprites
        assert len(cached_actions) == len(original_actions)

        # Verify spawn positions match
        for i, ((orig_sprite, _, _), (cached_sprite, _, _)) in enumerate(
            zip(original_actions, cached_actions, strict=False)
        ):
            assert abs(orig_sprite.center_x - cached_sprite.center_x) < 0.1, f"Sprite {i} spawn X position differs"
            assert abs(orig_sprite.center_y - cached_sprite.center_y) < 0.1, f"Sprite {i} spawn Y position differs"

    def test_path_caching_preserves_target_positions(self):
        """Test that cached paths preserve original target positions."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Verify cached target positions match formation positions
        for i, path_data in enumerate(view.cached_entry_paths):
            formation_sprite = view.enemy_formation[path_data["target_index"]]
            cached_target = path_data["target_position"]

            assert abs(formation_sprite.center_x - cached_target[0]) < 0.1, f"Target X position differs for sprite {i}"
            assert abs(formation_sprite.center_y - cached_target[1]) < 0.1, f"Target Y position differs for sprite {i}"

    def test_path_caching_preserves_sprite_count(self):
        """Test that cached paths maintain the same number of sprites."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()
        original_count = len(original_actions)

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Create new actions from cached paths
        cached_actions = view.create_entry_actions_from_cached_paths()
        cached_count = len(cached_actions)

        assert original_count == cached_count, f"Sprite count changed: original={original_count}, cached={cached_count}"
        assert cached_count == 16, f"Expected 16 sprites in 4x4 grid, got {cached_count}"

    def test_path_caching_preserves_sprite_properties(self):
        """Test that cached paths preserve sprite textures and properties."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Create new actions from cached paths
        cached_actions = view.create_entry_actions_from_cached_paths()

        # Verify sprite properties match
        for i, ((orig_sprite, _, _), (cached_sprite, _, _)) in enumerate(
            zip(original_actions, cached_actions, strict=False)
        ):
            assert orig_sprite.texture == cached_sprite.texture, f"Sprite {i} texture differs"

            # Handle scale comparison (scale might be a tuple or float)
            orig_scale = getattr(orig_sprite, "scale", 1.0)
            cached_scale = getattr(cached_sprite, "scale", 1.0)

            # If scale is a tuple, use the first element for comparison
            if isinstance(orig_scale, tuple):
                orig_scale = orig_scale[0] if orig_scale else 1.0
            if isinstance(cached_scale, tuple):
                cached_scale = cached_scale[0] if cached_scale else 1.0

            assert abs(orig_scale - cached_scale) < 0.01, f"Sprite {i} scale differs: {orig_scale} vs {cached_scale}"

    def test_path_caching_maintains_target_mapping(self):
        """Test that cached paths maintain correct sprite-to-target mapping."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Create new actions from cached paths
        cached_actions = view.create_entry_actions_from_cached_paths()

        # Verify target index mapping
        for i, ((_, _, orig_target_idx), (_, _, cached_target_idx)) in enumerate(
            zip(original_actions, cached_actions, strict=False)
        ):
            assert orig_target_idx == cached_target_idx, (
                f"Sprite {i} target index differs: original={orig_target_idx}, cached={cached_target_idx}"
            )

    def test_cached_paths_can_be_reused_multiple_times(self):
        """Test that cached paths can be used to generate multiple waves."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Create multiple waves from cached paths
        wave1_actions = view.create_entry_actions_from_cached_paths()
        wave2_actions = view.create_entry_actions_from_cached_paths()
        wave3_actions = view.create_entry_actions_from_cached_paths()

        # All waves should have same structure
        assert len(wave1_actions) == len(wave2_actions) == len(wave3_actions)

        # Verify each wave has correct spawn positions
        for wave_actions in [wave1_actions, wave2_actions, wave3_actions]:
            for i, path_data in enumerate(view.cached_entry_paths):
                sprite, _, target_idx = wave_actions[i]
                expected_spawn = path_data["spawn_position"]

                assert abs(sprite.center_x - expected_spawn[0]) < 0.1, "Wave spawn X position differs"
                assert abs(sprite.center_y - expected_spawn[1]) < 0.1, "Wave spawn Y position differs"
                assert target_idx == path_data["target_index"], "Target index differs"

    def test_cache_data_structure_integrity(self):
        """Test that cached path data structure is complete and valid."""
        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Verify cache structure
        assert view.cached_entry_paths is not None, "Cached paths should not be None"
        assert len(view.cached_entry_paths) == 16, f"Expected 16 cached paths, got {len(view.cached_entry_paths)}"

        # Verify each path data entry has required fields
        for i, path_data in enumerate(view.cached_entry_paths):
            assert "spawn_position" in path_data, f"Path {i} missing spawn_position"
            assert "target_position" in path_data, f"Path {i} missing target_position"
            assert "target_index" in path_data, f"Path {i} missing target_index"
            assert "texture" in path_data, f"Path {i} missing texture"
            assert "scale" in path_data, f"Path {i} missing scale"

            # Verify data types
            assert isinstance(path_data["spawn_position"], tuple), f"Path {i} spawn_position not tuple"
            assert isinstance(path_data["target_position"], tuple), f"Path {i} target_position not tuple"
            assert isinstance(path_data["target_index"], int), f"Path {i} target_index not int"
            assert len(path_data["spawn_position"]) == 2, f"Path {i} spawn_position not (x,y) tuple"
            assert len(path_data["target_position"]) == 2, f"Path {i} target_position not (x,y) tuple"

    def test_cached_sprites_stop_at_formation_slots(self):
        """Test that cached sprites actually stop at their formation slots."""
        from arcadeactions import Action

        view = MockStarfieldView()

        # Generate original entry actions
        original_actions = view.generate_original_entry_actions()

        # Cache the paths
        view.cache_entry_paths(original_actions)

        # Create new actions from cached paths
        cached_actions = view.create_entry_actions_from_cached_paths()

        # Create sprite list and apply cached actions
        test_sprite_list = arcade.SpriteList(lazy=True)
        for sprite, action, _ in cached_actions:
            action.apply(sprite, tag="test_entry")
            test_sprite_list.append(sprite)

        # Simulate movement for a reasonable time
        max_frames = 500
        frame_count = 0

        while frame_count < max_frames:
            Action.update_all(1 / 60)  # 60 FPS
            test_sprite_list.update()  # THIS WAS MISSING!
            frame_count += 1

            # Check if all sprites have stopped moving
            all_stopped = True
            moving_count = 0
            for sprite, _, _ in cached_actions:
                if abs(sprite.change_x) > 0.01 or abs(sprite.change_y) > 0.01:
                    all_stopped = False
                    moving_count += 1

            # Debug output every 50 frames
            if frame_count % 50 == 0:
                print(f"Frame {frame_count}: {moving_count} sprites still moving")
                if moving_count <= 3:  # Show details for first few moving sprites
                    for i, (sprite, _, target_index) in enumerate(cached_actions):
                        if abs(sprite.change_x) > 0.01 or abs(sprite.change_y) > 0.01:
                            target_sprite = view.enemy_formation[target_index]
                            distance = (
                                (sprite.center_x - target_sprite.center_x) ** 2
                                + (sprite.center_y - target_sprite.center_y) ** 2
                            ) ** 0.5
                            print(
                                f"  Sprite {i}: pos=({sprite.center_x:.1f}, {sprite.center_y:.1f}), vel=({sprite.change_x:.3f}, {sprite.change_y:.3f}), dist={distance:.2f}"
                            )
                            if i >= 2:  # Show only first 3
                                break

            if all_stopped:
                break

        # Verify that sprites stopped at their target positions
        assert all_stopped, f"Sprites did not stop moving after {frame_count} frames"

        for i, (sprite, _, target_index) in enumerate(cached_actions):
            target_sprite = view.enemy_formation[target_index]
            distance_to_target = (
                (sprite.center_x - target_sprite.center_x) ** 2 + (sprite.center_y - target_sprite.center_y) ** 2
            ) ** 0.5

            assert distance_to_target < 10.0, f"Sprite {i} did not reach target: distance={distance_to_target:.2f}"
            assert abs(sprite.change_x) < 0.01, f"Sprite {i} still has X velocity: {sprite.change_x}"
            assert abs(sprite.change_y) < 0.01, f"Sprite {i} still has Y velocity: {sprite.change_y}"

        print(f"✓ All sprites stopped at formation slots in {frame_count} frames")

    def test_error_handling_when_no_cached_paths(self):
        """Test proper error handling when trying to use paths without caching first."""
        view = MockStarfieldView()

        # Try to create actions without caching first
        with pytest.raises(ValueError, match="No cached paths available"):
            view.create_entry_actions_from_cached_paths()


class MockOptimizedStarfieldView:
    """Mock version of optimized StarfieldView for testing."""

    WINDOW_WIDTH = 720
    WINDOW_HEIGHT = 1024
    ENEMY_SCALE = 0.5
    ENEMY_WIDTH = 128 * ENEMY_SCALE
    ENEMY_HEIGHT = 128 * ENEMY_SCALE
    ENEMY_GRID_MARGIN = 80.0

    def __init__(self):
        self.enemy_formation = None
        self.enemy_list = arcade.SpriteList(lazy=True)
        self.cached_entry_paths = None
        self.cached_actions = None  # Pool of reusable actions
        self.wave_count = 0

    def calculate_centered_grid_layout(self, window_width, cols, sprite_width, desired_margin):
        """Calculate start_x and spacing_x to center a grid with specified margins."""
        leftmost_center = desired_margin + sprite_width / 2
        rightmost_center = window_width - desired_margin - sprite_width / 2
        total_center_distance = rightmost_center - leftmost_center
        spacing_x = total_center_distance / (cols - 1)
        start_x = leftmost_center
        return start_x, spacing_x

    def create_enemy_formation(self):
        """Create the target formation sprites (final positions)."""
        if self.enemy_formation is not None:
            return self.enemy_formation

        enemy_textures = [
            ":resources:images/enemies/bee.png",
            ":resources:images/enemies/fishPink.png",
            ":resources:images/enemies/fly.png",
            ":resources:images/enemies/mouse.png",
            ":resources:images/enemies/slimeBlue.png",
            ":resources:images/enemies/fishGreen.png",
        ]

        start_x, spacing_x = self.calculate_centered_grid_layout(
            window_width=self.WINDOW_WIDTH,
            cols=4,
            sprite_width=self.ENEMY_WIDTH,
            desired_margin=self.ENEMY_GRID_MARGIN,
        )

        target_sprites = [arcade.Sprite(enemy_textures[i % len(enemy_textures)], scale=0.5) for i in range(16)]

        self.enemy_formation = arrange_grid(
            sprites=target_sprites,
            rows=4,
            cols=4,
            start_x=start_x,
            start_y=self.WINDOW_HEIGHT - 400,
            spacing_x=spacing_x,
            spacing_y=self.ENEMY_HEIGHT * 1.5,
            visible=False,
        )

        return self.enemy_formation

    def create_reusable_enemy_sprites(self):
        """Create 16 reusable enemy sprites that will be reset for each wave."""
        if len(self.enemy_list) > 0:
            return  # Already created

        enemy_textures = [
            ":resources:images/enemies/bee.png",
            ":resources:images/enemies/fishPink.png",
            ":resources:images/enemies/fly.png",
            ":resources:images/enemies/mouse.png",
            ":resources:images/enemies/slimeBlue.png",
            ":resources:images/enemies/fishGreen.png",
        ]

        for i in range(16):
            sprite = arcade.Sprite(enemy_textures[i % len(enemy_textures)], scale=0.5)
            self.enemy_list.append(sprite)

    def generate_original_entry_actions(self):
        """Generate original entry actions and cache them."""
        formation = self.create_enemy_formation()

        entry_actions = create_formation_entry_from_sprites(
            formation,
            speed=5.0,
            stagger_delay=0.5,
            window_bounds=(0, 0, self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
        )

        return entry_actions

    def cache_entry_paths_once(self, entry_actions):
        """Cache the entry path data from the first wave only."""
        if self.cached_entry_paths is not None:
            return  # Already cached, don't overwrite

        self.cached_entry_paths = []

        for sprite, action, target_index in entry_actions:
            path_data = {
                "spawn_position": (sprite.center_x, sprite.center_y),
                "target_position": (
                    self.enemy_formation[target_index].center_x,
                    self.enemy_formation[target_index].center_y,
                ),
                "target_index": target_index,
                "texture": sprite.texture,
                "scale": getattr(sprite, "scale", 1.0),
                "velocity": getattr(action, "target_velocity", None),
            }
            self.cached_entry_paths.append(path_data)

    def create_action_pool_once(self):
        """Create reusable action pool from first wave."""
        if self.cached_actions is not None:
            return  # Already created

        if self.cached_entry_paths is None:
            raise ValueError("Must cache entry paths before creating action pool")

        self.cached_actions = []

        for path_data in self.cached_entry_paths:
            # Create a template action that can be reset and reused

            # For pooling, we'll create the action template but assign sprite later
            velocity = path_data["velocity"]
            target_position = path_data["target_position"]

            # Store action template data for later instantiation
            action_template = {
                "velocity": velocity,
                "target_position": target_position,
            }
            self.cached_actions.append(action_template)

    def setup_wave_optimized(self):
        """Setup a new wave using optimizations 1-3."""
        self.wave_count += 1

        # Stop all existing enemy actions for both sprite list and individual sprites
        from arcadeactions import Action, DelayFrames, MoveUntil, repeat, sequence
        from arcadeactions.pattern import create_wave_pattern

        Action.stop_actions_for_target(self.enemy_list, tag="enemy_formation_entry")
        Action.stop_actions_for_target(self.enemy_list, tag="enemy_wave")
        Action.stop_actions_for_target(self.enemy_list, tag="formation_completion_watcher")

        # Also stop actions for individual sprites
        for sprite in self.enemy_list:
            Action.stop_actions_for_target(sprite, tag="enemy_formation_entry")
            Action.stop_actions_for_target(sprite, tag="enemy_wave")
            Action.stop_actions_for_target(sprite, tag="formation_completion_watcher")

        # Create formation and enemy sprites only once
        self.create_enemy_formation()
        self.create_reusable_enemy_sprites()

        # Generate and cache paths only on first wave
        if self.cached_entry_paths is None:
            original_actions = self.generate_original_entry_actions()
            self.cache_entry_paths_once(original_actions)
            self.create_action_pool_once()

        # Reset and reposition existing sprites using cached data
        for i, (sprite, path_data) in enumerate(zip(self.enemy_list, self.cached_entry_paths, strict=False)):
            # Reset sprite state (optimization 1: reuse sprites)
            sprite.center_x, sprite.center_y = path_data["spawn_position"]
            sprite.visible = True
            sprite.alpha = 255
            sprite.change_x = 0
            sprite.change_y = 0

            # Create fresh action from template (optimization 3: action pooling)
            action_template = self.cached_actions[i]
            velocity = action_template["velocity"]
            target_position = action_template["target_position"]

            from arcadeactions.pattern import _create_precision_condition_and_callback

            # Create new action with fresh condition bound to this sprite
            action = MoveUntil(
                velocity=velocity,
                condition=_create_precision_condition_and_callback(target_position, sprite),
            )

            action.apply(sprite, tag="enemy_formation_entry")

        # Setup wave motion watcher (same as before)
        def all_enemies_arrived():
            vel_eps = 0.05
            stable_frames_required = 5

            moving = any(abs(s.change_x) > vel_eps or abs(s.change_y) > vel_eps for s in self.enemy_list)

            if moving:
                all_enemies_arrived._stable = 0
                return False

            all_enemies_arrived._stable = getattr(all_enemies_arrived, "_stable", 0) + 1
            return all_enemies_arrived._stable >= stable_frames_required

        def start_wave_motion():
            quarter_wave = create_wave_pattern(amplitude=30, length=80, speed=80, start_progress=0.75, end_progress=1.0)
            full_wave = create_wave_pattern(amplitude=30, length=80, speed=80)
            repeating_wave = sequence(quarter_wave, repeat(full_wave))
            repeating_wave.apply(self.enemy_list, tag="enemy_wave")

        delay_action = DelayFrames(condition=all_enemies_arrived, on_stop=start_wave_motion)
        if self.enemy_list:
            delay_action.apply(self.enemy_list[0], tag="formation_completion_watcher")


class TestSpaceClutterOptimizations:
    """Test suite for space clutter performance optimizations."""

    def teardown_method(self):
        """Clean up after each test."""
        from arcadeactions import Action

        Action.stop_all()

    def test_sprite_reuse_across_waves(self):
        """Test that sprites are reused instead of recreated across waves."""
        view = MockOptimizedStarfieldView()

        # Setup first wave
        view.setup_wave_optimized()
        first_wave_sprites = list(view.enemy_list)
        first_wave_ids = [id(sprite) for sprite in first_wave_sprites]

        assert len(first_wave_sprites) == 16
        assert view.wave_count == 1

        # Setup second wave
        view.setup_wave_optimized()
        second_wave_sprites = list(view.enemy_list)
        second_wave_ids = [id(sprite) for sprite in second_wave_sprites]

        assert len(second_wave_sprites) == 16
        assert view.wave_count == 2

        # Verify same sprite objects are reused
        assert first_wave_ids == second_wave_ids, "Sprite objects should be reused"

        # Setup third wave
        view.setup_wave_optimized()
        third_wave_sprites = list(view.enemy_list)
        third_wave_ids = [id(sprite) for sprite in third_wave_sprites]

        assert view.wave_count == 3
        assert first_wave_ids == third_wave_ids, "Sprite objects should be reused"

    def test_sprite_state_reset_between_waves(self):
        """Test that sprite state is properly reset between waves."""
        view = MockOptimizedStarfieldView()

        # Setup first wave
        view.setup_wave_optimized()

        # Modify sprite states to simulate mid-game state
        for sprite in view.enemy_list:
            sprite.center_x += 100
            sprite.center_y += 50
            sprite.visible = False
            sprite.alpha = 128
            sprite.change_x = 5
            sprite.change_y = -3

        # Store expected spawn positions from cache
        expected_positions = [path["spawn_position"] for path in view.cached_entry_paths]

        # Setup second wave
        view.setup_wave_optimized()

        # Verify all sprites are reset to proper state
        for i, sprite in enumerate(view.enemy_list):
            expected_x, expected_y = expected_positions[i]
            assert abs(sprite.center_x - expected_x) < 0.1, f"Sprite {i} X not reset properly"
            assert abs(sprite.center_y - expected_y) < 0.1, f"Sprite {i} Y not reset properly"
            assert sprite.visible is True, f"Sprite {i} visibility not reset"
            assert sprite.alpha == 255, f"Sprite {i} alpha not reset"
            # Note: change_x/change_y will be set by the action when it applies,
            # so we just verify they have been assigned some movement velocity
            assert sprite.change_x != 5, f"Sprite {i} change_x should be different from modified state"
            assert sprite.change_y != -3, f"Sprite {i} change_y should be different from modified state"

    def test_cache_persistence_across_waves(self):
        """Test that cache is created once and persists across waves."""
        view = MockOptimizedStarfieldView()

        # Verify no cache initially
        assert view.cached_entry_paths is None
        assert view.cached_actions is None

        # Setup first wave - should create cache
        view.setup_wave_optimized()

        first_cache = view.cached_entry_paths
        first_actions = view.cached_actions

        assert first_cache is not None
        assert first_actions is not None
        assert len(first_cache) == 16
        assert len(first_actions) == 16

        # Setup second wave - should reuse same cache
        view.setup_wave_optimized()

        second_cache = view.cached_entry_paths
        second_actions = view.cached_actions

        # Verify cache objects are identical (not recreated)
        assert first_cache is second_cache, "Cache should not be recreated"
        assert first_actions is second_actions, "Action templates should not be recreated"

        # Setup third wave - verify cache still persists
        view.setup_wave_optimized()

        assert view.cached_entry_paths is first_cache, "Cache should persist"
        assert view.cached_actions is first_actions, "Action templates should persist"

    def test_action_template_pooling(self):
        """Test that action templates are created once and reused."""
        view = MockOptimizedStarfieldView()

        # Setup first wave
        view.setup_wave_optimized()

        # Verify action templates are created
        assert view.cached_actions is not None
        assert len(view.cached_actions) == 16

        # Verify each template has required data
        for i, template in enumerate(view.cached_actions):
            assert "velocity" in template, f"Template {i} missing velocity"
            assert "target_position" in template, f"Template {i} missing target_position"
            assert template["velocity"] is not None, f"Template {i} velocity is None"
            assert template["target_position"] is not None, f"Template {i} target_position is None"

    def test_fresh_actions_created_per_wave(self):
        """Test that fresh action instances are created for each wave."""
        from arcadeactions import Action

        view = MockOptimizedStarfieldView()

        # Setup first wave and collect action instances
        view.setup_wave_optimized()

        first_wave_actions = []
        for sprite in view.enemy_list:
            actions = Action.get_actions_for_target(sprite, tag="enemy_formation_entry")
            first_wave_actions.extend(actions)

        assert len(first_wave_actions) == 16
        first_wave_action_ids = [id(action) for action in first_wave_actions]

        # Setup second wave and collect new action instances
        view.setup_wave_optimized()

        second_wave_actions = []
        for sprite in view.enemy_list:
            actions = Action.get_actions_for_target(sprite, tag="enemy_formation_entry")
            second_wave_actions.extend(actions)

        assert len(second_wave_actions) == 16
        second_wave_action_ids = [id(action) for action in second_wave_actions]

        # Verify different action instances (fresh actions for each wave)
        assert first_wave_action_ids != second_wave_action_ids, "Actions should be fresh instances"

        # But verify they use the same templates/data
        for i in range(16):
            first_action = first_wave_actions[i]
            second_action = second_wave_actions[i]

            # Verify same velocity (from template)
            assert first_action.target_velocity == second_action.target_velocity, (
                f"Action {i} velocity should match template"
            )

    def test_memory_efficiency_multiple_waves(self):
        """Test that multiple waves don't create memory leaks."""
        view = MockOptimizedStarfieldView()

        # Setup many waves to test for memory efficiency
        initial_sprite_count = len(view.enemy_list)

        for wave_num in range(5):
            view.setup_wave_optimized()

            # Verify consistent sprite count (no accumulation)
            assert len(view.enemy_list) == 16, f"Wave {wave_num}: sprite count should remain constant"

            # Verify wave counter increments
            assert view.wave_count == wave_num + 1, f"Wave count should be {wave_num + 1}"

        # Verify final state
        assert len(view.enemy_list) == 16, "Final sprite count should be 16"
        assert view.wave_count == 5, "Should have completed 5 waves"

        # Verify cache remains single instance
        assert view.cached_entry_paths is not None, "Cache should exist"
        assert view.cached_actions is not None, "Action templates should exist"
        assert len(view.cached_entry_paths) == 16, "Cache should have 16 entries"
        assert len(view.cached_actions) == 16, "Should have 16 action templates"

    def test_wave_setup_performance_characteristics(self):
        """Test that wave setup has consistent performance characteristics."""
        import time

        view = MockOptimizedStarfieldView()

        # Measure first wave setup time (includes cache creation)
        start_time = time.time()
        view.setup_wave_optimized()
        first_wave_time = time.time() - start_time

        # Measure subsequent wave setup times (should be faster)
        subsequent_times = []
        for _ in range(3):
            start_time = time.time()
            view.setup_wave_optimized()
            subsequent_time = time.time() - start_time
            subsequent_times.append(subsequent_time)

        # Verify subsequent waves are faster (or at least not slower)
        avg_subsequent_time = sum(subsequent_times) / len(subsequent_times)

        # Allow some variance but subsequent waves should generally be faster
        # since they skip expensive cache creation and sprite allocation
        assert avg_subsequent_time <= first_wave_time * 1.5, (
            f"Subsequent waves ({avg_subsequent_time:.4f}s) should not be much slower than first wave ({first_wave_time:.4f}s)"
        )
