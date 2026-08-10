# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .parts import Cube


class AssemblyIntegrityNested(AssemblyNode):
    """Separated topmost rigid solids at two assembly depths."""

    def __init__(self):
        self.left = Cube()
        self.group = NestedPair()
        super().__init__()
        self.group.translate([4, 0, 0])

    def render(self):
        return [self.left, self.group]


class NestedPair(AssemblyNode):

    def __init__(self):
        self.middle = Cube()
        self.right = Cube()
        super().__init__()
        self.right.translate([2, 0, 0])

    def render(self):
        return [self.middle, self.right]
