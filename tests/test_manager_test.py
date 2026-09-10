# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
import os
import tempfile
from argparse import Namespace
from contextlib import redirect_stdout, redirect_stderr
from unittest import TestCase
from unittest.mock import patch
from trimesh.creation import box
from solid_node.manager.test import Test as Runner, StopTestRun
from solid_node import test as framework
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
    base_mesh = AbstractBaseNode.base_mesh

    @property
    def mesh(self):
        self.mesh_access_count += 1
        return AbstractBaseNode.mesh.fget(self)


class FakeParent:
    def __init__(self, children):
        self.children = children


class RestoreChildrenCheckpointsTest(TestCase):
    """The runner holds its own snapshot of each child's operations
    (a test calling save_checkpoint() on a node cannot clobber the
    restore point — B9), restores by content rather than truncation,
    and never touches `mesh` while restoring (B8: mutating the fresh
    trimesh that `mesh` builds from disk was a discarded no-op).
    """

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.stl_path = os.path.join(tmpdir.name, 'child.stl')
        box((1, 1, 1)).export(self.stl_path)

    def test_restore_reverts_operations_and_mesh_reflects_restored_state(self):
        child = InstrumentedChild(self.stl_path)
        runner = Runner()
        runner.save_children_checkpoints(FakeParent(children=[child]))
        child.operations.append(Translation([5, 0, 0], node=None))

        # Sanity check: the added operation actually moved the mesh.
        translated_center = list(child.mesh.center_mass)
        self.assertNotAlmostEqual(translated_center[0], 0.0)

        runner.restore_children_checkpoints(FakeParent(children=[child]))

        self.assertEqual(child.operations, [])
        restored_center = list(child.mesh.center_mass)
        for actual in restored_center:
            self.assertAlmostEqual(actual, 0.0)

    def test_clobbered_node_checkpoint_cannot_move_the_restore_point(self):
        child = InstrumentedChild(self.stl_path)
        runner = Runner()
        runner.save_children_checkpoints(FakeParent(children=[child]))

        # A test leaks an operation and THEN calls save_checkpoint():
        # a runner trusting the node's own checkpoint index would now
        # restore to a state that includes the leak.
        child.operations.append(Translation([5, 0, 0], node=None))
        child.save_checkpoint()

        runner.restore_children_checkpoints(FakeParent(children=[child]))

        self.assertEqual(child.operations, [])

    def test_restore_reverts_inserted_operations_too(self):
        child = InstrumentedChild(self.stl_path)
        placement = Translation([1, 0, 0], node=None)
        child.operations.append(placement)
        runner = Runner()
        runner.save_children_checkpoints(FakeParent(children=[child]))

        # Perturbations are INSERTED before a placement, not appended;
        # truncating to a saved length would discard the wrong one.
        child.operations.insert(0, Translation([5, 0, 0], node=None))

        runner.restore_children_checkpoints(FakeParent(children=[child]))

        self.assertEqual(child.operations, [placement])

    def test_restore_does_not_access_mesh_property(self):
        # The B8 implementation called operation.mesh(child.mesh) once
        # per discarded operation -- an extra STL load + transform whose
        # result was thrown away immediately. Restoring should never
        # need to touch `mesh` at all.
        child = InstrumentedChild(self.stl_path)
        runner = Runner()
        runner.save_children_checkpoints(FakeParent(children=[child]))
        child.operations.append(Translation([5, 0, 0], node=None))

        runner.restore_children_checkpoints(FakeParent(children=[child]))

        self.assertEqual(child.mesh_access_count, 0)


class ResolvePathMappingTest(TestCase):
    """`solid test` is routinely handed the TEST file instead of the
    node file it exercises: `root/test_gear.py` instead of `root/gear.py`,
    or `root/test.py` instead of `root/__init__.py`. resolve_path() maps
    it back to the node file (the mirror image of loader.load_test's
    node->test mapping), so the runner proceeds exactly as if the node
    file had been given (skill-repo improvements.md #5)."""

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.dir = tmpdir.name

    def touch(self, name):
        path = os.path.join(self.dir, name)
        open(path, 'w').close()
        return path

    def test_maps_test_prefixed_file_to_its_node_file(self):
        self.touch('gear.py')
        test_path = self.touch('test_gear.py')
        runner = Runner()

        self.assertEqual(
            runner.resolve_path(test_path),
            os.path.join(self.dir, 'gear.py'),
        )

    def test_maps_bare_test_file_to_init_file(self):
        self.touch('__init__.py')
        test_path = self.touch('test.py')
        runner = Runner()

        self.assertEqual(
            runner.resolve_path(test_path),
            os.path.join(self.dir, '__init__.py'),
        )

    def test_ordinary_node_path_passes_through_unchanged(self):
        node_path = self.touch('gear.py')
        runner = Runner()

        self.assertEqual(runner.resolve_path(node_path), node_path)

    def test_missing_mapped_node_file_exits_with_clear_error(self):
        # test_gear.py exists, but its sibling gear.py does not.
        test_path = self.touch('test_gear.py')
        expected_node_path = os.path.join(self.dir, 'gear.py')
        runner = Runner()

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                runner.resolve_path(test_path)

        self.assertEqual(ctx.exception.code, 1)
        message = stderr.getvalue()
        self.assertIn(expected_node_path, message)
        # A single clear line, never a bare TypeError traceback.
        self.assertNotIn('Traceback', message)

    def test_missing_mapped_init_file_exits_with_clear_error(self):
        test_path = self.touch('test.py')
        expected_node_path = os.path.join(self.dir, '__init__.py')
        runner = Runner()

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                runner.resolve_path(test_path)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(expected_node_path, stderr.getvalue())


class NoNodeClassInModuleTest(TestCase):
    """A module with no AbstractBaseNode subclass defined in it -- the
    case when a stray file, or (before this fix) a TEST file, is handed
    to `solid test` -- must fail with a clear one-line error instead of
    the opaque `TypeError: 'NoneType' object is not callable` that
    calling the loader's None straight away used to produce."""

    def setUp(self):
        fixture_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'meta_project')
        fd, self.path = tempfile.mkstemp(
            suffix='.py', prefix='no_node_class_', dir=fixture_dir)
        os.close(fd)
        with open(self.path, 'w') as f:
            f.write("# fixture: deliberately defines no node class\n"
                     "VALUE = 1\n")
        self.addCleanup(os.remove, self.path)
        self.relative_path = os.path.relpath(self.path)

    def test_build_node_fails_clearly_instead_of_crashing(self):
        runner = Runner()

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                runner.build_node(self.relative_path)

        self.assertEqual(ctx.exception.code, 1)
        message = stderr.getvalue()
        self.assertIn(self.relative_path, message)
        self.assertNotIn('Traceback', message)


class MultiTestCaseFixture(TestCase):
    """Shared scratch-project setup for the companion TestCase binding
    tests below (tasks 4.1-4.3): a real, tiny, temp-dir project with its
    own manifest, built and rendered through openscad exactly as `solid
    test` runs a maker's project -- not stubbed, because binding is
    decided by real class identity (`declared is klass`) and a mock node
    cannot stand in for that."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        os.mkdir(os.path.join(self.root, 'boat'))
        open(os.path.join(self.root, 'boat', '__init__.py'), 'w').close()
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as stream:
            stream.write(
                '[tool.solid-node]\nmodel = "boat.windmill:Windmill"\n')
        # Other test modules in this suite set SOLID_BUILD_DIR at import
        # time (some to an absolute path elsewhere in the repo); a build
        # driven from this scratch project must publish into ITS OWN
        # _build, not one left behind by an unrelated module.
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('SOLID_BUILD_DIR', None)

    def write(self, relative, content):
        path = os.path.join(self.root, relative)
        with open(path, 'w') as stream:
            stream.write(content)
        return path

    def run_solid_test(self, path, failfast=False):
        """Drive Runner().handle() exactly as the CLI does, capturing
        stdout/stderr and turning a raised SystemExit into (code, out,
        err) instead of letting it propagate -- a passing run never
        calls sys.exit, so code is 0 in that case."""
        stdout, stderr = io.StringIO(), io.StringIO()
        args = Namespace(path=path, failfast=failfast)
        code = 0
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                Runner().handle(args)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()


WINDMILL_SOURCE = '''from solid_node.node import Solid2Node
from solid2 import cube


class Windmill(Solid2Node):
    def render(self):
        return cube(1, center=True)


class Sail(Solid2Node):
    def render(self):
        return cube(1, center=True)
'''

WINDMILL_TEST_SOURCE = '''from solid_node.test import TestCase
from .windmill import Windmill, Sail


class WindmillTest(TestCase):
    node = Windmill

    def test_windmill_builds(self):
        self.assertIsNotNone(self.node.mesh)


class SailTest(TestCase):
    node = Sail

    def test_sail_builds(self):
        self.assertIsNotNone(self.node.mesh)
'''


class CompanionMultipleTestCasesRunTest(MultiTestCaseFixture):
    """Task 4.1, and the spec's 'Several test cases in one companion
    file' scenario: before this cycle the loader returned only the
    first TestCase defined in a companion file (`candidates[0][1]`) --
    a second TestCase in the same file never ran, and the run still
    reported success. The proposal's own words: a silently unrun test
    is worse than a wrongly loaded node, because the wrong node is at
    least visible on screen and the missing test is visible nowhere.
    Each TestCase here declares the node it exercises, and both must
    run, each bound to the one it declared."""

    def test_both_test_cases_in_the_companion_file_run(self):
        node_path = self.write('boat/windmill.py', WINDMILL_SOURCE)
        self.write('boat/test_windmill.py', WINDMILL_TEST_SOURCE)

        code, stdout, stderr = self.run_solid_test(node_path)

        self.assertEqual(code, 0, stderr)
        self.assertIn('WindmillTest.test_windmill_builds', stdout)
        self.assertIn('SailTest.test_sail_builds', stdout)
        self.assertIn('Ran 2 tests', stdout)
        self.assertIn('2 passed, 0 failed', stdout)


HULL_SOURCE = '''from solid_node.node import Solid2Node
from solid2 import cube


class Hull(Solid2Node):
    def render(self):
        return cube(1, center=True)


class Deck(Solid2Node):
    def render(self):
        return cube(1, center=True)
'''

HULL_TEST_UNDECLARED_SOURCE = '''from solid_node.test import TestCase


class HullTest(TestCase):
    def test_never_runs(self):
        pass
'''


class UndeclaredTestCaseInMultiNodeModuleTest(MultiTestCaseFixture):
    """Task 4.2, failure branch: a TestCase with no `node = <Class>`
    declaration, next to a module defining several node classes, has no
    way to say which one it binds to. The run must fail loudly, naming
    the test case and every candidate node class -- never silently
    skip it and never silently guess one."""

    def test_undeclared_case_fails_the_run_naming_case_and_candidates(self):
        node_path = self.write('boat/hull.py', HULL_SOURCE)
        self.write('boat/test_hull.py', HULL_TEST_UNDECLARED_SOURCE)

        code, stdout, stderr = self.run_solid_test(node_path)

        self.assertEqual(code, 1)
        self.assertIn('HullTest', stderr)
        self.assertIn('Hull', stderr)
        self.assertIn('Deck', stderr)
        self.assertIn('must declare node', stderr)
        # Never silently skipped: the run must abort before any summary
        # -- in particular never a summary claiming everything passed.
        self.assertNotIn('passed', stdout)


MAST_SOURCE = '''from solid_node.node import Solid2Node
from solid2 import cube


class Mast(Solid2Node):
    def render(self):
        return cube(1, center=True)
'''

MAST_TEST_SOURCE = '''from solid_node.test import TestCase


class MastTest(TestCase):
    def test_mast_builds(self):
        self.assertIsNotNone(self.node.mesh)
        # The snake_case alias TestCase.set_node derives from the class
        # name is unaffected by whether `node` was declared or implied.
        self.assertIsNotNone(self.mast.mesh)
'''


class UndeclaredTestCaseBesideSingleNodeModuleTest(MultiTestCaseFixture):
    """Task 4.3: every project that predates this cycle has exactly one
    node class per test file and never declared `node = ...` -- that
    majority case must keep working unchanged. An undeclared TestCase
    beside a single-node module binds to that module's one node class
    implicitly, with no error and no behaviour change."""

    def test_undeclared_case_still_binds_and_runs(self):
        node_path = self.write('boat/mast.py', MAST_SOURCE)
        self.write('boat/test_mast.py', MAST_TEST_SOURCE)

        code, stdout, stderr = self.run_solid_test(node_path)

        self.assertEqual(code, 0, stderr)
        self.assertIn('MastTest.test_mast_builds', stdout)
        self.assertIn('Ran 1 tests', stdout)
        self.assertIn('1 passed, 0 failed', stdout)


class ComparisonKernelSelectionTest(TestCase):
    """The kernel a run compares on is a property of the run, resolved
    once from the flags, then the environment, then the exact default --
    and refused loudly when the pieces do not fit together."""

    def tearDown(self):
        framework.set_comparison_policy(None)

    def parser(self):
        import argparse
        parser = argparse.ArgumentParser()
        Runner().add_arguments(parser)
        return parser

    def test_exact_and_faceted_are_mutually_exclusive(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parser().parse_args(['--exact', '--faceted'])

    def test_flags_parse_into_a_kernel_and_an_epsilon(self):
        args = self.parser().parse_args(['--faceted', '--volume-epsilon', '0.5'])
        self.assertEqual((args.kernel, args.volume_epsilon), ('faceted', 0.5))
        args = self.parser().parse_args([])
        self.assertEqual((args.kernel, args.volume_epsilon), (None, None))

    def test_the_default_is_the_exact_kernel(self):
        policy = framework.resolve_comparison_policy(environ={})
        self.assertEqual(policy, ('exact', 0.0,
                                  framework.DEFAULT_PLACEMENT_QUANTUM))

    def test_faceted_without_an_epsilon_is_strict(self):
        policy = framework.resolve_comparison_policy('faceted', environ={})
        self.assertEqual(policy, ('faceted', 0.0,
                                  framework.DEFAULT_PLACEMENT_QUANTUM))

    def test_the_environment_selects_the_faceted_kernel(self):
        policy = framework.resolve_comparison_policy(
            environ={'SOLID_TEST_KERNEL': 'faceted',
                     'SOLID_TEST_VOLUME_EPSILON': '0.25'})
        self.assertEqual(policy, ('faceted', 0.25,
                                  framework.DEFAULT_PLACEMENT_QUANTUM))

    def test_a_flag_beats_the_environment(self):
        policy = framework.resolve_comparison_policy(
            'exact', environ={'SOLID_TEST_KERNEL': 'faceted',
                              'SOLID_TEST_VOLUME_EPSILON': '0.25'})
        self.assertEqual(policy, ('exact', 0.0,
                                  framework.DEFAULT_PLACEMENT_QUANTUM))

    def test_an_unknown_kernel_name_is_refused_naming_the_variable(self):
        with self.assertRaisesRegex(
                ValueError, r"SOLID_TEST_KERNEL.*'exact'.*'faceted'.*fast"):
            framework.resolve_comparison_policy(
                environ={'SOLID_TEST_KERNEL': 'fast'})

    def test_a_negative_epsilon_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'negative'):
            framework.resolve_comparison_policy(
                'faceted', -1.0, environ={})
        with self.assertRaisesRegex(ValueError, 'negative'):
            framework.resolve_comparison_policy(
                environ={'SOLID_TEST_KERNEL': 'faceted',
                         'SOLID_TEST_VOLUME_EPSILON': '-2'})

    def test_a_non_numeric_environment_epsilon_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'SOLID_TEST_VOLUME_EPSILON'):
            framework.resolve_comparison_policy(
                'faceted', environ={'SOLID_TEST_VOLUME_EPSILON': 'tiny'})

    def test_an_epsilon_offered_to_the_exact_kernel_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'nothing.*absorb'):
            framework.resolve_comparison_policy('exact', 0.5, environ={})
        with self.assertRaisesRegex(ValueError, 'nothing.*absorb'):
            framework.resolve_comparison_policy(None, 0.5, environ={})

    def test_the_environment_epsilon_is_not_read_by_the_exact_kernel(self):
        policy = framework.resolve_comparison_policy(
            environ={'SOLID_TEST_VOLUME_EPSILON': 'tiny'})
        self.assertEqual(policy, ('exact', 0.0,
                                  framework.DEFAULT_PLACEMENT_QUANTUM))

    def test_a_two_argument_construction_means_the_default_quantum(self):
        # The seven positional two-argument ComparisonPolicy(...) sites in
        # solid_node/test.py, solid_node/manager/test.py and this repo's
        # own tests are none of them edited to pass a quantum (design.md
        # §6); this is what makes that mean "at the default quantum".
        self.assertEqual(
            framework.ComparisonPolicy('exact', 0.0).placement_quantum,
            framework.DEFAULT_PLACEMENT_QUANTUM)

    def test_the_placement_quantum_flag_parses(self):
        args = self.parser().parse_args(['--placement-quantum', '1e-6'])
        self.assertEqual(args.placement_quantum, 1e-6)
        args = self.parser().parse_args([])
        self.assertIsNone(args.placement_quantum)

    def test_the_placement_quantum_is_not_in_the_kernel_group(self):
        args = self.parser().parse_args(
            ['--exact', '--placement-quantum', '1e-6'])
        self.assertEqual((args.kernel, args.placement_quantum),
                         ('exact', 1e-6))

    def test_the_default_placement_quantum(self):
        policy = framework.resolve_comparison_policy(environ={})
        self.assertEqual(policy.placement_quantum,
                         framework.DEFAULT_PLACEMENT_QUANTUM)

    def test_the_environment_selects_a_placement_quantum(self):
        policy = framework.resolve_comparison_policy(
            environ={'SOLID_TEST_PLACEMENT_QUANTUM': '1e-6'})
        self.assertEqual(policy.placement_quantum, 1e-6)

    def test_a_placement_quantum_flag_beats_the_environment(self):
        policy = framework.resolve_comparison_policy(
            placement_quantum=0,
            environ={'SOLID_TEST_PLACEMENT_QUANTUM': '1e-6'})
        self.assertEqual(policy.placement_quantum, 0.0)

    def test_a_zero_placement_quantum_is_the_exact_bytes_key(self):
        policy = framework.resolve_comparison_policy(
            placement_quantum=0, environ={})
        self.assertEqual(policy.placement_quantum, 0.0)

    def test_the_exact_kernel_accepts_a_placement_quantum(self):
        # Unlike --volume-epsilon, refused by the exact kernel.
        policy = framework.resolve_comparison_policy(
            'exact', placement_quantum=1e-6, environ={})
        self.assertEqual(policy, ('exact', 0.0, 1e-6))

    def test_the_environment_quantum_is_read_under_both_kernels(self):
        exact_policy = framework.resolve_comparison_policy(
            environ={'SOLID_TEST_PLACEMENT_QUANTUM': '1e-6'})
        faceted_policy = framework.resolve_comparison_policy(
            'faceted', environ={'SOLID_TEST_PLACEMENT_QUANTUM': '1e-6'})
        self.assertEqual(exact_policy.placement_quantum, 1e-6)
        self.assertEqual(faceted_policy.placement_quantum, 1e-6)

    def test_a_negative_placement_quantum_is_refused(self):
        # Unlike the epsilon's negative-value error, the spec requires
        # this one to name the flag or the variable that supplied the
        # value (design.md Sec 3 "Errors").
        with self.assertRaisesRegex(ValueError,
                                    r'--placement-quantum.*negative'):
            framework.resolve_comparison_policy(
                placement_quantum=-1.0, environ={})
        with self.assertRaisesRegex(
                ValueError, r'SOLID_TEST_PLACEMENT_QUANTUM.*negative'):
            framework.resolve_comparison_policy(
                environ={'SOLID_TEST_PLACEMENT_QUANTUM': '-1'})

    def test_a_non_finite_placement_quantum_is_refused(self):
        # inf collapses every relative matrix to the same all-zero cell
        # (one verdict served for every pair in the run); nan reaches
        # astype(np.int64) undefined. Both parse as valid floats, so
        # resolve_comparison_policy must check finiteness itself.
        with self.assertRaisesRegex(ValueError,
                                    r'--placement-quantum.*finite'):
            framework.resolve_comparison_policy(
                placement_quantum=float('inf'), environ={})
        with self.assertRaisesRegex(ValueError,
                                    r'--placement-quantum.*finite'):
            framework.resolve_comparison_policy(
                placement_quantum=float('nan'), environ={})
        with self.assertRaisesRegex(
                ValueError, r'SOLID_TEST_PLACEMENT_QUANTUM.*finite'):
            framework.resolve_comparison_policy(
                environ={'SOLID_TEST_PLACEMENT_QUANTUM': 'inf'})
        with self.assertRaisesRegex(
                ValueError, r'SOLID_TEST_PLACEMENT_QUANTUM.*finite'):
            framework.resolve_comparison_policy(
                environ={'SOLID_TEST_PLACEMENT_QUANTUM': 'nan'})

    def test_a_non_numeric_environment_quantum_is_refused(self):
        with self.assertRaisesRegex(
                ValueError, r'SOLID_TEST_PLACEMENT_QUANTUM.*length.*mm'):
            framework.resolve_comparison_policy(
                environ={'SOLID_TEST_PLACEMENT_QUANTUM': 'tight'})

    def test_an_empty_environment_quantum_means_unset(self):
        # Matches the kernel's and epsilon's siblings: environ.get(...)
        # or default, so a blank line in .env is unset, not an error.
        policy = framework.resolve_comparison_policy(
            environ={'SOLID_TEST_PLACEMENT_QUANTUM': ''})
        self.assertEqual(policy.placement_quantum,
                         framework.DEFAULT_PLACEMENT_QUANTUM)

    def test_the_runner_refuses_before_building_anything(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        args = Namespace(path='whatever.py', failfast=False,
                         kernel=None, volume_epsilon=0.5)
        with patch.object(Runner, 'build_node',
                          side_effect=AssertionError('must not build')):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as stop:
                    Runner().handle(args)
        self.assertEqual(stop.exception.code, 1)
        self.assertIn('nothing', stderr.getvalue())
        self.assertIn('absorb', stderr.getvalue())

    def test_the_framework_resolves_lazily_from_the_environment(self):
        framework.set_comparison_policy(None)
        with patch.dict(os.environ, {'SOLID_TEST_KERNEL': 'faceted',
                                     'SOLID_TEST_VOLUME_EPSILON': '0.5'}):
            self.assertEqual(framework.comparison_policy(),
                             ('faceted', 0.5,
                              framework.DEFAULT_PLACEMENT_QUANTUM))
        # Resolved once: the environment changing afterwards does not
        # move a run that has already chosen.
        with patch.dict(os.environ, {'SOLID_TEST_KERNEL': 'exact'}):
            self.assertEqual(framework.comparison_policy().kernel, 'faceted')

    def test_the_runner_sets_the_policy_it_resolved(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        args = Namespace(path='whatever.py', failfast=False,
                         kernel='faceted', volume_epsilon=0.5)
        seen = {}

        def record(path):
            seen['policy'] = framework.comparison_policy()
            raise SystemExit(0)

        # The reference is resolved before any build; stopping there is
        # enough to see the policy already in force and announced.
        with patch('solid_node.manager.test.resolve_node', record):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    Runner().handle(args)
        self.assertEqual(seen['policy'], ('faceted', 0.5,
                                          framework.DEFAULT_PLACEMENT_QUANTUM))
        self.assertIn('faceted kernel', stdout.getvalue())
        self.assertIn('0.5', stdout.getvalue())

    def test_an_exact_run_announces_nothing(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        args = Namespace(path='whatever.py', failfast=False,
                         kernel=None, volume_epsilon=None)
        with patch('solid_node.manager.test.resolve_node',
                   side_effect=SystemExit(0)):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    Runner().handle(args)
        self.assertEqual(stdout.getvalue(), '')

    def test_the_summary_line_names_a_faceted_run(self):
        runner = Runner()
        runner.policy = framework.ComparisonPolicy('faceted', 0.5)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.report(1.0)
        self.assertRegex(
            stdout.getvalue(),
            r'Ran 0 tests in 1\.00 seconds: 0 passed, 0 failed '
            r'\(faceted kernel, volume epsilon 0\.5 mm³\)')

    def test_the_summary_line_of_an_exact_run_is_unchanged(self):
        runner = Runner()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.report(1.0)
        self.assertEqual(
            stdout.getvalue(),
            '\nRan 0 tests in 1.00 seconds: 0 passed, 0 failed\n')

    def test_the_summary_line_is_unchanged_at_the_default_quantum(self):
        runner = Runner()
        runner.policy = framework.ComparisonPolicy('exact', 0.0)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.report(1.0)
        self.assertEqual(
            stdout.getvalue(),
            '\nRan 0 tests in 1.00 seconds: 0 passed, 0 failed\n')

    def test_the_summary_line_names_a_non_default_quantum(self):
        runner = Runner()
        runner.policy = framework.ComparisonPolicy('exact', 0.0, 1e-06)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.report(1.0)
        self.assertRegex(
            stdout.getvalue(),
            r'Ran 0 tests in 1\.00 seconds: 0 passed, 0 failed '
            r'\(placement quantum 1e-06 mm\)')

    def test_the_summary_line_names_the_quantum_beside_the_faceted_label(self):
        runner = Runner()
        runner.policy = framework.ComparisonPolicy('faceted', 0.5, 1e-06)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            runner.report(1.0)
        self.assertRegex(
            stdout.getvalue(),
            r'Ran 0 tests in 1\.00 seconds: 0 passed, 0 failed '
            r'\(faceted kernel, volume epsilon 0\.5 mm³, '
            r'placement quantum 1e-06 mm\)')


ROBOT_SOURCE = '''from solid_node.node import Solid2Node
from solid2 import cube


class Keel(Solid2Node):
    """A sub-assembly that only its parent can build."""

    def render(self):
        raise RuntimeError('keel needs its boat')


class Boat(Solid2Node):
    def render(self):
        return cube(1, center=True)
'''

ROBOT_TEST_SOURCE = '''from solid_node.test import TestCase
from boat.robot import Boat


class BoatTest(TestCase):
    node = Boat

    def test_boat_builds(self):
        self.assertIsNotNone(self.node.mesh)
'''


class BareFileCoversDeclaredClassesTest(MultiTestCaseFixture):
    """A bare file reference covers the node classes its companion
    declares and no other: a sub-assembly nobody tests, that cannot be
    built alone, is never built. openvmp's robot.py is the origin --
    a machine and five sub-assemblies whose ports the machine binds."""

    def test_an_undeclared_sub_assembly_is_not_built(self):
        node_path = self.write('boat/robot.py', ROBOT_SOURCE)
        self.write('boat/test_robot.py', ROBOT_TEST_SOURCE)

        code, stdout, stderr = self.run_solid_test(node_path)

        self.assertEqual(code, 0, stderr)
        self.assertNotIn('keel needs its boat', stderr)
        self.assertIn('BoatTest.test_boat_builds', stdout)
        self.assertIn('Ran 1 tests', stdout)

    def test_a_file_with_no_companion_builds_every_class(self):
        node_path = self.write('boat/hull.py', HULL_SOURCE)

        code, stdout, stderr = self.run_solid_test(node_path)

        self.assertEqual(code, 0, stderr)
        self.assertIn('Ran 0 tests', stdout)
