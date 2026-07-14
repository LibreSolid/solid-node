# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from trimesh.creation import box
from solid_node.node.operations import Rotation, Translation, unserialize


class FakeNode:
    """A minimal stand-in for AbstractBaseNode, only implementing the
    pieces Translation/Rotation.mesh() relies on."""

    def as_number(self, n):
        return float(n)


class FakeAnimatedAngle:
    """Stands in for a solid2 $t animated expression object: not a real
    number, but resolvable to one through a node's as_number()."""

    def __init__(self, value):
        self.value = value

    def __neg__(self):
        return FakeAnimatedAngle(-self.value)


class NodeResolvingAnimatedAngle(FakeNode):
    """A node whose as_number() knows how to resolve a FakeAnimatedAngle,
    like Solid2Node.as_number() resolves solid2 expressions via openscad."""

    def as_number(self, n):
        if isinstance(n, FakeAnimatedAngle):
            return n.value
        return super().as_number(n)


class TranslationReversedTest(TestCase):

    def test_reversed_keeps_node(self):
        node = FakeNode()
        translation = Translation(translation=[1, 2, 3], node=node)

        reversed_translation = translation.reversed

        self.assertIs(reversed_translation.node, node)
        self.assertEqual(reversed_translation.translation, [-1, -2, -3])


class UnserializeTest(TestCase):

    def test_unserialize_rotation(self):
        rotation = unserialize(['r', '90.0', [0, 0, 1]])

        self.assertIsInstance(rotation, Rotation)
        self.assertEqual(rotation.angle, '90.0')
        self.assertEqual(rotation.axis, [0, 0, 1])

    def test_unserialize_translation(self):
        translation = unserialize(['t', ['1.0', '2.0', '3.0']])

        self.assertIsInstance(translation, Translation)
        self.assertEqual(translation.translation, ['1.0', '2.0', '3.0'])
        self.assertIsNone(translation.node)

    def test_unserialize_translation_mesh_applies_without_node(self):
        # The serialized form never carries a node (it's dropped on the
        # wire), so a nodeless Translation must still be able to compute
        # a mesh transform, falling back to a plain float() conversion.
        translation = unserialize(['t', ['1.0', '2.0', '3.0']])
        mesh = box((1, 1, 1))

        translation.mesh(mesh)

        self.assertEqual(list(mesh.center_mass), [1.0, 2.0, 3.0])


class RotationReversedTest(TestCase):

    def test_reversed_keeps_node_and_negates_angle(self):
        node = FakeNode()
        rotation = Rotation(angle=90, axis=[0, 0, 1], node=node)

        reversed_rotation = rotation.reversed

        self.assertIs(reversed_rotation.node, node)
        self.assertEqual(reversed_rotation.angle, -90)
        self.assertEqual(reversed_rotation.axis, [0, 0, 1])


class RotationMeshTest(TestCase):

    def test_mesh_with_string_angle_and_no_node_falls_back_to_float(self):
        # A string angle (e.g. round-tripped through unserialize()) must
        # not be handed straight to math.radians().
        mesh = box((2, 4, 6))
        Rotation(angle="90", axis=[0, 0, 1]).mesh(mesh)

        expected = box((2, 4, 6))
        Rotation(angle=90, axis=[0, 0, 1]).mesh(expected)

        self.assertTrue((mesh.vertices == expected.vertices).all())

    def test_mesh_with_animated_angle_uses_node_as_number(self):
        # An animated angle (a solid2 $t expression, stood in for here by
        # FakeAnimatedAngle) is not a real number either; it must be
        # resolved through the node, just like Translation.mesh() does.
        node = NodeResolvingAnimatedAngle()
        mesh = box((2, 4, 6))
        Rotation(angle=FakeAnimatedAngle(90), axis=[0, 0, 1], node=node).mesh(mesh)

        expected = box((2, 4, 6))
        Rotation(angle=90, axis=[0, 0, 1]).mesh(expected)

        self.assertTrue((mesh.vertices == expected.vertices).all())
