# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A node's tracked source set, and the work it lets the build skip.

build-pipeline's Mtime-equality caching requires node.mtime to be the
maximum mtime "across all files tracked for the node", and that a change
to any contributing source file invalidate ancestor artifacts. A node
that tracks only its own file cannot honour that: in v8-engine both
crankshaft.py and cylinder_unit.py take their geometry from
kinematics.py, which defines no node, so editing it moves no tracked
mtime and every artifact reports up to date.

The two halves are tested together on purpose. Skipping render() is only
safe once the tracked set is right; before that, the unconditional
render is what keeps a shared-module edit correct.
"""

import os
import time
from unittest import mock

from solid2 import scad_render

from .base import BaseNodeTest
from .source_set_project import dimensions
from .source_set_project.block import Block
from .source_set_project.cyl import Cyl
from .source_set_project.jsblock import JsBlock
from .source_set_project.lonely import Lonely


PROJECT = os.path.dirname(os.path.realpath(dimensions.__file__))
DIMENSIONS = os.path.realpath(dimensions.__file__)
PACKAGE_INIT = os.path.join(PROJECT, '__init__.py')


def realpaths(node):
    return {os.path.realpath(path) for path in node.files}


def count_renders(NodeClass):
    """Patch NodeClass.render to count calls while still rendering."""
    calls = []
    original = NodeClass.render

    def counting(self):
        calls.append(self)
        return original(self)

    return calls, mock.patch.object(NodeClass, 'render', counting)


class SourceSetTest(BaseNodeTest):
    """What a node tracks."""

    def setUp(self):
        super().setUp()
        self.dimensions_times = (os.path.getatime(DIMENSIONS),
                                 os.path.getmtime(DIMENSIONS))

    def tearDown(self):
        os.utime(DIMENSIONS, self.dimensions_times)
        super().tearDown()

    def test_own_source_is_tracked(self):
        node = Cyl()
        self.assertIn(os.path.realpath(node.src), realpaths(node))

    def test_imported_project_module_is_tracked(self):
        """The defect in one line: dimensions.py decides Cyl's geometry."""
        self.assertIn(DIMENSIONS, realpaths(Cyl()))

    def test_library_modules_are_not_tracked(self):
        """Everything tracked lives inside the project. solid2, cadquery
        and solid_node itself are libraries, not project sources -- even
        when the framework's own checkout happens to sit under the
        working directory, as it does when this suite runs."""
        for path in realpaths(Cyl()):
            self.assertTrue(
                path.startswith(PROJECT + os.sep),
                f'{path} is outside the project tree but is tracked')

    def test_package_init_is_not_tracked(self):
        """The package __init__ is the root assembly's own source and
        imports every node. Python runs it to resolve Cyl's relative
        import, but following it would make every node in the project
        depend on every other one."""
        self.assertNotIn(PACKAGE_INIT, realpaths(Cyl()))

    def test_unrelated_node_is_not_invalidated(self):
        """The one-file-one-node property, stated as a test: a node that
        shares a package with Cyl but imports nothing from it tracks
        neither Cyl's source nor Cyl's dependencies."""
        files = realpaths(Lonely())
        self.assertNotIn(DIMENSIONS, files)
        self.assertNotIn(os.path.realpath(Cyl().src), files)

    def test_mtime_follows_the_imported_module(self):
        node = Cyl()
        future = time.time() + 10
        os.utime(DIMENSIONS, (future, future))
        self.assertEqual(node.mtime, os.path.getmtime(DIMENSIONS))

    def test_editing_an_imported_module_invalidates_the_artifact(self):
        """The correctness gate. A built artifact must stop reporting
        up to date once a module its geometry depends on is edited."""
        built = Block()
        built.assemble()
        self.assertTrue(built._up_to_date(built.stl_file))

        future = time.time() + 10
        os.utime(DIMENSIONS, (future, future))

        rebuilt = Block()
        self.assertFalse(rebuilt._up_to_date(rebuilt.stl_file))


class UpToDateLeafTest(BaseNodeTest):
    """What the build is allowed to skip once the set is trustworthy."""

    def test_up_to_date_leaf_is_not_rendered(self):
        Block().assemble()

        calls, patched = count_renders(Block)
        with patched:
            Block().assemble()

        self.assertEqual(calls, [], 'render() ran for an up-to-date leaf')

    def test_stale_leaf_is_rendered(self):
        """The skip must not be unconditional."""
        built = Block()
        built.assemble()
        os.remove(built.stl_file)

        calls, patched = count_renders(Block)
        with patched:
            Block().assemble()

        self.assertEqual(len(calls), 1, 'a stale leaf was not rendered')

    def test_skipped_leaf_assembles_the_same_scad(self):
        rendered = Block().assemble()
        skipped = Block().assemble()
        self.assertEqual(scad_render(skipped), scad_render(rendered))

    def test_cadquery_does_not_reexport_a_current_artifact(self):
        node = Block()
        node.assemble()

        again = Block()
        with mock.patch('cadquery.exporters.export') as export:
            scad = again.as_scad(again.render())

        export.assert_not_called()
        self.assertEqual(scad_render(scad), scad_render(node.model))

    def test_cadquery_exports_when_the_artifact_is_missing(self):
        # The stand-in still has to produce the file: the adapter
        # back-dates the STL it just wrote, and a mock that writes
        # nothing would fail this test on the missing file rather than
        # on the export.
        def export_stub(shape, path, kind):
            with open(path, 'w') as fh:
                fh.write('solid empty\nendsolid empty\n')

        node = Block()
        with mock.patch('cadquery.exporters.export',
                        side_effect=export_stub) as export:
            node.as_scad(node.render())
        export.assert_called_once()

    def test_jscad_does_not_respawn_for_a_current_artifact(self):
        node = JsBlock()
        with open(node.stl_file, 'w') as fh:
            fh.write('solid empty\nendsolid empty\n')
        os.utime(node.stl_file, (time.time(), node.mtime))

        with mock.patch('solid_node.node.adapters.jscad.Popen') as popen:
            node.as_scad(None)

        popen.assert_not_called()

    def test_jscad_runs_when_the_artifact_is_missing(self):
        node = JsBlock()
        with mock.patch('solid_node.node.adapters.jscad.Popen') as popen:
            node.as_scad(None)
        popen.assert_called_once()
