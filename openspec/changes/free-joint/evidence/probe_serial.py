"""What the six operations a Free would place look like in the document,
written by hand today: three rotations and one translation, two of the
six coordinates left unbound (a plain numeric 0)."""
import json

from solid2 import cube

from solid_node.core.serializer import serialize_node
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver


class Chassis(Solid2Node):
    def render(self):
        return cube(2, center=True)


class Rig(AssemblyNode):
    roll = Driver(default=0.0, unit='deg')
    pitch = Driver(default=0.0, unit='deg')
    yaw = Driver(default=0.0, unit='deg')
    height = Driver(default=0.0, unit='mm')

    chassis = Chassis()

    def render(self):
        pass

    def simulate(self):
        (self.chassis
         .rotate(self.roll, [1, 0, 0])
         .rotate(self.pitch, [0, 1, 0])
         .rotate(self.yaw, [0, 0, 1])
         .translate([0, 0, self.height]))


rig = Rig()
rig.set_state(roll=5.0, pitch=0.0, yaw=0.0, height=120.0)
document = serialize_node(rig, lambda rigid: rigid.name)
print(json.dumps(document, indent=1)[:2000])
