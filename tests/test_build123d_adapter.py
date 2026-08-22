# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The build123d leaf adapter.

build123d and CadQuery are both OCCT front ends, so this adapter is exact
in exactly the sense `exact-geometry` already defines, and the interesting
tests here are the ones where build123d differs from CadQuery: it has no
`.vals()`, its builder is not itself geometry, and its sketches and curves
share one namespace with its solids -- so namespace validation alone cannot
tell a leaf's legitimate output from a mistake.
"""

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import build123d as b3d
import cadquery as cq
from solid2 import cube

from solid_node.exact import shape_from_rendered
from solid_node.node import (Build123dNode, CadQueryNode, FusionNode,
                             Solid2Node)


class BuilderBox(Build123dNode):
    """The headline build123d idiom: a context-manager builder."""

    def __init__(self, size=2, **kwargs):
        self.size = size
        super().__init__(size, **kwargs)

    def render(self):
        with b3d.BuildPart() as builder:
            b3d.Box(self.size, self.size, self.size)
        return builder.part


class BuilderItselfBox(BuilderBox):
    """Returns the builder rather than its part -- the mistake a user makes
    first, and one the adapter accepts rather than punishes."""

    def render(self):
        with b3d.BuildPart() as builder:
            b3d.Box(self.size, self.size, self.size)
        return builder


class AlgebraBox(Build123dNode):
    """build123d's other API: algebra mode, returning a shape directly."""

    def render(self):
        return b3d.Box(2, 2, 2)


class SolidBox(Build123dNode):

    def render(self):
        return b3d.Solid.make_box(2, 2, 2)


class SketchLeaf(Build123dNode):

    def render(self):
        return b3d.Rectangle(2, 2)


class CurveLeaf(Build123dNode):

    def render(self):
        return b3d.Line((0, 0), (2, 2))


class CadQueryBox(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').box(2, 2, 2)


class Solid2Box(Solid2Node):

    def render(self):
        return cube(2)


class MixedBackendFusion(FusionNode):
    """One printed solid modelled half in CadQuery and half in build123d.
    The children overlap, so an exact fuse must yield a single solid."""

    def __init__(self):
        self.cadquery_half = CadQueryBox()
        self.build123d_half = BuilderBox()
        self.build123d_half.translate([1, 0, 0])
        super().__init__()

    def render(self):
        return [self.cadquery_half, self.build123d_half]


class MixedExactnessFusion(FusionNode):

    def __init__(self):
        self.exact_child = BuilderBox()
        self.faceted_child = Solid2Box()
        super().__init__()

    def render(self):
        return [self.exact_child, self.faceted_child]


class BuildDirTestCase(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.old_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name

    def tearDown(self):
        if self.old_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.old_build_dir


class Build123dConversionTest(TestCase):
    """The conversion every other behaviour rests on."""

    def test_build123d_solid_converts_preserving_volume(self):
        with b3d.BuildPart() as builder:
            b3d.Box(2, 2, 2)

        shape = shape_from_rendered(builder.part)

        self.assertIsInstance(shape, cq.Shape)
        self.assertAlmostEqual(shape.Volume(), builder.part.volume, places=6)
        self.assertAlmostEqual(shape.Volume(), 8.0, places=6)

    def test_builder_is_converted_through_its_finished_part(self):
        with b3d.BuildPart() as builder:
            b3d.Box(2, 2, 2)

        self.assertAlmostEqual(shape_from_rendered(builder).Volume(), 8.0,
                               places=6)

    def test_conversion_survives_a_brep_roundtrip(self):
        from solid_node.exact import cached_shape, write_brep

        shape = shape_from_rendered(b3d.Box(2, 2, 2))
        path = os.path.join(tempfile.mkdtemp(), 'part.brep')
        write_brep(shape, path, 1)

        self.assertAlmostEqual(cached_shape(path).Volume(), 8.0, places=6)

    def test_cadquery_conversion_is_untouched(self):
        rendered = cq.Workplane('XY').box(2, 2, 2)

        self.assertAlmostEqual(shape_from_rendered(rendered).Volume(), 8.0,
                               places=6)

    def test_shapes_from_both_backends_fuse_into_one_solid(self):
        from solid_node.exact import fuse_shapes, solid_count

        cadquery_shape = shape_from_rendered(cq.Workplane('XY').box(2, 2, 2))
        build123d_shape = shape_from_rendered(b3d.Box(2, 2, 2))

        fused = fuse_shapes(cadquery_shape, build123d_shape,
                            'cadquery', 'build123d')

        self.assertEqual(solid_count(fused), 1)


class Build123dRenderValidationTest(BuildDirTestCase):
    """build123d's sketches and curves live under the same top-level module
    as its solids, so `namespace` cannot reject them and the adapter must."""

    def test_a_sketch_result_is_rejected_naming_node_and_type(self):
        node = SketchLeaf(name='faceplate')

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('faceplate', str(raised.exception))
        self.assertIn('Rectangle', str(raised.exception))

    def test_a_curve_result_is_rejected_naming_node_and_type(self):
        node = CurveLeaf(name='profile')

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('profile', str(raised.exception))
        self.assertIn('Line', str(raised.exception))

    def test_a_foreign_namespace_is_still_rejected(self):
        class WrongBackend(Build123dNode):
            def render(self):
                return cq.Workplane('XY').box(2, 2, 2)

        with self.assertRaises(Exception):
            WrongBackend().assemble()

    def test_a_list_result_is_still_rejected(self):
        class ListLeaf(Build123dNode):
            def render(self):
                return [b3d.Box(2, 2, 2)]

        with self.assertRaises(Exception):
            ListLeaf().assemble()

    def test_every_solid_shaped_result_is_accepted(self):
        for node in (BuilderBox(), BuilderItselfBox(), AlgebraBox(),
                     SolidBox()):
            with self.subTest(node=type(node).__name__):
                node.assemble()
                self.assertAlmostEqual(node.shape().Volume(), 8.0, places=6)


class Build123dArtifactTest(BuildDirTestCase):

    def test_assemble_writes_stl_and_brep_and_imports_the_stl(self):
        node = BuilderBox()

        assembled = node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))
        self.assertTrue(node._up_to_date(node.brep_file))
        self.assertIn(node.local_stl, str(assembled))

    def test_a_current_artifact_is_not_re_exported(self):
        node = BuilderBox()
        node.assemble()

        second = BuilderBox()
        with patch('solid_node.node.exact_leaf.write_stl',
                   side_effect=AssertionError('must not re-export')), \
             patch('solid_node.node.exact_leaf.write_brep',
                   side_effect=AssertionError('must not re-export')):
            assembled = second.as_scad(second.render())

        self.assertIn(second.local_stl, str(assembled))

    def test_shape_reuses_the_current_brep_without_rendering(self):
        node = BuilderBox()
        node.assemble()
        node.model = None

        with patch.object(node, 'render', side_effect=AssertionError(
                'a current BREP must avoid rerendering')):
            shape = node.shape()

        self.assertAlmostEqual(shape.Volume(), 8.0, places=6)

    def test_shape_is_local_and_does_not_apply_node_operations(self):
        node = BuilderBox()
        node.translate([20, 0, 0])
        node.assemble()

        bounds = node.shape().BoundingBox()

        self.assertAlmostEqual(bounds.xmin, -1.0, places=6)
        self.assertAlmostEqual(bounds.xmax, 1.0, places=6)

    def test_the_stl_never_reaches_the_openscad_renderer(self):
        node = BuilderBox()
        node.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'an exact backend must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'an exact backend must not launch OpenSCAD')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))


class Build123dExactnessTest(BuildDirTestCase):

    def test_the_adapter_is_exact_without_rendering(self):
        self.assertTrue(object.__new__(Build123dNode).exact)

    def test_a_fusion_mixing_exact_backends_is_exact(self):
        fusion = MixedBackendFusion()
        fusion.assemble()

        self.assertTrue(fusion.exact)

    def test_a_fusion_mixing_exact_backends_fuses_to_one_solid(self):
        from solid_node.exact import solid_count

        fusion = MixedBackendFusion()
        fusion.assemble()

        self.assertEqual(solid_count(fusion.shape()), 1)

    def test_one_faceted_child_still_makes_the_composition_faceted(self):
        fusion = MixedExactnessFusion()
        fusion.assemble()

        self.assertFalse(fusion.exact)


class ExactAdapterIdentityTest(TestCase):
    """The exact adapters share an implementation base. Sharing it must not
    make them interchangeable to a type test, which is what a project's
    `isinstance` check and the backend lookup in generate_stl both rely on."""

    def test_the_exact_adapters_are_not_instances_of_each_other(self):
        cadquery_node = CadQueryBox()
        build123d_node = BuilderBox()

        self.assertNotIsInstance(cadquery_node, Build123dNode)
        self.assertNotIsInstance(build123d_node, CadQueryNode)
        self.assertIsNot(type(cadquery_node).__mro__[1],
                         type(build123d_node))

    def test_neither_adapter_resolves_to_a_mesh_rendering_backend(self):
        """generate_stl names the backend by walking the MRO for adapter
        class names. A shared ancestor must not introduce one."""
        mesh_backends = {'Solid2Node', 'OpenScadNode', 'FusionNode'}

        for adapter in (CadQueryNode, Build123dNode):
            with self.subTest(adapter=adapter.__name__):
                names = {cls.__name__ for cls in adapter.__mro__}
                self.assertEqual(names & mesh_backends, set())

    def test_a_subclass_defines_with_the_cq_editor_metaclass_active(self):
        """CheckCQEditor drops the declared bases under CQ-editor. It names
        no base, so it is unaffected by the adapter now inheriting
        ExactLeafNode -- but that is worth holding, since it rewrites the
        hierarchy at definition time."""
        import sys
        from types import ModuleType

        sys.modules['cq_editor.__main__'] = ModuleType('cq_editor.__main__')
        self.addCleanup(sys.modules.pop, 'cq_editor.__main__', None)

        class EditorPart(CadQueryNode):
            def render(self):
                return cq.Workplane('XY').box(2, 2, 2)

        self.assertEqual(EditorPart.__bases__, (object,))


class Build123dImportCostTest(TestCase):

    def test_importing_the_node_package_does_not_import_build123d(self):
        """`solid_node.node` imports every adapter eagerly and importing
        build123d costs about 1.6 seconds, which a project on another
        backend should not pay. The adapter therefore recognises build123d
        results by module name instead of importing the library."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, '-c',
             'import sys; import solid_node.node;'
             ' print("build123d" in sys.modules)'],
            capture_output=True, text=True, check=True)

        self.assertEqual(result.stdout.strip(), 'False')
