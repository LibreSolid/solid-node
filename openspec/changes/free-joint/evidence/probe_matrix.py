"""The hexapod's composition, three ways, at a set of poses:

1. the operations a Free would place (written by hand today, in the same
   order and the same frame), composed by the framework;
2. the same product built in NumPy;
3. the inverse of `Chassis._to_chassis`, transcribed from
   projects/Robots/hexapod_spiderbot_model/simulation/spiderbot.py:146-163.

The maximum absolute deviation between them is what the cycle's fixture
has to accept.
"""
import numpy as np
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.node.base import _compose_world_matrix
from solid_node.simulation import Driver


class Chassis(Solid2Node):
    def render(self):
        return cube(2, center=True)


class Rig(AssemblyNode):
    roll = Driver(default=0.0, unit='deg')
    pitch = Driver(default=0.0, unit='deg')
    yaw = Driver(default=0.0, unit='deg')
    height = Driver(default=0.0, unit='mm')

    chassis = Chassis()

    def render(self):
        pass

    def simulate(self):
        (self.chassis
         .rotate(self.roll, [1, 0, 0])
         .rotate(self.pitch, [0, 1, 0])
         .rotate(self.yaw, [0, 0, 1])
         .translate([0, 0, self.height]))


def rx(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])


def ry(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])


def rz(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def tr(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def to_chassis(point, roll, pitch, yaw, height):
    """`Chassis._to_chassis`, transcribed verbatim (degrees)."""
    from solid_node.math import cos, sin
    px, py, pz = point[0], point[1], point[2] - height
    cy, sy = cos(-yaw), sin(-yaw)
    px, py = px * cy - py * sy, px * sy + py * cy
    cp, sp = cos(-pitch), sin(-pitch)
    px, pz = px * cp + pz * sp, -px * sp + pz * cp
    cr, sr = cos(-roll), sin(-roll)
    py, pz = py * cr - pz * sr, py * sr + pz * cr
    return np.array([px, py, pz])


POSES = [(0, 0, 0, 0), (12, 8, 25, 165), (-15, -15, 0, 70),
         (5, -3, 180, 120), (90, 0, 45, 100), (0, 90, 30, 60),
         (-33.3, 21.7, -119.9, 143.25)]

worst_ops = 0.0
worst_inv = 0.0
probe = np.array([37.0, -91.5, 12.25, 1.0])
for roll, pitch, yaw, height in POSES:
    rig = Rig()
    rig.set_state(roll=roll, pitch=pitch, yaw=yaw, height=height)
    placed = _compose_world_matrix(rig.chassis)
    reference = tr([0, 0, height]) @ rz(yaw) @ ry(pitch) @ rx(roll)
    worst_ops = max(worst_ops, float(np.max(np.abs(placed - reference))))
    # `_to_chassis` must be the inverse of the same transform.
    world = reference @ probe
    back = to_chassis(world[:3], roll, pitch, yaw, height)
    worst_inv = max(worst_inv, float(np.max(np.abs(back - probe[:3]))))
    print(f'roll={roll:7} pitch={pitch:6} yaw={yaw:7} h={height:7}  '
          f'ops-vs-numpy={np.max(np.abs(placed - reference)):.3e}  '
          f'to_chassis-roundtrip={np.max(np.abs(back - probe[:3])):.3e}')

print()
print('max |framework composition - NumPy product| =', worst_ops)
print('max |_to_chassis(forward(p)) - p|          =', worst_inv)
