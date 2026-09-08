import cadquery as cq
from solid_node.node import AssemblyNode, CadQueryNode
from solid_node.parameters import Count, Length


class Part(CadQueryNode):
    size = Length(1.0)

    def render(self):
        return cq.Workplane('XY').box(self.size, 1, 1)


class Machine(AssemblyNode):
    count = Count(8, min=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parts = [Part(size=1 + i / 100) for i in range(self.count)]

    def render(self):
        for i, part in enumerate(self.parts):
            part.translate([3 * i, 0, 0])
        return self.parts
