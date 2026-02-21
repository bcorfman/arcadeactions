"""Layout helpers for one-window DevShell stage and rails."""

from __future__ import annotations


class DevShellRect:
    """Simple immutable rectangle container for DevShell regions."""

    __slots__ = ("x", "y", "width", "height")

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)


class DevShellRegions:
    """Computed stage + rail rectangles for a window size."""

    __slots__ = ("stage", "left", "right", "top", "bottom")

    def __init__(
        self,
        *,
        stage: DevShellRect,
        left: DevShellRect,
        right: DevShellRect,
        top: DevShellRect,
        bottom: DevShellRect,
    ) -> None:
        self.stage = stage
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom


class DevShellLayout:
    """Computes window-size constraints and stage/rail regions."""

    def __init__(
        self,
        *,
        stage_width: int,
        stage_height: int,
        left_rail_width: int,
        right_rail_width: int,
        top_rail_height: int,
        bottom_rail_height: int,
    ) -> None:
        self._stage_width = int(stage_width)
        self._stage_height = int(stage_height)
        self._left_rail_width = int(left_rail_width)
        self._right_rail_width = int(right_rail_width)
        self._top_rail_height = int(top_rail_height)
        self._bottom_rail_height = int(bottom_rail_height)

    def min_window_size(self) -> tuple[int, int]:
        """Return minimum width/height preserving stage+rail contract."""
        width = self._stage_width + self._left_rail_width + self._right_rail_width
        height = self._stage_height + self._top_rail_height + self._bottom_rail_height
        return (width, height)

    def clamp_window_size(self, width: int, height: int) -> tuple[int, int]:
        """Clamp requested size to minimum DevShell contract size."""
        min_width, min_height = self.min_window_size()
        return (max(int(width), min_width), max(int(height), min_height))

    def compute_regions(self, *, window_width: int, window_height: int, preview_clean: bool) -> DevShellRegions:
        """Compute stage + rail rectangles for given window dimensions."""
        width, height = self.clamp_window_size(window_width, window_height)

        if bool(preview_clean):
            stage = DevShellRect(0, 0, width, height)
            zero = DevShellRect(0, 0, 0, 0)
            return DevShellRegions(stage=stage, left=zero, right=zero, top=zero, bottom=zero)

        left_width = self._left_rail_width
        right_width = self._right_rail_width
        top_height = self._top_rail_height
        bottom_height = self._bottom_rail_height

        stage_x = left_width
        stage_y = bottom_height
        stage_width = width - left_width - right_width
        stage_height = height - top_height - bottom_height

        left = DevShellRect(0, 0, left_width, height)
        right = DevShellRect(width - right_width, 0, right_width, height)
        top = DevShellRect(left_width, height - top_height, stage_width, top_height)
        bottom = DevShellRect(left_width, 0, stage_width, bottom_height)
        stage = DevShellRect(stage_x, stage_y, stage_width, stage_height)
        return DevShellRegions(stage=stage, left=left, right=right, top=top, bottom=bottom)
