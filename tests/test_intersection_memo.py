# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""An intersection verdict is computed once per run.

A pair's verdict depends on its two geometries and their RELATIVE rigid
placement and on nothing else: emptiness and volume are invariant under a
common rigid transform, so two solids moved together share exactly the
volume they shared before. Asking the same question twice therefore has a
provably identical answer, and the animation sweep asks it constantly --
`@testing_steps(73)` recompares an assembly's static structure at every
instant though none of those pairs has moved relative to any other.

Measured on the v8-engine suite before this change: 36 347 comparisons,
19 747 of them (54%) repeating a key the run had already decided, worth
1108 s of its 1687 s. See `spike/interference/FINDINGS.md`.

The cache is a recomputation shortcut of the same kind as the AABB broad
phase -- it must never change a verdict. So the tests below pair every
"served from cache" assertion with the ones that pin what must still be
recomputed: a pair that really moved, a part that was rebuilt, a node with
no stable geometry identity, and the flush-contact verdict whose exact
0.0 mm3 volume the strict `volume_epsilon` default depends on.

The byte key above asks a narrower question than it means to. Measured on
3DPrintedClocks `wall_clock_02` under the exact kernel
(`workflow/warts.md`, "3DPrintedClocks wall clock 02 (2026-09-09, exact
sweep cost)"): a sweep instant costs ~19 s, almost all of it in
`BRepAlgoAPI_Common`. Of 118 candidate pairs per instant, 30 are rigidly
carried together by a parent -- the pendulum, the motion works, the
weight and its line -- and recompose a relative matrix that differs from
the previous instant's by ~1e-13 of float noise: the residue of composing
the same rigid motion through a different multiplication order, not a
real difference in placement. Only 5 pairs hit the byte key. The tests
below add that noise, the quantum that absorbs it, its boundary, its
`0` escape hatch, and the guarantee that only the verdict KEY is
quantised -- never the geometry a comparison is handed.
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import cadquery as cq
import numpy as np
from trimesh.creation import box

import solid_node.test as test_module
from solid_node.exact import _placement_cache, cached_shape, write_brep
from solid_node.node.base import AbstractBaseNode, _compose_world_matrix
from solid_node.node.operations import Rotation, Translation


class FakeNode:
    """Duck-typed stand-in exposing what the intersection path needs,
    reusing the REAL mesh getter -- the same pattern as
    tests/test_broad_phase_culling.py's FakeNode."""

    exact = False

    def __init__(self, name, stl_file):
        self.name = name
        self.stl_file = stl_file
        self.operations = []
        self._parent = None

    def as_number(self, value):
        return float(value)

    @property
    def mesh(self):
        return AbstractBaseNode.mesh.fget(self)


class MeshOnlyNode:
    """A node with no geometry file at all -- the test-double shape the
    `.mesh` fallback exists for. It has no stable identity, so it must
    never be cached."""

    exact = False

    def __init__(self, name, mesh):
        self.name = name
        self.mesh = mesh


class ExactFakeNode:
    """A minimal exact node whose shape has the stable cache identity the
    exact path's memo key needs -- the same `cached_shape`/`write_brep`
    technique `tests/test_exact_geometry.py`'s exact fixtures use, kept
    self-contained here rather than imported across test modules."""

    exact = True

    def __init__(self, name, brep_path):
        self.name = name
        self.operations = []
        self._parent = None
        self._brep_path = brep_path

    def shape(self):
        return cached_shape(self._brep_path)

    def as_number(self, value):
        return float(value)


class Parent:
    """A rigid parent carrying its own operations only. Two children
    composing the SAME parent operations into their own chain through the
    real `_compose_world_matrix` is exactly "carried together" -- the
    shape of the wall-clock-02 finding, not a stand-in for it."""

    def __init__(self):
        self.operations = []


class MemoTestCase(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.box_path = os.path.join(self.tmpdir.name, 'box.stl')
        box((2, 2, 2)).export(self.box_path)
        test_module._verdict_cache.clear()
        self._set_quantum(test_module.DEFAULT_PLACEMENT_QUANTUM)
        self.addCleanup(test_module.set_comparison_policy, None)

    def _set_quantum(self, quantum):
        """Fix the run's placement quantum -- the default unless a test
        overrides it -- while leaving the kernel and epsilon at what
        every scenario in this file already assumes: exact, strict."""
        test_module.set_comparison_policy(
            test_module.ComparisonPolicy('exact', 0.0, quantum))

    def _translated(self, name, translation):
        node = FakeNode(name, self.box_path)
        node.operations.append(Translation(translation, node))
        return node

    def _exact_brep(self, name, size=(1, 1, 1)):
        """An exact node backed by a written BREP, so `shape_identity`
        has something stable to key the exact path's memo on."""
        path = os.path.join(self.tmpdir.name, f'{name}.brep')
        write_brep(cq.Workplane('XY').box(*size).val(), path, 1 * 10 ** 9)
        return ExactFakeNode(name, path)

    def _carried_pair(self, first, second):
        """Attach `first` and `second` to a shared rigid parent and
        return it, so a test can move the pair together by appending an
        operation to the PARENT's own chain."""
        parent = Parent()
        first._parent = parent
        second._parent = parent
        return parent

    def _relative_matrix(self, first, second):
        return (np.linalg.inv(_compose_world_matrix(first))
               @ _compose_world_matrix(second))

    def _counted(self):
        """Patch the faceted kernel read so a boolean actually running is
        observable. `Manifold.__xor__` is the operation the fast path
        performs; counting calls to the helper that performs it is what
        distinguishes a served verdict from a recomputed one."""
        return patch.object(test_module, '_faceted_verdict',
                            wraps=test_module._faceted_verdict)


class RepeatedComparisons(MemoTestCase):

    def test_a_repeated_comparison_is_not_recomputed(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        with self._counted() as verdict:
            before = test_module._intersection_stats(first, second)
            after = test_module._intersection_stats(first, second)

        self.assertEqual(tuple(before), tuple(after))
        self.assertEqual(verdict.call_count, 1,
                         'the repeated comparison ran a boolean')

    def test_a_pair_moved_together_is_not_recomputed(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        with self._counted() as verdict:
            before = test_module._intersection_stats(first, second)
            first.operations.append(Translation([40, 7, -3], first))
            second.operations.append(Translation([40, 7, -3], second))
            after = test_module._intersection_stats(first, second)

        self.assertEqual(tuple(before), tuple(after))
        self.assertEqual(verdict.call_count, 1,
                         'a rigidly co-moved pair ran a second boolean')

    def test_a_moved_pair_is_recomputed(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        with self._counted() as verdict:
            overlapping = test_module._intersection_stats(first, second)
            second.operations.append(Translation([1000, 0, 0], second))
            separated = test_module._intersection_stats(first, second)

        self.assertFalse(overlapping.is_empty)
        self.assertTrue(separated.is_empty,
                        'a genuinely moved pair kept the old verdict')
        # Two computations, not one: the moved pair is a different key.
        # The second is decided by the broad phase inside the verdict
        # helper rather than by a boolean, which is where culling belongs
        # -- the memo skips the whole evaluation, culling skips the
        # kernel within it.
        self.assertEqual(verdict.call_count, 2,
                         'a genuinely moved pair was served the old verdict')

    def test_a_rotated_pair_is_recomputed(self):
        # A rotation changes the relative placement without changing any
        # translation, so it catches a key built from positions alone.
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        with self._counted() as verdict:
            before = test_module._intersection_stats(first, second)
            second.operations.append(Rotation(90, [0, 0, 1], second))
            after = test_module._intersection_stats(first, second)

        self.assertEqual(verdict.call_count, 2,
                         'a rotated pair was served the old verdict')
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)


class CacheValidity(MemoTestCase):

    def test_a_rebuilt_part_is_recomputed(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        overlapping = test_module._intersection_stats(first, second)
        self.assertFalse(overlapping.is_empty)

        # Same path, new geometry and new mtime: a shrunken box that no
        # longer reaches its neighbour.
        box((0.5, 0.5, 0.5)).export(self.box_path)
        os.utime(self.box_path, (2 * 10 ** 9, 2 * 10 ** 9))
        after = test_module._intersection_stats(first, second)

        self.assertTrue(after.is_empty,
                        'a rebuilt part was served its old verdict')

    def test_a_mesh_only_node_is_not_cached(self):
        mesh = box((2, 2, 2))
        moved = box((2, 2, 2))
        moved.apply_translation([1.5, 0, 0])
        first = MeshOnlyNode('First', mesh)
        second = MeshOnlyNode('Second', moved)

        overlapping = test_module._intersection_stats(first, second)
        second.mesh = box((2, 2, 2))
        second.mesh.apply_translation([1000, 0, 0])
        separated = test_module._intersection_stats(first, second)

        self.assertFalse(overlapping.is_empty)
        self.assertTrue(separated.is_empty,
                        'a node with no geometry identity was cached')
        self.assertEqual(len(test_module._verdict_cache), 0,
                         'a node with no geometry identity got an entry')

    def test_a_faceted_entry_never_serves_an_exact_comparison(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        faceted = test_module._intersection_stats(first, second)
        self.assertFalse(faceted.exact)

        entries = list(test_module._verdict_cache)
        self.assertTrue(entries, 'the faceted comparison was not cached')
        for key in entries:
            self.assertIn('faceted', key,
                          'a cache key does not record its evaluation path')


class FlushContactThroughTheCache(MemoTestCase):
    """The verdict the cache is least allowed to blur.

    A real flush abutment comes back NON-EMPTY with exactly 0.0mm^3, and
    the strict `volume_epsilon=0` default reports that as a foul --
    ADR-025's contract, which ADR-029 refused to fold into emptiness. A
    cache that returned "empty" for a served flush pair, or that rounded
    its way to a different verdict on the second ask, would defeat the
    feature silently. Both asks must report exactly what the first did.
    """

    def test_a_served_flush_verdict_is_the_computed_one(self):
        first = self._translated('First', [0, 0, 0])
        # Faces coincident at x = 1: contact, no shared volume.
        second = self._translated('Second', [2, 0, 0])

        computed = test_module._intersection_stats(first, second)
        served = test_module._intersection_stats(first, second)

        self.assertEqual(tuple(computed), tuple(served))
        self.assertEqual(served.volume, computed.volume)
        self.assertEqual(served.is_empty, computed.is_empty)
        if not computed.is_empty:
            self.assertEqual(computed.volume, 0.0,
                             'flush contact reported a positive volume')


class CarriedThroughAParent(MemoTestCase):
    """The wall-clock-02 finding, reproduced directly: two children
    compose the SAME parent operations into their own chain through the
    real `_compose_world_matrix`, and the relative matrix recomposed
    after the parent moves differs from the first by float noise -- not
    by a real change in placement."""

    def test_a_pair_carried_together_through_a_parent_is_not_recomputed(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        parent = self._carried_pair(first, second)
        before = self._relative_matrix(first, second)

        with self._counted() as verdict:
            first_stats = test_module._intersection_stats(first, second)
            parent.operations.append(
                Rotation(37.123456, [0.3, 0.7, 0.1], None))
            after = self._relative_matrix(first, second)
            self.assertNotEqual(
                before.tobytes(), after.tobytes(),
                'the parent rotation produced no float noise; this '
                'scenario proves nothing')
            self.assertLess(
                np.abs(after - before).max(),
                test_module.DEFAULT_PLACEMENT_QUANTUM,
                'the noise this test produces must fit under the default '
                'quantum, or it is not the noise this cycle is about')
            second_stats = test_module._intersection_stats(first, second)

        self.assertEqual(tuple(first_stats), tuple(second_stats))
        self.assertEqual(verdict.call_count, 1,
                         'a pair carried together by its parent ran a '
                         'second boolean')

    def test_a_pair_displaced_by_more_than_the_quantum_is_recomputed(self):
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        self._carried_pair(first, second)

        with self._counted() as verdict:
            test_module._intersection_stats(first, second)
            second.operations.append(Translation(
                [10 * test_module.DEFAULT_PLACEMENT_QUANTUM, 0, 0], second))
            test_module._intersection_stats(first, second)

        self.assertEqual(verdict.call_count, 2,
                         'a pair displaced past the quantum was served '
                         'the old verdict')

    def test_a_zero_quantum_restores_the_exact_key(self):
        self._set_quantum(0)
        first = self._translated('First', [0, 0, 0])
        second = self._translated('Second', [1.5, 0, 0])
        parent = self._carried_pair(first, second)
        before = self._relative_matrix(first, second)

        with self._counted() as verdict:
            test_module._intersection_stats(first, second)
            parent.operations.append(
                Rotation(37.123456, [0.3, 0.7, 0.1], None))
            after = self._relative_matrix(first, second)
            self.assertNotEqual(
                before.tobytes(), after.tobytes(),
                'the parent rotation produced no float noise; this '
                'scenario proves nothing')
            test_module._intersection_stats(first, second)

        self.assertEqual(verdict.call_count, 2,
                         'a quantum of 0 must key on the exact bytes, as '
                         'ADR-070 specified')


class SignedZeroDoesNotSplitACell(MemoTestCase):

    def test_signed_zero_does_not_split_a_cell(self):
        base = np.eye(4)
        negative_zero = base.copy()
        negative_zero[0, 3] = -0.0
        positive_zero = base.copy()
        positive_zero[0, 3] = 0.0
        self.assertNotEqual(
            negative_zero.tobytes(), positive_zero.tobytes(),
            'numpy stopped distinguishing -0.0 from 0.0 in bytes; this '
            'scenario proves nothing')

        negative_key = test_module._verdict_key(
            'a', base, 'b', negative_zero, 'exact')
        positive_key = test_module._verdict_key(
            'a', base, 'b', positive_zero, 'exact')

        self.assertEqual(negative_key, positive_key)


class ExactKernelQuantisation(MemoTestCase):

    def test_the_exact_kernel_quantises_too(self):
        first = self._exact_brep('first')
        second = self._exact_brep('second')
        second.operations.append(Translation([0.5, 0, 0], second))
        parent = self._carried_pair(first, second)
        before = self._relative_matrix(first, second)

        with patch.object(test_module, 'intersect_shapes',
                          wraps=test_module.intersect_shapes) as intersect:
            test_module._intersection_stats(first, second)
            parent.operations.append(
                Rotation(37.123456, [0.3, 0.7, 0.1], None))
            after = self._relative_matrix(first, second)
            self.assertNotEqual(
                before.tobytes(), after.tobytes(),
                'the parent rotation produced no float noise; this '
                'scenario proves nothing')
            test_module._intersection_stats(first, second)

        self.assertEqual(intersect.call_count, 1,
                         'the exact kernel ran a second OCCT boolean for '
                         'a pair carried together by its parent')


class NonFiniteRelativeMatrixYieldsNoKey(MemoTestCase):
    """A composed matrix that is already non-finite -- a degenerate
    operation's input, e.g. an unresolved keyframe expression, not a
    singular inversion (`np.linalg.inv` raises `LinAlgError` on an
    exactly singular matrix rather than returning inf/nan, so a
    degenerate SOURCE matrix, not a literally singular one, is the
    realistic route `_verdict_key` must refuse; design.md decision 1)."""

    def test_a_non_finite_relative_matrix_yields_no_key(self):
        degenerate = np.eye(4)
        degenerate[0, 0] = np.nan
        self.assertIsNone(test_module._verdict_key(
            'a', degenerate, 'b', np.eye(4), 'exact'))

    def test_a_non_finite_relative_matrix_is_never_cached(self):
        non_finite = np.eye(4) * np.nan
        key = test_module._verdict_key(
            'a', np.eye(4), 'b', non_finite, 'exact')
        self.assertIsNone(key)

        computed = []

        def compute():
            computed.append(True)
            return test_module.IntersectionStats(True, 0.0, True)

        test_module._memoized(key, compute)
        test_module._memoized(key, compute)

        self.assertEqual(len(computed), 2,
                         'a non-finite relative matrix was cached')
        self.assertEqual(len(test_module._verdict_cache), 0)


class TwoQuantaNeverCrossServe(MemoTestCase):

    def test_two_quanta_in_one_process_never_cross_serve(self):
        q = 1e-6
        matrix_at_q = np.eye(4)
        matrix_at_q[0, 3] = q  # cell 1 at quantum q ...
        matrix_at_double_q = np.eye(4)
        matrix_at_double_q[0, 3] = 2 * q  # ... and cell 1 at quantum 2q too

        self._set_quantum(q)
        key_q = test_module._verdict_key(
            'a', np.eye(4), 'b', matrix_at_q, 'exact')
        self._set_quantum(2 * q)
        key_double_q = test_module._verdict_key(
            'a', np.eye(4), 'b', matrix_at_double_q, 'exact')

        self.assertNotEqual(
            key_q, key_double_q,
            'two placements chosen to land on the same integer cell at '
            'different quanta served one another')


class PlacedGeometryIsNotQuantised(MemoTestCase):

    def test_the_placed_geometry_is_not_quantised(self):
        first = self._exact_brep('first')
        second = self._exact_brep('second')
        second.operations.append(Translation([0.5, 0, 0], second))

        test_module._intersection_stats(first, second)
        test_module._verdict_cache.clear()

        second.operations.append(Translation(
            [test_module.DEFAULT_PLACEMENT_QUANTUM / 4, 0, 0], second))
        test_module._intersection_stats(first, second)

        identity = test_module.shape_identity(second.shape())
        matrices = [key[1] for key in _placement_cache if key[0] == identity]
        self.assertEqual(len(matrices), 2,
                         'two comparisons at different exact placements '
                         'shared one placed geometry')
        self.assertNotEqual(matrices[0], matrices[1],
                            'the placed geometry was quantised')
