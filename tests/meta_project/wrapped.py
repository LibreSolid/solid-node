# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Wrapped(AssemblyNode):
    """Green fixture for mesh composition: a sub-assembly placed as a
    unit. The wrapper is translated, and the leaf's MESH must follow —
    the viewer already composes ancestor operations, so tests must see
    the same world geometry the user sees."""

    def __init__(self):
        self.unit = Unit()
        self.reference = Cube()
        super().__init__()
        self.unit.translate([10, 0, 0])
        self.reference.translate([20, 0, 0])

    def render(self):
        return [self.unit, self.reference]


class Unit(AssemblyNode):

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]


NODE = Wrapped
