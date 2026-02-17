"""Unit tests for sprite property inspector editing flows."""

from __future__ import annotations

import arcade

from arcadeactions.dev.property_history import PropertyHistory
from arcadeactions.dev.property_inspector import SpritePropertyInspector
from arcadeactions.dev.property_registry import SpritePropertyRegistry


class _WindowStub:
    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.width = width
        self.height = height


def _make_inspector() -> SpritePropertyInspector:
    inspector = SpritePropertyInspector(
        property_registry=SpritePropertyRegistry(),
        history=PropertyHistory(max_changes_per_sprite=20),
        window=_WindowStub(),
    )
    return inspector


def test_edit_center_x_updates_sprite_immediately(test_sprite):
    """Applying an edited value should immediately update the sprite property."""
    inspector = _make_inspector()
    inspector.set_selection([test_sprite])

    inspector.apply_property_text("center_x", "420")

    assert test_sprite.center_x == 420


def test_multi_select_angle_edit_updates_all_sprites():
    """Batch edit should apply the same property value to all selected sprites."""
    sprite_a = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.RED)
    sprite_b = arcade.SpriteSolidColor(width=8, height=8, color=arcade.color.BLUE)

    inspector = _make_inspector()
    inspector.set_selection([sprite_a, sprite_b])

    inspector.apply_property_text("angle", "45")

    assert sprite_a.angle == 45
    assert sprite_b.angle == 45


def test_expression_support_uses_screen_center_constant(test_sprite):
    """Numeric expressions should evaluate with SCREEN_CENTER constants."""
    inspector = _make_inspector()
    inspector.set_selection([test_sprite])

    inspector.apply_property_text("center_x", "SCREEN_CENTER + 100")

    assert test_sprite.center_x == 500


def test_copy_as_python_generates_assignments_for_selection(test_sprite):
    """Copy helper should emit Python assignment lines."""
    inspector = _make_inspector()
    test_sprite.center_x = 410
    test_sprite.angle = 30
    inspector.set_selection([test_sprite])

    snippet = inspector.copy_selection_as_python(property_names=["center_x", "angle"])

    assert "sprite.center_x = 410" in snippet
    assert "sprite.angle = 30" in snippet


def test_undo_redo_property_edits(test_sprite):
    """Inspector undo/redo should replay recorded property edits."""
    inspector = _make_inspector()
    inspector.set_selection([test_sprite])
    start_x = float(test_sprite.center_x)

    inspector.apply_property_text("center_x", "333")
    assert test_sprite.center_x == 333

    assert inspector.undo() is True
    assert test_sprite.center_x == start_x

    assert inspector.redo() is True
    assert test_sprite.center_x == 333


def test_apply_property_text_returns_false_when_selection_is_empty():
    """No selection should result in no-op edits."""
    inspector = _make_inspector()

    assert inspector.apply_property_text("center_x", "100") is False


def test_copy_selection_as_python_empty_selection_returns_empty():
    """Copy helper should return empty snippet when nothing is selected."""
    inspector = _make_inspector()

    snippet = inspector.copy_selection_as_python()

    assert snippet == ""


def test_copy_current_property_handles_no_current_property_or_selection(test_sprite):
    """Copy-current should return empty when no current property/selection exists."""
    inspector = _make_inspector()

    assert inspector.copy_current_property() == ""

    inspector.set_selection([test_sprite])
    inspector.set_selection([])
    assert inspector.copy_current_property() == ""


def test_move_active_property_and_visibility_helpers(test_sprite):
    """Selection/property navigation helpers should be stable for empty/non-empty lists."""
    inspector = _make_inspector()

    assert inspector.current_property() is None
    inspector.move_active_property(1)
    assert inspector.current_property() is None

    inspector.set_selection([test_sprite])
    assert inspector.selection() == [test_sprite]
    props = inspector.visible_properties()
    assert props
    first = inspector.current_property()
    inspector.move_active_property(1)
    assert inspector.current_property() is not None
    if len(props) > 1:
        assert inspector.current_property().name != first.name


def test_undo_uses_last_non_empty_selection(test_sprite):
    """Undo/redo should still work after selection becomes empty."""
    inspector = _make_inspector()
    inspector.set_selection([test_sprite])
    inspector.apply_property_text("center_x", "350")
    inspector.set_selection([])

    assert inspector.undo() is True
    assert inspector.redo() is True
