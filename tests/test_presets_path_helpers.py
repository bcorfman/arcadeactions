"""Coverage tests for legacy presets path helper modules."""

from __future__ import annotations

import math

from arcadeactions.presets import dive_paths, entry_paths


def test_dive_straight_curve_and_loop_shapes():
    """Basic dive path builders should return expected control-point shapes."""
    straight = dive_paths.dive_straight(10, 20, 30, 40)
    assert straight == [(10, 20), (30, 40)]

    curve = dive_paths.dive_curve(0, 0, 10, 20, curve_strength=5.0)
    assert curve[0] == (0, 0)
    assert curve[2] == (10, 20)
    assert curve[1] == (10.0, 10.0)

    loop = dive_paths.dive_loop(100, 200, 120, 50, loop_radius=25)
    assert loop[0] == (100, 200)
    assert loop[-1] == (120, 50)
    assert len(loop) == 5


def test_dive_zigzag_and_corkscrew_branch_behavior():
    """Zigzag min-segment clamp and corkscrew point density should be deterministic."""
    zig = dive_paths.dive_zigzag(0, 0, 0, 100, zigzag_width=10, segments=1)
    assert len(zig) == 3
    assert zig[1][0] in (-10, 10)

    cork = dive_paths.dive_corkscrew(0, 0, 0, 100, spiral_radius=10, turns=2.0)
    assert cork[0] == (0, 0)
    assert cork[-1] == (0, 100)
    assert len(cork) == int(2.0 * 4) + 2


def test_entry_path_helpers_cover_all_patterns():
    """Entry path helpers should generate stable waypoint lists and clamp segments."""
    circle = entry_paths.circle_arc_waypoints(100, 200, 30)
    assert len(circle) == 13
    assert circle[0] == circle[-1]

    exact = entry_paths.loop_the_loop_exact(
        start_x=10,
        start_y=0,
        end_x=40,
        end_y=80,
        loop_center_x=25,
        loop_center_y=40,
        loop_radius=15,
    )
    assert exact[0] == (10, 0)
    assert exact[-1] == (40, 80)
    assert (25, 31.0) in exact  # approach/exit point

    approx = entry_paths.loop_the_loop(0, 0, 50, 100, loop_radius=20)
    assert approx[0] == (0, 0)
    assert approx[-1] == (50, 100)
    assert len(approx) >= 8

    corkscrew = entry_paths.corkscrew_entry(0, 0, 0, 90, spiral_radius=12, turns=1.5)
    assert corkscrew[0] == (0, 0)
    assert corkscrew[-1] == (0, 90)
    assert len(corkscrew) == int(1.5 * 6) + 2

    zigzag = entry_paths.zigzag_entry(0, 0, 0, 100, zigzag_width=10, segments=1)
    assert len(zigzag) == 3
    assert zigzag[-1] == (0, 100)

    straight = entry_paths.straight_entry(1, 2, 3, 4)
    assert straight == [(1, 2), (3, 4)]

    swoop = entry_paths.swoop_entry(0, 0, 10, 20, swoop_strength=-4.0)
    assert swoop[0] == (0, 0)
    assert swoop[-1] == (10, 20)
    assert math.isclose(swoop[1][0], 1.0)
