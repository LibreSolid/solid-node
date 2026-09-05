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
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

from trimesh.creation import box

import solid_node.test as test_module
from solid_node.node.base import AbstractBaseNode
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


class MemoTestCase(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.box_path = os.path.join(self.tmpdir.name, 'box.stl')
        box((2, 2, 2)).export(self.box_path)
        test_module._verdict_cache.clear()

    def _translated(self, name, translation):
        node = FakeNode(name, self.box_path)
        node.operations.append(Translation(translation, node))
        return node

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
