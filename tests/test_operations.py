# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from unittest import TestCase
from trimesh.creation import box
from solid_node.node.operations import Rotation, Translation, unserialize


class FakeNode:
    """A minimal stand-in for AbstractBaseNode, only implementing the
    pieces Translation/Rotation.mesh() relies on."""

    def as_number(self, n):
        return float(n)


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
