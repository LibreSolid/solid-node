# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Leaves for the coupling fixtures.

The train's arbor carries a wheel and a rod, wired from the arbor's own
coordinate, so a relation that solves the arbor has something below it
that must bind in the same run. The arm's pulley turns and the belt it
drives travels: the two ends of an affine relation whose ratio is a
pitch arc, which is the one place a rotational coordinate becomes a
translational one.
"""

from solid2 import cube, cylinder

from solid_node.motion.joints import Revolute
from solid_node.motion.ports import RotationalPort, TranslationalPort
from solid_node.node import Solid2Node
from solid_node.parameters import Length


class Wheel(Solid2Node):
    """The part whose angle arrives on a plain port."""

    turn = RotationalPort(unit='deg')

    def render(self):
        return cylinder(r=30, h=6)


class Rod(Solid2Node):
    """The part whose angle arrives on a joint, so the framework places
    the body about the rod's own line."""

    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube([4, 40, 4], center=True)


class Link(Solid2Node):
    """A bar: geometry enough to be a real leaf, nothing that moves on
    its own."""

    length = Length(160.0, min=0)

    def render(self):
        return cube([20, self.length, 20], center=True)


class Pulley(Solid2Node):
    """A pulley turning on its own axis: one joint, so a node end may
    stand for it."""

    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cylinder(r=20, h=8)


class Belt(Solid2Node):
    """A belt: what travels when the pulley turns."""

    travel = TranslationalPort(unit='mm')

    def render(self):
        return cube([4, 200, 6], center=True)
