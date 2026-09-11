"""What a coordinate VALUE can be, and what happens today when a law
returns several of them.

The first question decides how a multi-target law's return is checked:
if a symbolic value were a string or a sequence, `len(returned)` could
not tell "four values" from "one value that happens to be sized".

The second is what the silence looks like today.
"""
from solid2.core.object_base import OpenSCADConstant

from solid2 import cube

from solid_node.motion.couplings import ForwardOnly
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import SignalPort
from solid_node.node import AssemblyNode, Solid2Node

symbolic = OpenSCADConstant('$t')
for name, value in (('float', 1.5), ('int', 2), ('symbolic', symbolic)):
    print(f'{name}: len? {hasattr(value, "__len__")}  '
          f'iter? {hasattr(value, "__iter__")}  '
          f'getitem? {hasattr(value, "__getitem__")}  type={type(value).__name__}')


class Leaf(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([2, 2, 2])


class Root(AssemblyNode):
    a = SignalPort()
    child = Leaf()
    # A law that returns FOUR values for one driven end: what a project
    # would write today if nothing checked it.
    a.drives(child.turn, law=lambda *nodes: ForwardOnly(
        lambda x: (x, 2 * x, 3 * x, 4 * x)))

    def render(self):
        return [self.child]

    def simulate(self):
        self.a = 1.0


node = Root()
node.set_state(time=0.0)
print('the slot after one run:', node.child.turn._value)
print('the operations it produced:',
      [f'{type(o).__name__}{getattr(o, "angle", "")}'
       for o in node.child.operations])
