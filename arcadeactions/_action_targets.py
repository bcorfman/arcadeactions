from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    import arcade

    SpriteTarget = arcade.Sprite | arcade.SpriteList
else:
    SpriteTarget = Any


class TargetAdapter(Protocol):
    """Protocol for normalized sprite targets."""

    target: Any

    def iter_sprites(self) -> Iterable[Any]: ...

    def iter_sprite_lists(self) -> Iterable[Any]: ...

    def describe_target(self) -> str: ...


class SpriteTargetAdapter:
    """Adapter for single sprites."""

    def __init__(self, sprite: SpriteTarget):
        self.target = sprite
        self._sprite_lists = sprite.sprite_lists

    def iter_sprites(self) -> Iterable[Any]:
        return (self.target,)

    def iter_sprite_lists(self) -> Iterable[Any]:
        return self._sprite_lists

    def describe_target(self) -> str:
        return type(self.target).__name__


class SpriteListTargetAdapter:
    """Adapter for sprite list targets."""

    def __init__(self, sprite_list: SpriteTarget):
        self.target = sprite_list

    def iter_sprites(self) -> Iterable[Any]:
        return self.target

    def iter_sprite_lists(self) -> Iterable[Any]:
        return (self.target,)

    def describe_target(self) -> str:
        return _get_sprite_list_name(self.target)


class IterableTargetAdapter:
    """Adapter for plain iterable targets."""

    def __init__(self, target: Iterable[Any]):
        self.target = target

    def iter_sprites(self) -> Iterable[Any]:
        return self.target

    def iter_sprite_lists(self) -> Iterable[Any]:
        return ()

    def describe_target(self) -> str:
        return type(self.target).__name__


_ADAPTERS: dict[type[Any], type[TargetAdapter]] = {}
_DEFAULTS_REGISTERED = False


def register_target_adapter(target_type: type[Any], adapter_type: type[TargetAdapter]) -> None:
    """Register a target adapter for an explicit type."""
    _ADAPTERS[target_type] = adapter_type


def _find_adapter_type(target_type: type[Any]) -> type[TargetAdapter] | None:
    for candidate in target_type.__mro__:
        adapter_type = _ADAPTERS.get(candidate)
        if adapter_type is not None:
            return adapter_type
    return None


def ensure_default_target_adapters() -> None:
    """Register adapters for Arcade Sprite and SpriteList types."""
    global _DEFAULTS_REGISTERED
    if _DEFAULTS_REGISTERED:
        return
    import arcade

    register_target_adapter(arcade.Sprite, SpriteTargetAdapter)
    register_target_adapter(arcade.SpriteList, SpriteListTargetAdapter)
    register_target_adapter(list, IterableTargetAdapter)
    register_target_adapter(tuple, IterableTargetAdapter)
    _DEFAULTS_REGISTERED = True


def adapt_target(target: Any) -> TargetAdapter:
    """Return an adapter for the given target or raise TypeError."""
    ensure_default_target_adapters()
    adapter_type = _find_adapter_type(type(target))
    if adapter_type is None:
        raise TypeError("Action target must be iterable or expose sprite_lists")
    return adapter_type(target)


def _get_sprite_list_name(sprite_list: Any) -> str:
    """Return a stable summary without scanning unrelated live objects."""
    return f"SpriteList(len={len(sprite_list)})"
