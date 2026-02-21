"""Window-free prototype palette panel for one-window DevShell mode."""

from __future__ import annotations

import arcade


class DevShellPrototypePalettePanel:
    """Panel controller for prototype listing and spawn actions."""

    def __init__(self, *, registry, dev_context) -> None:
        self._registry = registry
        self._dev_context = dev_context
        self.visible = False
        self.selected_index = 0

    def set_visible(self, value: bool) -> None:
        self.visible = bool(value)
        if self.visible:
            self._clamp_selected_index()

    def toggle_visible(self) -> None:
        self.set_visible(not self.visible)

    def prototype_ids(self) -> list[str]:
        return list(self._registry.all().keys())

    def spawn_selected(self) -> bool:
        prototypes = self.prototype_ids()
        if not prototypes:
            self.selected_index = 0
            return False
        self._clamp_selected_index()
        return self.spawn_by_id(prototypes[self.selected_index])

    def spawn_by_id(self, prototype_id: str) -> bool:
        if not self._registry.has(prototype_id):
            return False
        sprite = self._registry.create(prototype_id, self._dev_context)
        sprite.center_x = 640
        sprite.center_y = 360
        if self._dev_context.scene_sprites is None:
            return False
        self._dev_context.scene_sprites.append(sprite)
        return True

    def on_key_press(self, key: int, modifiers: int) -> bool:
        del modifiers
        if not self.visible:
            return False
        if key in (arcade.key.ESCAPE, arcade.key.F11):
            self.set_visible(False)
            return True
        if key == arcade.key.DOWN:
            self._move_selection(1)
            return True
        if key == arcade.key.UP:
            self._move_selection(-1)
            return True
        if key == arcade.key.ENTER:
            return self.spawn_selected()
        return False

    def on_text(self, text: str) -> bool:
        del text
        return False

    def on_text_motion(self, motion: int) -> bool:
        del motion
        return False

    def _clamp_selected_index(self) -> None:
        prototypes = self.prototype_ids()
        if not prototypes:
            self.selected_index = 0
            return
        if self.selected_index < 0:
            self.selected_index = 0
        if self.selected_index >= len(prototypes):
            self.selected_index = len(prototypes) - 1

    def _move_selection(self, direction: int) -> None:
        prototypes = self.prototype_ids()
        if not prototypes:
            self.selected_index = 0
            return
        self.selected_index = (self.selected_index + int(direction)) % len(prototypes)
