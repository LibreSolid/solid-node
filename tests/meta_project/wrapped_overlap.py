# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class WrappedOverlap(AssemblyNode):
    """Red fixture for mesh composition: the wrapper places its leaf
    exactly on top of the reference cube — in world space they overlap
    completely, so the no-intersection test must FAIL.

    This is the lie the composition bug told: with the leaf's mesh
    stuck at local coordinates, the intersection volume read 0 and the
    runner reported an impossible mechanism as collision-free."""

    def __init__(self):
        self.unit = Unit()
        self.reference = Cube()
        super().__init__()
        self.unit.translate([20, 0, 0])
        self.reference.translate([20, 0, 0])

    def render(self):
        return [self.unit, self.reference]


class Unit(AssemblyNode):

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]
