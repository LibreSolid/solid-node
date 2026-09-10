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

`assertNoSolidInterference`'s own whole-assembly index (ADR-091) may take
its bounds in a chosen INDEXING FRAME instead of world axes: for a
candidate frame `F`, a solid's index box is the AABB of its 8
local-bounds corners under `inv(F) @ M_i`. This is exact-negative for
the same reason a world box is (see the "Broad-phase completeness"
block below for the one-paragraph proof) -- the frame choice can only
change WHICH candidate pairs are emitted, never a verdict. World axes
(`F = I`) remain one candidate among the world frame and the placement
frames of the `_INDEXING_FRAME_CANDIDATES` largest topmost solids, and
`RigidNode`/`Assembly` (imported from tests/test_assembly_integrity.py)
build the real node trees the chosen-frame tests below run
`assertNoSolidInterference` against, exactly as that module's own tests
do.
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

from .test_assembly_integrity import Assembly, RigidNode


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
#
# The obligation extends to a bound taken in a chosen INDEXING FRAME
# (ADR-091), not only on world axes. The one-paragraph proof: let F be
# any invertible affine frame and A, B two placed solids with world
# matrices M_A, M_B. Let box_F(X) be the axis-aligned box of X's 8
# local-bounds corners under inv(F) @ M_X. inv(F) is an invertible
# affine map, so it carries the local box's convex hull onto the convex
# hull of the images of its corners; the solid is inside its local box,
# hence inside box_F. If box_F(A) and box_F(B) are disjoint then their
# images under inv(F) are disjoint, and an invertible map preserves
# intersection -- inv(F)*(A ∩ B) = (inv(F)*A) ∩ (inv(F)*B) = ∅ -- so
# A ∩ B = ∅. Box overlap in ANY ONE common frame therefore remains a
# necessary condition for intersection, whichever frame the index chose;
# the frame choice can only change WHICH superset of the meeting pairs
# is emitted, never drop a pair that meets. F = I (the world frame) is
# `_world_bounds` exactly, so world is not an approximation of today's
# behaviour -- it IS today's behaviour, bit for bit, and is always one
# of the candidates. `IndexingFrameCompletenessTest` re-runs the tables
# above through the chosen-frame seam to pin this; the tests that follow
# cover the frame's arithmetic (`_framed_bounds`), the margin that
# absorbs it, the candidate set, the score, the tie rule, the guards,
# and the no-regression pin for an ordinary axis-aligned project.


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
            manifold, local_bounds, matrix, _ = test_module._fast_geometry(part)
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


########################################
# The indexing frame (ADR-091)
#
# assertNoSolidInterference's own index may now take its bounds in a
# chosen frame instead of world axes (design.md of
# openspec/changes/broad-phase-indexing-frame). The tests below exercise
# the real seam -- _place_solid, _framed_bounds, _indexing_frame_boxes,
# _ranked_solid_candidates -- rather than reimplementing the chooser.


class IndexingFrameFixture(TestCase):
    """Shared helpers: a real STL per distinct size, and real
    `_place_solid` records built from `Placement`s, each carrying a
    `RigidNode`-shaped solid and the placement's own local bounds and
    matrix -- so a test exercises `_place_solid` and the assertion's own
    indexing seam, not a reimplementation of either."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self._stl_cache = {}

    def _stl_for(self, size):
        key = tuple(round(float(value), 9) for value in size)
        path = self._stl_cache.get(key)
        if path is None:
            path = os.path.join(
                self.tmpdir.name, f'sized-{len(self._stl_cache)}.stl')
            box(key).export(path)
            self._stl_cache[key] = path
        return path

    def assembly_records(self, placements):
        records = []
        for index, placement in enumerate(placements):
            low, high = placement.local_bounds
            size = tuple(float(value) for value in (high - low))
            node = RigidNode(f'Solid{index}', self._stl_for(size))
            identity = ('indexing-frame-fixture', index)
            records.append(test_module._place_solid(
                node, node.stl_file, placement.local_bounds,
                placement.matrix, None, identity))
        return records

    def assembly_emitted_pairs(self, records):
        """The ordered candidate pairs `assertNoSolidInterference`'s own
        indexing seam emits for these records: the chosen-frame boxes,
        swept by the same `_bounds_candidates` the assertion uses."""
        return list(test_module._bounds_candidates(
            test_module._indexing_frame_boxes(records)))


class IndexingFrameCompletenessTest(IndexingFrameFixture):
    """The chosen-frame index must not drop a meeting pair either: the
    same boundary table and exhaustive lattice that prove the world-axis
    index complete, run through the chosen-frame seam instead."""

    def test_boundary_table_is_complete_through_the_chosen_frame(self):
        for name, placements in BoundaryTableCompletenessTest().cases().items():
            with self.subTest(case=name):
                truth = intersecting_pairs(placements)
                records = self.assembly_records(placements)
                emitted = set(self.assembly_emitted_pairs(records))

                self.assertTrue(
                    truth <= emitted,
                    f'{name}: chosen-frame index omitted intersecting '
                    f'pairs {sorted(truth - emitted)}')

    def test_lattice_is_complete_through_the_chosen_frame(self):
        placements = LatticeCompletenessTest().placements()
        truth = intersecting_pairs(placements)
        records = self.assembly_records(placements)
        emitted = set(self.assembly_emitted_pairs(records))

        self.assertTrue(truth, 'fixture bug: the lattice must intersect')
        self.assertTrue(
            truth <= emitted,
            f'chosen-frame index omitted intersecting pairs '
            f'{sorted(truth - emitted)}')


class FramedBoundsConservativeTest(TestCase):
    """A bound taken in a non-world indexing frame must enclose the
    solid's placed geometry expressed in THAT frame -- the same
    obligation `WorldBoundsConservativeTest` proves for the identity
    frame, generalised to an arbitrary invertible frame (design.md
    section 1)."""

    def test_bound_in_a_rotated_frame_encloses_the_placed_geometry(self):
        placement = Placement((2.0, 2.0, 2.0), translation([5, -3, 2]))
        frame = rotation_z(30)
        inverse_frame = np.linalg.inv(frame)

        low, high = test_module._framed_bounds(
            placement.local_bounds, placement.matrix, inverse_frame)
        actual = placement.placed.transform(
            inverse_frame[:3, :4]).bounding_box()

        np.testing.assert_array_less(low - 1e-9, np.array(actual[:3]))
        np.testing.assert_array_less(np.array(actual[3:]), high + 1e-9)

    def test_world_frame_reproduces_world_bounds_exactly(self):
        placement = Placement((2.0, 2.0, 2.0), rotation_z(45))

        low, high = test_module._framed_bounds(
            placement.local_bounds, placement.matrix, np.eye(4))

        np.testing.assert_array_equal(low, placement.world_bounds[0])
        np.testing.assert_array_equal(high, placement.world_bounds[1])


class ClockShapedScenarioTest(TestCase):
    """The scenario the finding is about: a common rigid turn applied to
    every solid inflates every world box (up to sqrt(2) in the turn's
    plane) without changing what actually touches. Here `Plate` is the
    assembly's largest solid and carries no individual pre-turn
    rotation, so choosing ITS frame exactly undoes the shared turn for
    every solid and reproduces the un-turned design's own boxes."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def _node(self, name, size, offset):
        path = os.path.join(self.directory.name, f'{name}.stl')
        box(size).export(path)
        node = RigidNode(name, path)
        node.operations.append(Translation(offset, node))
        return node

    def _assembly(self, turned):
        plate = self._node('Plate', (30.0, 30.0, 4.0), [0, 0, -10])
        near_a = self._node('NearA', (2.0, 2.0, 2.0), [0, 0, 0])
        near_b = self._node('NearB', (2.0, 2.0, 2.0), [2.8, 0, 0])
        near_c = self._node('NearC', (2.0, 2.0, 2.0), [0, 2.8, 0])
        root = Assembly('Root', (plate, near_a, near_b, near_c))
        if turned:
            root.operations.append(Rotation(45, [0, 0, 1], root))
        return root

    def test_common_turn_costs_no_candidates_in_the_chosen_frame(self):
        turned_root = self._assembly(True)
        unturned_root = self._assembly(False)

        turned_records = test_module._placed_assembly_solids(turned_root)
        unturned_records = test_module._placed_assembly_solids(unturned_root)

        # indices: 0 Plate, 1 NearA, 2 NearB, 3 NearC
        world_boxes = [record[2] for record in turned_records]
        self.assertFalse(
            test_module._boxes_disjoint(world_boxes[1], world_boxes[2]),
            'fixture bug: NearA/NearB world boxes should overlap once turned')
        self.assertFalse(
            test_module._boxes_disjoint(world_boxes[1], world_boxes[3]),
            'fixture bug: NearA/NearC world boxes should overlap once turned')

        chosen_boxes = test_module._indexing_frame_boxes(turned_records)
        self.assertTrue(
            test_module._boxes_disjoint(chosen_boxes[1], chosen_boxes[2]),
            'the chosen frame should separate NearA from NearB')
        self.assertTrue(
            test_module._boxes_disjoint(chosen_boxes[1], chosen_boxes[3]),
            'the chosen frame should separate NearA from NearC')

        turned_world_pairs = set(test_module._bounds_candidates(world_boxes))
        self.assertIn((1, 2), turned_world_pairs)
        self.assertIn((1, 3), turned_world_pairs)

        turned_chosen_pairs = set(test_module._bounds_candidates(chosen_boxes))
        self.assertNotIn((1, 2), turned_chosen_pairs)
        self.assertNotIn((1, 3), turned_chosen_pairs)

        unturned_world_pairs = set(test_module._bounds_candidates(
            [record[2] for record in unturned_records]))
        self.assertEqual(turned_chosen_pairs, unturned_world_pairs)

        asserter.assertNoSolidInterference(turned_root)
        asserter.assertNoSolidInterference(unturned_root)


class FlushContactUnderTurnTest(IndexingFrameFixture):
    """The frame-change arithmetic must not let a touching pair fall
    through: `face_contact` and `edge_contact` (from
    `BoundaryTableCompletenessTest`), re-anchored far apart and placed by
    one common turn alongside a much larger axis-aligned solid, must
    both still be emitted once the chooser picks that solid's frame --
    and the enlargement margin is what makes that true (design.md
    section 1)."""

    def _placements(self):
        turn = rotation_z(45)
        cases = BoundaryTableCompletenessTest().cases()

        def anchored(placement, anchor):
            size = tuple(float(value) for value in (
                placement.local_bounds[1] - placement.local_bounds[0]))
            return Placement(
                size, turn @ translation(anchor) @ placement.matrix)

        face_moved, face_identity = cases['face_contact']
        edge_moved, edge_identity = cases['edge_contact']
        large = Placement((20.0, 20.0, 4.0), turn @ translation([0, 0, -20]))
        return [
            large,
            anchored(face_identity, [100, 0, 0]),
            anchored(face_moved, [100, 0, 0]),
            anchored(edge_identity, [200, 0, 0]),
            anchored(edge_moved, [200, 0, 0]),
        ]

    def test_flush_contact_is_emitted_once_the_chooser_picks_a_frame(self):
        placements = self._placements()
        records = self.assembly_records(placements)

        boxes = test_module._indexing_frame_boxes(records)
        self.assertFalse(
            np.array_equal(boxes[0][0], records[0][2][0])
            and np.array_equal(boxes[0][1], records[0][2][1]),
            'fixture bug: the chooser should not have picked the world '
            'frame here -- the large solid dominates the total volume')

        emitted = set(self.assembly_emitted_pairs(records))
        self.assertIn((1, 2), emitted)
        self.assertIn((3, 4), emitted)

    def test_zero_margin_exposes_the_frame_changes_arithmetic(self):
        """Pins the residue design.md section 1 names, not a guaranteed
        cull: measured on this machine/library version, the specific
        residue `inv(F) @ M` leaves on these exactly-touching boxes is a
        few ULPs at coordinates of order 1e2, landing off the axis the
        contact is measured on (confirmed at the box level below,
        independent of `_bounds_candidates`' disjointness threshold) and
        so it does not flip this particular pair from touching to
        separated. Per tasks.md task 1.5: this is reported rather than
        chased by tuning the fixture -- see evidence.md and the
        implementation commit message. The margin's purpose (design.md
        section 1) does not depend on this fixture reproducing the
        failure; it is restated and pinned positively by
        `test_flush_contact_is_emitted_once_the_chooser_picks_a_frame`
        above, which is unaffected by margin=0 not culling here."""
        placements = self._placements()
        records = self.assembly_records(placements)
        inverse_frame = np.linalg.inv(records[0][6])

        with patch.object(test_module, '_INDEXING_FRAME_MARGIN', 0.0):
            emitted = set(self.assembly_emitted_pairs(records))
            face_box_a = test_module._framed_bounds(
                records[1][7], records[1][6], inverse_frame)
            face_box_b = test_module._framed_bounds(
                records[2][7], records[2][6], inverse_frame)
            edge_box_a = test_module._framed_bounds(
                records[3][7], records[3][6], inverse_frame)
            edge_box_b = test_module._framed_bounds(
                records[4][7], records[4][6], inverse_frame)

        # The residue this test exists to measure: how far the
        # frame-changed touching coordinate landed from the exact
        # pre-turn value (0.0 on this machine -- see evidence.md).
        residue_face = float(face_box_a[1][0] - face_box_b[0][0])
        residue_edge = max(
            abs(float(edge_box_a[1][0] - edge_box_b[0][0])),
            abs(float(edge_box_a[1][1] - edge_box_b[0][1])))
        self.assertLess(abs(residue_face), 1e-9)
        self.assertLess(abs(residue_edge), 1e-9)

        culled = (1, 2) not in emitted or (3, 4) not in emitted
        if not culled:
            print(
                'note (task 1.5 fallback): zero margin did not cull '
                'either flush-contact pair on this machine/arithmetic '
                f'(face residue {residue_face!r}, edge residue '
                f'{residue_edge!r}); the positive half of this test '
                '(margin restored) still holds -- see evidence.md')


class DeterminismTest(IndexingFrameFixture):
    """Distinctly-sized solids (no diagonal ties) so a permutation of
    the input order cannot change which physical solid ranks where."""

    def _placements(self):
        turn = rotation_z(37)
        return [
            Placement((10.0, 10.0, 10.0), turn @ translation([0, 0, 0])),
            Placement((3.0, 3.0, 3.0), turn @ translation([6, 0, 0])),
            Placement((2.0, 2.0, 2.0), turn @ translation([0, 6, 0])),
            Placement((1.5, 1.5, 1.5), turn @ translation([0, 0, 6])),
        ]

    def test_same_records_choose_the_same_frame_and_pairs_twice(self):
        records = self.assembly_records(self._placements())

        first = self.assembly_emitted_pairs(records)
        second = self.assembly_emitted_pairs(records)

        self.assertEqual(first, second)

    def test_a_rank_preserving_permutation_chooses_the_same_geometric_frame(self):
        records = self.assembly_records(self._placements())
        order = [2, 0, 3, 1]
        shuffled = [records[index] for index in order]

        boxes = test_module._indexing_frame_boxes(records)
        shuffled_boxes = test_module._indexing_frame_boxes(shuffled)

        for position, original_index in enumerate(order):
            np.testing.assert_allclose(
                shuffled_boxes[position][0], boxes[original_index][0])
            np.testing.assert_allclose(
                shuffled_boxes[position][1], boxes[original_index][1])


class CandidateSetTest(IndexingFrameFixture):
    """`K = _INDEXING_FRAME_CANDIDATES = 3`: exactly the world frame and
    the three largest topmost solids by local-bounds diagonal are
    scored, and a fourth, larger solid displaces the third."""

    def _ranked_placements(self, count):
        placements = []
        for index in range(count):
            side = 2.0 + (count - index)
            placements.append(Placement(
                (side, side, side), translation([index * 1000.0, 0, 0])))
        return placements

    def test_exactly_world_and_the_k_largest_are_scored(self):
        records = self.assembly_records(self._ranked_placements(5))

        self.assertEqual(
            test_module._ranked_solid_candidates(records), [0, 1, 2])

    def test_a_fourth_larger_solid_displaces_the_third(self):
        placements = self._ranked_placements(5)
        low, high = placements[3].local_bounds
        placements[3] = Placement(
            tuple(float(value) for value in (high - low) * 100.0),
            translation([3000.0, 0, 0]))
        records = self.assembly_records(placements)

        self.assertEqual(
            test_module._ranked_solid_candidates(records), [3, 0, 1])


class StrictPreferenceAndTieRuleTest(IndexingFrameFixture):
    """An axis-aligned assembly chooses the WORLD frame because the
    padded candidate scores STRICTLY higher -- not because of the tie
    rule -- and the tie rule itself is pinned separately, isolated from
    ordinary arithmetic by forcing an exact score tie."""

    def _axis_aligned_placements(self):
        return [
            Placement((4.0, 4.0, 4.0), translation([0, 0, 0])),
            Placement((2.0, 2.0, 2.0), translation([10, 0, 0])),
            Placement((1.0, 1.0, 1.0), translation([0, 10, 0])),
        ]

    def test_axis_aligned_assembly_prefers_world_strictly(self):
        records = self.assembly_records(self._axis_aligned_placements())
        world_boxes = [record[2] for record in records]

        largest_matrix = records[0][6]
        inverse = np.linalg.inv(largest_matrix)
        candidate_boxes = [
            test_module._framed_bounds(record[7], record[6], inverse)
            for record in records]
        margin = test_module._INDEXING_FRAME_MARGIN
        padded_boxes = [
            (low - margin, high + margin) for low, high in candidate_boxes]

        def total_volume(boxes):
            return sum(
                float(np.prod(np.asarray(high) - np.asarray(low)))
                for low, high in boxes)

        world_score = total_volume(world_boxes)
        candidate_score = total_volume(padded_boxes)
        self.assertLess(
            world_score, candidate_score,
            'fixture bug: the padded candidate should score strictly '
            'worse than the unpadded world frame for an axis-aligned '
            'assembly')

        chosen = test_module._indexing_frame_boxes(records)
        for chosen_box, world_box in zip(chosen, world_boxes):
            np.testing.assert_array_equal(chosen_box[0], world_box[0])
            np.testing.assert_array_equal(chosen_box[1], world_box[1])

    def test_tie_breaks_to_the_earliest_candidate(self):
        records = self.assembly_records(self._axis_aligned_placements())
        world_boxes = [record[2] for record in records]
        by_identity = {
            (id(record[6]), id(record[7])): box
            for record, box in zip(records, world_boxes)}

        def forced_tie(local_bounds, matrix, inverse_frame):
            # Force every candidate frame to reproduce world's own boxes
            # exactly, regardless of which frame is being scored --
            # isolates the LAST-RESORT tie rule from the ordinary
            # strict-preference case covered above.
            return by_identity[(id(matrix), id(local_bounds))]

        with (patch.object(test_module, '_framed_bounds',
                           side_effect=forced_tie),
              patch.object(test_module, '_INDEXING_FRAME_MARGIN', 0.0)):
            chosen = test_module._indexing_frame_boxes(records)

        for chosen_box, world_box in zip(chosen, world_boxes):
            np.testing.assert_array_equal(chosen_box[0], world_box[0])
            np.testing.assert_array_equal(chosen_box[1], world_box[1])


class GuardTest(IndexingFrameFixture):
    """A candidate frame that cannot be inverted is dropped rather than
    raising or producing non-finite boxes; an assembly whose every solid
    frame is singular falls all the way back to the world index."""

    def _singular_matrix(self):
        matrix = np.eye(4)
        matrix[2, :] = 0.0
        return matrix

    def test_a_singular_candidate_frame_is_dropped(self):
        singular = self._singular_matrix()
        placements = [
            Placement((2.0, 2.0, 2.0), singular),
            Placement((1.0, 1.0, 1.0), translation([5, 0, 0])),
            Placement((1.0, 1.0, 1.0), translation([0, 5, 0])),
        ]
        records = self.assembly_records(placements)

        boxes = test_module._indexing_frame_boxes(records)

        self.assertEqual(len(boxes), 3)
        for box in boxes:
            self.assertTrue(np.all(np.isfinite(box[0])))
            self.assertTrue(np.all(np.isfinite(box[1])))

    def test_every_solid_frame_singular_falls_back_to_world(self):
        singular = self._singular_matrix()
        placements = [
            Placement((2.0, 2.0, 2.0), singular),
            Placement((1.0, 1.0, 1.0), singular @ translation([5, 0, 0])),
        ]
        records = self.assembly_records(placements)

        boxes = test_module._indexing_frame_boxes(records)
        world_boxes = [record[2] for record in records]

        for box, world_box in zip(boxes, world_boxes):
            np.testing.assert_array_equal(box[0], world_box[0])
            np.testing.assert_array_equal(box[1], world_box[1])


class AxisAlignedRegressionTest(IndexingFrameFixture):
    """The no-regression pin for the ordinary project: an axis-aligned
    assembly is indexed EXACTLY as today, bit for bit."""

    def test_axis_aligned_assembly_matches_todays_index_exactly(self):
        placements = [
            Placement((4.0, 4.0, 4.0), translation([0, 0, 0])),
            Placement((2.0, 2.0, 2.0), translation([5, 0, 0])),
            Placement((1.0, 1.0, 1.0), translation([0, 5, 0])),
        ]
        records = self.assembly_records(placements)

        chosen_pairs = self.assembly_emitted_pairs(records)
        today_pairs = list(test_module._bounds_candidates(
            [placement.world_bounds for placement in placements]))
        self.assertEqual(chosen_pairs, today_pairs)

        chosen_boxes = test_module._indexing_frame_boxes(records)
        world_boxes = [record[2] for record in records]
        for chosen_box, world_box in zip(chosen_boxes, world_boxes):
            np.testing.assert_array_equal(chosen_box[0], world_box[0])
            np.testing.assert_array_equal(chosen_box[1], world_box[1])


class SupportPathWorldBoundsTest(IndexingFrameFixture):
    """The gravity-support assertion must keep reading world-axis
    bounds regardless of this cycle: `record[2]` is `_world_bounds`
    applied to `record[7]`/`record[6]`, untouched by any indexing frame.
    `tests/test_assembly_supported.py`'s
    `GroundSeedTest.test_default_seeds_are_the_solids_at_the_furthest_extent`,
    `DropSupportTest.test_gravity_direction_selects_which_solids_are_held`
    and
    `BroadPhaseTest.test_only_bounds_overlapping_pairs_are_intersected`
    would break if that stopped being true; they are named here and run
    explicitly in task 3.5."""

    def test_record_world_bounds_are_untouched_world_axis_bounds(self):
        placements = [
            Placement(
                (2.0, 2.0, 2.0), rotation_z(45) @ translation([3, 0, 0])),
            Placement((1.0, 1.0, 1.0), translation([0, 5, 0])),
        ]
        records = self.assembly_records(placements)

        for record in records:
            expected = test_module._world_bounds(record[7], record[6])
            np.testing.assert_array_equal(record[2][0], expected[0])
            np.testing.assert_array_equal(record[2][1], expected[1])
