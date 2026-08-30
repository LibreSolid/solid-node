# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The STL leaf: a committed mesh as a first-class part.

The invariant this type exists for is that a foreign mesh enters the
project on the framework's terms rather than on its own. It is admitted
honestly -- a mesh that is not a closed solid fails at build time,
naming itself, unless the project declares it knows better. It is
selected explicitly -- a file holding a plate of parts is a pack, and a
node says which body it is, learning the pack's contents from the
failure itself. It is corrected in code -- scale and framing are an
`adjust` hook, not a vocabulary of constructor knobs. And what every
consumer downstream sees is the node's own artifact, materialized from
the source, never the foreign file in place.

No binary fixture is committed for any of this. The parts are authored
in CadQuery, exported, and read back as if they had been downloaded, so
the round trip itself is the evidence (design D7 of the `stl-node`
change).
"""

import os
import shutil
import tempfile
import time
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import trimesh

from solid_node.node import (Build123dNode, Build123dSheetNode, CadQueryNode,
                             FusionNode, JScadNode, OpenScadNode, Solid2Node,
                             StlNode)
from solid_node.openscad import openscad_binary

from .stl_project import originals, parts, rack
from .utils import edit_source


PROJECT = os.path.dirname(os.path.realpath(parts.__file__))
PARTS_MODULE = os.path.realpath(parts.__file__)
DIMENSIONS_MODULE = os.path.join(PROJECT, 'dimensions.py')

BRACKET_STL = os.path.join(PROJECT, 'bracket.stl')
PACK_STL = os.path.join(PROJECT, 'pack.stl')
TIE_PACK_STL = os.path.join(PROJECT, 'tie_pack.stl')
MIXED_PACK_STL = os.path.join(PROJECT, 'mixed_pack.stl')
LEAKY_STL = os.path.join(PROJECT, 'leaky.stl')

#: The pack's three bodies, as (size, position). Written to the file in
#: an order that is deliberately NOT the centroid order, so a node that
#: indexed the file's own body order would select the wrong part.
PACK_BODIES = (
    (4, (30, 0, 0)),
    (2, (-10, 0, 0)),
    (3, (5, 0, 0)),
)

#: Three bodies sharing an x, so ordering has to fall through to y and
#: then to z to be decided at all.
TIE_BODIES = (
    (4, (0, 10, 0)),
    (2, (0, 0, 0)),
    (3, (0, 0, 20)),
)


def box_mesh(size, position):
    mesh = trimesh.creation.box((size, size, size))
    mesh.apply_translation(position)
    return mesh


def torn(mesh):
    """The same mesh with one facet removed: a hole a slicer would have
    to guess its way across."""
    torn_mesh = mesh.copy()
    keep = np.ones(len(torn_mesh.faces), dtype=bool)
    keep[0] = False
    torn_mesh.update_faces(keep)
    return torn_mesh


def export_authored_part(NodeClass, path):
    """Build a CadQuery part in a scratch build directory and publish its
    mesh as if it had been downloaded."""
    directory = tempfile.mkdtemp()
    previous = os.environ.get('SOLID_BUILD_DIR')
    os.environ['SOLID_BUILD_DIR'] = directory
    try:
        node = NodeClass()
        node.assemble()
        shutil.copyfile(node.stl_file, path)
    finally:
        if previous is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = previous
        shutil.rmtree(directory, ignore_errors=True)


def setUpModule():
    export_authored_part(originals.OriginalBracket, BRACKET_STL)

    trimesh.util.concatenate(
        [box_mesh(size, position) for size, position in PACK_BODIES]
    ).export(PACK_STL, file_type='stl')

    trimesh.util.concatenate(
        [box_mesh(size, position) for size, position in TIE_BODIES]
    ).export(TIE_PACK_STL, file_type='stl')

    trimesh.util.concatenate([
        box_mesh(2, (-10, 0, 0)),
        torn(box_mesh(2, (10, 0, 0))),
    ]).export(MIXED_PACK_STL, file_type='stl')

    torn(box_mesh(2, (0, 0, 0))).export(LEAKY_STL, file_type='stl')


class UndeclaredPart(StlNode):
    """A subclass that forgot to say which mesh it is."""


class BuildDirTestCase(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.previous_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name

    def tearDown(self):
        if self.previous_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.previous_build_dir

    def keep_times(self, path):
        """Restore a source file's timestamps after a test moves them."""
        times = (os.path.getatime(path), os.path.getmtime(path))
        self.addCleanup(os.utime, path, times)

    def build_in_a_fresh_directory(self, NodeClass):
        """Build one node in a build directory of its own, as a second
        checkout or a cleaned tree would."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        previous = os.environ['SOLID_BUILD_DIR']
        os.environ['SOLID_BUILD_DIR'] = directory.name
        try:
            node = NodeClass()
            node.assemble()
            return node
        finally:
            os.environ['SOLID_BUILD_DIR'] = previous


def realpaths(node):
    return {os.path.realpath(path) for path in node.files}


class StlSourceDeclarationTest(BuildDirTestCase):
    """What the node declares, and what makes its artifact stale."""

    def test_the_declared_file_resolves_beside_the_wrapper_module(self):
        node = parts.Bracket()

        self.assertEqual(os.path.realpath(node.get_source_file()), BRACKET_STL)
        self.assertEqual(os.path.realpath(node.src), BRACKET_STL)

    def test_the_artifacts_mirror_the_source_location(self):
        node = parts.Bracket()

        self.assertEqual(node.basedir, PROJECT)
        self.assertEqual(os.path.basename(node.build_dir),
                         os.path.basename(PROJECT))
        self.assertTrue(node.stl_file.startswith(self.directory.name))

    def test_a_missing_declaration_fails_naming_the_class(self):
        with self.assertRaises(Exception) as raised:
            UndeclaredPart()

        self.assertIn('UndeclaredPart', str(raised.exception))
        self.assertIn('stl_source', str(raised.exception))

    def test_editing_the_mesh_invalidates_the_artifact(self):
        """The mesh IS this leaf's geometry, so a changed mesh must
        invalidate the artifact built from it.

        The file is genuinely rewritten. A stamp that moves over
        unchanged bytes is the case build-pipeline's content-verified
        fallback exists to spare, and this leaf is the one whose source
        set is largest -- a mesh, its wrapper, and what the wrapper
        imports -- so it is worth stating on the real thing.
        """
        self.keep_times(BRACKET_STL)
        built = parts.Bracket()
        built.assemble()
        self.assertTrue(built._up_to_date(built.stl_file))

        edit_source(self, BRACKET_STL)
        future = time.time() + 10
        os.utime(BRACKET_STL, (future, future))

        self.assertFalse(parts.Bracket()._up_to_date(built.stl_file))

    def test_restamping_the_mesh_leaves_the_artifact_current(self):
        """The same file, restamped and not rewritten."""
        self.keep_times(BRACKET_STL)
        built = parts.Bracket()
        built.assemble()

        future = time.time() + 10
        os.utime(BRACKET_STL, (future, future))

        self.assertTrue(parts.Bracket()._up_to_date(built.stl_file))

    def test_the_wrapper_module_is_tracked(self):
        """Unlike every other external-file leaf: the wrapper carries
        `adjust` and `body`, which decide the geometry."""
        self.assertIn(PARTS_MODULE, realpaths(parts.Bracket()))

    def test_editing_the_wrapper_invalidates_the_artifact(self):
        self.keep_times(PARTS_MODULE)
        built = parts.ScaledBracket()
        built.assemble()
        self.assertTrue(built._up_to_date(built.stl_file))

        edit_source(self, PARTS_MODULE)
        future = time.time() + 10
        os.utime(PARTS_MODULE, (future, future))

        self.assertFalse(parts.ScaledBracket()._up_to_date(built.stl_file))

    def test_a_module_the_wrapper_imports_is_tracked(self):
        """The closure is transitive: a constant an `adjust` hook scales
        by decides the artifact too."""
        self.assertIn(os.path.realpath(DIMENSIONS_MODULE),
                      realpaths(parts.ScaledBracket()))


class StlArtifactTest(BuildDirTestCase):
    """The node's own artifact, materialized from the foreign file."""

    def test_the_artifact_is_the_part_the_mesh_came_from(self):
        original = originals.OriginalBracket()
        original.assemble()
        imported = parts.Bracket()
        imported.assemble()

        self.assertAlmostEqual(imported.mesh.volume, original.mesh.volume,
                               places=6)
        np.testing.assert_allclose(imported.mesh.bounds, original.mesh.bounds,
                                   atol=1e-6)

    def test_the_artifact_occupies_the_same_space_as_that_part(self):
        original = originals.OriginalBracket()
        original.assemble()
        imported = parts.Bracket()
        imported.assemble()

        missing = trimesh.boolean.difference([original.mesh, imported.mesh])
        added = trimesh.boolean.difference([imported.mesh, original.mesh])

        self.assertAlmostEqual(missing.volume, 0.0, places=6)
        self.assertAlmostEqual(added.volume, 0.0, places=6)

    def test_the_artifact_is_written_in_binary(self):
        node = parts.Bracket()
        node.assemble()

        with open(node.stl_file, 'rb') as stream:
            head = stream.read(5)
        faces = len(trimesh.load(node.stl_file, force='mesh').faces)

        self.assertNotEqual(head, b'solid')
        self.assertEqual(os.path.getsize(node.stl_file), 84 + 50 * faces)

    def test_the_scad_imports_the_nodes_own_artifact(self):
        node = parts.Bracket()

        assembled = node.assemble()

        self.assertIn(node.local_stl, str(assembled))
        self.assertNotIn('bracket.stl', str(assembled))

    def test_a_current_artifact_is_not_rewritten(self):
        node = parts.Bracket()
        node.assemble()

        second = parts.Bracket()
        with patch('solid_node.node.adapters.stl._load_source_mesh',
                   side_effect=AssertionError('must not re-read source')), \
             patch('solid_node.node.adapters.stl._write_binary_stl',
                   side_effect=AssertionError('must not rewrite artifact')):
            assembled = second.as_scad(second.render())

        self.assertIn(second.local_stl, str(assembled))

    def test_a_missing_artifact_is_regenerated(self):
        node = parts.Bracket()
        node.assemble()
        os.remove(node.stl_file)

        again = parts.Bracket()
        again.assemble()

        self.assertTrue(again._up_to_date(again.stl_file))

    def test_the_artifact_is_stamped_with_the_source_mtime(self):
        node = parts.Bracket()
        node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))

    def test_the_leaf_never_reaches_the_openscad_renderer(self):
        node = parts.Bracket()
        node.assemble()

        with patch('solid_node.node.base.require_openscad',
                   side_effect=AssertionError(
                       'an imported mesh must not check OpenSCAD')), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'an imported mesh must not launch OpenSCAD')):
            node.generate_stl()

        self.assertTrue(os.path.exists(node.stl_file))

    def test_a_project_of_imported_parts_builds_with_no_renderer_at_all(self):
        openscad_binary.cache_clear()
        self.addCleanup(openscad_binary.cache_clear)

        with patch('solid_node.openscad.shutil.which', return_value=None), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'no external renderer may be launched')):
            node = rack.Rack()
            node.build_stls()

        for child in node.children:
            self.assertTrue(os.path.exists(child.stl_file))


class StlWatertightGateTest(BuildDirTestCase):
    """Admission: an open mesh is a defect, not a detail."""

    def test_a_leaky_mesh_is_rejected_naming_the_file_and_the_defect(self):
        node = parts.LeakyPart()

        with self.assertRaises(Exception) as raised:
            node.assemble()

        message = str(raised.exception)
        self.assertIn('leaky.stl', message)
        self.assertIn('watertight', message)
        self.assertIn('open edge', message)

    def test_a_rejected_mesh_leaves_no_artifact(self):
        node = parts.LeakyPart()

        with self.assertRaises(Exception):
            node.assemble()

        self.assertFalse(os.path.exists(node.stl_file))

    def test_the_escape_hatch_admits_a_known_open_mesh(self):
        node = parts.AdmittedLeakyPart()

        node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))
        self.assertFalse(trimesh.load(node.stl_file,
                                      force='mesh').is_watertight)

    def test_the_gate_judges_the_mesh_the_hook_returned(self):
        """A sound source torn open by its own `adjust` is still rejected:
        the hook cannot smuggle a defect past the gate."""
        node = parts.PunctureAdjustedBracket()

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn('watertight', str(raised.exception))
        self.assertFalse(os.path.exists(node.stl_file))

    def test_a_torn_neighbour_does_not_condemn_a_sound_part(self):
        sound = parts.SoundNeighbour()
        sound.assemble()

        self.assertTrue(sound._up_to_date(sound.stl_file))
        self.assertAlmostEqual(sound.mesh.volume, 8.0, places=6)

        with self.assertRaises(Exception) as raised:
            parts.TornNeighbour().assemble()

        self.assertIn('body 1', str(raised.exception))

    def test_the_admission_flag_stays_out_of_artifact_identity(self):
        """It governs admission, never geometry, so it must not key an
        artifact: the same part admitted knowingly is the same part."""
        strict = parts.LeakyPart()

        with patch.object(parts.LeakyPart, 'require_watertight', False):
            lenient = parts.LeakyPart()

        self.assertEqual(strict.uniq_id, lenient.uniq_id)
        self.assertEqual(strict.stl_file, lenient.stl_file)


class StlPackSelectionTest(BuildDirTestCase):
    """A multi-body file is a plate of parts, and a node is one of them."""

    def inventory_error(self, NodeClass):
        with self.assertRaises(Exception) as raised:
            NodeClass().assemble()
        return str(raised.exception)

    def test_an_unselected_pack_reports_its_body_count(self):
        message = self.inventory_error(parts.UnselectedPack)

        self.assertIn('pack.stl', message)
        self.assertIn('3 bodies', message)
        self.assertIn('body', message)

    def test_an_unselected_pack_lists_every_body(self):
        message = self.inventory_error(parts.UnselectedPack)

        for index in range(3):
            self.assertIn(f'body {index}:', message)
        self.assertIn('centroid', message)
        self.assertIn('bounds', message)
        self.assertIn('volume', message)

    def test_the_inventory_carries_each_bodys_place_and_size(self):
        message = self.inventory_error(parts.UnselectedPack)

        # body 0 is the 2mm cube at x=-10, body 2 the 4mm cube at x=30.
        self.assertIn('-10.000', message)
        self.assertIn('30.000', message)
        self.assertIn('8.000', message)
        self.assertIn('64.000', message)

    def test_a_body_index_selects_one_part(self):
        first = parts.FirstPackPart()
        first.assemble()
        last = parts.LastPackPart()
        last.assemble()

        self.assertAlmostEqual(first.mesh.volume, 8.0, places=6)
        self.assertAlmostEqual(last.mesh.volume, 64.0, places=6)

    def test_each_selection_is_its_own_artifact(self):
        first = parts.FirstPackPart()
        last = parts.LastPackPart()

        self.assertNotEqual(first.uniq_id, last.uniq_id)
        self.assertNotEqual(first.stl_file, last.stl_file)

    def test_a_selected_body_keeps_the_place_it_had_in_the_pack(self):
        node = parts.LastPackPart()
        node.assemble()

        np.testing.assert_allclose(node.mesh.centroid, [30, 0, 0], atol=1e-4)

    def test_a_single_body_file_needs_no_selection(self):
        node = parts.Bracket()

        node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))

    def test_body_zero_selects_the_only_body_of_a_single_body_file(self):
        whole = parts.Bracket()
        whole.assemble()
        selected = parts.SoleBodyBracket()
        selected.assemble()

        self.assertAlmostEqual(selected.mesh.volume, whole.mesh.volume,
                               places=6)

    def test_a_body_a_single_body_file_does_not_have_is_rejected(self):
        message = self.inventory_error(parts.SecondBodyOfBracket)

        self.assertIn('bracket.stl', message)
        self.assertIn('1 body', message)
        self.assertIn('body 0:', message)

    def test_an_out_of_range_body_reports_the_inventory(self):
        message = self.inventory_error(parts.OverflowPackPart)

        self.assertIn('3 bodies', message)
        self.assertIn('body 2:', message)

    def test_bodies_are_ordered_on_x_then_y_then_z(self):
        """The tie pack shares an x across all three bodies, so only the
        fall-through to y and then z can decide the order."""
        volumes = []
        for NodeClass in (parts.FirstTieBody, parts.SecondTieBody,
                          parts.ThirdTieBody):
            node = NodeClass()
            node.assemble()
            volumes.append(round(node.mesh.volume, 6))

        # (0,0,0) then (0,0,20) then (0,10,0): 2mm, 3mm and 4mm cubes.
        self.assertEqual(volumes, [8.0, 27.0, 64.0])

    def test_ordering_ignores_the_order_bodies_sit_in_the_file(self):
        """The file lists the 4mm body first; centroid order does not."""
        file_order = [
            round(body.volume, 6) for body in
            trimesh.load(PACK_STL, force='mesh').split(only_watertight=False)
        ]
        node = parts.FirstPackPart()
        node.assemble()

        self.assertEqual(file_order[0], 64.0)
        self.assertAlmostEqual(node.mesh.volume, 8.0, places=6)

    def test_the_same_index_selects_the_same_body_in_a_fresh_build(self):
        first = parts.LastPackPart()
        first.assemble()
        again = self.build_in_a_fresh_directory(parts.LastPackPart)

        self.assertNotEqual(first.stl_file, again.stl_file)
        self.assertAlmostEqual(again.mesh.volume, first.mesh.volume, places=6)
        np.testing.assert_allclose(again.mesh.centroid, first.mesh.centroid,
                                   atol=1e-6)


class StlAdjustTest(BuildDirTestCase):
    """Normalization is code, not knobs."""

    def test_a_hook_correction_reaches_the_artifact(self):
        verbatim = parts.Bracket()
        verbatim.assemble()
        scaled = parts.ScaledBracket()
        scaled.assemble()

        factor = 25.4 ** 3
        self.assertAlmostEqual(scaled.mesh.volume / verbatim.mesh.volume,
                               factor, places=3)
        np.testing.assert_allclose(scaled.mesh.bounds,
                                   verbatim.mesh.bounds * 25.4, atol=1e-3)

    def test_the_correction_is_baked_into_the_artifact_on_disk(self):
        scaled = parts.ScaledBracket()
        scaled.assemble()

        on_disk = trimesh.load(scaled.stl_file, force='mesh')

        self.assertAlmostEqual(on_disk.volume, scaled.mesh.volume, places=3)

    def test_a_node_without_the_hook_imports_verbatim(self):
        node = parts.Bracket()
        node.assemble()

        source = trimesh.load(BRACKET_STL, force='mesh')
        artifact = trimesh.load(node.stl_file, force='mesh')

        self.assertAlmostEqual(artifact.volume, source.volume, places=6)
        np.testing.assert_allclose(artifact.bounds, source.bounds, atol=1e-6)

    def test_the_adapter_offers_no_scale_or_recenter_knobs(self):
        self.assertFalse(hasattr(StlNode, 'scale'))
        self.assertFalse(hasattr(StlNode, 'units'))
        self.assertFalse(hasattr(StlNode, 'recenter'))


class StlAdapterContractTest(BuildDirTestCase):
    """The mesh-import leaf joins the roster without disturbing it."""

    def test_the_adapter_is_not_exact(self):
        self.assertFalse(object.__new__(StlNode).exact)

    def test_the_adapter_exposes_no_exact_geometry(self):
        node = parts.Bracket()

        with self.assertRaises(RuntimeError):
            node.shape()

    def test_the_adapter_is_distinct_from_every_other_leaf(self):
        node = parts.Bracket()

        for other in (CadQueryNode, Build123dNode, Build123dSheetNode,
                      Solid2Node, OpenScadNode, JScadNode):
            self.assertNotIsInstance(node, other)
            self.assertFalse(issubclass(StlNode, other))
            self.assertFalse(issubclass(other, StlNode))

    def test_the_backend_walk_resolves_no_mesh_backend(self):
        """generate_stl names the backend by walking the MRO for adapter
        class names; an imported mesh introduces none."""
        mesh_backends = {'Solid2Node', 'OpenScadNode', 'FusionNode'}
        names = {cls.__name__ for cls in StlNode.__mro__}

        self.assertEqual(names & mesh_backends, set())

    def test_a_fusion_over_an_imported_mesh_is_not_exact(self):
        fusion = rack.PostedBracket()

        fusion.assemble()

        self.assertFalse(fusion.exact)
        self.assertTrue(fusion.rigid)


class StlRackProjectTest(BuildDirTestCase):
    """The representative caller: a rack of downloaded brackets, and one
    of them fused with a part designed to fit it."""

    def test_every_imported_part_materializes_its_artifact(self):
        node = rack.Rack()

        node.assemble()

        for child in node.children:
            self.assertTrue(os.path.exists(child.stl_file))
            self.assertTrue(child._up_to_date(child.stl_file))

    def test_the_assembly_imports_each_materialized_artifact(self):
        node = rack.Rack()

        assembled = node.assemble()

        for child in node.children:
            self.assertIn(child.local_stl, str(assembled))

    def test_placement_moves_the_imported_part(self):
        node = rack.Rack()
        node.assemble()

        near, far = node.children

        np.testing.assert_allclose(near.mesh.centroid,
                                   [0, 0, originals.BRACKET_HEIGHT],
                                   atol=1e-3)
        np.testing.assert_allclose(far.mesh.centroid,
                                   [rack.BRACKET_SPACING, 0, 0], atol=1e-3)

    def test_the_far_bracket_is_turned_by_its_rotation(self):
        node = rack.Rack()
        node.assemble()

        near, far = node.children
        near_extent = near.mesh.bounds[1] - near.mesh.bounds[0]
        far_extent = far.mesh.bounds[1] - far.mesh.bounds[0]

        np.testing.assert_allclose(far_extent,
                                   [near_extent[1], near_extent[0],
                                    near_extent[2]], atol=1e-3)

    def test_a_part_designed_to_fit_fuses_with_the_imported_mesh(self):
        """The whole point of the leaf: the fusion is faceted, so it
        unions through the OpenSCAD mesh path, and the result is one
        solid holding both parts."""
        fusion = rack.PostedBracket()
        fusion.assemble()

        fusion.build_stls()

        fused = trimesh.load(fusion.stl_file, force='mesh')
        bracket, post = fusion.children

        self.assertEqual(len(fused.split(only_watertight=False)), 1)
        self.assertGreater(fused.volume, bracket.mesh.volume)
        self.assertLess(fused.volume,
                        bracket.mesh.volume + post.mesh.volume)
