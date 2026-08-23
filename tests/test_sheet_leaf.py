# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The sheet leaf: a part authored as a 2D profile plus a thickness.

What is worth testing here is the invariant the type exists for: the solid
in the tree and the cut file on disk both derive from the one authored
profile, so they cannot drift apart. Everything else -- exactness, the STL
and BREP, the freshness guard -- is `ExactLeafNode`'s and is only checked
where the sheet leaf extends it: the DXF joins the artifact set, and the
profile has a contract of its own that a generic render result does not.
"""

import math
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import build123d as b3d
import cadquery as cq
import ezdxf

from solid_node.exact import solid_count
from solid_node.node import (Build123dNode, Build123dSheetNode, CadQueryNode,
                             FusionNode, SheetLeafNode)
from solid_node.openscad import openscad_binary

from .sheet_project import frame_panel


PLATE_WIDTH = 40
PLATE_HEIGHT = 20
PLATE_THICKNESS = 6
HOLE_RADIUS = 3
SLOT_WIDTH = 6
SLOT_HEIGHT = 3


class Plate(Build123dSheetNode):
    """The simplest sheet part: a rectangle of stock."""

    thickness = PLATE_THICKNESS

    def profile(self):
        return b3d.Rectangle(PLATE_WIDTH, PLATE_HEIGHT)


class PerforatedPlate(Build123dSheetNode):
    """The same panel with a round hole and a t-slot-shaped cutout, the
    features a laser cutter actually has to reproduce."""

    thickness = PLATE_THICKNESS

    def profile(self):
        return (
            b3d.Rectangle(PLATE_WIDTH, PLATE_HEIGHT)
            - b3d.Pos(10, 0) * b3d.Circle(HOLE_RADIUS)
            - b3d.Pos(-12, 4) * b3d.Rectangle(SLOT_WIDTH, SLOT_HEIGHT)
        )


class FaceProfilePlate(Build123dSheetNode):
    """profile() returning a bare Face rather than a sketch."""

    thickness = 2

    def profile(self):
        return b3d.Rectangle(10, 10).faces()[0]


class BuilderProfilePlate(Build123dSheetNode):
    """profile() returning the BuildSketch builder rather than its sketch --
    the sketch-mode twin of the mistake Build123dNode already forgives."""

    thickness = 2

    def profile(self):
        with b3d.BuildSketch() as sketch:
            b3d.Rectangle(10, 10)
        return sketch


class DisjointPlate(Build123dSheetNode):
    """Two islands of material: two parts, not one."""

    thickness = 3

    def profile(self):
        return (b3d.Pos(-10, 0) * b3d.Rectangle(4, 4)
                + b3d.Pos(10, 0) * b3d.Rectangle(4, 4))


class SolidProfilePlate(Build123dSheetNode):
    """A solid where a profile belongs: the sheet leaf's characteristic
    authoring mistake, since a Build123dNode would accept this."""

    thickness = 3

    def profile(self):
        return b3d.Box(4, 4, 4)


class CurveProfilePlate(Build123dSheetNode):

    thickness = 3

    def profile(self):
        return b3d.Line((0, 0), (4, 4))


class OffPlanePlate(Build123dSheetNode):
    """A planar face, but not on the XY plane the extrusion starts from."""

    thickness = 3

    def profile(self):
        return b3d.Plane.XZ * b3d.Rectangle(10, 10)


class UndeclaredThicknessPlate(Build123dSheetNode):

    def profile(self):
        return b3d.Rectangle(10, 10)


class Panel(Build123dSheetNode):
    """A panel whose thickness is a constructor argument, so one class can
    be cut from two stocks."""

    def __init__(self, thickness, **kwargs):
        super().__init__(thickness=thickness, **kwargs)

    def profile(self):
        return b3d.Rectangle(10, 10)


class NegativeThicknessPlate(Build123dSheetNode):

    thickness = -1

    def profile(self):
        return b3d.Rectangle(10, 10)


class ZeroThicknessPlate(Build123dSheetNode):

    thickness = 0

    def profile(self):
        return b3d.Rectangle(10, 10)


class CadQueryBoss(CadQueryNode):
    """A solid overlapping the plate, modelled in the other exact backend."""

    def render(self):
        return cq.Workplane('XY').box(8, 8, 8)


class SheetAndBossFusion(FusionNode):
    """One printed solid: a sheet panel with a machined boss on it."""

    def __init__(self):
        self.panel = Plate()
        self.boss = CadQueryBoss()
        super().__init__()

    def render(self):
        return [self.panel, self.boss]


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


def dxf_entities(path):
    """The modelspace entity types of a DXF, counted by type."""
    modelspace = ezdxf.readfile(path).modelspace()
    counted = {}
    for entity in modelspace:
        counted[entity.dxftype()] = counted.get(entity.dxftype(), 0) + 1
    return counted


def counted_polylines(path):
    """How much of the profile was tessellated instead of kept as curves."""
    modelspace = ezdxf.readfile(path).modelspace()
    return sum(1 for entity in modelspace
               if entity.dxftype() in ('POLYLINE', 'LWPOLYLINE'))


class SheetSolidTest(BuildDirTestCase):
    """The derived solid: the profile extruded from the XY plane."""

    def test_the_solid_is_the_profile_extruded_by_the_thickness(self):
        node = Plate()
        node.assemble()

        volume = PLATE_WIDTH * PLATE_HEIGHT * PLATE_THICKNESS
        self.assertAlmostEqual(node.shape().Volume(), volume, places=6)

    def test_the_solid_runs_from_the_xy_plane_to_the_thickness(self):
        node = Plate()
        node.assemble()

        bounds = node.shape().BoundingBox()

        self.assertAlmostEqual(bounds.zmin, 0.0, places=6)
        self.assertAlmostEqual(bounds.zmax, PLATE_THICKNESS, places=6)

    def test_a_profile_with_holes_is_pierced_through_the_thickness(self):
        node = PerforatedPlate()
        node.assemble()

        area = (PLATE_WIDTH * PLATE_HEIGHT
                - 3.141592653589793 * HOLE_RADIUS ** 2
                - SLOT_WIDTH * SLOT_HEIGHT)

        self.assertAlmostEqual(node.shape().Volume(),
                               area * PLATE_THICKNESS, places=4)

    def test_a_face_profile_is_accepted(self):
        node = FaceProfilePlate()
        node.assemble()

        self.assertAlmostEqual(node.shape().Volume(), 200.0, places=6)

    def test_a_sketch_builder_profile_is_accepted(self):
        node = BuilderProfilePlate()
        node.assemble()

        self.assertAlmostEqual(node.shape().Volume(), 200.0, places=6)

    def test_render_is_not_the_extension_point(self):
        """The base owns render(), so a subclass that never writes one still
        renders -- and what it renders is derived from profile()."""
        self.assertIs(Build123dSheetNode.render, SheetLeafNode.render)
        self.assertNotIn('render', Plate.__dict__)


class SheetThicknessTest(BuildDirTestCase):

    def test_a_missing_thickness_fails_at_construction_naming_the_node(self):
        with self.assertRaises(Exception) as raised:
            UndeclaredThicknessPlate(name='side_panel')

        self.assertIn('side_panel', str(raised.exception))

    def test_a_zero_thickness_fails_at_construction_naming_the_node(self):
        with self.assertRaises(Exception) as raised:
            ZeroThicknessPlate(name='shim')

        self.assertIn('shim', str(raised.exception))

    def test_a_negative_thickness_fails_at_construction_naming_the_node(self):
        with self.assertRaises(Exception) as raised:
            NegativeThicknessPlate(name='spacer')

        self.assertIn('spacer', str(raised.exception))

    def test_two_thicknesses_are_two_parts(self):
        thin = Panel(3)
        thick = Panel(6)

        self.assertNotEqual(thin.uniq_id, thick.uniq_id)
        self.assertNotEqual(thin.stl_file, thick.stl_file)
        self.assertNotEqual(thin.dxf_file, thick.dxf_file)

    def test_two_thicknesses_do_not_reuse_each_others_artifacts(self):
        thin = Panel(3)
        thin.assemble()
        thick = Panel(6)
        thick.assemble()

        self.assertAlmostEqual(thin.shape().Volume(), 300.0, places=6)
        self.assertAlmostEqual(thick.shape().Volume(), 600.0, places=6)


class SheetProfileValidationTest(BuildDirTestCase):
    """One sheet leaf is one part, and a part is one planar face."""

    def test_two_disjoint_faces_are_rejected_naming_the_node(self):
        node = DisjointPlate(name='bracket_pair')

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('bracket_pair', str(raised.exception))

    def test_two_disjoint_faces_write_no_artifact(self):
        node = DisjointPlate(name='bracket_pair')

        with self.assertRaises(Exception):
            node.assemble()

        self.assertFalse(os.path.exists(node.stl_file))
        self.assertFalse(os.path.exists(node.brep_file))
        self.assertFalse(os.path.exists(node.dxf_file))

    def test_a_solid_profile_is_rejected_naming_node_and_type(self):
        node = SolidProfilePlate(name='riser')

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('riser', str(raised.exception))
        self.assertIn('Box', str(raised.exception))

    def test_a_curve_profile_is_rejected_naming_node_and_type(self):
        node = CurveProfilePlate(name='outline')

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('outline', str(raised.exception))
        self.assertIn('Line', str(raised.exception))

    def test_a_profile_off_the_xy_plane_is_rejected_naming_the_node(self):
        node = OffPlanePlate(name='web')

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('web', str(raised.exception))


class SheetDxfArtifactTest(BuildDirTestCase):
    """The cut file is an artifact like the STL and the BREP."""

    def test_the_dxf_is_written_beside_the_stl(self):
        node = PerforatedPlate()
        node.assemble()

        self.assertTrue(os.path.exists(node.dxf_file))
        self.assertEqual(os.path.dirname(node.dxf_file),
                         os.path.dirname(node.stl_file))
        self.assertEqual(node.dxf_file,
                         f'{node.stl_file[:-len(".stl")]}.dxf')

    def test_the_dxf_carries_the_boundary_and_the_holes(self):
        node = PerforatedPlate()
        node.assemble()

        counted = dxf_entities(node.dxf_file)

        # four sides of the panel plus four of the rectangular cutout,
        # and the round hole as its own entity.
        self.assertEqual(counted.get('LINE'), 8)
        self.assertEqual(counted.get('CIRCLE'), 1)

    def test_a_circular_hole_survives_as_an_arc_at_the_modelled_radius(self):
        node = PerforatedPlate()
        node.assemble()

        modelspace = ezdxf.readfile(node.dxf_file).modelspace()
        curved = [entity for entity in modelspace
                  if entity.dxftype() in ('CIRCLE', 'ARC')]

        self.assertEqual(len(curved), 1)
        self.assertAlmostEqual(curved[0].dxf.radius, HOLE_RADIUS, places=6)
        self.assertEqual(counted_polylines(node.dxf_file), 0)

    def test_the_dxf_is_in_millimetres_at_model_scale(self):
        node = PerforatedPlate()
        node.assemble()

        document = ezdxf.readfile(node.dxf_file)
        extents = [abs(vertex[0]) for entity in document.modelspace()
                   if entity.dxftype() == 'LINE'
                   for vertex in (entity.dxf.start, entity.dxf.end)]

        # 4 == ezdxf's $INSUNITS for millimeters
        self.assertEqual(document.header.get('$INSUNITS'), 4)
        self.assertAlmostEqual(max(extents), PLATE_WIDTH / 2, places=6)

    def test_a_current_dxf_is_not_rewritten(self):
        node = PerforatedPlate()
        node.assemble()

        second = PerforatedPlate()
        with patch('solid_node.node.adapters.build123d_sheet._export_dxf',
                   side_effect=AssertionError('must not re-export')):
            assembled = second.as_scad(second.render())

        self.assertIn(second.local_stl, str(assembled))

    def test_a_current_sheet_leaf_skips_its_render_entirely(self):
        node = PerforatedPlate()
        node.assemble()

        second = PerforatedPlate()

        self.assertTrue(second._render_can_be_skipped())

    def test_a_missing_dxf_alone_forces_regeneration(self):
        node = PerforatedPlate()
        node.assemble()
        os.remove(node.dxf_file)

        second = PerforatedPlate()
        self.assertTrue(second._up_to_date(second.stl_file))
        self.assertTrue(second._up_to_date(second.brep_file))
        self.assertFalse(second._render_can_be_skipped())

        second.assemble()

        self.assertTrue(second._up_to_date(second.dxf_file))

    def test_the_dxf_is_stamped_with_the_source_mtime(self):
        node = Plate()
        node.assemble()

        self.assertTrue(node._up_to_date(node.dxf_file))

    def test_the_sheet_leaf_routes_through_the_stl_like_the_other_kernels(self):
        node = Plate()

        assembled = node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))
        self.assertTrue(node._up_to_date(node.brep_file))
        self.assertIn(node.local_stl, str(assembled))


class SheetAdapterContractTest(BuildDirTestCase):
    """The sheet adapter joins the exact roster without disturbing it."""

    def test_the_adapter_is_exact_without_rendering(self):
        self.assertTrue(object.__new__(Build123dSheetNode).exact)

    def test_the_sheet_adapter_is_not_the_solid_build123d_adapter(self):
        sheet = Plate()

        self.assertNotIsInstance(sheet, Build123dNode)
        self.assertFalse(issubclass(Build123dSheetNode, Build123dNode))
        self.assertFalse(issubclass(Build123dNode, Build123dSheetNode))

    def test_the_sheet_adapter_is_not_a_cadquery_node(self):
        self.assertFalse(issubclass(Build123dSheetNode, CadQueryNode))
        self.assertFalse(issubclass(CadQueryNode, Build123dSheetNode))

    def test_the_backend_walk_resolves_no_mesh_backend(self):
        """generate_stl names the backend by walking the MRO for adapter
        class names. The sheet base must not introduce one."""
        mesh_backends = {'Solid2Node', 'OpenScadNode', 'FusionNode'}
        names = {cls.__name__ for cls in Build123dSheetNode.__mro__}

        self.assertEqual(names & mesh_backends, set())

    def test_the_stl_never_reaches_the_openscad_renderer(self):
        node = Plate()
        node.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'an exact backend must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'an exact backend must not launch OpenSCAD')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))

    def test_a_sheet_leaf_builds_with_no_openscad_on_the_path(self):
        openscad_binary.cache_clear()
        self.addCleanup(openscad_binary.cache_clear)

        with patch('solid_node.openscad.shutil.which', return_value=None), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'the subprocess must not be attempted')):
            node = PerforatedPlate()
            node.assemble()
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))
        self.assertTrue(os.path.exists(node.dxf_file))

    def test_a_fusion_of_a_sheet_and_a_cadquery_child_is_exact(self):
        fusion = SheetAndBossFusion()
        fusion.assemble()

        self.assertTrue(fusion.exact)

    def test_a_fusion_of_a_sheet_and_a_cadquery_child_fuses_to_one_solid(self):
        fusion = SheetAndBossFusion()
        fusion.assemble()

        self.assertEqual(solid_count(fusion.shape()), 1)


class SheetImportCostTest(TestCase):

    def test_importing_the_node_package_does_not_import_build123d(self):
        """The sheet adapter is exported from `solid_node.node` like every
        other adapter, and must not make importing that package pay
        build123d's import cost."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, '-c',
             'import sys; import solid_node.node;'
             ' from solid_node.node import Build123dSheetNode;'
             ' print("build123d" in sys.modules)'],
            capture_output=True, text=True, check=True)

        self.assertEqual(result.stdout.strip(), 'False')


class FramePanelProjectTest(BuildDirTestCase):
    """The representative caller: one panel of a laser-cut printer frame,
    built as a project rather than as a fragment, and checked in both of
    the forms it has to reach a maker -- the solid and the cut file."""

    def setUp(self):
        super().setUp()
        self.node = frame_panel.FramePanel()
        self.node.assemble()

    def profile_area(self):
        """The panel's area worked out independently of the model: stock
        less four t-slots (a slot crossed by a nut pocket) and four bolt
        holes."""
        slot = frame_panel.SLOT_LENGTH * frame_panel.SLOT_WIDTH
        pocket = (frame_panel.NUT_POCKET_DEPTH
                  * frame_panel.NUT_POCKET_LENGTH)
        crossing = frame_panel.NUT_POCKET_DEPTH * frame_panel.SLOT_WIDTH
        holes = len(frame_panel.BOLT_HOLES) * math.pi \
            * frame_panel.BOLT_RADIUS ** 2

        return (frame_panel.PANEL_WIDTH * frame_panel.PANEL_HEIGHT
                - 4 * (slot + pocket - crossing)
                - holes)

    def test_the_panel_is_its_profile_in_the_declared_stock(self):
        expected = self.profile_area() * frame_panel.STOCK_THICKNESS

        self.assertAlmostEqual(self.node.shape().Volume(), expected, places=3)

    def test_the_panel_is_one_solid_the_thickness_of_its_stock(self):
        # OCCT pads a bounding box around curved faces, and this panel has
        # bolt holes, so the extent is checked to a manufacturing tolerance
        # rather than to the kernel's last bit.
        bounds = self.node.shape().BoundingBox()

        self.assertEqual(solid_count(self.node.shape()), 1)
        self.assertAlmostEqual(bounds.zmin, 0.0, delta=0.01)
        self.assertAlmostEqual(bounds.zmax, frame_panel.STOCK_THICKNESS,
                               delta=0.01)

    def test_the_cut_file_carries_every_bolt_hole_as_a_circle(self):
        modelspace = ezdxf.readfile(self.node.dxf_file).modelspace()
        circles = [entity for entity in modelspace
                   if entity.dxftype() == 'CIRCLE']

        self.assertEqual(len(circles), len(frame_panel.BOLT_HOLES))
        for circle in circles:
            self.assertAlmostEqual(circle.dxf.radius, frame_panel.BOLT_RADIUS,
                                   places=6)

    def test_the_cut_file_is_not_tessellated(self):
        self.assertEqual(counted_polylines(self.node.dxf_file), 0)

    def test_the_cut_file_is_the_panel_at_model_scale(self):
        modelspace = ezdxf.readfile(self.node.dxf_file).modelspace()
        vertices = [vertex for entity in modelspace
                    if entity.dxftype() == 'LINE'
                    for vertex in (entity.dxf.start, entity.dxf.end)]

        self.assertAlmostEqual(max(v[0] for v in vertices),
                               frame_panel.PANEL_WIDTH / 2, places=6)
        self.assertAlmostEqual(max(v[1] for v in vertices),
                               frame_panel.PANEL_HEIGHT / 2, places=6)

    def test_the_slot_width_follows_the_declared_stock(self):
        """The cut file and the solid come from one profile, so a slot sized
        from `thickness` is the same number in both."""
        modelspace = ezdxf.readfile(self.node.dxf_file).modelspace()
        widths = {round(abs(entity.dxf.start[1] - entity.dxf.end[1]), 6)
                  for entity in modelspace if entity.dxftype() == 'LINE'}

        self.assertIn(round(frame_panel.SLOT_WIDTH, 6), widths)
