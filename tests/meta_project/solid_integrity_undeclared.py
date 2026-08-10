from solid_node.node import Solid2Node
from solid2 import cube, translate


class SolidIntegrityUndeclared(Solid2Node):

    def render(self):
        return cube(2) + translate(5, 0, 0)(cube(2))
