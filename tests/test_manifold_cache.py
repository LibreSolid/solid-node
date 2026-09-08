# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for docs/performance-improvement.md fix 3: caching
one manifold3d.Manifold per strong artifact observation -- admissibility judged
ONCE at cache fill, by the engine's own status -- instead of trimesh.boolean.intersection
re-checking watertightness and re-converting both meshes on EVERY
call. Per placement the cached Manifold is transformed (lazy) by the
composed world matrix and intersected directly (`a ^ b`), reading
is_empty()/volume() without ever converting the result back to a
trimesh.

FakeNode reuses the real AbstractBaseNode.mesh getter (same pattern as
tests/test_node_mesh_cache.py and tests/test_broad_phase_culling.py),
but the fast-path tests below monkeypatch solid_node.test's internals
directly rather than relying on real geometry, so the CRITICAL
volume_epsilon-vs-emptiness semantics can be pinned deterministically
rather than depending on real boolean noise.
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import trimesh
from trimesh.creation import box

import solid_node.test as test_module
from solid_node.mesh_engine import mesh_engine
from solid_node.node.base import AbstractBaseNode
from solid_node.node.operations import Translation
from solid_node.test import TestCase as AssertingTestCase


asserter = AssertingTestCase()


class FakeNode:

    def __init__(self, name, stl_file):
        self.name = name
        self.stl_file = stl_file
        self.operations = []
        self._parent = None

    def as_number(self, n):
        return float(n)

    base_mesh = AbstractBaseNode.base_mesh

    @property
    def mesh(self):
        return AbstractBaseNode.mesh.fget(self)


class MeshRaisesIfTouched(FakeNode):
    """Proves the fast path never falls back to node.mesh at all (no
    round trip): accessing .mesh is a hard failure."""

    @property
    def mesh(self):
        raise AssertionError(
            f'.mesh should never be accessed on the fast path for {self.name}')


class ManifoldCacheTestCase(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.box_path = os.path.join(self.tmpdir.name, 'box.stl')
        box((2, 2, 2)).export(self.box_path)

    def _part(self, name, translation=None):
        node = MeshRaisesIfTouched(name, self.box_path)
        if translation is not None:
            node.operations.append(Translation(translation, node))
        return node


class ManifoldCacheBuiltOnceTest(ManifoldCacheTestCase):
    """One Manifold built per strong artifact observation, shared across every
    assertion call and every node instance backed by that file --
    however many pairwise checks touch it."""

    def test_repeated_assertions_build_the_manifold_once(self):
        origin = self._part('Origin')
        near = self._part('Near', [0.5, 0, 0])
        far = self._part('Far', [1000, 0, 0])

        calls = []
        original_manifold, original_mesh = mesh_engine()

        def counting(*args, **kwargs):
            calls.append(1)
            return original_manifold(*args, **kwargs)

        # The engine is now resolved at the point of use rather than
        # bound as a module attribute, so the seam that counts real
        # constructions is the resolver. The contract under test is
        # unchanged: ONE build per artifact observation, however many
        # assertions touch it.
        with patch('solid_node.test.require_mesh_engine',
                   return_value=(counting, original_mesh)):
            asserter.assertNotIntersecting(origin, far)
            asserter.assertIntersecting(origin, near)
            asserter.assertNotIntersecting(near, far)

        # One STL (box.stl) shared by all three nodes -> one Manifold
        # build, however many pairwise assertions touch it.
        self.assertEqual(len(calls), 1)

    def test_never_falls_back_to_node_mesh(self):
        # MeshRaisesIfTouched.mesh raises if ever accessed -- if any
        # of these pass, the fast path never touched .mesh.
        origin = self._part('Origin')
        near = self._part('Near', [0.5, 0, 0])
        far = self._part('Far', [1000, 0, 0])

        asserter.assertNotIntersecting(origin, far)
        asserter.assertIntersecting(origin, near)


class MeshEngineGateTest(ManifoldCacheTestCase):
    """The mesh engine judges its own input: a Manifold whose status is
    not NoError is refused by name, once, at the first faceted read; a
    mesh trimesh doubts and the engine accepts is compared like any
    other."""

    def test_a_mesh_the_engine_refuses_names_the_file_and_status(self):
        # A box missing one triangle: not a manifold, to anyone.
        holey = trimesh.creation.box((2, 2, 2))
        holey.faces = holey.faces[:-1]
        holey_path = os.path.join(self.tmpdir.name, 'holey.stl')
        holey.export(holey_path)
        self.assertFalse(trimesh.load(holey_path).is_volume)

        part = self._part('Holey')
        part.stl_file = holey_path
        against = self._part('Against', [0.5, 0, 0])

        with self.assertRaises(ValueError) as ctx:
            asserter.assertNotIntersecting(part, against)

        self.assertIn(holey_path, str(ctx.exception))
        self.assertIn('NotManifold', str(ctx.exception))
        self.assertFalse(any(key[0] == holey_path
                             for key in test_module._manifold_cache))

    def test_a_mesh_trimesh_doubts_and_the_engine_accepts_is_compared(self):
        # Two boxes sharing one edge, as OpenSCAD 2021.01 exports a
        # snap tab against its wall: the edge belongs to four faces, so
        # trimesh calls the mesh non-watertight and two bodies, while
        # the engine builds it with NoError and the volume of both.
        shared = trimesh.util.concatenate([
            trimesh.creation.box((2, 2, 2)),
            trimesh.creation.box((2, 2, 2)).apply_translation([2, 2, 0])])
        shared.merge_vertices()
        shared_path = os.path.join(self.tmpdir.name, 'shared_edge.stl')
        shared.export(shared_path)
        self.assertFalse(trimesh.load(shared_path).is_watertight)

        part = self._part('Tabbed')
        part.stl_file = shared_path
        near = self._part('Near', [2.5, 2.5, 0])
        far = self._part('Far', [1000, 0, 0])

        asserter.assertIntersecting(part, near)
        asserter.assertNotIntersecting(part, far)
        asserter.assertIntersectVolumeAbove(part, near, 3.0)


class VolumeEpsilonEmptinessSemanticsTest(ManifoldCacheTestCase):
    """volume_epsilon-vs-emptiness semantics pin
    (docs/performance-improvement.md fix 3, reconciled against the
    pre-existing improvements.md #21 contract -- see the deviation
    noted in this toolmaker's final report): at volume_epsilon == 0
    (the default), the verdict is Manifold's OWN is_empty() alone --
    it must NOT be folded with "or volume() == 0", because a real
    flush abutment reproducibly comes back non-empty with EXACTLY
    0.0mm^3 volume in BOTH trimesh and Manifold (verified directly
    against tests/meta_project/flush_strict.py's built geometry), and
    #21's strict default must keep reporting that as a foul --
    demonstrated end-to-end in tests/test_meta.py's
    VolumeEpsilonMetaTest. At volume_epsilon > 0 the raw volume is
    compared against the epsilon exactly as before (unaffected by the
    is_empty question -- 0.0 is always <= any positive epsilon).
    Exercised here with a stubbed Manifold cache so all three cases
    (truly empty, non-empty-but-zero-volume, genuinely non-empty) are
    deterministic rather than dependent on real boolean noise.
    """

    class _FakeManifold:
        def __init__(self, is_empty, volume):
            self._is_empty = is_empty
            self._volume = volume

        def transform(self, matrix):
            return self

        def __xor__(self, other):
            return self

        def is_empty(self):
            return self._is_empty

        def volume(self):
            return self._volume

    def _stub_cache(self, manifold):
        # Bounds/matrices overlap trivially (both at the origin, no
        # operations) so the broad-phase never culls -- the stub
        # manifold's ^ / is_empty / volume are what get exercised.
        bounds = np.array([[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]])
        return patch('solid_node.test._cached_manifold',
                     return_value=(manifold, bounds, None))

    def test_truly_empty_manifold_is_empty(self):
        node1 = self._part('A')
        node2 = self._part('B')
        manifold = self._FakeManifold(is_empty=True, volume=0.0)

        with self._stub_cache(manifold):
            asserter.assertNotIntersecting(node1, node2)

    def test_nonempty_zero_volume_is_still_reported_by_default(self):
        # The flush-contact case (improvements.md #21): is_empty() is
        # False, but the volume Manifold reports is exactly zero --
        # the strict default (volume_epsilon == 0) must still report
        # this as a foul, matching trimesh's identical is_empty=False
        # verdict on the same real geometry pre-fix-3.
        node1 = self._part('A')
        node2 = self._part('B')
        manifold = self._FakeManifold(is_empty=False, volume=0.0)

        with self._stub_cache(manifold):
            with self.assertRaises(AssertionError) as ctx:
                asserter.assertNotIntersecting(node1, node2)

        self.assertIn('should not intersect', str(ctx.exception))

    def test_genuine_nonzero_volume_is_reported(self):
        node1 = self._part('A')
        node2 = self._part('B')
        manifold = self._FakeManifold(is_empty=False, volume=3.5)

        with self._stub_cache(manifold):
            with self.assertRaises(AssertionError) as ctx:
                asserter.assertNotIntersecting(node1, node2)

        self.assertIn('3.5', str(ctx.exception))

    def test_epsilon_above_a_nonempty_zero_volume_still_passes(self):
        node = self._part('Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = self._part('Slot')
        manifold = self._FakeManifold(is_empty=False, volume=0.0)

        with self._stub_cache(manifold):
            asserter.assertFreeWithin(node, 5, against, volume_epsilon=1e-2)

    def test_epsilon_compares_raw_volume_exactly_as_before(self):
        # volume_epsilon > 0: compare the raw volume against the
        # epsilon directly, same as the pre-Manifold code did with
        # trimesh's intersection.volume.
        node = self._part('Peg')
        node.operations.append(Translation([0, 0, 0], node))
        against = self._part('Slot')
        manifold = self._FakeManifold(is_empty=False, volume=1e-4)

        with self._stub_cache(manifold):
            asserter.assertBlockedBeyond(
                node, 10, against, volume_epsilon=1e-6)

            with self.assertRaises(AssertionError):
                asserter.assertBlockedBeyond(
                    node, 10, against, volume_epsilon=1e-2)


class RealGeometryEndToEndTest(ManifoldCacheTestCase):
    """A sanity check with genuine Manifold booleans on real STLs
    (not stubbed): verdicts and volumes must agree with trimesh's own
    boolean, within the spike's validated tolerance."""

    def test_overlapping_pair_volume_matches_trimesh(self):
        node1 = FakeNode('A', self.box_path)
        node2 = FakeNode('B', self.box_path)
        node2.operations.append(Translation([1.0, 0, 0], node2))

        reference = trimesh.boolean.intersection([node1.mesh, node2.mesh])

        is_empty, volume = test_module._intersection_stats(node1, node2)

        self.assertFalse(is_empty)
        self.assertAlmostEqual(volume, reference.volume, delta=1e-3)

    def test_disjoint_pair_is_empty(self):
        node1 = FakeNode('A', self.box_path)
        node2 = FakeNode('B', self.box_path)
        node2.operations.append(Translation([1000, 0, 0], node2))

        is_empty, volume = test_module._intersection_stats(node1, node2)

        self.assertTrue(is_empty)
        self.assertEqual(volume, 0.0)


class ExactPart:
    """A topmost rigid solid carrying BOTH exact geometry and a built
    STL, exactly as a real `CadQueryNode` does. The STL is what makes
    the point: it exists and is readable, so nothing about this part
    forces the assertion to reach for the mesh engine except the
    framework choosing to."""

    rigid = True
    exact = True
    children = ()

    def __init__(self, name, shape, stl_file):
        self.name = name
        self._shape = shape
        self.stl_file = stl_file
        self.operations = []
        self._parent = None

    def shape(self):
        return self._shape

    def as_number(self, value):
        return float(value)


class FacetedPart(FakeNode):
    """A topmost rigid solid with no exact geometry."""

    rigid = True
    exact = False
    children = ()


class Root:

    rigid = False

    def __init__(self, name, children):
        self.name = name
        self.children = tuple(children)
        self.operations = []
        self._parent = None
        for child in self.children:
            child._parent = self

    def as_number(self, value):
        return float(value)


class ExactAssemblyBuildsNoManifoldTest(ManifoldCacheTestCase):
    """The mesh engine belongs to the faceted path. Placing a solid for
    the spatial index must not of itself build that solid's Manifold, so
    an assembly whose every candidate pair is decided by the
    boundary-representation kernel builds none at all.

    Originating evidence: the browser-engine spike's all-exact fixture
    keeps 17 contracts green against a fail-by-name manifold3d
    stand-in and loses only its deliberate faceted marker -- the
    assertion logic is already exact-only; the plumbing was not.
    """

    def setUp(self):
        super().setUp()
        import cadquery as cq
        self.cq = cq

    def _exact(self, name, size, translation=None):
        shape = self.cq.Workplane('XY').box(*size).val()
        path = os.path.join(self.tmpdir.name, f'{name}.stl')
        box(size).export(path)
        part = ExactPart(name, shape, path)
        if translation is not None:
            part.operations.append(Translation(translation, part))
        return part

    def test_no_manifold_is_built_for_an_exact_assembly(self):
        first = self._exact('First', (2.0, 2.0, 2.0))
        second = self._exact('Second', (2.0, 2.0, 2.0), [10.0, 0, 0])

        with patch('solid_node.test._cached_manifold',
                   side_effect=AssertionError(
                       'the mesh engine must not be reached for an assembly '
                       'whose every candidate pair is exact')):
            asserter.assertNoSolidInterference(Root('Root', (first, second)))

    def test_no_manifold_is_built_for_an_overlapping_exact_pair(self):
        """The culled case would pass trivially; this pair really is
        compared, and still by the kernel alone."""
        first = self._exact('First', (2.0, 2.0, 2.0))
        second = self._exact('Second', (2.0, 2.0, 2.0), [1.0, 0, 0])

        with patch('solid_node.test._cached_manifold',
                   side_effect=AssertionError(
                       'an exact candidate pair must be decided by the '
                       'kernel, not the mesh engine')):
            with self.assertRaises(AssertionError) as ctx:
                asserter.assertNoSolidInterference(
                    Root('Root', (first, second)))

        self.assertIn('should not interfere', str(ctx.exception))

    def test_a_mixed_assembly_builds_one_manifold_per_faceted_comparison(self):
        """A mixed pair routes faceted, so BOTH its solids need a
        Manifold -- including the exact one. A solid no faceted pair
        reads needs none. Laziness, not exactness, is what selects."""
        exact_near = self._exact('ExactNear', (2.0, 2.0, 2.0))
        faceted_near = FacetedPart('FacetedNear', self.box_path)
        faceted_near.operations.append(
            Translation([1.0, 0, 0], faceted_near))
        exact_far = self._exact('ExactFar', (2.0, 2.0, 2.0), [1000.0, 0, 0])

        original = test_module._cached_manifold
        with patch('solid_node.test._cached_manifold',
                   wraps=original) as cached:
            with self.assertRaises(AssertionError):
                asserter.assertNoSolidInterference(Root(
                    'Root', (exact_near, faceted_near, exact_far)))

        built = [call.args[0] for call in cached.call_args_list]
        self.assertIn(exact_near.stl_file, built)
        self.assertIn(faceted_near.stl_file, built)
        self.assertNotIn(exact_far.stl_file, built)


class CulledSolidIsNotJudgedTest(ManifoldCacheTestCase):
    """Selecting a solid judges nothing. A solid the broad phase culls
    out of every pair is never read by the engine, so a mesh the engine
    would refuse raises only if some comparison actually reads it."""

    def _holey(self, name):
        holey = trimesh.creation.box((2, 2, 2))
        holey.faces = holey.faces[:-1]
        path = os.path.join(self.tmpdir.name, f'{name}.stl')
        holey.export(path)
        return path

    def test_a_culled_solid_is_not_judged(self):
        holey = FacetedPart('Holey', self._holey('holey'))
        holey.operations.append(Translation([1000, 0, 0], holey))
        first = FacetedPart('First', self.box_path)
        second = FacetedPart('Second', self.box_path)
        second.operations.append(Translation([10, 0, 0], second))

        asserter.assertNoSolidInterference(
            Root('Root', (first, second, holey)))

    def test_a_compared_solid_is_judged_by_the_engine(self):
        holey_path = self._holey('holey')
        holey = FacetedPart('Holey', holey_path)
        first = FacetedPart('First', self.box_path)

        with self.assertRaises(ValueError) as ctx:
            asserter.assertNoSolidInterference(Root('Root', (first, holey)))

        self.assertIn(holey_path, str(ctx.exception))
        self.assertIn('NotManifold', str(ctx.exception))
