import types

from arcadeactions import Action
from arcadeactions.frame_timing import after_frames


class FakeShadertoy:
    """Minimal stand-in for arcade.experimental.Shadertoy.

    Exposes a dict-like `program` for uniforms, resize() and render().
    """

    def __init__(self, size=(800, 600)):
        self.size = size
        self.program = {}
        self.resize_calls = []
        self.render_calls = 0

    def resize(self, size):
        self.size = size
        self.resize_calls.append(size)

    def render(self):
        self.render_calls += 1


def make_shadertoy_factory(fake: "FakeShadertoy"):
    def factory(initial_size):
        # size is provided by the action; we ignore and reuse the fake
        return fake

    return factory


class TestGlowUntil:
    def teardown_method(self):
        Action.stop_all()

    def test_glow_renders_and_sets_uniforms_with_camera_correction(self):
        from arcadeactions.conditional import GlowUntil

        # Arrange fakes
        fake = FakeShadertoy()

        # Uniforms provider returns world-space lightPosition that should be camera-corrected to screen-space
        def uniforms_provider(_shadertoy, _target):
            return {"lightPosition": (100.0, 50.0), "lightSize": 300.0}

        # Camera reports bottom-left offset in world space
        def get_camera_bottom_left():
            return (10.0, 5.0)

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
            uniforms_provider=uniforms_provider,
            get_camera_bottom_left=get_camera_bottom_left,
        )

        # Act: apply and run a couple of frames
        dummy_target = types.SimpleNamespace()
        action.apply(dummy_target)
        Action.update_all(0.016)
        Action.update_all(0.016)

        # Assert: render called, uniforms set with camera correction
        assert fake.render_calls >= 1
        assert fake.program["lightPosition"] == (90.0, 45.0)
        assert fake.program["lightSize"] == 300.0

        # After duration passes, action completes and stops rendering
        Action.update_all(0.05)
        render_calls_after = fake.render_calls
        Action.update_all(0.016)
        assert fake.render_calls == render_calls_after  # No new renders
        assert action.done

    def test_glow_resize(self):
        from arcadeactions.conditional import GlowUntil

        fake = FakeShadertoy()
        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(6),  # 0.1 seconds at 60 FPS
            auto_resize=True,
        )

        action.apply(types.SimpleNamespace())
        # Simulate window resize
        action.on_resize(123, 456)
        assert fake.resize_calls and fake.resize_calls[-1] == (123, 456)


class TestGlowUntilErrorHandling:
    """Test GlowUntil error handling and edge cases."""

    def teardown_method(self):
        Action.stop_all()

    def test_factory_failure(self):
        """Test GlowUntil handles shader factory failure gracefully."""
        from arcadeactions.conditional import GlowUntil

        def failing_factory(size):
            raise RuntimeError("Shader creation failed")

        action = GlowUntil(
            shadertoy_factory=failing_factory,
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
        )
        action.apply(types.SimpleNamespace())

        # Should not crash, shader should be None
        assert action._shader is None

        # Update should handle None shader gracefully
        Action.update_all(0.016)
        assert not action.done  # Should still be running

    def test_no_shader_update(self):
        """Test update_effect handles None shader."""
        from arcadeactions.conditional import GlowUntil

        action = GlowUntil(
            shadertoy_factory=lambda size: None,  # Returns None
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
        )
        action.apply(types.SimpleNamespace())

        # Should not crash on update
        Action.update_all(0.016)
        assert not action.done

    def test_on_stop_callback_exception(self):
        """Test GlowUntil handles on_stop callback exceptions."""
        from arcadeactions.conditional import GlowUntil

        fake = FakeShadertoy()

        def failing_callback(data):
            raise ValueError("Callback failed")

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(1),  # 0.01 seconds at 60 FPS (1 frame) - Very short duration
            on_stop=failing_callback,
        )
        action.apply(types.SimpleNamespace())

        # Should complete without crashing despite callback failure
        Action.update_all(0.02)
        assert action.done

    def test_uniforms_provider_failure(self):
        """Test GlowUntil handles uniforms_provider exceptions."""
        from arcadeactions.conditional import GlowUntil

        fake = FakeShadertoy()

        def failing_uniforms_provider(shader, target):
            raise RuntimeError("Uniforms failed")

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
            uniforms_provider=failing_uniforms_provider,
        )
        action.apply(types.SimpleNamespace())

        # Should not crash, should continue rendering
        Action.update_all(0.016)
        assert fake.render_calls >= 1

    def test_camera_correction_failure(self):
        """Test GlowUntil handles camera correction exceptions."""
        from arcadeactions.conditional import GlowUntil

        fake = FakeShadertoy()

        def uniforms_provider(shader, target):
            return {"lightPosition": (100.0, 200.0)}

        def failing_camera_provider():
            raise RuntimeError("Camera failed")

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
            uniforms_provider=uniforms_provider,
            get_camera_bottom_left=failing_camera_provider,
        )
        action.apply(types.SimpleNamespace())

        # Should not crash, should use original coordinates
        Action.update_all(0.016)
        assert fake.program["lightPosition"] == (100.0, 200.0)

    def test_render_failure(self):
        """Test GlowUntil handles render exceptions."""
        from arcadeactions.conditional import GlowUntil

        class FailingShadertoy(FakeShadertoy):
            def render(self):
                raise RuntimeError("Render failed")

        fake = FailingShadertoy()

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
        )
        action.apply(types.SimpleNamespace())

        # Should not crash on render failure
        Action.update_all(0.016)
        assert not action.done

    def test_resize_failure(self):
        """Test GlowUntil handles resize exceptions."""
        from arcadeactions.conditional import GlowUntil

        class FailingShadertoy(FakeShadertoy):
            def resize(self, size):
                raise RuntimeError("Resize failed")

        fake = FailingShadertoy()

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
            auto_resize=True,
        )
        action.apply(types.SimpleNamespace())

        # Should not crash on resize failure
        action.on_resize(800, 600)
        assert not action.done

    def test_clone_method(self):
        """Test GlowUntil clone method."""
        from arcadeactions.conditional import GlowUntil

        fake = FakeShadertoy()

        def uniforms_provider(shader, target):
            return {"test": 1.0}

        def camera_provider():
            return (10.0, 20.0)

        original = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=after_frames(3),  # 0.05 seconds at 60 FPS
            uniforms_provider=uniforms_provider,
            get_camera_bottom_left=camera_provider,
            auto_resize=False,
            draw_order="before",
        )

        cloned = original.clone()

        # Should have same configuration
        assert cloned._factory == original._factory
        assert cloned._uniforms_provider == original._uniforms_provider
        assert cloned._camera_bottom_left_provider == original._camera_bottom_left_provider
        assert cloned._auto_resize == original._auto_resize
        assert cloned._draw_order == original._draw_order
        assert cloned.condition != original.condition  # Different condition instance

    def test_manual_duration_completion_skips_condition_and_passes_none_to_callback(self):
        """Manual duration completion should stop before condition evaluation and pass None."""
        from arcadeactions.conditional import GlowUntil

        fake = FakeShadertoy()
        callback_args: list[tuple[object, ...]] = []
        condition_calls = {"count": 0}

        def condition_with_data():
            condition_calls["count"] += 1
            return {"source": "condition"}

        def on_stop(*args):
            callback_args.append(args)

        action = GlowUntil(
            shadertoy_factory=make_shadertoy_factory(fake),
            condition=condition_with_data,
            on_stop=on_stop,
        )
        action.apply(types.SimpleNamespace())
        action._duration = 0.01

        Action.update_all(0.02)

        assert action.done
        assert action._condition_met
        assert action.condition_data is None
        assert condition_calls["count"] == 0
        assert callback_args == [((None),)]
        assert fake.render_calls == 0
