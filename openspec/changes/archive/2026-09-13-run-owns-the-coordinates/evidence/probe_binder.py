"""Task 0.3: the two facts the run binder exists for, measured on the
tree BEFORE any change of this cycle.

(a) A coordinate bound OUTSIDE any enumeration is swept by
    `clear_solved` on the next phase, because it sits in the assembly's
    previous phase's bound list and its `_enum_marker` is not the
    current enumeration.
(b) `_step_relation` refuses `DoublyBound` when both ends of a relation
    hold values.

Run from the worktree with PYTHONPATH="$PWD".
"""

from solid2 import cube, cylinder

from solid_node.motion.joints import Revolute
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver


class Arbor(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cylinder(r=10, h=4)


class Body(AssemblyNode):
    crank = Driver(default=0.0, unit='deg')
    first = Arbor()

    crank.drives(first.turn, ratio=2.0)


class HandBound(Body):

    def simulate(self):
        self.first.turn = 99.0


def probe_a():
    root = Body()
    root.set_state(crank=10.0)
    slot = root.first.__dict__['_port_values']['turn']
    print('(a) after the rest render     first.turn =', slot._value,
          '  binder =', type(slot.binder).__name__,
          '  enum_marker set:', slot._enum_marker is not None)
    # Bind by hand OUTSIDE any enumeration, exactly as a run would.
    root.first.turn = 99.0
    print('(a) after the hand binding    first.turn =', slot._value,
          '  binder =', slot.binder,
          '  enum_marker:', slot._enum_marker)
    root.render()
    print('(a) after one more render()   first.turn =', slot._value,
          '  binder =', type(slot.binder).__name__)
    print('(a) VERDICT: the hand binding outside the enumeration was',
          'SWEPT and re-solved by the relation'
          if slot._value == 20.0 else 'KEPT')


def probe_b():
    root = HandBound()
    try:
        root.set_state(crank=10.0)
    except Exception as failure:
        print(f'(b) {type(failure).__name__}: {failure}')
    else:
        print('(b) VERDICT: nothing refused -- both ends bound was accepted')


probe_a()
print()
probe_b()
