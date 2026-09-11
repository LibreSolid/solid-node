"""A subclass that wants the same coordinate driven from a different
source: OpenTorque's preview subclass.

Run from the worktree with PYTHONPATH=.
"""
from solid2 import cube

from solid_node.motion.couplings import declared_relations
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort


class Rotor(Solid2Node):
    spin = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([2, 2, 2])


class Actuator(AssemblyNode):
    input_angle = RotationalPort(unit='deg')
    rotor = Rotor()
    drive = input_angle.drives(rotor.spin, ratio=8.0)

    def render(self):
        return [self.rotor]

    def simulate(self):
        self.input_angle = 5.0


class Preview(Actuator):
    """Wants `rotor.spin` driven from its own free-running source
    instead. Today the base's relation is still there."""

    free_run = RotationalPort(unit='deg')
    drive = free_run.drives(Actuator.rotor.spin, ratio=1.0)

    def simulate(self):
        super().simulate()
        self.free_run = 90.0


for klass in (Actuator, Preview):
    print(klass.__name__, 'declares',
          [relation.name or '<unnamed>'
           for relation in declared_relations(klass)])

node = Preview()
try:
    node.set_state(time=0.0)
except Exception as error:                            # noqa: BLE001
    print(f'{type(error).__name__}: {error}')
else:
    print('no refusal; rotor.spin =', node.rotor.spin.value)
