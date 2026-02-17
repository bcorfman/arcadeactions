### DevVisualizer Development Tools (arcadeactions/dev/):
* SpritePrototypeRegistry: Decorator-based registry for sprite "prefabs" that can be spawned in the visualizer
  - Use @register_prototype("id") to register factory functions
  - Prototypes receive DevContext with scene_sprites reference
  - Sprites must have _prototype_id attribute set for serialization
* PaletteSidebar: Drag-and-drop interface for spawning prototypes into scene
  - Shows list of registered prototypes
  - Handles mouse drag operations to spawn sprites at world coordinates
  - Maintains drag ghost sprite during drag operation
* SelectionManager: Multi-selection system for sprites
  - Single click: select sprite (replaces previous selection)
  - Shift-click: add/remove sprite from selection
  - Click-drag marquee: box-select multiple sprites
  - Draws glowing outline around selected sprites
  - Stores selection in internal set, exposes via get_selected()
* ActionPresetRegistry: Decorator-based registry for composable Action presets
  - Use @register_preset("id", category="Movement", params={"speed": 4}) to register
  - Presets return unbound Action instances (not applied to targets)
  - Supports parameter editing for bulk application
  - Actions stored as metadata (_action_configs) in edit mode, not running
* BoundaryGizmo: Visual editor for MoveUntil action bounds
  - Detects sprites with MoveUntil actions that have bounds
  - Displays semi-transparent rectangle showing bounds
  - Four draggable corner handles for editing bounds
  - Updates action.bounds via set_bounds() method in real-time
* YAML Templates: Export/import sprite scenes with action configurations
  - export_template(sprites, path=None): Export scene to YAML file
  - load_scene_template(path=None, ctx=...): Import scene from YAML (clears and rebuilds)
  - If `path` is omitted, prompts with `plyer.filechooser.save_file`/`open_file`
  - Supports symbolic bound expressions (OFFSCREEN_LEFT, SCREEN_RIGHT, etc.)
  - Actions stored as preset recipes, not running instances (edit mode)
  - Round-trip editing: export → modify → reimport → re-export
* Dev Command Palette Window (F8): Secondary window for development commands
  - Toggle with F8, close with F8 or ESC
  - Anchors to the left of the main window (matching the F11 palette side)
  - Stacks directly below the F11 sprite palette window when that window is present
  - Shows enabled/disabled command list with quick-key labels
  - Supports arrow-key selection + Enter execution
  - Unhandled keys forward to the main game window handlers
  - Import command reloads scene YAML and reapplies sprite action metadata immediately
  - Uses headless-safe behavior in tests/CI so palette tests do not require a display
* Source/Arrange Click Behavior:
  - `Ctrl+Click` on a sprite with source markers opens source at the marker line
  - Plain `Click` on a normal sprite opens the Sprite Property Inspector in **Sprite Properties** mode
  - Plain `Click` on a sprite with an `arrange` marker selects the full arrange-grid group and opens the Sprite Property Inspector in **Arrange Grid Settings** mode
* Sprite Property Inspector Window (Alt+I): Secondary window for live property editing
  - Toggle with Alt+I, independent from F12 edit-mode overlay visibility
  - Edits selected sprite properties in real time (single and multi-select)
  - Use `Enter` to start editing the highlighted property, type in the input widget, and press `Enter` again to commit
  - Entering edit mode pre-fills the widget with the current value and places the caret at the end
  - Supports expression input for numeric fields (for example `SCREEN_CENTER + 100`)
  - Use `Escape` to cancel an active edit; `Ctrl+Z` / `Ctrl+Shift+Z` still undo/redo changes
  - In Arrange Grid Settings mode, edit `rows`, `cols`, `start_x`, `start_y`, `spacing_x`, and `spacing_y` for the selected arrange-grid call
  - Changing `rows`/`cols` live-resizes the selected arrange group in-scene so sprite count matches `rows * cols`
  - Closing the inspector from the window titlebar close button is supported; `Alt+I` recreates/reopens it
  - If `arcade.gui` widget rendering fails on a backend/driver, inspector editing is disabled for that session instead of crashing
* Edit Mode vs Runtime Mode:
  - Edit Mode: Sprites are static, actions stored as metadata (_action_configs)
  - Entering edit mode (F12 on) freezes sprite `change_x`/`change_y`/`change_angle` motion fields
  - Leaving edit mode (F12 off) restores those motion fields and resumes actions
  - No action.apply() calls during editing - sprites remain frozen
  - Actions only instantiated when exporting to runtime or previewing
  - This allows selection, positioning, and parameter editing without movement
* Integration Pattern:
  - DevVisualizer components are standalone and composable
  - Use PaletteSidebar for spawning, SelectionManager for selection
  - Apply presets via registry.create() and store as metadata
  - Use BoundaryGizmo when sprite with bounded action is selected
  - Export/import via templates module for persistence
