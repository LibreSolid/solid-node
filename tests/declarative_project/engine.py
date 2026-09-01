# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A v8-shaped fixture: one root value moves eight repeated units and
the block they sit on."""

from solid2 import cube

from solid_node.node import AssemblyNode, Count, Length, Solid2Node
from .parts import Piston

STATION_PITCH = 44.0
BANK_HALF = 45.0
ROD_OFFSET = 5.2


class CylinderUnit(AssemblyNode):
    """A pure grouping node: nothing to position, no render()."""

    bore = Length(30.0, min=0)
    wall_clearance = Length(0.3, min=0)

    piston_diameter = bore - 2 * wall_clearance

    piston = Piston(diameter=piston_diameter)


class Cylinders(AssemblyNode):

    count = Count(8, min=2)
    bore = Length(30.0, min=0)

    units = CylinderUnit(bore=bore).repeat(count)

    def render(self):
        for index, unit in enumerate(self.units):
            pin = index // 2
            side = 1 if index % 2 == 0 else -1
            unit.rotate(side * BANK_HALF, [1, 0, 0])
            unit.translate([STATION_PITCH * pin - side * ROD_OFFSET, 0, 0])


class Block(Solid2Node):

    count = Count(8, min=2)
    bore = Length(30.0, min=0)
    pitch = Length(44.0, min=0)

    length = count * pitch / 2

    def render(self):
        return cube([self.length, self.bore * 2, self.bore], center=True)


class Engine(AssemblyNode):

    count = Count(8, min=2)
    bore = Length(30.0, min=0)

    cylinders = Cylinders(count=count, bore=bore)
    block = Block(count=count, bore=bore)
