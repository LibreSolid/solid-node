from solid_node.node import AssemblyNode
from solid2 import cylinder, translate
from simple_pipe import SimplePipe


class TwoPipes(AssemblyNode):

    def render(self):
        return [
            SimplePipe(),
            SimplePipe().translate(100, 0, 0),
        ]
