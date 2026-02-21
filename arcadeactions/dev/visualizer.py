"""DevVisualizer manager for coordinating visual editing tools.

Provides unified entry point for DevVisualizer with environment variable
support and keyboard toggle (F12).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

import arcade

if TYPE_CHECKING:
    from arcadeactions.dev.boundary_overlay import BoundaryGizmo
    from arcadeactions.dev.prototype_registry import DevContext
    from arcadeactions.dev.selection import SelectionManager

from arcadeactions import Action
from arcadeactions.dev import (
    event_handlers,
    visualizer_draw,
    visualizer_export,
    visualizer_keys,
    visualizer_metadata,
    window_utils,
)
from arcadeactions.dev import window_hooks as _window_hooks
from arcadeactions.dev.boundary_overlay import BoundaryGizmo
from arcadeactions.dev.command_registry import CommandExecutionContext, CommandRegistry
from arcadeactions.dev.arrange_editor import ArrangeGridEditor
from arcadeactions.dev.devshell_command_palette_panel import DevShellCommandPalettePanel
from arcadeactions.dev.devshell_coordinator import DevShellCoordinator
from arcadeactions.dev.devshell_layout import DevShellLayout, DevShellRegions
from arcadeactions.dev.devshell_property_inspector_panel import DevShellPropertyInspectorPanel
from arcadeactions.dev.devshell_prototype_palette_panel import DevShellPrototypePalettePanel
from arcadeactions.dev.property_history import PropertyHistory
from arcadeactions.dev.property_inspector import SpritePropertyInspector
from arcadeactions.dev.property_registry import SpritePropertyRegistry
from arcadeactions.dev.prototype_registry import DevContext, get_registry
from arcadeactions.dev.selection import SelectionManager
from arcadeactions.dev.visualizer_protocols import (
    SpriteWithActionConfigs,
    SpriteWithOriginal,
    SpriteWithPositionId,
    SpriteWithSourceMarkers,
    WindowWithContext,
)
from arcadeactions.dev.window_position_tracker import WindowPositionTracker

_MISSING_GIZMO_REFRESH_SECONDS = 0.25

__all__ = [
    "DevVisualizer",
    "enable_dev_visualizer",
    "get_dev_visualizer",
    "auto_enable_dev_visualizer_from_env",
    "SpriteWithActionConfigs",
    "SpriteWithOriginal",
    "SpriteWithPositionId",
    "SpriteWithSourceMarkers",
    "WindowWithContext",
]


def _install_window_attach_hook() -> None:
    """Install hook on set_window to attach DevVisualizer when a window becomes available."""
    _window_hooks.install_window_attach_hook(get_dev_visualizer)


def _install_update_all_attach_hook() -> None:
    """Wrap Action.update_all so we can attach DevVisualizer once a window exists."""
    _window_hooks.install_update_all_attach_hook(get_dev_visualizer)


class _NoopGameInputTarget:
    """Fallback game input target used while DevShell integration is partial."""

    def on_key_press(self, _key: int, _modifiers: int) -> bool:
        return False

    def on_text(self, _text: str) -> bool:
        return False

    def on_text_motion(self, _motion: int) -> bool:
        return False


class DevVisualizer:
    """
    Manager for DevVisualizer visual editing tools.

    Coordinates palette, selection, boundary gizmos, and scene management.
    Provides unified entry point with environment variable support and F12 toggle.
    """

    def __init__(
        self,
        scene_sprites: arcade.SpriteList | None = None,
        window: arcade.Window | None = None,
    ):
        """
        Initialize DevVisualizer.

        Args:
            scene_sprites: SpriteList for editable scene (created if None)
            window: Arcade window (auto-detected if None)
        """
        # Window must be assigned before any optional panel initialization that may depend on it.
        self.window = window

        if scene_sprites is None:
            scene_sprites = arcade.SpriteList()

        self.scene_sprites = scene_sprites
        self.ctx = DevContext(scene_sprites=scene_sprites)

        # Initialize components
        self.command_registry = CommandRegistry()
        self.devshell_coordinator: DevShellCoordinator | None = None
        self.devshell_layout: DevShellLayout | None = None
        self._devshell_prototype_palette_panel: DevShellPrototypePalettePanel | None = None
        self._devshell_command_palette_panel: DevShellCommandPalettePanel | None = None
        self._devshell_property_inspector_panel: DevShellPropertyInspectorPanel | None = None
        self._devshell_panels_enabled = True
        self._devshell_focus_last_pulse_token = 0
        self._devshell_focus_pulse_until = 0.0
        self.property_registry = SpritePropertyRegistry()
        self.property_history = PropertyHistory(max_changes_per_sprite=20)
        self.selection_manager = SelectionManager(scene_sprites)

        # Legacy override panel backend remains for compatibility with tests/utilities.
        from arcadeactions.dev.override_panel import OverridesPanel

        self.overrides_panel = OverridesPanel(self)
        self._register_default_commands()
        self._init_devshell_panels_if_enabled()

        # State
        self.visible = False
        self._dragging_gizmo_handle: tuple[BoundaryGizmo, object] | None = None
        self._dragging_sprites: list[tuple[arcade.Sprite, float, float]] | None = None  # (sprite, offset_x, offset_y)
        self._gizmos: WeakKeyDictionary[arcade.Sprite, BoundaryGizmo | None] = WeakKeyDictionary()
        self._gizmo_miss_refresh_at: WeakKeyDictionary[arcade.Sprite, float] = WeakKeyDictionary()
        self._frozen_sprite_motion: WeakKeyDictionary[arcade.Sprite, tuple[float, float, float]] = WeakKeyDictionary()
        self._position_tracker = WindowPositionTracker()

        # Create indicator text (shown when DevVisualizer is active)
        self._indicator_text = arcade.Text(
            "Palette [F11] | DEV EDIT MODE [F12]",
            10,
            10,
            arcade.color.YELLOW,
            16,
            bold=True,
        )

        # Track if we've attached to window
        self._attached = False
        self._original_on_draw: Callable[..., None] | None = None
        self._original_on_key_press: Callable[..., None] | None = None
        self._original_on_mouse_press: Callable[..., None] | None = None
        self._original_on_mouse_drag: Callable[..., None] | None = None
        self._original_on_mouse_release: Callable[..., None] | None = None
        self._original_on_text: Callable[..., None] | None = None
        self._original_on_text_motion: Callable[..., None] | None = None
        self._original_on_close: Callable[..., None] | None = None
        self._original_view_on_draw: Callable[..., None] | None = None
        self._original_show_view: Callable[..., None] | None = None
        self._original_set_location: Callable[..., None] | None = None

    @property
    def devshell_panels_enabled(self) -> bool:
        """Expose feature-flag state to event-handler routing helpers."""
        return self._devshell_panels_enabled

    def _init_devshell_panels_if_enabled(self) -> None:
        """Initialize one-window DevShell panel models behind feature flag."""
        if not self._devshell_panels_enabled:
            self.devshell_coordinator = None
            self.devshell_layout = None
            self._devshell_prototype_palette_panel = None
            self._devshell_command_palette_panel = None
            self._devshell_property_inspector_panel = None
            return

        self.devshell_layout = DevShellLayout(
            stage_width=1280,
            stage_height=720,
            left_rail_width=280,
            right_rail_width=340,
            top_rail_height=48,
            bottom_rail_height=36,
        )

        panel_inspector = SpritePropertyInspector(
            property_registry=self.property_registry,
            history=self.property_history,
            window=self.window,
        )
        self._devshell_property_inspector_panel = DevShellPropertyInspectorPanel(
            inspector=panel_inspector,
            on_edit_start=lambda: self._set_devshell_text_edit_owner("property_inspector", True),
            on_edit_end=lambda: self._set_devshell_text_edit_owner("property_inspector", False),
        )
        self._devshell_prototype_palette_panel = DevShellPrototypePalettePanel(
            registry=get_registry(),
            dev_context=self.ctx,
        )
        self._devshell_command_palette_panel = DevShellCommandPalettePanel(
            registry=self.command_registry,
            context_provider=self._build_command_context,
        )
        self.devshell_coordinator = DevShellCoordinator(
            game_target=_NoopGameInputTarget(),
            panel_targets={
                "prototype_palette": self._devshell_prototype_palette_panel,
                "command_palette": self._devshell_command_palette_panel,
                "property_inspector": self._devshell_property_inspector_panel,
            },
            panel_order=[],
            transient_panels={"command_palette"},
            close_panel=self._close_devshell_panel,
        )
        self._sync_devshell_panel_order()
        self._ensure_devshell_window_contract()

    def _set_devshell_text_edit_owner(self, panel_id: str, editing: bool) -> None:
        coordinator = self.devshell_coordinator
        if coordinator is None:
            return
        if editing:
            coordinator.focus_manager.begin_text_edit(panel_id)
            return
        coordinator.focus_manager.end_text_edit()

    def _ensure_devshell_window_contract(self) -> None:
        if not self._devshell_panels_enabled:
            return
        if self.window is None:
            return
        if self.devshell_layout is None:
            return
        min_width, min_height = self.devshell_layout.min_window_size()
        try:
            self.window.set_minimum_size(int(min_width), int(min_height))
        except Exception:
            return

    def devshell_regions(self) -> DevShellRegions | None:
        """Return current stage/rail regions for one-window DevShell mode."""
        if not self._devshell_panels_enabled:
            return None
        if self.devshell_layout is None:
            return None
        if self.window is None:
            return None
        coordinator = self.devshell_coordinator
        preview_clean = False
        if coordinator is not None:
            preview_clean = coordinator.state.is_preview_clean()
        return self.devshell_layout.compute_regions(
            window_width=int(self.window.width),
            window_height=int(self.window.height),
            preview_clean=preview_clean,
        )

    def toggle_preview_clean_mode(self) -> bool:
        """Toggle between Edit-Live and Preview-Clean when DevShell is enabled."""
        if not self._devshell_panels_enabled:
            return False
        coordinator = self.devshell_coordinator
        if coordinator is None:
            return False
        if coordinator.state.is_preview_clean():
            coordinator.set_preview_clean(False)
            return True
        coordinator.set_preview_clean(True)
        return True

    def _close_devshell_panel(self, panel_id: str) -> None:
        if panel_id == "prototype_palette" and self._devshell_prototype_palette_panel is not None:
            self._devshell_prototype_palette_panel.set_visible(False)
        if panel_id == "command_palette" and self._devshell_command_palette_panel is not None:
            self._devshell_command_palette_panel.set_visible(False)
        if panel_id == "property_inspector" and self._devshell_property_inspector_panel is not None:
            self._devshell_property_inspector_panel.set_visible(False)
        self._sync_devshell_panel_order()

    def _sync_devshell_panel_order(self) -> None:
        coordinator = self.devshell_coordinator
        if coordinator is None:
            return
        panel_order: list[str] = []
        if self._devshell_prototype_palette_panel is not None and self._devshell_prototype_palette_panel.visible:
            panel_order.append("prototype_palette")
        if self._devshell_command_palette_panel is not None and self._devshell_command_palette_panel.visible:
            panel_order.append("command_palette")
        if self._devshell_property_inspector_panel is not None and self._devshell_property_inspector_panel.visible:
            panel_order.append("property_inspector")
        coordinator.set_panel_order(panel_order)

    def track_window_position(self, window: arcade.Window) -> bool:
        """Track the current position of a window.

        This should be called after positioning a window to enable relative positioning
        of other windows. For example, call this after move_to_primary_monitor().

        Args:
            window: The window to track the position of

        Returns:
            True if a valid position was recorded, False otherwise.
        """
        return self._position_tracker.track_window_position(window)

    def _get_tracked_window_position(self, window: arcade.Window) -> tuple[int, int] | None:
        """Get the tracked position for a window."""
        return self._position_tracker.get_tracked_position(window)

    def reset_scene(self, scene_sprites: arcade.SpriteList) -> None:
        """Reset DevVisualizer state to use a new SpriteList.

        This is used to keep enable_dev_visualizer() idempotent when a caller
        provides a new SpriteList while a global DevVisualizer already exists.
        """
        self.scene_sprites = scene_sprites
        self.ctx = DevContext(scene_sprites=scene_sprites)
        self.selection_manager = SelectionManager(scene_sprites)
        from arcadeactions.dev.override_panel import OverridesPanel

        self.overrides_panel = OverridesPanel(self)
        self._dragging_gizmo_handle = None
        self._dragging_sprites = None
        self._gizmos = WeakKeyDictionary()
        self._gizmo_miss_refresh_at = WeakKeyDictionary()
        self._frozen_sprite_motion = WeakKeyDictionary()

    def update_main_window_position(self) -> bool:
        """Track the main window position for non-DevShell callers."""
        window = self.window
        if window is None:
            return False
        return self.track_window_position(window)

    def attach_to_window(self, window: arcade.Window | None = None) -> bool:
        """
        Attach DevVisualizer to window, wrapping event handlers.

        Args:
            window: Window to attach to (uses arcade.get_window() if None)

        Note: If already attached, detaches first before re-attaching.
        """
        # Detach if already attached
        if self._attached:
            self.detach_from_window()

        if window is None:
            try:
                window = arcade.get_window()
            except RuntimeError:
                return False

        if window is None:
            return False

        self.window = window
        self._ensure_devshell_window_contract()

        # Try to track the main window position for relative positioning
        self.track_window_position(window)

        event_handlers.wrap_window_handlers(self, window, has_window_context=window_utils.has_window_context)

        self._attached = True
        return True

    def _wrap_view_on_draw(self, view: arcade.View) -> None:
        """Wrap a View's on_draw and event handlers to integrate DevVisualizer."""
        event_handlers.wrap_view_handlers(self, view)

    def detach_from_window(self) -> None:
        """Detach DevVisualizer from window, restoring original handlers."""
        if not self._attached or self.window is None:
            return

        was_visible = self.visible

        self.window.on_draw = self._original_on_draw
        self.window.on_key_press = self._original_on_key_press
        self.window.on_mouse_press = self._original_on_mouse_press
        self.window.on_mouse_drag = self._original_on_mouse_drag
        self.window.on_mouse_release = self._original_on_mouse_release
        self.window.on_text = self._original_on_text
        self.window.on_text_motion = self._original_on_text_motion
        self.window.on_close = self._original_on_close
        if self._original_set_location is not None:
            self.window.set_location = self._original_set_location  # type: ignore[assignment]
        if self._original_on_close:
            self.window.on_close = self._original_on_close

        # Restore show_view
        if self._original_show_view:
            self.window.show_view = self._original_show_view  # type: ignore[assignment]

        # Restore current view's handlers if they exist
        current_view = getattr(self.window, "current_view", None)
        if current_view is not None and hasattr(current_view, "_dev_viz_original_on_draw"):
            current_view.on_draw = current_view._dev_viz_original_on_draw  # type: ignore[assignment]
            if hasattr(current_view, "_dev_viz_original_on_key_press"):
                current_view.on_key_press = current_view._dev_viz_original_on_key_press  # type: ignore[assignment]
            if hasattr(current_view, "_dev_viz_original_on_mouse_press"):
                current_view.on_mouse_press = current_view._dev_viz_original_on_mouse_press  # type: ignore[assignment]
            if hasattr(current_view, "_dev_viz_original_on_mouse_drag"):
                current_view.on_mouse_drag = current_view._dev_viz_original_on_mouse_drag  # type: ignore[assignment]
            if hasattr(current_view, "_dev_viz_original_on_mouse_release"):
                current_view.on_mouse_release = current_view._dev_viz_original_on_mouse_release  # type: ignore[assignment]
            if hasattr(current_view, "_dev_viz_original_on_text"):
                current_view.on_text = current_view._dev_viz_original_on_text  # type: ignore[assignment]
            if hasattr(current_view, "_dev_viz_original_on_text_motion"):
                current_view.on_text_motion = current_view._dev_viz_original_on_text_motion  # type: ignore[assignment]
            # Clean up stored originals
            for attr in [
                "_dev_viz_original_on_draw",
                "_dev_viz_original_on_key_press",
                "_dev_viz_original_on_mouse_press",
                "_dev_viz_original_on_mouse_drag",
                "_dev_viz_original_on_mouse_release",
                "_dev_viz_original_on_text",
                "_dev_viz_original_on_text_motion",
            ]:
                if hasattr(current_view, attr):
                    delattr(current_view, attr)

        self._attached = False
        if was_visible:
            # Mirror hide() semantics so paused actions resume on detach.
            # Also reset drag states to prevent stale state when reattaching.
            self._dragging_gizmo_handle = None
            self._dragging_sprites = None
            self.selection_manager._is_dragging_marquee = False
            self.selection_manager._marquee_start = None
            self.selection_manager._marquee_end = None
            Action.resume_all()

        self.visible = False

        self._original_on_close = None
        self._original_set_location = None

    def toggle(self) -> None:
        """Toggle DevVisualizer visibility and pause/resume actions."""
        if self.visible:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        """Show DevVisualizer and pause all actions (enter edit mode)."""
        self.visible = True
        self._ensure_devshell_window_contract()
        self._freeze_scene_sprite_motion()
        if self._devshell_prototype_palette_panel is not None:
            self._devshell_prototype_palette_panel.set_visible(True)
        self._sync_devshell_panel_order()
        Action.pause_all()

    def hide(self) -> None:
        """Hide DevVisualizer and resume all actions (exit edit mode)."""
        self.visible = False
        if self._devshell_prototype_palette_panel is not None:
            self._devshell_prototype_palette_panel.set_visible(False)
        if self._devshell_command_palette_panel is not None:
            self._devshell_command_palette_panel.set_visible(False)
        if self._devshell_property_inspector_panel is not None:
            self._devshell_property_inspector_panel.set_visible(False)
        self._sync_devshell_panel_order()
        if self.devshell_coordinator is not None:
            self.devshell_coordinator.set_active_panel(None)
        # Reset all drag states to prevent stale drag when hidden during drag operation
        # This ensures that if F12 is pressed during a drag, all drag states are cleaned up
        # since the mouse release event will be skipped when visible=False
        self._dragging_gizmo_handle = None
        self._dragging_sprites = None
        # Reset selection marquee drag state
        self.selection_manager._is_dragging_marquee = False
        self.selection_manager._marquee_start = None
        self.selection_manager._marquee_end = None
        self._restore_scene_sprite_motion()
        Action.resume_all()

    def _freeze_scene_sprite_motion(self) -> None:
        """Freeze per-sprite motion fields so edit-mode drags are deterministic."""
        for sprite in self.scene_sprites:
            if sprite not in self._frozen_sprite_motion:
                self._frozen_sprite_motion[sprite] = (
                    float(sprite.change_x),
                    float(sprite.change_y),
                    float(sprite.change_angle),
                )
            sprite.change_x = 0
            sprite.change_y = 0
            sprite.change_angle = 0

    def _restore_scene_sprite_motion(self) -> None:
        """Restore scene sprite motion fields captured at edit-mode entry."""
        for sprite, motion in list(self._frozen_sprite_motion.items()):
            sprite.change_x = motion[0]
            sprite.change_y = motion[1]
            sprite.change_angle = motion[2]
        self._frozen_sprite_motion = WeakKeyDictionary()

    def toggle_palette(self) -> None:
        """Toggle prototype palette panel visibility."""
        if self._devshell_prototype_palette_panel is None:
            return
        panel = self._devshell_prototype_palette_panel
        panel.toggle_visible()
        self._sync_devshell_panel_order()
        if self.devshell_coordinator is not None:
            if panel.visible:
                self.devshell_coordinator.set_active_panel("prototype_palette")
            else:
                self.devshell_coordinator.set_active_panel(None)

    def _build_command_context(self) -> CommandExecutionContext:
        """Build execution context for command handlers."""
        selection = list(self.selection_manager.get_selected())
        return CommandExecutionContext(
            window=self.window,
            scene_sprites=self.scene_sprites,
            selection=selection,
        )

    def _sync_property_inspector_selection(self) -> None:
        if self._devshell_property_inspector_panel is not None:
            self._devshell_property_inspector_panel.set_selection(self.selection_manager.get_selected())

    def toggle_property_inspector(self) -> None:
        """Toggle property inspector panel (Alt+I)."""
        if self._devshell_property_inspector_panel is None:
            return
        panel = self._devshell_property_inspector_panel
        panel.show_properties_mode()
        panel.set_visible(not panel.visible)
        self._sync_devshell_panel_order()
        if panel.visible:
            panel.set_selection(self.selection_manager.get_selected())
            if self.devshell_coordinator is not None:
                self.devshell_coordinator.set_active_panel("property_inspector")
            return
        if self.devshell_coordinator is not None:
            self.devshell_coordinator.set_active_panel(None)

    def open_property_inspector_for_current_selection(self) -> bool:
        """Show inspector in properties mode and sync current selection without toggling."""
        if self._devshell_property_inspector_panel is None:
            return False
        panel = self._devshell_property_inspector_panel
        panel.show_properties_mode()
        panel.set_selection(self.selection_manager.get_selected())
        panel.set_visible(True)
        self._sync_devshell_panel_order()
        if self.devshell_coordinator is not None:
            self.devshell_coordinator.set_active_panel("property_inspector")
        return True

    def toggle_command_palette(self) -> None:
        """Toggle command palette panel (F8)."""
        if self._devshell_command_palette_panel is None:
            return
        panel = self._devshell_command_palette_panel
        panel.toggle_visible()
        self._sync_devshell_panel_order()
        if self.devshell_coordinator is not None:
            if panel.visible:
                self.devshell_coordinator.set_active_panel("command_palette")
            else:
                self.devshell_coordinator.set_active_panel(None)

    def _register_default_commands(self) -> None:
        """Register built-in command palette commands."""
        self.command_registry.register_command(
            key=arcade.key.E,
            name="Export Scene",
            category="Export/Import",
            handler=self._command_export_scene,
        )
        self.command_registry.register_command(
            key=arcade.key.I,
            name="Import Scene",
            category="Export/Import",
            handler=self._command_import_scene,
        )
        self.command_registry.register_command(
            key=arcade.key.S,
            name="Toggle Snap-to-Grid",
            category="Positioning",
            handler=self._command_not_implemented,
            enabled_check=self._command_disabled,
        )
        self.command_registry.register_command(
            key=arcade.key.G,
            name="Toggle Grid Overlay",
            category="Visualization",
            handler=self._command_not_implemented,
            enabled_check=self._command_disabled,
        )
        self.command_registry.register_command(
            key=arcade.key.T,
            name="Open Template Browser",
            category="Other",
            handler=self._command_not_implemented,
            enabled_check=self._command_disabled,
        )
        self.command_registry.register_command(
            key=arcade.key.H,
            name="Show Help",
            category="Other",
            handler=self._command_show_help,
        )
        self.command_registry.register_command(
            key=arcade.key.L,
            name="Explain Selection",
            category="LLM",
            handler=self._command_not_implemented,
            enabled_check=self._command_disabled,
        )
        self.command_registry.register_command(
            key=arcade.key.F,
            name="Suggest Formation",
            category="LLM",
            handler=self._command_not_implemented,
            enabled_check=self._command_disabled,
        )
        self.command_registry.register_command(
            key=arcade.key.P,
            name="Generate Patch",
            category="LLM",
            handler=self._command_not_implemented,
            enabled_check=self._command_disabled,
        )

    @staticmethod
    def _command_disabled(_context: CommandExecutionContext) -> bool:
        return False

    @staticmethod
    def _command_not_implemented(_context: CommandExecutionContext) -> bool:
        return False

    def _command_export_scene(self, _context: CommandExecutionContext) -> bool:
        from arcadeactions.dev.templates import export_template

        filename = "scene.yaml"
        if os.path.exists("examples"):
            filename = "examples/boss_level.yaml"
        elif os.path.exists("scenes"):
            filename = "scenes/new_scene.yaml"

        export_template(self.scene_sprites, filename, prompt_user=False)
        print(f"✓ Exported {len(self.scene_sprites)} sprites to {filename}")
        return True

    def _command_import_scene(self, _context: CommandExecutionContext) -> bool:
        from arcadeactions.dev.templates import load_scene_template

        for filename in ["scene.yaml", "examples/boss_level.yaml", "scenes/new_scene.yaml"]:
            if os.path.exists(filename):
                load_scene_template(filename, self.ctx)
                for sprite in self.scene_sprites:
                    self.apply_metadata_actions(sprite)
                print(f"✓ Imported scene from {filename} ({len(self.scene_sprites)} sprites)")
                return True
        print("⚠ No scene file found. Try: scene.yaml, examples/boss_level.yaml, or scenes/new_scene.yaml")
        return True

    def _command_show_help(self, _context: CommandExecutionContext) -> bool:
        print("Dev Commands: E export, I import, H help, O overrides panel, F8 palette")
        return True

    def handle_key_press(self, key: int, modifiers: int) -> bool:
        """
        Handle keyboard input for DevVisualizer.

        Args:
            key: Key code
            modifiers: Modifier keys

        Returns:
            True if key was handled, False otherwise
        """
        return visualizer_keys.handle_key_press(self, key, modifiers)

    def _devshell_prototype_panel_geometry(self) -> tuple[int, int, int, int] | None:
        if self._devshell_prototype_palette_panel is None:
            return None
        regions = self.devshell_regions()
        if regions is None:
            return None
        if regions.left.width <= 0 or regions.left.height <= 0:
            return None
        panel_width = max(220, regions.left.width - 24)
        panel_height = max(200, regions.left.height - 120)
        left = regions.left.x + 12
        bottom = regions.left.y + 56
        return (left, bottom, panel_width, panel_height)

    def _handle_devshell_prototype_panel_click(self, x: int, y: int, button: int) -> bool:
        panel = self._devshell_prototype_palette_panel
        if panel is None:
            return False
        if not panel.visible:
            return False
        if button != arcade.MOUSE_BUTTON_LEFT:
            return False
        geometry = self._devshell_prototype_panel_geometry()
        if geometry is None:
            return False
        left, bottom, width, height = geometry
        if x < left or x > left + width or y < bottom or y > bottom + height:
            return False
        prototypes = panel.prototype_ids()
        if not prototypes:
            return True
        title_height = 34
        row_height = 20
        row_top = bottom + height - title_height - 8
        clicked_index = int((row_top - y) / row_height)
        if clicked_index < 0 or clicked_index >= len(prototypes):
            return True
        panel.selected_index = clicked_index
        panel.spawn_selected()
        return True

    def handle_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool:
        """
        Handle mouse press for DevVisualizer.

        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
            button: Mouse button
            modifiers: Modifier keys

        Returns:
            True if event was handled, False otherwise
        """
        shift = modifiers & arcade.key.MOD_SHIFT

        # Handle right-click to deselect all
        if button == arcade.MOUSE_BUTTON_RIGHT:
            self.selection_manager.clear_selection()
            return True

        # Only handle left mouse button for dragging and selection
        if button != arcade.MOUSE_BUTTON_LEFT:
            return False

        if self._handle_devshell_prototype_panel_click(x, y, button):
            return True

        # Palette is now in separate window, no need to check here
        ctrl_held = bool(modifiers & arcade.key.MOD_CTRL)
        shift_held = bool(modifiers & arcade.key.MOD_SHIFT)

        # Check boundary gizmo handles (highest priority)
        selected = self.selection_manager.get_selected()
        for sprite in selected:
            gizmo = self._get_gizmo(sprite)
            if gizmo and gizmo.has_bounded_action():
                handle = gizmo.get_handle_at_point(x, y)
                if handle:
                    self._dragging_gizmo_handle = (gizmo, handle)
                    return True

        # Check if clicking on a selected sprite to start drag
        clicked_sprites = arcade.get_sprites_at_point((x, y), self.scene_sprites)
        if clicked_sprites:
            clicked_sprite = clicked_sprites[0]

            if isinstance(clicked_sprite, SpriteWithSourceMarkers):
                markers = clicked_sprite._source_markers
                if markers and ctrl_held:
                    self.open_sprite_source(clicked_sprite, markers[0])
                    return True

                has_arrange_marker = self.sprite_has_arrange_marker(clicked_sprite)
                if has_arrange_marker and not ctrl_held and not shift_held:
                    arrange_group = self._arrange_group_for_sprite(clicked_sprite)
                    self.selection_manager.clear_selection()
                    self.selection_manager._selected.update(arrange_group)
                    self._sync_property_inspector_selection()
                    self.open_overrides_editor_for_sprite(clicked_sprite)
                    return True

            if clicked_sprite in selected:
                if not ctrl_held:
                    self.open_property_inspector_for_current_selection()
                # Start dragging selected sprites
                # Calculate offset from click point to each sprite's center
                self._dragging_sprites = []
                for sprite in selected:
                    offset_x = sprite.center_x - x
                    offset_y = sprite.center_y - y
                    self._dragging_sprites.append((sprite, offset_x, offset_y))
                return True

        # Then handle selection (for unselected sprites or empty space)
        if self.selection_manager.handle_mouse_press(x, y, shift):
            if clicked_sprites and not ctrl_held:
                self.open_property_inspector_for_current_selection()
            else:
                self._sync_property_inspector_selection()
            return True
        return False

    def handle_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> bool:
        """
        Handle mouse drag for DevVisualizer.

        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
            dx: X delta
            dy: Y delta
            buttons: Mouse buttons
            modifiers: Modifier keys

        Returns:
            True if event was handled, False otherwise
        """
        handled = False

        # Palette is now in separate window, no need to handle drag here

        # Handle gizmo drag (highest priority)
        if self._dragging_gizmo_handle:
            gizmo, handle = self._dragging_gizmo_handle
            gizmo.handle_drag(handle, dx, dy)
            handled = True

        # Handle sprite dragging
        elif self._dragging_sprites:
            # Update positions of all dragged sprites
            for sprite, offset_x, offset_y in self._dragging_sprites:
                sprite.center_x = x + offset_x
                sprite.center_y = y + offset_y
            handled = True

        # Handle selection marquee (lowest priority)
        elif self.selection_manager._is_dragging_marquee:
            self.selection_manager.handle_mouse_drag(x, y)
            handled = True

        return handled

    def handle_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> bool:
        """
        Handle mouse release for DevVisualizer.

        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
            button: Mouse button
            modifiers: Modifier keys

        Returns:
            True if event was handled, False otherwise
        """
        handled = False

        # Palette is now in separate window, no need to handle release here

        # Handle gizmo release
        if self._dragging_gizmo_handle:
            self._dragging_gizmo_handle = None
            handled = True

        # Handle sprite drag release
        if self._dragging_sprites:
            self._dragging_sprites = None
            handled = True

        # Handle selection release (returns None, check if actively dragging marquee)
        if self.selection_manager._is_dragging_marquee:
            self.selection_manager.handle_mouse_release(x, y)
            self._sync_property_inspector_selection()
            handled = True

        return handled

    def _get_gizmo(self, sprite: arcade.Sprite) -> BoundaryGizmo | None:
        """Get or create gizmo for sprite."""
        if sprite in self._gizmos:
            cached_gizmo = self._gizmos[sprite]
            if cached_gizmo is not None:
                return cached_gizmo

            now = time.monotonic()
            refresh_at = self._gizmo_miss_refresh_at.get(sprite, 0.0)
            if now < refresh_at:
                return None

            # Cache expired; force a re-check below
            del self._gizmos[sprite]
            self._gizmo_miss_refresh_at.pop(sprite, None)

        gizmo = BoundaryGizmo(sprite)
        if gizmo.has_bounded_action():
            self._gizmos[sprite] = gizmo
            self._gizmo_miss_refresh_at.pop(sprite, None)
            return gizmo

        # Negative cache to avoid re-checking every frame, but allow periodic refresh
        expires_at = time.monotonic() + _MISSING_GIZMO_REFRESH_SECONDS
        self._gizmos[sprite] = None
        self._gizmo_miss_refresh_at[sprite] = expires_at
        return None

    def draw(self) -> None:
        """Draw DevVisualizer overlays (selection, gizmos, source markers).

        Note: scene_sprites are drawn automatically in wrapped_on_draw(),
        so this method only draws the editor UI overlays. Palette is now in a
        separate window (toggle with F11).
        """
        if not self.visible:
            return

        # Verify we have a valid window and context before drawing
        if self.window is None:
            return
        self._sync_property_inspector_selection()

        visualizer_draw.draw_visualizer(self)

    def import_sprites(self, *sprite_lists: arcade.SpriteList, clear: bool = True) -> None:
        """Import sprites from game sprite lists into the scene for editing.

        Creates copies of sprites that can be edited in the DevVisualizer.
        Original sprites are stored as references for syncing back changes.

        Args:
            *sprite_lists: One or more SpriteList objects to import from
            clear: If True, clear existing scene sprites before importing (default: True)
        """
        if clear:
            self.scene_sprites.clear()
            self.selection_manager.clear_selection()
            self._gizmos.clear()
            self._gizmo_miss_refresh_at.clear()

        for sprite_list in sprite_lists:
            for original_sprite in sprite_list:
                # Create a copy of the sprite
                imported_sprite = arcade.Sprite()

                # Copy visual properties
                imported_sprite.texture = original_sprite.texture
                imported_sprite.center_x = original_sprite.center_x
                imported_sprite.center_y = original_sprite.center_y
                imported_sprite.angle = original_sprite.angle
                # Scale can be a tuple or float - handle both
                if isinstance(original_sprite.scale, tuple):
                    imported_sprite.scale = original_sprite.scale
                else:
                    imported_sprite.scale = (original_sprite.scale, original_sprite.scale)
                imported_sprite.alpha = original_sprite.alpha
                imported_sprite.color = original_sprite.color

                # Store reference to original for syncing back
                imported_sprite._original_sprite = original_sprite

                # Add to scene
                self.scene_sprites.append(imported_sprite)

    def export_sprites(self) -> None:
        """Export sprite changes back to original game sprites.

        Syncs position, angle, scale, and other properties from edited sprites
        back to their original sprites (if they have _original_sprite reference).
        """
        visualizer_export.export_sprites(self.scene_sprites)

    # ------------------------
    # Preset / edit-mode helpers
    # ------------------------
    def attach_preset_to_selected(self, preset_id: str, params: dict | None = None, tag: str | None = None) -> None:
        """Attach a preset to all currently selected sprites as metadata (_action_configs).

        This is the programmatic API used by the editor UI to attach presets in edit mode.
        """
        if params is None:
            params = {}

        selected = self.selection_manager.get_selected()
        for sprite in selected:
            # Initialize _action_configs if missing (protocol requires attribute to exist)
            if not isinstance(sprite, SpriteWithActionConfigs):
                sprite._action_configs = []  # type: ignore[attr-defined]
            entry = {"preset": preset_id, "params": params.copy()}
            if tag is not None:
                entry["tag"] = tag
            sprite._action_configs.append(entry)  # type: ignore[attr-defined]

    def update_action_config(
        self, sprite: arcade.Sprite | SpriteWithActionConfigs, config_index: int, **updates
    ) -> None:
        """Update a single action config dict on a sprite (edit mode).

        Args:
            sprite: Target sprite (must have _action_configs attribute)
            config_index: Index of config in sprite._action_configs
            **updates: Key/values to set on the config dict
        """
        if not isinstance(sprite, SpriteWithActionConfigs):
            raise ValueError("Sprite has no _action_configs")
        configs = sprite._action_configs
        if config_index < 0 or config_index >= len(configs):
            raise IndexError("config_index out of range")
        cfg = configs[config_index]
        cfg.update(updates)

    def update_selected_action_config(self, config_index: int, **updates) -> None:
        """Update the action config at the given index for all selected sprites."""
        selected = self.selection_manager.get_selected()
        for sprite in selected:
            try:
                self.update_action_config(sprite, config_index, **updates)
            except Exception:
                # Ignore failures per-sprite (e.g., missing index)
                pass

    def open_sprite_source(self, sprite: arcade.Sprite, marker: dict) -> None:
        """Open the editor at the sprite's source marker via `code --goto`."""
        import os
        import subprocess

        file = marker.get("file")
        lineno = marker.get("lineno")
        if not file:
            return
        path = os.path.abspath(file)
        try:
            subprocess.Popen(["code", "--goto", f"{path}:{lineno}"])
            return
        except Exception:
            print(f"Open file at {file}:{lineno}")

    def apply_metadata_actions(self, sprite: arcade.Sprite, resolver: Callable[[str], Any] | None = None) -> None:
        """Convert action metadata on sprite to actual running actions.

        Takes action configs stored as metadata (_action_configs) and applies
        them as actual Action instances. This converts from edit mode to runtime mode.

        Args:
            sprite: Sprite with _action_configs metadata to apply (early return if missing)
            resolver: Optional callable taking a string and returning a callable (for callbacks)
        """
        visualizer_metadata.apply_metadata_actions(sprite, self.ctx, resolver=resolver)

    def on_reload(self, changed_files: list, saved_state: dict | None = None) -> None:
        """Handle a reload event by parsing changed files and updating source markers on tagged sprites.

        Args:
            changed_files: list of pathlib.Path objects for changed files
            saved_state: preserved state passed from reload manager (ignored here)
        """
        try:
            from arcadeactions.dev import code_parser
            from arcadeactions.dev.position_tag import get_sprites_for
        except Exception:
            return

        # Parse all changed files and collect assignments
        parsed_assign_by_token: dict[str, list] = {}
        parsed_arrange_by_token: dict[str, list] = {}
        for file_path in changed_files:
            try:
                assignments, arrange_calls = code_parser.parse_file(str(file_path))
            except Exception:
                continue

            for a in assignments:
                # Extract tokens from target expression (simple identifier tokenization)
                import re

                tokens = re.findall(r"\b\w+\b", a.target_expr)
                for t in tokens:
                    parsed_assign_by_token.setdefault(t, []).append(a)

            # Also collect arrange calls and map by tokens
            for c in arrange_calls:
                for t in c.tokens:
                    parsed_arrange_by_token.setdefault(t, []).append(c)

        # For every tagged position id, update markers on runtime sprites
        # If token found in parsed_by_token -> mark yellow (changed), else if previous markers pointed
        # to one of the changed files but no longer present -> mark red
        # For assignment tokens
        for token, sprites in list(parsed_assign_by_token.items()):
            for sprite in get_sprites_for(token):
                markers = []
                for a in parsed_assign_by_token.get(token, []):
                    markers.append({"file": a.file, "lineno": a.lineno, "attr": a.attr, "status": "yellow"})
                sprite._source_markers = markers

        # For arrange call tokens, add an 'arrange' type marker
        for token, calls in list(parsed_arrange_by_token.items()):
            for sprite in get_sprites_for(token):
                # Initialize _source_markers if missing, then append
                if not isinstance(sprite, SpriteWithSourceMarkers):
                    sprite._source_markers = []  # type: ignore[attr-defined]
                markers = sprite._source_markers  # type: ignore[attr-defined]
                for c in parsed_arrange_by_token.get(token, []):
                    markers.append(
                        {"file": c.file, "lineno": c.lineno, "type": "arrange", "kwargs": c.kwargs, "status": "yellow"}
                    )
                sprite._source_markers = markers  # type: ignore[attr-defined]

    def get_override_inspector_for_sprite(self, sprite: object):
        """Return an ArrangeOverrideInspector for the first arrange marker on `sprite`.

        Returns None if sprite has no arrange markers.
        """
        try:
            from arcadeactions.dev.override_inspector import ArrangeOverrideInspector
        except Exception:
            return None

        if not isinstance(sprite, SpriteWithSourceMarkers):
            return None
        existing = sprite._source_markers
        for m in existing:
            if self._marker_points_to_arrange_call(m):
                return ArrangeOverrideInspector(m.get("file"), m.get("lineno"))
        return None

    @staticmethod
    def _marker_points_to_arrange_call(marker: dict) -> bool:
        if marker.get("type") == "arrange":
            return True
        file_path = marker.get("file")
        lineno = marker.get("lineno")
        if not file_path or lineno is None:
            return False
        try:
            lineno_int = int(lineno)
        except (TypeError, ValueError):
            return False
        if lineno_int < 1:
            return False
        try:
            lines = Path(file_path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return False
        if lineno_int > len(lines):
            return False
        return "arrange_grid" in lines[lineno_int - 1]

    def sprite_has_arrange_marker(self, sprite: object) -> bool:
        if not isinstance(sprite, SpriteWithSourceMarkers):
            return False
        for marker in sprite._source_markers:
            if self._marker_points_to_arrange_call(marker):
                return True
        return False

    @staticmethod
    def _arrange_marker_key(marker: dict) -> tuple[str, int] | None:
        file_path = marker.get("file")
        lineno = marker.get("lineno")
        if not file_path or lineno is None:
            return None
        try:
            return (str(file_path), int(lineno))
        except (TypeError, ValueError):
            return None

    def _first_arrange_marker(self, sprite: object) -> dict | None:
        if not isinstance(sprite, SpriteWithSourceMarkers):
            return None
        for marker in sprite._source_markers:
            if self._marker_points_to_arrange_call(marker):
                return marker
        return None

    def _arrange_group_for_sprite(self, sprite: object) -> list[arcade.Sprite]:
        marker = self._first_arrange_marker(sprite)
        if marker is None:
            if isinstance(sprite, arcade.Sprite):
                return [sprite]
            return []
        key = self._arrange_marker_key(marker)
        if key is None:
            if isinstance(sprite, arcade.Sprite):
                return [sprite]
            return []
        group: list[arcade.Sprite] = []
        for candidate in self.scene_sprites:
            if not isinstance(candidate, SpriteWithSourceMarkers):
                continue
            for candidate_marker in candidate._source_markers:
                if not self._marker_points_to_arrange_call(candidate_marker):
                    continue
                if self._arrange_marker_key(candidate_marker) == key:
                    group.append(candidate)
                    break
        return group

    def open_overrides_panel_for_sprite(self, sprite: object) -> bool:
        """Open the overrides panel for the given sprite (returns True if opened)."""
        return self.overrides_panel.open(sprite)

    def open_overrides_editor_for_sprite(self, sprite: object) -> bool:
        """Open arrange-grid settings editor inside the DevShell inspector panel."""
        marker = self._first_arrange_marker(sprite)
        if marker is None:
            return False
        marker_key = self._arrange_marker_key(marker)
        if marker_key is None:
            return False

        file_path, lineno = marker_key
        editor = ArrangeGridEditor(file_path, lineno)
        group = self._arrange_group_for_sprite(sprite)
        self.selection_manager.clear_selection()
        self.selection_manager._selected.update(group)
        self._sync_property_inspector_selection()

        marker_template = dict(marker)

        def _apply_layout(kwargs: dict[str, float | int]) -> None:
            nonlocal group
            group = self._apply_arrange_layout_to_group_live(group, kwargs, marker_template=marker_template)

        if self._devshell_property_inspector_panel is None:
            return False
        panel = self._devshell_property_inspector_panel
        panel.show_arrange_mode(editor, on_apply_layout=_apply_layout)
        panel.set_visible(True)
        self._sync_devshell_panel_order()
        if self.devshell_coordinator is not None:
            self.devshell_coordinator.set_active_panel("property_inspector")
        # No in-canvas override panel in arrange settings workflow.
        self.overrides_panel.visible = False
        return True

    def toggle_overrides_panel_for_sprite(self, sprite: object | None = None) -> bool:
        """Toggle the overrides panel. If sprite provided, open for that sprite."""
        return self.overrides_panel.toggle(sprite)

    @staticmethod
    def _apply_arrange_layout_to_group(sprites: list[arcade.Sprite], kwargs: dict[str, float | int]) -> None:
        rows = int(kwargs["rows"])
        cols = int(kwargs["cols"])
        start_x = float(kwargs["start_x"])
        start_y = float(kwargs["start_y"])
        spacing_x = float(kwargs["spacing_x"])
        spacing_y = float(kwargs["spacing_y"])
        if rows <= 0 or cols <= 0:
            return
        for index, sprite in enumerate(sprites):
            row = index // cols
            col = index % cols
            sprite.center_x = start_x + col * spacing_x
            sprite.center_y = start_y + row * spacing_y

    def _apply_arrange_layout_to_group_live(
        self,
        sprites: list[arcade.Sprite],
        kwargs: dict[str, float | int],
        *,
        marker_template: dict[str, Any],
    ) -> list[arcade.Sprite]:
        rows = int(kwargs["rows"])
        cols = int(kwargs["cols"])
        if rows <= 0 or cols <= 0:
            return list(sprites)

        target_count = rows * cols
        updated = list(sprites)
        current_count = len(updated)
        if target_count > current_count and current_count > 0:
            template = updated[-1]
            for _ in range(target_count - current_count):
                clone = self._clone_arrange_sprite(template, marker_template)
                self.scene_sprites.append(clone)
                updated.append(clone)
        elif target_count < current_count:
            removed = updated[target_count:]
            for sprite in removed:
                self.selection_manager._selected.discard(sprite)
                if sprite in self.scene_sprites:
                    self.scene_sprites.remove(sprite)
            updated = updated[:target_count]

        self._apply_arrange_layout_to_group(updated, kwargs)
        self.selection_manager.clear_selection()
        self.selection_manager._selected.update(updated)
        self._sync_property_inspector_selection()
        return updated

    @staticmethod
    def _clone_arrange_sprite(template: arcade.Sprite, marker_template: dict[str, Any]) -> arcade.Sprite:
        clone = arcade.Sprite(template.texture)
        clone.scale = template.scale
        clone.center_x = float(template.center_x)
        clone.center_y = float(template.center_y)
        clone.angle = float(template.angle)
        clone.alpha = int(template.alpha)
        clone.color = template.color
        clone.visible = bool(template.visible)
        clone._source_markers = [dict(marker_template)]
        return clone


# Global DevVisualizer instance
_global_dev_visualizer: DevVisualizer | None = None


def enable_dev_visualizer(
    scene_sprites: arcade.SpriteList | None = None,
    window: arcade.Window | None = None,
    auto_attach: bool = True,
) -> DevVisualizer:
    """
    Enable DevVisualizer with optional auto-attach to window.

    Args:
        scene_sprites: SpriteList for editable scene (created if None)
        window: Arcade window (auto-detected if None)
        auto_attach: Automatically attach to window (default: True)

    Returns:
        DevVisualizer instance
    """
    global _global_dev_visualizer

    if _global_dev_visualizer is not None:
        dev_viz = _global_dev_visualizer
        if scene_sprites is not None and dev_viz.scene_sprites is not scene_sprites:
            dev_viz.reset_scene(scene_sprites)
        if window is not None and dev_viz.window is not window:
            if dev_viz._attached:
                dev_viz.detach_from_window()
            dev_viz.window = window
        if auto_attach and not dev_viz._attached:
            attached = dev_viz.attach_to_window(window)
            if not attached:
                _install_window_attach_hook()
                _install_update_all_attach_hook()
        return dev_viz

    _global_dev_visualizer = DevVisualizer(scene_sprites=scene_sprites, window=window)

    if auto_attach:
        attached = _global_dev_visualizer.attach_to_window(window)
        if not attached:
            _install_window_attach_hook()
            _install_update_all_attach_hook()

    return _global_dev_visualizer


def get_dev_visualizer() -> DevVisualizer | None:
    """
    Get the global DevVisualizer instance.

    Returns:
        DevVisualizer instance if enabled, None otherwise
    """
    return _global_dev_visualizer


def auto_enable_dev_visualizer_from_env() -> DevVisualizer | None:
    """
    Auto-enable DevVisualizer if environment variable is set.

    Checks for environment variables (in order of preference):
    - ARCADEACTIONS_DEVVIZ=1 (explicit DevVisualizer)
    - ARCADEACTIONS_DEV=1 (general dev mode - includes DevVisualizer)

    Returns:
        DevVisualizer instance if enabled, None otherwise

    Note: If window doesn't exist yet, DevVisualizer is created but not attached.
    It will attach automatically when window becomes available (if auto_attach=True).
    When enabled via environment variable, DevVisualizer is automatically shown.

    This function is idempotent - if DevVisualizer is already enabled, returns the
    existing instance instead of creating a new one.
    """
    global _global_dev_visualizer

    # If already enabled, return existing instance (idempotent)
    if _global_dev_visualizer is not None:
        return _global_dev_visualizer

    # Check multiple environment variable options
    env_vars = [
        "ARCADEACTIONS_DEVVIZ",  # Explicit DevVisualizer
        "ARCADEACTIONS_DEV",  # General dev mode
    ]

    for env_var in env_vars:
        if os.environ.get(env_var) == "1":
            # Try to get window, but don't fail if it doesn't exist yet
            try:
                window = arcade.get_window()
            except RuntimeError:
                window = None

            # Always request auto_attach so we install the window hook when the
            # window doesn't exist yet (common during import-time env auto-enable).
            dev_viz = enable_dev_visualizer(window=window, auto_attach=True)
            # Auto-show when enabled via environment variable (user explicitly wants editor mode)
            dev_viz.show()
            return dev_viz

    return None
