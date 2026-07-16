# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Separated(AssemblyNode):
    """Green fixture for assertNoPairwiseIntersections (issue #11):
    three leaves, none sharing volume. Two of them (b, c) sit one
    level deep in a nested child assembly, so the leaf walk must
    recurse through child assemblies, not just stop at direct
    children."""

    def __init__(self):
        self.a = LegA()
        self.group = Pair()
        super().__init__()
        self.group.translate([10, 0, 0])

    def render(self):
        return [self.a, self.group]


class Pair(AssemblyNode):

    def __init__(self):
        self.b = LegB()
        self.c = LegC()
        super().__init__()
        self.c.translate([5, 0, 0])

    def render(self):
        return [self.b, self.c]


# Distinct classes so each leaf's node.name is unique in failure
# messages (a plain Cube() always reports as "Cube" -- see
# examples/gearbox root/housing_wall.py for the same subclassing
# trick, used there for FrontWall/MiddleWall/RearWall). Defined after
# Separated/Pair: the node loader picks the first node class defined
# in the file.
class LegA(Cube):
    pass


class LegB(Cube):
    pass


class LegC(Cube):
    pass
