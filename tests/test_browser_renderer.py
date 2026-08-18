# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import json
import os
import tempfile
import urllib.request
import argparse
import unittest
from unittest import TestCase
from unittest.mock import Mock, patch

from solid_node.viewers.browser import BrowserRenderer, BrowserSnapshotError
from solid_node.viewers.bundle import bundle_path
from solid_node.manager.snapshot import Snapshot
from tests.test_build_lock import lock_is_held
from tests.test_export import Cube
from PIL import Image

try:
    from playwright.sync_api import sync_playwright  # noqa: F401

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

HAS_BUNDLE = os.path.exists(bundle_path())
needs_bundle = unittest.skipUnless(
    HAS_BUNDLE, "widget bundle not built (npm run build)"
)


@needs_bundle
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

        self.assertEqual(
            os.stat(self.model).st_ino,
            os.stat(staged_model).st_ino,
        )
        os.remove(self.model)
        with open(staged_model, "rb") as staged:
            self.assertIn(b"solid cube", staged.read())

    def test_capture_begins_after_the_build_lock_is_released(self):
        node = self.node
        with (
            patch.object(node, "build_stls") as build,
            patch.object(self.renderer, "build_dir", return_value=self.build_dir),
            patch.object(self.renderer, "capture") as capture,
        ):
            build.side_effect = lambda: self.assertTrue(
                lock_is_held(self.build_dir)
            )
            capture.side_effect = lambda *args: self.assertFalse(
                lock_is_held(self.build_dir)
            )
            self.renderer.render(
                node,
                argparse.Namespace(
                    path="model.py", time=0.0, camera=None, imgsize="100x100"
                ),
                "shot.png",
            )

    def test_stage_is_removed_when_capture_fails(self):
        node = self.node
        with (
            patch.object(node, "build_stls"),
            patch.object(self.renderer, "build_dir", return_value=self.build_dir),
            patch.object(
                self.renderer,
                "capture",
                side_effect=RuntimeError("boom"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                self.renderer.render(
                    node,
                    argparse.Namespace(
                        path="model.py",
                        time=0.0,
                        camera=None,
                        imgsize="100x100",
                    ),
                    "shot.png",
                )
        leftovers = [
            name
            for name in os.listdir(self.temporary.name)
            if name.startswith("_build.web-snapshot.")
        ]
        self.assertEqual(leftovers, [])

    def test_server_exposes_manifest_mesh_bundle_and_mount_page(self):
        staging = self.renderer.stage(self.node, self.build_dir)
        self.addCleanup(self.renderer.remove_stage, staging)
        self.renderer.write_mount_page(
            staging, argparse.Namespace(time=0.0, camera=None)
        )
        with self.renderer.serve(staging) as url:
            for relative in (
                "viewer.json",
                "parts/cube.stl",
                "solid-widget.js",
                "index.html",
            ):
                with urllib.request.urlopen(f"{url}/{relative}") as response:
                    self.assertEqual(response.status, 200)


@needs_bundle
class PublishedBuildIsNotDisturbedTest(TestCase):
    """A snapshot is a reader: it must not republish or sweep the build.

    The published document and its artifacts belong to whatever produced
    them -- normally `solid develop`, serving the project's own root to the
    shop floor.  Photographing a subassembly must not replace that document
    with the subassembly's tree, delete the artifacts the root still needs,
    or discard a recorded build error.
    """

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
            json.dump(
                {
                    "format": "solid-node-document",
                    "version": 1,
                    "animation": {"fps": 30, "frames": 360},
                    "root": {
                        "name": "other",
                        "type": "rigid",
                        "model": "parts/other.stl",
                        "children": [],
                    },
                },
                output,
            )
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
                os.path.isfile(os.path.join(staging, "viewer.json"))
            )
            self.renderer.render(
                node,
                argparse.Namespace(
                    path="model.py", time=0.0, camera=None, imgsize="100x100"
                ),
                os.path.join(self.temporary.name, "shot.png"),
            )

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


class BrowserFailureTest(TestCase):
    def setUp(self):
        self.renderer = BrowserRenderer()

    def test_root_is_refused_without_disabling_the_sandbox(self):
        with patch("os.geteuid", return_value=0):
            with self.assertRaisesRegex(BrowserSnapshotError, "root.*sandbox"):
                self.renderer.assert_not_root()

    def test_missing_playwright_names_both_install_steps(self):
        with patch.dict(
            "sys.modules", {"playwright": None, "playwright.sync_api": None}
        ):
            with self.assertRaises(BrowserSnapshotError) as raised:
                self.renderer.playwright()
        message = str(raised.exception)
        self.assertIn("solid-node[web-snapshot]", message)
        self.assertIn("playwright install chromium", message)

    def test_missing_browser_has_actionable_install_message(self):
        browser_type = Mock()
        browser_type.launch.side_effect = Exception("Executable doesn't exist")
        with self.assertRaises(BrowserSnapshotError) as raised:
            self.renderer.launch(browser_type)
        self.assertIn("playwright install chromium", str(raised.exception))

    def test_missing_widget_bundle_reuses_the_build_remedy(self):
        with patch(
            "solid_node.viewers.browser.viewer_bundle.has_bundle",
            return_value=False,
        ):
            with self.assertRaises(BrowserSnapshotError) as raised:
                self.renderer.stage(Mock(), "/unused")
        self.assertIn("npm ci && npm run build", str(raised.exception))

    def test_browser_failure_never_falls_back_to_openscad(self):
        args = argparse.Namespace(
            path="model.py",
            output="shot.png",
            time=0.0,
            camera=None,
            autocenter=False,
            viewall=False,
            imgsize="100x100",
            projection=None,
            colorscheme=None,
            render=False,
            preview=False,
            view=None,
            renderer="web",
        )
        snapshot = Snapshot()
        node = Mock()
        node.__class__.__name__ = "Part"
        with (
            patch.object(snapshot, "_load_and_prepare_node", return_value=node),
            patch(
                "solid_node.viewers.browser.BrowserRenderer.render",
                side_effect=BrowserSnapshotError("browser missing"),
            ),
            patch("solid_node.manager.snapshot.OPENSCAD_RENDERER.render") as openscad,
        ):
            with self.assertRaises(SystemExit):
                snapshot.handle(args)
        openscad.assert_not_called()


@needs_bundle
@unittest.skipUnless(
    HAS_PLAYWRIGHT,
    'playwright not installed (pip install "solid-node[web-snapshot]" '
    "and playwright install chromium)",
)
class BrowserSnapshotEndToEndTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.web_output = os.path.join(cls.temporary.name, "web.png")
        cls.transparent_output = os.path.join(cls.temporary.name, "transparent.png")
        cls.openscad_output = os.path.join(cls.temporary.name, "openscad.png")
        cls.camera = "0,0,0,55,20,25,120"
        common = dict(
            path="tests/web_snapshot_project.py",
            time=0.0,
            camera=cls.camera,
            autocenter=False,
            viewall=False,
            imgsize="320x240",
            projection=None,
            colorscheme=None,
            render=False,
            preview=False,
            view=None,
        )
        Snapshot().handle(
            argparse.Namespace(
                **common,
                renderer="web",
                output=cls.web_output,
            )
        )
        transparent = dict(common)
        transparent["camera"] = None
        Snapshot().handle(
            argparse.Namespace(
                **transparent,
                renderer="web",
                output=cls.transparent_output,
            )
        )
        Snapshot().handle(
            argparse.Namespace(
                **common,
                renderer="openscad",
                output=cls.openscad_output,
            )
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_real_capture_has_a_transparent_border_and_opaque_model(self):
        image = Image.open(self.transparent_output).convert("RGBA")
        alpha = image.getchannel("A")
        border = (
            list(alpha.crop((0, 0, image.width, 1)).getdata())
            + list(
                alpha.crop((0, image.height - 1, image.width, image.height)).getdata()
            )
            + list(alpha.crop((0, 0, 1, image.height)).getdata())
            + list(
                alpha.crop((image.width - 1, 0, image.width, image.height)).getdata()
            )
        )
        self.assertEqual(set(border), {0})
        self.assertIn(255, alpha.getdata())

    def test_gimbal_camera_matches_openscad_silhouette(self):
        web = Image.open(self.web_output).convert("RGBA")
        openscad = Image.open(self.openscad_output).convert("RGBA")
        web_mask = {index for index, pixel in enumerate(web.getdata()) if pixel[3] > 32}
        background = openscad.getpixel((0, 0))[:3]
        openscad_mask = {
            index
            for index, pixel in enumerate(openscad.getdata())
            if max(abs(pixel[channel] - background[channel]) for channel in range(3))
            > 3
        }
        intersection_over_union = len(web_mask & openscad_mask) / len(
            web_mask | openscad_mask
        )
        self.assertGreater(
            intersection_over_union,
            0.95,
            "web/OpenSCAD silhouettes differ; check Chromium installation, "
            "OpenSCAD gimbal rotation convention, and 22.5 degree FOV",
        )
