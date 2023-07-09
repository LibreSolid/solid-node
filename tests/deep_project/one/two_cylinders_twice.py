from solid_node.node import AssemblyNode
from solid2 import cylinder, translate
from .two import TwoCylinders


class TwoCylindersTwice(AssemblyNode):

    def render(self):
        return [
            TwoCylinders(),
            TwoCylinders().rotate(180, [1, 0, 0]),
        ]
