"""
Instant actions for immediate sprite repositioning.

MoveTo: Set absolute position (center_x, center_y)
MoveBy: Offset current position by (dx, dy)
"""

from __future__ import annotations

from typing import Any

from .base import Action as _Action


class MoveTo(_Action):
    """Instantly move a sprite or sprite list to an absolute position.

    Usage:
        MoveTo((x, y)).apply(sprite)
        MoveTo(x, y).apply(sprite)  # Also accepts separate arguments
    """

    def __init__(self, x_or_position, y=None, on_stop: Any | None = None):
        # No condition; completes immediately in apply_effect
        super().__init__(condition=None, on_stop=on_stop)

        # Handle both tuple and separate argument forms
        if y is None:
            # Tuple form: MoveTo((x, y))
            if not isinstance(x_or_position, (tuple, list)) or len(x_or_position) != 2:
                raise ValueError("Position must be a tuple/list of (x, y) coordinates")
            self.target_position = tuple(x_or_position)
        else:
            # Separate argument form: MoveTo(x, y)
            self.target_position = (x_or_position, y)

    def apply_effect(self) -> None:
        tx, ty = self.target_position

        def _set_pos(sprite):
            sprite.center_x = tx
            sprite.center_y = ty

        self.for_each_sprite(_set_pos)

        # Complete instantly
        self._complete_action(mark_condition_met=True, callback_payload=None)
        # Remove from active actions immediately
        self.stop()

    def update(self, delta_time: float) -> None:
        """Override to execute when not paused (handles pause/resume).

        Uses existing _paused flag and done state - no new flags needed.
        """
        if not self._is_active or self.done:
            return

        # If paused, don't execute (wait for resume)
        if self._paused:
            return

        # Not paused and not done - execute the move
        self.apply_effect()

    def clone(self) -> MoveTo:
        return MoveTo(self.target_position, on_stop=self.on_stop)


class MoveBy(_Action):
    """Instantly offset a sprite or sprite list by (dx, dy).

    Usage:
        MoveBy((dx, dy)).apply(sprite)
        MoveBy(dx, dy).apply(sprite)  # Also accepts separate arguments
    """

    def __init__(self, dx_or_offset, dy=None, on_stop: Any | None = None):
        # No condition; completes immediately in apply_effect
        super().__init__(condition=None, on_stop=on_stop)

        # Handle both tuple and separate argument forms
        if dy is None:
            # Tuple form: MoveBy((dx, dy))
            if not isinstance(dx_or_offset, (tuple, list)) or len(dx_or_offset) != 2:
                raise ValueError("Offset must be a tuple/list of (dx, dy) coordinates")
            self.offset = tuple(dx_or_offset)
        else:
            # Separate argument form: MoveBy(dx, dy)
            self.offset = (dx_or_offset, dy)

    def apply_effect(self) -> None:
        dx, dy = self.offset

        def _add_pos(sprite):
            sprite.center_x += dx
            sprite.center_y += dy

        self.for_each_sprite(_add_pos)

        # Complete instantly
        self._complete_action(mark_condition_met=True, callback_payload=None)
        # Remove from active actions immediately
        self.stop()

    def update(self, delta_time: float) -> None:
        """Override to execute when not paused (handles pause/resume).

        Uses existing _paused flag and done state - no new flags needed.
        """
        if not self._is_active or self.done:
            return

        # If paused, don't execute (wait for resume)
        if self._paused:
            return

        # Not paused and not done - execute the move
        self.apply_effect()

    def clone(self) -> MoveBy:
        return MoveBy(self.offset, on_stop=self.on_stop)
