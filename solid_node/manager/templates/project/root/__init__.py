from solid_node.node import Solid2Node
from solid2 import cube, cylinder, translate

class DemoProject(Solid2Node):

    def render(self):
        return translate(-25, -25, 0)(
            cube(50, 50, 50)
        ) - cylinder(r=10, h=100)
