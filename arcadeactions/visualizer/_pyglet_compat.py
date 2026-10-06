"""Compatibility imports for Pyglet APIs that moved between major versions."""

try:
    from pyglet.graphics.api.gl.lib import GLException
except ModuleNotFoundError:
    # Pyglet 2 exposes this exception from its legacy OpenGL package.
    from pyglet.gl.lib import GLException

__all__ = ["GLException"]
