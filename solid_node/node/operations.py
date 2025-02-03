import numpy as np
import trimesh
from solid2 import (
    rotate as scad_rotate,
    translate as scad_translate,
)

"""
The operations that can be applied to a solid are represented
here as classes that are able to handle scad and mesh, other than
serializing itself for the web frontend. This way the same results
can be obtained in browser and in tests.
The operation is also able to revert itself.
"""

class Rotation:
    """A rotation operation defined by an angle and an axis"""
    def __init__(self, angle, axis):
        self.angle = angle
        self.axis = axis

    @property
    def serialized(self):
        return ['r', str(self.angle), self.axis]

    @property
    def reversed(self):
        return Rotation(-self.angle, self.axis)

    def scad(self, scad_object):
        return scad_rotate(self.angle, self.axis)(scad_object)

    def mesh(self, mesh):
        matrix = trimesh.transformations.rotation_matrix(
            np.radians(self.angle),
            self.axis,
        )
        mesh.apply_transform(matrix)


class Translation:
    """A translation operation defined by a vector"""
    def __init__(self, node, translation):
        self.node = node
        self.translation = translation

    @property
    def serialized(self):
        translation = [ str(x) for x in self.translation ]
        return ['t', translation]

    @property
    def reversed(self):
        return Translation(
            [ -x for x in self.translation ]
        )

    def scad(self, scad_object):
        return scad_translate(self.translation)(scad_object)

    def mesh(self, mesh):
        translation_n = [ self.node.as_number(n) for n in self.translation ]
        mesh.apply_translation(translation_n)


_operations = {
    'r': Rotation,
    't': Translation,
}

def unserialize(serialized):
    Operation = serialized.pop(0)
    return Operation(*serialized)
