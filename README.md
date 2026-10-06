<table style="border: none; border-collapse: collapse;">
<tr>
<td align="center" style="border: none; padding: 10px; vertical-align: bottom;">
<img src="https://github.com/bcorfman/gif_resources/blob/main/space_clutter.gif?raw=true" style="width: 400px"/>
<br/>
<em style="display: block; width: 400px; text-align: center;">Space Clutter! - A game prototype demonstrating grid formations, wave patterns, and MoveUntil actions</em>
</td>
<td align="center" style="border: none; padding: 10px; vertical-align: bottom;">
<img src="https://github.com/bcorfman/gif_resources/blob/main/laser_gates.gif?raw=true" style="width: 400px"/>
<br/>
<em style="display: block; width: 400px; text-align: center;">A <a href="https://github.com/bcorfman/laser_gates">full game</a> under development, using Actions</em>
<br/>
<img src="https://github.com/bcorfman/gif_resources/blob/main/pattern_demo.gif?raw=true" style="width: 400px"/>
<br/>
<em style="display: block; width: 400px; text-align: center;">Pattern Demo - Showcasing various movement patterns and formation arrangements</em>
</td>
</tr>
</table>

---

# ArcadeActions extension library for Arcade 3.x
[![Tests](https://github.com/bcorfman/arcadeactions/actions/workflows/test.yml/badge.svg)](https://github.com/bcorfman/arcadeactions/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/bcorfman/arcadeactions/graph/badge.svg?token=9AIZD1GLND)](https://codecov.io/gh/bcorfman/arcadeactions)

Project docs: [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bcorfman/arcadeactions)

## 🚀 Quick Appeal

ArcadeActions provides a structured way to orchestrate how objects move and respond over time, replacing scattered update code with clear, condition‑driven instructions. Instead of relying on fixed timers, it lets behaviors continue until meaningful conditions are met, which keeps logic aligned with what’s actually happening in the project. Its main contribution is turning complex, multi‑step behavior into concise, readable sequences that remain manageable as the project grows.

```python 
import arcade
from arcadeactions import MoveUntil, Action

class AsteroidDemoView(arcade.View):
    def __init__(self):
        super().__init__()
        # Minimal, explicit setup
        self.player = arcade.Sprite(":resources:/images/space_shooter/playerShip1_green.png")
        self.player.center_x, self.player.center_y = 400, 100

        self.asteroids = arcade.SpriteList()
        # Position asteroids in a simple pattern with different velocities
        positions = [(200, 450), (400, 400), (600, 450)]
        velocities = [(3, -2), (-2, -3), (4, -1)]
        
        for (x, y), (vx, vy) in zip(positions, velocities):
            rock = arcade.Sprite(":resources:/images/space_shooter/meteorGrey_big1.png")
            rock.center_x, rock.center_y = x, y
            self.asteroids.append(rock)
            
            # Each asteroid moves independently with its own velocity
            MoveUntil(
                velocity=(vx, vy),
                condition=self.player_asteroid_collision,
                on_stop=self.on_player_collision,
                bounds=(-64, -64, 864, 664),
                boundary_behavior="wrap",
            ).apply(rock)

    def player_asteroid_collision(self):
        """Return data when player hits any asteroid; None to keep moving."""
        hits = arcade.check_for_collision_with_list(self.player, self.asteroids)
        return {"hits": hits} if hits else None

    def on_player_collision(self, data):
        """React to collision."""
        print(f"Game over! {len(data['hits'])} asteroid(s) hit the player.")
        # ... reset player / end round / etc. ...

    def on_update(self, dt):
        Action.update_all(dt)
        self.player.update()
        self.asteroids.update()

    def on_draw(self):
        self.clear()
        self.player.draw()
        self.asteroids.draw()
```
This simple Asteroids example shows how animation actions can be logically separated from collision responses, making your code simple and appealing. 
If writing high-level game code appeals to you ... it's why you chose Python in the first place ... read on!

## 📚 Documentation Overview

### Essential Reading
1. **[API Usage Guide](docs/api_usage_guide.md)** - Summary API guide to using the framework
2. **[DeepWiki](https://deepwiki.com/bcorfman/arcadeactions)** - Complete end-to-end API guide
3. **[Testing Guide](docs/testing_guide.md)** - Testing patterns and best practices
4. **[PRD](docs/prd.md)** - Project requirements and architecture decisions

## 🚀 Getting Started

### 🛠️ Installation

**For Library Users:**
```bash
# Basic installation for most games; adjust the commands below depending on your Python package manager. 
pip install arcadeactions

# With optional state machine support (platformers/character action games)
pip install arcadeactions[statemachine]

# With state machine diagram generation 
pip install arcadeactions[statemachine_diagrams]
```
**For Contributors:**
```bash
# Clone the repository
git clone https://github.com/bcorfman/arcadeactions.git
cd arcadeactions

# Install for development (includes all optional dependencies and dev tools)
make devinstall

# Run tests
make test
```

### Quick Start by Game Type

Simple Arcade Games (no physics):
1. **Read the [API Usage Guide](docs/api_usage_guide.md)** to understand the framework
2. **Study working demos** to see Actions in practice
3. **Start with simple helper functions** (`move_until`, `rotate_until`)
4. **Build up to sequences** for complex behaviors

Platformers / Physics Games:
1. **Install with state machine support**: `uv add arcadeactions[statemachine]` (see Installation section above)
2. **Start with** `examples/pymunk_demo_platformer.py` - reference implementation
3. **Study the patterns**:
   - InputState with @dataclass
   - DUMB View / SMART State Machine architecture
   - Centralized physics in state machine
   - `cycle_textures_until` for animations
4. **Follow the architecture guide** (see Decision Matrix below)

## 🔧 Core Components

### ✅ Implementation

#### Base Action System (arcadeactions/base.py)
- **Action** - Core action class with global management
- **Global management** - Automatic action tracking and updates

#### Configuration (arcadeactions/config.py)
- **Configurable debug logging**: Fine-grained, level-based diagnostics with per-Action filtering for focused output
- **Debug levels**: Level 0 (off), Level 1 (summary counts), Level 2 (lifecycle events), Level 3+ (verbose per-frame details)
- **Action filtering**: Observe specific action classes or all actions for targeted debugging
- **Environment variables**: `ARCADEACTIONS_DEBUG=2`, `ARCADEACTIONS_DEBUG_ALL=1`, `ARCADEACTIONS_DEBUG_INCLUDE=MoveUntil,CallbackUntil`
- **Programmatic API**: `set_debug_options(level=2, include=["MoveUntil"])` or `observe_actions(MoveUntil, CallbackUntil)` in your app startup

#### Instant Action System (arcadeactions/instant.py)
- **MoveBy** - Relative Sprite or SpriteList positioning
- **MoveTo** - Absolute positioning

#### Conditional Actions (arcadeactions/movement.py, arcadeactions/paths.py, arcadeactions/transforms.py, arcadeactions/effects.py, arcadeactions/callbacks.py, arcadeactions/parametric.py)
- **MoveUntil** - Velocity-based movement until condition met (optional PyMunk physics integration)
- **FollowPathUntil** - Follow Bezier curve paths with optional automatic sprite rotation (optional PyMunk physics steering with `use_physics=True`)
- **RotateUntil** - Angular velocity rotation (optional PyMunk physics integration)
- **ScaleUntil** - Scale velocity changes  
- **FadeTo** - Fade alpha toward a target value
- **CycleTexturesUntil** - Cycle through a list of textures at a specific frame rate with simulation time duration support
- **BlinkUntil** - Toggle sprite visibility with optional enter/exit callbacks for collision management
- **CallbackUntil** - Execute callback functions at specified intervals or every frame until condition is met
- **DelayFrames** - Wait for a number of frames (or early-exit condition)
- **TweenUntil** - Direct property animation from start to end value
- **GlowUntil** - Render full-screen Shadertoy effects with camera offset support
- **EmitParticlesUntil** - Manage per-sprite particle emitters with anchor and rotation following

#### Composite Actions (arcadeactions/composite.py)
- **Sequential actions** - Run actions one after another (use `sequence()`)
- **Parallel actions** - Run actions in parallel (use `parallel()`)
- **Repeat actions** - Repeat an action indefinitely (use `repeat()`)

#### Boundary Handling (arcadeactions/movement.py)
- **MoveUntil with bounds** - Built-in boundary detection with bounce/wrap behaviors using edge-based coordinates

#### Formation Management (arcadeactions/formation.py)
- **Formation functions** - Grid, line, circle, diamond, V-formation, triangle, hexagonal grid, arc, concentric rings, cross, and arrow positioning
  - Zero-allocation support: pass `sprites=` to arrange existing sprites without allocating
  - Contract: exactly one of `sprites` or creation inputs (`count` or `sprite_factory`) is required
  - Grid rule: when `sprites` is provided, `len(sprites)` must equal `rows * cols`
  - See `examples/formation_demo.py` for a quick start

#### Movement Patterns (arcadeactions/pattern.py)
- **Movement pattern functions** - Zigzag, wave, spiral, figure-8, orbit, bounce, and patrol patterns
- **Condition helpers** - Time-based and sprite count conditions for conditional actions
- See `examples/pattern_demo.py` for a quick start

#### State Machine Integration
ArcadeActions integrates seamlessly with the external [`python-statemachine`](https://github.com/fgmacedo/python-statemachine) library for complex state-driven game logic.

**Complete Example:** See `examples/pymunk_demo_platformer.py` for the reimagined Arcade 3.x implementation showing:
- InputState with @dataclass
- State machine with guard conditions and named events
- Physics force application centralized in state machine
- CycleTexturesUntil for walk/climb animations
- Zero state flags - state machine as single source of truth

**Additional Reference:** The [AmazonWarriors](https://github.com/bcorfman/amazon-warriors) and [Laser Gates](https://github.com/bcorfman/laser-gates) projects demonstrate more complete and advanced patterns.

### ♻️ Zero-Allocation Gameplay (experimental)

ArcadeActions now provides an optional zero-allocation workflow to eliminate per-wave sprite creation.

1) Use the new `SpritePool` (in `arcadeactions.pools`) to pre-allocate sprites once at boot:

```python
from arcadeactions.pools import SpritePool
from arcadeactions import arrange_grid
import arcade

def make_block():
    return arcade.Sprite(":resources:images/items/star.png", scale=0.8)

pool = SpritePool(make_block, max_size=300)
blocks = pool.acquire(150)                                    # borrow invisible sprites
arrange_grid(rows=30, cols=5, sprites=blocks, start_x=0, start_y=0)  # position only
pool.assign(blocks)                                           # return to pool (hidden & neutral)
```

2) During gameplay, acquire → arrange → release without allocating:

```python
shield = pool.acquire(width * 30)
arrange_grid(rows=30, cols=width, sprites=shield, start_x=WINDOW+50, start_y=TUNNEL_H)
# ... gameplay ...
pool.release(shield)
```

SpritePool API:
- `acquire(n) -> list[Sprite]` — borrow invisible, un-positioned sprites
- `release(iterable[Sprite])` — return sprites to the pool (hidden, detached, reset)
- `assign(iterable[Sprite])` — load externally-created sprites into the pool once

Arrange functions contract:
- Provide exactly one of `sprites` or creation inputs (`count`/`sprite_factory`)
- When using `sprites` with `arrange_grid`, `len(sprites) == rows * cols` is required


#### Easing Effects (arcadeactions/easing.py)
- **Ease wrapper** - Apply smooth acceleration/deceleration curves to any conditional action
- **Multiple easing functions** - Built-in `arcadeactions.easing` support for ease-in, ease-out, sine, elastic, and back curves
- **Custom easing** - Create specialized easing curves and nested easing effects

#### Optional Physics Integration (arcadeactions/physics_adapter.py)
- **PyMunk Physics Support** - Optional integration with `arcade.PymunkPhysicsEngine` for physics-driven movement
- **Zero API Changes** - Existing code works unchanged; physics is opt-in via `Action.update_all(dt, physics_engine=engine)`
- **Automatic Kinematic Sync** - **NEW:** Kinematic bodies automatically synced (eliminates manual `set_velocity()` loops)
- **Automatic Routing** - `MoveUntil` and `RotateUntil` automatically use physics when engine is provided
- **Physics-Based Path Following** - `FollowPathUntil` with `use_physics=True` uses steering impulses for natural physics interaction
- **Fallback Behavior** - Actions work normally without a physics engine (direct sprite attribute manipulation)
- **Complete Example** - See `examples/pymunk_demo_platformer.py` for state machine + physics + actions integration
- **See the [API Usage Guide](docs/api_usage_guide.md#optional-physics-integration-arcade-3x--pymunk)** for detailed examples

#### Development Visualizer (arcadeactions/dev/) - **NEW**
ArcadeActions includes a comprehensive development visualizer for rapid prototyping and scene editing.

**Sprite Prototype Registry:**
- Register sprite "prefabs" with decorator-based factories
- Drag-and-drop spawning from palette into scene
- Automatic prototype ID tracking for serialization

```python
from arcadeactions.dev import register_prototype, DevContext

@register_prototype("enemy_ship")
def make_enemy_ship(ctx):
    ship = arcade.Sprite("res/enemy.png", scale=0.5)
    ship._prototype_id = "enemy_ship"
    return ship
```

**Palette Sidebar & Selection:**
- Visual palette showing all registered prototypes
- Drag prototypes from palette to spawn at cursor position
- Multi-selection: click-to-select, shift-click to add, click-drag marquee for box selection
- Visual outline indicators for selected sprites

**Preset Action Library:**
- Register composable action presets with default parameters
- Parameter editing sidebar for customizing presets
- Bulk attach presets to multiple selected sprites at once
- Actions stored as metadata in edit mode (not running) for safe editing

```python
from arcadeactions.dev import register_preset
from arcadeactions.conditional import infinite

@register_preset("scroll_left_cleanup", category="Movement", params={"speed": 4})
def preset_scroll_left_cleanup(ctx, speed):
    from arcadeactions.helpers import move_until
    return move_until(
        None,
        velocity=(-speed, 0),
        condition=infinite,
        bounds=(OFFSCREEN_LEFT, 0, SCREEN_RIGHT, SCREEN_HEIGHT),
        boundary_behavior="limit",
    )
```

**Boundary Gizmos:**
- Visual editor for `MoveUntil` action bounds
- Draggable corner handles to adjust boundary rectangles in real-time
- Semi-transparent overlay showing current bounds
- Updates action bounds via `set_bounds()` method

**YAML Template Export/Import:**
- Export entire scenes to YAML with sprite positions and action configurations
- Import scenes back into visualizer for round-trip editing
- Symbolic bound expressions (e.g., `OFFSCREEN_LEFT`, `SCREEN_RIGHT`) for readability
- Flat list schema: prototype, position, group, and action presets

```python
from arcadeactions.dev import export_template, load_scene_template, DevContext

# Export scene
export_template(scene_sprites, "wave1.yaml", prompt_user=False)

# Import scene (clears and rebuilds)
ctx = DevContext(scene_sprites=scene_sprites)
load_scene_template("wave1.yaml", ctx)
```

**Code Sync (Reverse Sync):**
- Automatic source code updates from visual edits
- Updates position assignments (e.g., `sprite.left = X`, `sprite.center_x = Y`)
- Updates `arrange_grid()` call parameters and per-cell overrides
- Preserves formatting and comments using libcst
- Creates backup files before changes

```python
from arcadeactions.dev.position_tag import positioned

@positioned("forcefield")
def make_forcefield():
    sprite = arcade.Sprite(":resources:images/tiles/grassCenter.png")
    sprite.left = 100
    sprite.top = 200
    return sprite

# After visual editing, export_sprites() automatically updates source code
dev_viz.export_sprites()  # Updates source file with new positions
```

**Arrange Grid Overrides Panel:**
- Edit per-cell position overrides in `arrange_grid()` calls (Press **O**)
- Fine-tune individual sprite positions within grid formations
- Keyboard shortcuts for navigation and editing
- Undo support for override edits

**Dev Command Palette:**
- Open a secondary command window with **F8**
- Run dev commands with quick keys (`E` export, `I` import, `H` help)
- Use `↑` / `↓` and `Enter` to execute highlighted commands

**Edit Mode vs Runtime:**
- **Edit Mode**: Sprites are static, actions stored as metadata (`_action_configs`), no `action.apply()` calls
- Allows safe selection, positioning, and parameter editing without movement
- Actions only instantiated when exporting to runtime or previewing
- Round-trip workflow: export → modify → reimport → re-export

**Integration:**
All DevVisualizer components are standalone and composable. Use `PaletteSidebar` for spawning, `SelectionManager` for selection, `ActionPresetRegistry` for presets, `BoundaryGizmo` for bounds editing, `OverridesPanel` for grid overrides, and `templates` module for persistence.

See `.cursor/rules/project.mdc` for detailed DevVisualizer architecture and usage patterns.

## 📋 Decision Matrix: When to Use What

### Basic Actions & Composition

| Scenario | Use | Example |
|----------|-----|---------|
| Simple sprite actions | Helper functions | `move_until(sprite, ..., tag="move")` |
| Sprite group actions | Helper functions on SpriteList | `move_until(enemies, ..., tag="formation")` |
| Complex sequences | Direct classes + `sequence()` | `sequence(DelayFrames(...), MoveUntil(...))` |
| Parallel behaviors | Direct classes + `parallel()` | `parallel(MoveUntil(...), RotateUntil(...))` |
| Formation positioning | Formation functions | `arrange_grid(enemies, rows=3, cols=5)` |
| Curved path movement | `follow_path_until` helper | `follow_path_until(sprite, points, ...)` |
| Visibility blinking | `blink_until` helper | `blink_until(sprite, seconds_until_change=0.25, ...)` |
| Periodic callbacks | `callback_until` helper | `callback_until(sprite, callback=fn, condition=cond, seconds_between_calls=0.1)` |
| Shader/particle effects | `callback_until` for temporal control | `callback_until(sprite, lambda: emitter.update(), condition=cond)` |
| Boundary detection | `move_until` with bounds | `move_until(sprite, bounds=b, boundary_behavior="bounce")` |
| Smooth acceleration | `ease()` helper | `ease(sprite, action, frames=seconds_to_frames(2.0))` |
| Property animation | `tween_until` helper | `tween_until(sprite, 0, 100, "center_x", ...)` |
| Visual scene editing | DevVisualizer | Palette spawning, multi-selection, preset library, boundary gizmos |
| Scene persistence | DevVisualizer YAML | Export/import scenes with round-trip editing support |
| Code sync | DevVisualizer + position tags | Automatic source code updates from visual edits |
| Grid overrides | DevVisualizer Overrides Panel | Per-cell position editing for arrange_grid formations (O) |

### State Machine Integration

| Scenario | Use | Example/Reference |
|----------|-----|-------------------|
| Character animation states | `python-statemachine` + `cycle_textures_until` | See `examples/pymunk_demo_platformer.py` |
| Input handling | `@dataclass` InputState | Simple fields + computed properties |
| Physics + animation + input | State machine with guards + centralized forces | State machine calls `physics.apply_force()` |
| Walk/climb animations | `cycle_textures_until` in enter callbacks | Start in `on_enter_walk`, stop in `on_exit_walk` |
| Jump physics | Physics in state enter callback | `on_enter_jump` calls `apply_impulse` |
| Complex platformer mechanics | State machine + physics callbacks | `pymunk_moved` triggers state transitions |

### Physics Integration

| Scenario | Use | Pattern |
|----------|-----|---------|
| Kinematic moving platforms | `move_until` + bounce + physics | Automatic kinematic sync (no manual loop) |
| Player with physics forces | State machine + `apply_physics_forces()` | Centralize in state machine method |
| Dynamic sprites | PyMunk with gravity | Use PyMunk directly (masses, collisions) |
| Physics path following | `FollowPathUntil` with `use_physics=True` | Steering impulses for natural movement |

### Architecture Decision Guide

| Your Game Type | Recommended Stack | Rationale |
|----------------|-------------------|-----------|
| Simple arcade (Asteroids, Space Invaders) | ArcadeActions alone | `sequence()`, `move_until`, formations |
| Complex arcade | python-statemachine + ArcadeActions | See full game projects above |
| Complex arcade with physics | python-statemachine + ArcadeActions + PyMunk | See `pymunk_demo_platformer.py` |
| Cutscenes/tutorials | `sequence()` + `parallel()` | Complex multi-step choreography |
| Rapid prototyping | DevVisualizer + ArcadeActions | Visual scene editing, YAML templates, preset library |

### View Architecture Pattern

| Component | Responsibility | Complexity |
|-----------|----------------|------------|
| DUMB View (Window) | Route input, call state machine events | Simple: 2-3 lines per handler |
| SMART State Machine | Guards, transitions, physics forces, animations | Complex: all game logic |
| @dataclass InputState | Hold input data, computed properties | Simple: fields + properties |
| PlayerSprite | Hold textures, forward to state machine | Medium: setup + callbacks |
