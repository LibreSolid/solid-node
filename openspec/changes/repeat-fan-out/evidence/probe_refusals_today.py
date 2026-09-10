"""What the tree does TODAY with the four sentences cycle 1 wants."""
import cadquery as cq
from solid_node.node import AssemblyNode, CadQueryNode
from solid_node.motion.ports import SignalPort, declared_ports
from solid_node.motion.joints import Prismatic, Revolute


class Bead(CadQueryNode):
    travel = Prismatic(axis=(0, 0, 1), unit='mm')
    def render(self):
        return cq.Workplane('XY').box(1, 1, 1)


def show(label, fn):
    try:
        fn()
        print(f'{label}: NO ERROR')
    except Exception as e:
        print(f'{label}: {type(e).__name__}: {e}')
    print()


def broadcast_driven():
    class Column(AssemblyNode):
        earth = SignalPort()
        beads = Bead().repeat(4)
        earth.drives(beads.travel)
show('1. driven broadcast  earth.drives(beads.travel)', broadcast_driven)


def broadcast_node_end():
    class Column(AssemblyNode):
        earth = SignalPort()
        beads = Bead().repeat(4)
        earth.drives(beads)
show('2. node end          earth.drives(beads)', broadcast_node_end)


def broadcast_source():
    class Column(AssemblyNode):
        earth = SignalPort()
        beads = Bead().repeat(4)
        beads.travel.drives(earth)
show('3. source broadcast  beads.travel.drives(earth)', broadcast_source)


def through_child():
    class Column(AssemblyNode):
        beads = Bead().repeat(4)
    class Root(AssemblyNode):
        drive = SignalPort()
        column = Column()
        drive.drives(column.beads.travel)
show('4. path into repeat  drive.drives(column.beads.travel)', through_child)


def reader():
    from solid_node.motion.ports import get_coordinate
show('5. get_coordinate import', reader)


def copy_index():
    class Column(AssemblyNode):
        beads = Bead().repeat(4)
    c = Column()
    print('   index on copy:', [getattr(b, 'index', '<absent>') for b in c.beads])
    print('   count on copy:', [getattr(b, 'count', '<absent>') for b in c.beads])
show('6. copy index/count', copy_index)
