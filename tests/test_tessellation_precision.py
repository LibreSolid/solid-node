# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Red-first proof for openspec/changes/declared-tessellation-precision.

A node cannot say how finely its solid should be tessellated: every exact
STL artifact goes through `exact.write_stl`, which fixed
`tolerance=0.1, angularTolerance=0.1` in its own body. This change lets an
`ExactLeafNode` or a `FusionNode` declare `linear_deflection` (mm) and
`angular_deflection` (radians) as class attributes that shape its own STL
artifact, while leaving `shape()` and the `.brep` untouched.

Section 1 proves the declaration and its validation, in isolation and
through a real build, on nodes defined directly in this module -- no
currency machinery is needed for those scenarios. Section 2 proves the
currency and identity consequences (ADR-071, ADR-026/063), which do need a
real on-disk project so a source edit is a genuine edit; it reuses the
`ScratchProjectTest` fixture `test_content_verified_currency.py` and
`test_node_scoped_currency.py` already share. Section 3 proves the faceted
test kernel judges on the declared mesh.
"""

import json
import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import cadquery as cq
import trimesh

from solid_node.node import CadQueryNode, FusionNode
from solid_node.exact import _shape_cache, deflections, write_stl
import solid_node.test as test_module

from tests.test_content_verified_currency import (
    DIMENSIONS, TRACE, ScratchProjectTest)


##############################################
# Section 1: the declaration


class CurvedDefault(CadQueryNode):
    """A curved solid whose angular deflection matters: a sphere's
    tessellation shrinks sharply as the angular bound loosens (8002 faces
    at 0.1 rad, 306 at 0.5 rad), where its linear bound alone barely moves
    it -- so this is the shape that tells the two attributes apart."""

    def render(self):
        return cq.Workplane('XY').sphere(5)


class CurvedCoarseAngular(CadQueryNode):
    """The same solid, declaring only a coarse angular_deflection."""

    angular_deflection = 0.5

    def render(self):
        return cq.Workplane('XY').sphere(5)


class CurvedCoarseLinear(CadQueryNode):
    """The same solid, declaring only a coarse linear_deflection."""

    linear_deflection = 0.05

    def render(self):
        return cq.Workplane('XY').sphere(5)


class BadLinearDeflection(CadQueryNode):

    linear_deflection = 0

    def render(self):
        return cq.Workplane('XY').sphere(5)


class RingChild(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').circle(3).circle(1).extrude(2)


class ShaftChild(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').circle(1).extrude(2)


class CoarseShaftChild(CadQueryNode):

    angular_deflection = 0.5

    def render(self):
        return cq.Workplane('XY').circle(1).extrude(2)


class CoarseFusion(FusionNode):
    """A fusion declaring its own coarse precision over children that
    declare nothing."""

    angular_deflection = 0.5

    def __init__(self):
        self.ring = RingChild()
        self.shaft = ShaftChild()
        super().__init__()

    def render(self):
        return [self.ring, self.shaft]


class DefaultFusion(FusionNode):
    """The same fusion, declaring nothing."""

    def __init__(self):
        self.ring = RingChild()
        self.shaft = ShaftChild()
        super().__init__()

    def render(self):
        return [self.ring, self.shaft]


class FusionOverCoarseChild(FusionNode):
    """A fusion declaring nothing, over a child that declares a coarse
    angular_deflection. The fusion's own artifact must stay at the
    default; only the child's own artifact is coarse."""

    def __init__(self):
        self.ring = RingChild()
        self.shaft = CoarseShaftChild()
        super().__init__()

    def render(self):
        return [self.ring, self.shaft]


class ExactDeclarationTest(TestCase):
    """Tasks 1.1, 1.3 and 1.4: the declaration shapes the STL alone."""

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

    def _triangles(self, path):
        return len(trimesh.load(path, process=False, file_type='stl').faces)

    def test_a_coarse_angular_declaration_yields_fewer_triangles(self):
        default = CurvedDefault()
        default.assemble()
        coarse = CurvedCoarseAngular()
        coarse.assemble()

        self.assertLess(self._triangles(coarse.stl_file),
                        self._triangles(default.stl_file))

    def test_an_undeclared_node_matches_the_historical_tessellation(self):
        """Pin the triangle count of a fixed solid at the framework's
        historical 0.1 mm / 0.1 rad, so a change to the defaults would be
        caught here."""
        node = CurvedDefault()
        node.assemble()

        self.assertEqual(self._triangles(node.stl_file), 8000)

    def test_angular_declared_alone_keeps_the_linear_default(self):
        node = CurvedCoarseAngular()
        self.assertEqual(deflections(node), (0.1, 0.5))

    def test_linear_declared_alone_keeps_the_angular_default(self):
        node = CurvedCoarseLinear()
        self.assertEqual(deflections(node), (0.05, 0.1))

    def test_bad_value_raises_and_writes_no_artifact(self):
        node = BadLinearDeflection()

        with self.assertRaisesRegex(
                ValueError, 'BadLinearDeflection.*linear_deflection'):
            node.assemble()

        self.assertFalse(os.path.exists(node.stl_file))

    def test_a_fusion_declares_its_own_precision(self):
        coarse = CoarseFusion()
        coarse.assemble()
        coarse.build_stls()
        default = DefaultFusion()
        default.assemble()
        default.build_stls()

        self.assertLess(self._triangles(coarse.stl_file),
                        self._triangles(default.stl_file))
        # Each child's own artifact is unaffected by the fusion's
        # declaration: neither Ring nor Shaft declares anything.
        self.assertEqual(self._triangles(coarse.ring.stl_file),
                         self._triangles(default.ring.stl_file))
        self.assertEqual(self._triangles(coarse.shaft.stl_file),
                         self._triangles(default.shaft.stl_file))

    def test_a_fusion_does_not_inherit_its_childs_precision(self):
        over_coarse_child = FusionOverCoarseChild()
        over_coarse_child.assemble()
        over_coarse_child.build_stls()
        default = DefaultFusion()
        default.assemble()
        default.build_stls()

        # The fusion itself declares nothing, so its fused artifact is at
        # the default precision, same as an all-default fusion.
        self.assertEqual(self._triangles(over_coarse_child.stl_file),
                         self._triangles(default.stl_file))
        # But the coarse child's own artifact stays coarse.
        self.assertLess(self._triangles(over_coarse_child.shaft.stl_file),
                        self._triangles(default.shaft.stl_file))

    def test_brep_and_shape_are_unaffected_by_declared_precision(self):
        default = CurvedDefault()
        default.assemble()
        coarse = CurvedCoarseAngular()
        coarse.assemble()

        with open(default.brep_file, 'rb') as handle:
            default_brep = handle.read()
        with open(coarse.brep_file, 'rb') as handle:
            coarse_brep = handle.read()

        self.assertEqual(default_brep, coarse_brep)
        self.assertAlmostEqual(
            default.shape().Volume(), coarse.shape().Volume(), places=6)
        # Only the STL differs.
        self.assertNotEqual(self._triangles(default.stl_file),
                            self._triangles(coarse.stl_file))


class DeflectionValidationTest(TestCase):
    """Task 1.2: every non-positive-finite-number value is refused, for
    both attributes, naming the node and the attribute."""

    BAD_VALUES = (0, -1, float('inf'), float('nan'), True, '0.5')

    def test_bad_linear_deflection_is_refused(self):
        for value in self.BAD_VALUES:
            with self.subTest(value=value):
                node = SimpleNamespace(
                    name='Suspect', linear_deflection=value,
                    angular_deflection=0.1)
                with self.assertRaisesRegex(
                        ValueError, 'Suspect.*linear_deflection'):
                    deflections(node)

    def test_bad_angular_deflection_is_refused(self):
        for value in self.BAD_VALUES:
            with self.subTest(value=value):
                node = SimpleNamespace(
                    name='Suspect', linear_deflection=0.1,
                    angular_deflection=value)
                with self.assertRaisesRegex(
                        ValueError, 'Suspect.*angular_deflection'):
                    deflections(node)

    def test_write_stl_direct_call_takes_the_tolerances_as_arguments(self):
        """D4: write_stl no longer fixes a default; every caller passes
        both tolerances explicitly."""
        box = trimesh.creation.box((2, 2, 2))

        class Shape:
            def exportStl(self, path, tolerance, angularTolerance):
                self.tolerance = tolerance
                self.angularTolerance = angularTolerance
                box.export(path, file_type='stl')

        shape = Shape()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'leaf.stl')
            write_stl(shape, path, 1 * 10 ** 9, 0.05, 0.5)

        self.assertEqual(shape.tolerance, 0.05)
        self.assertEqual(shape.angularTolerance, 0.5)


##############################################
# Section 2: currency and identity


PARTS = '''\
import cadquery as cq

from solid_node.node import CadQueryNode

from . import trace
from .dimensions import SIZE


class Declared(CadQueryNode):

    angular_deflection = 0.6

    def render(self):
        trace.record('Declared')
        return cq.Workplane('XY').sphere(SIZE)


class Undeclared(CadQueryNode):

    def render(self):
        trace.record('Undeclared')
        return cq.Workplane('XY').sphere(SIZE)
'''

MACHINE = '''\
from solid_node.node import AssemblyNode

from .parts import Declared, Undeclared


class Machine(AssemblyNode):

    def __init__(self):
        self.declared = Declared()
        self.undeclared = Undeclared()
        super().__init__()

    def render(self):
        self.undeclared.translate([10, 0, 0])
        return [self.declared, self.undeclared]
'''


class PrecisionCurrencyTest(ScratchProjectTest):
    """Tasks 2.1-2.3: editing the declared value in the module defining
    the class rides the ordinary node-scoped content path (ADR-071),
    does not touch identity (ADR-026/063), and changes the printed-piece
    id (ADR-043) because that id is a fingerprint of artifact content."""

    def project_files(self):
        return (('__init__.py', ''), ('trace.py', TRACE),
                ('dimensions.py', DIMENSIONS),
                ('parts.py', PARTS), ('machine.py', MACHINE))

    def edit_declared(self, value, source=PARTS):
        edited = source.replace(
            'angular_deflection = 0.6', f'angular_deflection = {value}')
        assert edited != source, 'the fixture did not edit Declared'
        self.write('parts.py', edited)

    def test_editing_the_declaration_rebuilds_only_that_node(self):
        node = self.build()
        self.renders()
        before = len(trimesh.load(
            node.declared.stl_file, process=False, file_type='stl').faces)
        undeclared_before = self.contents()[
            os.path.relpath(node.undeclared.stl_file, self.build_dir)]

        self.edit_declared('0.15')
        rebuilt = self.build()

        self.assertEqual(
            self.renders(), ['Declared'],
            'a sibling node class in the same file that declares nothing '
            'was rebuilt')
        after = len(trimesh.load(
            rebuilt.declared.stl_file, process=False,
            file_type='stl').faces)
        self.assertGreater(
            after, before,
            'a finer angular_deflection (0.6 -> 0.15) must yield more '
            'triangles, so the rewritten artifact is at the new precision')
        undeclared_after = self.contents()[
            os.path.relpath(rebuilt.undeclared.stl_file, self.build_dir)]
        self.assertEqual(undeclared_before, undeclared_after,
                         "the sibling's own artifact must not change")

    def test_the_declaration_is_not_artifact_identity(self):
        node = self.build()
        before_path = node.declared.stl_file
        before_uniq_id = node.declared.uniq_id
        matching_before = [
            relative for relative in self.artifacts()
            if 'Declared' in relative and relative.endswith('.stl')]

        self.edit_declared('0.15')
        rebuilt = self.build()

        self.assertEqual(rebuilt.declared.stl_file, before_path,
                         'a new declared precision must rewrite the same '
                         'artifact path, not create a second one')
        self.assertEqual(rebuilt.declared.uniq_id, before_uniq_id)
        matching_after = [
            relative for relative in self.artifacts()
            if 'Declared' in relative and relative.endswith('.stl')]
        self.assertEqual(matching_before, matching_after,
                         'a second artifact appeared in the build '
                         'directory for the same node')
        self.assertEqual(len(matching_after), 1)

    def test_redeclaring_precision_changes_the_piece_id(self):
        self.publish()
        with open(os.path.join(self.build_dir, 'viewer.json')) as snapshot:
            before = json.load(snapshot)
        before_pieces = {
            piece['name']: piece['id'] for piece in before['pieces']}

        self.edit_declared('0.15')
        self.publish()
        with open(os.path.join(self.build_dir, 'viewer.json')) as snapshot:
            after = json.load(snapshot)
        after_pieces = {
            piece['name']: piece['id'] for piece in after['pieces']}

        self.assertNotEqual(
            before_pieces['Declared'], after_pieces['Declared'],
            'a node redeclared at a new precision must be a different '
            'printed piece, since piece identity is a fingerprint of '
            "the built artifact's content")
        self.assertEqual(
            before_pieces['Undeclared'], after_pieces['Undeclared'],
            "the sibling's piece id must be unaffected")


##############################################
# Section 3: downstream verdicts


class FacetedCurvedLeaf(CadQueryNode):

    angular_deflection = 0.5

    def render(self):
        return cq.Workplane('XY').sphere(5)


class FacetedDefaultLeaf(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').sphere(5)


class FacetedPrecisionTest(TestCase):
    """Task 3.1: under `solid test --faceted`, a comparison reads a
    node's mesh from its stl_file (AbstractBaseNode.base_mesh /
    .mesh), never from shape() -- so the comparison necessarily judges
    on whatever precision the node declared. It is enough to show the
    mesh the faceted kernel reads for a coarse node carries the coarse
    triangle count (tasks.md 3.1's direction); no clearance is
    engineered to flip."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.old_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name
        _shape_cache.clear()
        self.addCleanup(test_module.set_comparison_policy, None)
        test_module._verdict_cache.clear()

    def tearDown(self):
        if self.old_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.old_build_dir

    def test_the_faceted_kernel_reads_the_declared_mesh(self):
        coarse = FacetedCurvedLeaf()
        coarse.assemble()
        default = FacetedDefaultLeaf()
        default.assemble()
        direct_coarse_count = len(trimesh.load(
            coarse.stl_file, process=False, file_type='stl').faces)
        direct_default_count = len(trimesh.load(
            default.stl_file, process=False, file_type='stl').faces)
        self.assertLess(direct_coarse_count, direct_default_count)

        test_module.set_comparison_policy(
            test_module.ComparisonPolicy('faceted', 0.0))

        with patch.object(coarse, 'shape', side_effect=AssertionError(
                'a faceted comparison must not read shape()')), \
             patch.object(default, 'shape', side_effect=AssertionError(
                'a faceted comparison must not read shape()')):
            stats = test_module._intersection_stats(coarse, default)
            coarse_mesh_faces = len(coarse.mesh.faces)
            default_mesh_faces = len(default.mesh.faces)

        self.assertFalse(stats.exact)
        self.assertEqual(coarse_mesh_faces, direct_coarse_count,
                         "the faceted kernel's mesh for the coarse node "
                         'must be the coarse artifact it declared, not a '
                         'default-precision re-tessellation')
        self.assertEqual(default_mesh_faces, direct_default_count)
        self.assertLess(coarse_mesh_faces, default_mesh_faces)
