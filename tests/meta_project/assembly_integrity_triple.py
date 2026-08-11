# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .parts import Cube


class AssemblyIntegrityTriple(AssemblyNode):
    """Three topmost rigid solids sharing one common region.

    A whole-assembly volume comparison feels safest here, so this
    fixture proves the pairwise path is not weaker: material shared by
    three solids is necessarily shared by some two of them, and the
    assertion must name such a pair.
    """

    def __init__(self):
        self.first = Cube()
        self.second = Cube()
        self.third = Cube()
        super().__init__()
        self.second.translate([0.5, 0, 0])
        self.third.translate([0, 0.5, 0])

    def render(self):
        return [self.first, self.second, self.third]
