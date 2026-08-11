# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit coverage for the topmost-rigid assembly interference contract."""

import inspect
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import numpy as np
from trimesh.creation import box

import solid_node.test as test_module
from solid_node.node.operations import Rotation, Translation
from solid_node.test import TestCase as AssertingTestCase


asserter = AssertingTestCase()


class RigidNode:

    rigid = True

    def __init__(self, name, stl_file=None, children=()):
        self.name = name
        self.stl_file = stl_file
        self.children = children
        self.operations = []
        self._parent = None

    def as_number(self, value):
        return float(value)


class Assembly:

    rigid = False

    def __init__(self, name, children):
        self.name = name
        self.children = tuple(children)
        self.operations = []
        self._parent = None
        for child in self.children:
            child._parent = self

    def as_number(self, value):
        return float(value)


class AssemblyIntegrityTestCase(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.box_path = os.path.join(self.directory.name, 'box.stl')
        box((2.0, 2.0, 2.0)).export(self.box_path)

    def part(self, name, translation=None):
        node = RigidNode(name, self.box_path)
        if translation is not None:
            node.operations.append(Translation(translation, node))
        return node

    def test_rigid_root_passes_without_loading_geometry(self):
        leaf = RigidNode('LeafWithoutBuiltGeometry')

        with patch('solid_node.test._cached_manifold',
                   side_effect=AssertionError('geometry must not load')):
            asserter.assertNoSolidInterference(leaf)

    def test_outer_fusion_is_selected_instead_of_its_ingredients(self):
        ingredient_path = os.path.join(self.directory.name, 'ingredient.stl')
        fusion_path = os.path.join(self.directory.name, 'fusion.stl')
        other_path = os.path.join(self.directory.name, 'other.stl')
        for path in (ingredient_path, fusion_path, other_path):
            box((2.0, 2.0, 2.0)).export(path)
        ingredient = RigidNode('Ingredient', ingredient_path)
        fusion = RigidNode('OuterFusion', fusion_path, (ingredient,))
        ingredient._parent = fusion
        other = RigidNode('Other', other_path)
        other.operations.append(Translation([10, 0, 0], other))
        assembly = Assembly('Root', (fusion, other))

        original = test_module._cached_manifold
        with patch('solid_node.test._cached_manifold',
                   wraps=original) as cached:
            asserter.assertNoSolidInterference(assembly)

        loaded = [call.args[0] for call in cached.call_args_list]
        self.assertNotIn(ingredient.stl_file, loaded)
        self.assertEqual(set(loaded), {fusion.stl_file, other.stl_file})

    def test_supplied_subtree_excludes_an_interfering_sibling(self):
        selected_a = self.part('SelectedA')
        selected_b = self.part('SelectedB', [10, 0, 0])
        selected = Assembly('Selected', (selected_a, selected_b))
        outside = self.part('Outside')
        Assembly('Root', (selected, outside))

        asserter.assertNoSolidInterference(selected)

    def test_current_keyframe_world_placement_controls_the_verdict(self):
        fixed = self.part('Fixed')
        moving = self.part('Moving')
        nested = Assembly('Nested', (moving,))
        root = Assembly('Root', (fixed, nested))

        moving.operations[:] = [Translation([3, 0, 0], moving)]
        asserter.assertNoSolidInterference(root)

        moving.operations[:] = [Translation([0.5, 0, 0], moving)]
        with self.assertRaisesRegex(AssertionError, 'Fixed.*Moving|Moving.*Fixed'):
            asserter.assertNoSolidInterference(root)

    def test_positive_overlap_names_the_pair_and_volume(self):
        first = self.part('First')
        second = self.part('Second', [0.5, 0, 0])
        assembly = Assembly('Root', (first, second))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertNoSolidInterference(assembly)

        message = str(caught.exception)
        self.assertIn('First', message)
        self.assertIn('Second', message)
        self.assertIn('intersection volume', message)

    def test_triple_overlap_fails_naming_a_pair(self):
        """Three solids sharing one region. This is the arrangement a
        whole-assembly volume comparison is intuitively good at, so
        prove the pairwise path handles it: shared material among three
        solids necessarily means some two of them share it."""
        solids = [self.part(f'Part{index}') for index in range(3)]

        with self.assertRaises(AssertionError) as caught:
            asserter.assertNoSolidInterference(Assembly('Root', solids))

        message = str(caught.exception)
        self.assertIn('should not interfere with', message)
        self.assertIn('intersection volume', message)
        self.assertEqual(
            sum(f'Part{index}' in message for index in range(3)), 2)

    def test_containment_fails_naming_the_pair(self):
        """A solid wholly inside another, with no surface crossing --
        the case where surface-intersection intuition fails. The
        conservative bounds still make it a candidate, and the exact
        boolean still returns the contained solid."""
        outer_path = os.path.join(self.directory.name, 'outer.stl')
        box((4.0, 4.0, 4.0)).export(outer_path)
        outer = RigidNode('Outer', outer_path)
        inner = self.part('Inner')

        with self.assertRaises(AssertionError) as caught:
            asserter.assertNoSolidInterference(
                Assembly('Root', (outer, inner)))

        message = str(caught.exception)
        self.assertIn('Outer', message)
        self.assertIn('Inner', message)
        self.assertIn('intersection volume', message)

    def test_exact_face_contact_passes_without_an_epsilon(self):
        first = self.part('First')
        second = self.part('Second', [2, 0, 0])

        asserter.assertNoSolidInterference(Assembly('Root', (first, second)))

    def test_rotated_separated_solids_tolerate_volume_roundoff(self):
        solids = []
        for index in range(32):
            node = self.part(f'Part{index}')
            node.operations.extend([
                Rotation(index * 7.3, [0, 0, 1], node),
                Translation([index * 4.1, index * 0.17, 0], node),
            ])
            solids.append(node)

        asserter.assertNoSolidInterference(Assembly('Root', solids))

    def test_assertion_exposes_no_overlap_epsilon(self):
        signature = inspect.signature(asserter.assertNoSolidInterference)

        self.assertEqual(tuple(signature.parameters), ('node',))

    def test_spatial_candidates_emit_only_full_aabb_overlaps(self):
        bounds = [
            (np.array([0, 0, 0]), np.array([1, 1, 1])),
            (np.array([5, 0, 0]), np.array([6, 1, 1])),
            (np.array([0.5, 0.5, 0.5]), np.array([1.5, 1.5, 1.5])),
            (np.array([0.5, 5, 0]), np.array([1.5, 6, 1])),
        ]

        self.assertEqual(list(test_module._bounds_candidates(bounds)), [(0, 2)])

    def test_no_whole_assembly_union_is_computed(self):
        """The point of the change: the assertion reaches its verdict
        through the spatial index alone. No Manifold batch union, no
        Trimesh union, no aggregate measurement of any kind -- those
        cost time proportional to the assembly's total triangle count on
        every passing run and named no offending pair."""
        first = self.part('First')
        second = self.part('Second', [10, 0, 0])

        with patch.object(
                test_module.Manifold, 'batch_boolean',
                side_effect=AssertionError('no whole-assembly union')), \
             patch('solid_node.test.trimesh.boolean.union',
                   side_effect=AssertionError('no whole-assembly union')):
            asserter.assertNoSolidInterference(Assembly(
                'Root', (first, second)))

    def test_bounds_candidates_are_the_verification_path(self):
        first = self.part('First')
        second = self.part('Second', [0.5, 0, 0])

        with patch('solid_node.test._candidate_intersection',
                   return_value=(True, 0.0)) as candidate:
            asserter.assertNoSolidInterference(
                Assembly('Root', (first, second)))

        candidate.assert_called_once()

    def test_nonempty_zero_volume_contact_passes(self):
        first = self.part('First')
        second = self.part('Second', [0.5, 0, 0])

        with patch('solid_node.test._candidate_intersection',
                   return_value=(False, 0.0)):
            asserter.assertNoSolidInterference(
                Assembly('Root', (first, second)))

    def test_any_positive_candidate_volume_fails_without_epsilon(self):
        first = self.part('First')
        second = self.part('Second', [0.5, 0, 0])
        smallest_positive = np.nextafter(0.0, 1.0)

        with patch('solid_node.test._candidate_intersection',
                   return_value=(False, smallest_positive)):
            with self.assertRaisesRegex(AssertionError,
                                        'intersection volume'):
                asserter.assertNoSolidInterference(
                    Assembly('Root', (first, second)))

    def test_sparse_candidate_sweep_does_not_visit_distant_pairs(self):
        bounds = [
            (np.array([index * 3, 0, 0]),
             np.array([index * 3 + 1, 1, 1]))
            for index in range(100)
        ]

        with patch('solid_node.test._boxes_disjoint',
                   wraps=test_module._boxes_disjoint) as disjoint:
            candidates = list(test_module._bounds_candidates(bounds))

        self.assertEqual(candidates, [])
        self.assertEqual(disjoint.call_count, 0)

    def test_deprecated_leaf_sweep_warns_with_migration_target(self):
        leaf = RigidNode('Leaf')

        with self.assertWarnsRegex(
                DeprecationWarning,
                'assertNoSolidInterference.*topmost rigid'):
            asserter.assertNoPairwiseIntersections(leaf)
