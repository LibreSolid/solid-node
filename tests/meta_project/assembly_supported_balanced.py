# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Green fixture for the statics phase: assemblies that reach ground AND
stand up, each by a different balance mechanism.

The groups are spread along Y so they never touch, and each is asserted
on its own subtree so its own lowest solid is what the virtual floor
meets.
"""

from solid_node.node import AssemblyNode

from .support_parts import Block, BoredBlock, Pin


class AssemblySupportedBalanced(AssemblyNode):

    def __init__(self):
        self.spanning = Spanning()
        self.counterweighted = Counterweighted()
        self.cantilevered = Cantilevered()
        super().__init__()
        self.counterweighted.translate([0, 20, 0])
        self.cantilevered.translate([0, 40, 0])

    def render(self):
        return [self.spanning, self.counterweighted, self.cantilevered]


class Spanning(AssemblyNode):
    """A bar carried by a support under each end: two landing patches
    with the bar's centre of mass between them."""

    def __init__(self):
        self.support = Block([2, 2, 2])
        self.far_support = Block([2, 2, 2])
        self.bar = Block([10, 2, 2])
        super().__init__()
        self.far_support.translate([8, 0, 0])
        self.bar.translate([0, 0, 2])

    def render(self):
        return [self.support, self.far_support, self.bar]


class Counterweighted(AssemblyNode):
    """A beam whose own centre of mass overhangs its single support, held
    down by a counterweight that pulls the combined resultant back over
    the landing patch."""

    def __init__(self):
        self.support = Block([2, 2, 2])
        self.beam = Block([6, 2, 2])
        self.weight = Block([2, 2, 8])
        super().__init__()
        self.beam.translate([0, 0, 2])
        self.weight.translate([0, 0, 4])

    def render(self):
        return [self.support, self.beam, self.weight]


class Cantilevered(AssemblyNode):
    """A pin cantilevering out of a grounded block's snug hole: the drop
    finds the hole's lower wall, the lift its upper wall, and only the
    couple of the two balances the pin."""

    def __init__(self):
        self.block = BoredBlock()
        self.pin = Pin()
        super().__init__()

    def render(self):
        return [self.block, self.pin]
