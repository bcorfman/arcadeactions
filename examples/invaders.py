"""
Efficient Slime Invaders - Demonstrating enhanced MoveUntil with data passing

This version shows how to avoid duplicate collision detection calls by using
the enhanced MoveUntil that can pass collision data from condition to callback.

From the project root, run with:
    uv run python examples/invaders.py
"""

import random

import arcade

from arcadeactions import Action, arrange_grid, center_window, move_until
from arcadeactions.helpers import move_to

SPRITE_SCALING_PLAYER = 0.75
SPRITE_SCALING_ENEMY = 0.75
SPRITE_SCALING_LASER = 1.0

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Slime Invaders"

# Velocities in pixels per frame at 60 FPS (Arcade native semantics)
BULLET_SPEED = 5  # 5 pixels/frame = 300 pixels/second at 60 FPS
ENEMY_SPEED = 2  # 2 pixels/frame = 120 pixels/second at 60 FPS
MAX_PLAYER_BULLETS = 3

# Enemy movement margins
ENEMY_VERTICAL_MARGIN = 15
RIGHT_ENEMY_BORDER = WINDOW_WIDTH - ENEMY_VERTICAL_MARGIN
LEFT_ENEMY_BORDER = ENEMY_VERTICAL_MARGIN
ENEMY_MOVE_DOWN_AMOUNT = 30

# Game state
GAME_OVER = 1
PLAY_GAME = 0


def _make_shield_block() -> arcade.Sprite:
    """Factory that creates a single shield block sprite."""
    return arcade.SpriteSolidColor(10, 20, color=arcade.color.WHITE)


class GameView(arcade.View):
    """Demonstrates efficient collision handling with enhanced MoveUntil."""

    def __init__(self):
        super().__init__()

        # Sprite lists
        self.player_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.player_bullet_list = arcade.SpriteList()
        self.enemy_bullet_list = arcade.SpriteList()
        self.shield_list = arcade.SpriteList()

        self.game_state = PLAY_GAME

        # Set up player
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING_PLAYER,
        )
        self.player_list.append(self.player_sprite)

        self.score = 0
        self.enemy_move_action = None
        self.enemy_direction = -1

        # Load textures
        self.texture_enemy_left = arcade.load_texture(":resources:images/enemies/slimeBlue.png")
        self.texture_enemy_right = self.texture_enemy_left.flip_left_right()
        self.texture_blue_laser = arcade.load_texture(":resources:images/space_shooter/laserBlue01.png").rotate_270()

        # Sounds
        self.hit_sound = arcade.load_sound(":resources:sounds/hit5.wav")
        arcade.play_sound(self.hit_sound, volume=0.0)  # Preload sound

        self.background_color = arcade.color.AMAZON
        self.window.set_mouse_cursor_visible(False)

        # Create text objects for better performance
        self.score_text = arcade.Text(
            "Score: 0",
            x=10,
            y=20,
            color=arcade.color.WHITE,
            font_size=14,
        )

        self.game_over_text = arcade.Text(
            "GAME OVER",
            x=WINDOW_WIDTH / 2,
            y=WINDOW_HEIGHT / 2,
            color=arcade.color.WHITE,
            font_size=60,
            anchor_x="center",
        )

        self.restart_text = arcade.Text(
            "Press R to Restart",
            x=WINDOW_WIDTH / 2,
            y=WINDOW_HEIGHT / 2 - 60,
            color=arcade.color.WHITE,
            font_size=20,
            anchor_x="center",
        )

    def reset(self):
        """Reset game state"""
        self.game_state = PLAY_GAME

        # Clear everything
        Action.stop_all()
        for sprite_list in [self.enemy_list, self.player_bullet_list, self.enemy_bullet_list, self.shield_list]:
            sprite_list.clear()

        # Reset state
        self.enemy_direction = -1
        self.score = 0
        self.score_text.text = "Score: 0"

        # Position player
        self.player_sprite.center_x = 50
        self.player_sprite.center_y = 70

        # Create shields
        step = self.width // 4 - 50
        for x in [step, step * 2, step * 3]:
            self.make_shield(x)

        self.setup_level_one()

    def setup_level_one(self):
        """Create enemy formation"""
        # Create enemies in a grid formation with a single call
        rows, cols = 5, 7
        self.enemy_list = arrange_grid(
            rows=rows,
            cols=cols,
            start_x=380,
            start_y=470,  # Position enemies higher up on screen
            spacing_x=80,
            spacing_y=60,
            sprite_factory=lambda: arcade.Sprite(self.texture_enemy_right, scale=SPRITE_SCALING_ENEMY),
        )

        self.start_enemy_movement()
        self.start_enemy_firing()

    def start_enemy_movement(self):
        """Start efficient enemy movement"""
        if len(self.enemy_list) == 0:
            return

        def enemies_hit_boundary():
            if self.enemy_direction > 0:
                rightmost_enemy = max(self.enemy_list, key=lambda e: e.right)
                return rightmost_enemy.right >= RIGHT_ENEMY_BORDER
            else:
                leftmost_enemy = min(self.enemy_list, key=lambda e: e.left)
                return leftmost_enemy.left <= LEFT_ENEMY_BORDER

        def on_boundary_hit():
            self.reverse_enemy_direction()

        velocity = (ENEMY_SPEED * self.enemy_direction, 0)
        self.enemy_move_action = move_until(
            self.enemy_list, velocity=velocity, condition=enemies_hit_boundary, on_stop=on_boundary_hit
        )

    def start_enemy_firing(self):
        """Start frame-based enemy firing that matches original behavior.

        We call allow_enemies_to_fire once per frame (via CallbackUntil) so the
        firing frequency matches the original time-based version from a85b5af,
        while still going through the Actions system for proper pause/step.
        """
        from arcadeactions import CallbackUntil, infinite

        firing_action = CallbackUntil(callback=self.allow_enemies_to_fire, condition=infinite)
        firing_action.apply(self.enemy_list, tag="enemy_firing")

    def reverse_enemy_direction(self):
        """Reverse enemy direction efficiently"""
        if self.enemy_move_action:
            self.enemy_move_action.stop()

        # Move down and reverse
        for enemy in self.enemy_list:
            enemy.center_y -= ENEMY_MOVE_DOWN_AMOUNT

        self.enemy_direction *= -1

        # Update textures efficiently
        new_texture = self.texture_enemy_left if self.enemy_direction > 0 else self.texture_enemy_right
        for enemy in self.enemy_list:
            enemy.texture = new_texture

        self.start_enemy_movement()

    def make_shield(self, x_start):
        """Create shield blocks"""
        # Build shield by creating a small grid of white blocks
        shield_grid = arrange_grid(
            rows=5,
            cols=20,
            start_x=x_start,
            start_y=200,  # Position shields between player and enemies
            spacing_x=10,
            spacing_y=20,
            sprite_factory=_make_shield_block,
        )

        self.shield_list.extend(shield_grid)

    def on_mouse_press(self, x, y, button, modifiers):
        """Fire player bullet with efficient collision detection"""
        if self.game_state == GAME_OVER or len(self.player_bullet_list) >= MAX_PLAYER_BULLETS:
            return

        # Create bullet
        bullet = arcade.Sprite(self.texture_blue_laser, scale=SPRITE_SCALING_LASER)
        bullet.center_x = self.player_sprite.center_x
        bullet.bottom = self.player_sprite.top
        self.player_bullet_list.append(bullet)

        def bullet_collision_check():
            enemy_hits = arcade.check_for_collision_with_list(bullet, self.enemy_list)
            shield_hits = arcade.check_for_collision_with_list(bullet, self.shield_list)
            off_screen = bullet.bottom > WINDOW_HEIGHT

            if enemy_hits or shield_hits or off_screen:
                return {"enemy_hits": enemy_hits, "shield_hits": shield_hits, "off_screen": off_screen}
            return  # Continue moving

        def handle_bullet_collision(collision_data):
            bullet.remove_from_sprite_lists()

            # Handle enemy hits
            for enemy in collision_data["enemy_hits"]:
                enemy.remove_from_sprite_lists()
                self.score += 1
                self.score_text.text = f"Score: {self.score}"
                arcade.play_sound(self.hit_sound)

            # Handle shield hits
            for shield in collision_data["shield_hits"]:
                shield.remove_from_sprite_lists()

            # Check if level complete
            if len(self.enemy_list) == 0:
                self.reset()

        move_until(
            bullet, velocity=(0, BULLET_SPEED), condition=bullet_collision_check, on_stop=handle_bullet_collision
        )

    def allow_enemies_to_fire(self):
        """Enemy firing with efficient collision detection"""
        x_spawn = []
        for enemy in self.enemy_list:
            chance = 4 + len(self.enemy_list) * 4

            if random.randrange(chance) == 0 and enemy.center_x not in x_spawn:
                bullet = arcade.Sprite(
                    ":resources:images/space_shooter/laserRed01.png",
                    scale=SPRITE_SCALING_LASER,
                )
                bullet.angle = 180
                bullet.center_x = enemy.center_x
                bullet.top = enemy.bottom
                self.enemy_bullet_list.append(bullet)

                def enemy_bullet_collision_check(bullet_ref=bullet):
                    player_hits = arcade.check_for_collision_with_list(bullet_ref, self.player_list)
                    shield_hits = arcade.check_for_collision_with_list(bullet_ref, self.shield_list)
                    off_screen = bullet_ref.top < 0

                    if player_hits or shield_hits or off_screen:
                        return {"player_hits": player_hits, "shield_hits": shield_hits, "off_screen": off_screen}
                    return {}  # Continue moving

                def handle_enemy_bullet_collision(collision_data, bullet_ref=bullet):
                    bullet_ref.remove_from_sprite_lists()

                    if collision_data["player_hits"]:
                        self.game_state = GAME_OVER

                    for shield in collision_data["shield_hits"]:
                        shield.remove_from_sprite_lists()

                move_until(
                    bullet,
                    velocity=(0, -BULLET_SPEED),
                    condition=enemy_bullet_collision_check,
                    on_stop=handle_enemy_bullet_collision,
                )

            # Track which x positions have already attempted to fire this frame,
            # matching the original a85b5af semantics (one possible shooter per column).
            x_spawn.append(enemy.center_x)

    def on_update(self, delta_time):
        """Game update loop"""
        if self.game_state == GAME_OVER:
            return

        # Update all actions globally - no more manual list management!
        Action.update_all(delta_time)

        # Update all sprite lists so sprites move based on their velocity
        self.enemy_list.update(delta_time)
        self.player_bullet_list.update(delta_time)
        self.enemy_bullet_list.update(delta_time)

        # Enemy firing is now handled by the frame-based CallbackUntil action

        # Check if enemies reached bottom
        if any(enemy.bottom < 100 for enemy in self.enemy_list):
            self.game_state = GAME_OVER

        # Next level if no enemies
        if len(self.enemy_list) == 0:
            self.reset()

    def on_mouse_motion(self, x, y, dx, dy):
        """Move player with mouse"""
        if self.game_state != GAME_OVER:
            # Apply MoveTo - will respect pause state automatically
            move_to(self.player_sprite, x, self.player_sprite.center_y)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.close()
        elif key == arcade.key.R and self.game_state == GAME_OVER:
            self.reset()

    def on_draw(self):
        """Render the game"""
        self.clear()

        # Draw all sprites
        self.enemy_list.draw()
        self.player_bullet_list.draw()
        self.enemy_bullet_list.draw()
        self.shield_list.draw(pixelated=True)
        self.player_list.draw()

        # Draw UI
        self.score_text.draw()

        if self.game_state == GAME_OVER:
            self.game_over_text.draw()
            self.restart_text.draw()


def main():
    """Run the Slime Invaders game"""
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, visible=False, vsync=True)
    center_window(window)
    window.set_visible(True)
    game = GameView()
    game.reset()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
