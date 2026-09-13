# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A FLEXIBLE part under a running root.

`tests/flexible_project`'s valve spring, driven from a JOINT COORDINATE
instead of from a driver: the shape parameter a flexible leaf publishes
is an expression like any other, so under a running root it names a bank
id and follows the committed bank exactly as a pose does.

Kept out of `machine.py` on purpose: importing it pulls molejo and
CadQuery in, and every other running fixture is answerable to neither.
"""

from solid_node.motion.joints import Prismatic
from solid_node.motion.ports import Time
from solid_node.node import AssemblyNode
from solid_node.simulation import Driver

from ..flexible_project.spring import FREE_HEIGHT, Spring


class LifterBody(AssemblyNode):
    """A pushrod on a prismatic joint, compressing the spring it
    carries."""

    travel = Prismatic(axis=(0, 0, 1), unit='mm')
    spring = Spring()

    def simulate(self):
        self.connect(FREE_HEIGHT - self.travel.value, self.spring.height)


class ValvegearBody(AssemblyNode):
    """The machine, with no time base of its own."""

    cam = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

    lifter = LifterBody()

    cam.drives(lifter.travel, ratio=1.0)


class Valvegear(ValvegearBody):
    """The same machine, running."""

    time = Time.running()
