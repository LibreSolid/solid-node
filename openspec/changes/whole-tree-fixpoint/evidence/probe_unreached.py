"""The two shapes the tree fixpoint is for, refused today, by name.

A: OpenFlexure's root -- an ancestor SOURCES from a coordinate a
   descendant's own relation solves.
B: wall clock 01 -- the chain is stated in `Train` while the root binds
   the far end of it, so the root's own relation has nothing to read.

Run from the worktree with PYTHONPATH=.
"""
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort


class Leaf(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([2, 2, 2])


##############################################
# A: an ancestor sources from a descendant-solved coordinate

class Axis(AssemblyNode):
    """openflexure's Axis: its own relation solves `travel` from the
    step count its own simulate() binds."""

    steps = RotationalPort(unit='deg')
    column = Leaf()
    steps.drives(column.turn, ratio=0.5)

    def render(self):
        return [self.column]

    def simulate(self):
        self.steps = 100.0


class Strut(Solid2Node):
    swing = Revolute(axis=(1, 0, 0), unit='deg')

    def render(self):
        return cube([2, 2, 2])


class RootA(AssemblyNode):
    z_axis = Axis()
    strut = Strut()
    z_axis.column.turn.drives(strut.swing, ratio=-0.25)

    def render(self):
        return [self.z_axis, self.strut]


##############################################
# B: the chain stated one level down, the known end bound at the root

class Train(AssemblyNode):
    centre = Leaf()
    third = Leaf()
    escape = Leaf()
    centre.turn.drives(third.turn, ratio=-6.0)
    third.turn.drives(escape.turn, ratio=-5.0)

    def render(self):
        return [self.centre, self.third, self.escape]


class Movement(AssemblyNode):
    power = Leaf()
    train = Train()
    power.turn.drives(train.centre.turn, ratio=-7.5)

    def render(self):
        return [self.power, self.train]

    def simulate(self):
        self.train.escape.turn = 30.0


for name, klass in (('A  ancestor sources from a descendant-solved '
                     'coordinate', RootA),
                    ('B  the chain stated one level down', Movement)):
    node = klass()
    try:
        node.set_state(time=0.0)
    except Exception as error:                       # noqa: BLE001
        print(f'{name}\n    {type(error).__name__}: {error}\n')
    else:
        print(f'{name}\n    no refusal; '
              f'{[getattr(c, "name", c) for c in node.children]}\n')
