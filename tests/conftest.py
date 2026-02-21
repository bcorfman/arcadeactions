"""Shared test fixtures and utilities for the ArcadeActions test suite."""

import os
import sys

import arcade
import pytest

# Import window_commands module to ensure we can patch it
try:
    import arcade.window_commands as window_commands_module
except ImportError:
    window_commands_module = None

# Import sprite_list module early so we can patch get_window in it
try:
    import arcade.sprite_list.sprite_list as sprite_list_module
except ImportError:
    sprite_list_module = None

from arcadeactions import Action


class StderrFilter:
    """Filter to suppress known harmless pyglet audio driver cleanup errors."""

    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.buffer = ""
        self.suppressing = False
        # Simple patterns to detect the pyglet audio driver error
        self.error_keywords = ["_delete_audio_driver", "Source._players", "Exception ignored in atexit callback"]

    def _contains_error(self, text):
        """Check if text contains the pyglet audio driver error."""
        # Check if all key error phrases are present
        text_lower = text.lower()
        return all(keyword.lower() in text_lower for keyword in self.error_keywords)

    def write(self, text):
        """Write to stderr, filtering out known harmless errors."""
        # Buffer writes to catch multi-line error messages
        self.buffer += text

        # Check if buffer contains the complete error
        if self._contains_error(self.buffer):
            # Suppress the entire error
            self.buffer = ""
            self.suppressing = False
            return

        # If we're currently suppressing, keep buffering until we see the error end
        if self.suppressing:
            # Check if we've seen enough to determine it's the error
            if "_players" in self.buffer and "AttributeError" in self.buffer:
                # Likely the end of the error, stop suppressing
                self.buffer = ""
                self.suppressing = False
                return
            # Keep suppressing
            return

        # Check if this looks like the start of the error
        if "_delete_audio_driver" in self.buffer or "Exception ignored in atexit callback" in self.buffer:
            self.suppressing = True
            # Don't write yet, keep buffering
            return

        # Normal output - flush buffer if it's getting large or we see newlines
        if len(self.buffer) > 8192:
            self.original_stderr.write(self.buffer)
            self.buffer = ""
        elif "\n" in text:
            # Flush complete lines
            lines = self.buffer.split("\n")
            self.buffer = lines[-1]  # Keep last incomplete line
            output = "\n".join(lines[:-1])
            if output:
                self.original_stderr.write(output + "\n")

    def flush(self):
        """Flush any remaining buffer and the original stderr."""
        if self.buffer and not self.suppressing:
            self.original_stderr.write(self.buffer)
            self.buffer = ""
        elif self.suppressing:
            # Clear suppressed error
            self.buffer = ""
            self.suppressing = False
        self.original_stderr.flush()

    def __getattr__(self, name):
        """Delegate other attributes to original stderr."""
        return self.original_stderr.__getattribute__(name)


def pytest_configure(config):
    """Install stderr filter and patch pyglet's atexit handler at pytest startup."""
    # Install the filter early, before any tests run
    # Keep it active permanently to catch atexit errors that occur after pytest finishes
    if not isinstance(sys.stderr, StderrFilter):
        sys.stderr = StderrFilter(sys.stderr)

    # Patch pyglet to prevent the AttributeError
    # This is a known issue in pyglet where _delete_audio_driver tries to access
    # Source._players which may not exist. We ensure it exists as an empty list.
    try:
        # Source is in pyglet.media.codecs.base, but might be imported as pyglet.media.Source
        # Try both import paths to be safe
        try:
            from pyglet.media.codecs.base import Source
        except ImportError:
            from pyglet.media import Source

        # Ensure Source._players exists to prevent AttributeError
        if not hasattr(Source, "_players"):
            Source._players = []
    except Exception:
        # If patching fails, fall back to stderr filtering
        pass


def pytest_collection_modifyitems(config, items):
    """Skip integration/slow tests locally unless in CI or explicitly requested.

    Integration tests (marked with @pytest.mark.integration) are skipped by default
    when running locally to avoid popping up windows. Slow tests (marked with
    @pytest.mark.slow) are also skipped by default. Both run automatically on
    GitHub Actions (CI=true or GITHUB_ACTIONS=true).

    To run integration tests locally, use: pytest -m integration
    To run slow tests locally, use: pytest -m slow
    """
    # Check if we're in CI
    is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"

    # Check if user explicitly requested integration or slow tests.
    marker_expr = config.getoption("-m", default="")
    integration_requested = bool(marker_expr) and "integration" in marker_expr
    slow_requested = bool(marker_expr) and "slow" in marker_expr

    if not is_ci and not integration_requested:
        skip_integration = pytest.mark.skip(reason="Integration tests skipped locally (use -m integration to run)")
        for item in items:
            is_integration = "integration" in item.keywords
            is_slow = "slow" in item.keywords
            if is_integration and not is_slow:
                item.add_marker(skip_integration)
    if not is_ci and not slow_requested:
        skip_slow = pytest.mark.skip(reason="Slow tests skipped locally (use -m slow to run)")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


class HeadlessWindow:
    """Minimal window substitute used on platforms without OpenGL support."""

    def __init__(self, width: int = 800, height: int = 600, visible: bool = False, **kwargs) -> None:
        self.width = width
        self.height = height
        self.visible = visible
        self.has_exit = False
        self.location: tuple[int, int] = (0, 0)
        self._title = kwargs.get("title", "Headless Window")
        self.handlers: dict[str, object] = {}
        self._view = None
        self._update_rate = 60

    @property
    def ctx(self):  # pragma: no cover - behaviour verified indirectly
        raise RuntimeError("No OpenGL context available (headless CI mode)")

    def close(self) -> None:
        self.has_exit = True

    def set_location(self, x: int, y: int) -> None:
        self.location = (x, y)

    def set_caption(self, title: str) -> None:
        self._title = title

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def clear(self) -> None:
        """No-op clear."""

    def switch_to(self) -> None:
        """No-op context switch."""

    def show_view(self, view) -> None:
        self._view = view

    @property
    def current_view(self):
        return self._view

    def on_draw(self, *args, **kwargs):  # pragma: no cover - defensive
        return None

    def on_update(self, *args, **kwargs):  # pragma: no cover - defensive
        return None

    def on_close(self) -> None:
        self.has_exit = True

    def push_handlers(self, **handlers) -> None:
        self.handlers.update(handlers)

    def set_visible(self, visible: bool) -> None:
        self.visible = bool(visible)

    def dispatch_event(self, event_type: str, *args, **kwargs):  # pragma: no cover - defensive
        handler = self.handlers.get(event_type)
        if handler:
            return handler(*args, **kwargs)
        return None


class HeadlessText:
    """Text stub for headless OpenGL environments."""

    def __init__(self, text: str, *args, **kwargs) -> None:  # noqa: ANN001
        self.text = text
        self.content_width = max(1, len(text)) * 6

    def draw(self) -> None:
        return None


# Global window instance (created lazily, shared across all tests)
_global_test_window = None
_original_window_class = None
_original_get_window = None
_original_get_window_module = None
_original_get_window_sprite_list = None
_original_spritelist_init = None
_original_ctx_property_global = None
_original_getattribute = None
_original_arcade_text = None
_headless_mode = False


@pytest.fixture(scope="session", autouse=True)
def _ensure_window_context():
    """Ensure a window context exists for all tests.

    This session-scoped autouse fixture creates a window once at the start
    of the test session and cleans it up at the end. This avoids the overhead
    of creating a window for every test while ensuring sprites/sprite lists
    can be created in CI environments.

    On Linux with Xvfb, creates a real window. On Windows/macOS CI without
    OpenGL, monkeypatches Window.__init__ to create a mock window.
    """
    global _global_test_window
    global _original_window_class
    global _original_get_window
    global _original_get_window_module
    global _original_get_window_sprite_list
    global _original_spritelist_init
    global _headless_mode
    global _original_arcade_text

    if _global_test_window is not None:
        yield
        return

    # Detect whether we need the headless fallback (Windows/macOS CI)
    is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
    is_linux = sys.platform.startswith("linux")
    _headless_mode = bool(is_ci and not is_linux)

    if not _headless_mode:
        try:
            _global_test_window = arcade.Window(800, 600, visible=False)
            if window_commands_module is not None:
                window_commands_module.set_window(_global_test_window)
            else:
                arcade.set_window(_global_test_window)
        except Exception:
            # Fall back to headless mode if creating a real window fails
            _headless_mode = True

    if _headless_mode:
        # Monkeypatch arcade.Window to use the headless implementation
        if _original_window_class is None:
            _original_window_class = arcade.Window
        arcade.Window = HeadlessWindow
        if _original_arcade_text is None:
            _original_arcade_text = arcade.Text
        arcade.Text = HeadlessText

        # Headless get_window implementation
        def headless_get_window():
            if _global_test_window is None:
                raise RuntimeError("Headless window not initialised")
            return _global_test_window

        if _original_get_window is None:
            _original_get_window = arcade.get_window
        arcade.get_window = headless_get_window

        if window_commands_module is not None and _original_get_window_module is None:
            _original_get_window_module = window_commands_module.get_window
            window_commands_module.get_window = headless_get_window

        if sprite_list_module is not None:
            if _original_get_window_sprite_list is None:
                _original_get_window_sprite_list = getattr(sprite_list_module, "get_window", None)
            sprite_list_module.get_window = headless_get_window

            if _original_spritelist_init is None:
                _original_spritelist_init = sprite_list_module.SpriteList.__init__

            def spritelist_init_lazy(
                self,
                use_spatial_hash: bool = False,
                spatial_hash_cell_size: int = 128,
                atlas=None,
                capacity: int = 100,
                lazy: bool = False,
                visible: bool = True,
            ) -> None:
                # Force lazy=True so GL resources are never touched on headless CI
                return _original_spritelist_init(
                    self,
                    use_spatial_hash,
                    spatial_hash_cell_size,
                    atlas,
                    capacity,
                    True,
                    visible,
                )

            sprite_list_module.SpriteList.__init__ = spritelist_init_lazy

        # Create the shared headless window instance
        _global_test_window = arcade.Window(800, 600, visible=False)
        if window_commands_module is not None:
            window_commands_module.set_window(_global_test_window)
        else:
            arcade.set_window(_global_test_window)

    yield

    # Teardown
    if _global_test_window is not None:
        try:
            _global_test_window.close()
        except Exception:
            pass
        try:
            if window_commands_module is not None:
                window_commands_module.set_window(None)
            else:
                arcade.set_window(None)
        except Exception:
            pass
        _global_test_window = None

    if _headless_mode:
        if _original_spritelist_init is not None and sprite_list_module is not None:
            sprite_list_module.SpriteList.__init__ = _original_spritelist_init
            _original_spritelist_init = None

        if _original_get_window_sprite_list is not None and sprite_list_module is not None:
            sprite_list_module.get_window = _original_get_window_sprite_list
            _original_get_window_sprite_list = None

        if window_commands_module is not None and _original_get_window_module is not None:
            window_commands_module.get_window = _original_get_window_module
            _original_get_window_module = None

        if _original_get_window is not None:
            arcade.get_window = _original_get_window
            _original_get_window = None

        if _original_window_class is not None:
            arcade.Window = _original_window_class
            _original_window_class = None
        if _original_arcade_text is not None:
            arcade.Text = _original_arcade_text
            _original_arcade_text = None

    _headless_mode = False


@pytest.fixture
def require_opengl():
    """Skip tests that need a real OpenGL context in headless CI."""
    if _headless_mode:
        pytest.skip("OpenGL context not available (headless CI mode)")
    return True


@pytest.fixture(scope="function")
def window():
    """Provide window context for tests that explicitly need it.

    Most tests don't need to request this - the window is created automatically.
    This fixture is for tests that need explicit access to the window object.
    """
    # Ensure window exists (should already exist from _ensure_window_context)
    try:
        win = arcade.get_window()
        if win is not None:
            yield win
            return
    except RuntimeError:
        pass

    # Fallback: return global window if it exists
    # Don't try to create a new window here - that should have been done
    # by _ensure_window_context. If we're here, something went wrong, but
    # we shouldn't try to create a real window on Windows/macOS CI.
    global _global_test_window
    if _global_test_window is not None:
        yield _global_test_window
    else:
        # If no window exists at all, this is a test setup problem
        # Yield None rather than trying to create a window (which would fail on CI)
        yield None


@pytest.fixture
def test_sprite(window) -> arcade.Sprite:
    """Create a sprite with texture for testing.

    Uses SpriteSolidColor for faster test execution (avoids texture file I/O).
    """
    sprite = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.WHITE)
    sprite.center_x = 100
    sprite.center_y = 100
    sprite.angle = 0
    sprite.scale = 1.0
    sprite.alpha = 255
    return sprite


@pytest.fixture
def test_sprite_list(window) -> arcade.SpriteList:
    """Create a SpriteList with test sprites.

    Uses SpriteSolidColor for faster test execution (avoids texture file I/O).
    """
    sprite_list = arcade.SpriteList()
    sprite1 = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.WHITE)
    sprite2 = arcade.SpriteSolidColor(width=32, height=32, color=arcade.color.WHITE)
    sprite1.center_x = 50
    sprite2.center_x = 150
    sprite_list.append(sprite1)
    sprite_list.append(sprite2)
    return sprite_list


@pytest.fixture(autouse=True)
def cleanup_actions():
    """Clean up actions after each test."""
    # Reset frame counter before each test
    Action._frame_counter = 0
    yield
    Action.stop_all()
    # Reset frame counter after each test as well
    Action._frame_counter = 0


class ActionTestBase:
    """Base class for action tests with common setup and teardown."""

    def teardown_method(self):
        """Clean up after each test."""
        Action.stop_all()


@pytest.fixture(autouse=True)
def _restore_global_window() -> None:
    """Ensure each test leaves the global window pointing at the headless test window."""
    yield
    global _global_test_window
    try:
        if _global_test_window is None or getattr(_global_test_window, "has_exit", False):
            _global_test_window = arcade.Window(800, 600, visible=False)
        arcade.set_window(_global_test_window)
        try:
            _global_test_window.switch_to()
        except Exception:
            pass
        if window_commands_module is not None:
            window_commands_module.set_window(_global_test_window)
    except Exception:
        # Ignore cleanup failures so individual tests can still succeed
        pass


@pytest.fixture
def enable_action_safety(monkeypatch):
    """Enable action safety features (conflict detection) for tests.

    This fixture enables ACTIONS_WARN_CONFLICTS environment variable
    so that conflict detection warnings are active during tests. Tests that
    need conflict detection should explicitly request this fixture.

    Example:
        def test_something(enable_action_safety):
            # Conflict detection warnings are now enabled
            ...
    """
    monkeypatch.setenv("ACTIONS_WARN_CONFLICTS", "1")
    yield
    # Cleanup handled by monkeypatch
