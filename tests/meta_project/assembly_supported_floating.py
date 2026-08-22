# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Red-by-construction fixture for assertAssemblySupported: the two ways
an assembly can be unsupported without any part looking wrong on its own.

`chain` is the defect the assertion exists for -- a part placed in space,
with a second part correctly resting on it. `leaning` is the transitive
half: two pieces that genuinely hold each other, and nothing else, while
the assembly's ground sits elsewhere.
"""

from solid_node.node import AssemblyNode

from .support_parts import Block, LeftHook, RightHook


class AssemblySupportedFloating(AssemblyNode):

    def __init__(self):
        self.chain = Chain()
        self.leaning = Leaning()
        super().__init__()
        self.leaning.translate([0, 20, 0])

    def render(self):
        return [self.chain, self.leaning]


class Chain(AssemblyNode):
    """A grounded base, a floater ten units above it, and a rider
    resting correctly on the floater: neither the floater nor its rider
    is held by anything."""

    def __init__(self):
        self.base = Block([4, 4, 2])
        self.floater = Block([2, 2, 2])
        self.rider = Block([2, 2, 2])
        super().__init__()
        self.floater.translate([1, 1, 10])
        self.rider.translate([1, 1, 12])

    def render(self):
        return [self.base, self.floater, self.rider]


class Leaning(AssemblyNode):
    """Two interlocking pieces that hold each other in a cycle, with the
    only grounded solid parked out of reach: mutual support is not
    ground."""

    def __init__(self):
        self.anchor = Block([4, 2, 2])
        self.left = LeftHook()
        self.right = RightHook()
        super().__init__()
        self.anchor.translate([10, 0, 0])

    def render(self):
        return [self.anchor, self.left, self.right]

