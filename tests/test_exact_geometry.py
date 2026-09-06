# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import tempfile
import json
import warnings
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import cadquery as cq
import numpy as np
import trimesh
from solid2 import cube

from solid_node.node import (
    Build123dNode,
    CadQueryNode,
    FusionNode,
    JScadNode,
    MolejoNode,
    OpenScadNode,
    Solid2Node,
)
from solid_node.exact import (_placement_cache, _shape_cache,
                              cached_shape, placed_shape,
                              solid_count, solid_volume, write_brep,
                              write_stl)
from solid_node.node.base import StlRenderStart
import solid_node.test as test_module
from solid_node.test import TestCase as GeometryTestCase, _intersection_stats
from solid_node.core.builder import Builder


class Box(CadQueryNode):

    def __init__(self, size=2, **kwargs):
        self.size = size
        super().__init__(size, **kwargs)

    def render(self):
        return cq.Workplane("XY").box(self.size, self.size, self.size)


class Ring(CadQueryNode):

    def render(self):
        return cq.Workplane("XY").circle(2).circle(1).extrude(2)


class Shaft(CadQueryNode):

    def render(self):
        return cq.Workplane("XY").circle(1).extrude(2)


class Solid2Box(Solid2Node):

    def render(self):
        return cube(2)


class ExactFusion(FusionNode):

    def __init__(self):
        self.ring = Ring()
        self.shaft = Shaft()
        super().__init__()

    def render(self):
        return [self.ring, self.shaft]


class MixedFusion(FusionNode):

    def __init__(self):
        self.exact_child = Box()
        self.faceted_child = Solid2Box()
        super().__init__()

    def render(self):
        return [self.exact_child, self.faceted_child]


class ShapeNode:
    rigid = True
    exact = True
    children = ()

    def __init__(self, shape, name, *, matrix_parent=None):
        self._shape = shape
        self.name = name
        self.operations = []
        self._parent = matrix_parent

    def shape(self):
        return self._shape

    def as_number(self, value):
        return float(value)


class MeshShapeNode(ShapeNode):

    def __init__(self, shape, mesh, name, *, exact=True):
        super().__init__(shape, name)
        self._mesh = mesh
        self.exact = exact

    @property
    def mesh(self):
        mesh = self._mesh.copy()
        for operation in self.operations:
            operation.mesh(mesh)
        return mesh


asserter = GeometryTestCase()


class NodeExactnessTest(TestCase):

    @staticmethod
    def uninitialized(node_type):
        return object.__new__(node_type)

    def test_leaf_exactness_is_derived_from_adapter_type(self):
        self.assertTrue(self.uninitialized(CadQueryNode).exact)
        self.assertTrue(self.uninitialized(Build123dNode).exact)
        # A flexible leaf's exact geometry is per-instant, but WHETHER it
        # has any is fixed by adapter type like every other adapter's.
        self.assertTrue(self.uninitialized(MolejoNode).exact)
        self.assertFalse(self.uninitialized(Solid2Node).exact)
        self.assertFalse(self.uninitialized(OpenScadNode).exact)
        self.assertFalse(self.uninitialized(JScadNode).exact)

    def test_exactness_does_not_require_one_backend(self):
        """Every exact adapter yields the same boundary representation, so a
        mixture of them composes exactly with no backend-agreement rule."""
        fusion = self.uninitialized(FusionNode)
        fusion.children = [self.uninitialized(CadQueryNode),
                           self.uninitialized(Build123dNode)]

        self.assertTrue(fusion.exact)

    def test_fusion_exactness_composes_from_children(self):
        exact = self.uninitialized(CadQueryNode)
        faceted = self.uninitialized(Solid2Node)

        exact_fusion = self.uninitialized(FusionNode)
        exact_fusion.children = [exact]
        self.assertTrue(exact_fusion.exact)

        mixed_fusion = self.uninitialized(FusionNode)
        mixed_fusion.children = [exact, faceted]
        self.assertFalse(mixed_fusion.exact)

    def test_unassembled_internal_node_refuses_vacuous_exactness(self):
        fusion = self.uninitialized(FusionNode)
        fusion.name = "unassembled"

        with self.assertRaisesRegex(RuntimeError, "unassembled"):
            _ = fusion.exact


class ExactArtifactTest(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.old_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name
        _shape_cache.clear()

    def tearDown(self):
        if self.old_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.old_build_dir

    def test_cadquery_build_writes_current_brep_and_shape_reuses_it(self):
        node = Box()
        node.assemble()

        self.assertTrue(node._up_to_date(node.brep_file))
        self.assertTrue(node._up_to_date(node.stl_file))
        node.model = None
        with patch.object(node, 'render', side_effect=AssertionError(
                'current BREP must avoid rerendering')):
            shape = node.shape()
        self.assertAlmostEqual(shape.Volume(), 8.0)

    def test_shape_is_local_and_does_not_apply_node_operations(self):
        node = Box()
        node.translate([20, 0, 0])
        node.assemble()

        bounds = node.shape().BoundingBox()
        self.assertAlmostEqual(bounds.xmin, -1.0, places=6)
        self.assertAlmostEqual(bounds.xmax, 1.0, places=6)

    def test_shape_cache_evicts_the_previous_mtime(self):
        path = os.path.join(self.directory.name, 'shape.brep')
        first_shape = cq.Workplane('XY').box(1, 1, 1).val()
        second_shape = cq.Workplane('XY').box(2, 2, 2).val()
        write_brep(first_shape, path, 1 * 10 ** 9)
        first = cached_shape(path)
        write_brep(second_shape, path, 2 * 10 ** 9)
        second = cached_shape(path)

        self.assertAlmostEqual(first.Volume(), 1.0)
        self.assertAlmostEqual(second.Volume(), 8.0)
        self.assertEqual([key for key in _shape_cache if key[0] == path],
                         [(path, 2.0)])

    def test_one_placement_serves_repeated_comparisons(self):
        """A placement is built once per (shape identity, matrix).

        `placed_shape` runs `BRepBuilderAPI_Transform` over the whole
        B-rep -- 6-19 ms on real parts -- and an animated assertion
        places the same solid by the same matrix at every candidate pair
        it visits. The second placement of a matrix already placed must
        cost a lookup.
        """
        path = os.path.join(self.directory.name, 'placed.brep')
        write_brep(cq.Workplane('XY').box(1, 1, 1).val(), path, 1 * 10 ** 9)
        shape = cached_shape(path)
        matrix = np.eye(4)
        matrix[0, 3] = 5.0

        first = placed_shape(shape, matrix)
        second = placed_shape(shape, matrix)

        self.assertIs(second, first)
        self.assertAlmostEqual(
            first.BoundingBox().xmin, 4.5, places=6)

    def test_a_different_matrix_builds_its_own_placement(self):
        path = os.path.join(self.directory.name, 'placed.brep')
        write_brep(cq.Workplane('XY').box(1, 1, 1).val(), path, 1 * 10 ** 9)
        shape = cached_shape(path)
        near, far = np.eye(4), np.eye(4)
        near[0, 3] = 5.0
        far[0, 3] = 9.0

        placed_near = placed_shape(shape, near)
        placed_far = placed_shape(shape, far)

        self.assertIsNot(placed_near, placed_far)
        self.assertAlmostEqual(placed_near.BoundingBox().xmin, 4.5, places=6)
        self.assertAlmostEqual(placed_far.BoundingBox().xmin, 8.5, places=6)

    def test_a_rebuilt_shape_is_never_served_the_old_placement(self):
        """The hazard this cache exists to avoid.

        A `cq.Shape` cannot be its own cache key: `Shape.__eq__` is
        `isSame()`, which compares the underlying TShape and ignores
        location, so a shape and a differently placed copy of it compare
        EQUAL. Nor can `id()` be one on its own, since CPython reuses an
        address after collection. The key is therefore the same
        `(file, mtime)` identity `_shape_cache` uses, and a rebuild under
        a new mtime must not be served the old geometry's placement.
        """
        path = os.path.join(self.directory.name, 'rebuilt.brep')
        matrix = np.eye(4)
        matrix[0, 3] = 5.0

        write_brep(cq.Workplane('XY').box(1, 1, 1).val(), path, 1 * 10 ** 9)
        before = placed_shape(cached_shape(path), matrix)
        write_brep(cq.Workplane('XY').box(2, 2, 2).val(), path, 2 * 10 ** 9)
        after = placed_shape(cached_shape(path), matrix)

        self.assertAlmostEqual(before.Volume(), 1.0)
        self.assertAlmostEqual(after.Volume(), 8.0)
        self.assertEqual(
            {key[0] for key in _placement_cache if key[0][0] == path},
            {(path, 2.0)},
            'a placement built from the evicted geometry survived')

    def test_a_shape_without_file_identity_is_not_cached(self):
        # A shape built on the fly -- a fusion composed for this
        # comparison, a node whose BREP is not current -- has no identity
        # to key on, so it is placed exactly as it is today.
        shape = cq.Workplane('XY').box(1, 1, 1).val()
        matrix = np.eye(4)

        first = placed_shape(shape, matrix)
        second = placed_shape(shape, matrix)

        self.assertIsNot(first, second)
        self.assertAlmostEqual(second.Volume(), 1.0)

    def test_fusion_composes_and_renders_exactly_without_subprocess(self):
        fusion = ExactFusion()
        fusion.assemble()

        with patch('solid_node.node.base.Popen', side_effect=AssertionError(
                'exact fusion must not launch OpenSCAD')):
            fusion.build_stls()

        self.assertTrue(fusion._up_to_date(fusion.brep_file))
        self.assertTrue(fusion._up_to_date(fusion.stl_file))
        self.assertEqual(solid_count(fusion.shape()), 1)
        self.assertAlmostEqual(solid_volume(fusion.shape()),
                               8 * 3.141592653589793, places=5)

    def test_publication_keeps_brep_private_and_sweep_spares_it(self):
        node = Box()
        node.assemble()
        builder = Builder('unused.py', build_dir=self.directory.name,
                          watch=False)
        builder.node = node

        builder._write_viewer_snapshot()

        with open(os.path.join(self.directory.name, 'viewer.json')) as handle:
            snapshot = json.load(handle)
        self.assertNotIn('.brep', json.dumps(snapshot))
        self.assertTrue(os.path.exists(node.brep_file))

    def test_builder_requires_brep_currency_for_exact_nodes(self):
        node = Box()
        node.assemble()
        builder = Builder('unused.py', build_dir=self.directory.name,
                          watch=False)
        builder.node = node
        self.assertTrue(builder._artifacts_are_current())

        os.remove(node.brep_file)

        self.assertFalse(builder._artifacts_are_current())

    def test_mixed_fusion_keeps_the_openscad_render_protocol(self):
        fusion = MixedFusion()
        fusion.assemble()
        process = Mock(pid=12345)
        with patch('solid_node.node.base.Popen', return_value=process):
            with self.assertRaises(StlRenderStart):
                fusion.generate_stl()


class ExactIntersectionTest(TestCase):

    def box(self, size, name):
        return ShapeNode(cq.Workplane('XY').box(*size).val(), name)

    def test_exact_intersection_reports_path_and_volume(self):
        left = self.box((2, 2, 2), 'left')
        right = self.box((2, 2, 2), 'right')
        right.operations.append(
            __import__('solid_node.node.operations', fromlist=['Translation'])
            .Translation([1, 0, 0], right))

        stats = _intersection_stats(left, right)

        self.assertTrue(stats.exact)
        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 4.0)

    def test_exact_boundary_contact_contains_no_solid(self):
        left = self.box((2, 2, 2), 'left')
        right = self.box((2, 2, 2), 'right')
        right.operations.append(
            __import__('solid_node.node.operations', fromlist=['Translation'])
            .Translation([2, 0, 0], right))

        stats = _intersection_stats(left, right)

        self.assertTrue(stats.exact)
        self.assertTrue(stats.is_empty)
        self.assertEqual(stats.volume, 0.0)

    def test_volume_assertions_share_the_exact_helper(self):
        left = self.box((2, 2, 2), 'left')
        right = self.box((2, 2, 2), 'right')

        asserter.assertIntersectVolumeAbove(left, right, 7.9)
        asserter.assertIntersectVolumeBelow(left, right, 8.1)
        with self.assertRaises(AssertionError):
            asserter.assertNotIntersecting(left, right)

    def test_kernel_failure_names_pair_and_never_loads_mesh(self):
        left = self.box((2, 2, 2), 'left')
        right = self.box((2, 2, 2), 'right')
        failed = Mock()
        failed.IsDone.return_value = False

        with patch('solid_node.exact.BRepAlgoAPI_Common', return_value=failed):
            with self.assertRaisesRegex(RuntimeError, 'left.*right'):
                _intersection_stats(left, right)

    def test_exact_aabb_culls_before_boolean(self):
        left = self.box((1, 1, 1), 'left')
        right = self.box((1, 1, 1), 'right')
        from solid_node.node.operations import Translation
        right.operations.append(Translation([10, 0, 0], right))

        with patch('solid_node.test.intersect_shapes',
                   side_effect=AssertionError('boolean must be culled')):
            stats = _intersection_stats(left, right)

        self.assertTrue(stats.exact)
        self.assertTrue(stats.is_empty)

    def test_mixed_pair_stays_on_faceted_fallback(self):
        shape = cq.Workplane('XY').box(1, 1, 1).val()
        mesh = trimesh.creation.box((1, 1, 1))
        exact = MeshShapeNode(shape, mesh, 'exact')
        faceted = MeshShapeNode(shape, mesh, 'faceted', exact=False)

        stats = _intersection_stats(exact, faceted)

        self.assertFalse(stats.exact)
        self.assertFalse(stats.is_empty)

    def test_distance_assertions_remain_mesh_based(self):
        shape = cq.Workplane('XY').box(1, 1, 1).val()
        mesh = trimesh.creation.box((1, 1, 1))
        exact = MeshShapeNode(shape, mesh, 'exact')
        other = MeshShapeNode(shape, mesh, 'other')

        with patch.object(exact, 'shape', side_effect=AssertionError(
                'distance assertions must not read exact geometry')):
            asserter.assertClose(exact, other, 0.01)
            asserter.assertFar(exact, other, 0.0)


class ExactConnectivityAndEpsilonTest(TestCase):

    def test_disconnected_exact_solid_is_counted_from_shape(self):
        first = cq.Workplane('XY').box(1, 1, 1).val()
        second = placed_shape(
            cq.Workplane('XY').box(1, 1, 1).val(),
            trimesh.transformations.translation_matrix([3, 0, 0]))
        node = ShapeNode(cq.Compound.makeCompound([first, second]), 'broken')

        with self.assertRaisesRegex(AssertionError, 'broken.*2'):
            asserter.assertNoDisconnectedSolids(node)

    def test_exact_join_requires_overlap_not_tangential_contact(self):
        solid = SimpleNamespace(rigid=True, _parent=None, operations=[])
        left = ShapeNode(cq.Workplane('XY').box(2, 2, 2).val(), 'left',
                         matrix_parent=solid)
        overlapping = ShapeNode(
            cq.Workplane('XY').box(2, 2, 2).val(), 'overlapping',
            matrix_parent=solid)
        touching = ShapeNode(
            cq.Workplane('XY').box(2, 2, 2).val(), 'touching',
            matrix_parent=solid)
        from solid_node.node.operations import Translation
        overlapping.operations.append(Translation([1, 0, 0], overlapping))
        touching.operations.append(Translation([2, 0, 0], touching))

        asserter.assertJoined(left, overlapping, min_weld_volume=3.9)
        with self.assertRaisesRegex(AssertionError, 'one body'):
            asserter.assertJoined(left, touching)

    def test_all_exact_perturbation_warns_and_ignores_epsilon(self):
        left = ShapeNode(cq.Workplane('XY').box(1, 1, 1).val(), 'left')
        right = ShapeNode(cq.Workplane('XY').box(1, 1, 1).val(), 'right')
        from solid_node.node.operations import Translation
        right.operations.append(Translation([10, 0, 0], right))

        with self.assertWarnsRegex(UserWarning, 'assertFreeWithin.*ignored'):
            asserter.assertFreeWithin(
                left, 1, right, along=[0, 1, 0], directions='forward',
                volume_epsilon=1e-6)

    def test_mixed_perturbation_keeps_epsilon_live_without_warning(self):
        shape = cq.Workplane('XY').box(1, 1, 1).val()
        mesh = trimesh.creation.box((1, 1, 1))
        exact = MeshShapeNode(shape, mesh, 'exact')
        faceted = MeshShapeNode(shape, mesh, 'faceted', exact=False)
        from solid_node.node.operations import Translation
        faceted.operations.append(Translation([10, 0, 0], faceted))

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            asserter.assertFreeWithin(
                exact, 1, faceted, along=[0, 1, 0], directions='forward',
                volume_epsilon=1e-6)

        self.assertFalse(any('ignored volume_epsilon' in str(item.message)
                             for item in caught))

    def test_exact_pairwise_epsilon_cannot_hide_overlap(self):
        left = ShapeNode(cq.Workplane('XY').box(2, 2, 2).val(), 'left')
        right = ShapeNode(cq.Workplane('XY').box(2, 2, 2).val(), 'right')
        root = SimpleNamespace(rigid=False, children=(left, right),
                               operations=[], _parent=None)
        left._parent = root
        right._parent = root

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            with self.assertRaises(AssertionError):
                asserter.assertNoPairwiseIntersections(
                    root, volume_epsilon=1000)

    def test_exact_pairwise_flush_contact_passes_and_warns(self):
        left = ShapeNode(cq.Workplane('XY').box(2, 2, 2).val(), 'left')
        right = ShapeNode(cq.Workplane('XY').box(2, 2, 2).val(), 'right')
        from solid_node.node.operations import Translation
        right.operations.append(Translation([2, 0, 0], right))
        root = SimpleNamespace(rigid=False, children=(left, right),
                               operations=[], _parent=None)
        left._parent = root
        right._parent = root

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            asserter.assertNoPairwiseIntersections(
                root, volume_epsilon=1e-6)

        self.assertTrue(any('assertNoPairwiseIntersections ignored' in
                            str(item.message) for item in caught))


class StlShapeNode(ShapeNode):
    """An exact node that also has a built STL -- what a real exact leaf
    looks like to the test framework, so a faceted run has a mesh to
    compare while `shape()` stays available to refuse."""

    def __init__(self, shape, stl_file, name, *, matrix_parent=None):
        super().__init__(shape, name, matrix_parent=matrix_parent)
        self.stl_file = stl_file

    def base_mesh(self):
        from solid_node.node.base import AbstractBaseNode
        return AbstractBaseNode.base_mesh(self)

    @property
    def mesh(self):
        from solid_node.node.base import AbstractBaseNode
        return AbstractBaseNode.mesh.fget(self)


def _refuse_shape(node):
    return patch.object(node, 'shape', side_effect=AssertionError(
        f'{node.name}.shape() must not be read under the faceted kernel'))


class FacetedKernelTest(TestCase):
    """Under the faceted comparison kernel an exact node is compared like
    one that is not: on its mesh, never through its shape, with the run's
    epsilon applied to every engine verdict."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(test_module.set_comparison_policy, None)
        test_module._verdict_cache.clear()
        self.unit_box = cq.Workplane('XY').box(1, 1, 1).val()

    def faceted(self, epsilon=0.0):
        test_module.set_comparison_policy(
            test_module.ComparisonPolicy('faceted', epsilon))

    def stl(self, name, mesh):
        path = os.path.join(self.directory.name, f'{name}.stl')
        mesh.export(path)
        return path

    def box_node(self, name, translation=None, size=(1, 1, 1)):
        node = StlShapeNode(
            cq.Workplane('XY').box(*size).val(),
            self.stl(name, trimesh.creation.box(size)), name)
        if translation is not None:
            from solid_node.node.operations import Translation
            node.operations.append(Translation(translation, node))
        return node

    def test_two_exact_nodes_are_compared_on_their_meshes(self):
        self.faceted()
        left = self.box_node('left')
        right = self.box_node('right', [0.5, 0, 0])

        with _refuse_shape(left), _refuse_shape(right):
            stats = _intersection_stats(left, right)

        self.assertFalse(stats.exact)
        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 0.5, places=6)

    def test_no_kernel_name_is_resolved(self):
        # The deferred kernel names are what would import the exact stack
        # through the test framework; a faceted run never reaches one.
        self.faceted()
        left = self.box_node('left')
        right = self.box_node('right', [0.5, 0, 0])
        refused = {name: patch.object(
            test_module, name, side_effect=AssertionError(name))
            for name in ('intersect_shapes', 'placed_shape', 'fuse_shapes',
                         'solid_count', 'solid_volume', 'shape_identity',
                         'cached_bounding_box')}
        for refusal in refused.values():
            refusal.start()
            self.addCleanup(refusal.stop)

        stats = _intersection_stats(left, right)
        self.assertFalse(stats.is_empty)
        asserter.assertIntersecting(left, right)

    def test_the_model_still_reports_its_exactness(self):
        self.faceted()
        self.assertTrue(self.box_node('left').exact)

    def test_disconnected_exact_solid_is_counted_from_its_stl(self):
        self.faceted()
        two = trimesh.util.concatenate([
            trimesh.creation.box((1, 1, 1)),
            trimesh.creation.box((1, 1, 1)).apply_translation([3, 0, 0])])
        node = StlShapeNode(self.unit_box, self.stl('broken', two), 'broken')

        with _refuse_shape(node):
            with self.assertRaisesRegex(AssertionError, 'broken.*STL.*2'):
                asserter.assertNoDisconnectedSolids(node)

    def test_exact_features_are_welded_on_their_meshes(self):
        self.faceted()
        solid = SimpleNamespace(rigid=True, _parent=None, operations=[])
        left = StlShapeNode(self.unit_box,
                            self.stl('left', trimesh.creation.box((2, 2, 2))),
                            'left', matrix_parent=solid)
        overlapping = StlShapeNode(
            self.unit_box, self.stl('over', trimesh.creation.box((2, 2, 2))),
            'overlapping', matrix_parent=solid)
        from solid_node.node.operations import Translation
        overlapping.operations.append(Translation([1, 0, 0], overlapping))

        with _refuse_shape(left), _refuse_shape(overlapping), patch.object(
                test_module, 'fuse_shapes',
                side_effect=AssertionError('no fuse on the faceted kernel')):
            asserter.assertJoined(left, overlapping, min_weld_volume=3.9)

    def test_an_exact_assembly_is_verified_on_manifolds(self):
        self.faceted()
        apart = self.box_node('apart', [5, 0, 0])
        near = self.box_node('near')
        root = SimpleNamespace(rigid=False, children=(apart, near),
                               operations=[], _parent=None)
        apart._parent = near._parent = root

        with _refuse_shape(apart), _refuse_shape(near):
            asserter.assertNoSolidInterference(root)

        overlapping = self.box_node('overlapping', [0.5, 0, 0])
        root.children = (overlapping, near)
        overlapping._parent = root
        with _refuse_shape(overlapping), _refuse_shape(near):
            with self.assertRaisesRegex(AssertionError,
                                        'intersection volume 0.5'):
                asserter.assertNoSolidInterference(root)

    def test_the_run_epsilon_absorbs_a_sliver(self):
        self.faceted(epsilon=0.5)
        left = self.box_node('left')
        right = self.box_node('right', [0.8, 0, 0])

        stats = _intersection_stats(left, right)

        self.assertTrue(stats.is_empty)
        self.assertEqual(stats.volume, 0.0)
        asserter.assertNotIntersecting(left, right)

    def test_a_real_overlap_survives_the_run_epsilon(self):
        self.faceted(epsilon=0.5)
        left = self.box_node('left', size=(4, 4, 4))
        right = self.box_node('right', [3.25, 0, 0], size=(4, 4, 4))

        stats = _intersection_stats(left, right)

        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 12.0, places=6)
        with self.assertRaisesRegex(AssertionError, 'left.*right'):
            asserter.assertNotIntersecting(left, right)

    def test_the_run_epsilon_reaches_the_assembly_assertion(self):
        self.faceted(epsilon=0.5)
        left = self.box_node('left')
        right = self.box_node('right', [0.8, 0, 0])
        root = SimpleNamespace(rigid=False, children=(left, right),
                               operations=[], _parent=None)
        left._parent = right._parent = root

        asserter.assertNoSolidInterference(root)

    def test_a_strict_faceted_run_keeps_flush_contact_fouling(self):
        # Epsilon 0.0 changes nothing: the non-empty zero-volume flush
        # contact of ADR-025/029 still fouls, as it does today.
        self.faceted(epsilon=0.0)
        left = self.box_node('left')
        right = self.box_node('right', [1.0, 0, 0])

        stats = _intersection_stats(left, right)

        self.assertEqual(stats.volume, 0.0)
        self.assertFalse(stats.is_empty)

    def test_a_perturbation_epsilon_stays_live_without_a_warning(self):
        self.faceted(epsilon=0.25)
        left = self.box_node('left')
        right = self.box_node('right', [10, 0, 0])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            asserter.assertFreeWithin(
                left, 1, right, along=[0, 1, 0], directions='forward',
                volume_epsilon=1e-6)

        self.assertFalse(any('ignored volume_epsilon' in str(item.message)
                             for item in caught))

    def test_the_verdict_cache_holds_the_raw_verdict(self):
        self.faceted(epsilon=0.5)
        left = self.box_node('left')
        right = self.box_node('right', [0.8, 0, 0])
        self.assertTrue(_intersection_stats(left, right).is_empty)

        self.faceted(epsilon=0.0)
        stats = _intersection_stats(left, right)

        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 0.2, places=6)

    def test_the_exact_kernel_is_untouched(self):
        test_module.set_comparison_policy(
            test_module.ComparisonPolicy('exact', 0.0))
        left = self.box_node('left')
        right = self.box_node('right', [0.5, 0, 0])

        stats = _intersection_stats(left, right)

        self.assertTrue(stats.exact)
        self.assertAlmostEqual(stats.volume, 0.5, places=6)


class MeshNeverJudgedOnTheExactPathTest(FacetedKernelTest):
    """Selecting a solid, placing it in the broad phase, or comparing it
    on the exact kernel never judges its mesh: only a faceted read asks
    the engine, and only the engine's own status refuses."""

    def holey_node(self, name, translation=None):
        holey = trimesh.creation.box((1, 1, 1))
        holey.faces = holey.faces[:-1]
        node = StlShapeNode(self.unit_box, self.stl(name, holey), name)
        if translation is not None:
            from solid_node.node.operations import Translation
            node.operations.append(Translation(translation, node))
        return node

    def no_engine(self):
        return patch.object(test_module, 'require_mesh_engine',
                            side_effect=AssertionError('no Manifold here'))

    def test_an_exact_run_never_judges_a_mesh(self):
        left = self.holey_node('holey')
        right = self.box_node('right', [0.5, 0, 0])

        with self.no_engine():
            stats = _intersection_stats(left, right)

        self.assertTrue(stats.exact)
        self.assertFalse(stats.is_empty)
        self.assertAlmostEqual(stats.volume, 0.5, places=6)

    def test_the_broad_phase_does_not_judge_a_mesh(self):
        holey = self.holey_node('holey', [5, 0, 0])
        near = self.box_node('near')
        root = SimpleNamespace(rigid=False, children=(holey, near),
                               operations=[], _parent=None)
        holey._parent = near._parent = root

        with self.no_engine():
            asserter.assertNoSolidInterference(root)

    def test_a_faceted_run_refuses_only_what_the_engine_refuses(self):
        self.faceted()
        left = self.holey_node('holey')
        right = self.box_node('right', [0.5, 0, 0])

        with self.assertRaisesRegex(ValueError, 'holey.*NotManifold'):
            _intersection_stats(left, right)


class DegenerateTriangleExportTest(TestCase):
    """An exact artifact's mesh carries no degenerate triangles: the
    leaf export drops what OCCT tessellates with no area, as the fused
    solid's export already did."""

    def test_write_stl_drops_degenerate_triangles(self):
        box = trimesh.creation.box((2, 2, 2))
        vertices = np.vstack([box.vertices, [[5, 5, 5], [6, 6, 6]]])
        faces = np.vstack([box.faces, [[8, 8, 9]]])
        tessellated = trimesh.Trimesh(vertices, faces, process=False)

        class Shape:
            def exportStl(self, path, tolerance, angularTolerance):
                tessellated.export(path, file_type='stl')

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'leaf.stl')
            write_stl(Shape(), path, 1 * 10 ** 9)
            raw = trimesh.load(path, process=False)

        self.assertEqual(len(raw.faces), 12)
        self.assertTrue(raw.nondegenerate_faces().all())
        self.assertEqual(len(raw.vertices), 36)
