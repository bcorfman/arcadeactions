import os
import subprocess
import textwrap
from unittest import mock

import arcade

from arcadeactions.dev.position_tag import tag_sprite
from arcadeactions.dev.visualizer import DevVisualizer


class DummySprite:
    def __init__(self):
        self.center_x = 10
        self.center_y = 20
        self.height = 16


def test_on_reload_marks_tagged_sprite(tmp_path):
    src = textwrap.dedent(
        """
        forcefield.left = 100
        forcefield.top = 200
        """
    )
    p = tmp_path / "forcefield.py"
    p.write_text(src)

    # Create runtime sprite and tag it
    s = DummySprite()
    tag_sprite(s, "forcefield")

    # Create DevVisualizer and call on_reload
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    dev_viz.on_reload([p], saved_state={})

    assert hasattr(s, "_source_markers")
    markers = s._source_markers
    assert len(markers) >= 1
    m = markers[0]
    assert str(m["file"]) == str(p)
    # lineno should be 1 or 2 depending on leading newline; check it is an int
    assert isinstance(m["lineno"], int)


def test_open_sprite_source_calls_code_goto(tmp_path):
    # Create marker and verify VS Code CLI receives file:line.
    marker = {"file": str(tmp_path / "x.py"), "lineno": 12}
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    with mock.patch.object(subprocess, "Popen") as popen_mock:
        dev_viz.open_sprite_source(None, marker)
        popen_mock.assert_called_once_with(["code", "--goto", f"{os.path.abspath(marker['file'])}:12"])


def test_open_sprite_source_prints_fallback_when_code_cli_fails(tmp_path):
    marker = {"file": str(tmp_path / "x.py"), "lineno": 12}
    dev_viz = DevVisualizer(scene_sprites=arcade.SpriteList())
    with mock.patch.object(subprocess, "Popen", side_effect=OSError("missing")):
        with mock.patch("builtins.print") as print_mock:
            dev_viz.open_sprite_source(None, marker)
            print_mock.assert_called_once_with(f"Open file at {marker['file']}:{marker['lineno']}")
