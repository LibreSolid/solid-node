# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for docs/performance-improvement.md fix 2: an AABB
broad-phase before any exact boolean in solid_node/test.py's
intersection-based assertions. A part's world AABB (the box of its 8
local-bounds corners transformed by its composed world matrix -- see
solid_node.node.base._compose_world_matrix, fix 1) is a conservative
superset of its real footprint; when two parts' world boxes are
disjoint their intersection is exactly empty, and the boolean can be
skipped. This is exact-negative only -- it must never change a verdict,
only skip work when the answer is already certain.

FakeNode is a duck-typed stand-in exposing exactly the attributes the
broad-phase needs (name, stl_file, operations) -- real geometry, real
Rotation/Translation operations, no full node tree or openscad build,
in the same spirit as tests/test_node_mesh_cache.py's FakeNode.
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import trimesh
from trimesh.creation import box

from solid_node.node.base import AbstractBaseNode
from solid_node.node.operations import Rotation, Translation
from solid_node.test import TestCase as AssertingTestCase


asserter = AssertingTestCase()


class FakeNode:
    """Duck-typed stand-in exposing exactly what the broad-phase (and
    the real AbstractBaseNode.mesh getter it builds on) needs: name,
    stl_file, operations, and an optional _parent. Reuses the REAL
    mesh property getter -- same pattern as
    tests/test_node_mesh_cache.py's FakeNode."""

    def __init__(self, name, stl_file):
        self.name = name
        self.stl_file = stl_file
        self.operations = []
        self._parent = None

    def as_number(self, n):
        return float(n)

    @property
    def mesh(self):
        return AbstractBaseNode.mesh.fget(self)


class BroadPhaseTestCase(TestCase):
    """Shared fixtures: a size-2 cube STL on disk, and three
    placements built from it --

    - `far_away`: translated 1000mm off -- world AABBs disjoint.
    - `corner_a` / `corner_b`: `corner_b` is `corner_a` rotated 45deg
      about Z (so its world AABB grows past its actual diamond
      footprint) and `corner_a` sits in the resulting AABB-only gap --
      world boxes overlap, but the real solids never touch (min
      x+y on corner_a's face is 1.8, the diamond's is capped at
      1.4142 -- a comfortable margin, not a boundary-touching case).
    - `overlapping_a` / `overlapping_b`: genuinely, robustly
      intersecting cubes (a straightforward 0.5mm axis overlap).
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.box_path = os.path.join(self.tmpdir.name, 'box.stl')
        box((2, 2, 2)).export(self.box_path)

    def _part(self, name):
        return FakeNode(name, self.box_path)

    def _translated(self, name, translation):
        node = self._part(name)
        node.operations.append(Translation(translation, node))
        return node

    def _rotated_then_translated(self, name, angle, axis, translation):
        node = self._part(name)
        node.operations.append(Rotation(angle, axis, node))
        node.operations.append(Translation(translation, node))
        return node

    def far_pair(self):
        origin = self._part('Origin')
        far_away = self._translated('FarAway', [1000, 0, 0])
        return origin, far_away

    def corner_gap_pair(self):
        # corner_a: axis-aligned cube centered at (1.9, 1.9, 0) --
        # world AABB x/y in [0.9, 2.9]. Its own footprint IS its AABB
        # (unrotated), so any point of it has x >= 0.9 and y >= 0.9.
        corner_a = self._translated('CornerA', [1.9, 1.9, 0])
        # corner_b: same cube, rotated 45deg about Z, left at the
        # origin -- world AABB x/y in [-1.4142, 1.4142], overlapping
        # corner_a's AABB in the [0.9, 1.4142] corner. But corner_b's
        # real footprint is the diamond |x|+|y| <= 1.4142: for any of
        # corner_a's points (x>=0.9, y>=0.9), x+y >= 1.8 > 1.4142, so
        # the diamond never reaches into corner_a's actual box.
        corner_b = self._rotated_then_translated(
            'CornerB', 45, [0, 0, 1], [0, 0, 0])
        return corner_a, corner_b

    def overlapping_pair(self):
        overlapping_a = self._part('OverlapA')
        overlapping_b = self._translated('OverlapB', [0.5, 0, 0])
        return overlapping_a, overlapping_b


class DisjointPairCulledTest(BroadPhaseTestCase):
    """assertNotIntersecting / assertFreeWithin / assertNoPairwise
    Intersections: a genuinely disjoint pair passes WITHOUT the
    boolean ever running."""

    def test_assert_not_intersecting_never_calls_the_boolean(self):
        origin, far_away = self.far_pair()

        def _fail(*a, **kw):
            raise AssertionError('boolean must not run for a disjoint pair')

        with patch('solid_node.test.trimesh.boolean.intersection',
                   side_effect=_fail):
            asserter.assertNotIntersecting(origin, far_away)

    def test_assert_free_within_never_calls_the_boolean(self):
        origin, far_away = self.far_pair()

        def _fail(*a, **kw):
            raise AssertionError('boolean must not run for a disjoint pair')

        with patch('solid_node.test.trimesh.boolean.intersection',
                   side_effect=_fail):
            asserter.assertFreeWithin(origin, 5, far_away)

    def test_assert_no_pairwise_intersections_never_calls_the_boolean(self):
        origin, far_away = self.far_pair()
        origin.children = ()
        far_away.children = ()

        class Assembly:
            name = 'Assembly'
            children = (origin, far_away)

        def _fail(*a, **kw):
            raise AssertionError('boolean must not run for a disjoint pair')

        with patch('solid_node.test.trimesh.boolean.intersection',
                   side_effect=_fail):
            asserter.assertNoPairwiseIntersections(Assembly())


class DisjointPairFailsFastTest(BroadPhaseTestCase):
    """assertIntersecting / assertBlockedBeyond (expect_intersect=True):
    a disjoint pair fails IMMEDIATELY, without running the boolean,
    with the SAME AssertionError message today's is_empty path
    produces."""

    def test_assert_intersecting_fails_fast_with_todays_message(self):
        origin, far_away = self.far_pair()

        def _fail(*a, **kw):
            raise AssertionError('boolean must not run for a disjoint pair')

        with patch('solid_node.test.trimesh.boolean.intersection',
                   side_effect=_fail):
            with self.assertRaises(AssertionError) as ctx:
                asserter.assertIntersecting(origin, far_away)

        self.assertEqual(
            str(ctx.exception),
            f"{origin.name} should intersect {far_away.name}")

    def test_assert_blocked_beyond_fails_fast_with_todays_message(self):
        origin, far_away = self.far_pair()
        origin.operations.append(Translation([0, 0, 0], origin))
        original_ops = list(origin.operations)

        def _fail(*a, **kw):
            raise AssertionError('boolean must not run for a disjoint pair')

        with patch('solid_node.test.trimesh.boolean.intersection',
                   side_effect=_fail):
            with self.assertRaises(AssertionError) as ctx:
                asserter.assertBlockedBeyond(origin, 10, far_away)

        message = str(ctx.exception)
        self.assertIn(origin.name, message)
        self.assertIn(far_away.name, message)
        self.assertIn('no intersection', message)
        # The perturbation is still cleaned up in the finally, even
        # on the fail-fast path.
        self.assertEqual(origin.operations, original_ops)


class OverlappingBoxNonIntersectingRunsBooleanTest(BroadPhaseTestCase):
    """A pair whose world AABBs overlap but whose real geometry does
    NOT intersect: the broad-phase must not (and, being conservative,
    cannot) cull it -- the boolean genuinely runs, and still correctly
    reports no intersection."""

    def test_boolean_runs_and_correctly_reports_no_intersection(self):
        corner_a, corner_b = self.corner_gap_pair()
        calls = []
        original = trimesh.boolean.intersection

        def _counting(*args, **kwargs):
            calls.append(args)
            return original(*args, **kwargs)

        with patch('solid_node.test.trimesh.boolean.intersection',
                   side_effect=_counting):
            asserter.assertNotIntersecting(corner_a, corner_b)

        self.assertEqual(len(calls), 1)


class GenuineIntersectionStillDetectedTest(BroadPhaseTestCase):
    """The broad-phase is exact-negative only: a pair with overlapping
    boxes AND real intersecting geometry must still be reported as
    intersecting -- never culled into a false pass."""

    def test_assert_not_intersecting_still_fails_on_real_overlap(self):
        overlapping_a, overlapping_b = self.overlapping_pair()

        with self.assertRaises(AssertionError) as ctx:
            asserter.assertNotIntersecting(overlapping_a, overlapping_b)

        self.assertIn('should not intersect', str(ctx.exception))

    def test_assert_intersecting_passes_on_real_overlap(self):
        overlapping_a, overlapping_b = self.overlapping_pair()

        asserter.assertIntersecting(overlapping_a, overlapping_b)
