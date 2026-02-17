"""
DevVisualizer Speed Lab - Combined editor/runtime example.

Priorities:
- Dev Speed Boost features (command palette, animation inspector, snap-to-grid,
  template browser, grid overlay, scene validator) with safe fallbacks.
- Missing ArcadeActions features: RotateUntil, ScaleUntil,
  GlowUntil, EmitParticlesUntil.

Usage:
  ARCADEACTIONS_DEVVIZ=1 uv run python examples/devviz_speed_lab.py

Notes:
- Auto-exports a default YAML scene on first run.
- Uses Arcade built-in resources only.
- Main window draws sprites only (no text overlays). Console prints provide guidance.
"""

from __future__ import annotations

import os
from pathlib import Path

import arcade
from arcade import particles
from arcade.experimental.shadertoy import Shadertoy

from arcadeactions import (
    Action,
    EmitParticlesUntil,
    FadeTo,
    GlowUntil,
    MoveUntil,
    RotateUntil,
    ScaleUntil,
    arrange_grid,
    center_window,
    infinite,
    repeat,
    sequence,
)
from arcadeactions.dev import (
    DevContext,
    enable_dev_visualizer,
    export_template,
    get_prototype_registry,
    load_scene_template,
    register_preset,
    register_prototype,
)
from arcadeactions.dev.position_tag import positioned, tag_sprite

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "DevVisualizer Speed Lab"

YAML_PATH = Path(__file__).with_suffix(".yaml")

GRID_SIZE = 32

# Arcade built-in assets
GATE_TEXTURE = ":resources:images/tiles/doorClosed_mid.png"
BLADE_TEXTURE = ":resources:images/items/star.png"
PICKUP_TEXTURE = ":resources:images/items/gemBlue.png"
TURRET_TEXTURE = ":resources:images/space_shooter/playerShip1_orange.png"
SPARK_TEXTURE = ":resources:images/items/coinGold.png"

# Simple Shadertoy source (compact, no external files)
SHADER_SOURCE = """
void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord.xy / iResolution.xy;
    float glow = 0.4 + 0.6 * sin(iTime + uv.x * 6.2831);
    vec3 col = vec3(uv.y, uv.x, glow);
    fragColor = vec4(col, 1.0);
}
"""


@register_prototype("gate")
@positioned("gate_anchor")
def make_gate(ctx: DevContext) -> arcade.Sprite:
    sprite = arcade.Sprite(GATE_TEXTURE, scale=1.2)
    sprite._prototype_id = "gate"
    return sprite


@register_prototype("blade")
@positioned("blade_anchor")
def make_blade(ctx: DevContext) -> arcade.Sprite:
    sprite = arcade.Sprite(BLADE_TEXTURE, scale=0.8)
    sprite._prototype_id = "blade"
    return sprite


@register_prototype("pickup")
@positioned("pickup_anchor")
def make_pickup(ctx: DevContext) -> arcade.Sprite:
    sprite = arcade.Sprite(PICKUP_TEXTURE, scale=0.6)
    sprite._prototype_id = "pickup"
    return sprite


@register_prototype("turret")
def make_turret(ctx: DevContext) -> arcade.Sprite:
    sprite = arcade.Sprite(TURRET_TEXTURE, scale=0.5)
    sprite._prototype_id = "turret"
    return sprite


class DevVizSpeedLabView(arcade.View):
    def __init__(self) -> None:
        super().__init__()
        self.scene_sprites = arcade.SpriteList()
        self.dev_ctx = DevContext(scene_sprites=self.scene_sprites)
        self._emitters: list[particles.Emitter] = []
        self._glow_shader: Shadertoy | None = None
        self._glow_action: GlowUntil | None = None
        self._fallback_grid_enabled = False
        self._fallback_shortcuts_enabled = False
        self._dev_viz = None

        self._register_presets()

    def _register_presets(self) -> None:
        @register_preset("spin_blade", category="Effects", params={"speed": 4.0})
        def preset_spin_blade(ctx: DevContext, speed: float = 4.0) -> RotateUntil:
            return RotateUntil(angular_velocity=speed, condition=infinite)

        @register_preset("pulse_pickup", category="Effects", params={"speed": 0.01})
        def preset_pulse_pickup(ctx: DevContext, speed: float = 0.01) -> ScaleUntil:
            return ScaleUntil(velocity=speed, condition=infinite)

        @register_preset("fade_gate", category="Effects", params={"speed": -2.0})
        def preset_fade_gate(ctx: DevContext, speed: float = -2.0) -> Action:
            speed_abs = abs(speed)
            if speed_abs == 0:
                speed_abs = 2.0

            return repeat(
                sequence(
                    FadeTo(target_alpha=0, speed=speed_abs),
                    FadeTo(target_alpha=255, speed=speed_abs),
                )
            )

        @register_preset("glow_gate", category="Effects")
        def preset_glow_gate(ctx: DevContext) -> GlowUntil:
            action = GlowUntil(
                shadertoy_factory=self._create_shadertoy,
                condition=infinite,
            )
            self._glow_action = action
            return action

        @register_preset("sparks_blade", category="Effects", params={"interval": 0.06})
        def preset_sparks_blade(ctx: DevContext, interval: float = 0.06) -> EmitParticlesUntil:
            return EmitParticlesUntil(
                emitter_factory=self._create_spark_emitter,
                condition=infinite,
                follow_rotation=True,
            )

        @register_preset("gate_slide", category="Movement", params={"speed": 2.0})
        def preset_gate_slide(ctx: DevContext, speed: float = 2.0) -> MoveUntil:
            bounds = (120, 200, WINDOW_WIDTH - 120, WINDOW_HEIGHT - 200)
            return MoveUntil(
                velocity=(speed, 0),
                condition=infinite,
                bounds=bounds,
                boundary_behavior="bounce",
            )

    def _create_shadertoy(self, size: tuple[int, int]) -> Shadertoy:
        actual_size = size
        if actual_size == (0, 0):
            actual_size = self.window.get_framebuffer_size()
        toy = Shadertoy(actual_size, SHADER_SOURCE)
        self._glow_shader = toy
        return toy

    def _create_spark_emitter(self, sprite: arcade.Sprite) -> particles.Emitter:
        emitter = particles.make_interval_emitter(
            (sprite.center_x, sprite.center_y),
            [SPARK_TEXTURE],
            emit_interval=0.06,
            emit_duration=9999.0,
            particle_speed=1.2,
            particle_lifetime_min=0.4,
            particle_lifetime_max=0.8,
            particle_scale=0.15,
            fade_particles=True,
        )
        self._emitters.append(emitter)
        return emitter

    def setup(self) -> None:
        self._load_or_create_scene()
        self._hydrate_arrange_markers_for_overrides_panel()
        self._apply_runtime_actions()
        self._enable_dev_visualizer_if_requested()
        self._print_console_help()

    def _load_or_create_scene(self) -> None:
        if YAML_PATH.exists():
            load_scene_template(YAML_PATH, self.dev_ctx)
            return

        self._build_default_scene()
        export_template(self.scene_sprites, YAML_PATH, prompt_user=False)

    def _build_default_scene(self) -> None:
        self.scene_sprites.clear()
        self._emitters.clear()

        registry = get_prototype_registry()

        gate = registry.create("gate", self.dev_ctx)
        gate.center_x = WINDOW_WIDTH * 0.5
        gate.center_y = WINDOW_HEIGHT * 0.6
        gate._action_configs = [
            {"preset": "gate_slide", "params": {"speed": 2.0}},
            {"preset": "fade_gate", "params": {"speed": -2.0}},
            {"preset": "glow_gate", "params": {}},
        ]

        blade = registry.create("blade", self.dev_ctx)
        blade.center_x = WINDOW_WIDTH * 0.2
        blade.center_y = WINDOW_HEIGHT * 0.55
        blade._action_configs = [
            {"preset": "spin_blade", "params": {"speed": 5.0}},
            {"preset": "sparks_blade", "params": {"interval": 0.06}},
        ]

        pickup = registry.create("pickup", self.dev_ctx)
        pickup.center_x = WINDOW_WIDTH * 0.75
        pickup.center_y = WINDOW_HEIGHT * 0.35
        pickup._action_configs = [
            {"preset": "pulse_pickup", "params": {"speed": 0.01}},
        ]

        turrets = arcade.SpriteList()
        for i in range(6):
            turret = registry.create("turret", self.dev_ctx)
            tag_sprite(turret, f"turret_{i}")
            turret._action_configs = [
                {"preset": "spin_blade", "params": {"speed": 1.5}},
            ]
            turrets.append(turret)

        arrange_grid(
            sprites=turrets,
            rows=1,
            cols=6,
            start_x=160,
            start_y=120,
            spacing_x=160,
            spacing_y=60,
        )

        self.scene_sprites.extend([gate, blade, pickup])
        self.scene_sprites.extend(turrets)

    def _hydrate_arrange_markers_for_overrides_panel(self) -> None:
        """Attach arrange-grid source markers so `O` panel is available in this lab."""
        try:
            from arcadeactions.dev.code_parser import parse_file
        except Exception:
            return

        try:
            _, arrange_calls = parse_file(str(Path(__file__)))
        except Exception:
            return
        if not arrange_calls:
            return

        arrange_call = arrange_calls[0]
        marker = {
            "file": arrange_call.file,
            "lineno": arrange_call.lineno,
            "type": "arrange",
            "kwargs": arrange_call.kwargs,
            "status": "yellow",
        }
        for sprite in self.scene_sprites:
            if getattr(sprite, "_prototype_id", None) == "turret":
                sprite._source_markers = [dict(marker)]

    def _enable_dev_visualizer_if_requested(self) -> None:
        if os.environ.get("ARCADEACTIONS_DEVVIZ") != "1" and os.environ.get("ARCADEACTIONS_DEV") != "1":
            return

        self._dev_viz = enable_dev_visualizer(scene_sprites=self.scene_sprites, window=self.window, auto_attach=True)
        self._dev_viz.show()

    def _apply_runtime_actions(self) -> None:
        Action.stop_all()
        self._emitters.clear()
        self._glow_shader = None

        if self._dev_viz is not None:
            for sprite in self.scene_sprites:
                self._dev_viz.apply_metadata_actions(sprite)
        else:
            from arcadeactions.dev.visualizer_metadata import apply_metadata_actions

            for sprite in self.scene_sprites:
                apply_metadata_actions(sprite, self.dev_ctx)

        for sprite in self.scene_sprites:
            if sprite._prototype_id == "pickup":
                continue

    def _print_console_help(self) -> None:
        print("=" * 60)
        print("DevVisualizer Speed Lab")
        print("=" * 60)
        print(f"Default YAML: {YAML_PATH}")
        print("Press F12 to toggle DevVisualizer (if enabled)")
        print("Press F8 for Command Palette (fallback hotkeys enabled if missing)")
        print("Fallback hotkeys: E export | I import | G grid | S snap | T template | V validate")
        print("=" * 60)

    def _toggle_fallback_shortcuts(self) -> None:
        self._fallback_shortcuts_enabled = True

    def _export_yaml(self) -> None:
        export_template(self.scene_sprites, YAML_PATH, prompt_user=False)
        print(f"Exported YAML: {YAML_PATH}")

    def _import_yaml(self) -> None:
        load_scene_template(YAML_PATH, self.dev_ctx)
        self._apply_runtime_actions()
        print(f"Imported YAML: {YAML_PATH}")

    def _toggle_grid(self) -> None:
        self._fallback_grid_enabled = not self._fallback_grid_enabled

    def _snap_to_grid(self) -> None:
        if self._dev_viz is None:
            return
        selected = self._dev_viz.selection_manager.get_selected()
        for sprite in selected:
            sprite.center_x = round(sprite.center_x / GRID_SIZE) * GRID_SIZE
            sprite.center_y = round(sprite.center_y / GRID_SIZE) * GRID_SIZE

    def _validate_scene(self) -> None:
        offscreen = []
        for sprite in self.scene_sprites:
            if (
                sprite.center_x < 0
                or sprite.center_x > WINDOW_WIDTH
                or sprite.center_y < 0
                or sprite.center_y > WINDOW_HEIGHT
            ):
                offscreen.append(sprite._prototype_id)
        if offscreen:
            print(f"Scene validator: offscreen sprites -> {offscreen}")
        else:
            print("Scene validator: OK")

    def on_draw(self) -> None:
        self.clear()

        if self._fallback_grid_enabled:
            for x in range(0, WINDOW_WIDTH + 1, GRID_SIZE):
                arcade.draw_line(x, 0, x, WINDOW_HEIGHT, arcade.color.DIM_GRAY, 1)
            for y in range(0, WINDOW_HEIGHT + 1, GRID_SIZE):
                arcade.draw_line(0, y, WINDOW_WIDTH, y, arcade.color.DIM_GRAY, 1)

        if self._glow_action is not None:
            self._glow_action.update_effect(0.0)

        for emitter in self._emitters:
            emitter.draw()

        if self._dev_viz is None:
            self.scene_sprites.draw()

    def on_update(self, delta_time: float) -> None:
        if self._glow_shader is not None:
            self._glow_shader.time += delta_time

        Action.update_all(delta_time)
        self.scene_sprites.update()

    def on_key_press(self, key: int, modifiers: int) -> None:
        if key == arcade.key.ESCAPE:
            self.window.close()
            return

        if key == arcade.key.F8:
            self._toggle_fallback_shortcuts()
            print("Command Palette not detected. Using fallback hotkeys.")
            return

        if not self._fallback_shortcuts_enabled:
            return

        if key == arcade.key.E:
            self._export_yaml()
        elif key == arcade.key.I:
            self._import_yaml()
        elif key == arcade.key.G:
            self._toggle_grid()
        elif key == arcade.key.S:
            self._snap_to_grid()
        elif key == arcade.key.T:
            self._import_yaml()
        elif key == arcade.key.V:
            self._validate_scene()


def main() -> None:
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, visible=False, vsync=True)
    center_window(window)
    window.set_visible(True)

    view = DevVizSpeedLabView()
    window.show_view(view)
    view.setup()

    arcade.run()


if __name__ == "__main__":
    main()
