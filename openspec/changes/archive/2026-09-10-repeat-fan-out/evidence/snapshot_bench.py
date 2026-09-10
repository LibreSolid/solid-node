# Evidence bench for repeat-fan-out (task 9.2): four bodies placed by
# ONE broadcast relation with a per-copy law, at three poses. Placement
# (the row) is the parent's own render() loop over the realized copies;
# lift is the broadcast -- exactly the split declaring.rst states between
# "placement variation is enumerate plus constants" and "drive variation
# is a broadcast relation with a per-copy law".

from solid2 import cube

from solid_node.node import AssemblyNode, Solid2Node
from solid_node.motion.joints import Prismatic
from solid_node.motion.ports import SignalPort


class Bead(Solid2Node):
    """One joint, no `index` of its own."""

    travel = Prismatic(axis=(0, 0, 1), unit='mm')

    def render(self):
        return cube([8, 8, 8], center=True)


def stagger(column, bead):
    """Each copy lifts by the shared level PLUS its own rank -- the
    per-copy law that turns one broadcast into a visible staircase."""
    rank = bead.index
    return lambda level: level + rank * 3.0


class Column(AssemblyNode):
    """Four beads in a row (the parent's own placement loop), lifted by
    ONE relation broadcast over the repeat with a per-copy law."""

    earth = SignalPort()
    beads = Bead().repeat(4)

    earth.drives(beads.travel, law=stagger)

    def simulate(self):
        self.earth = self.time * 10.0

    def render(self):
        for index, bead in enumerate(self.beads):
            bead.translate([index * 12.0, 0, 0])
        return list(self.beads)
