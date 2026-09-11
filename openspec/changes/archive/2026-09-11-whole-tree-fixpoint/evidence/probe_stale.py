"""An author-bound joint keeps its VALUE between runs while its motion
is swept: Prusa i3's 37.5 mm, hangprinter's masked winches.

Run from the worktree with PYTHONPATH=.
"""
from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Prismatic


class Carriage(Solid2Node):
    travel = Prismatic(axis=(1, 0, 0), unit='mm')

    def render(self):
        return cube([2, 2, 2])


class Printer(AssemblyNode):
    """The rest-default guard the catalogue writes."""

    carriage = Carriage()

    def render(self):
        return [self.carriage]

    def simulate(self):
        if self.carriage.travel.value is None:
            self.carriage.travel = 37.5


def state(printer, label):
    slot = printer.carriage.travel
    applied = [f'{type(o).__name__}{getattr(o, "translation", "")}'
               for o in printer.carriage.operations]
    print(f'{label:16} value={slot._value!r:8} binder={slot.binder!r:6} '
          f'operations={applied}')


printer = Printer()
printer.set_state(time=0.0)
state(printer, 'first run')
printer.set_state(time=0.5)
state(printer, 'second run')
printer.set_state(time=0.9)
state(printer, 'third run')
