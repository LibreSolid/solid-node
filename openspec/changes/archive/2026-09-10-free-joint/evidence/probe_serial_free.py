"""`probe_serial.py` again, with a REAL `Free` in place of the four
hand-written calls, and the two documents diffed.

The hand-written rig binds four values, two of them `0.0`, and never
touches the sideways freedoms, so the equivalent binds `pose.roll`,
`pose.pitch`, `pose.yaw` and `pose.z` and leaves `pose.x` and `pose.y`
unbound. What the free joint publishes has to be what the hand-written
form published: three ordinary rotations and one ordinary translation,
the two untouched components a plain `0`, no new key and no new
operation kind.

    PYTHONPATH=<worktree> python probe_serial_free.py
"""
import json

from solid2 import cube

from solid_node.core.serializer import serialize_node
from solid_node.motion.joints import Free
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver


class HandWrittenChassis(Solid2Node):
    def render(self):
        return cube(2, center=True)


class FreeChassis(Solid2Node):
    pose = Free(angle_unit='deg', length_unit='mm')

    def render(self):
        return cube(2, center=True)


class HandWritten(AssemblyNode):
    roll = Driver(default=0.0, unit='deg')
    pitch = Driver(default=0.0, unit='deg')
    yaw = Driver(default=0.0, unit='deg')
    height = Driver(default=0.0, unit='mm')

    chassis = HandWrittenChassis()

    def render(self):
        pass

    def simulate(self):
        (self.chassis
         .rotate(self.roll, [1, 0, 0])
         .rotate(self.pitch, [0, 1, 0])
         .rotate(self.yaw, [0, 0, 1])
         .translate([0, 0, self.height]))


class Jointed(AssemblyNode):
    roll = Driver(default=0.0, unit='deg')
    pitch = Driver(default=0.0, unit='deg')
    yaw = Driver(default=0.0, unit='deg')
    height = Driver(default=0.0, unit='mm')

    chassis = FreeChassis()

    def render(self):
        pass

    def simulate(self):
        self.chassis.pose.roll = self.roll
        self.chassis.pose.pitch = self.pitch
        self.chassis.pose.yaw = self.yaw
        self.chassis.pose.z = self.height


def shape(document):
    """The document without what is per-run: the mtime and the names."""
    document = dict(document)
    document.pop('mtime', None)
    document.pop('name', None)
    document['children'] = [shape(child)
                            for child in document.get('children', ())]
    return document


def keys(document, found=None):
    found = set() if found is None else found
    found.update(document)
    for child in document.get('children', ()):
        keys(child, found)
    return found


documents = {}
for label, rig in (('hand-written', HandWritten()), ('Free', Jointed())):
    rig.set_state(roll=5.0, pitch=0.0, yaw=0.0, height=120.0)
    documents[label] = shape(serialize_node(rig, lambda rigid: rigid.name))
    print(f'--- {label}')
    print(json.dumps(documents[label]['children'][0]['operations']))
    print('    document keys:', sorted(keys(documents[label])))

print()
print('identical:', documents['hand-written'] == documents['Free'])
