# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the connectivity assertions and the declared body
count -- the contract that a rigid printed part is ONE connected
solid.

The gap these close: watertightness is a per-shell property, so a mesh
made of N disjoint closed shells is watertight, has a positive volume,
exports to a valid STL, and renders in the viewer looking like one
part. Nothing in the framework distinguished it from a real single
body, so a part that fell apart into floating fragments -- a fan whose
blades never reached its hub, a lever plate whose label bars never
touched it -- built green and shipped.

Like tests/test_assertions.py these use tiny stand-ins with a real
.mesh, rather than driving a full STL build.
"""

from unittest import TestCase
import numpy as np
from trimesh.creation import box
from trimesh.util import concatenate

from solid_node.test import TestCase as AssertingTestCase


asserter = AssertingTestCase()


class FakeNode:
    """Minimal stand-in for a rigid node: a name and a .mesh, which is
    all the connectivity assertions read."""

    def __init__(self, mesh, name='Node', bodies=None):
        self.name = name
        self._mesh = mesh
        self.bodies = bodies
        self.children = tuple()
        self.rigid = True

    @property
    def mesh(self):
        return self._mesh.copy()


class FakeAssembly:
    """Stand-in for an internal node: children, and no mesh of its own."""

    def __init__(self, children, name='Assembly'):
        self.name = name
        self.children = children
        self.rigid = False


def one_body(size=2.0):
    return box((size,) * 3)


def two_bodies(gap=5.0):
    """Two boxes with clear air between them -- one mesh, two connected
    components, and watertight all the same."""
    first = box((2.0, 2.0, 2.0))
    second = box((2.0, 2.0, 2.0))
    second.apply_translation([gap, 0.0, 0.0])
    return concatenate([first, second])


def welded_pair(overlap=0.5):
    """Two boxes sharing `overlap` mm of volume: a real weld."""
    first = box((2.0, 2.0, 2.0))
    second = box((2.0, 2.0, 2.0))
    second.apply_translation([2.0 - overlap, 0.0, 0.0])
    return first, second


def touching_pair():
    """Two boxes whose faces meet exactly, sharing no volume."""
    first = box((2.0, 2.0, 2.0))
    second = box((2.0, 2.0, 2.0))
    second.apply_translation([2.0, 0.0, 0.0])
    return first, second


class DisjointShellsAreWatertightTest(TestCase):
    """The premise: this is why the framework could not see the bug."""

    def test_two_disjoint_shells_are_watertight_and_positive_volume(self):
        mesh = two_bodies()
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_volume)
        self.assertAlmostEqual(mesh.volume, 16.0, places=6)


class AssertOneBodyTest(TestCase):

    def test_single_body_passes(self):
        asserter.assertOneBody(FakeNode(one_body(), name='Shaft'))

    def test_disconnected_part_fails(self):
        node = FakeNode(two_bodies(), name='FanSails')
        with self.assertRaises(AssertionError) as caught:
            asserter.assertOneBody(node)
        message = str(caught.exception)
        self.assertIn('FanSails', message)
        self.assertIn('2', message)

    def test_tangential_contact_is_not_a_join(self):
        """Faces that meet exactly do not weld: the union of two boxes
        touching on a plane is still two components. This is precisely
        what `union()` on non-overlapping solids produces."""
        first, second = touching_pair()
        node = FakeNode(concatenate([first, second]), name='ForkCarriage')
        with self.assertRaises(AssertionError):
            asserter.assertOneBody(node)


class AssertBodyCountTest(TestCase):

    def test_expected_count_passes(self):
        asserter.assertBodyCount(FakeNode(two_bodies(), name='Pair'), 2)

    def test_wrong_count_fails_naming_both_numbers(self):
        node = FakeNode(two_bodies(), name='SelectorGate')
        with self.assertRaises(AssertionError) as caught:
            asserter.assertBodyCount(node, 1)
        message = str(caught.exception)
        self.assertIn('SelectorGate', message)
        self.assertIn('1', message)
        self.assertIn('2', message)


class AssertJoinedTest(TestCase):

    def test_overlapping_features_are_joined(self):
        first, second = welded_pair(overlap=0.5)
        asserter.assertJoined(FakeNode(first, name='Hub'),
                              FakeNode(second, name='Blade'))

    def test_separated_features_fail(self):
        first = box((2.0, 2.0, 2.0))
        second = box((2.0, 2.0, 2.0))
        second.apply_translation([5.0, 0.0, 0.0])
        with self.assertRaises(AssertionError) as caught:
            asserter.assertJoined(FakeNode(first, name='FanHub'),
                                  FakeNode(second, name='FanSails'))
        message = str(caught.exception)
        self.assertIn('FanHub', message)
        self.assertIn('FanSails', message)

    def test_weld_below_the_stated_minimum_fails(self):
        """A 0.05mm lick of overlap is not a joint you can print."""
        first, second = welded_pair(overlap=0.05)
        with self.assertRaises(AssertionError) as caught:
            asserter.assertJoined(FakeNode(first, name='Neck'),
                                  FakeNode(second, name='Carriage'),
                                  min_weld_volume=1.0)
        self.assertIn('weld', str(caught.exception).lower())

    def test_weld_above_the_stated_minimum_passes(self):
        first, second = welded_pair(overlap=0.5)
        asserter.assertJoined(FakeNode(first, name='Neck'),
                              FakeNode(second, name='Carriage'),
                              min_weld_volume=1.0)


class AssertNoDisconnectedPartsTest(TestCase):
    """The tree-walking safety net, sibling of
    assertNoPairwiseIntersections."""

    def test_all_single_body_leaves_pass(self):
        root = FakeAssembly([
            FakeNode(one_body(), name='a'),
            FakeAssembly([FakeNode(one_body(), name='b')], name='sub'),
        ])
        asserter.assertNoDisconnectedParts(root)

    def test_one_fragmented_leaf_anywhere_fails(self):
        root = FakeAssembly([
            FakeNode(one_body(), name='plinth'),
            FakeAssembly([
                FakeNode(one_body(), name='hub'),
                FakeNode(two_bodies(), name='sails'),
            ], name='fan_rotor'),
        ])
        with self.assertRaises(AssertionError) as caught:
            asserter.assertNoDisconnectedParts(root)
        self.assertIn('sails', str(caught.exception))

    def test_a_leaf_may_declare_a_legitimate_body_count(self):
        """A part that is deliberately several bodies (a printed sprue
        of small items) declares it and is held to that number."""
        root = FakeAssembly([
            FakeNode(two_bodies(), name='sprue', bodies=2),
        ])
        asserter.assertNoDisconnectedParts(root)

    def test_a_declared_count_is_still_enforced(self):
        root = FakeAssembly([
            FakeNode(two_bodies(), name='sprue', bodies=3),
        ])
        with self.assertRaises(AssertionError):
            asserter.assertNoDisconnectedParts(root)


class DeclaredBodyCountTest(TestCase):
    """Build-time enforcement: a node may declare how many connected
    bodies its own STL must have, and the build refuses to publish a
    model that violates it."""

    def test_base_node_declares_no_body_count_by_default(self):
        """Default is unchecked, so no existing project pays the cost
        of loading its meshes at build time."""
        from solid_node.node.base import AbstractBaseNode
        self.assertIsNone(AbstractBaseNode.bodies)

    def test_fusion_node_declares_one_body(self):
        """'A fusion of components into a single, inseparable unit' was
        a docstring promise with nothing behind it."""
        from solid_node.node import FusionNode
        self.assertEqual(FusionNode.bodies, 1)

    def test_verify_bodies_passes_a_single_body(self):
        from solid_node.node.base import AbstractBaseNode
        node = FakeNode(one_body(), name='Fusion', bodies=1)
        AbstractBaseNode.verify_bodies(node)

    def test_verify_bodies_rejects_a_fragmented_result(self):
        from solid_node.node.base import AbstractBaseNode, DisconnectedBodyError
        node = FakeNode(two_bodies(), name='Fusion', bodies=1)
        with self.assertRaises(DisconnectedBodyError) as caught:
            AbstractBaseNode.verify_bodies(node)
        self.assertIn('Fusion', str(caught.exception))

    def test_verify_bodies_skips_an_undeclared_node(self):
        from solid_node.node.base import AbstractBaseNode
        node = FakeNode(two_bodies(), name='Whatever', bodies=None)
        AbstractBaseNode.verify_bodies(node)

    def test_verify_bodies_skips_a_non_rigid_node(self):
        from solid_node.node.base import AbstractBaseNode
        node = FakeNode(two_bodies(), name='Assembly', bodies=1)
        node.rigid = False
        AbstractBaseNode.verify_bodies(node)
