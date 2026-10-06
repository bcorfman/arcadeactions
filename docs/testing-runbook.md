# Testing Runbook

## Pyglet 3 visualizer import compatibility

**Purpose:** Check that renderer code and tests import the OpenGL exception adapter under Pyglet 3 and that visualizer tests collect.

**Setup / seed:** Install the branch dependencies with `uv sync --all-groups`. Pyglet 3 is supplied by the Arcade 4 development dependency.

**Safe actions:** Dependency installation, linting, test collection, and tests are local and reversible.

**Destructive or external actions:** None.

**Steps:**

1. Run the focused visualizer tests and collection check below.
2. For graphics dependent CI coverage, install the example extras and run the integration and full suites under Xvfb.

**Verify:**

```bash
uv run python -m pytest tests/unit/test_visualizer_overlay_renderer_unit.py tests/unit/test_visualizer_panel_renderers_unit.py tests/integration/test_visualizer_renderer.py -q
uv run python -m pytest --collect-only -q
uv run pytest tests/ -q --ignore=tests/integration
uv run --no-project --with arcade==3.3.3 --with pyglet==2.1.14 python -c 'from arcadeactions.visualizer._pyglet_compat import GLException; print(GLException.__module__)'
uv sync --extra statemachine --extra pymunk --dev
CI=true LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a uv run pytest tests/integration/ -q
CI=true LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a uv run pytest tests/ -q
timeout 5s xvfb-run -a env LIBGL_ALWAYS_SOFTWARE=1 uv run python examples/invaders.py
timeout 5s xvfb-run -a env LIBGL_ALWAYS_SOFTWARE=1 uv run python examples/pymunk_demo_platformer.py
```

Expected: focused tests pass; tests requiring OpenGL are skipped only when no graphics context is available; all configured tests collect; the CI full suite passes. With Xvfb, `tests/integration/` reported 265 passed and `tests/` reported 2,157 passed on Arcade 4.0.0.dev7. The Pyglet PR dependency set reported 2,156 passed and 1 skipped. Both affected example smoke commands ran until their five-second timeout. The compatibility check prints `pyglet.gl.lib`. A direct import of `pyglet.gl.lib` fails on Pyglet 3 with `ModuleNotFoundError: No module named 'pyglet.gl'`. Production and test code should import `GLException` through `arcadeactions.visualizer._pyglet_compat` and easing curves through `arcadeactions.easing`.

**Cleanup:** None.

**Notes:** The adapter imports `pyglet.graphics.api.gl.lib.GLException` on Pyglet 3 and falls back to the Pyglet 2 module path. Arcade 4 no longer provides `arcade.easing`; ArcadeActions owns the easing curves now. Sprite list debug labels use a stable length summary and do not scan unrelated live runtime objects. Formation conversion and cloning defer atlas registration until drawing, and non-rendering space clutter tests use lazy sprite lists. The examples CI job installs the `pymunk` extra required by the Pymunk demo.
