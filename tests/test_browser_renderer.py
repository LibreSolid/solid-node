# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The web snapshot renderer: this side stages, the viewer photographs."""

import argparse
import json
import os
import sys
import tempfile
import unittest
from subprocess import CompletedProcess
from unittest import TestCase
from unittest.mock import Mock, patch

from solid_node.viewers import browser as browser_module
from solid_node.viewers.browser import BrowserRenderer, BrowserSnapshotError
from solid_node.viewers.bundle import has_bundle
from solid_node.core.builder import prepare_build_dir
from solid_node.manager.snapshot import Snapshot
from tests.test_build_lock import lock_is_held
from tests.test_export import Cube

VIEWER = [sys.executable, '-m', 'solid_node_viewer']

needs_viewer = unittest.skipUnless(
    has_bundle(), 'solid-node-viewer not installed (pip install "solid-node[viewer]")'
)


def snapshot_args(**overrides):
    values = dict(path='model.py', time=0.0, camera=None, imgsize='100x100')
    values.update(overrides)
    return argparse.Namespace(**values)


@needs_viewer
class BrowserStagingTest(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.build_dir = os.path.join(self.temporary.name, "_build")
        os.makedirs(self.build_dir)
        self.node = Cube(self.build_dir)
        self.model = self.node.stl_file
        self.renderer = BrowserRenderer()

    def test_stage_hardlinks_every_artifact_and_pins_it(self):
        staging = self.renderer.stage(self.node, self.build_dir)
        self.addCleanup(self.renderer.remove_stage, staging)
        staged_model = os.path.join(staging, "parts", "cube.stl")
        self.assertEqual(os.stat(self.model).st_ino, os.stat(staged_model).st_ino)
        os.remove(self.model)
        with open(staged_model, "rb") as staged:
            self.assertIn(b"solid cube", staged.read())

    def test_stage_holds_the_document_and_nothing_of_the_viewer(self):
        staging = self.renderer.stage(self.node, self.build_dir)
        self.addCleanup(self.renderer.remove_stage, staging)
        self.assertEqual(sorted(os.listdir(staging)), ['parts', 'viewer.json'])

    def test_capture_begins_after_the_build_lock_is_released(self):
        node = self.node
        with (
            patch.object(node, "build_stls") as build,
            patch.object(self.renderer, "build_dir", return_value=self.build_dir),
            patch.object(self.renderer, "capture") as capture,
        ):
            build.side_effect = lambda: self.assertTrue(lock_is_held(self.build_dir))
            capture.side_effect = lambda *args: self.assertFalse(lock_is_held(self.build_dir))
            self.renderer.render(node, snapshot_args(), "shot.png")

    def test_stage_is_removed_when_capture_fails(self):
        node = self.node
        with (
            patch.object(node, "build_stls"),
            patch.object(self.renderer, "build_dir", return_value=self.build_dir),
            patch.object(self.renderer, "capture", side_effect=RuntimeError("boom")),
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                self.renderer.render(node, snapshot_args(), "shot.png")
        leftovers = [name for name in os.listdir(self.temporary.name)
                     if name.startswith("_build.web-snapshot.")]
        self.assertEqual(leftovers, [])

    def test_stage_survives_overlapping_build_preparation(self):
        staging = self.renderer.stage(self.node, self.build_dir)
        self.addCleanup(self.renderer.remove_stage, staging)
        staged_document = os.path.join(staging, 'viewer.json')
        staged_model = os.path.join(staging, 'parts', 'cube.stl')

        prepare_build_dir(self.build_dir)

        self.assertTrue(os.path.isfile(staged_document))
        with open(staged_model, 'rb') as artifact:
            self.assertIn(b'solid cube', artifact.read())


@needs_viewer
class PublishedBuildIsNotDisturbedTest(TestCase):
    """A snapshot is a reader: it must not republish or sweep the build."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.build_dir = os.path.join(self.temporary.name, "_build")
        os.makedirs(os.path.join(self.build_dir, "parts"))
        self.unrelated = os.path.join(self.build_dir, "parts", "other.stl")
        with open(self.unrelated, "wb") as output:
            output.write(b"solid other\nendsolid other\n")
        self.document = os.path.join(self.build_dir, "viewer.json")
        with open(self.document, "w") as output:
            json.dump({
                "format": "solid-node-document", "version": 1,
                "animation": {"fps": 30, "frames": 360},
                "root": {"name": "other", "type": "rigid",
                         "model": "parts/other.stl", "children": []},
            }, output)
        self.errors = os.path.join(self.build_dir, "errors.json")
        with open(self.errors, "w") as output:
            json.dump({"error": "a real failure", "tstamp": 1.0}, output)
        self.renderer = BrowserRenderer()

    def render(self):
        node = Cube(self.build_dir)
        with (
            patch.object(node, "build_stls"),
            patch.object(self.renderer, "build_dir", return_value=self.build_dir),
            patch.object(self.renderer, "capture") as capture,
        ):
            capture.side_effect = lambda staging, *rest: self.assertTrue(
                os.path.isfile(os.path.join(staging, "viewer.json")))
            self.renderer.render(node, snapshot_args(),
                                 os.path.join(self.temporary.name, "shot.png"))

    def test_artifacts_of_another_published_tree_survive(self):
        self.render()
        self.assertTrue(os.path.isfile(self.unrelated))

    def test_the_published_document_is_left_alone(self):
        with open(self.document) as source:
            before = source.read()
        self.render()
        with open(self.document) as source:
            self.assertEqual(source.read(), before)

    def test_a_recorded_build_error_is_not_cleared(self):
        self.render()
        self.assertTrue(os.path.isfile(self.errors))

    def test_the_staged_document_describes_the_photographed_node(self):
        staged = {}
        original = self.renderer.stage

        def capture_stage(node, build_dir):
            staging = original(node, build_dir)
            with open(os.path.join(staging, "viewer.json")) as source:
                staged.update(json.load(source))
            return staging

        with patch.object(self.renderer, "stage", side_effect=capture_stage):
            self.render()
        self.assertEqual(staged["root"]["name"], "Cube")
        self.assertEqual(staged["root"]["model"], "parts/cube.stl")


class CaptureDelegationTest(TestCase):
    """The photograph is the viewer's; this side only says what to shoot."""

    def setUp(self):
        self.renderer = BrowserRenderer()
        self.completed = CompletedProcess(args=[], returncode=0, stdout='', stderr='')

    def test_the_viewer_capture_runs_on_the_staging_directory(self):
        with patch.object(browser_module, 'run', return_value=self.completed) as run:
            self.renderer.capture('/tmp/staged', snapshot_args(time=0.25, imgsize='320x240'),
                                  'out/shot.png')
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command, VIEWER + [
            'capture', '/tmp/staged', '-o', 'out/shot.png',
            '--imgsize', '320x240', '--time', '0.25',
        ])
        self.assertTrue(run.call_args.kwargs.get('capture_output'))

    def test_a_requested_camera_is_resolved_here_and_handed_over(self):
        with patch.object(browser_module, 'run', return_value=self.completed) as run:
            self.renderer.capture('/tmp/staged', snapshot_args(camera='10,20,30,0,0,0'),
                                  'shot.png')
        command = run.call_args.args[0]
        self.assertIn('--view', command)
        view = command[command.index('--view') + 1]
        self.assertEqual([float(v) for v in view.split(',')], [10, 20, 30, 0, 0, 0])
        self.assertIn('--up', command)
        self.assertIn('--fov', command)
        self.assertEqual(float(command[command.index('--fov') + 1]), 22.5)

    def test_no_camera_means_no_camera_flags(self):
        with patch.object(browser_module, 'run', return_value=self.completed) as run:
            self.renderer.capture('/tmp/staged', snapshot_args(), 'shot.png')
        command = run.call_args.args[0]
        for flag in ('--view', '--up', '--fov'):
            self.assertNotIn(flag, command)

    def test_the_viewers_failure_is_reported_verbatim(self):
        failed = CompletedProcess(args=[], returncode=1, stdout='',
                                  stderr="Error: Install the browser renderer with "
                                         "`pip install 'solid-node-viewer[snapshot]'`\n")
        with patch.object(browser_module, 'run', return_value=failed):
            with self.assertRaises(BrowserSnapshotError) as raised:
                self.renderer.capture('/tmp/staged', snapshot_args(), 'shot.png')
        self.assertIn("solid-node-viewer[snapshot]", str(raised.exception))

    def test_a_missing_viewer_is_refused_before_staging(self):
        with patch.object(browser_module.viewer_bundle, 'has_bundle', return_value=False), \
             patch.object(browser_module.viewer_bundle, 'missing_bundle_remedy',
                          return_value='pip install "solid-node[viewer]"'):
            with self.assertRaises(BrowserSnapshotError) as raised:
                self.renderer.stage(Mock(), "/unused")
        self.assertIn('solid-node[viewer]', str(raised.exception))

    def test_browser_failure_never_falls_back_to_openscad(self):
        args = argparse.Namespace(
            path="model.py", output="shot.png", time=0.0, camera=None,
            autocenter=False, viewall=False, imgsize="100x100", projection=None,
            colorscheme=None, render=False, preview=False, view=None, renderer="web",
        )
        snapshot = Snapshot()
        node = Mock()
        node.__class__.__name__ = "Part"
        with (
            patch.object(snapshot, "_load_and_prepare_node", return_value=node),
            patch("solid_node.viewers.browser.BrowserRenderer.render",
                  side_effect=BrowserSnapshotError("browser missing")),
            patch("solid_node.manager.snapshot.OPENSCAD_RENDERER.render") as openscad,
        ):
            with self.assertRaises(SystemExit):
                snapshot.handle(args)
        openscad.assert_not_called()


@needs_viewer
@unittest.skipUnless(
    os.environ.get('SOLID_NODE_WEB_SNAPSHOT_E2E'),
    'set SOLID_NODE_WEB_SNAPSHOT_E2E=1 to photograph through the installed viewer',
)
class BrowserSnapshotEndToEndTest(TestCase):
    """The whole path, through the real viewer: opt-in, because it needs
    the viewer's snapshot extra and a downloaded Chromium."""

    def test_a_transparent_photograph_is_written(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            output = os.path.join(temporary, "web.png")
            Snapshot().handle(argparse.Namespace(
                path="tests/web_snapshot_project.py", time=0.0, camera=None,
                autocenter=False, viewall=False, imgsize="320x240", projection=None,
                colorscheme=None, render=False, preview=False, view=None,
                renderer="web", output=output,
            ))
            alpha = Image.open(output).convert("RGBA").getchannel("A")
            self.assertEqual(alpha.getpixel((0, 0)), 0)
            self.assertIn(255, alpha.getdata())
