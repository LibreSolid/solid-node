from solid_node.node import AssemblyNode
from solid2 import cylinder, translate
from . import TwoCylindersTwice


class ThirdLevel(AssemblyNode):

    def render(self):
        return [
            TwoCylindersTwice(),
            TwoCylindersTwice().rotate(180, [0, 1, 0]),
        ]
