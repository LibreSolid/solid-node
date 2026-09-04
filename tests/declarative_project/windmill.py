# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A windmill-shaped root: a ratio-derived radius, a flag gating a
guard, a legacy child, and a child whose height has no default."""

from solid_node.node import AssemblyNode
from solid_node.parameters import Flag, Length, Ratio
from .parts import Guard, Rotor, Tower


class Windmill(AssemblyNode):

    overall_height = Length(400.0, min=0)
    rotor_fraction = Ratio(0.36, min=0, max=1)
    guard_installed = Flag(True)

    rotor_radius = overall_height * rotor_fraction

    tower = Tower(height=overall_height)
    rotor = Rotor(radius=rotor_radius)
    guard = Guard()

    def render(self):
        if not self.guard_installed:
            self.guard.omit()
