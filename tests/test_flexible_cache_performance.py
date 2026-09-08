# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Bounded reusable faceted geometry for flexible leaves.

These tests keep the performance assertion structural: a mesh/Manifold
construction is observable, while timing is deliberately not part of the
contract.  The fixture is the valve-spring shape that motivated P04.
"""

import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import PropertyMock, patch

import solid_node.test as test_module
from solid_node.node import base as base_module
from trimesh.creation import box

from .flexible_project import spring as fixture


class FlexibleFacetedCacheTest(TestCase):

    def setUp(self):
        test_module._flexible_manifold_cache.clear()
        self.addCleanup(test_module._flexible_manifold_cache.clear)

    def spring_at(self, lift):
        machine = fixture.Valvetrain()
        machine.set_state(lift=lift)
        machine.assemble()
        return machine

    def flexible_at(self, node_class, lift):
        node = node_class()
        node.height.value = fixture.FREE_HEIGHT - lift
        return node

    def test_interleaved_three_binding_working_set_constructs_three_meshes(self):
        """The v8-shaped 80-read workload retains all useful bindings."""
        machine = self.spring_at(0.0)
        bindings = (0.0, 4.0, 8.0)
        observations = []

        with patch.object(machine.spring, '_snapshot_mesh',
                          wraps=machine.spring._snapshot_mesh) as evaluated, \
                patch.object(test_module, '_admitted',
                             wraps=test_module._admitted) as admitted:
            for index in range(80):
                lift = bindings[index % len(bindings)]
                machine.set_state(lift=lift)
                manifold, bounds = test_module._flexible_manifold(
                    machine.spring)
                observations.append((
                    tuple(bounds[0]), tuple(bounds[1]), manifold.volume(),
                ))

        self.assertEqual(evaluated.call_count, 3)
        self.assertEqual(admitted.call_count, 3)
        self.assertEqual(len(observations), 80)
        for index, observation in enumerate(observations):
            self.assertEqual(observation, observations[index % 3])

    def test_source_distinct_nodes_with_forced_uniq_id_collisions_do_not_share(self):
        """`uniq_id` is a display/artifact abbreviation, never this key."""
        first = self.flexible_at(fixture.Spring, 2.0)
        second = self.flexible_at(AlternateSpring, 2.0)
        second.uniq_id = first.uniq_id

        with patch.object(first, '_snapshot_mesh',
                          wraps=first._snapshot_mesh) as first_mesh, \
                patch.object(second, '_snapshot_mesh',
                             wraps=second._snapshot_mesh) as second_mesh:
            test_module._flexible_manifold(first)
            test_module._flexible_manifold(second)

        self.assertEqual(first_mesh.call_count, 1)
        self.assertEqual(second_mesh.call_count, 1)
        self.assertEqual(len(test_module._flexible_manifold_cache), 2)

    def test_source_equal_instances_with_full_identity_reuse_one_geometry(self):
        first = self.flexible_at(fixture.Spring, 2.0)
        second = self.flexible_at(fixture.Spring, 2.0)

        with patch.object(first, '_snapshot_mesh',
                          wraps=first._snapshot_mesh) as first_mesh, \
                patch.object(second, '_snapshot_mesh',
                             wraps=second._snapshot_mesh) as second_mesh:
            test_module._flexible_manifold(first)
            test_module._flexible_manifold(second)

        self.assertEqual((first_mesh.call_count, second_mesh.call_count),
                         (1, 0))

    def test_adapter_technology_is_part_of_the_geometry_identity(self):
        first = self.flexible_at(fixture.Spring, 2.0)
        second = self.flexible_at(fixture.Spring, 2.0)
        second.tech = 'other-technology'

        with patch.object(first, '_snapshot_mesh',
                          wraps=first._snapshot_mesh) as first_mesh, \
                patch.object(second, '_snapshot_mesh',
                             wraps=second._snapshot_mesh) as second_mesh:
            test_module._flexible_manifold(first)
            test_module._flexible_manifold(second)

        self.assertEqual((first_mesh.call_count, second_mesh.call_count),
                         (1, 1))

    def test_forced_structural_short_hash_collision_does_not_share(self):
        first = self.flexible_at(AlternateSpring, 2.0)
        second = self.flexible_at(TwinSpring, 2.0)
        second.uniq_id = first.uniq_id

        with patch.object(first, '_snapshot_mesh',
                          wraps=first._snapshot_mesh) as first_mesh, \
                patch.object(second, '_snapshot_mesh',
                             wraps=second._snapshot_mesh) as second_mesh:
            test_module._flexible_manifold(first)
            test_module._flexible_manifold(second)

        self.assertEqual((first_mesh.call_count, second_mesh.call_count),
                         (1, 1))

    def test_shortened_binding_hash_collision_does_not_share_geometry(self):
        """The full canonical binding, not its twelve-hex filename hash, keys geometry."""
        node = self.spring_at(0.0).spring

        with patch.object(base_module, '_HASH_LEN', 0), \
                patch.object(node, '_snapshot_mesh',
                             wraps=node._snapshot_mesh) as evaluated:
            test_module._flexible_manifold(node)
            node._parent.set_state(lift=5.0)
            test_module._flexible_manifold(node)

        self.assertEqual(evaluated.call_count, 2)

    def test_serialized_spec_change_at_one_binding_is_a_cache_miss(self):
        node = self.spring_at(3.0).spring
        original = node._shape_spec

        with patch.object(node, '_snapshot_mesh',
                          wraps=node._snapshot_mesh) as evaluated:
            test_module._flexible_manifold(node)
            with patch.object(node, '_shape_spec',
                              side_effect=lambda rendered: {
                                  **original(rendered), 'revision': 'next',
                              }):
                test_module._flexible_manifold(node)

        self.assertEqual(evaluated.call_count, 2)

    def test_miss_evaluates_the_one_shape_that_supplied_its_identity(self):
        node = self.spring_at(3.0).spring
        observed = []
        original = node.current_shape

        def current_shape():
            rendered = original()
            observed.append(rendered)
            return rendered

        with patch.object(node, 'current_shape', side_effect=current_shape) \
                as current, \
                patch.object(node, '_snapshot_mesh',
                             wraps=node._snapshot_mesh) as evaluated:
            test_module._flexible_manifold(node)

        self.assertEqual(current.call_count, 1)
        self.assertIs(evaluated.call_args.args[0], observed[0])

    def test_unobservable_source_is_never_retained(self):
        node = self.spring_at(3.0).spring

        with patch.object(type(node), 'source_fingerprint',
                          new_callable=PropertyMock,
                          return_value=None), \
                patch.object(node, '_snapshot_mesh',
                             wraps=node._snapshot_mesh) as evaluated:
            test_module._flexible_manifold(node)
            test_module._flexible_manifold(node)

        self.assertEqual(evaluated.call_count, 2)
        self.assertEqual(len(test_module._flexible_manifold_cache), 0)

    def test_signed_zero_binding_values_remain_distinct_cache_identities(self):
        node = self.flexible_at(fixture.Spring, 2.0)
        node.height.value = 0.0
        positive_key, _, _ = node._faceted_cache_snapshot()
        node.height.value = -0.0
        negative_key, _, _ = node._faceted_cache_snapshot()

        self.assertNotEqual(positive_key, negative_key)

    def test_current_source_identity_change_at_one_binding_is_a_cache_miss(self):
        node = self.spring_at(3.0).spring
        with TemporaryDirectory() as directory:
            contributor = os.path.join(directory, 'shape.py')
            with open(contributor, 'w') as source:
                source.write('shape = 1\n')
            node.files.add(contributor)

            with patch.object(node, '_snapshot_mesh',
                              wraps=node._snapshot_mesh) as evaluated:
                test_module._flexible_manifold(node)
                with open(contributor, 'w') as source:
                    source.write('shape = 22\n')
                test_module._flexible_manifold(node)

        self.assertEqual(evaluated.call_count, 2)

    def test_lru_eviction_caps_retention_and_recomputes_a_revisit(self):
        machine = self.spring_at(0.0)
        bindings = (0.0, 2.0, 4.0, 6.0)

        with patch.object(test_module, '_FLEXIBLE_MANIFOLD_CACHE_LIMIT', 3,
                          create=True), \
                patch.object(machine.spring, '_snapshot_mesh',
                             wraps=machine.spring._snapshot_mesh) as evaluated:
            for lift in bindings:
                if lift == bindings[-1]:
                    # The first key was just read, so access order evicts
                    # the second key when this fourth one is admitted.
                    machine.set_state(lift=bindings[0])
                    test_module._flexible_manifold(machine.spring)
                machine.set_state(lift=lift)
                test_module._flexible_manifold(machine.spring)
            self.assertEqual(len(test_module._flexible_manifold_cache), 3)
            machine.set_state(lift=bindings[1])
            test_module._flexible_manifold(machine.spring)

        self.assertEqual(evaluated.call_count, 5)

    def test_default_limit_bounds_a_long_distinct_structural_trajectory(self):
        """Distinct definitions, not one binding, exercise the default cap."""
        limit = test_module._FLEXIBLE_MANIFOLD_CACHE_LIMIT
        node_types = [type(f'DistinctSpring{index}', (fixture.Spring,), {
            '__module__': fixture.Spring.__module__,
        })
                      for index in range(limit * 2)]
        nodes = [self.flexible_at(node_type, 2.0) for node_type in node_types]

        first_manifold, first_bounds = test_module._flexible_manifold(nodes[0])
        for node in nodes[1:]:
            test_module._flexible_manifold(node)
            self.assertLessEqual(len(test_module._flexible_manifold_cache),
                                 limit)
        revisited_manifold, revisited_bounds = test_module._flexible_manifold(
            nodes[0])

        self.assertEqual(len(test_module._flexible_manifold_cache), limit)
        self.assertAlmostEqual(revisited_manifold.volume(),
                               first_manifold.volume())
        self.assertEqual(tuple(revisited_bounds[0]), tuple(first_bounds[0]))
        self.assertEqual(tuple(revisited_bounds[1]), tuple(first_bounds[1]))

    def test_public_base_mesh_override_remains_the_faceted_geometry_seam(self):
        node = self.flexible_at(TranslatedMeshSpring, 2.0)

        with patch.object(node, 'base_mesh', wraps=node.base_mesh) as mesh:
            manifold, local_bounds = test_module._flexible_manifold(node)
            repeated, repeated_bounds = test_module._flexible_manifold(node)

        self.assertEqual(mesh.call_count, 2)
        self.assertGreater(local_bounds[0][0], 50)
        self.assertAlmostEqual(manifold.volume(), repeated.volume())
        self.assertEqual(tuple(local_bounds[0]), tuple(repeated_bounds[0]))
        self.assertEqual(tuple(local_bounds[1]), tuple(repeated_bounds[1]))
        self.assertEqual(len(test_module._flexible_manifold_cache), 0)

    def test_flexible_verdicts_are_not_memoized_after_geometry_reuse(self):
        with TemporaryDirectory(prefix='solid-flex-verdict-') as build, \
                patch.dict(os.environ, {'SOLID_BUILD_DIR': build}):
            machine = self.spring_at(4.0)
            for path in (machine.spring.stl_file, machine.retainer.stl_file):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                box((1, 1, 1)).export(path)

            test_module._verdict_cache.clear()
            with patch.object(type(machine.retainer), 'exact', False), \
                    patch.object(test_module, '_faceted_verdict',
                                 wraps=test_module._faceted_verdict) as verdict:
                test_module._intersection_stats(
                    machine.spring, machine.retainer)
                machine.set_state(lift=8.0)
                test_module._intersection_stats(
                    machine.spring, machine.retainer)

        self.assertEqual(verdict.call_count, 2)
        self.assertEqual(len(test_module._verdict_cache), 0)

    def test_exact_memo_remains_per_instance_and_last_binding_only(self):
        first = self.flexible_at(fixture.Spring, 2.0)
        second = self.flexible_at(fixture.Spring, 2.0)

        with patch.object(first, '_snapshot_shape',
                          return_value=('first', 0.0)) as first_shape, \
                patch.object(second, '_snapshot_shape',
                             return_value=('second', 0.0)) as second_shape:
            self.assertEqual(first._exact_solid(), ('first', 0.0))
            self.assertEqual(first._exact_solid(), ('first', 0.0))
            first.height.value = fixture.FREE_HEIGHT - 4.0
            self.assertEqual(first._exact_solid(), ('first', 0.0))
            self.assertEqual(second._exact_solid(), ('second', 0.0))

        self.assertEqual((first_shape.call_count, second_shape.call_count),
                         (2, 1))


class AlternateSpring(fixture.Spring):
    """The same shape under a separate defining module/source identity."""


class TwinSpring(fixture.Spring):
    """A second class in this module for structural-id collision coverage."""


class TranslatedMeshSpring(fixture.Spring):
    """A project override of FlexibleNode's public mesh seam."""

    def base_mesh(self):
        mesh = super().base_mesh()
        mesh.apply_translation([100, 0, 0])
        return mesh
