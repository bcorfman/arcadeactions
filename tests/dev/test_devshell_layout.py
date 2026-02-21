"""Unit tests for one-window DevShell layout sizing and region calculations."""

from __future__ import annotations

from arcadeactions.dev.devshell_layout import DevShellLayout


def test_min_window_size_includes_stage_and_rails():
    """Minimum size should include stage plus both horizontal/vertical rails."""
    layout = DevShellLayout(
        stage_width=1280,
        stage_height=720,
        left_rail_width=280,
        right_rail_width=320,
        top_rail_height=48,
        bottom_rail_height=36,
    )

    assert layout.min_window_size() == (1880, 804)


def test_clamp_window_size_enforces_minimum_contract():
    """Clamp should snap too-small windows back to the minimum contract."""
    layout = DevShellLayout(
        stage_width=1280,
        stage_height=720,
        left_rail_width=240,
        right_rail_width=240,
        top_rail_height=40,
        bottom_rail_height=40,
    )

    width, height = layout.clamp_window_size(1400, 760)

    assert (width, height) == (1760, 800)


def test_edit_live_regions_keep_stage_isolated_from_rails():
    """In Edit-Live mode stage rect should be fully bounded by reserved rails."""
    layout = DevShellLayout(
        stage_width=1280,
        stage_height=720,
        left_rail_width=220,
        right_rail_width=300,
        top_rail_height=44,
        bottom_rail_height=32,
    )
    regions = layout.compute_regions(window_width=1900, window_height=900, preview_clean=False)

    assert regions.stage.width == 1380
    assert regions.stage.height == 824
    assert regions.stage.x == 220
    assert regions.stage.y == 32

    assert regions.left.width == 220
    assert regions.right.width == 300
    assert regions.top.height == 44
    assert regions.bottom.height == 32


def test_preview_clean_collapses_rails_to_zero_and_uses_full_stage():
    """Preview-Clean should collapse rails and use full window for stage rendering."""
    layout = DevShellLayout(
        stage_width=1280,
        stage_height=720,
        left_rail_width=220,
        right_rail_width=300,
        top_rail_height=44,
        bottom_rail_height=32,
    )
    regions = layout.compute_regions(window_width=1900, window_height=900, preview_clean=True)

    assert regions.stage.x == 0
    assert regions.stage.y == 0
    assert regions.stage.width == 1900
    assert regions.stage.height == 900

    assert regions.left.width == 0
    assert regions.right.width == 0
    assert regions.top.height == 0
    assert regions.bottom.height == 0
