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

    def hollowed(self, name, boxes, cavities):
        """One printed solid: the union of `boxes` less the union of
        `cavities` -- the shape a bored block needs, and the only way to
        give a snug hole an upper and a lower wall."""
        path = os.path.join(self.directory.name, f'{name}.stl')
        trimesh.boolean.difference(
            [self._mesh(boxes), self._mesh(cavities)]).export(path)
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
        reaches over the post's top face. The lip is thicker than the
        drop, so the drop straddles that face instead of tunnelling past
        it, and reaches left far enough to put the hook's centre of mass
        over the patch it lands on."""
        post = self.block('post', (-1, 1), (-5, 1))
        hook = self.welded('hook', [
            ((-4, 1.5), (1.2, 2.2)),    # lip, over the post's top face
            ((1.2, 2.2), (-3, 2.2)),    # body, hanging clear beside it
        ])
        return post, hook, Assembly('root', (post, hook))

    def leaning_pair(self):
        """Two interlocking pieces that hold each other: `a`'s tongue
        lies on `b`'s shelf, and `b`'s tongue lies on `a`'s shelf, so
        each one's drop lands in the other. `b` overhangs the patch that
        carries it and stands only because `a`'s tongue restrains it
        from above."""
        first = self.welded('left_hook', [
            ((0, 4), (2, 16)),          # body
            ((3.5, 6.5), (2, 4)),       # shelf, under the right tongue
            ((3.5, 5.5), (7.5, 9.5)),   # tongue, over the right shelf
        ])
        second = self.welded('right_hook', [
            ((4.5, 7.5), (5.5, 7.5)),   # shelf, under the left tongue
            ((5.5, 7.5), (4, 6)),       # tongue, over the left shelf
            ((7, 9), (4, 10)),          # body
        ])
        return first, second

    ####################
    # Equilibrium fixtures: every one of these reaches ground, so the
    # verdict they exercise is the statics phase and nothing else.

    def one_end_bar(self):
        """A horizontal bar whose only landing patch lies under one end,
        with its centre of mass three bar-thicknesses out past it."""
        support = self.block('support', (0, 2), (0, 2))
        bar = self.block('bar', (0, 10), (2, 4))
        return support, bar, Assembly('root', (support, bar))

    def two_end_bar(self):
        """The same bar with a second landing patch under its far end."""
        support = self.block('support', (0, 2), (0, 2))
        far_support = self.block('far_support', (8, 10), (0, 2))
        bar = self.block('bar', (0, 10), (2, 4))
        return bar, Assembly('root', (support, far_support, bar))

    def offset_stack(self):
        """Three solids each resting well inside its own interface,
        whose upper pair's combined centre of mass passes beyond the
        lowest interface's patch."""
        base = self.block('base', (0, 4), (0, 2))
        mid = self.block('mid', (1.5, 5.5), (2, 4))
        top = self.block('top', (4.5, 5.5), (4, 9))
        return mid, Assembly('root', (base, mid, top))

    def counterweighted(self, weight=True):
        """A beam whose own centre of mass overhangs its support patch,
        optionally carrying the counterweight that pulls the combined
        resultant back over the patch."""
        support = self.block('support', (0, 2), (0, 2))
        beam = self.block('beam', (0, 6), (2, 4))
        parts = [support, beam]
        if weight:
            parts.append(self.block('counterweight', (0, 2), (4, 12)))
        return beam, Assembly('root', tuple(parts))

    def pinned_block(self):
        """A pin cantilevering out of a grounded block's snug hole: the
        drop reaches the hole's lower wall, the lift its upper wall, and
        only the couple of the two balances the pin."""
        block = self.hollowed(
            'block',
            [((-4, 0), (0, 6), (-3, 3))],
            [((-4.5, 0.5), (2.9, 4.1), (-1.1, 1.1))])
        pin = self.block('pin', (-4, 10), (3, 4))
        return pin, Assembly('root', (block, pin))

    def tippy_pair(self):
        """A top-heavy solid standing on its own small foot beside a
        squat neighbour: both are default seeds, only one can stand."""
        tippy = self.welded('tippy', [((0, 2), (0, 2)), ((0, 8), (2, 4))])
        neighbour = self.block('neighbour', (20, 24), (0, 2))
        return tippy, neighbour, Assembly('root', (tippy, neighbour))

    def boundary_balance(self):
        """A block whose centre of mass sits exactly over the far edge of
        its landing patch: an equilibrium, but only just."""
        base = self.block('base', (0, 4), (0, 2))
        top = self.block('top', (2, 6), (2, 4))
        return top, Assembly('root', (base, top))

    def overhead_only(self):
        """A solid with nothing under it and a roof above it: the lift
        sweep sees the roof, the support graph must not."""
        frame = self.welded('frame', [((0, 2), (0, 10)), ((0, 8), (10, 12))])
        hung = self.block('hung', (4, 6), (7, 9.5))
        return hung, Assembly('root', (frame, hung))


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

        self.assertEqual(
            tuple(signature.parameters),
            ('node', 'gravity', 'max_drop', 'ground', 'supports',
             'stability_margin'))
        self.assertEqual(signature.parameters['gravity'].default, (0, 0, -1))
        self.assertEqual(signature.parameters['max_drop'].default, 1.0)
        self.assertIsNone(signature.parameters['ground'].default)
        self.assertIsNone(signature.parameters['supports'].default)
        self.assertEqual(signature.parameters['stability_margin'].default, 0.0)


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
        slab = self.block('slab', (0, 4), (0, 2))

        asserter.assertAssemblySupported(
            Assembly('root', (slab, first, second)), max_drop=1.5)

    def test_mutual_cycle_with_no_path_to_ground_fails_naming_both(self):
        first, second = self.leaning_pair()
        elsewhere = self.block('elsewhere', (10, 14), (0, 2))

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
            with patch('solid_node.test._interface_contacts',
                       wraps=test_module._interface_contacts) as extract:
                asserter.assertAssemblySupported(Assembly('root', (base, top)))

        # One kernel Boolean: the drop of the top onto the base. The
        # base's landing on the faceted floor, and every contact patch
        # including the exact pair's, are read off the Manifolds --
        # statics needs a patch's extent, not Boolean validity.
        self.assertEqual(kernel.call_count, 1)
        self.assertIn(('top', 'base'),
                      {(call.args[1].name, call.args[2].name)
                       for call in extract.call_args_list})

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

        # One drop of each upper block onto its own base, and one of
        # each base onto the floor it stands on; nothing across the two
        # clusters, and no solid dropped onto itself.
        self.assertEqual(boolean.call_count, 4)
        self.assertEqual(
            {(call.args[0][0].name, call.args[1][0].name)
             for call in boolean.call_args_list},
            {('near_top', 'near_base'), ('far_top', 'far_base'),
             ('near_base', 'the floor'), ('far_base', 'the floor')})

    def test_a_distant_floating_solid_costs_no_boolean(self):
        base = self.block('base', (-1, 1), (-1, 1))
        top = self.block('top', (-1, 1), (1, 3))
        far = self.block('far', (1000, 1002), (50, 52))
        root = Assembly('root', (base, top, far))

        with patch('solid_node.test._placed_intersection',
                   wraps=test_module._placed_intersection) as boolean:
            with self.assertRaises(AssertionError) as caught:
                asserter.assertAssemblySupported(root)

        # The top onto the base, and the base onto the floor: the
        # distant floater's boxes reach neither.
        self.assertEqual(boolean.call_count, 2)
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


class StaticEquilibriumTest(SupportFixture):
    """Reaching ground is not standing up. Every assembly below is
    transitively supported; the verdict comes from whether push-only
    contact forces over the detected interfaces can balance each solid's
    weight and the torque it makes about its own centre of mass."""

    def test_bar_supported_at_one_end_fails_naming_it_and_the_torque(self):
        _, _, root = self.one_end_bar()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)

        message = str(caught.exception)
        self.assertIn('bar', message)
        self.assertIn('torque', message)
        self.assertIn('supports', message)
        # Not a reachability verdict: the bar does reach ground.
        self.assertNotIn('no support path', message)

    def test_bar_supported_at_both_ends_passes(self):
        _, root = self.two_end_bar()

        asserter.assertAssemblySupported(root)

    def test_offset_stack_beyond_the_lowest_patch_fails(self):
        mid, root = self.offset_stack()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)

        message = str(caught.exception)
        self.assertIn(mid.name, message)
        self.assertIn('torque', message)

    def test_overhanging_beam_fails_without_its_counterweight(self):
        _, root = self.counterweighted(weight=False)

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)

        self.assertIn('beam', str(caught.exception))

    def test_counterweight_restores_a_feasible_distribution(self):
        _, root = self.counterweighted()

        asserter.assertAssemblySupported(root)

    def test_cantilevered_pin_in_a_snug_hole_passes(self):
        _, root = self.pinned_block()

        asserter.assertAssemblySupported(root, max_drop=0.5)

    def test_the_pin_couple_needs_the_lift_detected_contact(self):
        """Without the overhead wall the same pin has only the hole's
        lower wall to push on, and no push-only distribution there can
        cancel the cantilever's torque."""
        block = self.hollowed(
            'block',
            [((-4, 0), (0, 4.1), (-3, 3))],
            [((-4.5, 0.5), (2.9, 4.2), (-1.1, 1.1))])
        pin = self.block('pin', (-4, 10), (3, 4))

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(
                Assembly('root', (block, pin)), max_drop=0.5)

        self.assertIn('pin', str(caught.exception))

    def test_a_solid_whose_edges_yield_no_contact_fails_loudly(self):
        """A reachability edge is not an interface: with contact
        extraction returning nothing, the solid that needs balancing
        fails instead of passing silently."""
        _, _, root = self.stack()

        with patch('solid_node.test._interface_contacts', return_value=[]):
            with self.assertRaises(AssertionError) as caught:
                asserter.assertAssemblySupported(root)

        message = str(caught.exception)
        self.assertIn('equilibrium', message)
        self.assertIn('top', message)

    def test_the_verdict_is_deterministic_across_repeated_runs(self):
        _, _, passing = self.stack()
        _, _, failing = self.one_end_bar()

        for _ in range(3):
            asserter.assertAssemblySupported(passing)
            with self.assertRaises(AssertionError) as caught:
                asserter.assertAssemblySupported(failing)
            self.assertIn('torque', str(caught.exception))


class AnchoringTest(SupportFixture):
    """With `ground=None` the only anchored body is the virtual floor,
    so a default seed must stand on its own footprint. An explicit
    `ground` anchors the named solids instead, and no floor exists."""

    def test_tippy_default_seeded_solid_fails_on_the_virtual_floor(self):
        tippy, neighbour, root = self.tippy_pair()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)

        message = str(caught.exception)
        self.assertIn(tippy.name, message)
        self.assertNotIn(neighbour.name, message)

    def test_explicit_ground_anchors_the_named_solids_without_a_floor(self):
        tippy, neighbour, root = self.tippy_pair()

        asserter.assertAssemblySupported(root, ground=[tippy, neighbour])

    def test_an_anchored_ground_still_requires_the_rest_to_balance(self):
        support, bar, root = self.one_end_bar()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root, ground=support)

        self.assertIn(bar.name, str(caught.exception))

    def test_declared_support_transmits_an_unrestricted_wrench(self):
        """A press fit holds against force AND torque; the declared edge
        exempts exactly that hold while the supporter still balances."""
        post = self.block('post', (-1, 1), (-5, 1))
        fitted = self.block('fitted', (1, 3), (-1, 1))
        root = Assembly('root', (post, fitted))

        asserter.assertAssemblySupported(root, supports=[(fitted, post)])


class StabilityMarginTest(SupportFixture):
    """`stability_margin` shrinks every contact patch toward its own
    centroid, so a balance that lives on a patch boundary can be
    rejected on request."""

    def test_boundary_exact_balance_passes_at_the_default_margin(self):
        _, root = self.boundary_balance()

        asserter.assertAssemblySupported(root)

    def test_a_positive_margin_rejects_the_boundary_exact_balance(self):
        top, root = self.boundary_balance()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root, stability_margin=0.5)

        self.assertIn(top.name, str(caught.exception))

    def test_a_negative_margin_raises(self):
        _, root = self.boundary_balance()

        with self.assertRaises(ValueError) as caught:
            asserter.assertAssemblySupported(root, stability_margin=-0.1)

        self.assertIn('stability_margin', str(caught.exception))

    def test_a_negative_margin_is_loud_for_a_trivial_selection(self):
        leaf = RigidNode('leaf')

        with self.assertRaises(ValueError):
            asserter.assertAssemblySupported(leaf, stability_margin=-1.0)


class LiftSweepTest(SupportFixture):
    """The lift sweep contributes contacts only. Its verdicts never
    enter the support graph, and it is culled by the same broad phase
    the drop sweep uses."""

    def test_an_overhead_restraint_is_not_a_support_edge(self):
        hung, root = self.overhead_only()

        with self.assertRaises(AssertionError) as caught:
            asserter.assertAssemblySupported(root)

        message = str(caught.exception)
        self.assertIn(hung.name, message)
        self.assertIn('no support path', message)

    def test_both_sweeps_only_extract_bounds_overlapping_pairs(self):
        support = self.block('support', (0, 2), (0, 2))
        far_support = self.block('far_support', (8, 10), (0, 2))
        bar = self.block('bar', (0, 10), (2, 4))
        far = self.block('far', (1000, 1002), (0, 2))
        root = Assembly('root', (support, far_support, bar, far))

        with patch('solid_node.test._interface_contacts',
                   wraps=test_module._interface_contacts) as extract:
            asserter.assertAssemblySupported(root)

        pairs = {(call.args[1].name, call.args[2].name)
                 for call in extract.call_args_list}
        near = {'support', 'far_support', 'bar'}
        self.assertIn(('bar', 'support'), pairs)
        # The distant block meets the floor and nothing else, in either
        # sweep: no boolean is ever paid across the two clusters.
        self.assertFalse({pair for pair in pairs
                          if 'far' in pair and set(pair) & near})


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
