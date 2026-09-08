# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The molejo adapter: the first flexible leaf technology.

What is under test here is the seam, not molejo. molejo's own fixtures
pin its evaluators to each other; this file proves that what the node
publishes IS molejo's evaluation of the shape its `render()` authored, at
the values its ports carry -- and that the artifact lifecycle around it
behaves: one file per binding, mtime currency within a binding, and the
build's sweep collecting the bindings nothing references any more.

The fixture is a valve spring, the part the v8-engine project designed
around because the framework could not model it, plus a straight cable
run whose swept volume has a closed form to check the mesh against.
"""

import json
import os
import time
from unittest.mock import patch

import molejo
import molejo.brep
import numpy as np
import trimesh
from solid2 import cube

from solid_node.core.builder import Builder
from solid_node.exact import solid_count, solid_volume
from solid_node.node import MolejoNode
from solid_node.node.base import binding_hash
from solid_node.node.flexible import FlexibleNode
from solid_node.node.qualified import DriverToken
from solid_node.test import TestCase as GeometryTestCase, _intersection_stats

from .base import BaseNodeTest
from .flexible_project import spring as fixture


asserter = GeometryTestCase()


def bound_valvetrain(lift=0.0):
    node = fixture.Valvetrain()
    node.set_state(lift=lift)
    return node


class MolejoRenderContractTest(BaseNodeTest):
    """`render()` returns the backend's object, as every adapter does."""

    def test_the_adapter_declares_the_molejo_namespace(self):
        self.assertEqual(MolejoNode.namespace, 'molejo')

    def test_the_adapter_is_a_flexible_leaf(self):
        self.assertTrue(issubclass(MolejoNode, FlexibleNode))
        self.assertFalse(fixture.Spring().rigid)

    def test_a_shape_whose_parameters_match_its_ports_assembles(self):
        node = bound_valvetrain(lift=4.0)

        assembled = node.assemble()

        self.assertEqual(node.spring.height.value, fixture.FREE_HEIGHT - 4.0)
        self.assertIn('.stl', str(assembled))

    def test_a_result_outside_the_namespace_is_rejected_naming_the_node(self):
        node = fixture.WrongBackendSpring()

        with self.assertRaises(Exception) as raised:
            node.validate(cube(4, center=True))

        message = str(raised.exception)
        self.assertIn('WrongBackendSpring', message)
        self.assertIn('molejo', message)

    def test_a_parameter_without_a_port_fails_naming_both_name_sets(self):
        node = fixture.UnportedSpring()

        with self.assertRaises(Exception) as raised:
            node.assemble()

        message = str(raised.exception)
        self.assertIn('UnportedSpring', message)
        self.assertIn('height', message)
        self.assertIn('none', message)

    def test_molejos_own_evaluation_failure_is_surfaced_verbatim(self):
        """The adapter never wraps molejo's error: a dangling parameter
        names itself and its slot in the document."""
        shape = fixture.Cable().render()

        with self.assertRaises(molejo.EvaluationError) as raised:
            shape.evaluate()

        self.assertIn('length', str(raised.exception))


class MolejoMeshTest(BaseNodeTest):
    """The mesh is molejo's evaluation of the same spec and values."""

    def evaluated(self, node):
        return node.render().evaluate(**node.bound_values())

    def test_the_mesh_is_molejos_evaluation_of_the_same_spec(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()
        expected = self.evaluated(node.spring)

        mesh = node.spring.base_mesh()

        self.assertEqual(len(mesh.vertices), len(expected.vertices))
        np.testing.assert_array_equal(np.asarray(mesh.vertices),
                                      expected.vertices)
        np.testing.assert_array_equal(np.asarray(mesh.faces), expected.faces)

    def test_the_vertex_count_is_the_declared_tessellation(self):
        """molejo's tessellation is declared, never adaptive: the count
        is what makes per-frame buffer reuse safe, so it must not depend
        on the binding."""
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        at_rest = len(node.spring.base_mesh().vertices)

        node.set_state(lift=fixture.MAX_LIFT)

        self.assertEqual(len(node.spring.base_mesh().vertices), at_rest)

    def test_a_straight_run_matches_its_analytic_volume(self):
        cable = fixture.Cable()
        cable.length.value = 50.0

        mesh = cable.base_mesh()

        # A regular n-gon inscribed in the circle, swept: the mesh is the
        # analytic cylinder scaled by (n / 2pi) sin(2pi / n).
        analytic = np.pi * fixture.CABLE_RADIUS ** 2 * 50.0
        polygonal = analytic * (
            fixture.CABLE_PROFILE_SAMPLES / (2 * np.pi)
        ) * np.sin(2 * np.pi / fixture.CABLE_PROFILE_SAMPLES)

        self.assertTrue(mesh.is_watertight)
        self.assertAlmostEqual(mesh.volume, polygonal, places=6)
        self.assertLess(abs(mesh.volume - analytic) / analytic, 0.01)

    def test_two_bindings_give_two_meshes(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        at_rest = node.spring.base_mesh()

        node.set_state(lift=fixture.MAX_LIFT)
        compressed = node.spring.base_mesh()

        self.assertLess(compressed.bounds[1][2], at_rest.bounds[1][2])
        self.assertFalse(np.array_equal(np.asarray(at_rest.vertices),
                                        np.asarray(compressed.vertices)))

    def test_one_binding_evaluates_deterministically(self):
        node = bound_valvetrain(lift=4.0)

        first = node.spring.render().evaluate(**node.spring.bound_values())
        second = node.spring.render().evaluate(**node.spring.bound_values())

        self.assertEqual(first.to_stl(), second.to_stl())

    def test_the_world_mesh_places_the_evaluated_geometry(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        node.spring.translate([0, 0, 10])

        np.testing.assert_allclose(
            node.spring.mesh.bounds[0],
            node.spring.base_mesh().bounds[0] + [0, 0, 10], atol=1e-6)


class MolejoExactTest(BaseNodeTest):
    """The exact path: molejo's B-rep evaluator, at the bound instant.

    A spring is only interesting to an assertion when it is somewhere,
    and where it is depends on the machine -- so the exact geometry of a
    flexible leaf is per-instant, evaluated from the same spec and the
    same bound values the mesh comes from. Exactness itself is not:
    `MolejoNode.exact` is fixed by adapter type, like every exact
    adapter's, so a type test never has to render anything.
    """

    def test_the_adapter_is_exact_by_type_without_rendering(self):
        self.assertTrue(object.__new__(MolejoNode).exact)

    def test_the_shape_is_one_closed_solid_at_the_binding(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()

        shape = node.spring.shape()

        self.assertEqual(solid_count(shape), 1)
        self.assertTrue(shape.isValid())
        self.assertGreater(solid_volume(shape), 0.0)

    def test_the_shape_is_molejos_brep_evaluation_of_the_same_spec(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()
        expected = molejo.brep.evaluate(node.spring.render().to_dict(),
                                        node.spring.bound_values())

        # The same solid, measured twice: molejo integrates it through
        # its own kernel accessor and the framework through CadQuery's,
        # which agree to the approximation the sweep declares rather than
        # to the last bit.
        volume = solid_volume(node.spring.shape())
        self.assertLess(abs(volume - expected.volume()) / expected.volume(),
                        node.spring.shape_tolerance)
        self.assertTrue(expected.is_closed())

    def test_the_shape_volume_agrees_with_the_mesh_volume(self):
        """One-sided on purpose: the faceted mesh is inscribed in the
        smooth solid, so it UNDERSTATES it, and a mesh that came out
        bigger would mean the two evaluators disagree about the part."""
        node = bound_valvetrain(lift=4.0)
        node.assemble()

        exact_volume = solid_volume(node.spring.shape())
        mesh_volume = node.spring.base_mesh().volume

        self.assertLessEqual(mesh_volume, exact_volume)
        # Measured 3.0% for this spring at molejo's declared 240x16
        # tessellation of a 2mm wire on a 14mm coil.
        self.assertLess((exact_volume - mesh_volume) / exact_volume, 0.05)

    def test_an_analytic_run_agrees_far_more_closely(self):
        """The same one-sided rule at a finer profile: a 64-gon cylinder
        is within 0.2% of the true one, and the exact solid is the true
        one -- the analytic volume, not a finer facet sum."""
        cable = fixture.Cable()
        cable.length.value = 50.0

        exact_volume = solid_volume(cable.shape())
        mesh_volume = cable.base_mesh().volume
        analytic = np.pi * fixture.CABLE_RADIUS ** 2 * 50.0

        self.assertAlmostEqual(exact_volume, analytic, places=6)
        self.assertLessEqual(mesh_volume, exact_volume)
        self.assertLess((exact_volume - mesh_volume) / exact_volume, 0.005)

    def test_the_declared_approximation_tolerance_is_surfaced(self):
        """molejo declares where it approximated; hiding that would make
        the framework claim an exactness the geometry does not keep."""
        node = bound_valvetrain(lift=4.0)
        node.assemble()
        cable = fixture.Cable()
        cable.length.value = 50.0

        self.assertEqual(node.spring.shape_tolerance,
                         molejo.brep.APPROXIMATION)
        self.assertEqual(cable.shape_tolerance, 0.0)

    def test_a_new_binding_gives_a_new_solid(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        at_rest = solid_volume(node.spring.shape())

        node.set_state(lift=fixture.MAX_LIFT)

        self.assertNotAlmostEqual(solid_volume(node.spring.shape()), at_rest,
                                  places=3)

    def test_an_unbound_port_on_the_exact_path_names_node_and_port(self):
        node = fixture.Spring()

        with self.assertRaises(Exception) as raised:
            node.shape()

        message = str(raised.exception)
        self.assertIn('Spring', message)
        self.assertIn('height', message)

    def test_no_brep_artifact_is_persisted_for_a_flexible_leaf(self):
        """A flexible leaf's solid is computed on demand. Persistence and
        mtime currency are structurally about RIGID nodes -- the builder
        requires a `.brep` only for a node that is both rigid and exact,
        and the post-build sweep spares every `.brep` unconditionally, so
        a per-binding one could never be collected."""
        node = bound_valvetrain(lift=4.0)
        node.assemble()

        node.spring.shape()

        self.assertFalse(os.path.exists(node.spring.brep_file))
        directory = os.path.dirname(node.spring.basepath)
        prefix = os.path.basename(node.spring.basepath)
        self.assertEqual([name for name in os.listdir(directory)
                          if name.startswith(prefix)
                          and name.endswith('.brep')], [])


class MolejoExactAssertionTest(BaseNodeTest):
    """A spring instant answers an exact question on B-rep geometry."""

    def assembled(self, lift=4.0):
        node = bound_valvetrain(lift=lift)
        node.assemble()
        return node

    def test_an_assembly_of_a_spring_and_a_rigid_exact_part_is_exact(self):
        node = self.assembled()

        self.assertTrue(node.spring.exact)
        self.assertTrue(node.retainer.exact)
        self.assertTrue(node.exact)

    def test_the_pair_decides_through_the_exact_path(self):
        node = self.assembled()

        with patch.object(node.spring, 'base_mesh', side_effect=AssertionError(
                'an exact question must not read the flexible mesh')):
            stats = _intersection_stats(node.spring, node.retainer)

        self.assertTrue(stats.exact)

    def test_the_public_assertion_decides_on_the_brep_solids(self):
        node = self.assembled()

        with patch.object(node.spring, 'base_mesh', side_effect=AssertionError(
                'an exact assertion must not read the flexible mesh')):
            asserter.assertNotIntersecting(node.spring, node.retainer)


class MolejoTimeFedSnapshotTest(BaseNodeTest):
    """A leaf fed by animation time, which the build keeps symbolic.

    There is no instant to photograph, so the camera declines rather
    than failing the build or inventing one. Everything else about the
    node is unaffected -- this is a statement about the `.scad` path
    alone, and the document is where a flexible part is delivered.
    """

    def snapshots(self, node):
        directory = os.path.dirname(node.valvetrain.spring.basepath)
        prefix = os.path.basename(node.valvetrain.spring.basepath)
        return sorted(name for name in os.listdir(directory)
                      if name.startswith(prefix) and name.endswith('.stl'))

    def test_a_time_fed_flexible_leaf_assembles(self):
        node = fixture.TimedEngine()

        node.assemble()

        self.assertTrue(node._assembled)

    def test_it_writes_no_snapshot_artifact(self):
        node = fixture.TimedEngine()

        node.assemble()

        self.assertIsNone(node.valvetrain.spring.snapshot_file)
        self.assertEqual(self.snapshots(node), [])

    def test_it_contributes_no_geometry_to_the_scad(self):
        node = fixture.TimedEngine()

        node.assemble()

        self.assertNotIn('.stl', node.valvetrain.spring.scad_code)

    def test_the_document_still_carries_the_symbolic_expression(self):
        node = fixture.TimedEngine()
        node.assemble()

        document = node.valvetrain.spring.flexible_document()

        self.assertEqual(document['tech'], 'molejo')
        self.assertIn('$t', document['params']['height'])

    def test_an_unbound_port_still_fails_loudly(self):
        node = fixture.UnboundSpringMachine()

        with self.assertRaises(Exception) as raised:
            node.assemble()

        message = str(raised.exception)
        self.assertIn('height', message)
        self.assertIn('connect', message)


class MolejoSnapshotArtifactTest(BaseNodeTest):
    """One artifact per binding, current within a binding."""

    def snapshots(self, node):
        directory = os.path.dirname(node.spring.basepath)
        prefix = os.path.basename(node.spring.basepath)
        return sorted(name for name in os.listdir(directory)
                      if name.startswith(prefix) and name.endswith('.stl'))

    def test_the_snapshot_is_named_by_the_node_and_the_binding(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()
        values = node.spring.bound_values()

        snapshot = node.spring.snapshot_file

        self.assertEqual(snapshot, node.spring.snapshot_stl_file(values))
        self.assertIn(node.spring.uniq_id, os.path.basename(snapshot))
        self.assertIn(binding_hash(values), os.path.basename(snapshot))
        self.assertTrue(os.path.isfile(snapshot))

    def test_the_scad_imports_the_snapshot(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()

        self.assertIn(os.path.basename(node.spring.snapshot_file),
                      node.spring.scad_code)

    def test_the_snapshot_holds_molejos_evaluation(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()
        expected = node.spring.render().evaluate(**node.spring.bound_values())

        written = trimesh.load(node.spring.snapshot_file, force='mesh')

        self.assertEqual(len(written.faces), len(expected.faces))
        with open(node.spring.snapshot_file, 'rb') as artifact:
            self.assertEqual(artifact.read(), expected.to_stl())

    def test_the_snapshot_is_stamped_with_the_source_mtime(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()

        self.assertTrue(node.spring._up_to_date(node.spring.snapshot_file))

    def test_the_same_binding_does_not_re_evaluate(self):
        node = bound_valvetrain(lift=4.0)
        node.assemble()

        again = bound_valvetrain(lift=4.0)
        rendered = again.spring.render()
        with patch.object(type(again.spring), '_snapshot_stl',
                          side_effect=AssertionError(
                              'a current snapshot must not be re-evaluated')):
            assembled = again.spring.as_scad(rendered)

        self.assertIn(os.path.basename(node.spring.snapshot_file),
                      str(assembled))

    def test_a_different_binding_is_a_different_artifact(self):
        """A build assembles a freshly loaded tree, so the second binding
        arrives the way a later build's would."""
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        at_rest = node.spring.snapshot_file

        moved = bound_valvetrain(lift=fixture.MAX_LIFT)
        moved.assemble()
        compressed = moved.spring.snapshot_file

        self.assertNotEqual(at_rest, compressed)
        self.assertEqual(len(self.snapshots(node)), 2)
        self.assertTrue(os.path.isfile(at_rest))
        self.assertTrue(os.path.isfile(compressed))

    def test_a_binding_never_changes_the_nodes_identity(self):
        at_rest = bound_valvetrain(lift=0.0)
        compressed = bound_valvetrain(lift=fixture.MAX_LIFT)

        self.assertEqual(at_rest.spring.uniq_id, compressed.spring.uniq_id)

    def test_an_unbound_port_on_the_scad_path_names_node_and_port(self):
        node = fixture.Spring()

        with self.assertRaises(Exception) as raised:
            node.as_scad(node.render())

        message = str(raised.exception)
        self.assertIn('Spring', message)
        self.assertIn('height', message)

    def test_a_symbolic_binding_on_the_scad_path_fails_loudly(self):
        node = fixture.Spring()
        node.height.value = DriverToken('valvetrain.lift')

        with self.assertRaises(Exception) as raised:
            node.as_scad(node.render())

        message = str(raised.exception)
        self.assertIn('Spring', message)
        self.assertIn('height', message)
        self.assertIn('valvetrain.lift', message)


class MolejoSnapshotSweepTest(BaseNodeTest):
    """A superseded binding's artifact is collected; the bound one is not."""

    def publish(self, node):
        builder = Builder('model.py', build_dir=self.build_dir)
        builder.node = node
        builder._write_viewer_snapshot()
        with open(os.path.join(self.build_dir, 'viewer.json')) as document:
            return json.load(document)

    def test_the_referenced_snapshot_survives_the_sweep(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()

        self.publish(node)

        self.assertTrue(os.path.isfile(node.spring.snapshot_file))

    def touch_sources(self):
        """Age the fixture's source, as the edit a later build follows.

        The build path binds the drivers' declared defaults, so a build
        whose binding differs is a build whose source differs -- which is
        also the only thing that changes the published document, since it
        describes the machine symbolically rather than one pose.
        """
        path = os.path.realpath(fixture.__file__)
        times = (os.path.getatime(path), os.path.getmtime(path))
        self.addCleanup(os.utime, path, times)
        future = time.time() + 10
        os.utime(path, (future, future))

    def test_a_binding_change_alone_republishes_nothing(self):
        """The document is symbolic, so moving the machine does not
        change it -- and a publication that changed nothing sweeps
        nothing, leaving the previous binding's snapshot where it is."""
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        self.publish(node)
        at_rest = node.spring.snapshot_file

        moved = bound_valvetrain(lift=fixture.MAX_LIFT)
        moved.assemble()
        builder = Builder('model.py', build_dir=self.build_dir)
        builder.node = moved

        self.assertFalse(builder._write_viewer_snapshot())
        self.assertNotEqual(moved.spring.snapshot_file, at_rest)
        self.assertTrue(os.path.isfile(at_rest))

    def test_a_superseded_snapshot_is_collected(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()
        self.publish(node)
        superseded = node.spring.snapshot_file

        self.touch_sources()
        moved = bound_valvetrain(lift=fixture.MAX_LIFT)
        moved.assemble()
        self.publish(moved)

        self.assertNotEqual(moved.spring.snapshot_file, superseded)
        self.assertTrue(os.path.isfile(moved.spring.snapshot_file))
        self.assertFalse(os.path.exists(superseded))

    def test_the_rigid_sibling_keeps_its_own_artifact(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()

        self.publish(node)

        self.assertTrue(os.path.isfile(node.retainer.stl_file))

    def test_a_flexible_leaf_is_no_printed_piece(self):
        node = bound_valvetrain(lift=0.0)
        node.assemble()

        document = self.publish(node)
        spring = next(child for child in document['root']['children']
                      if child['name'] == 'spring')

        self.assertNotIn('model', spring)
        self.assertNotIn('piece', spring)
        self.assertEqual([piece['name'] for piece in document['pieces']],
                         ['Retainer'])


class MolejoMeshPathPairTest(BaseNodeTest):
    """A mixed pair -- flexible plus faceted -- decides on the current
    binding, never on a file at the leaf's inherited rigid artifact path.

    The Metamaquina2 belts found this: every pulley in that machine is a
    faceted Solid2Node, so the pair takes the mesh path, and the flexible
    leaf's `stl_file` points at an artifact it never writes -- or worse, at
    a stale one a rigid predecessor of the node left behind.
    """

    def assembled(self, lift=4.0):
        node = bound_valvetrain(lift=lift)
        node.assemble()
        return node

    def faceted(self, node):
        return patch.object(type(node.retainer), 'exact', False)

    def test_the_mixed_pair_does_not_require_a_rigid_artifact(self):
        node = self.assembled()

        self.assertFalse(os.path.exists(node.spring.stl_file))
        with self.faceted(node):
            stats = _intersection_stats(node.spring, node.retainer)

        self.assertFalse(stats.exact)
        self.assertTrue(stats.is_empty or stats.volume == 0.0)

    def test_a_stale_rigid_artifact_cannot_answer_for_the_binding(self):
        node = self.assembled()

        os.makedirs(os.path.dirname(node.spring.stl_file), exist_ok=True)
        box = trimesh.creation.box(extents=(200.0, 200.0, 200.0))
        box.export(node.spring.stl_file)

        with self.faceted(node):
            asserter.assertNotIntersecting(node.spring, node.retainer)

    def test_the_flexible_manifold_is_cached_per_binding(self):
        # A binding no other test uses, so the first read builds and the
        # second proves the (uniq_id, binding) cache -- identical
        # instances at one binding deliberately share an entry.
        node = self.assembled(lift=7.25)

        with self.faceted(node):
            with patch.object(node.spring, '_snapshot_mesh',
                              wraps=node.spring._snapshot_mesh) as evaluated:
                _intersection_stats(node.spring, node.retainer)
                _intersection_stats(node.spring, node.retainer)

        self.assertEqual(evaluated.call_count, 1)
