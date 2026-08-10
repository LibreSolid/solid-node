# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for solid integrity and solid-local connectivity.

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

import inspect
import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock
import trimesh
from trimesh.creation import box
from trimesh.util import concatenate

from solid_node.test import TestCase as AssertingTestCase
from solid_node.node import AssemblyNode, FusionNode
from solid_node.node.base import AbstractBaseNode, _topmost_rigid_nodes
from solid_node.node.internal import InternalNode
from solid_node.node.operations import Translation


asserter = AssertingTestCase()


class FakeNode:
    """Minimal stand-in for a rigid node: a name and a .mesh, which is
    all the connectivity assertions read."""

    def __init__(self, mesh, name='Node'):
        self.name = name
        self._mesh = mesh
        self.children = tuple()
        self.rigid = True

    @property
    def mesh(self):
        return self._mesh.copy()


class StlNode:
    """Small real-STL node for exercising matrix composition paths."""

    def __init__(self, stl_file, name, parent=None):
        self.stl_file = stl_file
        self.name = name
        self._parent = parent
        self.operations = []
        self.rigid = True

    def as_number(self, value):
        return float(value)

    @property
    def mesh(self):
        return AbstractBaseNode.mesh.fget(self)


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


class DisjointShellsAreWatertightTest(TestCase):
    """The premise: this is why the framework could not see the bug."""

    def test_two_disjoint_shells_are_watertight_and_positive_volume(self):
        mesh = two_bodies()
        self.assertTrue(mesh.is_watertight)
        self.assertTrue(mesh.is_volume)
        self.assertAlmostEqual(mesh.volume, 16.0, places=6)


class TopmostRigidNodesTest(TestCase):

    def test_walk_stops_at_outer_solid_and_rigid_root_selects_itself(self):
        leaf = SimpleNamespace(rigid=True, children=(), name='leaf')
        nested = SimpleNamespace(rigid=True, children=(leaf,), name='nested')
        outer = SimpleNamespace(rigid=True, children=(nested,), name='outer')
        assembly = SimpleNamespace(rigid=False, children=(outer,),
                                   name='assembly')

        self.assertEqual(list(_topmost_rigid_nodes(assembly)), [outer])
        self.assertEqual(list(_topmost_rigid_nodes(outer)), [outer])


class AssertNoDisconnectedSolidsTest(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def stl_node(self, name, mesh, *, rigid=True, children=(), parent=None):
        path = os.path.join(self.directory.name, f'{name}.stl')
        mesh.export(path)
        return SimpleNamespace(name=name, stl_file=path, rigid=rigid,
                               children=children, _parent=parent,
                               operations=[])

    def test_names_disconnected_solid_and_body_count(self):
        broken = self.stl_node('broken-gear', two_bodies())

        with self.assertRaises(AssertionError) as caught:
            asserter.assertNoDisconnectedSolids(broken)

        self.assertIn('broken-gear', str(caught.exception))
        self.assertIn('2', str(caught.exception))

    def test_passes_each_selected_single_body_solid(self):
        left = self.stl_node('left', one_body())
        right = self.stl_node('right', one_body())
        assembly = SimpleNamespace(name='assembly', rigid=False,
                                   children=(left, right))

        asserter.assertNoDisconnectedSolids(assembly)

    def test_stops_at_enclosing_fusion(self):
        ingredient = self.stl_node('fragmented-ingredient', two_bodies())
        fusion = self.stl_node('joined-fusion', one_body(),
                               children=(ingredient,))

        asserter.assertNoDisconnectedSolids(fusion)

    def test_checks_only_the_passed_subtree(self):
        good = self.stl_node('selected', one_body())
        broken = self.stl_node('outside', two_bodies())
        SimpleNamespace(name='assembly', rigid=False, children=(good, broken))

        asserter.assertNoDisconnectedSolids(good)

    def test_does_not_compose_animated_placement(self):
        animated = Mock()
        animated.matrix.side_effect = TypeError('(360 * $t) is not a number')
        solid = self.stl_node('animated-solid', one_body())
        solid.operations.append(animated)
        assembly = SimpleNamespace(name='assembly', rigid=False,
                                   children=(solid,), operations=[])
        solid._parent = assembly

        asserter.assertNoDisconnectedSolids(assembly)

        animated.matrix.assert_not_called()


class FusionHierarchyTest(TestCase):

    def test_fusion_rejects_non_rigid_child_naming_both_nodes(self):
        fusion = object.__new__(FusionNode)
        fusion.name = 'OuterSolid'
        assembly = object.__new__(AssemblyNode)
        assembly.name = 'MovingParts'

        with self.assertRaises(Exception) as caught:
            fusion.validate([assembly])

        message = str(caught.exception)
        self.assertIn('OuterSolid', message)
        self.assertIn('MovingParts', message)

    def test_the_rule_belongs_to_fusion_not_to_the_base_class(self):
        """InternalNode must not know its own subclasses: the fusion
        rule lives on FusionNode, and a plain InternalNode subclass
        that is not a fusion imposes no rigidity requirement."""
        self.assertIn('validate', FusionNode.__dict__)

        source = inspect.getsource(InternalNode.validate)
        self.assertNotIn('FusionNode', source)

        class OuterAssembly(AssemblyNode):
            pass

        outer = object.__new__(OuterAssembly)
        outer.name = 'Outer'
        inner = object.__new__(AssemblyNode)
        inner.name = 'Inner'
        self.assertFalse(inner.rigid)

        InternalNode.validate(outer, [inner])

    def test_as_scad_does_not_shadow_type_determined_rigidity(self):
        fusion = object.__new__(FusionNode)
        fusion.root = None
        fusion.files = set()
        fusion._link_child = Mock()
        child = SimpleNamespace(
            rigid=True,
            files=set(),
            assemble=Mock(return_value=object()),
        )

        InternalNode.as_scad(fusion, [child])

        self.assertNotIn('rigid', fusion.__dict__)


class RemovedConnectivityApiTest(TestCase):

    def test_declared_body_api_is_absent(self):
        import solid_node.node.base as base

        self.assertFalse(hasattr(base.AbstractBaseNode, 'bodies'))
        self.assertFalse(hasattr(base.AbstractBaseNode, 'verify_bodies'))
        self.assertFalse(hasattr(base, 'DisconnectedBodyError'))
        self.assertNotIn('bodies', FusionNode.__dict__)

    def test_redundant_test_assertions_are_absent(self):
        self.assertFalse(hasattr(asserter, 'assertOneBody'))
        self.assertFalse(hasattr(asserter, 'assertBodyCount'))
        self.assertFalse(hasattr(asserter, 'assertNoDisconnectedParts'))


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

    def test_animated_enclosing_solid_is_not_composed(self):
        with tempfile.TemporaryDirectory() as directory:
            stl_file = os.path.join(directory, 'feature.stl')
            one_body().export(stl_file)
            assembly = SimpleNamespace(rigid=False, _parent=None, operations=[])
            solid = SimpleNamespace(rigid=True, _parent=assembly, operations=[])
            animated_placement = Mock()
            animated_placement.matrix.side_effect = TypeError(
                '(360 * $t) is not a number')
            solid.operations.append(animated_placement)
            first = StlNode(stl_file, 'Hub', parent=solid)
            second = StlNode(stl_file, 'Blade', parent=solid)
            second.operations.append(Translation([1, 0, 0], second))

            asserter.assertJoined(first, second)
            asserter.assertJoined(first, second)

            animated_placement.matrix.assert_not_called()

    def test_features_of_different_solids_are_refused(self):
        """The dangerous direction of solid-local framing: each node
        placed in its OWN solid's frame lands at that part's origin, so
        the distance the assembly holds between the parts vanishes and
        two features that share nothing would read as welded."""
        with tempfile.TemporaryDirectory() as directory:
            stl_file = os.path.join(directory, 'feature.stl')
            one_body().export(stl_file)
            assembly = SimpleNamespace(rigid=False, _parent=None,
                                       operations=[], name='Rig')
            left = StlNode(stl_file, 'LeftBracket', parent=assembly)
            right = StlNode(stl_file, 'RightBracket', parent=assembly)
            right.operations.append(Translation([1000, 0, 0], right))

            with self.assertRaises(AssertionError) as caught:
                asserter.assertJoined(left, right)

        message = str(caught.exception)
        self.assertIn('different solids', message)
        self.assertIn('LeftBracket', message)
        self.assertIn('RightBracket', message)

    def test_unassembled_doubles_are_still_comparable(self):
        """A node with no parent is not linked into a tree, so it is
        not evidence of a second part: the guard stays out of the way
        of plain mesh geometry."""
        first, second = welded_pair()

        asserter.assertJoined(FakeNode(first, name='Hub'),
                              FakeNode(second, name='Boss'))

    def test_pair_joined_only_through_third_feature_still_fails(self):
        first = box((2, 2, 2))
        second = box((2, 2, 2))
        second.apply_translation([4, 0, 0])
        bridge = box((4, 2, 2))
        bridge.apply_translation([2, 0, 0])
        whole = trimesh.boolean.union([first, bridge, second])
        self.assertEqual(len(whole.split(only_watertight=False)), 1)

        with self.assertRaises(AssertionError):
            asserter.assertJoined(FakeNode(first, name='A'),
                                  FakeNode(second, name='B'))
