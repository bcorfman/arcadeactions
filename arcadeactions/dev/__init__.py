"""
ArcadeActions development tools - hot-reload, visualization, and editing utilities.

This module provides development-focused tools that extend ArcadeActions with
instant feedback, visual editing, and hot-reload capabilities.

Usage:
    from arcadeactions.dev import enable_dev_mode

    # Enable development mode (hot-reload + dev tools)
    enable_dev_mode(
        watch_paths=["src/my_game/waves/", "src/my_game/scenes/"],
        auto_reload=True,
        preserve_state=True,  # Preserve game state across reloads
        reload_key="R"  # Enable R key for manual reload
    )

    # In game loop:
    manager = enable_dev_mode(...)
    manager.process_reloads()  # Process queued reloads
    manager.indicator.update(delta_time)
    manager.indicator.draw()

    # Or use environment variable:
    # ARCADEACTIONS_DEV=1 uv run python game.py
"""

import os
from collections.abc import Callable
from pathlib import Path

from . import code_parser
from .boundary_overlay import BoundaryGizmo, BoundaryHandle
from .command_registry import CommandExecutionContext, CommandRegistry
from .devshell_command_palette_panel import DevShellCommandPalettePanel
from .devshell_coordinator import DevShellCoordinator
from .devshell_focus import DevShellFocusManager
from .devshell_input_router import DevShellInputRouter
from .devshell_layout import DevShellLayout, DevShellRect, DevShellRegions
from .devshell_property_inspector_panel import DevShellPropertyInspectorPanel
from .devshell_prototype_palette_panel import DevShellPrototypePalettePanel
from .devshell_state import (
    DevShellFocusVisualState,
    DevShellMode,
    DevShellPanelVisualState,
    DevShellStateController,
)
from .devshell_text_buffer import DevShellTextBuffer
from .palette import PaletteSidebar
from .presets import (
    ActionPresetRegistry,
    get_preset_registry,
    register_preset,
)
from .property_history import PropertyHistory
from .property_inspector import SpritePropertyInspector
from .property_registry import PropertyDefinition, SpritePropertyRegistry
from .prototype_registry import (
    DevContext,
    SpritePrototypeRegistry,
    register_prototype,
)
from .prototype_registry import (
    get_registry as get_prototype_registry,
)
from .reload import ReloadIndicator, ReloadManager
from .selection import SelectionManager
from .templates import SYMBOLIC, export_template, load_scene_template
from .visualizer import (
    DevVisualizer,
    auto_enable_dev_visualizer_from_env,
    enable_dev_visualizer,
    get_dev_visualizer,
)
from .watch import FileWatcher

__all__ = [
    # Hot reload
    "FileWatcher",
    "ReloadManager",
    "ReloadIndicator",
    "enable_dev_mode",
    "auto_enable_from_env",
    # DevVisualizer
    "DevContext",
    "SpritePrototypeRegistry",
    "register_prototype",
    "get_prototype_registry",
    "ActionPresetRegistry",
    "register_preset",
    "get_preset_registry",
    "PaletteSidebar",
    "PropertyDefinition",
    "PropertyHistory",
    "SpritePropertyRegistry",
    "SpritePropertyInspector",
    "SelectionManager",
    "BoundaryGizmo",
    "BoundaryHandle",
    "CommandRegistry",
    "CommandExecutionContext",
    "DevShellCommandPalettePanel",
    "DevShellCoordinator",
    "DevShellPropertyInspectorPanel",
    "DevShellPrototypePalettePanel",
    "DevShellLayout",
    "DevShellRect",
    "DevShellRegions",
    "DevShellFocusManager",
    "DevShellInputRouter",
    "DevShellMode",
    "DevShellPanelVisualState",
    "DevShellFocusVisualState",
    "DevShellStateController",
    "DevShellTextBuffer",
    "export_template",
    "load_scene_template",
    "SYMBOLIC",
    "code_parser",
    # DevVisualizer Manager
    "DevVisualizer",
    "enable_dev_visualizer",
    "get_dev_visualizer",
    "auto_enable_dev_visualizer_from_env",
]


def enable_dev_mode(
    watch_paths: list[Path | str] | None = None,
    auto_reload: bool = True,
    preserve_state: bool = True,
    auto_restore: bool = True,
    reload_key: str | None = "R",
    state_provider: Callable[[], dict] | None = None,
    sprite_provider: Callable[[], list] | None = None,
    on_reload: Callable[[list[Path], dict], None] | None = None,
    root_path: Path | str | None = None,
    patterns: list[str] | None = None,
    debounce_seconds: float = 0.3,
) -> ReloadManager:
    """
    Enable development mode with hot-reload functionality.

    Creates and starts a ReloadManager that monitors Python files for changes
    and automatically reloads them, preserving game state across reloads.

    Args:
        watch_paths: Directories to watch for changes (default: current directory)
        auto_reload: Automatically reload on file change (default: True)
        preserve_state: Preserve game state across reloads (default: True)
            When True, sprite positions, action state, and custom state are preserved
            When False, state preservation is skipped (faster but loses game state)
        auto_restore: Automatically restore sprite state after reload (default: True)
            When True, sprite positions/angles/scales are restored automatically
            When False, state is only passed to on_reload callback
            Only used when preserve_state=True
        reload_key: Keyboard key for manual reload (default: "R")
            Call manager.on_key_press(key, modifiers) in your window's on_key_press
            Use None to disable manual reload key
        state_provider: Optional callback to capture custom game state
            Should return a dictionary with game-specific state
        sprite_provider: Optional callback to provide sprites for state preservation
            Should return a list of arcade.Sprite or arcade.SpriteList to preserve
        on_reload: Optional callback called after reload completes
            Receives (changed_files: list[Path], preserved_state: dict)
        root_path: Root path for module name resolution (default: current directory)
        patterns: File patterns to watch (default: ["*.py"])
        debounce_seconds: Debounce time for file changes (default: 0.3)

    Returns:
        ReloadManager instance - call .process_reloads() in game loop

    Example:
        def on_game_reload(files, state):
            # Reconstruct game objects after reload
            reconstruct_waves(state)

        manager = enable_dev_mode(
            watch_paths=["src/game/waves/"],
            on_reload=on_game_reload,
            state_provider=lambda: {"score": player.score, "level": current_level},
            sprite_provider=lambda: [player_sprite] + list(enemy_sprites)
        )

        # In game loop:
        manager.process_reloads()
        manager.indicator.update(delta_time)
        manager.indicator.draw()

        # In on_key_press handler:
        def on_key_press(self, key, modifiers):
            if self.manager:
                self.manager.on_key_press(key, modifiers)
    """
    if watch_paths is None:
        watch_paths = [Path.cwd()]

    if root_path is None:
        # Try to infer root_path from watch_paths
        if watch_paths:
            # Use first watch path's parent as root, or the watch path itself
            first_path = Path(watch_paths[0])
            if first_path.is_file():
                root_path = first_path.parent
            elif first_path.is_dir():
                root_path = first_path
            else:
                root_path = Path.cwd()
        else:
            root_path = Path.cwd()

    # Always resolve root_path to absolute path to avoid issues with
    # FileWatcher providing absolute paths in callbacks
    root_path = Path(root_path).resolve()

    manager = ReloadManager(
        watch_paths=watch_paths,
        root_path=root_path,
        auto_reload=auto_reload,
        preserve_state=preserve_state,
        auto_restore=auto_restore,
        state_provider=state_provider,
        sprite_provider=sprite_provider,
        on_reload=on_reload,
        patterns=patterns,
        debounce_seconds=debounce_seconds,
    )

    # Store reload_key for keyboard shortcut support
    manager.reload_key = reload_key

    manager.start()

    return manager


def auto_enable_from_env() -> ReloadManager | None:
    """
    Auto-enable dev mode if ARCADEACTIONS_DEV environment variable is set.

    Checks for ARCADEACTIONS_DEV=1 and automatically enables hot-reload
    with default settings.

    Returns:
        ReloadManager instance if enabled, None otherwise

    Example:
        # In game.py:
        manager = auto_enable_from_env()
        if manager:
            # Dev mode enabled - call process_reloads() in loop
            pass
    """
    if os.environ.get("ARCADEACTIONS_DEV") == "1":
        return enable_dev_mode()
    return None


# Note: DevVisualizer auto-enable is handled by arcadeactions/__init__.py
# to avoid duplicate initialization when arcadeactions.dev is imported.
