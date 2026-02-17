# ArcadeActions Development Tools

Development-focused tools for ArcadeActions that enable hot-reload, visual editing, and rapid iteration workflows.

## FileWatcher

Monitors file system paths for changes and triggers callbacks when files are modified, with intelligent debouncing to prevent excessive reloads during rapid edits.

### Features

- **Multi-path monitoring**: Watch multiple directories simultaneously
- **Pattern filtering**: Only watch specific file types (e.g., `*.py`)
- **Debouncing**: Automatically batches rapid changes to prevent callback spam
- **Recursive watching**: Monitors subdirectories automatically
- **Context manager support**: Clean resource management with `with` statement
- **Thread-safe**: Uses background threads for efficient file monitoring

### Basic Usage

```python
from pathlib import Path
from arcadeactions.dev import FileWatcher

def on_files_changed(changed_files: list[Path]) -> None:
    print(f"Files changed: {[f.name for f in changed_files]}")
    # Trigger reload logic here

# Create and start watcher
watcher = FileWatcher(
    paths=["src/game/"],
    callback=on_files_changed,
    patterns=["*.py"],
    debounce_seconds=0.3
)
watcher.start()

# ... do work ...

watcher.stop()
```

### Context Manager

```python
from arcadeactions.dev import FileWatcher

with FileWatcher(paths=["src/"], callback=on_reload) as watcher:
    # Watcher automatically starts
    # ... do work ...
    pass
# Watcher automatically stops
```

### Parameters

- **paths** (`list[Path | str]`): Directories or files to watch
- **callback** (`Callable[[list[Path]], None]`): Function called with list of changed file paths
- **patterns** (`list[str] | None`): File patterns to watch (default: `["*.py"]`)
- **debounce_seconds** (`float`): Minimum quiet time before triggering callback (default: `0.3`)

### How Debouncing Works

When files change rapidly (e.g., saving multiple times in quick succession), the watcher:

1. Collects all changed file paths
2. Waits for a quiet period (no changes for `debounce_seconds`)
3. Calls the callback once with the accumulated list of changes

This prevents overwhelming your reload logic with redundant callbacks during active editing.

### Example: Hot-Reload Workflow

```python
import importlib
from pathlib import Path
from arcadeactions.dev import FileWatcher

# Modules to watch and reload
watched_modules = {
    Path("src/game/waves.py"): "game.waves",
    Path("src/game/enemies.py"): "game.enemies",
}

def reload_modules(changed_files: list[Path]) -> None:
    """Reload changed modules."""
    for file_path in changed_files:
        module_name = watched_modules.get(file_path.resolve())
        if module_name:
            try:
                module = __import__(module_name, fromlist=[''])
                importlib.reload(module)
                print(f"✓ Reloaded {module_name}")
            except Exception as e:
                print(f"✗ Error reloading {module_name}: {e}")

# Start watching
watcher = FileWatcher(
    paths=["src/game/"],
    callback=reload_modules,
    patterns=["*.py"],
    debounce_seconds=0.5
)
watcher.start()
```

### Threading Considerations

The FileWatcher uses background threads for efficient monitoring:

- File system events are handled in a watchdog observer thread
- Debouncing happens in a separate debounce worker thread
- Your callback is called from the debounce thread

**Important**: If your callback modifies game state, ensure proper synchronization. Consider using a queue to defer actual reload until the main game loop.

### Error Handling

Callbacks that raise exceptions won't crash the watcher:

```python
def safe_callback(changed_files: list[Path]) -> None:
    try:
        # Your reload logic here
        pass
    except Exception as e:
        print(f"Reload error: {e}")
        # Watcher continues running
```

### Performance

The FileWatcher is lightweight:

- Negligible CPU usage when files aren't changing
- Efficient event batching via debouncing
- Non-blocking (uses background threads)

For large codebases, consider narrowing the watch paths to only directories that contain hot-reloadable code.

## ReloadManager

High-level hot-reload orchestration that uses FileWatcher to automatically reload Python modules when files change, with state preservation and integration with the Action system.

### Features

- **Automatic module reloading**: Detects file changes and reloads Python modules using `importlib.reload()`
- **State preservation**: Captures sprite positions, action states, and custom game state before reload
- **Thread-safe queue**: Safely handles file change notifications from background thread
- **Visual feedback**: Optional flash indicator when reload completes
- **Error handling**: Gracefully handles reload failures without crashing
- **Action system integration**: Coordinates with ArcadeActions during reload

### Basic Usage

```python
from pathlib import Path
from arcadeactions.dev import enable_dev_mode

# Enable dev mode with hot-reload
manager = enable_dev_mode(
    watch_paths=["src/game/waves/"],
    root_path=Path("src/"),
    on_reload=lambda files, state: reconstruct_game(files, state)
)

# In game loop:
manager.process_reloads()  # Process queued reloads
manager.indicator.update(delta_time)
manager.indicator.draw()
```

### Advanced Usage

```python
from pathlib import Path
from arcadeactions.dev import enable_dev_mode

def on_reload(changed_files: list[Path], preserved_state: dict) -> None:
    """Called after modules are reloaded."""
    # Reconstruct game objects from new module definitions
    reconstruct_waves(preserved_state)

def state_provider() -> dict:
    """Capture custom game state before reload."""
    return {
        "player_score": player.score,
        "current_level": current_level,
        "enemy_count": len(enemies),
    }

def sprite_provider() -> list:
    """Provide sprites for state preservation."""
    # Return list of sprites to preserve positions/angles/scales
    return [player_sprite] + list(enemy_sprites)

manager = enable_dev_mode(
    watch_paths=["src/game/waves/", "src/game/enemies/"],
    root_path=Path("src/"),
    auto_reload=True,
    on_reload=on_reload,
    state_provider=state_provider,
    sprite_provider=sprite_provider,
    debounce_seconds=0.3,
)

# Start watching
manager.start()

# In game loop:
def on_update(delta_time: float) -> None:
    manager.process_reloads()
    manager.indicator.update(delta_time)
    Action.update_all(delta_time)

def on_draw() -> None:
    arcade.start_render()
    # ... draw game ...
    manager.indicator.draw()  # Draw reload flash
```

### Environment Variable

Enable dev mode automatically via environment variable:

```bash
ARCADEACTIONS_DEV=1 uv run python game.py
```

```python
from arcadeactions.dev import auto_enable_from_env

# Auto-enable if ARCADEACTIONS_DEV=1
manager = auto_enable_from_env()
if manager:
    # Dev mode enabled
    pass
```

### Manual Reload

Force reload specific files:

```python
# Reload specific files
manager.force_reload([Path("src/game/waves.py")])

# Reload all watched modules
manager.force_reload()
```

### State Preservation and Restoration

ReloadManager automatically preserves and restores game state across reloads:

- **Sprite state**: Position, angle, scale (for sprites provided by `sprite_provider`)
  - Baseline state is captured when manager is created
  - After reload, sprites are automatically restored to baseline positions
  - Prevents sprites from drifting during development iterations
- **Action state**: Tags, elapsed time, pause status (for all active actions)
- **Custom state**: Provided by `state_provider` callback

#### Automatic Restoration

By default, sprite positions/angles/scales are automatically restored after reload:

```python
manager = enable_dev_mode(
    watch_paths=["src/game/"],
    auto_restore=True,  # Default - automatically restore sprite state
    sprite_provider=lambda: [player_sprite] + list(enemy_sprites)
)
```

When `auto_restore=True`:
1. Baseline state is captured when manager is created
2. After reload, sprites are automatically restored to baseline positions
3. `on_reload` callback runs after restoration (can override positions)

When `auto_restore=False`:
- State is captured and passed to `on_reload` callback only
- No automatic restoration (manual control)

**Note**: To enable sprite state preservation, provide a `sprite_provider` callback that returns a list of sprites. Without this, only action and custom state will be preserved.

### Module Reload Strategy

ReloadManager:

1. Converts file paths to module names (e.g., `src/game/waves.py` → `game.waves`)
2. Clears `__pycache__` to ensure fresh reload from source
3. Invalidates import caches
4. Reloads modules using `importlib.reload()`
5. Handles errors gracefully

**Note**: Only modules that are already imported will be reloaded. Modules not yet imported are skipped.

### Thread Safety

- FileWatcher callbacks run in background thread
- Reload requests are queued thread-safely
- `process_reloads()` must be called from main thread (game loop)

### Visual Feedback

The `ReloadIndicator` provides a brief yellow flash overlay when reload completes:

```python
# Indicator is automatically created
manager.indicator.trigger()  # Manually trigger flash
manager.indicator.update(delta_time)  # Update animation
manager.indicator.draw()  # Draw overlay
```

### Error Handling

ReloadManager handles errors gracefully with real fallback logic:

- Failed module reloads are logged and skipped (returns `False`)
- Exceptions in `state_provider` are logged with fallback to empty dict
- Exceptions in `sprite_provider` are logged with fallback to empty list
- Exceptions in `on_reload` callback are not caught (your responsibility)
- All error handling provides genuine fallbacks, no silent error suppression

### Keyboard Shortcut for Manual Reload

Enable keyboard shortcut for manual reload by calling `manager.on_key_press()` in your window's key handler:

```python
class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(800, 600, "My Game")
        self.manager = enable_dev_mode(
            watch_paths=["src/game/"],
            reload_key="R"  # Enable R key for manual reload
        )
    
    def on_key_press(self, key, modifiers):
        # Let reload manager handle keyboard shortcuts
        if self.manager:
            self.manager.on_key_press(key, modifiers)
```

Supported reload keys:
- `"R"` - R key (default)
- `"F5"` - F5 key
- `"F6"` - F6 key
- `None` - Disable keyboard shortcut

### State Preservation Control

Control whether state is preserved during reload:

```python
# Preserve state (default) - slower but maintains game state
manager = enable_dev_mode(
    watch_paths=["src/game/"],
    preserve_state=True,  # Default
    state_provider=lambda: {"score": player.score},
    sprite_provider=lambda: [player_sprite]
)

# Skip state preservation - faster but loses game state
manager = enable_dev_mode(
    watch_paths=["src/game/"],
    preserve_state=False  # Skip state preservation
)
```

When `preserve_state=False`:
- Reloads are faster (no state capture overhead)
- Sprite positions, action states, and custom state are NOT preserved
- Useful for quick iteration when state doesn't matter

When `preserve_state=True` (default):
- Sprite positions, angles, scales are preserved
- Action states (tags, elapsed time) are preserved
- Custom state from `state_provider` is preserved
- Slower but maintains game continuity

### Parameters

**enable_dev_mode()**:

- **watch_paths** (`list[Path | str] | None`): Directories to watch (default: current directory)
- **root_path** (`Path | str | None`): Root path for module resolution (default: inferred from watch_paths)
- **auto_reload** (`bool`): Automatically reload on file change (default: `True`)
- **preserve_state** (`bool`): Preserve game state across reloads (default: `True`)
- **auto_restore** (`bool`): Automatically restore sprite state after reload (default: `True`)
  - When `True`, sprite positions/angles/scales are automatically restored to baseline
  - When `False`, state is only passed to `on_reload` callback
  - Only used when `preserve_state=True`
- **reload_key** (`str | None`): Keyboard key for manual reload (default: `"R"`)
- **on_reload** (`Callable[[list[Path], dict], None] | None`): Callback after reload
- **state_provider** (`Callable[[], dict] | None`): Callback to capture custom state
- **sprite_provider** (`Callable[[], list] | None`): Callback to provide sprites for state preservation
- **patterns** (`list[str] | None`): File patterns to watch (default: `["*.py"]`)
- **debounce_seconds** (`float`): Debounce time for file changes (default: `0.3`)

### Example

See [examples/hot_reload_demo.py](../../examples/hot_reload_demo.py) for a complete working example.

## DevVisualizer

A comprehensive visual editor for rapid prototyping, scene editing, and action configuration. DevVisualizer provides drag-and-drop sprite spawning, multi-selection, preset action libraries, boundary editing, and YAML-based scene persistence.

**Key Features:**
- **Automatic pause/resume**: Actions pause when DevVisualizer is visible (edit mode)
- **Import existing sprites**: Edit sprites from running games
- **Export changes**: Sync edited positions back to game
- **F12 toggle**: Quick switch between edit mode and runtime mode
- **Non-destructive**: Edits don't affect running game until exported

### Workflows

**Workflow 1: Editing Existing Game**
```bash
# Run game with DevVisualizer enabled
ARCADEACTIONS_DEVVIZ=1 uv run python examples/invaders.py

# In game:
# 1. Press F12 to enter edit mode (game pauses automatically)
# 2. Import sprites from game for editing (programmatically or via hotkey)
# 3. Adjust positions, edit properties
# 4. Export changes back to game
# 5. Press F12 to resume game and see changes
```

**Workflow 2: Creating New Scenes from Scratch (Truly Zero Boilerplate)**

**Option A: Use the Level Generator (Recommended for New Users)**
```bash
# Generate a new level file with all boilerplate code automatically
uv run python -m arcadeactions.dev.create_level my_level.py

# Or use interactive mode (prompts for filename)
uv run python -m arcadeactions.dev.create_level

# The generator will:
# 1. Create the file with all necessary boilerplate
# 2. Automatically run it with DevVisualizer enabled
# 3. You can start editing immediately!
```

**Option B: Manual Creation (For Advanced Users)**
```bash
# Start with empty scene - ABSOLUTELY NO API calls needed!
ARCADEACTIONS_DEVVIZ=1 uv run python examples/create_boss_level.py

# In editor:
# 1. DevVisualizer auto-enables (no enable_dev_visualizer() call needed!)
# 2. Press F12 to toggle DevVisualizer main overlay (if not visible)
# 3. Press F11 to open palette window
# 4. Click prototypes in palette to spawn sprites
# 5. Click sprites in main window to select them
# 6. Press E to export scene to YAML
# 7. Load YAML in your game code

# Example: create_boss_level.py
# - Just register prototypes with @register_prototype
# - Create a simple View with on_draw() that calls self.clear()
# - That's it! DevVisualizer automatically draws scene_sprites
# - No get_dev_visualizer(), no scene_sprites.draw(), NOTHING!
# - Completely transparent - perfect for beginners!
```

**Workflow 3: Iterative YAML Editing**
```bash
# Round-trip editing
# 1. Export scene to YAML
# 2. Edit YAML in text editor (adjust positions, change presets)
# 3. Import YAML back into DevVisualizer
# 4. Visual adjustments
# 5. Re-export to YAML
```

### Quick Start

**Environment Variable (Recommended):**
```bash
# Enable DevVisualizer automatically
ARCADEACTIONS_DEVVIZ=1 uv run python game.py

# Or use general dev mode (also enables DevVisualizer)
ARCADEACTIONS_DEV=1 uv run python game.py
```

Once enabled, press **F12** to toggle DevVisualizer on/off (edit mode vs runtime mode).

### Level Generator Tool

**New to DevVisualizer? Start here!** The level generator automatically creates all the boilerplate code you need:

```bash
# Shortest command (Makefile target) - Recommended!
make create-level my_level.py

# Or use interactive mode (prompts for filename)
make create-level

# Alternative: Console script (if package is installed)
arccreate-level my_level.py

# Full command (always works)
uv run python -m arcadeactions.dev.create_level my_level.py
```

The generator will:
1. Create a Python file with all necessary boilerplate code
2. Include example prototype registration
3. Set up the View class and main() function
4. Automatically run the file with DevVisualizer enabled

**Features:**
- Automatically derives title from filename (e.g., `my_level.py` → "My Level")
- Creates export name from filename (e.g., `my_level.py` → `my_level.yaml`)
- Validates filename and handles edge cases
- Prompts before overwriting existing files
- Runs the generated file immediately with `ARCADEACTIONS_DEVVIZ=1`

**Example:**
```bash
$ create-action-level boss_fight.py
✓ Created level file: /path/to/boss_fight.py

Running boss_fight.py with DevVisualizer enabled...
```

**Note:** The console script (`create-action-level`) provides a system-wide command that works from any directory.

The generated file includes everything you need - just add your prototype registrations and start editing!

**Zero-Boilerplate Example (Manual Creation - For Advanced Users):**
```python
# create_boss_level.py - Truly zero boilerplate!
import arcade
from arcadeactions import center_window
from arcadeactions.dev import register_prototype

# Register prototypes - these appear in palette automatically
# That's all you need! DevVisualizer handles everything else.
@register_prototype("boss")
def make_boss(ctx):
    sprite = arcade.Sprite(":resources:images/enemies/slimeBlue.png", scale=2.0)
    sprite._prototype_id = "boss"
    return sprite

class SceneEditorView(arcade.View):
    def on_draw(self):
        self.clear()
        # That's it! DevVisualizer automatically draws scene sprites
        # No API calls needed - completely transparent

def main():
    window = arcade.Window(1280, 720, "Boss Level Editor", visible=False)
    center_window(window)
    window.set_visible(True)
    window.show_view(SceneEditorView())
    arcade.run()

if __name__ == "__main__":
    main()

# Run with: ARCADEACTIONS_DEVVIZ=1 uv run python create_boss_level.py
# Press F12 to toggle main overlay, F11 to toggle palette
# Press E to export, I to import
# No get_dev_visualizer(), no scene_sprites.draw() - nothing!
```

**Programmatic (for integrating with existing games):**
```python
from arcadeactions.dev import enable_dev_visualizer

# Enable DevVisualizer (auto-attaches to window)
dev_viz = enable_dev_visualizer(
    scene_sprites=my_scene_sprites,
    auto_attach=True
)

# Press F12 to toggle visibility
```

### Features

- **Sprite Prototype Registry**: Register sprite "prefabs" with decorator-based factories
- **Palette Window**: Separate window with click-to-spawn interface for prototypes (F11)
- **Multi-Selection**: Click-to-select, shift-click, and marquee box selection
- **Action Preset Library**: Composable action presets with parameter editing
- **Boundary Gizmos**: Visual editor for MoveUntil action bounds with draggable handles
- **Sprite Property Inspector**: Secondary property editor window for selected sprites (Alt+I)
- **YAML Templates**: Export/import scenes with round-trip editing support
- **Symbolic Bound Expressions**: Human-readable tokens (OFFSCREEN_LEFT, SCREEN_RIGHT, etc.)
- **Edit Mode**: Sprites are static during editing; actions stored as metadata, not running

### Basic Usage

**Simplest approach (environment variable):**
```bash
# Set environment variable and run game
ARCADEACTIONS_DEVVIZ=1 uv run python game.py

# In your game code, register prototypes:
from arcadeactions.dev import register_prototype

@register_prototype("enemy_ship")
def make_enemy_ship(ctx):
    sprite = arcade.Sprite(":resources:images/space_shooter/enemyShip1.png")
    sprite._prototype_id = "enemy_ship"
    return sprite

# Press F12 to toggle main overlay, F11 to toggle palette
# Click prototypes in palette to spawn, select sprites, edit bounds, export YAML
```

**Programmatic setup:**
```python
import arcade
from arcadeactions.dev import enable_dev_visualizer, register_prototype

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.scene_sprites = arcade.SpriteList()
        
        # Register prototypes
        @register_prototype("enemy_ship")
        def make_enemy(ctx):
            sprite = arcade.Sprite(":resources:images/space_shooter/enemyShip1.png")
            sprite._prototype_id = "enemy_ship"
            return sprite
        
        # Enable DevVisualizer (auto-attaches to window)
        self.dev_viz = enable_dev_visualizer(
            scene_sprites=self.scene_sprites,
            auto_attach=True
        )
        # Press F12 to toggle main overlay, F11 to toggle palette
    
    def on_draw(self):
        """Draw game and DevVisualizer overlays."""
        self.clear()
        self.scene_sprites.draw()
        # DevVisualizer draws automatically when visible (F12)
```

### Sprite Prototype Registration

### Palette Window

The palette window is a separate window that displays registered sprite prototypes. Press **F11** to toggle it.

**Features:**
- Separate window (doesn't overlap main window)
- Click-to-spawn: Click a prototype to spawn it at center of main window (640, 360)
- Resizable and movable
- Auto-shows when DevVisualizer is enabled via environment variable
- Similar pattern to ACE timeline window (F4)

**Spawning Sprites:**
1. Press F11 to open palette window
2. Click a prototype name in the palette
3. Sprite spawns at center of main window
4. Move sprite by selecting and repositioning (future: drag to desired position)

Register sprite "prefabs" that can be spawned from the palette:

```python
from arcadeactions.dev import register_prototype, DevContext
import arcade

@register_prototype("enemy_ship")
def make_enemy_ship(ctx: DevContext):
    """Factory function that creates an enemy ship sprite."""
    ship = arcade.Sprite(":resources:images/space_shooter/enemyShip1.png", scale=0.5)
    ship._prototype_id = "enemy_ship"  # Required for serialization
    return ship

@register_prototype("power_up")
def make_power_up(ctx: DevContext):
    """Factory function that creates a power-up sprite."""
    power = arcade.Sprite(":resources:images/items/star.png", scale=0.8)
    power._prototype_id = "power_up"
    return power
```

**Key Points:**
- Factory functions receive a `DevContext` with scene references
- Must set `_prototype_id` attribute for YAML serialization
- Prototypes are registered globally and can be accessed via `get_registry()`

### Action Preset Library

Create reusable action presets with default parameters:

```python
from arcadeactions.dev import register_preset
from arcadeactions.conditional import infinite

@register_preset("scroll_left_cleanup", category="Movement", params={"speed": 4})
def preset_scroll_left_cleanup(ctx, speed):
    """Preset for sprites that scroll left and cleanup when offscreen."""
    from arcadeactions.helpers import move_until
    return move_until(
        None,  # Unbound action - not applied yet
        velocity=(-speed, 0),
        condition=infinite,
        bounds=(-100, 0, 900, 600),
        boundary_behavior="limit",
        on_boundary_enter=lambda s, axis, side: ctx.on_cleanup(s) if side == "left" else None,
    )

@register_preset("orbit_pattern", category="Movement", params={"radius": 50, "angular_speed": 2})
def preset_orbit(ctx, radius, angular_speed):
    """Preset for orbiting movement pattern."""
    from arcadeactions.pattern import create_orbit_pattern
    return create_orbit_pattern(radius=radius, angular_velocity=angular_speed, condition=infinite)
```

**Key Points:**
- Presets return **unbound actions** (not applied to targets)
- Default parameters are provided in the decorator
- Parameters can be overridden when creating actions from presets
- Actions are stored as metadata in edit mode, not running

### Bulk Preset Attachment

Apply presets to multiple selected sprites at once:

```python
from arcadeactions.dev import get_preset_registry

def attach_preset_to_selected(self, preset_id: str, **params):
    """Bulk attach preset to all selected sprites."""
    selected = self.selection_manager.get_selected()
    preset_registry = get_preset_registry()
    
    for sprite in selected:
        # Store action config as metadata (edit mode)
        if not hasattr(sprite, "_action_configs"):
            sprite._action_configs = []
        
        sprite._action_configs.append({
            "preset": preset_id,
            "params": params,
        })
```

### Boundary Gizmo Editing

Visually edit bounds of MoveUntil actions with draggable handles:

```python
from arcadeactions.dev import BoundaryGizmo
from arcadeactions.conditional import MoveUntil, infinite

# Create sprite with bounded action
sprite = arcade.Sprite(":resources:images/items/star.png")
action = MoveUntil(
    velocity=(5, 0),
    condition=infinite,
    bounds=(0, 0, 800, 600),
    boundary_behavior="limit",
)
action.apply(sprite, tag="movement")

# Create gizmo for visual editing
gizmo = BoundaryGizmo(sprite)

# In mouse handler:
def on_mouse_press(self, x, y, button, modifiers):
    # Check if clicking on a handle
    handle = gizmo.get_handle_at_point(x, y)
    if handle:
        self.dragging_handle = handle
        self.drag_start = (x, y)

def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
    if self.dragging_handle:
        gizmo.handle_drag(self.dragging_handle, dx, dy)
        # Bounds are updated in real-time via set_bounds()

def on_mouse_release(self, x, y, button, modifiers):
    self.dragging_handle = None
```

**Key Points:**
- Gizmo automatically detects MoveUntil actions with bounds
- Four corner handles allow independent edge adjustment
- Bounds update in real-time via `action.set_bounds()`
- Visual feedback with semi-transparent rectangle overlay

### YAML Template Export/Import

Export scenes to YAML, modify them, and reimport for iterative design:

```python
from arcadeactions.dev import export_template, load_scene_template, DevContext

# Export scene
scene_sprites = arcade.SpriteList()
# ... populate scene with sprites and action configs ...
export_template(scene_sprites, "wave1.yaml", prompt_user=False)
# Or omit path to open a file picker (plyer):
export_template(scene_sprites, path=None, prompt_user=False)

# Later: Import and modify
ctx = DevContext(scene_sprites=arcade.SpriteList())
load_scene_template("wave1.yaml", ctx)
# Or omit path to open a file picker (plyer):
load_scene_template(path=None, ctx=ctx)

# Modify sprites (positions, action configs)
for sprite in ctx.scene_sprites:
    sprite.center_x += 50  # Adjust position
    # Modify action configs
    if hasattr(sprite, "_action_configs"):
        for config in sprite._action_configs:
            if config["preset"] == "scroll_left_cleanup":
                config["params"]["speed"] = 6.0  # Change speed

# Re-export
export_template(ctx.scene_sprites, "wave1.yaml", prompt_user=False)
```

**YAML Schema:**
```yaml
- prototype: "enemy_ship"
  x: 200
  y: 400
  group: "wave_enemies"
  actions:
    - preset: "scroll_left_cleanup"
      params:
        speed: 4.0
- prototype: "power_up"
  x: 500
  y: 300
  group: ""
  actions: []
```

**Symbolic Bound Expressions:**
The YAML loader supports symbolic tokens for bounds:

```python
# In YAML:
bounds: [OFFSCREEN_LEFT, 0, SCREEN_RIGHT, SCREEN_HEIGHT]

# Resolved to actual values during import
# OFFSCREEN_LEFT = -100, SCREEN_RIGHT = 800, etc.
```

Available symbolic tokens:
- `OFFSCREEN_LEFT`, `OFFSCREEN_RIGHT`
- `SCREEN_LEFT`, `SCREEN_RIGHT`
- `SCREEN_BOTTOM`, `SCREEN_TOP`
- `SCREEN_WIDTH`, `SCREEN_HEIGHT`
- `WALL_WIDTH`

### Edit Mode vs Runtime Mode

**Critical Distinction:** DevVisualizer operates in **edit mode** where sprites are static and actions are automatically paused:

```python
# Edit Mode (DevVisualizer visible)
dev_viz.show()  # Automatically pauses all actions via Action.pause_all()
# Sprites are static - no movement
# Actions are paused but still exist

# Runtime Mode (Game running)
dev_viz.hide()  # Automatically resumes all actions via Action.resume_all()
Action.update_all(delta_time)  # Actions execute normally

# Toggle between modes with F12
# Press F12 → pauses actions (edit mode)
# Press F12 again → resumes actions (runtime mode)
```

**Key Features:**
- **Automatic pause/resume**: Showing DevVisualizer pauses all actions; hiding resumes them
- **Non-destructive**: Actions remain intact, just paused during editing
- **Safe editing**: Edit sprite positions without interference from running actions
- **Action metadata**: Store action configs as metadata for later instantiation

**Working with Action Metadata:**
```python
# Store action config as metadata (won't execute in edit mode)
sprite._action_configs = [
    {"action_type": "MoveUntil", "velocity": (5, 0), "condition": "infinite"}
]

# Convert to runtime actions
dev_viz.apply_metadata_actions(sprite)
dev_viz.hide()  # Resume actions
Action.update_all(delta_time)  # Sprite now moves
```

This separation allows safe editing without sprites moving during design.

### Importing Sprites from Existing Games

DevVisualizer can import sprites from running games for editing:

```python
# In your game code
class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.enemies = arcade.SpriteList()
        self.bullets = arcade.SpriteList()
        # ... populate sprite lists ...
        
        # Create DevVisualizer
        self.dev_viz = enable_dev_visualizer(auto_attach=True)
        
        # Import sprites from game for editing
        # This creates copies that can be edited without affecting the running game
        self.dev_viz.import_sprites(self.enemies, self.bullets)
```

**Import Features:**
- **Creates copies**: Original sprites remain untouched during editing
- **Preserves properties**: Texture, position, angle, scale, color, alpha all copied
- **Tracks originals**: Stores reference to original sprite for syncing back changes
- **Multiple lists**: Import from multiple sprite lists at once
- **Clear or append**: Choose to replace scene or add to existing sprites

**Export Changes Back:**
```python
# After editing in DevVisualizer
dev_viz.export_sprites()  # Syncs positions/properties back to original sprites

# Example workflow:
# 1. Press F12 to enter edit mode (pauses game)
# 2. Import sprites: dev_viz.import_sprites(game_sprites)
# 3. Edit positions, adjust properties
# 4. Export changes: dev_viz.export_sprites()
# 5. Press F12 to exit edit mode (resumes game)
```

**Code Sync (Reverse Sync):**
DevVisualizer can automatically update your source code files when you export sprite changes. This requires sprites to be tagged with position IDs:

```python
from arcadeactions.dev.position_tag import positioned

@positioned("forcefield")
def make_forcefield():
    sprite = arcade.Sprite(":resources:images/tiles/grassCenter.png")
    sprite.left = 100
    sprite.top = 200
    return sprite

# When you export_sprites(), DevVisualizer will:
# - Find the source code location for sprite.left/center_x assignments
# - Update the source file with new values
# - Preserve formatting and comments using libcst
```

The code sync system:
- Updates position assignments (e.g., `sprite.left = X`, `sprite.center_x = Y`)
- Updates `arrange_grid()` call parameters (`start_x`, `start_y`)
- Creates per-cell overrides in `arrange_grid()` calls when individual sprites are moved
- Creates backup files (`.bak`) before making changes
- Preserves code formatting and comments

**Import Options:**
```python
# Clear scene before importing (default)
dev_viz.import_sprites(enemies, bullets, clear=True)

# Append to existing scene
dev_viz.import_sprites(power_ups, clear=False)

# Import single sprite list
dev_viz.import_sprites(player_list)
```

### Multi-Selection

DevVisualizer supports three selection modes:

1. **Single Click**: Select one sprite (replaces previous selection)
2. **Shift-Click**: Add/remove sprite from selection (toggle)
3. **Click-Drag Marquee**: Box-select multiple sprites

```python
# Selection manager handles all three modes automatically
manager = SelectionManager(scene_sprites)

# Single click
manager.handle_mouse_press(x, y, shift=False)

# Shift-click
manager.handle_mouse_press(x, y, shift=True)

# Marquee (drag)
manager.handle_mouse_press(start_x, start_y, shift=False)
manager.handle_mouse_drag(current_x, current_y)
manager.handle_mouse_release(end_x, end_y)

# Get selected sprites
selected = manager.get_selected()  # Returns list[arcade.Sprite]
```

### Environment Variables

DevVisualizer supports multiple environment variable names for flexibility:

1. **`ARCADEACTIONS_DEVVIZ=1`** (Recommended) - Explicit DevVisualizer enable
2. **`ARCADEACTIONS_DEV=1`** - General dev mode (also enables hot-reload)

**Priority:** If multiple are set, `ARCADEACTIONS_DEVVIZ` takes precedence, then `ARCADEACTIONS_DEV`.

When enabled via environment variable, DevVisualizer automatically:
- Creates a scene SpriteList
- Attaches to the current window
- Registers F12, F11, F8, and Alt+I keyboard handlers
- Shows main overlay and palette window automatically

### Keyboard Shortcuts

- **F12**: Toggle DevVisualizer main overlay (selection, gizmos, indicator)
- **F11**: Toggle palette window (separate window with sprite prototypes)
- **F8**: Toggle dev command palette window (secondary command UI)
- **Alt+I**: Toggle sprite property inspector window (live property editing)
- **Enter** (in property inspector): Start editing highlighted property, and commit current text input
- **Escape** (in property inspector): Cancel active property edit (or close window if not editing)
- **Ctrl+Z / Ctrl+Shift+Z** (in property inspector): Undo/redo property edits
- **E**: Export scene to YAML (saves to scene.yaml or examples/boss_level.yaml)
- **I**: Import scene from YAML (loads from scene.yaml, examples/boss_level.yaml, or scenes/new_scene.yaml)
- **ESC**: Close application (in generated level files)
- **Mouse**: Click prototypes in palette to spawn, click sprites to select, drag gizmo handles
- **Ctrl+Left Click** (sprite with source marker): Open source file at marker line
- **Left Click** (sprite with arrange marker): Select the full arrange-grid group and open arrange-grid settings editor
- **Shift+Click**: Add/remove from selection
- **Click+Drag**: Marquee box selection

**Arrange Settings Shortcuts** (when Arrange Grid Settings mode is open):
- **Up/Down arrows**: Select one of `rows`, `cols`, `start_x`, `start_y`, `spacing_x`, `spacing_y`
- **Enter**: Start editing selected setting, then commit edited value
- **Escape**: Cancel active edit (or close window if not editing)
- **Ctrl+Z / Ctrl+Shift+Z**: Undo/redo setting edits

### Parameters

**enable_dev_visualizer()**:
- **scene_sprites** (`arcade.SpriteList | None`): SpriteList for editable scene (created if None)
- **window** (`arcade.Window | None`): Arcade window (auto-detected if None)
- **auto_attach** (`bool`): Automatically attach to window (default: `True`)

**DevVisualizer Methods**:
- **show()**: Show DevVisualizer main overlay and palette window, pause all actions (enter edit mode)
- **hide()**: Hide DevVisualizer main overlay and palette window, resume all actions (exit edit mode)
- **toggle()**: Toggle main overlay visibility and pause/resume state
- **toggle_palette()**: Toggle palette window visibility (F11)
- **import_sprites(*sprite_lists, clear=True)**: Import sprites from game for editing
- **export_sprites()**: Sync edited sprite properties back to originals
- **apply_metadata_actions(sprite)**: Convert action metadata to runtime actions

**PaletteWindow** (Separate window for sprite palette):
- **registry** (`SpritePrototypeRegistry`): Registry with registered prototypes
- **ctx** (`DevContext`): DevContext with scene_sprites reference
- **title** (`str`): Window title (default: `"Sprite Palette"`)
- **width** (`int`): Window width (default: `250`)
- **height** (`int`): Window height (default: `400`)
- **on_close_callback** (`Callable`): Optional callback when window closes
- **Methods**: `show_window()`, `hide_window()`, `toggle_window()`

**PaletteSidebar** (Deprecated - use PaletteWindow instead):
- Kept for backward compatibility
- Use PaletteWindow for new code

**SelectionManager**:
- **scene_sprites** (`arcade.SpriteList`): SpriteList containing sprites that can be selected

**BoundaryGizmo**:
- **sprite** (`arcade.Sprite`): Sprite to check for bounded actions

**position_tag module**:
- **tag_sprite(sprite, position_id)**: Tag a sprite with a stable position ID
- **positioned(position_id)**: Decorator for factory functions to auto-tag sprites
- **get_sprites_for(position_id)**: Get all sprites with a given position ID
- **remove_sprite_from_registry(sprite)**: Remove sprite from position registry

**code_parser module**:
- **parse_file(path)**: Parse file and return position assignments and arrange calls
- **parse_source(source, filename)**: Parse source string and return assignments and calls
- **PositionAssignment**: Dataclass with file, lineno, target_expr, attr, value_src
- **ArrangeCall**: Dataclass with file, lineno, call_src, kwargs, tokens

**export_template**:
- **sprites** (`arcade.SpriteList`): SpriteList containing sprites to export
- **path** (`str | Path`): File path to write YAML to
- **prompt_user** (`bool`): If True, prompt before overwriting (default: `True`)

**load_scene_template**:
- **path** (`str | Path`): File path to read YAML from
- **ctx** (`DevContext`): DevContext with scene_sprites and registry access
- Returns: `arcade.SpriteList` with loaded sprites

### Arrange Grid Overrides Editor

DevVisualizer repurposes the Sprite Property Inspector window as an Arrange Grid Settings editor for `arrange_grid()`-linked sprites.

**Opening the Overrides Editor:**
1. Select or click a sprite linked to an `arrange_grid()` call
2. Plain left-click an arrange-linked sprite
3. The inspector switches to **Arrange Grid Settings** mode
4. Edit `rows`, `cols`, `start_x`, `start_y`, `spacing_x`, and `spacing_y` directly

**Using Position Tags:**
To enable code sync and override editing, tag your sprites with stable position IDs:

```python
from arcadeactions.dev.position_tag import positioned, tag_sprite

# Option 1: Decorator on factory function
@positioned("enemy_formation")
def make_enemy():
    sprite = arcade.Sprite(":resources:images/enemies/slimeBlue.png")
    return sprite

# Option 2: Tag at runtime
enemy = arcade.Sprite(":resources:images/enemies/slimeBlue.png")
tag_sprite(enemy, "enemy_formation")
```

**Code Parser:**
The code parser finds position assignments and `arrange_grid()` calls in your source:

```python
from arcadeactions.dev.code_parser import parse_file, PositionAssignment, ArrangeCall

# Parse a source file
assignments, arrange_calls = parse_file("game.py")

# Position assignments (sprite.left, sprite.top, sprite.center_x)
for assign in assignments:
    print(f"{assign.target_expr}.{assign.attr} = {assign.value_src} at line {assign.lineno}")

# Arrange grid calls
for call in arrange_calls:
    print(f"arrange_grid at line {call.lineno} with {call.kwargs}")
```

### Best Practices

1. **Zero boilerplate for new scenes**: Just register prototypes and use `get_dev_visualizer()` - no `enable_dev_visualizer()` needed
2. **Register prototypes early**: Set up all prototypes before creating the visualizer
3. **Use palette window**: Press F11 to open the separate palette window (cleaner than overlay)
4. **Click to spawn**: Click prototypes in palette window to spawn sprites at center (640, 360)
5. **Use meaningful preset names**: Clear names make the preset library easier to navigate
6. **Organize presets by category**: Use categories like "Movement", "Effects", "Formations"
7. **Store action configs as metadata**: Never call `action.apply()` during editing
8. **Export frequently**: Press E to save work often with YAML export
9. **Use symbolic bounds**: Makes YAML files more readable and maintainable
10. **Test round-trip**: Verify export → import → export maintains all data
11. **Tag sprites for code sync**: Use `@positioned()` decorator or `tag_sprite()` to enable automatic source code updates
12. **Use arrange settings editor for grid tuning**: Left-click sprites from arrange_grid calls to edit rows/cols/start/spacing values

### Example

See [Pattern 12-16 in API Usage Guide](../../docs/api_usage_guide.md#development-visualizer-actionsdev) for detailed usage patterns and complete examples.

## See Also

- [Plan: 10× Developer Speed Boost](../../.cursor/plans/) - Full roadmap for development tools
- [Example: file_watcher_demo.py](../../examples/file_watcher_demo.py) - Live demonstration
- [Tests: test_file_watcher.py](../../tests/test_file_watcher.py) - Usage examples in tests
