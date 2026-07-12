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

"""
The operations that can be applied to a solid are represented
here as classes that are able to handle scad and mesh, other than
serializing themselves for the web frontend. This way the same results
can be obtained in browser and in tests.
The operation is also able to revert itself.
"""

import math
import trimesh
from solid2 import (
    rotate as scad_rotate,
    translate as scad_translate,
)


def _as_number(node, value):
    """Converts value to a plain number. When a node is available its
    as_number is used, so solid2 animated expressions can be resolved;
    otherwise falls back to a plain float() conversion (used when an
    operation was rebuilt through unserialize(), which has no node)."""
    if node is None:
        return float(value)
    return node.as_number(value)


class Rotation:
    """A rotation operation defined by an angle and an axis"""

    def __init__(self, angle, axis, node=None):
        self.angle = angle
        self.axis = axis
        self.node = node

    @property
    def serialized(self):
        """Returns a serialized rotation as ["r", angle, axis]"""
        return ['r', str(self.angle), self.axis]

    @property
    def reversed(self):
        """Return an operation that reverses the rotation"""
        return Rotation(-self.angle, self.axis, self.node)

    def scad(self, scad_object):
        """Returns a scad object with a rotation applied"""
        return scad_rotate(self.angle, self.axis)(scad_object)

    def mesh(self, mesh):
        """Applies a rotation to a mesh"""
        matrix = trimesh.transformations.rotation_matrix(
            math.radians(_as_number(self.node, self.angle)),
            self.axis,
        )
        mesh.apply_transform(matrix)


class Translation:
    """A translation operation defined by a vector"""

    def __init__(self, translation, node=None):
        self.translation = translation
        self.node = node

    @property
    def serialized(self):
        """Returns a serialized translation as ["t", translation_vector]"""
        translation = [ str(x) for x in self.translation ]
        return ['t', translation]

    @property
    def reversed(self):
        """Returns an operation that reverts the translation"""
        return Translation(
            [ -x for x in self.translation ],
            self.node,
        )

    def scad(self, scad_object):
        """Returns a scad object with a translation applied"""
        return scad_translate(self.translation)(scad_object)

    def mesh(self, mesh):
        """Applies a translation to a mesh"""
        translation_n = [ _as_number(self.node, n) for n in self.translation ]
        mesh.apply_translation(translation_n)


_operations = {
    'r': Rotation,
    't': Translation,
}

def unserialize(serialized):
    """Unserializes a serialized operation"""
    Operation = _operations[serialized.pop(0)]
    return Operation(*serialized)
