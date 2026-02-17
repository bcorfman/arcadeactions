from __future__ import annotations

from arcadeactions.dev.override_inspector import ArrangeOverrideInspector
from arcadeactions.dev.visualizer_protocols import SpriteWithSourceMarkers


class OverridesPanel:
    """Non-graphical panel for listing and editing arrange_grid per-cell overrides.

    This serves as the UI backend: a minimal panel used by DevVisualizer that can be
    wired to rendering code later. All operations delegate to ArrangeOverrideInspector.
    """

    def __init__(self, dev_visualizer) -> None:
        self.dev_visualizer = dev_visualizer
        self.visible: bool = False
        self.sprite = None
        self.inspector: ArrangeOverrideInspector | None = None

        # UI state
        self._selected_index: int | None = None

        # Inline edit state
        self.editing: bool = False
        self._input_buffer: str = ""
        self._editing_field: str = "x"  # 'x' or 'y'
        self._last_error: str = ""
        self._grid_rows: int = 0
        self._grid_cols: int = 0
        self._selected_cell_index: int = 0

    @staticmethod
    def _parse_grid_dimension(value: object, default: int) -> int:
        if value is None:
            return default
        try:
            parsed = int(str(value).strip())
        except (TypeError, ValueError):
            return default
        return max(1, parsed)

    def start_edit(self, field: str = "x") -> None:
        """Begin inline edit for the selected override. Field must be 'x' or 'y'."""
        if field not in ("x", "y"):
            raise ValueError("field must be 'x' or 'y'")
        if self._selected_index is None:
            cells = self.list_cells()
            if not cells:
                return
            self._selected_index = 0
            self._selected_cell_index = 0
        sel = self.get_selected_cell()
        if not sel:
            return
        self._editing_field = field
        # Initialize buffer empty so user can type new values
        self._input_buffer = ""
        self.editing = True

    def handle_input_char(self, ch: str) -> None:
        """Handle a single character of input while editing. Supports digits, comma, minus, and backspace ("\b")."""
        if not self.editing:
            return
        if ch == "\b":
            self._input_buffer = self._input_buffer[:-1]
            return
        # Only allow digits, comma, minus
        if ch.isdigit() or ch in (",", "-"):
            self._input_buffer += ch

    def commit_edit(self) -> None:
        """Parse the input buffer and apply the override (both x,y expected)."""
        if not self.editing:
            return
        try:
            parts = [p.strip() for p in self._input_buffer.split(",", 1)]
            if len(parts) == 1:
                # If only one value provided, treat as x and keep existing y
                x = int(parts[0])
                sel = self.get_selected()
                y = sel.get("y") or 0
            else:
                x = int(parts[0]) if parts[0] != "" else 0
                y = int(parts[1]) if parts[1] != "" else 0
            sel = self.get_selected()
            if sel:
                row = sel.get("row")
                col = sel.get("col")
                self.set_override(row, col, x, y)
        except Exception:
            # Ignore parse errors and cancel
            pass
        finally:
            self.editing = False
            self._input_buffer = ""

    def cancel_edit(self) -> None:
        self.editing = False
        self._input_buffer = ""

    def select_next(self) -> None:
        self.select_cell_next()

    def select_prev(self) -> None:
        self.select_cell_prev()

    def get_selected(self) -> dict | None:
        return self.get_selected_cell()

    def list_cells(self) -> list[dict]:
        overrides = self.list_overrides()
        if self._grid_rows <= 0 or self._grid_cols <= 0:
            return [
                {
                    "row": int(entry.get("row") or 0),
                    "col": int(entry.get("col") or 0),
                    "x": int(entry.get("x") or 0),
                    "y": int(entry.get("y") or 0),
                    "overridden": True,
                }
                for entry in overrides
            ]

        by_cell: dict[tuple[int, int], dict] = {}
        for entry in overrides:
            row = int(entry.get("row") or 0)
            col = int(entry.get("col") or 0)
            by_cell[(row, col)] = entry

        cells: list[dict] = []
        for row in range(self._grid_rows):
            for col in range(self._grid_cols):
                existing = by_cell.get((row, col))
                if existing is None:
                    cells.append({"row": row, "col": col, "x": 0, "y": 0, "overridden": False})
                else:
                    cells.append(
                        {
                            "row": row,
                            "col": col,
                            "x": int(existing.get("x") or 0),
                            "y": int(existing.get("y") or 0),
                            "overridden": True,
                        }
                    )
        return cells

    def get_selected_cell(self) -> dict | None:
        cells = self.list_cells()
        if not cells:
            return None
        if self._selected_index is None:
            return None
        self._selected_cell_index = self._selected_index
        if self._selected_cell_index < 0 or self._selected_cell_index >= len(cells):
            return None
        self._selected_index = self._selected_cell_index
        return cells[self._selected_cell_index]

    def select_cell_next(self) -> None:
        cells = self.list_cells()
        if not cells:
            self._selected_cell_index = 0
            self._selected_index = None
            return
        if self._selected_index is None:
            self._selected_index = 0
            self._selected_cell_index = 0
            return
        self._selected_cell_index = self._selected_index
        self._selected_cell_index = min(len(cells) - 1, self._selected_cell_index + 1)
        self._selected_index = self._selected_cell_index

    def select_cell_prev(self) -> None:
        cells = self.list_cells()
        if not cells:
            self._selected_cell_index = 0
            self._selected_index = None
            return
        if self._selected_index is None:
            self._selected_index = 0
            self._selected_cell_index = 0
            return
        self._selected_cell_index = self._selected_index
        self._selected_cell_index = max(0, self._selected_cell_index - 1)
        self._selected_index = self._selected_cell_index

    def increment_selected(self, dx: int, dy: int) -> None:
        sel = self.get_selected_cell()
        if not sel:
            return
        row = sel.get("row")
        col = sel.get("col")
        x = sel.get("x") or 0
        y = sel.get("y") or 0
        self.set_override(row, col, x + dx, y + dy)

    def draw(self) -> None:
        """Draw a simple textual representation of the overrides panel."""
        if not self.visible or not self.inspector:
            return
        win = self.dev_visualizer.window
        if not win:
            return
        w = getattr(win, "width", 800)
        h = getattr(win, "height", 600)

        # Draw a translucent background at top-right
        panel_w = 260
        panel_h = 210
        x = w - panel_w / 2 - 8
        y = h - panel_h / 2 - 40
        import arcade

        panel_left = x - panel_w / 2
        panel_bottom = y - panel_h / 2
        panel_color = (34, 40, 42, 230)
        try:
            arcade.draw_lbwh_rectangle_filled(panel_left, panel_bottom, panel_w, panel_h, panel_color)
        except Exception:
            arcade.draw_rect_filled(arcade.rect.XYWH(x, y, panel_w, panel_h), panel_color)
        title = "Overrides"
        arcade.draw_text(title, x - panel_w / 2 + 8, y + panel_h / 2 - 20, arcade.color.WHITE, 14)

        cells = self.list_cells()
        for i, o in enumerate(cells[:8]):
            # Render x/y and highlight editing field if applicable
            x_val = o.get("x")
            y_val = o.get("y")
            if self.editing and self._selected_cell_index == i:
                x_s = f"[{x_val}]" if self._editing_field == "x" else f"x{x_val}"
                y_s = f"[{y_val}]" if self._editing_field == "y" else f"y{y_val}"
            else:
                x_s = f"x{x_val}"
                y_s = f"y{y_val}"
            marker = "*" if o.get("overridden") else "-"
            text = f"{i}: r{o.get('row')} c{o.get('col')} {x_s} {y_s} {marker}"
            color = arcade.color.YELLOW if self._selected_cell_index == i else arcade.color.WHITE
            arcade.draw_text(text, x - panel_w / 2 + 8, y + panel_h / 2 - 40 - i * 16, color, 12)

        # Draw input buffer if editing
        if self.editing:
            buf_text = self._input_buffer or ""
            arcade.draw_text(
                f"Edit: {buf_text}", x - panel_w / 2 + 8, y - panel_h / 2 + 20, arcade.color.LIGHT_GRAY, 12
            )
        if self._last_error:
            arcade.draw_text(self._last_error, x - panel_w / 2 + 8, y - panel_h / 2 + 6, arcade.color.RED, 10)

    def handle_key(self, key: str) -> None:
        """Handle simple key commands from DevVisualizer.

        Currently supports Ctrl+Z for undoing the last inspector change.
        """
        if key == "CTRL+Z":
            if self.inspector and self.inspector.undo():
                # Keep both compatibility and cell selection state consistent.
                self._selected_cell_index = max(0, self._selected_cell_index)
                self._selected_index = self._selected_cell_index
            return
        if key == "CTRL+SHIFT+Z":
            self._last_error = "Redo is not available for arrange overrides yet."
            return

    def open(self, sprite: object) -> bool:
        """Open the panel for the given sprite's arrange call. Returns True if opened."""
        inspector = self.dev_visualizer.get_override_inspector_for_sprite(sprite)
        if not inspector:
            return False
        rows = 1
        cols = 1
        if isinstance(sprite, SpriteWithSourceMarkers):
            for marker in sprite._source_markers:
                if not self.dev_visualizer._marker_points_to_arrange_call(marker):
                    continue
                kwargs = marker.get("kwargs")
                if isinstance(kwargs, dict):
                    rows = self._parse_grid_dimension(kwargs.get("rows"), rows)
                    cols = self._parse_grid_dimension(kwargs.get("cols"), cols)
                break
        if rows <= 0 or cols <= 0:
            try:
                existing = inspector.list_overrides()
            except Exception:
                existing = []
            for entry in existing:
                rows = max(rows, int(entry.get("row") or 0) + 1)
                cols = max(cols, int(entry.get("col") or 0) + 1)
            if rows <= 0:
                rows = 1
            if cols <= 0:
                cols = 1
        self.sprite = sprite
        self.inspector = inspector
        self._grid_rows = rows
        self._grid_cols = cols
        self._selected_cell_index = 0
        self._selected_index = 0
        self.visible = True
        return True

    def close(self) -> None:
        self.visible = False
        self.sprite = None
        self.inspector = None
        self._selected_cell_index = 0
        self._selected_index = None

    def toggle(self, sprite: object | None = None) -> bool:
        """Toggle panel visibility. If sprite is provided, open for that sprite."""
        if self.visible:
            self.close()
            return False
        if sprite is None and self.sprite is not None:
            sprite = self.sprite
        if sprite is None:
            return False
        return self.open(sprite)

    def is_open(self) -> bool:
        return self.visible

    # Delegate methods
    def list_overrides(self) -> list[dict]:
        if not self.inspector:
            return []
        try:
            overrides = self.inspector.list_overrides()
        except Exception as exc:
            self._last_error = f"Overrides error: {exc}"
            return []
        self._last_error = ""
        return overrides

    def set_override(self, row: int, col: int, x: int, y: int):
        if not self.inspector:
            raise RuntimeError("OverridesPanel is not open")
        return self.inspector.set_override(row, col, x, y)

    def remove_override(self, row: int, col: int):
        if not self.inspector:
            raise RuntimeError("OverridesPanel is not open")
        return self.inspector.remove_override(row, col)
