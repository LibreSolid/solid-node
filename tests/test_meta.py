# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Meta-tests: run `solid test` end-to-end on the fixture projects in
tests/meta_project/ and assert the runner reports each deliberately
green test as passing and each deliberately red test as failing, for
the right reason.

This is the layer the unit tests structurally cannot cover: they drive
the runner with fake nodes, stubbing out the render/keyframe/mesh
machinery. Here real nodes are built (real STLs, real meshes) and the
whole pipeline — CLI, loader, builder, runner, assertions — must
transmit the true color of each contract.
"""

import os
import re
import subprocess
import sys
from unittest import TestCase

BASEDIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BASEDIR)
BUILD_DIR = os.path.join(BASEDIR, '_build_meta')

ANSI = re.compile(r'\x1b\[[0-9;]*m')
RESULT = re.compile(r'^Running \S+?\.(?P<name>test_\w+)', re.MULTILINE)
SUMMARY = re.compile(
    r'Ran (?P<total>\d+) tests in [\d.]+ seconds: '
    r'(?P<passed>\d+) passed, (?P<failed>\d+) failed')


class SolidTestRun:
    """The parsed outcome of one `solid test` subprocess."""

    def __init__(self, proc):
        self.returncode = proc.returncode
        self.stdout = ANSI.sub('', proc.stdout)
        self.stderr = proc.stderr

        self.results = {}
        for line in self.stdout.splitlines():
            match = RESULT.match(line)
            if not match:
                continue
            name = match.group('name')
            self.results[name] = 'failed' if 'FAIL!' in line else 'passed'

        summary = SUMMARY.search(self.stdout)
        if not summary:
            raise AssertionError(
                f"solid test printed no summary line.\n"
                f"stdout:\n{self.stdout}\nstderr:\n{self.stderr}")
        self.total = int(summary.group('total'))
        self.passed = int(summary.group('passed'))
        self.failed = int(summary.group('failed'))


_runs = {}

def solid_test(fixture):
    """Run `solid test` on tests/meta_project/<fixture>.py (cached:
    each fixture project runs at most once per meta-test session)."""
    if fixture not in _runs:
        _runs[fixture] = SolidTestRun(
            run_solid_test_path(f'tests/meta_project/{fixture}.py'))
    return _runs[fixture]


def solid_test_at_path(path):
    """Run `solid test <path>` on an arbitrary path (uncached, not
    parsed): for asserting on a path string that isn't a `<fixture>.py`
    node file, e.g. the fixture's TEST path or a deliberately bogus
    one -- both may exit before printing a summary line, which
    SolidTestRun requires."""
    return run_solid_test_path(path)


def run_solid_test_path(path):
    env = dict(os.environ, SOLID_BUILD_DIR=BUILD_DIR)
    return subprocess.run(
        [sys.executable, '-c',
         'from solid_node.cli import manage; manage()',
         'test', path],
        cwd=REPO_DIR, env=env,
        capture_output=True, text=True, timeout=300,
    )


class GreenProjectMetaTest(TestCase):
    """A project whose contracts genuinely hold must come out all
    green: right test names, right counts, exit code 0."""

    def test_all_tests_pass(self):
        run = solid_test('apart')
        self.assertEqual(run.results, {
            'test_cubes_do_not_intersect': 'passed',
            'test_placed_cube_is_where_placed': 'passed',
        })
        self.assertEqual((run.total, run.passed, run.failed), (2, 2, 0))
        self.assertEqual(run.returncode, 0)


class KeyframeIdempotencyMetaTest(TestCase):
    """Bug: AssemblyNode.set_keyframe re-renders without undoing the
    previous render's operations, so kinematic operations accumulate
    across the instants of a multi-instant test (improvements.md #1)."""

    def test_absolute_kinematics_hold_at_every_instant(self):
        run = solid_test('slider')
        self.assertEqual(run.results,
                         {'test_cube_at_absolute_position': 'passed'})
        self.assertEqual(run.returncode, 0)

    def test_accumulation_cannot_mask_a_real_collision(self):
        run = solid_test('collider')
        self.assertEqual(run.results,
                         {'test_slider_never_hits_obstacle': 'failed'})
        self.assertIn('should not intersect', run.stdout)
        self.assertNotEqual(run.returncode, 0)


class KeyframePropagationMetaTest(TestCase):
    """Bug: set_keyframe did not propagate to nested assemblies, so a
    child assembly of the node under test kept symbolic time and its
    children's meshes were unusable (improvements.md #2)."""

    def test_nested_assembly_children_get_numeric_time(self):
        run = solid_test('nested')
        self.assertEqual(run.results,
                         {'test_nested_cube_moves_with_time': 'passed'})
        self.assertEqual(run.returncode, 0)


class MeshCompositionMetaTest(TestCase):
    """Bug: node.mesh applied only the node's own operations, so any
    placement living on an ancestor assembly was invisible to mesh
    tests — they passed trivially with intersection volume 0
    (improvements.md #10)."""

    def test_wrapper_placement_reaches_leaf_meshes(self):
        run = solid_test('wrapped')
        self.assertEqual(run.results, {
            'test_leaf_mesh_is_at_world_position': 'passed',
            'test_wrapper_placement_separates_the_parts': 'passed',
        })
        self.assertEqual(run.returncode, 0)

    def test_local_meshes_cannot_mask_a_world_overlap(self):
        run = solid_test('wrapped_overlap')
        self.assertEqual(run.results,
                         {'test_wrapped_leaf_clears_reference': 'failed'})
        self.assertIn('should not intersect', run.stdout)
        self.assertNotEqual(run.returncode, 0)


class RunnerIsolationMetaTest(TestCase):
    """Bug: the runner restored child state once per test (not per
    instant), by truncating to a checkpoint index stored ON the node —
    so a leaked operation poisoned the remaining instants, and a test
    calling save_checkpoint() clobbered the runner's restore point
    (improvements.md #9)."""

    def test_leaks_and_clobbers_never_poison_later_assertions(self):
        run = solid_test('leaky')
        self.assertEqual(run.results, {
            'test_a_leaks_and_clobbers_checkpoint': 'passed',
            'test_b_starts_clean_after_leaky_test': 'passed',
            'test_c_each_instant_starts_clean': 'passed',
        })
        self.assertEqual(run.returncode, 0)


class MultiDriverMetaTest(TestCase):
    """Bug: two independent assemblies driving the SAME node instance
    (a wheel steered by one assembly, spun by its child axle assembly —
    legitimate, e.g. a car's front wheel) corrupted each other's
    kinematics under the snapshot-baseline restore: the SECOND
    assembly to ever touch the node captured the FIRST assembly's
    freshly appended operation as its own restore baseline, and froze
    it there forever (skill-repo improvements.md #18)."""

    def test_wheel_tracks_both_drivers(self):
        run = solid_test('steered_wheel')
        self.assertEqual(run.results,
                         {'test_wheel_tracks_both_drivers': 'passed'})
        self.assertEqual(run.returncode, 0)

    def test_stale_driver_cannot_mask_a_real_collision(self):
        run = solid_test('steered_collision')
        self.assertEqual(run.results,
                         {'test_wheel_never_hits_obstacle': 'failed'})
        self.assertIn('should not intersect', run.stdout)
        self.assertNotEqual(run.returncode, 0)


class UniqIdKeyMetaTest(TestCase):
    """Bug (skill-repo improvements.md #3 + #13): name= used to REPLACE
    the parameter-based artifact key, and raw kwargs serialized verbatim
    into the filename. The same-name/different-parameters lie is
    covered at build level in tests/test_uniq_id.py (same-name siblings
    collide in the viewer tree, a separate open issue, #16) rather than
    here; these two cover the twin adversarial-green cases that ARE
    straightforward as meta fixtures."""

    def test_distinctly_named_cubes_get_correct_independent_geometry(self):
        run = solid_test('named_sizes')
        self.assertEqual(
            run.results,
            {'test_distinctly_named_cubes_get_correct_independent_geometry':
                'passed'})
        self.assertEqual((run.total, run.passed, run.failed), (1, 1, 0))
        self.assertEqual(run.returncode, 0)

    def test_leaf_with_long_list_parameter_builds(self):
        run = solid_test('long_params')
        self.assertEqual(run.results, {'test_mesh_exists': 'passed'})
        self.assertEqual((run.total, run.passed, run.failed), (1, 1, 0))
        self.assertEqual(run.returncode, 0)


class ChildNamingMetaTest(TestCase):
    """Green fixture for child-name derivation (skill-repo
    improvements.md #16): a child's node.name comes from the
    attribute the parent instance holds it under -- not always the
    class name -- so two same-class children (`left`/`right`) and a
    list attribute (`posts`) never collide in the viewer's
    name-addressed tree."""

    def test_children_named_after_holding_attribute(self):
        run = solid_test('garage')
        self.assertEqual(
            run.results,
            {'test_children_get_attribute_derived_names': 'passed'})
        self.assertEqual((run.total, run.passed, run.failed), (1, 1, 0))
        self.assertEqual(run.returncode, 0)


class RedProjectMetaTest(TestCase):
    """A project with a genuinely violated contract must come out red,
    and red for the right reason: the mesh assertion itself — not an
    ImportError, not a vacuous pass."""

    def test_violated_contract_is_reported_as_failure(self):
        run = solid_test('overlapping')
        self.assertEqual(run.results,
                         {'test_overlapping_cubes_reported': 'failed'})
        self.assertEqual((run.total, run.passed, run.failed), (1, 0, 1))
        self.assertIn('AssertionError', run.stdout)
        self.assertIn('should not intersect', run.stdout)

    def test_failures_set_a_nonzero_exit_code(self):
        """CI and agents branch on the exit code; a red run that exits
        0 reads as green to everything downstream."""
        run = solid_test('overlapping')
        self.assertNotEqual(run.returncode, 0)


class PerturbationAssertionsMetaTest(TestCase):
    """assertBlockedBeyond/assertFreeWithin (issue #6): a genuine
    torque fit (square peg, square pocket, ~13deg of play) must come
    out blocked well beyond its play and free well within it, in both
    signed directions. A gamed fit -- an oversized pocket that never
    truly touches the peg -- must not be able to pass as blocked: the
    anti-gaming guarantee."""

    def test_genuine_fit_blocked_beyond_and_free_within_play(self):
        run = solid_test('keyed')
        self.assertEqual(run.results, {
            'test_peg_blocked_beyond_play': 'passed',
            'test_peg_free_within_play': 'passed',
        })
        self.assertEqual((run.total, run.passed, run.failed), (2, 2, 0))
        self.assertEqual(run.returncode, 0)

    def test_gamed_fit_cannot_pass_the_blocked_beyond_contract(self):
        run = solid_test('keyed_loose')
        self.assertEqual(run.results, {
            'test_peg_blocked_beyond_play': 'failed',
            'test_peg_free_within_play': 'passed',
        })
        self.assertIn('should be blocked', run.stdout)
        self.assertIn('no intersection', run.stdout)
        self.assertNotEqual(run.returncode, 0)


class PairwiseAdjacencyMetaTest(TestCase):
    """assertNoPairwiseIntersections (issue #11): every pair of leaves
    under the assembled tree, recursing through nested child
    assemblies -- not just a node's direct children -- must be
    non-intersecting."""

    def test_all_separated_leaves_pass(self):
        run = solid_test('separated')
        self.assertEqual(run.results,
                         {'test_no_pairwise_intersections': 'passed'})
        self.assertEqual(run.returncode, 0)

    def test_nonadjacent_overlap_is_reported_naming_both_leaves(self):
        # Under the OLD always-class-name naming, this asserted 'LegA'
        # and 'LegC' (the fixture's helper subclasses, defined only to
        # get a distinct node.name per leaf -- see separated_overlap.py).
        # Under the ratified derivation (skill-repo improvements.md
        # #16), node.name instead comes from the attribute the parent
        # holds the child under: SeparatedOverlap.a -> 'a', and
        # OverlappingPair.c -> 'c'. The fixture itself still holds
        # (its contract is unchanged, just its failure message's
        # vocabulary), so only this expectation moves.
        run = solid_test('separated_overlap')
        self.assertEqual(run.results,
                         {'test_no_pairwise_intersections': 'failed'})
        self.assertIn('a should not intersect c', run.stdout)
        self.assertNotEqual(run.returncode, 0)


class TestPathMetaTest(TestCase):
    """Bug: `solid test` habitually gets handed the TEST file rather
    than the node file it exercises (root/test_gear.py instead of
    root/gear.py) -- the loader finds no node class in the test
    module, load_instance returns None, and the runner called it,
    raising a bare `TypeError: 'NoneType' object is not callable'
    (skill-repo improvements.md #5). Passing the TEST path must behave
    exactly like passing the node path, and a path that maps to a
    node file that doesn't exist must fail with a clear message."""

    def test_test_path_produces_identical_results_to_node_path(self):
        node_run = solid_test('apart')
        test_run = SolidTestRun(
            solid_test_at_path('tests/meta_project/test_apart.py'))

        self.assertEqual(test_run.results, node_run.results)
        self.assertEqual(
            (test_run.total, test_run.passed, test_run.failed),
            (node_run.total, node_run.passed, node_run.failed),
        )
        self.assertEqual((test_run.total, test_run.passed, test_run.failed),
                          (2, 2, 0))
        self.assertEqual(test_run.returncode, 0)

    def test_bogus_test_path_fails_clearly_instead_of_a_bare_traceback(self):
        proc = solid_test_at_path('tests/meta_project/test_totally_bogus.py')

        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)
        self.assertIn('tests/meta_project/totally_bogus.py', proc.stderr)


class NodeMarkerMetaTest(TestCase):
    """The NODE marker (skill-repo improvements.md #14): the loader
    used to return the FIRST AbstractBaseNode subclass defined in a
    file -- an unenforced "main class first" convention that, when
    violated, silently loaded the wrong node. A file defining several
    node classes and no NODE marker must now fail loudly instead,
    naming the file, the candidate classes, and the remedy."""

    def test_unmarked_multi_class_file_fails_loudly_with_remedy(self):
        proc = solid_test_at_path('tests/meta_project/unmarked.py')

        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)
        self.assertIn('tests/meta_project/unmarked.py', proc.stderr)
        self.assertIn('Unmarked', proc.stderr)
        self.assertIn('AlsoANode', proc.stderr)
        self.assertIn('NODE = ', proc.stderr)

    def test_marker_loads_main_class_despite_helper_defined_first(self):
        """The exact trap from the recent session: a helper subclass
        defined BEFORE the main node class. With NODE naming the main
        class, `solid test` must exercise Trap -- not Helper -- and
        the same genuine contract as apart.py must hold."""
        run = solid_test('trap')
        self.assertEqual(run.results, {
            'test_cubes_do_not_intersect': 'passed',
            'test_placed_cube_is_where_placed': 'passed',
        })
        self.assertEqual((run.total, run.passed, run.failed), (2, 2, 0))
        self.assertEqual(run.returncode, 0)
