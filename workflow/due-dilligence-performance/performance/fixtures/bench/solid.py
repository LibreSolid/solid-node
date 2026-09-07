from solid2 import cube
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.parameters import Count, Flag, Length
from solid_node.simulation import Driver


class Part(Solid2Node):
    size = Length(1.0)

    def render(self):
        return cube([self.size, 1, 1])


class Machine(AssemblyNode):
    count = Count(8, min=1)
    distinct = Flag(True)
    explicit = Flag(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parts = [Part(size=1 + i / 100 if self.distinct else 1,
                           name=f'parts-{i}' if self.explicit else None)
                      for i in range(self.count)]

    def render(self):
        for i, part in enumerate(self.parts):
            part.translate([3 * i, 0, 0])
        return self.parts


class Driven(Machine):
    position = Driver(default=0, unit='mm')

    def simulate(self):
        self.parts[0].translate([self.position, 0, 0])
