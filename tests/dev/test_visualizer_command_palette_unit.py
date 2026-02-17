"""Unit tests for DevVisualizer command-palette integration paths."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.command_registry import CommandExecutionContext
from arcadeactions.dev.visualizer import DevVisualizer


@pytest.fixture(autouse=True)
def forbid_real_secondary_windows(mocker):
    """Guard: these unit tests must not create real secondary windows."""
    mocker.patch(
        "arcadeactions.dev.visualizer.PaletteWindow", side_effect=AssertionError("PaletteWindow creation forbidden")
    )
    mocker.patch(
        "arcadeactions.dev.visualizer.CommandPaletteWindow",
        side_effect=AssertionError("CommandPaletteWindow creation forbidden"),
    )


def _make_window_stub(mocker):
    """Create a minimal window stub for DevVisualizer unit tests."""
    window = mocker.MagicMock()
    window.closed = False
    window.current_view = None
    window.on_draw = mocker.MagicMock()
    window.on_key_press = mocker.MagicMock()
    window.on_mouse_press = mocker.MagicMock()
    window.on_mouse_drag = mocker.MagicMock()
    window.on_mouse_release = mocker.MagicMock()
    window.on_close = mocker.MagicMock()
    window.get_location = mocker.MagicMock(return_value=(100, 200))
    window.activate = mocker.MagicMock()
    window.show_view = mocker.MagicMock()
    window.set_location = mocker.MagicMock()
    return window


def test_build_command_context_uses_current_selection(mocker, test_sprite_list):
    """Context should include selected sprites and active window."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=test_sprite_list, window=window)
    selected_sprite = test_sprite_list[0]
    dev_viz.selection_manager._selected.add(selected_sprite)

    context = dev_viz._build_command_context()

    assert context.window is window
    assert context.scene_sprites is test_sprite_list
    assert context.selection == [selected_sprite]


def test_toggle_command_palette_creates_and_toggles(mocker):
    """toggle_command_palette should create window, refresh context, and toggle visibility."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_palette = mocker.MagicMock()
    mock_palette.visible = False
    mocker.patch.object(
        dev_viz,
        "_create_command_palette_window",
        side_effect=lambda: setattr(dev_viz, "command_palette_window", mock_palette),
    )
    mock_context = mocker.patch.object(dev_viz, "_build_command_context", return_value=mocker.MagicMock())
    mocker.patch.object(dev_viz, "_position_command_palette_window")
    mocker.patch.object(dev_viz, "_restore_command_palette_location_after_show")
    mocker.patch.object(dev_viz, "_activate_main_window")

    dev_viz.toggle_command_palette()

    mock_context.assert_called_once()
    mock_palette.set_context.assert_called_once()
    mock_palette.show_window.assert_called_once()


def test_toggle_command_palette_returns_when_creation_fails(mocker):
    """toggle_command_palette should return quietly when creation fails."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mocker.patch.object(dev_viz, "_create_command_palette_window")
    dev_viz.command_palette_window = None

    dev_viz.toggle_command_palette()

    assert dev_viz.command_palette_window is None


def test_hide_hides_command_palette(mocker):
    """hide should hide command palette when present."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz.command_palette_window = mocker.MagicMock()
    mock_resume = mocker.patch("arcadeactions.dev.visualizer.Action.resume_all")

    dev_viz.hide()

    dev_viz.command_palette_window.hide_window.assert_called_once()
    mock_resume.assert_called_once()


def test_toggle_command_palette_hides_when_visible(mocker):
    """toggle_command_palette should hide when command palette is currently visible."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_palette = mocker.MagicMock()
    mock_palette.visible = True
    dev_viz.command_palette_window = mock_palette
    cache_mock = mocker.patch.object(dev_viz, "_cache_command_palette_desired_location")
    activate_mock = mocker.patch.object(dev_viz, "_activate_main_window")

    dev_viz.toggle_command_palette()

    cache_mock.assert_called_once()
    mock_palette.hide_window.assert_called_once()
    activate_mock.assert_called_once()


def test_detach_closes_command_palette(mocker):
    """detach_from_window should close and clear command palette window."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz._attached = True
    command_palette = mocker.MagicMock()
    dev_viz.command_palette_window = command_palette

    # Seed required originals used during detach.
    dev_viz._original_on_draw = window.on_draw
    dev_viz._original_on_key_press = window.on_key_press
    dev_viz._original_on_mouse_press = window.on_mouse_press
    dev_viz._original_on_mouse_drag = window.on_mouse_drag
    dev_viz._original_on_mouse_release = window.on_mouse_release
    dev_viz._original_on_close = window.on_close

    dev_viz.detach_from_window()

    command_palette.close.assert_called_once()
    assert dev_viz.command_palette_window is None


def test_default_command_registry_contains_expected_keys(mocker):
    """Built-in command set should include enabled and disabled command keys."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    context = CommandExecutionContext(window=window, scene_sprites=dev_viz.scene_sprites, selection=[])
    enabled = dev_viz.command_registry.get_enabled_commands(context)
    enabled_keys = {command.key for command in enabled}

    assert arcade.key.E in enabled_keys
    assert arcade.key.I in enabled_keys
    assert arcade.key.H in enabled_keys
    assert arcade.key.G not in enabled_keys


def test_create_command_palette_positions_next_to_main_window(mocker):
    """Creation should anchor command palette to main-window left edge with frame padding."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_palette = mocker.MagicMock()
    mock_palette.width = 400
    mock_palette.height = 240
    mocker.patch("arcadeactions.dev.visualizer.CommandPaletteWindow", return_value=mock_palette)
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    window.get_location = mocker.MagicMock(return_value=(100, 200))

    dev_viz._create_command_palette_window()

    mock_palette.set_location.assert_called_once_with(-308, 200)


def test_create_command_palette_positions_below_sprite_palette_when_available(mocker):
    """Creation should stack command palette below the F11 palette window when present."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite_palette = mocker.MagicMock()
    sprite_palette.get_location.return_value = (-158, 200)
    sprite_palette.height = 400
    dev_viz.palette_window = sprite_palette
    mock_palette = mocker.MagicMock()
    mock_palette.width = 400
    mock_palette.height = 240
    mocker.patch("arcadeactions.dev.visualizer.CommandPaletteWindow", return_value=mock_palette)
    mocker.patch(
        "arcadeactions.dev.visualizer.window_decorations.measure_window_decoration_deltas", return_value=(None, None)
    )
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    window.get_location = mocker.MagicMock(return_value=(100, 200))

    dev_viz._create_command_palette_window()

    mock_palette.set_location.assert_called_once_with(-308, 604)


def test_position_command_palette_uses_cached_location_when_anchor_unchanged(mocker):
    """Positioning should reuse cached location to avoid per-toggle drift."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_palette = mocker.MagicMock()
    mock_palette.width = 400
    mock_palette.height = 240
    dev_viz.command_palette_window = mock_palette
    dev_viz._command_palette_desired_location = (-300, -40)
    dev_viz._command_palette_position_anchor = (100, 200)
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    window.get_location = mocker.MagicMock(return_value=(100, 200))

    dev_viz._position_command_palette_window(force=False)

    mock_palette.set_location.assert_called_once_with(-300, -40)


def test_create_command_palette_uses_f11_cached_location_when_direct_location_missing(mocker):
    """Stacking should fallback to F11 cached desired location when direct location lookup fails."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite_palette = mocker.MagicMock()
    sprite_palette.height = 400
    dev_viz.palette_window = sprite_palette
    dev_viz._palette_desired_location = (-158, 200)
    mock_palette = mocker.MagicMock()
    mock_palette.width = 400
    mock_palette.height = 240
    mocker.patch("arcadeactions.dev.visualizer.CommandPaletteWindow", return_value=mock_palette)
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    mocker.patch.object(dev_viz, "_get_window_location", return_value=None)
    dev_viz._position_tracker.get_tracked_position = mocker.MagicMock(return_value=None)
    window.get_location = mocker.MagicMock(return_value=(100, 200))

    dev_viz._create_command_palette_window()

    mock_palette.set_location.assert_called_once_with(-308, 604)


def test_create_command_palette_adds_f11_frame_height_when_measured(mocker):
    """Stacking should include measured F11 frame/titlebar height when available."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite_palette = mocker.MagicMock()
    sprite_palette.get_location.return_value = (-158, 200)
    sprite_palette.height = 400
    dev_viz.palette_window = sprite_palette
    mock_palette = mocker.MagicMock()
    mock_palette.width = 400
    mock_palette.height = 240
    mocker.patch("arcadeactions.dev.visualizer.CommandPaletteWindow", return_value=mock_palette)
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    window.get_location = mocker.MagicMock(return_value=(100, 200))
    mocker.patch(
        "arcadeactions.dev.visualizer.window_decorations.measure_window_decoration_deltas", return_value=(0, 28)
    )

    dev_viz._create_command_palette_window()

    mock_palette.set_location.assert_called_once_with(-308, 632)


def test_create_command_palette_ignores_position_errors(mocker):
    """Creation should swallow set_location errors."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_palette = mocker.MagicMock()
    mock_palette.set_location.side_effect = RuntimeError("boom")
    mocker.patch("arcadeactions.dev.visualizer.CommandPaletteWindow", return_value=mock_palette)
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    window.get_location = mocker.MagicMock(return_value=(1, 2))

    dev_viz._create_command_palette_window()


def test_create_command_palette_noop_when_already_present(mocker):
    """Creation should return early when palette already exists."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    existing = mocker.MagicMock()
    dev_viz.command_palette_window = existing
    ctor = mocker.patch("arcadeactions.dev.visualizer.CommandPaletteWindow")

    dev_viz._create_command_palette_window()

    ctor.assert_not_called()
    assert dev_viz.command_palette_window is existing


def test_command_export_scene_prefers_examples_path(mocker):
    """Export command should select examples path when examples directory exists."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_export = mocker.patch("arcadeactions.dev.templates.export_template")
    mocker.patch("arcadeactions.dev.visualizer.os.path.exists", side_effect=lambda path: path == "examples")

    result = dev_viz._command_export_scene(
        CommandExecutionContext(window=window, scene_sprites=dev_viz.scene_sprites, selection=[])
    )

    assert result is True
    mock_export.assert_called_once()
    assert mock_export.call_args.args[1] == "examples/boss_level.yaml"


def test_command_export_scene_uses_scenes_fallback(mocker):
    """Export command should use scenes path when examples path is unavailable."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_export = mocker.patch("arcadeactions.dev.templates.export_template")
    mocker.patch(
        "arcadeactions.dev.visualizer.os.path.exists",
        side_effect=lambda path: path == "scenes",
    )

    result = dev_viz._command_export_scene(
        CommandExecutionContext(window=window, scene_sprites=dev_viz.scene_sprites, selection=[])
    )

    assert result is True
    assert mock_export.call_args.args[1] == "scenes/new_scene.yaml"


def test_command_import_scene_loads_first_existing(mocker):
    """Import command should load first existing candidate scene file."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_load = mocker.patch("arcadeactions.dev.templates.load_scene_template")
    mocker.patch("arcadeactions.dev.visualizer.os.path.exists", side_effect=lambda path: path == "scene.yaml")
    apply_mock = mocker.patch.object(dev_viz, "apply_metadata_actions")
    sprite_a = object()
    sprite_b = object()
    dev_viz.scene_sprites = [sprite_a, sprite_b]

    result = dev_viz._command_import_scene(
        CommandExecutionContext(window=window, scene_sprites=dev_viz.scene_sprites, selection=[])
    )

    assert result is True
    mock_load.assert_called_once()
    assert mock_load.call_args.args[0] == "scene.yaml"
    assert apply_mock.call_count == 2
    apply_mock.assert_any_call(sprite_a)
    apply_mock.assert_any_call(sprite_b)


def test_command_import_scene_when_missing_files(mocker):
    """Import command should still return True when no candidate files exist."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_load = mocker.patch("arcadeactions.dev.templates.load_scene_template")
    mocker.patch("arcadeactions.dev.visualizer.os.path.exists", return_value=False)

    result = dev_viz._command_import_scene(
        CommandExecutionContext(window=window, scene_sprites=dev_viz.scene_sprites, selection=[])
    )

    assert result is True
    mock_load.assert_not_called()


def test_command_show_help_prints_message(mocker, capsys):
    """Help command should print available command summary and succeed."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)

    result = dev_viz._command_show_help(
        CommandExecutionContext(window=window, scene_sprites=dev_viz.scene_sprites, selection=[])
    )

    assert result is True
    assert "Dev Commands" in capsys.readouterr().out


def test_command_placeholder_helpers_return_false(mocker):
    """Disabled and placeholder command handlers should return False."""
    window = _make_window_stub(mocker)
    context = CommandExecutionContext(window=window, scene_sprites=arcade.SpriteList(), selection=[])
    assert DevVisualizer._command_disabled(context) is False
    assert DevVisualizer._command_not_implemented(context) is False


def test_cache_command_palette_desired_location_uses_tracked_position(mocker):
    """Caching should use tracker location and update anchor from main window."""
    window = _make_window_stub(mocker)
    window.get_location.return_value = (120, 220)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz.command_palette_window = mocker.MagicMock()
    dev_viz._position_tracker.get_tracked_position = mocker.MagicMock(return_value=(10, 20))

    dev_viz._cache_command_palette_desired_location()

    assert dev_viz._command_palette_desired_location == (10, 20)
    assert dev_viz._command_palette_position_anchor == (120, 220)


def test_set_command_palette_location_handles_errors_and_tracks_success(mocker):
    """Setting command palette location should tolerate backend failures and track success."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)

    # No palette -> no-op
    dev_viz.command_palette_window = None
    dev_viz._set_command_palette_location((1, 2))

    # set_location failure -> early return
    bad_palette = mocker.MagicMock()
    bad_palette.set_location.side_effect = RuntimeError("boom")
    dev_viz.command_palette_window = bad_palette
    dev_viz._set_command_palette_location((3, 4))

    # success path -> tracker called
    good_palette = mocker.MagicMock()
    dev_viz.command_palette_window = good_palette
    track = mocker.patch.object(dev_viz._position_tracker, "track_known_position")
    dev_viz._set_command_palette_location((5, 6))

    good_palette.set_location.assert_called_once_with(5, 6)
    track.assert_called_once_with(good_palette, 5, 6)


def test_restore_command_palette_location_after_show_reasserts_when_visible(mocker):
    """Restore-after-show should set desired location now and schedule reassert."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    palette = mocker.MagicMock()
    palette.visible = True
    dev_viz.command_palette_window = palette
    dev_viz._command_palette_desired_location = (-300, 120)
    set_loc = mocker.patch.object(dev_viz, "_set_command_palette_location")
    callbacks: list[object] = []
    mocker.patch("arcadeactions.dev.visualizer.arcade.schedule_once", side_effect=lambda cb, _dt: callbacks.append(cb))

    dev_viz._restore_command_palette_location_after_show()

    set_loc.assert_called_once_with((-300, 120))
    assert len(callbacks) == 1
    callbacks[0](0.0)
    assert set_loc.call_count == 2


def test_get_palette_frame_extra_height_handles_none_and_measure_errors(mocker):
    """Palette frame-height helper should return 0 when unavailable or measure fails."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)

    dev_viz.palette_window = None
    assert dev_viz._get_palette_frame_extra_height() == 0

    dev_viz.palette_window = mocker.MagicMock()
    mocker.patch(
        "arcadeactions.dev.visualizer.window_decorations.measure_window_decoration_deltas",
        side_effect=RuntimeError("measure failed"),
    )
    dev_viz._palette_decoration_dy = None
    assert dev_viz._get_palette_frame_extra_height() == 0


def test_resolve_sprite_palette_location_for_stack_prefers_tracked_then_direct_then_cached(mocker):
    """Stack resolver should prefer tracked, then direct, then cached palette locations."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz.palette_window = mocker.MagicMock()

    dev_viz._position_tracker.get_tracked_position = mocker.MagicMock(return_value=(1, 2))
    assert dev_viz._resolve_sprite_palette_location_for_stack() == (1, 2)

    dev_viz._position_tracker.get_tracked_position = mocker.MagicMock(return_value=None)
    mocker.patch.object(dev_viz, "_get_window_location", return_value=(3, 4))
    assert dev_viz._resolve_sprite_palette_location_for_stack() == (3, 4)

    mocker.patch.object(dev_viz, "_get_window_location", return_value=None)
    dev_viz._palette_desired_location = (5, 6)
    assert dev_viz._resolve_sprite_palette_location_for_stack() == (5, 6)
