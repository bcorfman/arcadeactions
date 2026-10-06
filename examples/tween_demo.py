"""
TweenUntil Demo using ArcadeActions

This example shows how to use ArcadeActions' TweenUntil action to animate sprite properties
with different easing functions. Each ball moves horizontally from left to right using precise
A-to-B position animation, demonstrating various easing curves applied to the tweening.

TweenUntil is perfect for this use case because:
- Each ball needs to move from exact start position to exact end position
- The animation should stop when reaching the target position
- We want precise control over the position property with easing curves

This is different from the Ease wrapper class, which would be used for smooth acceleration
into continuous movement (like missile launches or vehicle acceleration).

From the project root, run with:
    uv run python examples/tween_demo.py

"""

import arcade
from arcadeactions import easing
from arcade.types import Color

from arcadeactions import Action, center_window, tween_until
from arcadeactions.frame_timing import after_frames, seconds_to_frames

# --- Constants ---
SPRITE_SCALING = 0.5
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "ArcadeActions TweenUntil Demo"

BACKGROUND_COLOR = "#F5D167"
TEXT_COLOR = "#4B1DF2"
BALL_COLOR = "#42B5EB"
LINE_COLOR = "#45E6D0"
LINE_WIDTH = 3

X_START = 40
X_END = 1200
Y_INTERVAL = 60
BALL_RADIUS = 13
TWEEN_FRAMES = seconds_to_frames(6.0)  # 360 frames at 60 FPS

# List of (easing function, label) to demonstrate with TweenUntil
EASING_FUNCTIONS = [
    (easing.linear, "Linear"),
    (easing.ease_out, "Ease out"),
    (easing.ease_in, "Ease in"),
    (easing.smoothstep, "Smoothstep"),
    (easing.ease_in_out, "Ease in/out"),
    (easing.ease_out_elastic, "Ease out elastic"),
    (easing.ease_in_back, "Ease in back"),
    (easing.ease_out_back, "Ease out back"),
    (easing.ease_in_sin, "Ease in sin"),
    (easing.ease_out_sin, "Ease out sin"),
    (easing.ease_in_out_sin, "Ease in out sin"),
]


class AnimatedBall(arcade.SpriteCircle):
    """A ball that can be animated with ArcadeActions TweenUntil."""

    def __init__(self, radius, color):
        super().__init__(radius, color)


class InterpolateDemoView(arcade.View):
    """Main application view for the TweenUntil demo."""

    def __init__(self):
        super().__init__()
        self.background_color = Color.from_hex_string(BACKGROUND_COLOR)
        self.ball_list = arcade.SpriteList()
        self.text_list = []
        self.lines = arcade.shape_list.ShapeElementList()

    def setup(self):
        text_color = Color.from_hex_string(TEXT_COLOR)
        line_color = Color.from_hex_string(LINE_COLOR)
        y = Y_INTERVAL
        for ease_func, label in EASING_FUNCTIONS:
            # Create ball
            ball = AnimatedBall(BALL_RADIUS, Color.from_hex_string(BALL_COLOR))
            ball.position = (X_START, y)
            self.ball_list.append(ball)
            # Create line
            line = arcade.shape_list.create_line(
                X_START,
                y - BALL_RADIUS - LINE_WIDTH,
                X_END,
                y - BALL_RADIUS,
                line_color,
                line_width=LINE_WIDTH,
            )
            self.lines.append(line)
            # Create label
            text = arcade.Text(
                label,
                x=X_START,
                y=y - BALL_RADIUS,
                color=text_color,
                font_size=24,
            )
            self.text_list.append(text)

            # Use a nested function to correctly capture the loop variables (ease_func, label)
            # and create a self-restarting animation loop for each ball using TweenUntil.
            def start_animation_loop(target_ball, current_ease_func, current_label):
                def create_and_apply_animation(start_x, end_x):
                    # This callback is triggered when one leg of the animation completes.
                    # It starts the next leg in the opposite direction.
                    def on_complete(data=None):
                        create_and_apply_animation(start_x=end_x, end_x=start_x)

                    # TweenUntil: Perfect for precise A-to-B position animation
                    # Directly animates center_x from start_x to end_x with easing curve
                    tween_until(
                        target_ball,
                        start_value=start_x,
                        end_value=end_x,
                        property_name="center_x",
                        condition=after_frames(TWEEN_FRAMES),
                        on_stop=on_complete,
                        ease_function=current_ease_func,
                    )

                # Start the first animation from left to right.
                create_and_apply_animation(X_START, X_END)

            start_animation_loop(ball, ease_func, label)
            y += Y_INTERVAL

    def on_draw(self):
        self.clear()
        self.lines.draw()
        self.ball_list.draw()
        for text in self.text_list:
            text.draw()

    def on_update(self, delta_time):
        # Update all ArcadeActions
        Action.update_all(delta_time)
        self.ball_list.update()


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, visible=False)
    center_window(window)
    window.set_visible(True)
    view = InterpolateDemoView()
    view.setup()
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    main()
