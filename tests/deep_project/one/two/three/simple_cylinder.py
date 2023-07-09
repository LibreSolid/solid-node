from solid_node.node import Solid2Node
from solid2 import cylinder


class SimpleCylinder(Solid2Node):

    def __init__(self, radius=1, height=10):
        self.radius = radius
        self.height = height
        super().__init__(radius, height)

    def render(self):
        return cylinder(r=self.radius, h=self.height)
