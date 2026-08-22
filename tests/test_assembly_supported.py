# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit coverage for the whole-assembly gravity support contract.

`assertAssemblySupported` selects the same topmost rigid solids as
`assertNoSolidInterference` and proves each one is transitively held
against gravity: a solid displaced by `max_drop` along the gravity
vector must land, with positive volume, in another solid, and that
chain must reach a grounded seed.

The fixtures are real STLs of real boxes -- and, where the contract
needs a shape a single box cannot make (a hook's lip, two interlocking
lips), real unions of boxes -- driven by real Translation operations
through the same RigidNode/Assembly doubles the interference contract
uses in tests/test_assembly_integrity.py. Every box is given as its
world x/z (and optionally y) span, because support is entirely a
question about which solid sits above which.
"""

import inspect
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import trimesh
from trimesh.creation import box

import solid_node.test as test_module
from solid_node.node.operations import Translation
from solid_node.test import TestCase as AssertingTestCase

from .test_assembly_integrity import Assembly, RigidNode


asserter = AssertingTestCase()


class ExactRigidNode(RigidNode):
    """A selected solid that also exposes exact B-rep geometry, so the
    pair routing (exact kernel vs cached Manifolds) can be observed."""

    exact = True

    def __init__(self, name, stl_file, shape):
        super().__init__(name, stl_file)
        self._shape = shape

    def shape(self):
        return self._shape


class SupportFixture(TestCase):
    """Box-span fixture builder shared by the cases below."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def _mesh(self, boxes):
        meshes = []
        for spec in boxes:
            x_span, z_span = spec[0], spec[1]
            y_span = spec[2] if len(spec) > 2 else (-1.0, 1.0)
            mesh = box((x_span[1] - x_span[0],
                        y_span[1] - y_span[0],
                        z_span[1] - z_span[0]))
            mesh.apply_translation([(x_span[0] + x_span[1]) / 2,
                                    (y_span[0] + y_span[1]) / 2,
                                    (z_span[0] + z_span[1]) / 2])
            meshes.append(mesh)
        if len(meshes) == 1:
            return meshes[0]
        return trimesh.boolean.union(meshes)

    def welded(self, name, boxes):
        """One printed solid whose STL is the union of `boxes`."""
        path = os.path.join(self.directory.name, f'{name}.stl')
        self._mesh(boxes).export(path)
        return RigidNode(name, path)

    def block(self, name, x_span, z_span, y_span=(-1.0, 1.0)):
        """One printed solid: a box spanning the given world ranges."""
        return self.welded(name, [(x_span, z_span, y_span)])

    def exact_block(self, name, x_span, z_span, y_span=(-1.0, 1.0)):
        """The same box as `block`, additionally exposing exact
        geometry, so a pair of these routes through the kernel."""
        import cadquery as cq

        path = os.path.join(self.directory.name, f'{name}.stl')
        self._mesh([(x_span, z_span, y_span)]).export(path)
        shape = (
            cq.Workplane('XY')
            .box(x_span[1] - x_span[0],
                 y_span[1] - y_span[0],
                 z_span[1] - z_span[0])
            .translate(((x_span[0] + x_span[1]) / 2,
                        (y_span[0] + y_span[1]) / 2,
                        (z_span[0] + z_span[1]) / 2))
            .val()
        )
        return ExactRigidNode(name, path, shape)

    def stack(self):
        """The canonical pair: a base sitting at the assembly's lowest
        extent and a block resting flush on it."""
        base = self.block('base', (-1, 1), (-1, 1))
        top = self.block('top', (-1, 1), (1, 3))
        return base, top, Assembly('root', (base, top))

    def hook(self):
        """A post and a hook hanging beside it, held only by a lip that
        reaches over the post's top face."""
        post = self.block('post', (-1, 1), (-5, 1))
        hook = self.welded('hook', [
            ((-1, 1.5), (1.2, 1.7)),    # lip, over the post's top face
            ((1.2, 2.2), (-3, 1.7)),    # body, hanging clear beside it
        ])
        return post, hook, Assembly('root', (post, hook))

    def leaning_pair(self):
        """Two interlocking pieces that hold each other: `a`'s lip lies
        over `b`'s lip, and `b`'s arm reaches back over `a`'s body, so
        each one's drop lands in the other."""
        first = self.welded('left_hook', [
            ((0, 2), (2, 4)),           # body
            ((2, 2.9), (3.5, 4)),       # lip, over the right hook's lip
        ])
        second = self.welded('right_hook', [
            ((3, 5), (2, 4)),           # body
            ((2.1, 3.2), (2, 2.5)),     # lip, under a's lip
            ((4, 4.5), (3, 5)),         # column
            ((0, 4.5), (4.5, 5)),       # arm, over the left hook's body
        ])
        return first, second


class TrivialSelectionTest(SupportFixture):
    """Zero or one selected solid is already a supported assembly: with
    nothing else to rest on, there is no support question to answer and
    no geometry to load -- exactly as with the interference assertion."""

    def test_single_rigid_root_passes_without_loading_geometry(self):
        leaf = RigidNode('LeafWithoutBuiltGeometry')

        with patch('solid_node.test._cached_manifold',
                   side_effect=AssertionError('geometry must not load')):
            asserter.assertAssemblySupported(leaf)

    def test_empty_assembly_passes_without_loading_geometry(self):
        with patch('solid_node.test._cached_manifold',
                   side_effect=AssertionError('geometry must not load')):
            asserter.assertAssemblySupported(Assembly('empty', ()))

    def test_assertion_exposes_exactly_the_ratified_knobs(self):
        signature = inspect.signature(asserter.assertAssemblySupported)

        self.assertEqual(tuple(signature.parameters),
                         ('node', 'gravity', 'max_drop', 'ground', 'supports'))
        self.assertEqual(signature.parameters['gravity'].default, (0, 0, -1))
        self.assertEqual(signature.parameters['max_drop'].default, 1.0)
        self.assertIsNone(signature.parameters['ground'].default)
        self.assertIsNone(signature.parameters['supports'].default)


class DropSupportTest(SupportFixture):
    """The support edge itself: a solid is held when its drop lands in
    another solid with positive volume."""

    def test_resting_stack_on_the_lowest_solid_passes(self):
        _, _, root = self.stack()

        asserter.assertAssemblySupported(root)

    def test_floating_solid_fails_naming_it_with_drop_and_gravity(self):
        base = self.block('base', (-1, 1), (-1, 1))
        floater = self.block('floater', (-1, 1), (10, 12))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(Assembly('root', (base, floater)))

        message = str(caught.exception)
        self.assertIn('floater', message)
        self.assertNotIn('base', message)
        self.assertIn('dropped 1mm along gravity (0, 0, -1)', message)

    def test_support_through_a_floating_supporter_does_not_ground(self):
        base = self.block('base', (-1, 1), (-1, 1))
        floater = self.block('floater', (-1, 1), (10, 12))
        rider = self.block('rider', (-1, 1), (12, 14))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(
                Assembly('root', (base, floater, rider)))

        message = str(caught.exception)
        self.assertIn('floater', message)
        self.assertIn('rider', message)

    def test_zero_volume_contact_after_the_drop_is_not_support(self):
        base = self.block('base', (-1, 1), (-1, 1))
        # Dropped by exactly 1.0 the block's bottom face lands ON the
        # base's top face: boundary contact, no shared volume, no hold.
        block = self.block('block', (-1, 1), (2, 4))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(Assembly('root', (base, block)))

        self.assertIn('block', str(caught.exception))

    def test_clearance_play_below_the_drop_counts_as_support(self):
        base = self.block('base', (-1, 1), (-1, 1))
        seated = self.block('seated', (-1, 1), (1.3, 3.3))

        asserter.assertAssemblySupported(Assembly('root', (base, seated)))

    def test_a_drop_below_the_clearance_play_reads_as_floating(self):
        """The documented max_drop rule from the other side: a drop
        smaller than the design's vertical play cannot see the seat."""
        base = self.block('base', (-1, 1), (-1, 1))
        seated = self.block('seated', (-1, 1), (1.3, 3.3))

        with self.assertRaises(AssertionError):
            asserter.assertAssemblySupported(
                Assembly('root', (base, seated)), max_drop=0.2)

    def test_hanging_solid_held_by_engagement_passes(self):
        _, _, root = self.hook()

        asserter.assertAssemblySupported(root)

    def test_gravity_direction_selects_which_solids_are_held(self):
        """One assembly, two gravities. The block floats beside a tall
        wall: under Z-down nothing holds it, under X-down the wall
        does."""
        wall = self.block('wall', (-1, 0), (0, 10))
        block = self.block('block', (0.5, 2.5), (5, 7))
        root = Assembly('root', (wall, block))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)
        self.assertIn('block', str(caught.exception))

        asserter.assertAssemblySupported(root, gravity=(-1, 0, 0))

    def test_gravity_vector_is_normalized_rather_than_scaling_the_drop(self):
        base = self.block('base', (-1, 1), (-1, 1))
        seated = self.block('seated', (-1, 1), (1.3, 3.3))
        root = Assembly('root', (base, seated))

        asserter.assertAssemblySupported(root, gravity=(0, 0, -100))
        with self.assertRaises(AssertionError):
            asserter.assertAssemblySupported(
                root, gravity=(0, 0, -100), max_drop=0.2)


class MutualLeanTest(SupportFixture):
    """A cycle of mutually leaning solids is grounded exactly when some
    member reaches the ground; it never grounds itself."""

    def test_mutual_cycle_reaching_the_ground_passes(self):
        first, second = self.leaning_pair()
        # The slab reaches under the LEFT hook only, so the right one is
        # grounded solely through the cycle edge onto its neighbour.
        slab = self.block('slab', (-1, 2), (0, 1.5))

        asserter.assertAssemblySupported(
            Assembly('root', (slab, first, second)), max_drop=1.5)

    def test_mutual_cycle_with_no_path_to_ground_fails_naming_both(self):
        first, second = self.leaning_pair()
        elsewhere = self.block('elsewhere', (10, 12), (0, 1.5))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(
                Assembly('root', (elsewhere, first, second)), max_drop=1.5)

        message = str(caught.exception)
        self.assertIn('left_hook', message)
        self.assertIn('right_hook', message)
        self.assertNotIn('elsewhere', message)


class GroundSeedTest(SupportFixture):
    """Which solids start out grounded."""

    def test_default_seeds_are_the_solids_at_the_furthest_extent(self):
        base, top, root = self.stack()

        asserter.assertAssemblySupported(root)

        # The top is NOT a seed: its own extent along gravity is a whole
        # block away from the assembly's furthest extent. It passes only
        # through its drop edge onto the base.
        with patch('solid_node.test._placed_intersection',
                   return_value=test_module.IntersectionStats(
                       True, 0.0, False)):
            with self.assertRaises(AssertionError) as caught:
                asserter.assertAssemblySupported(root)
        self.assertIn('top', str(caught.exception))
        self.assertNotIn('base', str(caught.exception))

    def test_explicit_ground_replaces_the_default_seeds(self):
        base, top, root = self.stack()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root, ground=top)

        message = str(caught.exception)
        self.assertIn('base', message)
        self.assertNotIn('top', message)

    def test_explicit_ground_naming_the_lowest_solid_passes(self):
        base, _, root = self.stack()

        asserter.assertAssemblySupported(root, ground=base)

    def test_ground_accepts_a_sequence_of_nodes(self):
        base, top, root = self.stack()

        asserter.assertAssemblySupported(root, ground=[base, top])

    def test_ground_resolves_down_through_an_assembly(self):
        base = self.block('base', (-1, 1), (-1, 1))
        top = self.block('top', (-1, 1), (1, 3))
        holder = Assembly('holder', (base,))
        root = Assembly('root', (holder, top))

        asserter.assertAssemblySupported(root, ground=holder)

    def test_ground_resolves_up_from_an_ingredient_of_a_solid(self):
        base, top, root = self.stack()
        ingredient = RigidNode('ingredient')
        ingredient._parent = base
        base.children = (ingredient,)

        asserter.assertAssemblySupported(root, ground=ingredient)

    def test_ground_outside_the_selection_raises(self):
        _, _, root = self.stack()
        stranger = self.block('stranger', (20, 22), (-1, 1))

        with self.assertRaises(ValueError) as caught:
            asserter.assertAssemblySupported(root, ground=stranger)

        self.assertIn('stranger', str(caught.exception))


class DeclaredSupportsTest(SupportFixture):
    """`supports` is the visible exemption for holds the drop test does
    not model: press fits, glue, friction."""

    def friction_fit(self):
        post = self.block('post', (-1, 1), (-5, 1))
        fitted = self.block('fitted', (1, 3), (-1, 1))
        return post, fitted, Assembly('root', (post, fitted))

    def test_friction_fit_fails_without_a_declared_support(self):
        _, _, root = self.friction_fit()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)

        self.assertIn('fitted', str(caught.exception))

    def test_declared_support_holds_a_friction_fit_solid(self):
        post, fitted, root = self.friction_fit()

        asserter.assertAssemblySupported(root, supports=[(fitted, post)])

    def test_declared_support_does_not_ground_a_floating_supporter(self):
        post = self.block('post', (-1, 1), (-5, 1))
        floater = self.block('floater', (5, 7), (10, 12))
        fitted = self.block('fitted', (5, 7), (12, 14))
        root = Assembly('root', (post, floater, fitted))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(
                root, supports=[(fitted, floater)])

        message = str(caught.exception)
        self.assertIn('fitted', message)
        self.assertIn('floater', message)
        self.assertNotIn('post', message)

    def test_unresolvable_supports_pair_raises(self):
        post, fitted, root = self.friction_fit()
        stranger = self.block('stranger', (20, 22), (-1, 1))

        with self.assertRaises(ValueError) as caught:
            asserter.assertAssemblySupported(
                root, supports=[(fitted, stranger)])
        self.assertIn('stranger', str(caught.exception))

        with self.assertRaises(ValueError):
            asserter.assertAssemblySupported(
                root, supports=[(stranger, post)])


class KnobErrorTest(SupportFixture):
    """Invalid knobs are loud, never a silent pass."""

    def test_zero_gravity_raises(self):
        _, _, root = self.stack()

        with self.assertRaises(ValueError) as caught:
            asserter.assertAssemblySupported(root, gravity=(0, 0, 0))

        self.assertIn('gravity', str(caught.exception))

    def test_non_positive_max_drop_raises(self):
        _, _, root = self.stack()

        for value in (0, -1.0):
            with self.subTest(max_drop=value):
                with self.assertRaises(ValueError) as caught:
                    asserter.assertAssemblySupported(root, max_drop=value)
                self.assertIn('max_drop', str(caught.exception))

    def test_invalid_knobs_are_loud_even_for_a_trivial_selection(self):
        leaf = RigidNode('leaf')

        with self.assertRaises(ValueError):
            asserter.assertAssemblySupported(leaf, gravity=(0, 0, 0))
        with self.assertRaises(ValueError):
            asserter.assertAssemblySupported(leaf, max_drop=0)


class ExactRoutingTest(SupportFixture):
    """A pair of exact solids is intersected by the B-rep kernel; any
    other pair goes through the cached Manifolds."""

    def test_exact_assembly_drops_through_the_kernel(self):
        base = self.exact_block('base', (-1, 1), (-1, 1))
        top = self.exact_block('top', (-1, 1), (1, 3))

        with patch('solid_node.test.intersect_shapes',
                   wraps=test_module.intersect_shapes) as kernel:
            asserter.assertAssemblySupported(Assembly('root', (base, top)))

        self.assertEqual(kernel.call_count, 1)

    def test_a_mixed_pair_routes_through_the_manifolds(self):
        base = self.exact_block('base', (-1, 1), (-1, 1))
        top = self.block('top', (-1, 1), (1, 3))

        with patch('solid_node.test.intersect_shapes',
                   wraps=test_module.intersect_shapes) as kernel:
            asserter.assertAssemblySupported(Assembly('root', (base, top)))

        kernel.assert_not_called()

    def test_the_kernel_verdict_still_catches_a_floating_exact_solid(self):
        base = self.exact_block('base', (-1, 1), (-1, 1))
        floater = self.exact_block('floater', (-1, 1), (10, 12))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(Assembly('root', (base, floater)))

        self.assertIn('floater', str(caught.exception))


class BroadPhaseTest(SupportFixture):
    """Only pairs whose displaced and placed world boxes overlap ever
    meet a Boolean."""

    def test_only_bounds_overlapping_pairs_are_intersected(self):
        near_base = self.block('near_base', (-1, 1), (-1, 1))
        near_top = self.block('near_top', (-1, 1), (1, 3))
        far_base = self.block('far_base', (100, 102), (-1, 1))
        far_top = self.block('far_top', (100, 102), (1, 3))
        root = Assembly('root',
                        (near_base, near_top, far_base, far_top))

        with patch('solid_node.test._placed_intersection',
                   wraps=test_module._placed_intersection) as boolean:
            asserter.assertAssemblySupported(root)

        # One drop each for the two resting blocks; nothing across the
        # two clusters, and no solid dropped onto itself.
        self.assertEqual(boolean.call_count, 2)

    def test_a_distant_floating_solid_costs_no_boolean(self):
        base = self.block('base', (-1, 1), (-1, 1))
        top = self.block('top', (-1, 1), (1, 3))
        far = self.block('far', (1000, 1002), (50, 52))
        root = Assembly('root', (base, top, far))

        with patch('solid_node.test._placed_intersection',
                   wraps=test_module._placed_intersection) as boolean:
            with self.assertRaises(AssertionError) as caught:
                asserter.assertAssemblySupported(root)

        self.assertEqual(boolean.call_count, 1)
        self.assertIn('far', str(caught.exception))

    def test_support_candidates_are_directed_and_never_self_paired(self):
        """The candidate index is asked a directed question -- solid i
        DISPLACED against solid j PLACED -- so it must pair the two
        bound sets across, never a solid with its own drop."""
        def span(low_z, high_z):
            return (np.array([0.0, 0.0, low_z]), np.array([1.0, 1.0, high_z]))

        # Solid 0 spans z [0, 1] and solid 1 spans z [1, 2]; dropping by
        # one moves each down a full unit.
        dropped = [span(-1.0, 0.0), span(0.0, 1.0)]
        placed = [span(0.0, 1.0), span(1.0, 2.0)]

        candidates = set(test_module._support_candidates(dropped, placed))

        self.assertEqual(candidates, {(1, 0)})


class KeyframePlacementTest(SupportFixture):
    """The runner's testing instant places the assembly; the assertion
    neither accepts nor sets a keyframe."""

    def test_current_world_placement_controls_the_verdict(self):
        base = self.block('base', (-1, 1), (-1, 1))
        moving = self.block('moving', (-1, 1), (-1, 1))
        nested = Assembly('nested', (moving,))
        root = Assembly('root', (base, nested))

        moving.operations[:] = [Translation([0, 0, 2], moving)]
        asserter.assertAssemblySupported(root)

        moving.operations[:] = [Translation([0, 0, 10], moving)]
        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)
        self.assertIn('moving', str(caught.exception))
