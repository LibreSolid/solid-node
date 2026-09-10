"""A body placed by a `Free` above a ground plane, with a mast and an
arm so the eye can read its attitude.

    solid snapshot floating.py:Machine --set roll=... --set pitch=...
                   --set yaw=... --set height=... --viewall
"""
from solid2 import cube, cylinder

from solid_node.motion.joints import Free
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.parameters import Angle, Length


class Chassis(Solid2Node):
    """The floating body: a slab, a mast up +z and an arm out +x, so
    roll, pitch and yaw are all legible from one view."""

    pose = Free(angle_unit='deg', length_unit='mm')

    def render(self):
        return (cube([60, 30, 6], center=True)
                + cylinder(r=3, h=40).translate([0, 0, 3])
                + cube([50, 4, 4], center=False).translate([0, -2, 0]))


class Ground(Solid2Node):
    def render(self):
        return cube([160, 160, 2], center=True)


class Machine(AssemblyNode):

    roll = Angle(0.0)
    pitch = Angle(0.0)
    yaw = Angle(0.0)
    height = Length(0.0)

    ground = Ground()
    chassis = Chassis()

    def render(self):
        self.ground.translate([0.0, 0.0, -20.0])

    def simulate(self):
        self.chassis.pose.roll = self.roll
        self.chassis.pose.pitch = self.pitch
        self.chassis.pose.yaw = self.yaw
        self.chassis.pose.z = self.height
