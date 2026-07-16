# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class SeparatedOverlap(AssemblyNode):
    """Red fixture: `LegA` and the nested group's `LegC` share volume
    -- a NON-adjacent pair. `group` as a whole is placed far from `a`
    (x=10), and `LegC`'s own local offset (x=-10) brings it right back
    to collide with `a`; `LegB` clears both. This is the kind of pair
    an adjacent-only check would miss but the full pairwise sweep must
    catch: assertNoPairwiseIntersections must fail here, naming
    exactly LegA and LegC -- the meta harness checks that."""

    def __init__(self):
        self.a = LegA()
        self.group = OverlappingPair()
        super().__init__()
        self.group.translate([10, 0, 0])

    def render(self):
        return [self.a, self.group]


class OverlappingPair(AssemblyNode):

    def __init__(self):
        self.b = LegB()
        self.c = LegC()
        super().__init__()
        self.b.translate([5, 0, 0])
        self.c.translate([-10, 0.3, 0])

    def render(self):
        return [self.b, self.c]


# Distinct classes for unique node.name in the failure message.
# Defined after SeparatedOverlap/OverlappingPair: the node loader
# picks the first node class defined in the file.
class LegA(Cube):
    pass


class LegB(Cube):
    pass


class LegC(Cube):
    pass
