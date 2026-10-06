"""
Sprite formation and arrangement functions.

This module provides functions for arranging sprites in various geometric patterns
like lines, grids, circles, V-formations, and diamonds. These functions can either
arrange existing sprites or create new ones using a sprite factory.
"""

import math
from collections.abc import Callable
from typing import Any

import arcade


def _default_factory(texture: str = ":resources:images/items/star.png", scale: float = 1.0):
    """Return a lambda that creates a sprite with the given texture and scale."""
    return lambda: arcade.Sprite(texture, scale=scale)


def _ensure_sprite_list(sprites) -> arcade.SpriteList:
    """Return sprites as an arcade.SpriteList."""
    try:
        sprites.draw
        return sprites
    except AttributeError:
        # A converted list may only be used for formation calculations. Defer
        # GPU and atlas allocation until Arcade actually draws the list.
        sprite_list = arcade.SpriteList(lazy=True)
        for sprite in sprites:
            sprite_list.append(sprite)
        return sprite_list


def arrange_line(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    start_x: float = 0,
    start_y: float = 0,
    spacing: float = 50.0,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a horizontal line.

    Exactly one of *sprites* or *count* must be provided. If *sprites* is given,
    it is arranged in-place. If *count* is given, a new :class:`arcade.SpriteList`
    is created with sprites produced by *sprite_factory* (defaults to a simple star sprite).

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        start_x: X coordinate of the first sprite
        start_y: Y coordinate for all sprites in the line
        spacing: Distance between adjacent sprites
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Arrange existing sprites (zero-allocation)
        pooled_sprites = pool.acquire(5)
        arrange_line(pooled_sprites, start_x=100, start_y=200, spacing=60)

        # Create new sprites in a line
        line = arrange_line(count=5, start_x=0, start_y=300, spacing=50)

        # Create hidden sprites for formation entry
        hidden_line = arrange_line(count=5, start_x=200, start_y=400, visible=False)
    """
    # Validate exactly one of sprites or count is provided
    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")

        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    # Arrange positions
    for i, sprite in enumerate(sprites):
        sprite.center_x = start_x + i * spacing
        sprite.center_y = start_y
        sprite.visible = visible  # Ensure visibility is set

    return sprites


def arrange_grid(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    rows: int = 5,
    cols: int = 10,
    start_x: float = 100,
    start_y: float = 500,
    spacing_x: float = 60.0,
    spacing_y: float = 50.0,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a rectangular grid formation.

    If *sprites* is provided, they are arranged in-place and must match ``rows × cols``.
    If *sprites* is **None**, a new :class:`arcade.SpriteList` with ``rows × cols``
    sprites is created using *sprite_factory* (defaults to a star sprite).

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        rows: Number of rows in the grid
        cols: Number of columns in the grid
        start_x: X coordinate of the top-left sprite
        start_y: Y coordinate of the top-left sprite
        spacing_x: Horizontal distance between adjacent sprites
        spacing_y: Vertical distance between adjacent rows
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Arrange pooled sprites in a grid (zero-allocation)
        pooled_sprites = pool.acquire(15)  # 3*5 sprites
        arrange_grid(pooled_sprites, rows=3, cols=5, start_x=200, start_y=400)

        # Create a 3x5 grid of new sprites
        stars = arrange_grid(rows=3, cols=5, start_x=200, start_y=400)

        # Create hidden grid for formation entry
        hidden_grid = arrange_grid(rows=4, cols=10, start_x=200, start_y=400, visible=False)
    """
    if sprites is None:
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(rows * cols):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

        # Validate sprite count matches grid dimensions
        expected_count = rows * cols
        if len(sprites) != expected_count:
            raise ValueError(f"sprite count ({len(sprites)}) does not match rows * cols ({expected_count})")

    for i, sprite in enumerate(sprites):
        row = i // cols
        col = i % cols
        sprite.center_x = start_x + col * spacing_x
        sprite.center_y = start_y + row * spacing_y
        sprite.visible = visible  # Ensure visibility is set

    return sprites


def arrange_circle(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    center_x: float = 400,
    center_y: float = 300,
    radius: float = 100.0,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a circular formation.

    Sprites are arranged starting from the top (π/2) and moving clockwise.
    This ensures that increasing Y values move sprites upward, consistent
    with the coordinate system used in other arrangement functions.

    With 4 sprites, they will be placed at:
    - First sprite: top (π/2)
    - Second sprite: right (0)
    - Third sprite: bottom (-π/2)
    - Fourth sprite: left (π)

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        center_x: X coordinate of the circle center
        center_y: Y coordinate of the circle center
        radius: Radius of the circle
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create sprites in a circle
        circle_formation = arrange_circle(count=8, center_x=400, center_y=300, radius=120)

        # Arrange existing sprites in a circle
        arrange_circle(existing_sprites, center_x=200, center_y=200, radius=80)

        # Create hidden circle for formation entry
        hidden_circle = arrange_circle(count=8, center_x=400, center_y=300, radius=100, visible=False)
    """
    # Validate exactly one of sprites or count is provided
    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    count = len(sprites)
    if count == 0:
        return sprites

    angle_step = 2 * math.pi / count
    for i, sprite in enumerate(sprites):
        # Start at π/2 (top) and go clockwise (negative angle)
        # Subtract π/2 to start at the top instead of the right
        angle = math.pi / 2 - i * angle_step
        sprite.center_x = center_x + math.cos(angle) * radius
        sprite.center_y = center_y + math.sin(angle) * radius
        sprite.visible = visible  # Ensure visibility is set

    return sprites


def arrange_v_formation(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    apex_x: float = 400,
    apex_y: float = 500,
    spacing: float = 50.0,
    direction: str = "up",
    rotate_with_direction: bool = False,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a V or wedge formation.

    The formation grows from the apex in the specified direction, with sprites placed
    in alternating left-right pattern. The V can point up, down, left, or right.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        apex_x: X coordinate of the V formation apex (tip)
        apex_y: Y coordinate of the V formation apex (tip)
        spacing: Distance between adjacent sprites along the V arms
        direction: Direction the V points ("up", "down", "left", "right")
        rotate_with_direction: Whether to rotate sprites to face the direction (default: False)
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create a V formation pointing up (default)
        v_formation = arrange_v_formation(count=7, apex_x=400, apex_y=100, spacing=60)

        # Create a V formation pointing down
        down_v = arrange_v_formation(count=7, apex_x=400, apex_y=500, spacing=60, direction="down")

        # Create a V formation pointing left with sprite rotation
        left_v = arrange_v_formation(
            count=7, apex_x=100, apex_y=300, spacing=60, direction="left", rotate_with_direction=True
        )

        # Arrange existing sprites in V formation pointing right
        arrange_v_formation(flying_birds, direction="right", spacing=40)
    """
    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    count = len(sprites)
    if count == 0:
        return sprites

    # Validate direction
    _validate_v_direction(direction)

    # Define V angle (45 degrees for a nice V shape)
    v_angle = 45.0
    angle_rad = math.radians(v_angle)

    # Place the first sprite at the apex
    sprites[0].center_x = apex_x
    sprites[0].center_y = apex_y
    sprites[0].visible = visible

    # Set rotation for apex sprite if needed
    if rotate_with_direction:
        sprites[0].angle = _direction_base_angle(direction)

    for i in range(1, count):
        side = 1 if i % 2 == 1 else -1
        distance = (i + 1) // 2 * spacing

        # Calculate base offsets for V shape
        base_offset_x = side * math.cos(angle_rad) * distance
        base_offset_y = math.sin(angle_rad) * distance

        # Apply direction transformation
        offset_x, offset_y = _compute_v_offsets(direction, base_offset_x, base_offset_y)

        sprites[i].center_x = apex_x + offset_x
        sprites[i].center_y = apex_y + offset_y
        sprites[i].visible = visible

        # Set rotation for wing sprites if needed
        if rotate_with_direction:
            sprite_angle = _direction_base_angle(direction)

            # Add slight angle variation for wing sprites to face outward
            if side == 1:  # Right wing
                sprite_angle += v_angle
            else:  # Left wing
                sprite_angle -= v_angle

            sprites[i].angle = sprite_angle

    return sprites


def _validate_v_direction(direction: str) -> None:
    valid_directions = ["up", "down", "left", "right"]
    if direction not in valid_directions:
        raise ValueError(f"direction must be one of {valid_directions}, got '{direction}'")


def _compute_v_offsets(direction: str, base_offset_x: float, base_offset_y: float) -> tuple[float, float]:
    if direction == "up":
        return base_offset_x, base_offset_y
    if direction == "down":
        return base_offset_x, -base_offset_y
    if direction == "left":
        return -base_offset_y, base_offset_x
    return base_offset_y, base_offset_x


def _direction_base_angle(direction: str) -> float:
    rotation_map = {"up": 0, "down": 180, "left": 90, "right": 270}
    return rotation_map[direction]


def arrange_diamond(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    center_x: float = 400,
    center_y: float = 300,
    spacing: float = 50.0,
    include_center: bool = True,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a diamond formation.

    Sprites are arranged in concentric diamond-shaped layers around a center point.
    The formation can optionally include a center sprite, then places sprites in
    diamond-shaped rings at increasing distances. Each layer forms a diamond pattern
    with sprites positioned using Manhattan distance.

    The diamond formation grows outward in layers:
    - Layer 0: 1 sprite at center (if include_center=True)
    - Layer 1: 4 sprites forming a small diamond
    - Layer 2: 8 sprites forming a larger diamond
    - Layer 3: 12 sprites, etc.

    Total sprites for n layers:
    - With center: 1 + 4 + 8 + 12 + ... = 1 + 2*n*(n+1) for n ≥ 1
    - Without center: 4 + 8 + 12 + ... = 2*n*(n+1) for n ≥ 1

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        center_x: X coordinate of the diamond center
        center_y: Y coordinate of the diamond center
        spacing: Distance between adjacent layer rings
        include_center: Whether to place a sprite at the center (default: True)
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create a solid diamond formation with 13 sprites (1 + 4 + 8)
        diamond = arrange_diamond(count=13, center_x=400, center_y=300, spacing=60)

        # Create a hollow diamond formation with 12 sprites (4 + 8)
        hollow_diamond = arrange_diamond(
            count=12, center_x=400, center_y=300, spacing=60, include_center=False
        )

        # Arrange existing sprites in diamond formation
        arrange_diamond(existing_sprites, center_x=200, center_y=200, spacing=40)

        # Create hidden diamond for formation entry
        hidden_diamond = arrange_diamond(count=13, center_x=400, center_y=300, spacing=60, visible=False)

        # Diamond formations work well for:
        # - Enemy attack patterns (solid for boss, hollow for minions)
        # - Defensive formations (hollow allows protected units inside)
        # - Crystal/gem displays (hollow showcases central item)
        # - Special effect arrangements (hollow creates visual focus)
    """
    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    count = len(sprites)
    if count == 0:
        return sprites

    # Place sprites starting from center (if included) and working outward in diamond layers
    sprite_index = 0
    layer = 0 if include_center else 1

    while sprite_index < count:
        if layer == 0 and include_center:
            # Center sprite
            if sprite_index < count:
                sprites[sprite_index].center_x = center_x
                sprites[sprite_index].center_y = center_y
                sprites[sprite_index].visible = visible
                sprite_index += 1
        else:
            # Diamond layer at distance layer * spacing from center
            # Each layer has 4 * layer sprites positioned around the diamond perimeter
            layer_distance = layer * spacing
            sprites_in_layer = min(4 * layer, count - sprite_index)

            # Place sprites evenly around the diamond perimeter
            # Diamond has 4 cardinal directions, with sprites between them
            for i in range(sprites_in_layer):
                if sprite_index >= count:
                    break

                # Calculate the angle for this sprite position
                # Distribute sprites evenly around the full perimeter
                angle = i * 2 * math.pi / (4 * layer)

                # Convert angle to diamond coordinates
                # Use the "taxicab" or "Manhattan" distance approach for diamond shape
                # The diamond has vertices at (±d, 0) and (0, ±d) where d = layer_distance

                # Convert polar coordinates to diamond coordinates
                # For a diamond, we want |x| + |y| = layer_distance (Manhattan distance)
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)

                # Normalize to diamond shape by scaling to Manhattan distance
                # The diamond boundary satisfies |x| + |y| = r
                # Given direction (cos_a, sin_a), find the point on diamond boundary
                if abs(cos_a) + abs(sin_a) > 0:  # Avoid division by zero
                    scale = layer_distance / (abs(cos_a) + abs(sin_a))
                    offset_x = cos_a * scale
                    offset_y = sin_a * scale
                else:
                    offset_x = layer_distance
                    offset_y = 0

                sprites[sprite_index].center_x = center_x + offset_x
                sprites[sprite_index].center_y = center_y + offset_y
                sprites[sprite_index].visible = visible  # Ensure visibility is set
                sprite_index += 1

        layer += 1

    return sprites


def arrange_triangle(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    apex_x: float = 400,
    apex_y: float = 500,
    row_spacing: float = 50.0,
    lateral_spacing: float = 60.0,
    invert: bool = False,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a triangular formation.

    Sprites are arranged in successive rows (1, 2, 3, ...) forming a triangle.
    The first sprite is placed at the apex, then subsequent rows spread outward.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        apex_x: X coordinate of the triangle apex (tip)
        apex_y: Y coordinate of the triangle apex (tip)
        row_spacing: Vertical distance between rows
        lateral_spacing: Horizontal distance between sprites in same row
        invert: If True, triangle grows upward; if False, grows downward
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create downward triangle with 6 sprites (1+2+3)
        triangle = arrange_triangle(count=6, apex_x=400, apex_y=500, row_spacing=50)

        # Create upward triangle
        up_triangle = arrange_triangle(count=10, apex_x=300, apex_y=200, invert=True)

        # Arrange existing sprites in triangle
        arrange_triangle(existing_sprites, apex_x=200, apex_y=300, lateral_spacing=40)
    """
    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    sprite_index = 0
    row = 0
    total_sprites = len(sprites)

    while sprite_index < total_sprites:
        sprites_in_row = row + 1  # Row 0 has 1 sprite, row 1 has 2, etc.
        sprites_to_place = min(sprites_in_row, total_sprites - sprite_index)

        # Calculate Y position for this row
        y_pos = apex_y + row * row_spacing if invert else apex_y - row * row_spacing

        # Calculate starting X position to center the row
        if sprites_to_place == 1:
            start_x = apex_x
        else:
            total_width = (sprites_to_place - 1) * lateral_spacing
            start_x = apex_x - total_width / 2

        # Place sprites in this row
        for i in range(sprites_to_place):
            if sprite_index >= total_sprites:
                break
            sprites[sprite_index].center_x = start_x + i * lateral_spacing
            sprites[sprite_index].center_y = y_pos
            sprites[sprite_index].visible = visible
            sprite_index += 1

        row += 1

    return sprites


def get_slot_coordinates(
    formation_fn: Callable[..., arcade.SpriteList],
    index: int,
    **kwargs: Any,
) -> tuple[float, float]:
    """Get the coordinates for a sprite at a given index in a formation.

    This helper computes the slot coordinates without actually placing sprites,
    which is useful for breakaway return logic and other formation calculations.

    Args:
        formation_fn: Formation function from this module (e.g., arrange_line, arrange_grid)
        index: Zero-based index of the sprite in the formation
        **kwargs: Parameters passed to formation_fn (must match the function's signature)

    Returns:
        (x, y) coordinates for the sprite at the given index

    Raises:
        ValueError: If formation function is not supported or parameters are invalid
        IndexError: If index is out of bounds for the formation

    Example:
        # Get slot 2 in a line formation
        x, y = get_slot_coordinates(arrange_line, 2, start_x=100, start_y=200, spacing=50, count=5)
        # Returns (200, 200)

        # Get slot 3 in a grid formation
        x, y = get_slot_coordinates(arrange_grid, 3, rows=2, cols=3, start_x=100, start_y=300, spacing_x=50, spacing_y=40)
        # Returns (100, 340)
    """
    fn_name = formation_fn.__name__
    slot_handlers = {
        "arrange_line": _get_line_slot,
        "arrange_grid": _get_grid_slot,
        "arrange_circle": _get_circle_slot,
        "arrange_v_formation": _get_v_slot,
        "arrange_triangle": _get_triangle_slot,
    }
    handler = slot_handlers.get(fn_name)
    if handler is None:
        raise ValueError(f"Unsupported formation function: {fn_name}")
    return handler(index, **kwargs)


def _require_count(name: str, kwargs: dict[str, Any]) -> int:
    count = kwargs.get("count")
    if count is None:
        raise ValueError(f"{name} requires 'count' parameter")
    return count


def _validate_index(index: int, count: int) -> None:
    if index < 0 or index >= count:
        raise IndexError(f"Index {index} out of bounds for count {count}")


def _get_line_slot(index: int, **kwargs: Any) -> tuple[float, float]:
    count = _require_count("arrange_line", kwargs)
    _validate_index(index, count)

    start_x = kwargs.get("start_x", 0)
    start_y = kwargs.get("start_y", 0)
    spacing = kwargs.get("spacing", 50.0)
    return (start_x + index * spacing, start_y)


def _get_grid_slot(index: int, **kwargs: Any) -> tuple[float, float]:
    rows = kwargs.get("rows", 5)
    cols = kwargs.get("cols", 10)
    total_count = rows * cols
    if index < 0 or index >= total_count:
        raise IndexError(f"Index {index} out of bounds for grid {rows}x{cols} (total {total_count})")

    start_x = kwargs.get("start_x", 100)
    start_y = kwargs.get("start_y", 500)
    spacing_x = kwargs.get("spacing_x", 60.0)
    spacing_y = kwargs.get("spacing_y", 50.0)
    row = index // cols
    col = index % cols
    x = start_x + col * spacing_x
    y = start_y + row * spacing_y
    return (x, y)


def _get_circle_slot(index: int, **kwargs: Any) -> tuple[float, float]:
    count = _require_count("arrange_circle", kwargs)
    _validate_index(index, count)

    center_x = kwargs.get("center_x", 400)
    center_y = kwargs.get("center_y", 300)
    radius = kwargs.get("radius", 100.0)
    angle_step = 2 * math.pi / count
    angle = math.pi / 2 - index * angle_step
    x = center_x + math.cos(angle) * radius
    y = center_y + math.sin(angle) * radius
    return (x, y)


def _get_v_slot(index: int, **kwargs: Any) -> tuple[float, float]:
    count = _require_count("arrange_v_formation", kwargs)
    _validate_index(index, count)

    apex_x = kwargs.get("apex_x", 400)
    apex_y = kwargs.get("apex_y", 500)
    spacing = kwargs.get("spacing", 50.0)
    direction = kwargs.get("direction", "up")

    if index == 0:
        return (apex_x, apex_y)

    v_angle = 45.0
    angle_rad = math.radians(v_angle)
    side = 1 if index % 2 == 1 else -1
    distance = (index + 1) // 2 * spacing
    base_offset_x = side * math.cos(angle_rad) * distance
    base_offset_y = math.sin(angle_rad) * distance
    offset_x, offset_y = _compute_v_offsets(direction, base_offset_x, base_offset_y)
    return (apex_x + offset_x, apex_y + offset_y)


def _get_triangle_slot(index: int, **kwargs: Any) -> tuple[float, float]:
    count = _require_count("arrange_triangle", kwargs)
    _validate_index(index, count)

    apex_x = kwargs.get("apex_x", 400)
    apex_y = kwargs.get("apex_y", 500)
    row_spacing = kwargs.get("row_spacing", 50.0)
    lateral_spacing = kwargs.get("lateral_spacing", 60.0)
    invert = kwargs.get("invert", False)

    sprite_index = 0
    row = 0
    while sprite_index < count:
        sprites_in_row = row + 1
        if sprite_index + sprites_in_row > index:
            col = index - sprite_index
            break
        sprite_index += sprites_in_row
        row += 1
    else:
        raise IndexError(f"Index {index} out of bounds for count {count}")

    sprites_to_place = min(sprites_in_row, count - sprite_index)
    y_pos = apex_y + row * row_spacing if invert else apex_y - row * row_spacing

    if sprites_to_place == 1:
        start_x = apex_x
    else:
        total_width = (sprites_to_place - 1) * lateral_spacing
        start_x = apex_x - total_width / 2

    x = start_x + col * lateral_spacing
    y = y_pos
    return (x, y)


def arrange_hexagonal_grid(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    rows: int = 5,
    cols: int = 10,
    start_x: float = 100,
    start_y: float = 500,
    spacing: float = 60.0,
    orientation: str = "pointy",
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a hexagonal grid formation.

    Creates an offset grid where every other row is shifted to create
    a honeycomb-like hexagonal pattern.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        rows: Number of rows in the grid
        cols: Number of columns in the grid
        start_x: X coordinate of the top-left sprite
        start_y: Y coordinate of the top-left sprite
        spacing: Distance between adjacent sprites
        orientation: "pointy" (default) or "flat" for hexagon orientation
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create a 4x6 hexagonal grid
        hex_grid = arrange_hexagonal_grid(rows=4, cols=6, start_x=100, start_y=400)

        # Arrange existing sprites in hexagonal pattern
        arrange_hexagonal_grid(existing_sprites, rows=3, cols=5, spacing=50)
    """
    if sprites is None:
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(rows * cols):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    # Calculate offset and spacing based on orientation
    if orientation == "pointy":
        row_offset_x = spacing / 2
        row_spacing_y = spacing * math.sqrt(3) / 2
    else:  # flat
        row_offset_x = spacing * math.sqrt(3) / 2
        row_spacing_y = spacing / 2

    for i, sprite in enumerate(sprites):
        row = i // cols
        col = i % cols

        # Calculate base position
        x = start_x + col * spacing
        y = start_y + row * row_spacing_y

        # Offset every other row for hexagonal pattern
        if row % 2 == 1:
            x += row_offset_x

        sprite.center_x = x
        sprite.center_y = y
        sprite.visible = visible

    return sprites


def arrange_arc(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    center_x: float = 400,
    center_y: float = 300,
    radius: float = 100.0,
    start_angle: float = 0.0,
    end_angle: float = 180.0,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in an arc formation.

    Sprites are arranged along a circular arc between two angles.
    Angles are in degrees, with 0° pointing right and increasing counterclockwise.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        center_x: X coordinate of the arc center
        center_y: Y coordinate of the arc center
        radius: Radius of the arc
        start_angle: Starting angle in degrees (0° = right)
        end_angle: Ending angle in degrees
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create a semicircle arc
        arc = arrange_arc(count=8, center_x=400, center_y=300, radius=120,
                         start_angle=0, end_angle=180)

        # Create a fan pattern
        fan = arrange_arc(count=5, center_x=200, center_y=200, radius=80,
                         start_angle=45, end_angle=135)
    """
    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    count = len(sprites)
    if count == 0:
        return sprites

    # Validate angle range
    if start_angle >= end_angle:
        raise ValueError("start_angle must be less than end_angle")

    # Convert angles to radians
    start_rad = math.radians(start_angle)
    end_rad = math.radians(end_angle)

    # Calculate angle step
    if count == 1:
        angle_step = 0
        current_angle = (start_rad + end_rad) / 2  # Place single sprite in middle
    else:
        angle_step = (end_rad - start_rad) / (count - 1)
        current_angle = start_rad

    for sprite in sprites:
        sprite.center_x = center_x + math.cos(current_angle) * radius
        sprite.center_y = center_y + math.sin(current_angle) * radius
        sprite.visible = visible
        current_angle += angle_step

    return sprites


def arrange_concentric_rings(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    radii: list[float] | None = None,
    sprites_per_ring: list[int] | None = None,
    center_x: float = 400,
    center_y: float = 300,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in concentric rings formation.

    Creates multiple circular rings at different radii from a center point.
    Each ring can have a different number of sprites.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        radii: List of radii for each ring
        sprites_per_ring: List of sprite counts for each ring
        center_x: X coordinate of the center
        center_y: Y coordinate of the center
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create bull's-eye pattern
        rings = arrange_concentric_rings(
            radii=[50, 100, 150],
            sprites_per_ring=[6, 12, 18],
            center_x=400, center_y=300
        )

        # Arrange existing sprites in rings
        arrange_concentric_rings(
            existing_sprites,
            radii=[40, 80],
            sprites_per_ring=[4, 8],
            center_x=200, center_y=200
        )
    """
    if radii is None:
        radii = [50, 100]
    if sprites_per_ring is None:
        sprites_per_ring = [6, 12]

    # Validate parameters
    if len(radii) != len(sprites_per_ring):
        raise ValueError("radii and sprites_per_ring lists must have the same length")

    total_sprites_needed = sum(sprites_per_ring)

    if sprites is None:
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(total_sprites_needed):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    sprite_index = 0
    for _ring_idx, (radius, sprite_count) in enumerate(zip(radii, sprites_per_ring, strict=False)):
        if sprite_index >= len(sprites):
            break

        # Calculate how many sprites to actually place in this ring
        sprites_to_place = min(sprite_count, len(sprites) - sprite_index)

        if sprites_to_place == 0:
            continue

        # Calculate angle step for even distribution
        angle_step = 2 * math.pi / sprites_to_place

        for i in range(sprites_to_place):
            if sprite_index >= len(sprites):
                break

            angle = i * angle_step
            sprite = sprites[sprite_index]
            sprite.center_x = center_x + math.cos(angle) * radius
            sprite.center_y = center_y + math.sin(angle) * radius
            sprite.visible = visible
            sprite_index += 1

    return sprites


def arrange_cross(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    center_x: float = 400,
    center_y: float = 300,
    arm_length: float = 100.0,
    spacing: float = 50.0,
    include_center: bool = True,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in a cross or plus formation.

    Creates a cross pattern with equal-length arms extending up, down, left, and right
    from a center point. Optionally includes a center sprite.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        center_x: X coordinate of the cross center
        center_y: Y coordinate of the cross center
        arm_length: Length of each arm from center
        spacing: Distance between sprites along arms
        include_center: Whether to place a sprite at the center (default: True)
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create cross with center sprite
        cross = arrange_cross(count=9, center_x=400, center_y=300, arm_length=100)

        # Create hollow cross (no center)
        hollow_cross = arrange_cross(count=8, center_x=200, center_y=200,
                                   arm_length=80, include_center=False)
    """
    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    sprite_index = 0
    total_sprites = len(sprites)

    # Place center sprite if requested
    if include_center and sprite_index < total_sprites:
        sprites[sprite_index].center_x = center_x
        sprites[sprite_index].center_y = center_y
        sprites[sprite_index].visible = visible
        sprite_index += 1

    # Calculate sprites per arm
    remaining_sprites = total_sprites - sprite_index
    sprites_per_arm = remaining_sprites // 4
    extra_sprites = remaining_sprites % 4

    # Define arm directions: right, up, left, down
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    for arm_idx, (dx, dy) in enumerate(directions):
        arm_sprite_count = sprites_per_arm + (1 if arm_idx < extra_sprites else 0)

        for step in range(1, arm_sprite_count + 1):
            if sprite_index >= total_sprites:
                break

            x = center_x + dx * step * spacing
            y = center_y + dy * step * spacing

            sprites[sprite_index].center_x = x
            sprites[sprite_index].center_y = y
            sprites[sprite_index].visible = visible
            sprite_index += 1

    return sprites


def arrange_arrow(
    sprites: arcade.SpriteList | list[arcade.Sprite] | None = None,
    *,
    count: int | None = None,
    tip_x: float = 400,
    tip_y: float = 500,
    rows: int = 3,
    spacing_along: float = 50.0,
    spacing_outward: float = 40.0,
    invert: bool = False,
    sprite_factory: Callable[[], arcade.Sprite] | None = None,
    visible: bool = True,
) -> arcade.SpriteList:
    """Create or arrange sprites in an arrow or spear-head formation.

    Creates an arrow pattern with a tip sprite and symmetric wings extending
    backward and outward from the tip.

    Args:
        sprites: Existing sprites to arrange, or None to create new ones
        count: Number of sprites to create (required if sprites is None)
        tip_x: X coordinate of the arrow tip
        tip_y: Y coordinate of the arrow tip
        rows: Number of rows of wings behind the tip
        spacing_along: Distance between rows along the arrow shaft
        spacing_outward: Distance outward from center for each row of wings
        invert: If True, arrow points upward; if False, points downward
        sprite_factory: Function to create new sprites (if sprites is None)
        visible: Whether sprites should be visible (default: True)

    Returns:
        The arranged sprite list

    Example:
        # Create downward-pointing arrow
        arrow = arrange_arrow(count=7, tip_x=400, tip_y=500, rows=3)

        # Create upward-pointing arrow
        up_arrow = arrange_arrow(count=9, tip_x=300, tip_y=200, rows=4, invert=True)

        # Arrange existing sprites in arrow formation
        arrange_arrow(existing_sprites, tip_x=200, tip_y=300, spacing_along=40)
    """
    # Validate exactly one of sprites or count is provided

    if sprites is not None and count is not None:
        raise ValueError("Cannot specify both 'sprites' and 'count'. Use exactly one.")

    if sprites is None:
        if count is None or count <= 0:
            raise ValueError("When *sprites* is None you must supply a positive *count*.")
        sprite_factory = sprite_factory or _default_factory()
        sprites = arcade.SpriteList()
        for _ in range(count):
            sprite = sprite_factory()
            sprite.visible = visible
            sprites.append(sprite)
    else:
        sprites = _ensure_sprite_list(sprites)

    sprite_index = 0
    total_sprites = len(sprites)

    if total_sprites == 0:
        return sprites

    # Place tip sprite
    sprites[sprite_index].center_x = tip_x
    sprites[sprite_index].center_y = tip_y
    sprites[sprite_index].visible = visible
    sprite_index += 1

    # Calculate direction multiplier
    direction = 1 if invert else -1

    # Place wing rows
    for row in range(1, rows + 1):
        if sprite_index >= total_sprites:
            break

        # Calculate Y position for this row
        y_pos = tip_y + direction * row * spacing_along

        # Calculate wing spread for this row
        wing_spread = row * spacing_outward

        # Place left wing if sprite available
        if sprite_index < total_sprites:
            sprites[sprite_index].center_x = tip_x - wing_spread
            sprites[sprite_index].center_y = y_pos
            sprites[sprite_index].visible = visible
            sprite_index += 1

        # Place right wing if sprite available
        if sprite_index < total_sprites:
            sprites[sprite_index].center_x = tip_x + wing_spread
            sprites[sprite_index].center_y = y_pos
            sprites[sprite_index].visible = visible
            sprite_index += 1

    return sprites
