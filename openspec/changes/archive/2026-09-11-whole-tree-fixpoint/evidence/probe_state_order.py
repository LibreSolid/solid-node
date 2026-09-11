"""When a node's driver snapshot arrives, relative to when its parent
renders.

`set_state` binds each node's entries just before rendering THAT node, so
at the moment the ROOT renders, no descendant has its snapshot yet. Any
design in which the root's render drives its descendants' simulate phases
has to move the snapshot ahead of the enumeration; this measures how far
behind it is today.

Run from the worktree with PYTHONPATH=.
"""
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver


class Body(Solid2Node):
    def render(self):
        return cube([2, 2, 2])


class Axis(AssemblyNode):
    step = Driver(default=0.0, unit='deg', range=(0.0, 100.0))
    body = Body()

    def render(self):
        return [self.body]

    def simulate(self):
        print(f'    Axis.simulate   reads step = {self.step}')


class Machine(AssemblyNode):
    axis = Axis()

    def render(self):
        return [self.axis]

    def simulate(self):
        print(f'    Machine.simulate: the axis holds {self.axis._states} '
              f'while this phase runs')


machine = Machine()
print('first set_state(step=10)')
machine.set_state(step=10.0, time=0.0)
print('second set_state(step=90)')
machine.set_state(step=90.0, time=0.0)
