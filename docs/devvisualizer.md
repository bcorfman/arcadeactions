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
* DevShell Command Palette Panel (F8): In-window command panel
  - Toggle with F8, close with F8 or ESC
  - Shows enabled/disabled command list with quick-key labels
  - Supports arrow-key selection + Enter execution
  - Import command reloads scene YAML and reapplies sprite action metadata immediately
  - Routed through the single DevShell input path
* Source/Arrange Click Behavior:
  - `Ctrl+Click` on a sprite with source markers opens source at the marker line
  - Plain `Click` on a normal sprite opens the Sprite Property Inspector in **Sprite Properties** mode
  - Plain `Click` on a sprite with an `arrange` marker selects the full arrange-grid group and opens the Sprite Property Inspector in **Arrange Grid Settings** mode
* DevShell Property Inspector Panel (Alt+I): In-window live property editing
  - Toggle with Alt+I
  - Edits selected sprite properties in real time (single and multi-select)
  - Use `Enter` to start editing the highlighted property, type in the input widget, and press `Enter` again to commit
  - Entering edit mode pre-fills the widget with the current value and places the caret at the end
  - Supports expression input for numeric fields (for example `SCREEN_CENTER + 100`)
  - Use `Escape` to cancel an active edit; `Ctrl+Z` / `Ctrl+Shift+Z` still undo/redo changes
  - In Arrange Grid Settings mode, edit `rows`, `cols`, `start_x`, `start_y`, `spacing_x`, and `spacing_y` for the selected arrange-grid call
  - Changing `rows`/`cols` live-resizes the selected arrange group in-scene so sprite count matches `rows * cols`
  - Panel editing is window-free and backend-independent
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

### Phase 0 DevShell Foundation (One-Window Migration)
* DevShellLayout (`arcadeactions/dev/devshell_layout.py`)
  - Encodes minimum window-size contract: stage + rails
  - Computes stage/rail rectangles for Edit-Live and Preview-Clean
  - Live integration:
    - `DevVisualizer` enforces min window size in DevShell mode (`set_minimum_size`)
    - draw path renders Edit-Live rail regions and stage boundary from computed regions
* DevShellFocusManager (`arcadeactions/dev/devshell_focus.py`)
  - Tracks open panel order, active panel, and text-edit ownership
  - Supports focus cycling semantics used by `Tab` / `Shift+Tab`
* DevShellInputRouter (`arcadeactions/dev/devshell_input_router.py`)
  - Single-owner input dispatch for key/text/text-motion
  - Implements layered `Esc` behavior:
    - exit text-edit mode
    - close transient panel
    - clear focus back to game stage
* DevShellStateController (`arcadeactions/dev/devshell_state.py`)
  - Runtime mode model: `Edit-Live`, `Preview-Clean`, `Production`
  - Preview toggle semantics and production-mode focus reset
  - Focus visibility state model for panel UI rendering:
    - top focus label (`Focus: ...`)
    - active panel flags
    - caret ownership flag
    - focus pulse token for transient highlight animation
* DevShellCommandPalettePanel (`arcadeactions/dev/devshell_command_palette_panel.py`)
  - Window-free command palette panel model for DevShell rails
  - Handles:
    - open/close visibility
    - enabled-command navigation (`Up`/`Down`)
    - command execution (`Enter`, quick keys)
    - panel close shortcuts (`Esc`, `F8`)
  - Exposes router adapter methods:
    - `on_key_press`
    - `on_text` (returns `False`)
    - `on_text_motion` (returns `False`)
  - Designed for router-driven integration with no cross-window forwarding
* DevShellTextBuffer (`arcadeactions/dev/devshell_text_buffer.py`)
  - Deterministic text-edit core for inspector/prompt panels
  - Supports:
    - single-insert semantics (no duplicate char insertion)
    - selection replacement
    - backspace/delete semantics
    - caret movement and line-edge jumps
  - Intended to replace backend-coupled widget text mutation in DevShell migrations
* DevShellPropertyInspectorPanel (`arcadeactions/dev/devshell_property_inspector_panel.py`)
  - Window-free inspector panel controller for one-window DevShell rails
  - Delegates property model behavior to existing inspector model while replacing widget input path
  - Handles:
    - Enter-to-edit / Enter-to-commit flow
    - layered Esc behavior (cancel edit before hide)
    - Ctrl+Z / Ctrl+Shift+Z undo/redo delegation
    - navigation keys and bool toggle support
    - editing key motions via `DevShellTextBuffer`
  - Exposes router adapter methods:
    - `on_key_press`
    - `on_text`
    - `on_text_motion`
  - Emits edit start/end callbacks so coordinator focus state can own/release text-edit routing deterministically
* DevShellCoordinator (`arcadeactions/dev/devshell_coordinator.py`)
  - Integration-ready composition layer combining:
    - `DevShellFocusManager`
    - `DevShellStateController`
    - `DevShellInputRouter`
  - Synchronizes runtime mode changes with input routing behavior
  - Provides a single routing entry point for key/text/text-motion
* Feature flag integration status (`ARCADEACTIONS_DEVVIZ=1`)
  - `DevVisualizer` initializes window-free DevShell prototype palette, command palette, and property inspector panel models.
  - Wrapped key/text/text-motion handlers route to `devshell_coordinator` first when available.
  - In DevShell mode, wrappers now bypass legacy property-inspector forwarding and legacy `Esc` close-window behavior to avoid mixed-path regressions.
  - F11 (`toggle_palette`), F8 (`toggle_command_palette`), and inspector-open paths (`Alt+I`, click-open selection flow) use DevShell panel visibility/focus state instead of opening a secondary window.
  - Edit-Live mode now draws basic in-window DevShell panels when visible:
    - prototype palette panel (registered prototype list + selection marker)
    - command palette panel (header + enabled command list with current selection marker)
    - property inspector panel (header + current property/value summary + validation error line)
  - Edit-Live draw path now renders a focus overlay (top-right) with:
    - `Focus: <owner>` label
    - per-panel `[ACTIVE]` badge
    - transient per-panel `[PULSE]` badge on focus changes
    - per-panel `[TEXT]` badge when a panel owns text-edit mode
  - Preview-Clean mode suppresses the focus overlay.
  - Runtime mode hotkey:
    - `F10` toggles `Edit-Live` ↔ `Preview-Clean`
  - Secondary-window paths have been removed in favor of DevShell-only routing.
* Current status
  - These are isolated foundation modules with dedicated unit coverage
  - Unit coverage includes:
    - `tests/dev/test_devshell_layout.py`
    - `tests/dev/test_devshell_focus.py`
    - `tests/dev/test_devshell_input_router.py`
    - `tests/dev/test_devshell_state.py`
    - `tests/dev/test_devshell_command_palette_panel.py`
    - `tests/dev/test_devshell_text_buffer.py`
    - `tests/dev/test_devshell_property_inspector_panel.py`
    - `tests/dev/test_devshell_coordinator.py`
  - Integration-unit coverage includes:
    - `tests/dev/test_event_handlers_devshell_unit.py`
    - `tests/dev/test_visualizer_devshell_panels_unit.py`
    - `tests/dev/test_visualizer_devshell_focus_overlay_unit.py`
  - Legacy secondary-window forwarding/tests removed; DevShell-only routing remains.
