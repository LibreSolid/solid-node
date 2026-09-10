"""A disk carried round the origin by an Orbit while an arm shows its
attitude, and a second disk turned by a Revolute for comparison."""
from solid2 import cube, cylinder

from solid_node.motion.joints import Orbit, Revolute
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.parameters import Angle

RADIUS = 25.0


class Disk(Solid2Node):
    """The arm points +x at rest: if the attitude moves, the eye sees it."""

    spin = Revolute(axis=(0, 0, 1), at=(RADIUS, 0.0, 0.0), unit='deg')
    orbit = Orbit(axis=(0, 0, 1), unit='deg')

    def render(self):
        return (cylinder(r=8, h=4)
                + cube([16, 3, 4], center=False).translate([0, -1.5, 0]))


class Turned(Solid2Node):
    """The same body on a Revolute about the same line: today's spelling."""

    orbit = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return (cylinder(r=8, h=4)
                + cube([16, 3, 4], center=False).translate([0, -1.5, 0]))


class Post(Solid2Node):
    def render(self):
        return cylinder(r=3, h=90)


class Machine(AssemblyNode):

    angle = Angle(0.0)
    spin_angle = Angle(0.0)

    post = Post()
    carried = Disk()
    turned = Turned()

    def render(self):
        self.carried.translate([RADIUS, 0.0, 0.0])
        self.turned.translate([RADIUS, 0.0, 40.0])
        self.post.translate([0.0, 0.0, -20.0])

    def simulate(self):
        self.carried.spin = self.spin_angle
        self.carried.orbit = self.angle
        self.turned.orbit = self.angle
