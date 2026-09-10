"""design.md section 6's probe, re-run against the real Orbit."""
import numpy as np
from solid2 import cube

from solid_node.motion.joints import Orbit
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.node.base import _compose_world_matrix


class Body(Solid2Node):
    orbit = Orbit(axis=(0, 0, 1), unit='deg')
    def render(self):
        return cube(2, center=True)


class Bench(AssemblyNode):
    body = Body()
    def render(self):
        self.body.translate([10, 0, 0])
    def simulate(self):
        self.body.orbit = self.time * 360


bench = Bench()
bench.render()
print('SYMBOLIC serialized:', bench.body.operations[0].serialized)
bench.set_keyframe(0.25)
print('KEYFRAME 0.25 serialized:', bench.body.operations[0].serialized)
bench.clear_keyframe()
print('CLEARED  serialized:', bench.body.operations[0].serialized)

rest = np.eye(4); rest[:3, 3] = [10, 0, 0]
print()
for angle in (0, 17, 90, 213.5):
    body = Body()
    body.translate([10, 0, 0])
    body.orbit = angle
    got = _compose_world_matrix(body)
    turn = np.eye(4)
    a = np.radians(angle)
    turn[:2, :2] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]
    want = turn @ np.array([10.0, 0.0, 0.0, 1.0])
    print(f'theta={angle:>6}  max|R - I| = '
          f'{np.max(np.abs(got[:3, :3] - np.eye(3))):.1e}   '
          f'carried point {np.round(got[:3, 3], 12)} vs R(theta).p '
          f'{np.round(want[:3], 12)}  (delta '
          f'{np.max(np.abs(got[:3, 3] - want[:3])):.3e} mm)')
