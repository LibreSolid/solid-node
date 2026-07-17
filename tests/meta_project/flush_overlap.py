# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class FlushOverlap(AssemblyNode):
    """Anti-gaming red fixture for volume_epsilon (improvements.md
    #21): same two unit cubes as flush.py, but stacked with a genuine
    0.5mm overlap along Z instead of a flush meet -- comfortably above
    any noise floor. volume_epsilon must not legitimize real
    interference: assertNoPairwiseIntersections(volume_epsilon=1e-6)
    must still report this pair."""

    def __init__(self):
        self.a = Cube()
        self.b = Cube()
        super().__init__()
        self.a.translate([0, 0, 0.5])
        self.b.translate([0, 0, 1.0])

    def render(self):
        return [self.a, self.b]
