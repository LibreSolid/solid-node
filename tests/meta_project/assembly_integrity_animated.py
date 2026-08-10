# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .parts import Cube


class AssemblyIntegrityAnimated(AssemblyNode):
    """A nested moving solid is clear, overlapping, then touching."""

    def __init__(self):
        self.fixed = Cube()
        self.carriage = MovingCarriage()
        super().__init__()

    def render(self):
        return [self.fixed, self.carriage]


class MovingCarriage(AssemblyNode):

    def __init__(self):
        self.moving = Cube()
        super().__init__()

    def render(self):
        # t=0: clear at x=2; t=.5: positive overlap at x=.5;
        # t=1: boundary contact at x=-1.
        self.moving.translate([2 - 3 * self.time, 0, 0])
        return [self.moving]
