# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode, FusionNode

from .parts import Cube


class Welded(AssemblyNode):
    """Green fixture for solid-local connectivity: one printed part,
    animated as a whole.

    The bracket is a real fusion of two overlapping cubes, and the
    assembly both offsets and rotates it with `self.time`. Connectivity
    inside the bracket must be answered in the bracket's OWN frame:
    unaffected by where the assembly puts it, and identical at every
    animation instant. Composing the world frame here would resolve the
    `$t` rotation, which is exactly the coupling this fixture exists to
    keep out."""

    def __init__(self):
        self.bracket = Bracket()
        super().__init__()

    def render(self):
        self.bracket.rotate(360 * self.time, [0, 0, 1]).translate([25, 0, 0])
        return [self.bracket]


class Bracket(FusionNode):
    """Two cubes overlapping by 0.4mm along X: one connected body with
    a real weld between the named features."""

    def __init__(self):
        self.hub = Cube()
        self.boss = Cube()
        super().__init__()
        self.boss.translate([0.6, 0, 0])

    def render(self):
        return [self.hub, self.boss]
