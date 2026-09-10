"""Probe (run from the worktree with PYTHONPATH="$PWD"): ENDS IN A
DELIBERATE KeyError -- that traceback IS the finding, because
`declared_ports` reports no entry at all for a six-coordinate joint.

Throwaway probe: what today's tree does when a joint owns SIX
coordinates instead of one. Nothing here is proposed code."""
from solid_node.motion.joints import Joint, Revolute, declared_joints
from solid_node.motion.ports import (RotationalPort, TranslationalPort,
                                     declared_ports)
from solid_node.node.assembly import AssemblyNode
from solid_node.node import Solid2Node
from solid2 import cube


class FakeFree(Joint):
    """A stub with SIX coordinates and NO `.coordinate`, to see what the
    existing seams do with it."""
    coordinate_kind = RotationalPort
    default_unit = 'deg'

    def __init__(self, at=(0, 0, 0)):
        super().__init__(axis=(0, 0, 1), at=at)
        del self.coordinate
        self.coordinates = {}
        for name, kind in (('roll', RotationalPort), ('pitch', RotationalPort),
                           ('yaw', RotationalPort), ('x', TranslationalPort),
                           ('y', TranslationalPort), ('z', TranslationalPort)):
            self.coordinates[name] = kind(unit='deg')

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner
        for sub, port in self.coordinates.items():
            port.name = f'{name}.{sub}'
            port.owner = owner

    def __getattr__(self, attribute):
        try:
            return self.__dict__['coordinates'][attribute]
        except KeyError:
            raise AttributeError(attribute)


class Chassis(Solid2Node):
    pose = FakeFree()

    def render(self):
        return cube(2, center=True)


print('declared_joints:', list(declared_joints(Chassis)))
print('declared_ports :', list(declared_ports(Chassis)))

from solid_node.motion.couplings import read_through, PathRef, _coordinate_of
print('_coordinate_of(the joint):', _coordinate_of(Chassis.pose))
try:
    found = read_through(Chassis, 'pose', 'chassis.pose')
    print('read_through(pose) ->', found)
except Exception as failure:
    print('read_through(pose) RAISED', type(failure).__name__, failure)

# The sub-coordinate as a class-body read of the joint object.
print('Chassis.pose.roll ->', Chassis.pose.roll, Chassis.pose.roll.name)

# setattr with a dotted name
node = Chassis()
setattr(node, 'pose.roll', 12.0)
print("after setattr(node,'pose.roll',12): node.__dict__['pose.roll'] =",
      node.__dict__.get('pose.roll'),
      '| slot value =', declared_ports(Chassis)['pose.roll'].__get__(node).value)
