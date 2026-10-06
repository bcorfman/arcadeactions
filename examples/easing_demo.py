"""
Ease Wrapper Demo using ArcadeActions

This example shows how to use ArcadeActions' Ease wrapper class to create smooth acceleration
and deceleration effects for continuous actions. Each missile launches with different easing curves,
smoothly accelerating to cruise speed and then continuing at that speed until hitting a boundary.

Ease is perfect for this use case because:
- Missiles need realistic acceleration from 0 to cruise speed
- After acceleration completes, missiles should continue at constant velocity
- We want smooth transitions into continuous movement, not precise A-to-B positioning

This is different from TweenUntil, which would be used for precise property animation
that stops at a target value (like UI elements or health bars).

From the project root, run with:
    uv run python examples/easing_demo.py
"""

import arcade
from arcadeactions import easing
from arcade.types import Color

from arcadeactions import Action, center_window, ease, infinite, seconds_to_frames

# --- Constants ---
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "ArcadeActions Ease Wrapper Demo"

BACKGROUND_COLOR = "#2C3E50"
TEXT_COLOR = "#ECF0F1"
MISSILE_COLOR = "#E74C3C"
TRAIL_COLOR = "#F39C12"
LINE_COLOR = "#3498DB"
LINE_WIDTH = 2

X_START = 250
MISSILE_VELOCITY = 5  # pixels per frame cruise speed (300 pixels/second at 60 FPS)
Y_INTERVAL = 60
MISSILE_SIZE = 8
EASING_DURATION_SECONDS = 2.0  # friendliness constant for explanation
EASING_FRAMES = seconds_to_frames(EASING_DURATION_SECONDS)

# List of (easing function, label) to demonstrate with Ease wrapper
EASING_FUNCTIONS = [
    (easing.linear, "Linear"),
    (easing.ease_out, "Ease out"),
    (easing.ease_in, "Ease in"),
    (easing.ease_in_out, "Ease in/out"),
    (easing.ease_out_elastic, "Ease out elastic"),
    (easing.ease_in_back, "Ease in back"),
    (easing.ease_out_back, "Ease out back"),
]


class Missile(arcade.SpriteCircle):
    """A missile that can be launched with smooth acceleration using Ease wrapper."""

    def __init__(self, radius, color):
        super().__init__(radius, color)
        self.trail_points = []
        self.max_trail_length = 20

    def update(self, delta_time=None, *args, **kwargs):
        super().update(delta_time, *args, **kwargs)

        # Add current position to trail
        self.trail_points.append((self.center_x, self.center_y))
        if len(self.trail_points) > self.max_trail_length:
            self.trail_points.pop(0)


class EaseDemoView(arcade.View):
    """Main application view for the Ease wrapper demo."""

    def __init__(self):
        super().__init__()
        self.background_color = Color.from_hex_string(BACKGROUND_COLOR)
        self.missile_list = arcade.SpriteList()
        self.text_list = []
        self.lines = arcade.shape_list.ShapeElementList()

    def setup(self):
        text_color = Color.from_hex_string(TEXT_COLOR)
        line_color = Color.from_hex_string(LINE_COLOR)

        y = Y_INTERVAL
        for ease_func, label in EASING_FUNCTIONS:
            # Create missile
            missile = Missile(MISSILE_SIZE, Color.from_hex_string(MISSILE_COLOR))
            missile.position = (X_START, y)
            self.missile_list.append(missile)

            # Create reference line showing launch path
            line = arcade.shape_list.create_line(
                X_START,
                y,
                WINDOW_WIDTH - 60,
                y,
                line_color,
                line_width=LINE_WIDTH,
            )
            self.lines.append(line)

            # Create label
            text = arcade.Text(
                label,
                x=X_START - 50,
                y=y - 5,
                color=text_color,
                font_size=16,
                anchor_x="right",
            )
            self.text_list.append(text)

            # Launch missile with Ease wrapper for smooth acceleration
            self._launch_missile(missile, ease_func, label)

            y += Y_INTERVAL

    def _launch_missile(self, missile, ease_func, label):
        """Launch a missile with smooth acceleration using Ease wrapper."""

        def on_boundary_hit(sprite, axis, side):
            """Clear trail when missile wraps to the other side."""
            if side == "right":  # Only clear trail when wrapping from right edge
                sprite.trail_points.clear()

        # Create continuous movement action (missile flies until hitting boundary)
        # Note: Don't apply the action yet - Ease will apply it
        from arcadeactions.conditional import MoveUntil

        # Edge-based bounds: missile is 16px wide (radius=8), so add half-width to boundaries
        # This allows the sprite center to reach the full window width
        bounds = (-8, -8, WINDOW_WIDTH + 8, WINDOW_HEIGHT + 8)
        continuous_flight = MoveUntil(
            velocity=(MISSILE_VELOCITY, 0),  # Cruise velocity
            condition=infinite,  # Never stop on its own
            bounds=bounds,
            boundary_behavior="wrap",
            on_boundary_enter=on_boundary_hit,
        )

        # Wrap with Ease for smooth acceleration to cruise speed
        ease(missile, continuous_flight, frames=EASING_FRAMES, ease_function=ease_func)

    def on_draw(self):
        self.clear()

        # Draw reference lines
        self.lines.draw()

        # Draw missile trails
        trail_color = Color.from_hex_string(TRAIL_COLOR)
        for missile in self.missile_list:
            if len(missile.trail_points) > 1:
                for i in range(len(missile.trail_points) - 1):
                    alpha = int(255 * (i / len(missile.trail_points)))
                    trail_color_faded = (*trail_color[:3], alpha)
                    arcade.draw_line(
                        missile.trail_points[i][0],
                        missile.trail_points[i][1],
                        missile.trail_points[i + 1][0],
                        missile.trail_points[i + 1][1],
                        trail_color_faded,
                        2,
                    )

        # Draw missiles
        self.missile_list.draw()

        # Draw labels
        for text in self.text_list:
            text.draw()

        # Draw instructions
        instructions = arcade.Text(
            "Watch how each missile accelerates differently to the same cruise speed",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - 30,
            color=Color.from_hex_string(TEXT_COLOR),
            font_size=18,
            anchor_x="center",
        )
        instructions.draw()

    def on_update(self, delta_time):
        # Update all ArcadeActions (handles Easing wrapper and continuous movement)
        Action.update_all(delta_time)

        # Update missiles (applies velocities and updates trails)
        self.missile_list.update(delta_time)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.close()


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, visible=False)
    center_window(window)
    window.set_visible(True)
    view = EaseDemoView()
    view.setup()
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    main()
