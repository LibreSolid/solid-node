# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import trimesh
from solid2 import cube

from solid_node import currency
from solid_node.node import AssemblyNode, FusionNode
from solid_node.node.base import _atomic_write_bytes
from solid_node.node.adapters.cadquery import CadQueryNode
from solid_node.node.exact_leaf import ExactLeafNode
from solid_node.node.leaf import LeafNode


class NativeMeshLeaf(LeafNode):
    """Test adapter with native mesh production and deliberately no SCAD hook."""

    namespace = 'trimesh'

    def __init__(self, offset=(0, 0, 0), size=(2, 2, 2), **kwargs):
        if isinstance(offset, (int, float)):
            offset = (offset, 0, 0)
        self.offset = offset
        self.size = size
        super().__init__(offset=offset, size=size, **kwargs)

    def render(self):
        mesh = trimesh.creation.box(self.size)
        mesh.apply_translation(self.offset)
        return mesh

    def materialize(self, rendered):
        _atomic_write_bytes(
            self.stl_file, rendered.export(file_type='stl'), self.mtime_ns,
            self.source_digest, self.source_fingerprint,
        )


class NativePair(FusionNode):
    def __init__(self, left_size=(2, 2, 2), right_size=(2, 2, 2),
                 right_offset=(1, 0, 0), placed=False):
        self.left = NativeMeshLeaf(size=left_size)
        self.right = NativeMeshLeaf(
            size=right_size,
            offset=(0, 0, 0) if placed else right_offset,
        )
        if placed:
            self.right.translate(right_offset)
        super().__init__(left_size=left_size, right_size=right_size,
                         right_offset=right_offset, placed=placed)

    def render(self):
        return [self.left, self.right]


class NativeAssembly(AssemblyNode):
    def __init__(self):
        self.pair = NativePair()
        super().__init__()

    def render(self):
        return [self.pair]


class BackendNeutralMaterializationTest(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name

    def tearDown(self):
        if self.old_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.old_build_dir
        self.directory.cleanup()

    def test_native_fusion_builds_without_scad_or_openscad(self):
        machine = NativeAssembly()
        with patch.object(NativeMeshLeaf, 'as_scad',
                          side_effect=AssertionError('SCAD boundary used')), \
             patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError('OpenSCAD boundary used')):
            machine.build_stls()

        fused = trimesh.load(machine.pair.stl_file, force='mesh')
        self.assertAlmostEqual(fused.volume, 12.0, places=5)
        self.assertEqual(len(fused.split(only_watertight=False)), 1)

    def test_portable_export_does_not_construct_scad_assembly(self):
        from solid_node.core.export import export_node

        machine = NativeAssembly()
        output = os.path.join(self.directory.name, 'export')
        with patch.object(NativeMeshLeaf, 'as_scad',
                          side_effect=AssertionError('SCAD leaf used')), \
             patch.object(FusionNode, 'as_scad',
                          side_effect=AssertionError('SCAD fusion used')), \
             patch.object(AssemblyNode, 'as_scad',
                          side_effect=AssertionError('SCAD assembly used')):
            manifest = export_node(machine, output, widget=False)

        self.assertEqual(manifest['root']['type'], 'AssemblyNode')
        self.assertTrue(os.path.exists(os.path.join(output, 'manifest.json')))

    def test_scad_compatibility_is_still_explicit(self):
        leaf = NativeMeshLeaf()
        leaf.build_stls()
        self.assertIn(leaf.local_stl, str(leaf.assemble()))

    def test_faceted_fusion_edge_cases_have_analytic_geometry(self):
        cases = (
            ('overlap', {}, 12.0, (-1.0, 2.0), 1),
            ('identical', {'right_offset': (0, 0, 0)}, 8.0,
             (-1.0, 1.0), 1),
            ('contained', {'left_size': (4, 4, 4),
                           'right_offset': (0, 0, 0)}, 64.0,
             (-2.0, 2.0), 1),
            ('disjoint', {'right_offset': (3, 0, 0)}, 16.0,
             (-1.0, 4.0), 2),
            ('face-touching', {'right_offset': (2, 0, 0)}, 16.0,
             (-1.0, 3.0), 1),
            ('edge-touching', {'right_offset': (2, 2, 0)}, 16.0,
             (-1.0, 3.0), 2),
            ('near-coincident', {'right_offset': (0.0001, 0, 0)},
             8.0004, (-1.0, 1.0001), 1),
            ('placed', {'right_offset': (1, 0, 0), 'placed': True},
             12.0, (-1.0, 2.0), 1),
        )
        for name, arguments, volume, x_bounds, bodies in cases:
            with self.subTest(name=name):
                fusion = NativePair(**arguments)
                fusion.build_stls()
                mesh = trimesh.load(fusion.stl_file, force='mesh')
                self.assertAlmostEqual(mesh.volume, volume, places=4)
                self.assertAlmostEqual(mesh.bounds[0][0], x_bounds[0],
                                       places=5)
                self.assertAlmostEqual(mesh.bounds[1][0], x_bounds[1],
                                       places=5)
                self.assertEqual(
                    len(mesh.split(only_watertight=False)), bodies)
                self.assertTrue(mesh.is_winding_consistent)

    def test_old_or_missing_fusion_recipe_is_a_hard_cache_miss(self):
        fusion = NativePair()
        fusion.build_stls()
        self.assertEqual(currency.recorded_recipe(fusion.stl_file),
                         fusion.geometry_recipe)

        currency.record(fusion.stl_file, fusion.source_digest,
                        fusion.source_fingerprint)
        self.assertIsNone(currency.recorded_recipe(fusion.stl_file))
        self.assertFalse(fusion._up_to_date(fusion.stl_file))

        fusion.generate_stl()
        self.assertEqual(currency.recorded_recipe(fusion.stl_file),
                         fusion.geometry_recipe)

    def test_missing_mesh_engine_fails_without_openscad_fallback(self):
        fusion = NativePair()
        fusion._prepare()
        with patch('solid_node.node.fusion.require_mesh_engine',
                   side_effect=RuntimeError('manifold unavailable')), \
             patch('solid_node.node.base.require_openscad') as openscad:
            with self.assertRaisesRegex(RuntimeError, 'manifold unavailable'):
                fusion.generate_stl()
        openscad.assert_not_called()

    def test_invalid_fusion_input_names_child_and_does_not_fallback(self):
        fusion = NativePair()
        fusion._prepare()
        invalid = trimesh.creation.box((2, 2, 2))
        invalid.update_faces(range(len(invalid.faces) - 1))
        invalid.export(fusion.right.stl_file)
        with patch('solid_node.node.base.require_openscad') as openscad:
            with self.assertRaisesRegex(ValueError, r'right: manifold3d'):
                fusion.generate_stl()
        openscad.assert_not_called()

    def test_builtin_subclass_as_scad_override_selects_legacy_bridge(self):
        import cadquery as cq

        class LegacyCadQuery(CadQueryNode):
            def render(self):
                return cq.Workplane('XY').box(2, 2, 2)

            def as_scad(self, rendered):
                return cube(3)

        node = LegacyCadQuery()
        with patch.object(ExactLeafNode, 'materialize',
                          side_effect=AssertionError('native hook used')), \
             patch.object(node, 'generate_scad') as generate:
            node._prepare()
        generate.assert_called_once_with()
        self.assertIn('cube', str(node.model))
