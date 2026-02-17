"""Unit tests for DevVisualizer property inspector integration."""

from __future__ import annotations

import arcade
import pytest

from arcadeactions.dev.visualizer import DevVisualizer


@pytest.fixture(autouse=True)
def _mock_arcade_text(mocker):
    def create_text(*args, **kwargs):
        text = mocker.MagicMock()
        text.y = kwargs.get("y", 0)
        text.text = args[0] if args else ""
        text.draw = mocker.MagicMock()
        return text

    mocker.patch("arcadeactions.dev.visualizer.arcade.Text", side_effect=create_text)


def _make_window_stub(mocker):
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
    window.width = 800
    window.height = 600
    return window


def test_alt_i_toggles_property_inspector_from_key_handler(mocker):
    """Alt+I should route through DevVisualizer key handling and toggle inspector."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    toggle_mock = mocker.patch.object(dev_viz, "toggle_property_inspector")

    handled = dev_viz.handle_key_press(arcade.key.I, arcade.key.MOD_ALT)

    assert handled is True
    toggle_mock.assert_called_once_with()


def test_toggle_property_inspector_creates_window_and_syncs_selection(mocker, test_sprite):
    """First toggle should create window and provide current selection context."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([test_sprite]), window=window)
    dev_viz.selection_manager._selected.add(test_sprite)

    inspector_window = mocker.MagicMock()
    inspector_window.visible = False
    inspector_window.is_closed = False
    create_mock = mocker.patch.object(dev_viz, "_create_property_inspector_window")

    def _create():
        dev_viz.property_inspector_window = inspector_window

    create_mock.side_effect = _create

    dev_viz.toggle_property_inspector()

    inspector_window.set_selection.assert_called_once_with([test_sprite])
    inspector_window.show_window.assert_called_once()


def test_hide_does_not_clear_property_history(mocker, test_sprite):
    """Undo history should survive F12 show/hide toggles."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([test_sprite]), window=window)
    history = dev_viz.property_history

    old_x = float(test_sprite.center_x)
    test_sprite.center_x = old_x + 10
    history.record_change(test_sprite, "center_x", old_x, old_x + 10)

    dev_viz.show()
    dev_viz.hide()

    assert history.undo(test_sprite) is not None
    assert test_sprite.center_x == old_x


def test_toggle_property_inspector_hides_when_already_visible(mocker):
    """Second toggle should hide inspector and re-activate main window."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.visible = True
    inspector_window.is_closed = False
    dev_viz.property_inspector_window = inspector_window
    activate = mocker.patch.object(dev_viz, "_activate_main_window")

    dev_viz.toggle_property_inspector()

    inspector_window.hide_window.assert_called_once()
    activate.assert_called_once()


def test_create_property_inspector_window_builds_components(mocker):
    """Creation should instantiate inspector model and window wrapper."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    mock_window = mocker.MagicMock()
    ctor_model = mocker.patch("arcadeactions.dev.visualizer.SpritePropertyInspector", return_value=mocker.MagicMock())
    ctor_window = mocker.patch("arcadeactions.dev.visualizer.PropertyInspectorWindow", return_value=mock_window)
    position = mocker.patch.object(dev_viz, "_position_property_inspector_window")

    dev_viz._create_property_inspector_window()

    ctor_model.assert_called_once()
    ctor_window.assert_called_once()
    assert callable(ctor_window.call_args.kwargs["on_close_callback"])
    position.assert_called_once()
    assert dev_viz.property_inspector_window is mock_window


def test_toggle_property_inspector_recreates_when_existing_window_is_closed(mocker):
    """Toggle should recreate property inspector after OS-level close."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    stale_window = mocker.MagicMock()
    stale_window.is_closed = True
    stale_window.visible = False
    dev_viz.property_inspector_window = stale_window
    replacement = mocker.MagicMock()
    replacement.is_closed = False
    replacement.visible = False
    create_mock = mocker.patch.object(dev_viz, "_create_property_inspector_window")

    def _create():
        dev_viz.property_inspector_window = replacement

    create_mock.side_effect = _create

    dev_viz.toggle_property_inspector()

    create_mock.assert_called_once_with()
    replacement.show_window.assert_called_once_with()


def test_position_property_inspector_window_sets_location(mocker):
    """Positioning should place inspector to the right of the main window."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.width = 360
    dev_viz.property_inspector_window = inspector_window
    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)

    dev_viz._position_property_inspector_window()

    inspector_window.set_location.assert_called_once_with(908, 200)


def test_position_property_inspector_window_returns_on_errors(mocker):
    """Positioning should no-op if location checks fail or set_location raises."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.width = 360
    dev_viz.property_inspector_window = inspector_window

    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=False)
    dev_viz._position_property_inspector_window()
    inspector_window.set_location.assert_not_called()

    mocker.patch.object(dev_viz, "_main_window_has_valid_location", return_value=True)
    inspector_window.set_location.side_effect = RuntimeError("boom")
    dev_viz._position_property_inspector_window()


def test_reset_scene_syncs_existing_property_inspector_selection(mocker, test_sprite):
    """reset_scene should refresh inspector selection when inspector window exists."""
    window = _make_window_stub(mocker)
    original_list = arcade.SpriteList([test_sprite])
    dev_viz = DevVisualizer(scene_sprites=original_list, window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.is_closed = False
    dev_viz.property_inspector_window = inspector_window
    new_list = arcade.SpriteList([test_sprite])

    dev_viz.reset_scene(new_list)

    inspector_window.set_selection.assert_called_once_with([])


def test_detach_closes_property_inspector_window(mocker):
    """detach_from_window should close property inspector window and clear reference."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz._attached = True
    dev_viz._original_on_draw = window.on_draw
    dev_viz._original_on_key_press = window.on_key_press
    dev_viz._original_on_mouse_press = window.on_mouse_press
    dev_viz._original_on_mouse_drag = window.on_mouse_drag
    dev_viz._original_on_mouse_release = window.on_mouse_release
    dev_viz._original_on_close = window.on_close
    inspector_window = mocker.MagicMock()
    inspector_window.is_closed = False
    dev_viz.property_inspector_window = inspector_window

    dev_viz.detach_from_window()

    inspector_window.close.assert_called_once()
    assert dev_viz.property_inspector_window is None


def test_property_inspector_close_callback_clears_window_reference(mocker):
    """Close callback should clear stale property inspector reference."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.is_closed = True
    inspector_window.visible = False
    dev_viz.property_inspector_window = inspector_window

    dev_viz._on_property_inspector_close()

    assert dev_viz.property_inspector_window is None


def test_selection_sync_called_from_mouse_press_and_release(mocker):
    """Selection sync should run after selection manager handles click/marquee release."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sync = mocker.patch.object(dev_viz, "_sync_property_inspector_selection")
    mocker.patch("arcadeactions.dev.visualizer.arcade.get_sprites_at_point", return_value=[])
    dev_viz.selection_manager.handle_mouse_press = mocker.MagicMock(return_value=True)

    assert dev_viz.handle_mouse_press(10, 10, arcade.MOUSE_BUTTON_LEFT, 0) is True
    sync.assert_called_once()

    dev_viz.selection_manager._is_dragging_marquee = True
    dev_viz.selection_manager.handle_mouse_release = mocker.MagicMock()
    dev_viz.handle_mouse_release(10, 10, arcade.MOUSE_BUTTON_LEFT, 0)
    assert sync.call_count == 2


def test_draw_syncs_property_inspector_selection_before_render(mocker):
    """draw should sync inspector selection before delegating overlay draw."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz.visible = True
    sync = mocker.patch.object(dev_viz, "_sync_property_inspector_selection")
    draw_overlay = mocker.patch("arcadeactions.dev.visualizer.visualizer_draw.draw_visualizer")

    dev_viz.draw()

    sync.assert_called_once()
    draw_overlay.assert_called_once_with(dev_viz)


def test_toggle_property_inspector_switches_window_to_properties_mode(mocker):
    """Alt+I flow should reset inspector window mode back to properties."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.is_closed = False
    inspector_window.visible = False
    dev_viz.property_inspector_window = inspector_window

    dev_viz.toggle_property_inspector()

    inspector_window.show_properties_mode.assert_called_once_with()


def test_open_overrides_editor_for_sprite_shows_inspector_window(mocker):
    """Opening overrides editor should repurpose inspector window and hide legacy overlay."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite._source_markers = [{"file": "scene.py", "lineno": 42, "type": "arrange"}]
    dev_viz.scene_sprites.append(sprite)
    inspector_window = mocker.MagicMock()
    inspector_window.is_closed = False
    inspector_window.visible = False
    dev_viz.property_inspector_window = inspector_window
    dev_viz.overrides_panel.visible = True
    mocker.patch.object(dev_viz, "_property_inspector_window_needs_recreate", return_value=False)
    editor_ctor = mocker.patch("arcadeactions.dev.visualizer.ArrangeGridEditor", return_value=mocker.MagicMock())
    position = mocker.patch.object(dev_viz, "_position_property_inspector_window")

    opened = dev_viz.open_overrides_editor_for_sprite(sprite)

    assert opened is True
    editor_ctor.assert_called_once_with("scene.py", 42)
    assert inspector_window.show_arrange_mode.call_count == 1
    inspector_window.show_window.assert_called_once_with()
    assert dev_viz.overrides_panel.visible is False
    position.assert_called_once_with()


def test_open_overrides_editor_for_sprite_keeps_visible_window_position(mocker):
    """Arrange editor should update visible inspector content without reposition/show cycle."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite._source_markers = [{"file": "scene.py", "lineno": 42, "type": "arrange"}]
    dev_viz.scene_sprites.append(sprite)
    inspector_window = mocker.MagicMock()
    inspector_window.is_closed = False
    inspector_window.visible = True
    dev_viz.property_inspector_window = inspector_window
    mocker.patch.object(dev_viz, "_property_inspector_window_needs_recreate", return_value=False)
    mocker.patch("arcadeactions.dev.visualizer.ArrangeGridEditor", return_value=mocker.MagicMock())
    position = mocker.patch.object(dev_viz, "_position_property_inspector_window")

    opened = dev_viz.open_overrides_editor_for_sprite(sprite)

    assert opened is True
    inspector_window.show_arrange_mode.assert_called_once()
    position.assert_not_called()
    inspector_window.show_window.assert_not_called()


def test_open_overrides_editor_for_sprite_returns_false_without_panel(mocker):
    """Editor open should fail fast when sprite has no arrange marker."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite._source_markers = [{"file": "scene.py", "lineno": 12}]

    opened = dev_viz.open_overrides_editor_for_sprite(sprite)

    assert opened is False


def test_apply_arrange_layout_to_group_ignores_rows_cols_mismatch():
    """Layout apply should not raise when rows*cols differs from selected sprite count."""
    sprite_a = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite_b = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.BLUE)

    DevVisualizer._apply_arrange_layout_to_group(
        [sprite_a, sprite_b],
        {
            "rows": 3,
            "cols": 3,
            "start_x": 100.0,
            "start_y": 200.0,
            "spacing_x": 10.0,
            "spacing_y": 20.0,
        },
    )

    assert sprite_a.center_x == 100.0
    assert sprite_a.center_y == 200.0
    assert sprite_b.center_x == 110.0
    assert sprite_b.center_y == 200.0


def test_apply_arrange_layout_to_group_live_adds_sprites_when_needed(mocker):
    """Live arrange apply should add sprites so rows*cols count is reflected."""
    window = _make_window_stub(mocker)
    marker = {"file": "scene.py", "lineno": 42, "type": "arrange"}
    sprites = [arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED) for _ in range(6)]
    for sprite in sprites:
        sprite._source_markers = [marker]
    scene = arcade.SpriteList()
    for sprite in sprites:
        scene.append(sprite)
    dev_viz = DevVisualizer(scene_sprites=scene, window=window)
    dev_viz.selection_manager._selected.update(sprites)

    updated = dev_viz._apply_arrange_layout_to_group_live(
        sprites,
        {
            "rows": 1,
            "cols": 7,
            "start_x": 100.0,
            "start_y": 200.0,
            "spacing_x": 10.0,
            "spacing_y": 20.0,
        },
        marker_template=marker,
    )

    assert len(updated) == 7
    assert len(dev_viz.scene_sprites) == 7
    assert len(dev_viz.selection_manager.get_selected()) == 7


def test_apply_arrange_layout_to_group_live_removes_sprites_when_needed(mocker):
    """Live arrange apply should remove trailing sprites when rows*cols shrinks."""
    window = _make_window_stub(mocker)
    marker = {"file": "scene.py", "lineno": 42, "type": "arrange"}
    sprites = [arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED) for _ in range(6)]
    for sprite in sprites:
        sprite._source_markers = [marker]
    scene = arcade.SpriteList()
    for sprite in sprites:
        scene.append(sprite)
    dev_viz = DevVisualizer(scene_sprites=scene, window=window)
    dev_viz.selection_manager._selected.update(sprites)

    updated = dev_viz._apply_arrange_layout_to_group_live(
        sprites,
        {
            "rows": 1,
            "cols": 4,
            "start_x": 100.0,
            "start_y": 200.0,
            "spacing_x": 10.0,
            "spacing_y": 20.0,
        },
        marker_template=marker,
    )

    assert len(updated) == 4
    assert len(dev_viz.scene_sprites) == 4
    assert len(dev_viz.selection_manager.get_selected()) == 4


def test_click_normal_sprite_opens_property_inspector(mocker):
    """Plain left-click on a normal sprite should open inspector in properties mode."""
    window = _make_window_stub(mocker)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([sprite]), window=window)
    mocker.patch("arcadeactions.dev.visualizer.arcade.get_sprites_at_point", return_value=[sprite])
    dev_viz.selection_manager.handle_mouse_press = mocker.MagicMock(return_value=True)
    dev_viz.selection_manager.get_selected = mocker.MagicMock(return_value=[sprite])
    open_properties = mocker.patch.object(dev_viz, "open_property_inspector_for_current_selection")

    handled = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

    assert handled is True
    open_properties.assert_called_once_with()


def test_click_normal_sprite_updates_visible_inspector_without_recreate(mocker):
    """When inspector is visible, click should update selection/mode without reopen/recreate."""
    window = _make_window_stub(mocker)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([sprite]), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.visible = True
    inspector_window.is_closed = False
    dev_viz.property_inspector_window = inspector_window

    create_window = mocker.patch.object(dev_viz, "_create_property_inspector_window")
    mocker.patch("arcadeactions.dev.visualizer.arcade.get_sprites_at_point", return_value=[sprite])
    dev_viz.selection_manager.handle_mouse_press = mocker.MagicMock(return_value=True)
    dev_viz.selection_manager.get_selected = mocker.MagicMock(return_value=[sprite])

    handled = dev_viz.handle_mouse_press(100, 100, arcade.MOUSE_BUTTON_LEFT, 0)

    assert handled is True
    create_window.assert_not_called()
    inspector_window.show_properties_mode.assert_called_once_with()
    inspector_window.set_selection.assert_called_once_with([sprite])
    inspector_window.show_window.assert_not_called()
    inspector_window.hide_window.assert_not_called()


def test_open_property_inspector_returns_false_when_window_creation_fails(mocker):
    """open property inspector should return False when window cannot be created."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz.property_inspector_window = None
    mocker.patch.object(dev_viz, "_property_inspector_window_needs_recreate", return_value=True)
    mocker.patch.object(dev_viz, "_create_property_inspector_window", return_value=None)

    assert dev_viz.open_property_inspector_for_current_selection() is False


def test_open_property_inspector_returns_true_when_already_visible(mocker):
    """open property inspector should be a no-op success when window is already visible."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    inspector_window = mocker.MagicMock()
    inspector_window.visible = True
    inspector_window.is_closed = False
    dev_viz.property_inspector_window = inspector_window

    assert dev_viz.open_property_inspector_for_current_selection() is True
    inspector_window.show_window.assert_not_called()


def test_property_inspector_window_needs_recreate_cases(mocker):
    """needs_recreate should handle none/open/closed inspector states."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)

    dev_viz.property_inspector_window = None
    assert dev_viz._property_inspector_window_needs_recreate() is True

    live = mocker.MagicMock()
    live.is_closed = False
    dev_viz.property_inspector_window = live
    assert dev_viz._property_inspector_window_needs_recreate() is False

    closed = mocker.MagicMock()
    closed.is_closed = True
    dev_viz.property_inspector_window = closed
    assert dev_viz._property_inspector_window_needs_recreate() is True
    assert dev_viz.property_inspector_window is None


def test_arrange_marker_helpers_cover_invalid_inputs(mocker, tmp_path):
    """Arrange marker helper methods should gracefully reject malformed markers."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)

    assert dev_viz._arrange_marker_key({"file": "scene.py"}) is None
    assert dev_viz._arrange_marker_key({"file": "scene.py", "lineno": "bad"}) is None
    assert dev_viz._first_arrange_marker(object()) is None
    assert dev_viz.sprite_has_arrange_marker(object()) is False

    path = tmp_path / "scene.py"
    path.write_text("x = 1\nnot_arrange()\n", encoding="utf-8")
    assert dev_viz._marker_points_to_arrange_call({"file": str(path), "lineno": 2}) is False
    assert dev_viz._marker_points_to_arrange_call({"file": str(path), "lineno": 0}) is False
    assert dev_viz._marker_points_to_arrange_call({"file": str(path), "lineno": "bad"}) is False


def test_open_overrides_editor_returns_false_for_invalid_marker_key(mocker):
    """Arrange editor open should fail when marker key extraction fails."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite._source_markers = [{"file": "scene.py", "lineno": "bad", "type": "arrange"}]

    assert dev_viz.open_overrides_editor_for_sprite(sprite) is False


def test_open_overrides_editor_returns_false_when_window_creation_still_missing(mocker):
    """Arrange editor open should fail if inspector window cannot be created."""
    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite._source_markers = [{"file": "scene.py", "lineno": 42, "type": "arrange"}]
    dev_viz.property_inspector_window = None
    mocker.patch.object(dev_viz, "_property_inspector_window_needs_recreate", return_value=True)
    mocker.patch.object(dev_viz, "_create_property_inspector_window", return_value=None)

    assert dev_viz.open_overrides_editor_for_sprite(sprite) is False


def test_apply_arrange_layout_to_group_and_live_handle_non_positive_dims(mocker):
    """Arrange layout helpers should no-op for non-positive rows/cols."""
    sprite = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    old_pos = (sprite.center_x, sprite.center_y)
    DevVisualizer._apply_arrange_layout_to_group(
        [sprite],
        {"rows": 0, "cols": 1, "start_x": 1.0, "start_y": 2.0, "spacing_x": 3.0, "spacing_y": 4.0},
    )
    assert (sprite.center_x, sprite.center_y) == old_pos

    window = _make_window_stub(mocker)
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList([sprite]), window=window)
    updated = dev_viz._apply_arrange_layout_to_group_live(
        [sprite],
        {"rows": 0, "cols": 0, "start_x": 1.0, "start_y": 2.0, "spacing_x": 3.0, "spacing_y": 4.0},
        marker_template={"file": "scene.py", "lineno": 1, "type": "arrange"},
    )
    assert updated == [sprite]


def test_detach_restores_wrapped_view_handlers_and_cleans_up_attrs(mocker):
    """detach_from_window should restore wrapped view callbacks and delete stash attrs."""
    window = _make_window_stub(mocker)
    current_view = mocker.MagicMock()
    current_view.on_draw = mocker.MagicMock()
    current_view.on_key_press = mocker.MagicMock()
    current_view.on_mouse_press = mocker.MagicMock()
    current_view.on_mouse_drag = mocker.MagicMock()
    current_view.on_mouse_release = mocker.MagicMock()
    orig_draw = mocker.MagicMock()
    orig_key = mocker.MagicMock()
    orig_press = mocker.MagicMock()
    orig_drag = mocker.MagicMock()
    orig_release = mocker.MagicMock()
    current_view._dev_viz_original_on_draw = orig_draw
    current_view._dev_viz_original_on_key_press = orig_key
    current_view._dev_viz_original_on_mouse_press = orig_press
    current_view._dev_viz_original_on_mouse_drag = orig_drag
    current_view._dev_viz_original_on_mouse_release = orig_release
    window.current_view = current_view

    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList(), window=window)
    dev_viz._attached = True
    dev_viz._original_on_draw = window.on_draw
    dev_viz._original_on_key_press = window.on_key_press
    dev_viz._original_on_mouse_press = window.on_mouse_press
    dev_viz._original_on_mouse_drag = window.on_mouse_drag
    dev_viz._original_on_mouse_release = window.on_mouse_release
    dev_viz._original_on_close = window.on_close
    dev_viz._original_show_view = window.show_view

    dev_viz.detach_from_window()

    assert current_view.on_draw is orig_draw
    assert current_view.on_key_press is orig_key
    assert current_view.on_mouse_press is orig_press
    assert current_view.on_mouse_drag is orig_drag
    assert current_view.on_mouse_release is orig_release
    assert not hasattr(current_view, "_dev_viz_original_on_draw")
