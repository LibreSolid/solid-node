# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Red-by-construction fixture for the statics phase: nothing floats,
every solid reaches ground, and neither group can stand.

`cantilever` is the defect the pilot probed the reachability phase
with -- a bar supported at one end only. `tippy` is the seed that used
to be exempt: a top-heavy solid whose centre of mass falls outside its
own footprint on the unmodelled floor.
"""

from solid_node.node import AssemblyNode

from .support_parts import Block, TopHeavy


class AssemblySupportedUnbalanced(AssemblyNode):

    def __init__(self):
        self.cantilever = Cantilever()
        self.tippy = Tippy()
        super().__init__()
        self.tippy.translate([0, 20, 0])

    def render(self):
        return [self.cantilever, self.tippy]


class Cantilever(AssemblyNode):
    """A bar resting on one support, its centre of mass four bar
    thicknesses out past the landing patch."""

    def __init__(self):
        self.support = Block([2, 2, 2])
        self.bar = Block([10, 2, 2])
        super().__init__()
        self.bar.translate([0, 0, 2])

    def render(self):
        return [self.support, self.bar]


class Tippy(AssemblyNode):
    """A top-heavy solid standing on its own small foot beside a squat
    neighbour: both are default seeds, only one can stand."""

    def __init__(self):
        self.tippy = TopHeavy()
        self.neighbour = Block([4, 2, 2])
        super().__init__()
        self.neighbour.translate([20, 0, 0])

    def render(self):
        return [self.tippy, self.neighbour]
