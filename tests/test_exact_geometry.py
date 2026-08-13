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
import trimesh
from solid2 import cube

from solid_node.node import (
    CadQueryNode,
    FusionNode,
    JScadNode,
    OpenScadNode,
    Solid2Node,
)
from solid_node.exact import (_shape_cache, cached_shape, placed_shape,
                              solid_count, solid_volume, write_brep)
from solid_node.node.base import StlRenderStart
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
        self.assertFalse(self.uninitialized(Solid2Node).exact)
        self.assertFalse(self.uninitialized(OpenScadNode).exact)
        self.assertFalse(self.uninitialized(JScadNode).exact)

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
        write_brep(first_shape, path, 1)
        first = cached_shape(path)
        write_brep(second_shape, path, 2)
        second = cached_shape(path)

        self.assertAlmostEqual(first.Volume(), 1.0)
        self.assertAlmostEqual(second.Volume(), 8.0)
        self.assertEqual([key for key in _shape_cache if key[0] == path],
                         [(path, 2.0)])

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
