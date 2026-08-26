# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Two instances of ONE driver-declaring class, under one parent.

The whole point of instance qualification is a class-local driver name
that collides for real. `Axis` declares `motor`; `Machine` holds two of
them as `x_axis` and `y_axis` and declares nothing itself, so every
driver in this machine lives on a duplicated descendant -- the shape
the expression spike modelled (spike/expressions/machine_model.py) and
the shape ADR-056 stage 3a exists for.

`ListMachine` holds the same two axes in a LIST instead, which is how
`_attr_name_for` derives the `<attr>-<index>` names that are legal node
names but illegal expression identifiers.

Neither class binds its own defaults in `__init__`: since this change
the build/test loader binds them from the declarations.
"""

import solid_node.math as sn_math
from solid_node.node import AssemblyNode, TranslationalPort
from solid_node.simulation import Driver, Instruction

from .parts import Cube

# GT2 belt on a 20-tooth pulley: 40mm/rev over 200 steps x 16 microsteps.
MM_PER_USTEP = 40.0 / (200 * 16)
DEG_PER_USTEP = 360.0 / (200 * 16)


class Axis(AssemblyNode):
    """One driven linear axis, declaring the class-local `motor`."""

    motor = Driver(default=8000, range=(0, 8000), unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)
    position = TranslationalPort(unit='mm', scale=MM_PER_USTEP)

    instructions = {
        'Home': Instruction({'motor': 0.0}, duration=2.0),
    }

    def __init__(self, label, **kwargs):
        super().__init__(label, **kwargs)
        self.label = label
        self.carriage = Cube(size=4.0)
        self.pulley = Cube(size=2.0)
        self.cover = Cube(size=3.0)

    def render(self):
        usteps = self.state['motor']
        self.connect(usteps, self.position)
        # Linear in the driver, and through the port's unit scale.
        self.carriage.translate([self.position.value, 0, 0])
        self.pulley.rotate(usteps * DEG_PER_USTEP, [0, 0, 1])
        # MIXED: one formula holding both `$t` and a driver term, which
        # is what the .scad path has to substitute PARTIALLY -- driver
        # numeric, animation time still symbolic.
        self.cover.translate([
            5.0 * sn_math.cos(360.0 * self.time) + self.position.value * 0.1,
            0,
            0,
        ])
        return [self.carriage, self.pulley, self.cover]


class Machine(AssemblyNode):
    """The parent: declares no driver of its own on purpose."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_axis = Axis('x')
        self.y_axis = Axis('y')

    def render(self):
        return [self.x_axis, self.y_axis]


class ListMachine(AssemblyNode):
    """The same two axes held in a list, so each child's derived name is
    `axes-0` / `axes-1` -- a legal node name and an illegal id segment.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.axes = [Axis('x'), Axis('y')]

    def render(self):
        return list(self.axes)
