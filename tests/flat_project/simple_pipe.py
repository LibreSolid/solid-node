from solid_node.node import Solid2Node
from solid2 import cylinder


class SimplePipe(Solid2Node):

    def render(self):
        return cylinder(r=10, h=100) - cylinder(r=8, h=100)
