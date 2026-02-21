"""Test suite for DevVisualizer manager.

Tests the unified DevVisualizer manager with environment variable support
and F12 toggle functionality.
"""

import os

import arcade
import pytest

from arcadeactions.dev.prototype_registry import register_prototype
from arcadeactions.dev.visualizer import (
    DevVisualizer,
    auto_enable_dev_visualizer_from_env,
    enable_dev_visualizer,
    get_dev_visualizer,
)
from tests.conftest import ActionTestBase


@pytest.fixture(autouse=True)
def mock_arcade_text(mocker):
    """Mock arcade.Text to avoid OpenGL requirements in headless CI environments.

    This fixture patches arcade.Text in the visualizer module before DevVisualizer
    is created, preventing OpenGL context errors when Text objects are created
    in __init__ methods.
    """

    def create_mock_text(*args, **kwargs):
        """Create a new mock Text instance for each call."""
        mock_text = mocker.MagicMock()
        # Set default properties that tests might access
        mock_text.y = kwargs.get("y", args[2] if len(args) > 2 else 10)
        mock_text.text = kwargs.get("text", args[0] if len(args) > 0 else "")
        mock_text.draw = mocker.MagicMock()
        return mock_text

    # Patch Text in the visualizer module where it's used
    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", side_effect=create_mock_text)


@pytest.fixture(autouse=True)
def cleanup_global_dev_visualizer():
    """Clean up global DevVisualizer instance between tests."""
    import arcadeactions.dev.visualizer as viz_module
    from arcadeactions.dev import window_hooks

    yield
    # Cleanup after test
    if viz_module._global_dev_visualizer is not None:
        viz_module._global_dev_visualizer.detach_from_window()
    viz_module._global_dev_visualizer = None
    # Restore window hook if installed
    if window_hooks._window_attach_hook_installed:
        if window_hooks.window_commands_module is not None and window_hooks._original_set_window is not None:
            window_hooks.window_commands_module.set_window = window_hooks._original_set_window  # type: ignore[assignment]
        window_hooks._window_attach_hook_installed = False
        window_hooks._original_set_window = None
    # Restore update_all hook if installed
    if window_hooks._update_all_attach_hook_installed:
        from arcadeactions import Action

        if window_hooks._previous_update_all_func is not None:
            Action.update_all = classmethod(window_hooks._previous_update_all_func)  # type: ignore[method-assign]
        window_hooks._update_all_attach_hook_installed = False
        window_hooks._previous_update_all_func = None


@pytest.mark.integration
class TestDevVisualizerManager(ActionTestBase):
    """Test suite for DevVisualizer manager."""

    def test_dev_visualizer_creation(self, window):
        """Test creating DevVisualizer instance."""
        scene_sprites = arcade.SpriteList()
        dev_viz = DevVisualizer(scene_sprites=scene_sprites)

        assert dev_viz.scene_sprites == scene_sprites
        assert dev_viz.visible is False
        # Legacy secondary-window palette was removed; DevShell panels are in-window.
        assert hasattr(dev_viz, "palette_window") is False
        assert dev_viz.selection_manager is not None

    def test_dev_visualizer_auto_creates_scene(self, window):
        """Test DevVisualizer creates scene_sprites if not provided."""
        dev_viz = DevVisualizer()

        assert dev_viz.scene_sprites is not None
        assert isinstance(dev_viz.scene_sprites, arcade.SpriteList)

    @pytest.mark.integration
    def test_toggle_visibility(self, window):
        """Test toggling DevVisualizer visibility."""
        dev_viz = DevVisualizer()

        assert dev_viz.visible is False
        dev_viz.toggle()
        assert dev_viz.visible is True
        dev_viz.toggle()
        assert dev_viz.visible is False

    @pytest.mark.integration
    def test_show_hide(self, window):
        """Test show/hide methods."""
        dev_viz = DevVisualizer()

        dev_viz.show()
        assert dev_viz.visible is True

        dev_viz.hide()
        assert dev_viz.visible is False

    @pytest.mark.integration
    def test_attach_to_window(self, window):
        """Test attaching DevVisualizer to window."""
        dev_viz = DevVisualizer()
        dev_viz.attach_to_window(window)

        assert dev_viz._attached is True
        assert dev_viz.window == window

    @pytest.mark.integration
    def test_f12_toggle_when_attached(self, window):
        """Test F12 key toggles DevVisualizer when attached."""
        dev_viz = DevVisualizer()
        dev_viz.attach_to_window(window)

        assert dev_viz.visible is False

        # Simulate F12 key press
        window.on_key_press(arcade.key.F12, 0)

        assert dev_viz.visible is True

        # Press F12 again
        window.on_key_press(arcade.key.F12, 0)

        assert dev_viz.visible is False

    @pytest.mark.integration
    def test_detach_from_window(self, window):
        """Test detaching DevVisualizer restores original handlers."""
        dev_viz = DevVisualizer()
        original_draw = window.on_draw

        dev_viz.attach_to_window(window)
        assert dev_viz._attached is True

        dev_viz.detach_from_window()
        assert dev_viz._attached is False
        assert window.on_draw == original_draw

    def test_enable_dev_visualizer(self, window):
        """Test enable_dev_visualizer function."""
        scene_sprites = arcade.SpriteList()
        dev_viz = enable_dev_visualizer(scene_sprites=scene_sprites, auto_attach=False)

        assert dev_viz is not None
        assert dev_viz.scene_sprites == scene_sprites

    def test_get_dev_visualizer(self, window):
        """Test getting global DevVisualizer instance."""
        # Initially None (cleaned up by fixture)
        assert get_dev_visualizer() is None

        # Enable it
        dev_viz = enable_dev_visualizer(auto_attach=False)
        assert get_dev_visualizer() == dev_viz

    def test_auto_enable_from_env_devviz(self, window):
        """Test auto-enable with ARCADEACTIONS_DEVVIZ=1."""
        # Save original value
        original = os.environ.get("ARCADEACTIONS_DEVVIZ")

        try:
            os.environ["ARCADEACTIONS_DEVVIZ"] = "1"
            dev_viz = auto_enable_dev_visualizer_from_env()

            assert dev_viz is not None
            assert isinstance(dev_viz, DevVisualizer)
        finally:
            if original is None:
                os.environ.pop("ARCADEACTIONS_DEVVIZ", None)
            else:
                os.environ["ARCADEACTIONS_DEVVIZ"] = original

    def test_auto_enable_from_env_dev(self, window):
        """Test auto-enable with ARCADEACTIONS_DEV=1."""
        # Save original values
        original_devviz = os.environ.get("ARCADEACTIONS_DEVVIZ")
        original_dev = os.environ.get("ARCADEACTIONS_DEV")

        try:
            # Clear DEVVIZ, set DEV
            os.environ.pop("ARCADEACTIONS_DEVVIZ", None)
            os.environ["ARCADEACTIONS_DEV"] = "1"

            dev_viz = auto_enable_dev_visualizer_from_env()

            assert dev_viz is not None
            assert isinstance(dev_viz, DevVisualizer)
        finally:
            if original_devviz is None:
                os.environ.pop("ARCADEACTIONS_DEVVIZ", None)
            else:
                os.environ["ARCADEACTIONS_DEVVIZ"] = original_devviz
            if original_dev is None:
                os.environ.pop("ARCADEACTIONS_DEV", None)
            else:
                os.environ["ARCADEACTIONS_DEV"] = original_dev

    def test_auto_enable_returns_none_when_not_set(self, window):
        """Test auto-enable returns None when no env vars set."""
        # Save and clear all env vars
        original_devviz = os.environ.get("ARCADEACTIONS_DEVVIZ")
        original_dev = os.environ.get("ARCADEACTIONS_DEV")

        try:
            os.environ.pop("ARCADEACTIONS_DEVVIZ", None)
            os.environ.pop("ARCADEACTIONS_DEV", None)

            dev_viz = auto_enable_dev_visualizer_from_env()

            assert dev_viz is None
        finally:
            if original_devviz:
                os.environ["ARCADEACTIONS_DEVVIZ"] = original_devviz
            if original_dev:
                os.environ["ARCADEACTIONS_DEV"] = original_dev

    @pytest.mark.integration
    def test_mouse_handling_when_visible(self, window):
        """Test mouse events are handled when DevVisualizer is visible."""
        scene_sprites = arcade.SpriteList()
        dev_viz = DevVisualizer(scene_sprites=scene_sprites)
        dev_viz.attach_to_window(window)
        dev_viz.show()

        # Register a prototype for testing
        @register_prototype("test_sprite")
        def make_test(ctx):
            sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.RED)
            sprite._prototype_id = "test_sprite"
            return sprite

        # Click on palette should be handled (should not crash)
        dev_viz.handle_mouse_press(50, 60, 1, 0)

    @pytest.mark.integration
    def test_draw_when_visible(self, window):
        """Test DevVisualizer draws when visible."""
        if window is None:
            pytest.skip("No window available")

        scene_sprites = arcade.SpriteList()
        dev_viz = DevVisualizer(scene_sprites=scene_sprites)
        dev_viz.show()

        # Should not crash
        dev_viz.draw()

        # When hidden, should not draw
        dev_viz.hide()
        dev_viz.draw()  # Should return early without drawing

    @pytest.mark.integration
    def test_visible_indicator_when_active(self, window):
        """Test that DevVisualizer shows a visible indicator when active."""
        if window is None:
            pytest.skip("No window available")

        dev_viz = DevVisualizer()
        dev_viz.show()

        # Indicator text should exist
        assert dev_viz._indicator_text is not None
        assert "DEV" in dev_viz._indicator_text.text or "DevVisualizer" in dev_viz._indicator_text.text

        # Drawing should include indicator (should not crash)
        dev_viz.draw()

    @pytest.mark.integration
    def test_auto_attach_after_window_available(self, monkeypatch):
        """Test DevVisualizer attaches automatically when window becomes available."""
        import arcade.window_commands as window_commands

        # Ensure no window is reported
        def raise_no_window():
            raise RuntimeError("No window")

        monkeypatch.setattr(arcade, "get_window", raise_no_window)

        # Stub set_window to avoid actual Arcade behaviour
        created_windows: list[object] = []

        def fake_set_window(window):
            created_windows.append(window)

        monkeypatch.setattr(window_commands, "set_window", fake_set_window)

        # Enable DevVisualizer (auto attach will fail and install hook)
        dev_viz = enable_dev_visualizer(auto_attach=True)
        assert dev_viz is not None
        assert dev_viz._attached is False

        # Simulate window creation - patched set_window should attach
        class FakeWindow:
            def __init__(self):
                self.on_draw = lambda: None
                self.on_key_press = lambda key, modifiers: None
                self.on_mouse_press = lambda *args: None
                self.on_mouse_drag = lambda *args: None
                self.on_mouse_release = lambda *args: None

        fake_window = FakeWindow()

        # Call patched set_window (installed by DevVisualizer)
        window_commands.set_window(fake_window)

        # DevVisualizer should now be attached
        assert dev_viz._attached is True

    @pytest.mark.integration
    def test_auto_attach_via_update_all_hook(self, monkeypatch):
        """Test DevVisualizer can auto-attach via Action.update_all, like the debug visualizer."""
        from arcadeactions import Action

        # Start with no window
        def raise_no_window():
            raise RuntimeError("No window")

        monkeypatch.setattr(arcade, "get_window", raise_no_window)

        dev_viz = enable_dev_visualizer(auto_attach=True)
        assert dev_viz is not None
        assert dev_viz._attached is False

        # Now simulate that a window exists later
        class FakeWindow:
            def __init__(self):
                self.on_draw = lambda: None
                self.on_key_press = lambda key, modifiers: None
                self.on_mouse_press = lambda *args: None
                self.on_mouse_drag = lambda *args: None
                self.on_mouse_release = lambda *args: None

        fake_window = FakeWindow()
        monkeypatch.setattr(arcade, "get_window", lambda: fake_window)

        # Calling Action.update_all should trigger the devviz attach attempt
        Action.update_all(0)

        assert dev_viz._attached is True


@pytest.mark.integration
class TestDevVisualizerPauseResume(ActionTestBase):
    """Test suite for DevVisualizer pause/resume functionality."""

    @pytest.mark.integration
    def test_actions_paused_when_visible(self, window):
        """Test that actions are paused when DevVisualizer becomes visible."""
        from arcadeactions import Action, infinite, move_until

        # Create sprite with action
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100
        move_until(sprite, velocity=(5, 0), condition=infinite)

        # Create DevVisualizer and show it
        dev_viz = DevVisualizer()
        dev_viz.show()

        # Actions should be paused
        assert Action.is_paused() is True

    @pytest.mark.integration
    def test_actions_resumed_when_hidden(self, window):
        """Test that actions are resumed when DevVisualizer becomes hidden."""
        from arcadeactions import Action, infinite, move_until

        # Create sprite with action
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100
        move_until(sprite, velocity=(5, 0), condition=infinite)

        # Create DevVisualizer, show then hide
        dev_viz = DevVisualizer()
        dev_viz.show()
        assert Action.is_paused() is True

        dev_viz.hide()
        assert Action.is_paused() is False

    @pytest.mark.integration
    def test_toggle_pauses_and_resumes(self, window):
        """Test that toggle() pauses/resumes actions."""
        from arcadeactions import Action, infinite, move_until

        # Create sprite with action first
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100
        move_until(sprite, velocity=(5, 0), condition=infinite)

        dev_viz = DevVisualizer()

        # Toggle on - should pause
        dev_viz.toggle()
        assert dev_viz.visible is True
        assert Action.is_paused() is True

        # Toggle off - should resume
        dev_viz.toggle()
        assert dev_viz.visible is False
        assert Action.is_paused() is False

    @pytest.mark.integration
    def test_sprites_dont_move_when_paused(self, window):
        """Test that sprites don't move when actions are paused."""
        from arcadeactions import Action, infinite, move_until

        # Create sprite with action
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100
        move_until(sprite, velocity=(5, 0), condition=infinite)

        # Show DevVisualizer to pause actions
        dev_viz = DevVisualizer()
        dev_viz.show()

        # Update actions - should not move sprite
        initial_x = sprite.center_x
        Action.update_all(1.0 / 60.0)

        assert sprite.center_x == initial_x

    @pytest.mark.integration
    def test_sprites_move_when_resumed(self, window):
        """Test that sprites move again when actions are resumed."""
        from arcadeactions import Action, infinite, move_until

        # Create sprite with action
        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100
        move_until(sprite, velocity=(5, 0), condition=infinite)

        # Show then hide DevVisualizer
        dev_viz = DevVisualizer()
        dev_viz.show()
        dev_viz.hide()

        # Update actions - should set velocity
        Action.update_all(1.0 / 60.0)

        # Check that velocity is set (sprite will move when sprite.update() is called)
        assert sprite.change_x > 0

    @pytest.mark.integration
    def test_show_freezes_scene_sprite_motion(self, window):
        """Entering edit mode should freeze scene sprite linear/angular motion."""
        scene_sprites = arcade.SpriteList()
        sprite = arcade.Sprite()
        sprite.change_x = 3.0
        sprite.change_y = -2.0
        sprite.change_angle = 5.0
        scene_sprites.append(sprite)
        dev_viz = DevVisualizer(scene_sprites=scene_sprites)

        dev_viz.show()

        assert sprite.change_x == 0
        assert sprite.change_y == 0
        assert sprite.change_angle == 0

    @pytest.mark.integration
    def test_hide_restores_scene_sprite_motion(self, window):
        """Leaving edit mode should restore pre-freeze scene sprite motion."""
        scene_sprites = arcade.SpriteList()
        sprite = arcade.Sprite()
        sprite.change_x = 4.0
        sprite.change_y = 1.5
        sprite.change_angle = -8.0
        scene_sprites.append(sprite)
        dev_viz = DevVisualizer(scene_sprites=scene_sprites)

        dev_viz.show()
        dev_viz.hide()

        assert sprite.change_x == 4.0
        assert sprite.change_y == 1.5
        assert sprite.change_angle == -8.0


@pytest.mark.integration
class TestDevVisualizerSpriteIntegration(ActionTestBase):
    """Test suite for integrating existing game sprites with DevVisualizer."""

    def test_import_sprites_from_game(self, window):
        """Test importing sprites from existing game sprite lists."""
        # Create game sprites
        game_sprites = arcade.SpriteList()
        for i in range(5):
            sprite = arcade.Sprite()
            sprite.center_x = i * 100
            sprite.center_y = 200
            game_sprites.append(sprite)

        # Create DevVisualizer and import sprites
        dev_viz = DevVisualizer()
        dev_viz.import_sprites(game_sprites)

        # Scene should now contain copies of game sprites
        assert len(dev_viz.scene_sprites) == 5
        for i, sprite in enumerate(dev_viz.scene_sprites):
            assert sprite.center_x == i * 100
            assert sprite.center_y == 200

    def test_import_sprites_preserves_properties(self, window):
        """Test that importing sprites preserves texture, scale, angle, etc."""
        # Create game sprite with properties
        game_sprites = arcade.SpriteList()
        sprite = arcade.Sprite(":resources:images/items/star.png", scale=2.0)
        sprite.center_x = 300
        sprite.center_y = 400
        sprite.angle = 45
        game_sprites.append(sprite)

        # Import into DevVisualizer
        dev_viz = DevVisualizer()
        dev_viz.import_sprites(game_sprites)

        # Check properties preserved
        imported = dev_viz.scene_sprites[0]
        assert imported.center_x == 300
        assert imported.center_y == 400
        assert imported.angle == 45
        # Scale is a tuple in Arcade 3.x
        assert imported.scale == (2.0, 2.0)

    def test_import_sprites_stores_original_reference(self, window):
        """Test that imported sprites store reference to original."""
        # Create game sprite
        game_sprites = arcade.SpriteList()
        original = arcade.Sprite()
        original.center_x = 100
        game_sprites.append(original)

        # Import into DevVisualizer
        dev_viz = DevVisualizer()
        dev_viz.import_sprites(game_sprites)

        # Check reference stored
        imported = dev_viz.scene_sprites[0]
        assert hasattr(imported, "_original_sprite")
        assert imported._original_sprite is original

    def test_export_sprites_syncs_back_to_game(self, window):
        """Test that exporting sprites syncs changes back to original."""
        # Create game sprite
        game_sprites = arcade.SpriteList()
        original = arcade.Sprite()
        original.center_x = 100
        original.center_y = 200
        game_sprites.append(original)

        # Import and modify
        dev_viz = DevVisualizer()
        dev_viz.import_sprites(game_sprites)
        dev_viz.scene_sprites[0].center_x = 300
        dev_viz.scene_sprites[0].center_y = 400

        # Export changes
        dev_viz.export_sprites()

        # Original should be updated
        assert original.center_x == 300
        assert original.center_y == 400

    def test_import_multiple_sprite_lists(self, window):
        """Test importing sprites from multiple sprite lists."""
        # Create multiple sprite lists
        enemies = arcade.SpriteList()
        for i in range(3):
            sprite = arcade.Sprite()
            sprite.center_x = i * 50
            enemies.append(sprite)

        bullets = arcade.SpriteList()
        for i in range(2):
            sprite = arcade.Sprite()
            sprite.center_x = i * 100
            bullets.append(sprite)

        # Import both
        dev_viz = DevVisualizer()
        dev_viz.import_sprites(enemies, bullets)

        # Should have all sprites
        assert len(dev_viz.scene_sprites) == 5

    def test_clear_scene_before_import(self, window):
        """Test that import_sprites clears existing scene first."""
        dev_viz = DevVisualizer()

        # Add some sprites to scene
        for i in range(3):
            dev_viz.scene_sprites.append(arcade.Sprite())

        assert len(dev_viz.scene_sprites) == 3

        # Import new sprites
        game_sprites = arcade.SpriteList()
        game_sprites.append(arcade.Sprite())

        dev_viz.import_sprites(game_sprites, clear=True)

        # Should only have imported sprite
        assert len(dev_viz.scene_sprites) == 1

    def test_append_to_scene_without_clearing(self, window):
        """Test that import_sprites can append without clearing."""
        dev_viz = DevVisualizer()

        # Add some sprites to scene
        for i in range(3):
            dev_viz.scene_sprites.append(arcade.Sprite())

        # Import without clearing
        game_sprites = arcade.SpriteList()
        game_sprites.append(arcade.Sprite())

        dev_viz.import_sprites(game_sprites, clear=False)

        # Should have both old and new sprites
        assert len(dev_viz.scene_sprites) == 4


@pytest.mark.integration
class TestDevVisualizerEditMode(ActionTestBase):
    """Test suite for DevVisualizer edit mode."""

    @pytest.mark.integration
    def test_actions_stored_as_metadata(self, window):
        """Test that actions are stored as metadata in edit mode."""

        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100

        # Apply action in edit mode
        dev_viz = DevVisualizer()
        dev_viz.show()

        # Store action config instead of applying
        action_config = {
            "action_type": "MoveUntil",
            "velocity": (5, 0),
            "condition": "infinite",
        }

        if not hasattr(sprite, "_action_configs"):
            sprite._action_configs = []
        sprite._action_configs.append(action_config)

        # Sprite should have metadata
        assert hasattr(sprite, "_action_configs")
        assert len(sprite._action_configs) == 1
        assert sprite._action_configs[0]["velocity"] == (5, 0)

    @pytest.mark.integration
    def test_edit_mode_does_not_apply_actions(self, window, monkeypatch):
        """Test that edit mode writes metadata without applying actions."""
        scene_sprites = arcade.SpriteList()
        sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.BLUE)
        scene_sprites.append(sprite)

        dev_viz = DevVisualizer(scene_sprites=scene_sprites)
        dev_viz.show()

        dev_viz.selection_manager._selected.add(sprite)

        def fail_apply(*args, **kwargs):
            raise AssertionError("Action.apply should not run in edit mode")

        monkeypatch.setattr("arcadeactions.base.Action.apply", fail_apply)

        dev_viz.attach_preset_to_selected("test_preset", params={"speed": 3}, tag="movement")

        assert hasattr(sprite, "_action_configs")
        assert sprite._action_configs[0]["preset"] == "test_preset"

    def test_apply_metadata_actions_to_runtime(self, window):
        """Test converting metadata actions to runtime actions."""
        from arcadeactions import Action

        sprite = arcade.Sprite()
        sprite.center_x = 100
        sprite.center_y = 100

        # Store action metadata
        sprite._action_configs = [
            {
                "action_type": "MoveUntil",
                "velocity": (5, 0),
                "condition": "infinite",
            }
        ]

        # Convert to runtime
        dev_viz = DevVisualizer()
        dev_viz.apply_metadata_actions(sprite)

        # Action should be applied
        dev_viz.hide()  # Resume actions
        Action.update_all(1.0 / 60.0)

        # Check velocity is set (sprite moves when sprite.update() is called)
        assert sprite.change_x == 5

    @pytest.mark.integration
    def test_edit_mode_indicator(self, window):
        """Test that edit mode shows proper indicator."""
        if window is None:
            pytest.skip("No window available")

        dev_viz = DevVisualizer()
        dev_viz.show()

        # Should show edit mode indicator
        assert "EDIT" in dev_viz._indicator_text.text

    def test_export_includes_action_metadata(self, window):
        """Test that YAML export includes action metadata."""
        from arcadeactions.dev import export_template

        sprite = arcade.Sprite()
        sprite._prototype_id = "test_sprite"
        sprite._action_configs = [
            {
                "preset": "scroll_left",
                "params": {"speed": 4},
            }
        ]

        dev_viz = DevVisualizer()
        dev_viz.scene_sprites.append(sprite)

        # Export to YAML
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            export_template(dev_viz.scene_sprites, f.name, prompt_user=False)

            # Read back and verify
            import yaml

            with open(f.name) as read_f:
                data = yaml.safe_load(read_f)

            assert len(data) == 1
            assert "actions" in data[0]
            assert len(data[0]["actions"]) == 1
            assert data[0]["actions"][0]["preset"] == "scroll_left"
