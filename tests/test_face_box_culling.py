# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The face-box tier with a containment guard (ADR-092).

A whole-solid AABB can never separate a wheel running between two plates:
the plates' box encloses the wheel's in every frame. What decides such a
pair is cheap and local -- no FACE of one solid comes near any face of the
other -- and this tier asks exactly that question, after the AABB cull and
before any boolean.

The three-step proof (design.md section 2, stated in full in ADR-092):

  1. Disjoint face boxes ⇒ disjoint boundaries. A face's AABB contains
     that face, so the union of a shape's face boxes contains its whole
     boundary; carrying one shape's boxes into the other's frame by an
     invertible affine map and enlarging them can only grow what they
     contain. So if no transformed box of shape 2 meets any box of
     shape 1, the two placed boundaries do not meet.
  2. Disjoint boundaries ⇒ each solid entirely inside or entirely outside
     the partner. Two closed solids whose boundaries do not meet are
     either disjoint, or one lies wholly inside the other -- there is no
     partial overlap without the boundaries crossing.
  3. One representative point per SOLID, in BOTH directions, decides. A
     shape may be a compound of several solids, each a separate connected
     body, so one vertex of EACH solid of each shape is classified
     against EACH solid of the partner. If every classification is
     `TopAbs_OUT`, no solid of either shape lies inside the other, and by
     step 2 the intersection is empty.

Disjoint face boxes alone are NOT a verdict: a solid wholly inside another
also has disjoint boundaries. That is exactly why the containment guard
exists, and it is what the tests below spend most of their weight on --
the containment, cavity, compound and both-directions scenarios all exist
to keep a later reader from "simplifying" the guard away.
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import cadquery as cq
import numpy as np

import solid_node.test as test_module
from solid_node.exact import cached_shape, write_brep
from tests.exact_test_support import clear_exact_shape_caches


def _frame_and_wheel():
    """The originating model's shape: a thin disc running in the air
    between two plates, the plates and their pillar fused into ONE exact
    solid so a whole-solid box genuinely cannot separate the pair -- the
    wheel's box is a strict subset of the frame's on every axis."""
    plate = cq.Workplane('XY').box(20, 20, 2)
    top = plate.translate((0, 0, 11))
    bottom = plate.translate((0, 0, -11))
    pillar = (cq.Workplane('XY').center(8, 8).circle(1)
             .extrude(22).translate((0, 0, -11)))
    frame = top.union(bottom).union(pillar).val()
    wheel = cq.Workplane('XY').circle(5).extrude(2).translate((0, 0, -1)).val()
    return frame, wheel


class FaceBoxCullingTestCase(TestCase):
    """Shared fixture plumbing: real BREP-backed shapes with the stable
    cache identity `cached_face_boxes`/`placed_shape` need, and the
    tier's own seam plus the verdict path around it, so a test exercises
    `_faces_disjoint` AND the real call sites rather than a
    reimplementation of either."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        clear_exact_shape_caches()
        self._next_mtime = iter(
            value * 10 ** 9 for value in range(1, 10 ** 6))

    def brep(self, shape, name):
        """Write `shape` to a cached BREP artifact and load it back, so
        it carries the stable cache identity the tier's per-shape cache
        and the placement cache both key on."""
        path = os.path.join(self.tmpdir.name, f'{name}.brep')
        write_brep(shape, path, next(self._next_mtime))
        return cached_shape(path)

    def exact_pair(self, shape1, matrix1, shape2, matrix2,
                  name1='first', name2='second'):
        """The verdict path around the tier: `_exact_verdict`'s own AABB
        cull, the face-box tier, then the boolean -- the real call site,
        not a reimplementation of it."""
        return test_module._exact_verdict(
            shape1, matrix1, shape2, matrix2, name1, name2)

    def no_boolean(self):
        return patch.object(
            test_module, 'intersect_shapes',
            side_effect=AssertionError('boolean must be culled'))

    def counted_boolean(self):
        return patch.object(test_module, 'intersect_shapes',
                            wraps=test_module.intersect_shapes)


class BetweenPlatesTest(FaceBoxCullingTestCase):
    """design.md's central scenario: the pair a whole-solid box can never
    separate, however it is framed."""

    def test_a_wheel_between_two_plates_is_decided_without_a_boolean(self):
        frame, wheel = _frame_and_wheel()
        self.assertEqual(len(frame.Solids()), 1,
                         'fixture bug: the frame must be one fused solid')
        frame_shape = self.brep(frame, 'frame')
        wheel_shape = self.brep(wheel, 'wheel')
        identity = np.eye(4)

        frame_box = test_module.cached_bounding_box(frame_shape)
        wheel_box = test_module.cached_bounding_box(wheel_shape)
        world_frame = (
            np.array([frame_box.xmin, frame_box.ymin, frame_box.zmin]),
            np.array([frame_box.xmax, frame_box.ymax, frame_box.zmax]))
        world_wheel = (
            np.array([wheel_box.xmin, wheel_box.ymin, wheel_box.zmin]),
            np.array([wheel_box.xmax, wheel_box.ymax, wheel_box.zmax]))
        self.assertFalse(
            test_module._boxes_disjoint(world_frame, world_wheel),
            'fixture bug: the wheel is not enclosed by the frame\'s '
            'whole-solid box -- this scenario stopped exercising '
            'enclosure and must fail loudly, not pass vacuously')

        with self.no_boolean():
            stats = self.exact_pair(
                frame_shape, identity, wheel_shape, identity,
                'frame', 'wheel')

        self.assertTrue(stats.is_empty)
        self.assertEqual(stats.volume, 0.0)
        self.assertTrue(stats.exact)


class ContainmentTest(FaceBoxCullingTestCase):
    """The guard's whole purpose: face boxes alone would wrongly clear
    this pair, so it must still reach the kernel."""

    def test_a_small_cube_wholly_inside_a_big_cube_still_runs_the_boolean(self):
        big = self.brep(cq.Workplane('XY').box(10, 10, 10).val(), 'big')
        small = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'small')
        identity = np.eye(4)

        with self.counted_boolean() as boolean:
            stats = self.exact_pair(
                big, identity, small, identity, 'big', 'small')

        self.assertEqual(
            boolean.call_count, 1,
            'the containment guard must send this pair to the boolean')
        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 8.0)


class CavityTest(FaceBoxCullingTestCase):

    def test_a_solid_in_a_cavity_is_decided_without_a_boolean(self):
        hollow = self.brep(
            cq.Workplane('XY').box(20, 20, 20)
            .faces('>Z').workplane().rect(10, 10).cutBlind(-15).val(),
            'hollow')
        inner = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'inner')
        identity = np.eye(4)

        with self.no_boolean():
            stats = self.exact_pair(
                hollow, identity, inner, identity, 'hollow', 'inner')

        self.assertTrue(stats.is_empty)
        self.assertEqual(stats.volume, 0.0)


class FlushContactTest(FaceBoxCullingTestCase):
    """Verdict semantics are untouched: touching face boxes overlap, so a
    real flush abutment still reaches the kernel and still fouls at
    exactly 0.0 mm^3."""

    def _pair(self):
        left = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'left')
        right = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'right')
        offset = np.eye(4)
        offset[0, 3] = 2.0
        return left, right, offset

    def test_flush_contact_still_reaches_the_kernel(self):
        left, right, offset = self._pair()

        with self.counted_boolean() as boolean:
            stats = self.exact_pair(
                left, np.eye(4), right, offset, 'left', 'right')

        self.assertEqual(boolean.call_count, 1,
                         'flush contact must still reach the kernel')
        self.assertTrue(stats.is_empty)
        self.assertEqual(stats.volume, 0.0)

    def test_flush_contact_is_not_culled_even_at_zero_margin(self):
        # This fixture's transformed side is computed EXACTLY: axis-
        # aligned boxes, an identity rotation and a dyadic offset, so
        # `inv(M1) @ M2` carries no float residue in float64. What stops
        # the cull at margin 0 here is genuinely the touching, not the
        # margin absorbing arithmetic residue -- the margin's job is
        # float residue in the transformed side, not the touching itself
        # (design.md section 4, task 1.5). Do not extend this to a
        # rotated fixture: it would be flaky at margin 0 by design, which
        # is the very reason the margin exists.
        left, right, offset = self._pair()
        placed_left = test_module.placed_shape(left, np.eye(4))
        placed_right = test_module.placed_shape(right, offset)

        with patch.object(test_module, '_FACE_BOX_MARGIN', 0.0):
            proven = test_module._faces_disjoint(
                left, placed_left, right, placed_right, offset)

        self.assertFalse(
            proven, 'flush contact was culled even at zero margin')


class ClassifierLoadedSolidBySolidTest(FaceBoxCullingTestCase):
    """Pins design.md section 1 step 4 against a later simplification
    that would rest on unspecified `BRepClass3d_SolidClassifier`
    behaviour for a compound: the classifier must be loaded from one
    SOLID at a time, never from a compound."""

    def test_the_classifier_is_constructed_only_from_solids(self):
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier as Real
        from OCP.TopAbs import TopAbs_SOLID

        frame, wheel = _frame_and_wheel()
        frame_shape = self.brep(frame, 'frame')
        wheel_shape = self.brep(wheel, 'wheel')
        identity = np.eye(4)
        placed_frame = test_module.placed_shape(frame_shape, identity)
        placed_wheel = test_module.placed_shape(wheel_shape, identity)

        with patch('OCP.BRepClass3d.BRepClass3d_SolidClassifier',
                   wraps=Real) as classifier:
            proven = test_module._faces_disjoint(
                frame_shape, placed_frame, wheel_shape, placed_wheel,
                identity)

        self.assertTrue(proven)
        self.assertTrue(classifier.call_args_list,
                        'the guard never constructed a classifier')
        for call in classifier.call_args_list:
            (loaded,), _ = call
            self.assertEqual(
                loaded.ShapeType(), TopAbs_SOLID,
                'the classifier was loaded from something other than '
                'one solid')


class MarginTest(FaceBoxCullingTestCase):

    def _pair(self, gap):
        left = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'left')
        right = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'right')
        matrix = np.eye(4)
        matrix[0, 3] = 2.0 + gap
        return left, right, matrix

    def test_a_gap_under_the_margin_declines(self):
        left, right, matrix = self._pair(test_module._FACE_BOX_MARGIN / 10)
        placed_left = test_module.placed_shape(left, np.eye(4))
        placed_right = test_module.placed_shape(right, matrix)

        proven = test_module._faces_disjoint(
            left, placed_left, right, placed_right, matrix)

        self.assertFalse(
            proven,
            'a gap smaller than the margin must decline, not decide')

    def test_a_gap_well_beyond_the_margin_is_decided(self):
        left, right, matrix = self._pair(1000 * test_module._FACE_BOX_MARGIN)
        placed_left = test_module.placed_shape(left, np.eye(4))
        placed_right = test_module.placed_shape(right, matrix)

        proven = test_module._faces_disjoint(
            left, placed_left, right, placed_right, matrix)

        self.assertTrue(proven)

    def test_the_margin_is_what_moved_the_boundary(self):
        """Between the two cases above, patching the margin to 0 turns
        the small-gap pair from a decline into a decision -- pinning
        that the margin, not something else (such as OCCT's own face-box
        tolerance enlargement, which alone is well under this gap), is
        what moved the boundary."""
        left, right, matrix = self._pair(test_module._FACE_BOX_MARGIN / 2)
        placed_left = test_module.placed_shape(left, np.eye(4))
        placed_right = test_module.placed_shape(right, matrix)

        with patch.object(test_module, '_FACE_BOX_MARGIN', 0.0):
            proven = test_module._faces_disjoint(
                left, placed_left, right, placed_right, matrix)

        self.assertTrue(proven)


class CompoundStraddlingTest(FaceBoxCullingTestCase):
    """One component of a compound sits inside the partner, one entirely
    outside, and no boundaries meet anywhere. Exactly why one
    representative per SOLID is classified rather than one per shape."""

    def _compound_and_big(self):
        big = cq.Workplane('XY').box(10, 10, 10).val()
        outside = cq.Workplane('XY').box(2, 2, 2).translate((0, 0, 50)).val()
        inside = cq.Workplane('XY').box(2, 2, 2).val()
        # `outside` first: the mutation test below relies on it being
        # `.Solids()[0]`.
        compound = cq.Compound.makeCompound([outside, inside])
        return compound, big

    def test_one_component_inside_the_partner_still_runs_the_boolean(self):
        compound, big = self._compound_and_big()
        compound_shape = self.brep(compound, 'compound')
        big_shape = self.brep(big, 'big')
        identity = np.eye(4)

        with self.counted_boolean() as boolean:
            stats = self.exact_pair(
                compound_shape, identity, big_shape, identity,
                'compound', 'big')

        self.assertEqual(boolean.call_count, 1)
        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 8.0)

    def test_classifying_only_the_first_solid_wrongly_proves_it_empty(self):
        """The mutation that proves this test: taking only the FIRST
        solid of each shape (here, the OUTSIDE component, which really
        is mutually outside the partner) makes the guard miss the INSIDE
        component entirely and wrongly report the pair empty. Restore
        the real per-solid loop after this assertion; this proves the
        test, it is not a change to keep."""
        compound, big = self._compound_and_big()
        compound_shape = self.brep(compound, 'compound')
        big_shape = self.brep(big, 'big')
        identity = np.eye(4)
        placed_compound = test_module.placed_shape(compound_shape, identity)
        placed_big = test_module.placed_shape(big_shape, identity)

        def one_solid_only(placed1, placed2):
            from OCP.BRepClass3d import BRepClass3d_SolidClassifier
            from OCP.gp import gp_Pnt
            from OCP.Precision import Precision
            from OCP.TopAbs import TopAbs_OUT
            solids1 = placed1.Solids()[:1]
            solids2 = placed2.Solids()[:1]
            if not solids1 or not solids2:
                return False
            points1 = test_module._representative_points(solids1, gp_Pnt)
            points2 = test_module._representative_points(solids2, gp_Pnt)
            if points1 is None or points2 is None:
                return False
            tolerance = Precision.Confusion_s()
            return (test_module._classified_out(
                        points1, solids2, BRepClass3d_SolidClassifier,
                        TopAbs_OUT, tolerance)
                    and test_module._classified_out(
                        points2, solids1, BRepClass3d_SolidClassifier,
                        TopAbs_OUT, tolerance))

        with patch.object(test_module, '_mutually_outside',
                          side_effect=one_solid_only):
            proven = test_module._faces_disjoint(
                compound_shape, placed_compound, big_shape, placed_big,
                identity)

        self.assertTrue(
            proven,
            'mutation check: classifying only one solid per shape must '
            'wrongly prove this straddling pair empty -- if it does not, '
            'this test protects nothing')


class BothDirectionsNeededTest(FaceBoxCullingTestCase):
    """Two failure shapes, each caught by only ONE of the two
    classification directions (design.md section 2)."""

    def _direction_only(self, keep):
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.gp import gp_Pnt
        from OCP.Precision import Precision
        from OCP.TopAbs import TopAbs_OUT

        def weakened(placed1, placed2):
            solids1 = placed1.Solids()
            solids2 = placed2.Solids()
            if not solids1 or not solids2:
                return False
            points1 = test_module._representative_points(solids1, gp_Pnt)
            points2 = test_module._representative_points(solids2, gp_Pnt)
            if points1 is None or points2 is None:
                return False
            tolerance = Precision.Confusion_s()
            if keep == 'first':
                return test_module._classified_out(
                    points1, solids2, BRepClass3d_SolidClassifier,
                    TopAbs_OUT, tolerance)
            return test_module._classified_out(
                points2, solids1, BRepClass3d_SolidClassifier,
                TopAbs_OUT, tolerance)

        return patch.object(test_module, '_mutually_outside',
                            side_effect=weakened)

    def test_shape_one_inside_shape_two_needs_the_first_direction(self):
        """Shape 1 (small) is wholly inside shape 2 (big): shape 1's own
        points classify IN shape 2, which is the ONLY direction that
        catches it -- shape 2's points are OUT of shape 1 regardless.
        Dropping shape 1's own check (keeping only the second direction)
        must wrongly prove this pair empty."""
        small = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'small')
        big = self.brep(cq.Workplane('XY').box(10, 10, 10).val(), 'big')
        identity = np.eye(4)
        placed_small = test_module.placed_shape(small, identity)
        placed_big = test_module.placed_shape(big, identity)

        with self._direction_only('second'):
            proven = test_module._faces_disjoint(
                small, placed_small, big, placed_big, identity)

        self.assertTrue(
            proven,
            'mutation check: dropping shape 1\'s own classification must '
            'wrongly prove containment empty, or this test protects '
            'nothing')

    def test_shape_two_embedded_in_a_wall_needs_the_second_direction(self):
        """Shape 2 sits entirely embedded in the solid WALL of a hollow
        shape 1, touching no face of it: shape 2's own points classify IN
        shape 1's material, which is the ONLY direction that catches it
        -- shape 1's own points (outer corners) are OUT of the tiny
        embedded solid regardless. Dropping shape 2's own check (keeping
        only the first direction) must wrongly prove this pair empty."""
        hollow = self.brep(
            cq.Workplane('XY').box(20, 20, 20)
            .faces('>Z').workplane().rect(10, 10).cutBlind(-15).val(),
            'hollow')
        embedded = self.brep(
            cq.Workplane('XY').box(1, 1, 1).translate((8, 8, 8)).val(),
            'embedded')
        identity = np.eye(4)
        placed_hollow = test_module.placed_shape(hollow, identity)
        placed_embedded = test_module.placed_shape(embedded, identity)

        with self._direction_only('first'):
            proven = test_module._faces_disjoint(
                hollow, placed_hollow, embedded, placed_embedded, identity)

        self.assertTrue(
            proven,
            'mutation check: dropping shape 2\'s own classification must '
            'wrongly prove wall-embedding empty, or this test protects '
            'nothing')


class DeclineTest(FaceBoxCullingTestCase):
    """Every way the tier is specified to decline rather than decide --
    and never to raise while doing it."""

    def test_a_faceless_shape_declines(self):
        edge = cq.Edge.makeLine(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0))
        box = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'box')
        placed_edge = test_module.placed_shape(edge, np.eye(4))
        placed_box = test_module.placed_shape(box, np.eye(4))

        proven = test_module._faces_disjoint(
            edge, placed_edge, box, placed_box, np.eye(4))

        self.assertFalse(proven)

    def test_a_shape_with_no_solids_declines(self):
        base = cq.Workplane('XY').box(2, 2, 2).val()
        shell = cq.Shell.makeShell(base.Faces()[:-1])
        self.assertEqual(len(shell.Solids()), 0,
                         'fixture bug: the open shell has a solid')
        far = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'far')
        matrix = np.eye(4)
        matrix[0, 3] = 100
        placed_shell = test_module.placed_shape(shell, np.eye(4))
        placed_far = test_module.placed_shape(far, matrix)

        proven = test_module._faces_disjoint(
            shell, placed_shell, far, placed_far, matrix)

        self.assertFalse(proven)

    def test_a_solid_with_no_vertices_declines(self):
        shape1 = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'a')
        shape2 = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'b')
        matrix = np.eye(4)
        matrix[0, 3] = 100
        placed1 = test_module.placed_shape(shape1, np.eye(4))
        placed2 = test_module.placed_shape(shape2, matrix)

        class NoVertexSolid:
            def Vertices(self):
                return []

        class FakePlaced:
            def Solids(self):
                return [NoVertexSolid()]

        proven = test_module._faces_disjoint(
            shape1, FakePlaced(), shape2, placed2, matrix)

        self.assertFalse(proven)

    def test_a_non_finite_relative_matrix_declines(self):
        shape1 = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'a')
        shape2 = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'b')
        placed1 = test_module.placed_shape(shape1, np.eye(4))
        degenerate = np.eye(4)
        degenerate[0, 0] = np.nan

        proven = test_module._faces_disjoint(
            shape1, placed1, shape2, placed1, degenerate)

        self.assertFalse(proven)

    def _classifier_states(self):
        frame, wheel = _frame_and_wheel()
        frame_shape = self.brep(frame, 'frame')
        wheel_shape = self.brep(wheel, 'wheel')
        identity = np.eye(4)
        placed_frame = test_module.placed_shape(frame_shape, identity)
        placed_wheel = test_module.placed_shape(wheel_shape, identity)
        return frame_shape, placed_frame, wheel_shape, placed_wheel, identity

    def _decline_with(self, stub_classifier):
        (frame_shape, placed_frame, wheel_shape, placed_wheel,
         identity) = self._classifier_states()

        with patch('OCP.BRepClass3d.BRepClass3d_SolidClassifier',
                   return_value=stub_classifier):
            proven = test_module._faces_disjoint(
                frame_shape, placed_frame, wheel_shape, placed_wheel,
                identity)

        self.assertFalse(proven)

    def test_a_classifier_reporting_on_declines(self):
        from OCP.TopAbs import TopAbs_ON

        class OnClassifier:
            def Perform(self, point, tolerance):
                pass

            def Rejected(self):
                return False

            def State(self):
                return TopAbs_ON

        self._decline_with(OnClassifier())

    def test_a_classifier_reporting_unknown_declines(self):
        from OCP.TopAbs import TopAbs_UNKNOWN

        class UnknownClassifier:
            def Perform(self, point, tolerance):
                pass

            def Rejected(self):
                return False

            def State(self):
                return TopAbs_UNKNOWN

        self._decline_with(UnknownClassifier())

    def test_a_rejected_classification_declines(self):
        from OCP.TopAbs import TopAbs_OUT

        class RejectedClassifier:
            def Perform(self, point, tolerance):
                pass

            def Rejected(self):
                return True

            def State(self):
                # Rejected() true means "computed by rejection, state is
                # OUT" per OCCT's own documentation -- this tier declines
                # on Rejected() regardless of the reported state.
                return TopAbs_OUT

        self._decline_with(RejectedClassifier())

    def test_a_classifier_exception_declines(self):
        def raising(*arguments, **keywords):
            raise RuntimeError('OCCT blew up')

        (frame_shape, placed_frame, wheel_shape, placed_wheel,
         identity) = self._classifier_states()

        with patch('OCP.BRepClass3d.BRepClass3d_SolidClassifier',
                   side_effect=raising):
            proven = test_module._faces_disjoint(
                frame_shape, placed_frame, wheel_shape, placed_wheel,
                identity)

        self.assertFalse(proven)


class RecordCarriesLocalShapeTest(FaceBoxCullingTestCase):
    """design.md section 6a: `_place_solid`'s trailing `record[8]` is the
    LOCAL shape, and the tier reached through `_placed_intersection`
    measures face boxes from it -- never from the placed copy."""

    def _records(self):
        frame, wheel = _frame_and_wheel()
        frame_shape = self.brep(frame, 'frame')
        wheel_shape = self.brep(wheel, 'wheel')
        identity = np.eye(4)
        zero_bounds = (np.zeros(3), np.zeros(3))
        frame_record = test_module._place_solid(
            object(), None, zero_bounds, identity, frame_shape,
            ('frame-id', 1))
        wheel_record = test_module._place_solid(
            object(), None, zero_bounds, identity, wheel_shape,
            ('wheel-id', 1))
        return frame_shape, wheel_shape, frame_record, wheel_record

    def test_record_eight_is_the_local_shape_not_the_placed_copy(self):
        frame_shape, wheel_shape, frame_record, wheel_record = (
            self._records())

        self.assertEqual(len(frame_record), 9)
        self.assertIs(frame_record[8], frame_shape)
        self.assertIsNot(frame_record[8], frame_record[3])
        self.assertEqual(
            test_module.shape_identity(frame_record[8]), frame_record[5])
        # Positions 0-7 hold what they held before.
        self.assertEqual(frame_record[6].tolist(), np.eye(4).tolist())
        self.assertIsNotNone(frame_record[3])

    def test_record_key_guard_still_separates_the_virtual_floor(self):
        _, _, frame_record, wheel_record = self._records()
        virtual_floor_shaped = (None, None, None, None)

        self.assertIsNone(
            test_module._record_key(
                virtual_floor_shaped, wheel_record, 5, 'exact'),
            'a short virtual-floor-shaped record was treated as real')
        self.assertIsNotNone(
            test_module._record_key(frame_record, wheel_record, 5, 'exact'))

    def test_the_tier_measures_face_boxes_from_the_local_shape(self):
        frame_shape, wheel_shape, frame_record, wheel_record = (
            self._records())

        with patch.object(test_module, 'cached_face_boxes',
                          wraps=test_module.cached_face_boxes) as boxes:
            with self.no_boolean():
                test_module._placed_intersection(frame_record, wheel_record)

        measured = [call.args[0] for call in boxes.call_args_list]
        self.assertIn(frame_shape, measured)
        self.assertIn(wheel_shape, measured)
        self.assertNotIn(frame_record[3], measured)
        self.assertNotIn(wheel_record[3], measured)


class FaceBoxCacheTest(FaceBoxCullingTestCase):

    def test_cached_face_boxes_is_measured_once_per_identity(self):
        from OCP.BRepBndLib import BRepBndLib

        shape = self.brep(cq.Workplane('XY').box(2, 2, 2).val(), 'cached')

        with patch.object(BRepBndLib, 'Add_s',
                          wraps=BRepBndLib.Add_s) as add:
            first = test_module.cached_face_boxes(shape)
            second = test_module.cached_face_boxes(shape)

        self.assertEqual(
            add.call_count, len(shape.Faces()),
            'the second call re-measured the shape\'s faces')
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.shape, (len(shape.Faces()), 2, 3))
        self.assertEqual(first.dtype, np.float64)

    def test_a_rebuild_evicts_the_cached_face_boxes(self):
        from solid_node.exact import _face_box_cache, _shape_keys

        path = os.path.join(self.tmpdir.name, 'evict.brep')
        write_brep(cq.Workplane('XY').box(2, 2, 2).val(), path, 1 * 10 ** 9)
        shape = cached_shape(path)
        test_module.cached_face_boxes(shape)
        key = _shape_keys[id(shape)]
        self.assertIn(key, _face_box_cache)

        write_brep(cq.Workplane('XY').box(4, 4, 4).val(), path, 2 * 10 ** 9)
        rebuilt = cached_shape(path)
        test_module.cached_face_boxes(rebuilt)

        self.assertNotIn(key, _face_box_cache,
                         'a rebuild did not evict the old face boxes')

    def test_a_shape_with_no_identity_is_measured_and_not_cached(self):
        from solid_node.exact import _face_box_cache

        shape = cq.Workplane('XY').box(2, 2, 2).val()
        before = len(_face_box_cache)

        boxes = test_module.cached_face_boxes(shape)

        self.assertEqual(len(_face_box_cache), before)
        self.assertEqual(boxes.shape, (6, 2, 3))
        self.assertEqual(boxes.dtype, np.float64)


class ConservativeUnderTriangulationTest(FaceBoxCullingTestCase):
    """A triangulation's vertices lie ON the exact surface, so a face box
    taken with `useTriangulation=True` could shrink below it; this tier's
    boxes must still reach the exact extent regardless."""

    def test_face_boxes_reach_the_exact_radius_under_a_triangulation(self):
        from OCP.BRepMesh import BRepMesh_IncrementalMesh

        shape = self.brep(
            cq.Workplane('XY').circle(5).extrude(10).val(), 'cylinder')
        BRepMesh_IncrementalMesh(shape.wrapped, 0.5)

        boxes = test_module.cached_face_boxes(shape)

        low = boxes[:, 0, :].min(axis=0)
        high = boxes[:, 1, :].max(axis=0)
        self.assertLessEqual(low[0], -5.0)
        self.assertGreaterEqual(high[0], 5.0)
        self.assertLessEqual(low[1], -5.0)
        self.assertGreaterEqual(high[1], 5.0)
