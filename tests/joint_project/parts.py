# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Leaves for the joint fixtures: a link, and the two parts one arbor
carries -- a wheel taking its angle on a plain port, and a rod taking it
on a joint of its own."""

from solid2 import cube, cylinder

from solid_node.motion.joints import Prismatic, Revolute
from solid_node.motion.ports import RotationalPort
from solid_node.node import Solid2Node
from solid_node.parameters import Length


class Link(Solid2Node):
    """One bar of an arm: geometry enough to be a real leaf, and
    nothing that moves on its own."""

    length = Length(160.0, min=0)

    def render(self):
        return cube([20, self.length, 20], center=True)


class Wheel(Solid2Node):
    """The driven part whose angle arrives on a plain port: what the
    arbor hands it is a value, and the wheel does its own placing."""

    turn = RotationalPort(unit='deg')

    def render(self):
        return cylinder(r=30, h=6)


class Rod(Solid2Node):
    """The driven part whose angle arrives on a JOINT: the same wiring,
    but the framework places the body about the rod's own line."""

    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([4, 40, 4], center=True)


class Spool(Solid2Node):
    """A declarative child with a port: what a wiring reaches when the
    child also has parameters of its own."""

    diameter = Length(20.0, min=0)

    turn = RotationalPort(unit='deg')

    def render(self):
        return cylinder(r=self.diameter / 2, h=8)


class Carriage(Solid2Node):
    """A slide: one prismatic coordinate, ranged in millimetres."""

    travel = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')

    def render(self):
        return cube([40, 20, 10], center=True)
