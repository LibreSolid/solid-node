# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
import os
import tempfile
from contextlib import redirect_stdout
from unittest import TestCase
from trimesh.creation import box
from solid_node.manager.test import Test as Runner, StopTestRun
from solid_node.node.base import AbstractBaseNode
from solid_node.node.operations import Translation


def with_instants(*values):
    """Stand-in for solid_node.test.testing_steps/testing_instant: tags
    a plain function with the instants Test.run_test iterates over."""
    def decorator(method):
        method.testing_instants = list(values)
        return method
    return decorator


class FakeNode:
    """A minimal stand-in for a real Node instance, providing only what
    Test.run_class_tests/run_test touch: `children` (iterated by
    save/restore_children_checkpoints), `set_keyframe`, and plain
    `test_*` methods discovered through dir()/getattr.
    """
    children = ()

    def __init__(self):
        self.calls = []
        self.last_instant = None

    def set_keyframe(self, instant):
        self.last_instant = instant


class AlwaysPassesNode(FakeNode):
    @with_instants(0, 1, 2)
    def test_multi_instant(self):
        self.calls.append(self.last_instant)


class FirstInstantFailsNode(FakeNode):
    @with_instants(0, 1, 2)
    def test_multi_instant(self):
        self.calls.append(self.last_instant)
        if self.last_instant == 0:
            raise AssertionError("boom")


class FirstTestFailsNode(FakeNode):
    # dir() visits these in alphabetical order, so test_a_fails always
    # runs before test_b_should_not_run.
    def test_a_fails(self):
        self.calls.append('a')
        raise AssertionError("boom")

    def test_b_should_not_run(self):
        self.calls.append('b')


def run_class_tests_capturing_stdout(runner, node):
    # Only run_tests() catches StopTestRun (the signal a failfast failure
    # raises to abort the remaining run); direct run_class_tests() callers,
    # like these instants-loop-focused tests, must do so themselves.
    with redirect_stdout(io.StringIO()):
        try:
            runner.run_class_tests(node, node)
        except StopTestRun:
            pass


class FailfastInstantsLoopTest(TestCase):
    """Regression tests for B6: `if self.failfast: break` sat outside the
    `except` block, breaking the instants loop unconditionally -- even
    when the instant just passed."""

    def test_all_passing_instants_run_even_with_failfast(self):
        node = AlwaysPassesNode()
        runner = Runner()
        runner.failfast = True
        runner.test_case = None

        run_class_tests_capturing_stdout(runner, node)

        self.assertEqual(node.calls, [0, 1, 2])
        self.assertEqual(runner.num_passed, 1)
        self.assertEqual(runner.num_failed, 0)

    def test_failfast_stops_instants_loop_after_first_failure(self):
        node = FirstInstantFailsNode()
        runner = Runner()
        runner.failfast = True
        runner.test_case = None

        run_class_tests_capturing_stdout(runner, node)

        self.assertEqual(node.calls, [0])
        self.assertEqual(runner.num_failed, 1)

    def test_without_failfast_all_instants_run_despite_failure(self):
        node = FirstInstantFailsNode()
        runner = Runner()
        runner.failfast = False
        runner.test_case = None

        run_class_tests_capturing_stdout(runner, node)

        self.assertEqual(node.calls, [0, 1, 2])
        self.assertEqual(runner.num_failed, 1)


class FailfastAbortsRunTest(TestCase):
    """Regression tests for B6: --failfast's help text promises to "stop
    the test run on the first error", but the old `break` only escaped
    the instants loop, so the run continued into the next test_* method.
    """

    def test_failfast_skips_remaining_tests_after_a_failure(self):
        node = FirstTestFailsNode()
        runner = Runner()
        runner.failfast = True
        runner.test_case = None
        runner.node = node

        out = io.StringIO()
        with redirect_stdout(out):
            runner.run_tests()

        self.assertEqual(node.calls, ['a'])
        self.assertEqual(runner.num_failed, 1)
        self.assertEqual(runner.num_passed, 0)
        # The summary line must still print after an aborted run.
        self.assertIn("Ran 1 tests", out.getvalue())
        self.assertIn("1 failed", out.getvalue())

    def test_without_failfast_all_tests_run(self):
        node = FirstTestFailsNode()
        runner = Runner()
        runner.failfast = False
        runner.test_case = None
        runner.node = node

        out = io.StringIO()
        with redirect_stdout(out):
            runner.run_tests()

        self.assertEqual(node.calls, ['a', 'b'])
        self.assertEqual(runner.num_failed, 1)
        self.assertEqual(runner.num_passed, 1)
        self.assertIn("Ran 2 tests", out.getvalue())


class InstrumentedChild:
    """A minimal stand-in for a Node instance for restore_children_checkpoints:
    reuses the *real* AbstractBaseNode.save_checkpoint/restore_checkpoint and
    the real `mesh` property getter (instrumented only to count accesses),
    so the test exercises the actual checkpoint/mesh semantics rather than a
    reimplementation of them.
    """

    def __init__(self, stl_file):
        self.stl_file = stl_file
        self.operations = []
        self.checkpoint = None
        self.mesh_access_count = 0

    save_checkpoint = AbstractBaseNode.save_checkpoint
    restore_checkpoint = AbstractBaseNode.restore_checkpoint

    @property
    def mesh(self):
        self.mesh_access_count += 1
        return AbstractBaseNode.mesh.fget(self)


class FakeParent:
    def __init__(self, children):
        self.children = children


class RestoreChildrenCheckpointsTest(TestCase):
    """Regression tests for B8: restore_children_checkpoints applied
    reverted operations to `child.mesh`, but `mesh` (base.py) builds a
    brand new trimesh from disk on every access and recomputes it from
    `self.operations` -- mutating that fresh, unstored mesh is a
    discarded no-op. Restoring `operations` (which restore_checkpoint()
    already does) is sufficient.
    """

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.stl_path = os.path.join(tmpdir.name, 'child.stl')
        box((1, 1, 1)).export(self.stl_path)

    def test_restore_trims_operations_and_mesh_reflects_restored_state(self):
        child = InstrumentedChild(self.stl_path)
        child.save_checkpoint()
        child.operations.append(Translation([5, 0, 0], node=None))

        # Sanity check: the added operation actually moved the mesh.
        translated_center = list(child.mesh.center_mass)
        self.assertNotAlmostEqual(translated_center[0], 0.0)

        Runner().restore_children_checkpoints(FakeParent(children=[child]))

        self.assertEqual(child.operations, [])
        restored_center = list(child.mesh.center_mass)
        for actual in restored_center:
            self.assertAlmostEqual(actual, 0.0)

    def test_restore_does_not_access_mesh_property(self):
        # The old implementation called operation.mesh(child.mesh) once
        # per discarded operation -- an extra STL load + transform whose
        # result was thrown away immediately. Restoring should never
        # need to touch `mesh` at all.
        child = InstrumentedChild(self.stl_path)
        child.save_checkpoint()
        child.operations.append(Translation([5, 0, 0], node=None))

        Runner().restore_children_checkpoints(FakeParent(children=[child]))

        self.assertEqual(child.mesh_access_count, 0)
