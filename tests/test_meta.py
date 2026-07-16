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
        env = dict(os.environ, SOLID_BUILD_DIR=BUILD_DIR)
        proc = subprocess.run(
            [sys.executable, '-c',
             'from solid_node.cli import manage; manage()',
             'test', f'tests/meta_project/{fixture}.py'],
            cwd=REPO_DIR, env=env,
            capture_output=True, text=True, timeout=300,
        )
        _runs[fixture] = SolidTestRun(proc)
    return _runs[fixture]


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
