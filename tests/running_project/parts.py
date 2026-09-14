# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Leaves for the running fixtures.

Three kinds of coordinate, so one machine exercises all of them: a
joint on a leaf (`Arbor`), a translational joint on a leaf (`Slide`),
and a PLAIN port on a leaf (`Wheel`), which the run never owns and the
ordinary enumeration recomputes from a run-bound source on every tick.
`Block` is geometry with nothing that moves, for an assembly that needs
a body to place.
"""

from solid2 import cube, cylinder

from solid_node.motion.joints import Prismatic, Revolute
from solid_node.motion.ports import RotationalPort
from solid_node.node import Solid2Node


class Arbor(Solid2Node):
    """A shaft turning about its own axis: one joint, on a LEAF."""

    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cylinder(r=10, h=4)


class Slide(Solid2Node):
    """A carriage travelling along one line."""

    travel = Prismatic(axis=(1, 0, 0), unit='mm')

    def render(self):
        return cube([20, 6, 6], center=True)


class Wheel(Solid2Node):
    """The part whose angle arrives on a PLAIN port: not a joint, so
    never in the run's bank."""

    turn = RotationalPort(unit='deg')

    def render(self):
        return cylinder(r=20, h=6)


class Block(Solid2Node):
    """Geometry and nothing that moves."""

    def render(self):
        return cube([10, 10, 10], center=True)
