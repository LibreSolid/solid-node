from solid_node.node import AssemblyNode
from solid2 import cylinder, translate
from .three import SimpleCylinder


class TwoCylinders(AssemblyNode):

    def render(self):
        return [
            SimpleCylinder(radius=10, height=5),
            SimpleCylinder(radius=5, height=10),
        ]
