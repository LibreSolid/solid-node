# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Leaves for the declarative fixtures, shaped like the evidence: a
piston with six declared lengths, its legacy twin with the same six
forwarded by hand, a tower whose height has no default, and a guard
that is a plain legacy class."""

from solid2 import cube, cylinder

from solid_node.node import Length, Solid2Node


class Piston(Solid2Node):

    diameter = Length(29.4, min=0)
    crown_height = Length(18.0, min=0)
    skirt_depth = Length(12.0, min=0)
    slot_width = Length(10.6, min=0)
    slot_top = Length(7.0)
    pin_bore = Length(6.6, min=0)

    total_height = crown_height + skirt_depth

    def render(self):
        return cylinder(r=self.diameter / 2, h=self.total_height)


class LegacyPiston(Solid2Node):
    """The same part in the constructor form, forwarding every kwarg."""

    def __init__(self, diameter=29.4, crown_height=18.0, skirt_depth=12.0,
                 slot_width=10.6, slot_top=7.0, pin_bore=6.6, name=None):
        self.diameter = diameter
        self.crown_height = crown_height
        self.skirt_depth = skirt_depth
        self.slot_width = slot_width
        self.slot_top = slot_top
        self.pin_bore = pin_bore
        super().__init__(
            diameter=diameter, crown_height=crown_height,
            skirt_depth=skirt_depth, slot_width=slot_width,
            slot_top=slot_top, pin_bore=pin_bore, name=name)

    def render(self):
        return cylinder(r=self.diameter / 2,
                        h=self.crown_height + self.skirt_depth)


class Tower(Solid2Node):
    """A height with no default: the parent says how tall."""

    height = Length(min=0)
    width = Length(40.0, min=0)

    def render(self):
        return cube([self.width, self.width, self.height])


class Rotor(Solid2Node):

    radius = Length(min=0)

    def render(self):
        return cylinder(r=self.radius, h=2.0)


class Guard(Solid2Node):
    """A legacy class, usable as a declared child of a declarative
    parent."""

    def __init__(self, thickness=1.6, name=None):
        self.thickness = thickness
        super().__init__(thickness=thickness, name=name)

    def render(self):
        return cube([10.0, 10.0, self.thickness])
