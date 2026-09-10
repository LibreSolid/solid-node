"""Does an identity wiring over .repeat() already work today?"""
from solid_node.node import AssemblyNode, CadQueryNode
from solid_node.motion.ports import SignalPort, declared_ports
from solid_node.motion.joints import Prismatic
import cadquery as cq


class Bead(CadQueryNode):
    travel = Prismatic(axis=(0, 0, 1), unit='mm')

    def render(self):
        return cq.Workplane('XY').box(1, 1, 1)


class Column(AssemblyNode):
    earth = SignalPort()
    beads = Bead(travel=earth).repeat(4)

    def simulate(self):
        self.earth = 3.0


c = Column()
c.assemble()
print('beads:', [b.name for b in c.beads])
print('travels:', [b.travel.value for b in c.beads])
print('uniq:', {b.uniq_id for b in c.beads})
print('ops:', [len(b.operations) for b in c.beads])
