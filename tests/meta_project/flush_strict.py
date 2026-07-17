# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class FlushContactStrict(AssemblyNode):
    """Red fixture: the exact same flush geometry as flush.py, but its
    test uses assertNoPairwiseIntersections with the default
    volume_epsilon=0.0 -- the OLD `is_empty` strictness. The two cubes
    share no real volume, yet the boolean noise sliver at their flush
    interface is non-empty, so this must be reported as a failure --
    demonstrating the wart improvements.md #21 fixes."""

    def __init__(self):
        self.a = Cube()
        self.b = Cube()
        super().__init__()
        self.a.translate([0, 0, 0.5])
        self.b.translate([0, 0, 1.5])

    def render(self):
        return [self.a, self.b]
