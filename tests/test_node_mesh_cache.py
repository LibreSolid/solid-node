# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for docs/performance-improvement.md fix 1:
AbstractBaseNode.mesh used to reload the STL from disk on EVERY access
and apply each operation (own + every ancestor's) as a separate
apply_transform pass. These tests pin the replacement -- a
module-level base-mesh cache keyed on (stl_file, mtime), plus a SINGLE
composed world matrix applied in one apply_transform -- against the
OLD per-operation path (reimplemented here directly, since base.py no
longer has it) and against the caching/copy/liveness contracts the fix
promises.

FakeNode below is a duck-typed stand-in for AbstractBaseNode, in the
same spirit as tests/test_manager_test.py's InstrumentedChild: it
reuses the REAL AbstractBaseNode.mesh property getter and real
Rotation/Translation operations, so these tests exercise the actual
implementation rather than a reimplementation of it.
"""

import os
import tempfile
import time
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import trimesh
from trimesh.creation import box

from solid_node.node.base import AbstractBaseNode
from solid_node.node.operations import Rotation, Translation


def _old_style_mesh(node):
    """The algorithm AbstractBaseNode.mesh used before fix 1: reload
    the STL from disk, then apply each operation (own, then every
    ancestor's, walking node -> parent -> ...) as a separate
    mesh-mutating pass."""
    mesh = trimesh.load(node.stl_file)
    current = node
    while current is not None:
        for operation in current.operations:
            operation.mesh(mesh)
        current = getattr(current, '_parent', None)
    return mesh


class FakeNode:
    """Duck-typed stand-in for AbstractBaseNode: a real stl_file on
    disk, a real .operations list, and an optional ._parent -- enough
    for AbstractBaseNode.mesh's getter to run unmodified."""

    def __init__(self, stl_file, parent=None):
        self.stl_file = stl_file
        self.operations = []
        self._parent = parent

    def as_number(self, n):
        return float(n)

    @property
    def mesh(self):
        return AbstractBaseNode.mesh.fget(self)


class FakeAnimatedAngle:
    """Stands in for a solid2 $t animated expression: not a real
    number, resolvable only through a node's as_number()."""

    def __init__(self, value):
        self.value = value

    def __neg__(self):
        return FakeAnimatedAngle(-self.value)


class AnimatedFakeNode(FakeNode):
    """A FakeNode whose as_number() resolves FakeAnimatedAngle through
    a settable keyframe value, mirroring how AssemblyNode.set_keyframe
    makes a solid2 $t expression numeric."""

    def __init__(self, stl_file, parent=None):
        super().__init__(stl_file, parent)
        self._keyframe_value = 0.0

    def as_number(self, n):
        if isinstance(n, FakeAnimatedAngle):
            return self._keyframe_value
        return float(n)

    def set_keyframe(self, value):
        self._keyframe_value = value


class _Ancestor:
    """A minimal ancestor: only .operations and ._parent, exactly what
    the node -> ancestors walk needs -- an AssemblyNode stand-in
    without any rendering machinery."""

    def __init__(self, operations, parent=None):
        self.operations = operations
        self._parent = parent


class MeshCacheTestCase(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.stl_path = os.path.join(self.tmpdir.name, 'part.stl')
        box((2, 3, 4)).export(self.stl_path)


class BaseMeshCacheTest(MeshCacheTestCase):
    """The module-level (stl_file, mtime) cache: a real disk load must
    happen at most once per distinct (stl_file, mtime) pair, however
    many times .mesh is accessed."""

    def test_repeated_mesh_access_loads_stl_from_disk_once(self):
        node = FakeNode(self.stl_path)
        node.operations.append(Translation([1, 0, 0], node))

        calls = []
        original_load = trimesh.load

        def counting_load(path, *args, **kwargs):
            calls.append(path)
            return original_load(path, *args, **kwargs)

        with patch('solid_node.node.base.trimesh.load',
                   side_effect=counting_load):
            node.mesh
            node.mesh
            node.mesh

        self.assertEqual(len(calls), 1)

    def test_two_nodes_sharing_an_stl_file_load_it_once(self):
        node_a = FakeNode(self.stl_path)
        node_b = FakeNode(self.stl_path)

        calls = []
        original_load = trimesh.load

        def counting_load(path, *args, **kwargs):
            calls.append(path)
            return original_load(path, *args, **kwargs)

        with patch('solid_node.node.base.trimesh.load',
                   side_effect=counting_load):
            node_a.mesh
            node_b.mesh

        self.assertEqual(len(calls), 1)

    def test_mtime_change_invalidates_the_cache(self):
        node = FakeNode(self.stl_path)
        first_volume = node.mesh.volume

        box((6, 6, 6)).export(self.stl_path)
        newer = os.path.getmtime(self.stl_path) + 5
        os.utime(self.stl_path, (newer, newer))

        second_volume = node.mesh.volume

        self.assertNotAlmostEqual(first_volume, second_volume, places=2)


class CopySemanticsTest(MeshCacheTestCase):
    """.mesh must hand back a COPY: callers are free to mutate it, and
    the cached base mesh (and any other caller's mesh) must stay
    pristine."""

    def test_mutating_a_returned_mesh_does_not_affect_the_next_access(self):
        node = FakeNode(self.stl_path)

        first = node.mesh
        first.apply_translation([1000, 1000, 1000])

        second = node.mesh

        self.assertFalse(np.allclose(second.vertices.mean(axis=0),
                                     first.vertices.mean(axis=0)))
        # The second access is unaffected by the first mutation --
        # still centered near the origin, not near (1000, 1000, 1000).
        self.assertLess(np.linalg.norm(second.vertices.mean(axis=0)), 10)


class ComposedMatrixMatchesOldPathTest(MeshCacheTestCase):
    """The new single-matrix composition must produce numerically
    identical vertices (tight tolerance) to the OLD per-operation
    path, for a node with a multi-op chain AND a parent assembly
    chain."""

    def _node(self):
        grandparent = _Ancestor(operations=[
            Rotation(15, [0, 1, 0]),
            Translation([1, -2, 0.5]),
        ])
        parent = _Ancestor(operations=[
            Rotation(45, [1, 0, 0]),
            Translation([10, 0, 0]),
        ], parent=grandparent)
        node = FakeNode(self.stl_path, parent=parent)
        node.operations.append(Rotation(30, [0, 0, 1], node))
        node.operations.append(Translation([2, 3, 4], node))
        return node

    def test_multi_op_chain_with_parent_matches_old_path(self):
        node = self._node()

        expected = _old_style_mesh(node)
        actual = node.mesh

        self.assertEqual(len(actual.vertices), len(expected.vertices))
        np.testing.assert_allclose(
            actual.vertices, expected.vertices, atol=1e-7, rtol=1e-9)


class ReflectsLiveOperationsListTest(MeshCacheTestCase):
    """Every .mesh access must reflect the CURRENT operations list --
    the perturbation assertions in solid_node/test.py insert an
    operation into node.operations and remove it in a finally, so a
    world matrix cached across accesses would silently ignore the
    perturbation (or leak it after removal)."""

    def test_mid_list_insert_and_remove_are_reflected_live(self):
        node = FakeNode(self.stl_path)
        placement = Translation([5, 0, 0], node)
        node.operations.append(placement)

        baseline = node.mesh
        self.assertTrue(np.allclose(baseline.vertices,
                                    _old_style_mesh(node).vertices))

        perturbation = Rotation(30, [0, 0, 1], node)
        node.operations.insert(0, perturbation)
        try:
            perturbed = node.mesh
            self.assertTrue(np.allclose(
                perturbed.vertices, _old_style_mesh(node).vertices,
                atol=1e-7))
            self.assertFalse(np.allclose(
                perturbed.vertices, baseline.vertices, atol=1e-6))
        finally:
            node.operations.remove(perturbation)

        restored = node.mesh
        np.testing.assert_allclose(
            restored.vertices, baseline.vertices, atol=1e-7, rtol=1e-9)


class ReflectsKeyframeChangeTest(MeshCacheTestCase):
    """The composed world matrix must never be cached across
    set_keyframe changes: operation values can be solid2 animated
    expressions resolved through as_number() at ACCESS TIME."""

    def test_mesh_changes_after_set_keyframe(self):
        node = AnimatedFakeNode(self.stl_path)
        node.operations.append(
            Rotation(FakeAnimatedAngle(1), [0, 0, 1], node))
        node.operations.append(Translation([5, 0, 0], node))

        node.set_keyframe(0)
        mesh_at_0 = node.mesh
        np.testing.assert_allclose(
            mesh_at_0.vertices, _old_style_mesh(node).vertices,
            atol=1e-7, rtol=1e-9)

        node.set_keyframe(90)
        mesh_at_90 = node.mesh
        np.testing.assert_allclose(
            mesh_at_90.vertices, _old_style_mesh(node).vertices,
            atol=1e-7, rtol=1e-9)

        self.assertFalse(np.allclose(
            mesh_at_0.vertices, mesh_at_90.vertices, atol=1e-6))
