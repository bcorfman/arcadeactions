"""Unit tests for SpritePropertyRegistry value read/write behavior."""

from __future__ import annotations

import pytest

from arcadeactions.dev.property_registry import SpritePropertyRegistry


def test_get_and_set_position_property(test_sprite):
    """Position tuple should map to center_x/center_y fields."""
    registry = SpritePropertyRegistry()

    registry.set_value(test_sprite, "position", (111, 222))

    assert registry.get_value(test_sprite, "position") == (111, 222)
    assert test_sprite.center_x == 111
    assert test_sprite.center_y == 222


def test_opacity_alias_reads_and_writes_alpha(test_sprite):
    """Opacity should be an alias for alpha."""
    registry = SpritePropertyRegistry()

    registry.set_value(test_sprite, "opacity", 90)

    assert registry.get_value(test_sprite, "opacity") == 90
    assert test_sprite.alpha == 90


def test_custom_property_round_trip(test_sprite):
    """Custom properties should be written/read from __dict__."""
    registry = SpritePropertyRegistry()

    registry.set_value(test_sprite, "custom_flag", "ready")

    assert registry.get_value(test_sprite, "custom_flag") == "ready"


def test_get_unknown_property_raises_key_error(test_sprite):
    """Unknown properties should fail fast with KeyError."""
    registry = SpritePropertyRegistry()

    with pytest.raises(KeyError):
        registry.get_value(test_sprite, "missing_property")


def test_editor_type_inference_for_common_custom_types(test_sprite):
    """Custom property editor type should be inferred from sample value type."""
    registry = SpritePropertyRegistry()
    test_sprite.bool_flag = True
    test_sprite.number_value = 1.5
    test_sprite.vector_value = (1, 2)
    test_sprite.dict_value = {"x": 1}

    props = registry.properties_for_selection([test_sprite])
    by_name = {prop.name: prop.editor_type for prop in props}

    assert by_name["bool_flag"] == "bool"
    assert by_name["number_value"] == "number"
    assert by_name["vector_value"] == "vector2"
    assert by_name["dict_value"] == "dict"


def test_editor_type_defaults_to_text_for_unknown_custom_value(test_sprite):
    """Unknown custom value types should use text editor fallback."""

    class _CustomValue:
        pass

    registry = SpritePropertyRegistry()
    test_sprite.custom_object = _CustomValue()

    props = registry.properties_for_selection([test_sprite])
    by_name = {prop.name: prop.editor_type for prop in props}

    assert by_name["custom_object"] == "text"
