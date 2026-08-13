# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .exact_tight_fit import ExactShaft


class ExactSubfacetInterference(AssemblyNode):

    def __init__(self):
        self.left = ExactShaft()
        self.right = ExactShaft()
        super().__init__()
        self.right.rotate(7, [0, 0, 1])
        self.right.translate([9.999, 0, 0])

    def render(self):
        return [self.left, self.right]
