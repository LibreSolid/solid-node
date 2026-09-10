"""What a class reads when it reads, inside its own `simulate()`, a
coordinate its OWN relations solve: Thor's two motor pulleys, and
openflexure's thread ratio pushed one level up.

Run from the worktree with PYTHONPATH=.
"""
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort


class Pulley(Solid2Node):
    def render(self):
        return cube([2, 2, 2])


class Rotor(Solid2Node):
    spin = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([2, 2, 2])


class Art4(AssemblyNode):
    """Thor: `left` is a derived coordinate of this class, and the
    class's own simulate() turns a pulley by it."""

    wrist = RotationalPort(unit='deg')
    tool = RotationalPort(unit='deg')
    left = wrist + 2 * tool
    pulley = Pulley()

    def render(self):
        return [self.pulley]

    def simulate(self):
        self.wrist = 10.0
        self.tool = 4.0
        read = self.left
        print(f'  own derived coordinate read in own simulate(): '
              f'{read!r} -> value {read.value!r}')
        self.pulley.rotate(read.value, [0, 0, 1])
        print(f'  the pulley\'s operations after rotate(): '
              f'{[type(o).__name__ for o in self.pulley.operations]}')


class Actuator(AssemblyNode):
    """openflexure: the thread ratio the class's own relation solves,
    read back inside the same class's simulate()."""

    steps = RotationalPort(unit='deg')
    rotor = Rotor()
    steps.drives(rotor.spin, ratio=0.5)

    def render(self):
        return [self.rotor]

    def simulate(self):
        self.steps = 100.0
        print(f'  own relation-bound joint coordinate read in own '
              f'simulate(): {self.rotor.spin.value!r}')


for klass in (Art4, Actuator):
    print(klass.__name__)
    node = klass()
    node.set_state(time=0.0)
    print()

art = Art4()
art.set_state(time=0.0)
print('after the run, the same derived coordinate reads',
      art.left.value)
