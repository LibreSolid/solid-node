# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Apart(AssemblyNode):
    """Green fixture: two unit cubes 10 apart. Its tests genuinely
    hold, and the meta harness asserts the runner reports them all
    as passing."""

    def __init__(self):
        self.a = Cube()
        self.b = Cube()
        super().__init__()
        self.b.translate([10, 0, 0])

    def render(self):
        return [self.a, self.b]
