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

import itertools
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import trimesh
from manifold3d import Manifold
from trimesh.creation import box

import solid_node.test as test_module
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
    cannot) cull it -- the exact boolean genuinely runs, and still
    correctly reports no intersection.

    Fix 3 (docs/performance-improvement.md) replaces the exact-boolean
    engine this non-culled path calls -- a cached Manifold's `^`
    instead of trimesh.boolean.intersection -- so the proof here is
    engine-agnostic: confirm the fixture's world boxes genuinely
    overlap (not culled), via the same _boxes_disjoint helper the fast
    path itself uses, then confirm the assertion still computes the
    correct (empty) verdict.
    """

    def test_boxes_overlap_and_the_exact_boolean_still_reports_no_intersection(self):
        corner_a, corner_b = self.corner_gap_pair()

        fast_a = test_module._fast_geometry(corner_a)
        fast_b = test_module._fast_geometry(corner_b)
        box_a = test_module._world_bounds(fast_a[1], fast_a[2])
        box_b = test_module._world_bounds(fast_b[1], fast_b[2])
        self.assertFalse(
            test_module._boxes_disjoint(box_a, box_b),
            'fixture bug: these boxes should overlap, not be culled')

        asserter.assertNotIntersecting(corner_a, corner_b)


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


########################################
# Broad-phase completeness
#
# assertNoSolidInterference reaches its verdict through the spatial
# index alone: _world_bounds, _boxes_disjoint, and _bounds_candidates
# decide which pairs ever meet an exact boolean. Everything the
# assertion promises therefore rests on ONE obligation --
#
#   for any two placed solids whose exact intersection is non-empty,
#   _bounds_candidates emits that pair.
#
# The obligation has two halves, and neither is an empirical question
# needing search. _world_bounds is conservative by construction (the
# local box contains the geometry, and an affine map carries the convex
# hull of the 8 corners onto the convex hull of their images), so a test
# can only catch the implementation drifting off that theorem. The
# emit-every-overlapping-pair half is three axis comparisons, one strict
# inequality and one interval prune, whose realistic defect space is
# small and enumerable: a reversed comparison, a wrong axis index, an
# inverted strict/non-strict, an off-by-one in the active-list prune.
#
# So the coverage below is deterministic and enumerated rather than
# randomly generated -- a named boundary table, a finite exhaustive
# lattice, and a differential check over the fixtures this module
# already builds. A seeded generator was considered and rejected: it
# would search stochastically for a defect list that can simply be
# written down, and would need seed capture, replay override, shrinking
# and bit-exact case dumping purely to turn a random failure back into
# the hardcoded case the table already holds (see the ADR's rejected
# alternatives). Every case here reproduces by construction.
#
# All three layers assert CONTAINMENT, never equality: the index is
# free to emit extra pairs -- that is exactly what "conservative"
# means -- and demanding equality would forbid it.


class Placement:
    """A cube placed by a world matrix, carrying the three things the
    broad phase reads: local bounds, the world matrix, and (for the
    brute-force side of the comparison) the placed Manifold."""

    def __init__(self, size, matrix):
        manifold = Manifold.cube(size, True)
        low_high = manifold.bounding_box()
        self.local_bounds = np.array([low_high[:3], low_high[3:]], float)
        self.matrix = np.asarray(matrix, float)
        self.placed = manifold.transform(self.matrix[:3, :4])
        self.world_bounds = test_module._world_bounds(
            self.local_bounds, self.matrix)


def translation(offset):
    matrix = np.eye(4)
    matrix[:3, 3] = offset
    return matrix


def rotation_z(degrees):
    radians = np.radians(degrees)
    cos, sin = np.cos(radians), np.sin(radians)
    matrix = np.eye(4)
    matrix[:2, :2] = [[cos, -sin], [sin, cos]]
    return matrix


def intersecting_pairs(placements):
    """Brute force: every index pair whose EXACT intersection is
    non-empty. This is the ground truth the index must not miss."""
    return {
        (first, second)
        for first, second in itertools.combinations(
            range(len(placements)), 2)
        if not (placements[first].placed ^ placements[second].placed
                ).is_empty()
    }


def emitted_pairs(placements):
    return set(test_module._bounds_candidates(
        [placement.world_bounds for placement in placements]))


def box_overlapping_pairs(placements):
    """Every index pair whose world AABBs overlap, computed here rather
    than through _boxes_disjoint so the comparison is independent of the
    code under test. Boxes that merely touch count as overlapping: the
    predicate is deliberately strict, because a touching pair can still
    produce a non-empty zero-volume intersection (ADR-029)."""
    def overlap(first, second):
        low_a, high_a = first
        low_b, high_b = second
        return all(low_a[axis] <= high_b[axis] and low_b[axis] <= high_a[axis]
                   for axis in range(3))

    return {
        (first, second)
        for first, second in itertools.combinations(
            range(len(placements)), 2)
        if overlap(placements[first].world_bounds,
                   placements[second].world_bounds)
    }


class BoundaryTableCompletenessTest(TestCase):
    """The named boundary table: one case per condition that could
    plausibly break the culling predicate, each asserting the
    obligation directly. Cubes are size 2 centred on the origin, so an
    unrotated part spans [-1, 1] and a 2.0 offset is exact contact."""

    def cases(self):
        unit = (2.0, 2.0, 2.0)
        return {
            'fully_separated': (
                Placement(unit, translation([10, 0, 0])),
                Placement(unit, np.eye(4))),
            'face_contact': (
                Placement(unit, translation([2, 0, 0])),
                Placement(unit, np.eye(4))),
            'edge_contact': (
                Placement(unit, translation([2, 2, 0])),
                Placement(unit, np.eye(4))),
            'vertex_contact': (
                Placement(unit, translation([2, 2, 2])),
                Placement(unit, np.eye(4))),
            'positive_overlap': (
                Placement(unit, translation([0.5, 0, 0])),
                Placement(unit, np.eye(4))),
            'full_containment': (
                Placement((6.0, 6.0, 6.0), np.eye(4)),
                Placement(unit, np.eye(4))),
            'coincident_bounds': (
                Placement(unit, np.eye(4)),
                Placement(unit, np.eye(4))),
            'separated_on_x_only': (
                Placement(unit, translation([3, 0.5, 0.5])),
                Placement(unit, np.eye(4))),
            'separated_on_y_only': (
                Placement(unit, translation([0.5, 3, 0.5])),
                Placement(unit, np.eye(4))),
            'separated_on_z_only': (
                Placement(unit, translation([0.5, 0.5, 3])),
                Placement(unit, np.eye(4))),
            'rotated_overlap': (
                Placement(unit, rotation_z(45) @ translation([0.5, 0, 0])),
                Placement(unit, np.eye(4))),
            'rotated_clear_of_a_grown_box': (
                Placement(unit, rotation_z(45)),
                Placement(unit, translation([1.9, 1.9, 0]))),
        }

    def test_every_intersecting_case_is_emitted(self):
        for name, placements in self.cases().items():
            with self.subTest(case=name):
                truth = intersecting_pairs(placements)
                emitted = emitted_pairs(placements)

                self.assertTrue(
                    truth <= emitted,
                    f'{name}: broad phase omitted intersecting pairs '
                    f'{sorted(truth - emitted)}')

    def test_the_table_covers_both_verdicts(self):
        """A table that happened to contain only disjoint cases would
        satisfy the obligation vacuously. Prove it does not."""
        verdicts = {
            bool(intersecting_pairs(placements))
            for placements in self.cases().values()
        }

        self.assertEqual(verdicts, {True, False})

    def test_zero_extent_bounds_are_not_culled(self):
        """A degenerate (zero-thickness) world bound is checked at the
        bounds layer: a zero-thickness solid is not a valid manifold, so
        there is no geometry to compare against, but the predicate must
        still not cull a box that touches."""
        flat = (np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 0.0]))
        crossing = (np.array([0.5, 0.5, -1.0]), np.array([1.5, 1.5, 1.0]))

        self.assertFalse(test_module._boxes_disjoint(flat, crossing))
        self.assertEqual(
            list(test_module._bounds_candidates([flat, crossing])), [(0, 1)])


class LatticeCompletenessTest(TestCase):
    """A finite exhaustive lattice. Unit cubes at half-integer offsets
    over a bounded grid produce, by construction, every relative
    arrangement the predicate distinguishes -- deep overlap, partial
    overlap on one/two/three axes, exact face contact, and clean
    separation -- and covers them completely rather than sampling them.

    The 3.0 offset is what makes separation reachable: unit cubes span
    half a unit either side of their centre, so 0.0/0.5/1.0 alone would
    leave every pair overlapping or touching and the culling half of
    the proof vacuous. 64 placements is 2016 pairs of 12-triangle
    cubes."""

    def placements(self):
        offsets = (0.0, 0.5, 1.0, 3.0)
        return [
            Placement((1.0, 1.0, 1.0), translation([x, y, z]))
            for x, y, z in itertools.product(offsets, repeat=3)
        ]

    def test_lattice_emits_every_intersecting_pair(self):
        placements = self.placements()

        truth = intersecting_pairs(placements)
        emitted = emitted_pairs(placements)

        self.assertTrue(truth, 'fixture bug: the lattice must intersect')
        self.assertTrue(
            truth <= emitted,
            f'broad phase omitted intersecting pairs '
            f'{sorted(truth - emitted)}')

    def test_lattice_still_culls(self):
        """The companion half: containment would also hold for an index
        that emitted everything. Confirm real culling happens, so the
        completeness result is not vacuous."""
        placements = self.placements()
        every_pair = set(itertools.combinations(range(len(placements)), 2))

        self.assertLess(len(emitted_pairs(placements)), len(every_pair))

    def test_lattice_emits_exactly_the_box_overlapping_pairs(self):
        """Completeness alone cannot see a defect that makes the index
        emit MORE than it should -- dropping an axis from the
        disjointness test, say, which stays correct while quietly
        costing exact booleans. The index's own contract is exact
        (`_bounds_candidates` yields genuine AABB overlaps and nothing
        else), so pin it against an independent box comparison."""
        placements = self.placements()

        self.assertEqual(emitted_pairs(placements),
                         box_overlapping_pairs(placements))


class WorldBoundsConservativeTest(TestCase):
    """_world_bounds must enclose the placed geometry under any world
    matrix, and must genuinely grow under rotation rather than passing
    the untransformed local box through."""

    def test_rotated_bound_encloses_the_placed_geometry(self):
        placement = Placement((2.0, 2.0, 2.0), rotation_z(45))
        low, high = placement.world_bounds
        actual = placement.placed.bounding_box()

        np.testing.assert_array_less(low - 1e-9, np.array(actual[:3]))
        np.testing.assert_array_less(np.array(actual[3:]), high + 1e-9)

    def test_rotated_bound_is_a_strict_superset_of_the_local_box(self):
        placement = Placement((2.0, 2.0, 2.0), rotation_z(45))
        low, high = placement.world_bounds
        local_low, local_high = placement.local_bounds

        self.assertLess(low[0], local_low[0])
        self.assertGreater(high[0], local_high[0])
        self.assertLess(low[1], local_low[1])
        self.assertGreater(high[1], local_high[1])

    def test_translated_bound_tracks_the_translation(self):
        placement = Placement((2.0, 2.0, 2.0), translation([5, -3, 2]))
        low, high = placement.world_bounds

        np.testing.assert_allclose(low, [4, -4, 1])
        np.testing.assert_allclose(high, [6, -2, 3])


class ExistingFixtureDifferentialTest(BroadPhaseTestCase):
    """The third layer: ride the fixtures this module already builds.
    Costs no new geometry and widens automatically as the module grows."""

    def all_fixture_parts(self):
        origin, far_away = self.far_pair()
        corner_a, corner_b = self.corner_gap_pair()
        overlapping_a, overlapping_b = self.overlapping_pair()
        return [origin, far_away, corner_a, corner_b,
                overlapping_a, overlapping_b]

    def test_index_emits_every_intersecting_fixture_pair(self):
        parts = self.all_fixture_parts()
        placed = []
        for part in parts:
            manifold, local_bounds, matrix = test_module._fast_geometry(part)
            placement = Placement.__new__(Placement)
            placement.local_bounds = local_bounds
            placement.matrix = matrix
            placement.placed = manifold.transform(matrix[:3, :4])
            placement.world_bounds = test_module._world_bounds(
                local_bounds, matrix)
            placed.append(placement)

        truth = intersecting_pairs(placed)
        emitted = emitted_pairs(placed)

        self.assertTrue(truth, 'fixture bug: some pair must intersect')
        self.assertTrue(
            truth <= emitted,
            f'broad phase omitted intersecting pairs '
            f'{sorted(truth - emitted)}')
