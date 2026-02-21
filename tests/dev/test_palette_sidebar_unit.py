"""Unit tests for legacy PaletteSidebar behavior."""

from __future__ import annotations

from arcadeactions.dev.palette import PaletteSidebar


class _Registry:
    def __init__(self) -> None:
        self._items: dict[str, callable] = {}

    def all(self) -> dict[str, callable]:
        return self._items

    def has(self, prototype_id: str) -> bool:
        return prototype_id in self._items

    def create(self, prototype_id: str, _ctx):
        factory = self._items[prototype_id]
        return factory()


class _Scene:
    def __init__(self) -> None:
        self.items: list[object] = []

    def append(self, item: object) -> None:
        self.items.append(item)


class _Ctx:
    def __init__(self, scene_sprites) -> None:
        self.scene_sprites = scene_sprites


class _SpriteStub:
    def __init__(self) -> None:
        self.center_x = 0
        self.center_y = 0
        self.alpha = 255
        self.draw_calls = 0

    def draw(self) -> None:
        self.draw_calls += 1


class _TextStub:
    def __init__(self, text: str, x: int, y: int, _color, _font_size: int) -> None:
        self.text = text
        self.x = x
        self.y = y
        self.draw_calls = 0

    def draw(self) -> None:
        self.draw_calls += 1


def test_palette_handle_spawn_and_drag_release_flow(monkeypatch):
    """Spawn and drag/release should create sprite and append to scene."""
    registry = _Registry()
    registry._items["enemy"] = _SpriteStub
    scene = _Scene()
    sidebar = PaletteSidebar(registry=registry, ctx=_Ctx(scene), x=10, y=10, width=120)

    sidebar.handle_spawn("missing", 10, 20)
    assert scene.items == []

    sidebar.handle_spawn("enemy", 100, 200)
    assert len(scene.items) == 1
    spawned = scene.items[0]
    assert spawned.center_x == 100
    assert spawned.center_y == 200

    # Click first (and only) item row.
    click_x = sidebar.x + 5
    click_y = sidebar.y + sidebar._item_height
    assert sidebar.handle_mouse_press(click_x, click_y) is True
    assert sidebar._drag_ghost is not None
    assert sidebar._drag_ghost.alpha == 128
    sidebar.handle_mouse_drag(300, 400)
    assert sidebar._drag_ghost.center_x == 300
    assert sidebar._drag_ghost.center_y == 400

    assert sidebar.handle_mouse_release(500, 600) is True
    assert len(scene.items) == 2
    assert sidebar._dragging_prototype is None
    assert sidebar._drag_ghost is None


def test_palette_mouse_press_bounds_visibility_and_draw_cache(monkeypatch):
    """Bounds and visibility should gate clicks; draw should rebuild/cache text."""
    monkeypatch.setattr("arcadeactions.dev.palette.arcade.Text", _TextStub)
    registry = _Registry()
    registry._items["a"] = _SpriteStub
    registry._items["b"] = _SpriteStub
    sidebar = PaletteSidebar(registry=registry, ctx=_Ctx(_Scene()), x=20, y=20, width=100)

    sidebar.visible = False
    assert sidebar.handle_mouse_press(25, 30) is False
    sidebar.visible = True
    assert sidebar.handle_mouse_press(10, 30) is False

    # Rebuild text cache on first draw.
    sidebar.draw()
    assert len(sidebar._text_cache) == 2
    first_cache = list(sidebar._text_cache)
    sidebar.draw()
    assert sidebar._text_cache == first_cache

    # Registry list mutation should force cache rebuild.
    registry._items["c"] = _SpriteStub
    sidebar.draw()
    assert len(sidebar._text_cache) == 3


def test_palette_release_without_drag_and_ctx_without_scene():
    """Release without drag should return False; missing scene should skip append."""
    registry = _Registry()
    registry._items["enemy"] = _SpriteStub
    sidebar = PaletteSidebar(registry=registry, ctx=_Ctx(None))

    assert sidebar.handle_mouse_release(10, 10) is False
    sidebar.handle_spawn("enemy", 12, 34)
