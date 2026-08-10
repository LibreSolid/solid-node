from solid_node.node import Solid2Node
from solid2 import cube


class SolidIntegrityGreen(Solid2Node):

    def render(self):
        return cube(2)
