"""
Starfield demo showcasing ArcadeActions MoveUntil with wrapping boundaries.

This was intentionally built to resemble the starfield in Galaga.

Press ESC at any time to exit the application.

This example intentionally keeps the implementation minimal while still
following the project design guidelines (see docs/api_usage_guide.md).
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable

import arcade
from arcadeactions import easing

from arcadeactions import (
    Action,
    BlinkUntil,
    DelayFrames,
    MoveUntil,
    TweenUntil,
    center_window,
    infinite,
)
from arcadeactions.frame_timing import after_frames

# ---------------------------------------------------------------------------
# Window configuration
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 1280
WINDOW_TITLE = "ArcadeActions Starfield"

# ---------------------------------------------------------------------------
# Blink configuration
# ---------------------------------------------------------------------------
BLINK_GROUP_COUNT = 5
BLINK_RATE_MIN_FRAMES = 12  # ~0.2 seconds at 60 FPS
BLINK_RATE_MAX_FRAMES = 24  # ~0.4 seconds at 60 FPS
STAR_VELOCITY_TAG = "star_velocity_phase"

# ---------------------------------------------------------------------------
# Starfield configuration
# ---------------------------------------------------------------------------
# Number of stars per layer. Feel free to tweak for denser / sparser fields.
MAX_STARS: int = 400
# A small margin lets us spawn stars just outside the visible area so they
# don't wrap immediately when the demo starts.
VERTICAL_MARGIN: int = 5

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _random_star_position() -> tuple[float, float]:
    """Return a random (x, y) position slightly above the top of the screen."""
    x = random.uniform(0, WINDOW_WIDTH)
    y = random.uniform(0, WINDOW_HEIGHT) + 5
    return x, y


def _create_star_sprite(color: arcade.Color, size: int = 2) -> arcade.Sprite:
    """Create a tiny square sprite representing a single star."""
    sprite = arcade.SpriteSolidColor(size, size, color=color)
    sprite.center_x, sprite.center_y = _random_star_position()
    return sprite


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------
class StarfieldView(arcade.View):
    """Simple starfield rendered using five independent sprite lists."""

    def __init__(self):
        super().__init__()

        self.star_list = arcade.SpriteList()
        self._blink_groups: list[arcade.SpriteList] = []
        self._current_phase_action = None
        self._setup_stars()

        # A solid black background keeps the focus on the starfield.
        self.background_color = arcade.color.BLACK

    # ---------------------------------------------------------------------
    # Setup helpers
    # ---------------------------------------------------------------------
    def on_stars_wrap(self, sprite, axis):
        # When a star hits a vertical boundary, wrap it to the opposite side.
        # We check the direction of movement to decide which edge to wrap to.
        if sprite.change_y < 0:
            # Moving down, wrap to top
            sprite.position = (random.uniform(0, WINDOW_WIDTH), WINDOW_HEIGHT + VERTICAL_MARGIN)
        else:
            # Moving up, wrap to bottom
            sprite.position = (random.uniform(0, WINDOW_WIDTH), -VERTICAL_MARGIN)

    def _setup_stars(self) -> None:
        """Populate sprite list with stars, and start actions."""
        bounds = (0, -VERTICAL_MARGIN, WINDOW_WIDTH, WINDOW_HEIGHT + VERTICAL_MARGIN)

        blink_rates = [
            int(BLINK_RATE_MIN_FRAMES + i * (BLINK_RATE_MAX_FRAMES - BLINK_RATE_MIN_FRAMES) / (BLINK_GROUP_COUNT - 1))
            for i in range(BLINK_GROUP_COUNT)
        ]
        self._blink_groups = [arcade.SpriteList() for _ in range(BLINK_GROUP_COUNT)]
        group_indices = list(range(BLINK_GROUP_COUNT))
        random.shuffle(group_indices)
        group_cycle = itertools.cycle(group_indices)

        for _ in range(MAX_STARS):
            color = (random.randint(20, 255), random.randint(20, 255), random.randint(20, 255))
            star = _create_star_sprite(color, size=3)
            self.star_list.append(star)

            group_index = next(group_cycle)
            self._blink_groups[group_index].append(star)

        for blink_list, blink_rate_frames in zip(self._blink_groups, blink_rates):
            if len(blink_list) == 0:
                continue
            BlinkUntil(frames_until_change=blink_rate_frames, condition=infinite).apply(blink_list)

        # Action 1: A permanent action that handles boundary checking and wrapping.
        # It has zero velocity so it only enforces the rules, it doesn't cause movement.
        wrapping_action = MoveUntil(
            velocity=(0, 0),
            condition=infinite,
            bounds=bounds,
            boundary_behavior="wrap",
            on_boundary_exit=self.on_stars_wrap,
        )
        wrapping_action.apply(self.star_list)

        # Action 2: A phase-driven velocity loop that re-applies itself.
        self._start_velocity_cycle()

    # ---------------------------------------------------------------------
    # Velocity control helpers
    # ---------------------------------------------------------------------
    def _start_velocity_cycle(self) -> None:
        Action.stop_actions_for_target(self.star_list, tag=STAR_VELOCITY_TAG)
        self._set_velocity(0.0)
        self._schedule_delay(60, self._accelerate_forward)  # 1 second at 60 FPS

    def _accelerate_forward(self) -> None:
        self._apply_tween(
            target_value=-4.0,
            frames=120,  # 2 seconds at 60 FPS
            ease_function=easing.ease_in,
            next_step=self._hold_forward_speed,
        )

    def _hold_forward_speed(self) -> None:
        self._hold_velocity(-4.0, 300, self._accelerate_reverse)  # 5 seconds at 60 FPS

    def _accelerate_reverse(self) -> None:
        self._apply_tween(
            target_value=14.0,
            frames=30,  # 0.5 seconds at 60 FPS
            ease_function=easing.ease_out,
            next_step=self._hold_reverse_speed,
        )

    def _hold_reverse_speed(self) -> None:
        self._hold_velocity(14.0, 90, self._decelerate_to_stop)  # 1.5 seconds at 60 FPS

    def _decelerate_to_stop(self) -> None:
        self._apply_tween(
            target_value=0.0,
            frames=120,  # 2 seconds at 60 FPS
            ease_function=easing.ease_out,
            next_step=self._start_velocity_cycle,
        )

    def _schedule_delay(self, frames: int, next_step: Callable[[], None]) -> None:
        delay_action = DelayFrames(frames=frames, on_stop=lambda _info=None: next_step())
        self._current_phase_action = delay_action.apply(self.star_list, tag=STAR_VELOCITY_TAG)

    def _apply_tween(
        self,
        target_value: float,
        frames: int,
        ease_function: Callable[[float], float],
        next_step: Callable[[], None],
    ) -> None:
        start_value = self._current_velocity()
        tween_action = TweenUntil(
            start_value=start_value,
            end_value=target_value,
            property_name="change_y",
            condition=after_frames(frames),
            on_stop=lambda _result=None: next_step(),
            ease_function=ease_function,
        )
        self._current_phase_action = tween_action.apply(self.star_list, tag=STAR_VELOCITY_TAG)

    def _hold_velocity(self, velocity: float, frames: int, next_step: Callable[[], None]) -> None:
        self._set_velocity(velocity)
        self._schedule_delay(frames, next_step)

    def _set_velocity(self, velocity: float) -> None:
        for sprite in self.star_list:
            sprite.change_y = velocity

    def _current_velocity(self) -> float:
        if len(self.star_list) == 0:
            return 0.0
        return self.star_list[0].change_y

    # ---------------------------------------------------------------------
    # Arcade callbacks
    # ---------------------------------------------------------------------
    def on_update(self, delta_time: float):
        # Update all active actions first (updates velocities & wrapping).
        Action.update_all(delta_time)

        # Apply velocities to sprites.
        self.star_list.update()

    def on_draw(self):
        # Clear screen (preferred over arcade.start_render() inside a View).
        self.clear()
        self.star_list.draw()

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.ESCAPE:
            self.window.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, visible=False, vsync=True)
    center_window(window)
    window.set_visible(True)
    window.show_view(StarfieldView())
    arcade.run()


if __name__ == "__main__":
    main()
