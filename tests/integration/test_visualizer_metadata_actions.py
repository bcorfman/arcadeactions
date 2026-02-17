"""Integration tests for DevVisualizer metadata action application."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.visualizer import DevVisualizer, SpriteWithActionConfigs


@pytest.fixture
def dev_visualizer(window):
    """Create a DevVisualizer instance for testing."""
    scene_sprites = arcade.SpriteList()
    dev_viz = DevVisualizer(scene_sprites=scene_sprites, window=window)
    return dev_viz


@pytest.fixture
def sprite_with_configs(test_sprite):
    """Create a sprite with _action_configs attribute."""
    test_sprite._action_configs = []
    return test_sprite


class TestApplyMetadataActionsPreset:
    """Test preset-based action application."""

    def test_apply_metadata_actions_with_preset(self, dev_visualizer, sprite_with_configs, mocker):
        """Test preset resolution and application."""
        mock_registry = mocker.MagicMock()
        mock_preset_action = mocker.MagicMock()
        mock_registry.create.return_value = mock_preset_action
        mocker.patch("arcadeactions.dev.get_preset_registry", return_value=mock_registry)

        sprite_with_configs._action_configs = [{"preset": "test_preset", "params": {"speed": 5}}]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_registry.create.assert_called_once_with("test_preset", dev_visualizer.ctx, speed=5)
        mock_preset_action.apply.assert_called_once_with(sprite_with_configs)


class TestApplyMetadataActionsActionTypes:
    """Test different action types in apply_metadata_actions."""

    def test_apply_metadata_actions_move_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test MoveUntil action type."""
        mock_move_until = mocker.patch("arcadeactions.move_until")

        sprite_with_configs._action_configs = [
            {
                "action_type": "MoveUntil",
                "velocity": (5, 0),
                "condition": "infinite",
                "bounds": (0, 0, 800, 600),
            }
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_move_until.assert_called_once()
        call_kwargs = mock_move_until.call_args[1]
        assert call_kwargs["velocity"] == (5, 0)
        assert call_kwargs["bounds"] == (0, 0, 800, 600)

    def test_apply_metadata_actions_follow_path_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test FollowPathUntil action type."""
        mock_follow_path = mocker.patch("arcadeactions.follow_path_until")

        sprite_with_configs._action_configs = [
            {
                "action_type": "FollowPathUntil",
                "control_points": [(0, 0), (100, 100), (200, 0)],
                "velocity": 50,
                "condition": "infinite",
            }
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_follow_path.assert_called_once()
        call_kwargs = mock_follow_path.call_args[1]
        assert call_kwargs["control_points"] == [(0, 0), (100, 100), (200, 0)]
        assert call_kwargs["velocity"] == 50

    def test_apply_metadata_actions_cycle_textures_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test CycleTexturesUntil action type."""
        mock_cycle = mocker.patch("arcadeactions.cycle_textures_until")

        textures = [arcade.SpriteSolidColor(32, 32, arcade.color.RED)]
        sprite_with_configs._action_configs = [
            {
                "action_type": "CycleTexturesUntil",
                "textures": textures,
                "frames_per_texture": 5,
                "condition": "infinite",
            }
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_cycle.assert_called_once()
        call_kwargs = mock_cycle.call_args[1]
        assert call_kwargs["textures"] == textures
        assert call_kwargs["frames_per_texture"] == 5

    def test_apply_metadata_actions_fade_to(self, dev_visualizer, sprite_with_configs, mocker):
        """Test FadeTo action type."""
        mock_fade = mocker.patch("arcadeactions.fade_to")

        sprite_with_configs._action_configs = [
            {"action_type": "FadeTo", "target_alpha": 0, "speed": 10, "condition": "infinite"}
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_fade.assert_called_once()
        call_kwargs = mock_fade.call_args[1]
        assert call_kwargs["target_alpha"] == 0
        assert call_kwargs["speed"] == 10

    def test_apply_metadata_actions_blink_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test BlinkUntil action type."""
        mock_blink = mocker.patch("arcadeactions.blink_until")

        sprite_with_configs._action_configs = [
            {"action_type": "BlinkUntil", "frames_until_change": 10, "condition": "infinite"}
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_blink.assert_called_once()
        call_kwargs = mock_blink.call_args[1]
        assert call_kwargs["frames_until_change"] == 10

    def test_apply_metadata_actions_rotate_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test RotateUntil action type."""
        mock_rotate = mocker.patch("arcadeactions.rotate_until")

        sprite_with_configs._action_configs = [
            {"action_type": "RotateUntil", "angular_velocity": 90, "condition": "infinite"}
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_rotate.assert_called_once()
        call_kwargs = mock_rotate.call_args[1]
        assert call_kwargs["angular_velocity"] == 90

    def test_apply_metadata_actions_tween_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test TweenUntil action type."""
        mock_tween = mocker.patch("arcadeactions.tween_until")

        sprite_with_configs._action_configs = [
            {
                "action_type": "TweenUntil",
                "start_value": 0,
                "end_value": 100,
                "property_name": "center_x",
                "condition": "infinite",
            }
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_tween.assert_called_once()
        call_kwargs = mock_tween.call_args[1]
        assert call_kwargs["start_value"] == 0
        assert call_kwargs["end_value"] == 100
        assert call_kwargs["property_name"] == "center_x"

    def test_apply_metadata_actions_scale_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test ScaleUntil action type."""
        mock_scale = mocker.patch("arcadeactions.scale_until")

        sprite_with_configs._action_configs = [
            {"action_type": "ScaleUntil", "velocity": (0.1, 0.1), "condition": "infinite"}
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_scale.assert_called_once()
        call_kwargs = mock_scale.call_args[1]
        assert call_kwargs["velocity"] == (0.1, 0.1)

    def test_apply_metadata_actions_callback_until(self, dev_visualizer, sprite_with_configs, mocker):
        """Test CallbackUntil action type."""
        mock_callback = mocker.patch("arcadeactions.callback_until")

        def test_callback():
            pass

        sprite_with_configs._action_configs = [
            {"action_type": "CallbackUntil", "callback": test_callback, "condition": "infinite"}
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_callback.assert_called_once()
        call_kwargs = mock_callback.call_args[1]
        assert call_kwargs["callback"] == test_callback

    def test_apply_metadata_actions_delay_frames(self, dev_visualizer, sprite_with_configs, mocker):
        """Test DelayFrames action type."""
        mock_delay = mocker.patch("arcadeactions.delay_frames")

        sprite_with_configs._action_configs = [{"action_type": "DelayFrames", "condition": "infinite"}]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_delay.assert_called_once()


class TestApplyMetadataActionsResolvers:
    """Test callback and condition resolvers."""

    def test_apply_metadata_actions_with_resolver(self, dev_visualizer, sprite_with_configs, mocker):
        """Test callback/condition resolver parameter."""
        mock_move_until = mocker.patch("arcadeactions.move_until")

        def resolver(name):
            if name == "test_callback":
                return lambda: None
            return None

        sprite_with_configs._action_configs = [
            {
                "action_type": "MoveUntil",
                "velocity": (5, 0),
                "condition": "infinite",
                "on_stop": "test_callback",
            }
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs, resolver=resolver)

        mock_move_until.assert_called_once()
        call_kwargs = mock_move_until.call_args[1]
        assert call_kwargs["on_stop"] is not None

    def test_apply_metadata_actions_with_overrides(self, dev_visualizer, sprite_with_configs, mocker):
        """Test velocity, bounds, boundary_behavior overrides."""
        mock_move_until = mocker.patch("arcadeactions.move_until")

        sprite_with_configs._action_configs = [
            {
                "action_type": "MoveUntil",
                "velocity": (5, 0),
                "condition": "infinite",
                "bounds": (0, 0, 800, 600),
                "boundary_behavior": "limit",
            }
        ]

        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_move_until.assert_called_once()
        call_kwargs = mock_move_until.call_args[1]
        assert call_kwargs["bounds"] == (0, 0, 800, 600)
        assert call_kwargs["boundary_behavior"] == "limit"


class TestApplyMetadataActionsErrorHandling:
    """Test error handling in apply_metadata_actions."""

    def test_apply_metadata_actions_skips_invalid_presets(self, dev_visualizer, sprite_with_configs, mocker):
        """Verify graceful handling of invalid presets."""
        mock_registry = mocker.MagicMock()
        mock_registry.create.side_effect = Exception("Invalid preset")
        mocker.patch("arcadeactions.dev.get_preset_registry", return_value=mock_registry)

        sprite_with_configs._action_configs = [{"preset": "invalid_preset", "params": {}}]

        # Should not crash
        dev_visualizer.apply_metadata_actions(sprite_with_configs)

        mock_registry.create.assert_called_once()

    def test_apply_metadata_actions_no_action_configs(self, dev_visualizer, test_sprite, mocker):
        """Test early return when sprite lacks _action_configs."""
        # Sprite doesn't have _action_configs attribute
        assert not isinstance(test_sprite, SpriteWithActionConfigs)

        mock_registry = mocker.patch("arcadeactions.dev.get_preset_registry")

        dev_visualizer.apply_metadata_actions(test_sprite)

        mock_registry.assert_not_called()
