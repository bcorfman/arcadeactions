"""Keyboard handling helpers for DevVisualizer."""

from __future__ import annotations

import os
from typing import Any

import arcade


def handle_key_press(dev_viz: Any, key: int, modifiers: int) -> bool:
    if key == arcade.key.I and modifiers & arcade.key.MOD_ALT:
        dev_viz.toggle_property_inspector()
        return True

    if key == arcade.key.F11:
        dev_viz.toggle_palette()
        return True

    if key == arcade.key.F8:
        dev_viz.toggle_command_palette()
        return True

    if key == arcade.key.E:
        return _export_scene(dev_viz)

    if key == arcade.key.I:
        return _import_scene(dev_viz)

    if key in (arcade.key.DELETE, arcade.key.BACKSPACE):
        return _delete_selected(dev_viz)

    return False


def _export_scene(dev_viz: Any) -> bool:
    from arcadeactions.dev.templates import export_template

    filename = "scene.yaml"
    if os.path.exists("examples"):
        filename = "examples/boss_level.yaml"
    elif os.path.exists("scenes"):
        filename = "scenes/new_scene.yaml"

    export_template(dev_viz.scene_sprites, filename, prompt_user=False)
    print(f"✓ Exported {len(dev_viz.scene_sprites)} sprites to {filename}")
    return True


def _import_scene(dev_viz: Any) -> bool:
    from arcadeactions.dev.templates import load_scene_template

    for filename in ["scene.yaml", "examples/boss_level.yaml", "scenes/new_scene.yaml"]:
        if os.path.exists(filename):
            load_scene_template(filename, dev_viz.ctx)
            print(f"✓ Imported scene from {filename} ({len(dev_viz.scene_sprites)} sprites)")
            return True
    print("⚠ No scene file found. Try: scene.yaml, examples/boss_level.yaml, or scenes/new_scene.yaml")
    return True


def _delete_selected(dev_viz: Any) -> bool:
    selected = dev_viz.selection_manager.get_selected()
    if not selected:
        return False

    for sprite in selected:
        if sprite in dev_viz.scene_sprites:
            dev_viz.scene_sprites.remove(sprite)
        if sprite in dev_viz._gizmos:
            del dev_viz._gizmos[sprite]
        if sprite in dev_viz._gizmo_miss_refresh_at:
            del dev_viz._gizmo_miss_refresh_at[sprite]
    dev_viz.selection_manager.clear_selection()
    print(f"✓ Deleted {len(selected)} sprite(s)")
    return True
