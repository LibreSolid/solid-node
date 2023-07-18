import numpy as np
import trimesh
from solid2 import (
    rotate as scad_rotate,
    translate as scad_translate,
)


class Rotation:
    def __init__(self, angle, axis):
        self.angle = angle
        self.axis = axis

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

    def serialized(self):
        return ['r', self.angle, self.axis]


class Translation:
    def __init__(self, node, translation):
        self.node = node
        self.translation = translation

    def reversed(self):
        return Translation(
            [ -x for x in self.translation ]
        )

    def scad(self, scad_object):
        return scad_translate(self.translation)(scad_object)

    def mesh(self, mesh):
        translation_n = [ self.node.as_number(n) for n in self.translation ]
        mesh.apply_translation(translation_n)

    def serialized(self):
        return ['t', self.translation]


_operations = {
    'r': Rotation,
    't': Translation,
}

def unserialize(serialized):
    Operation = serialized.pop(0)
    return Operation(*serialized)
