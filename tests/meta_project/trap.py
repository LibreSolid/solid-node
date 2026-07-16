# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Green fixture reproducing the exact trap that bit a real agent
session (skill-repo improvements.md #14): naming a helper subclass so
it ends up defined BEFORE the main node class in the file. Under the
old first-defined-wins loader this silently loaded the helper instead
of the node under test, and the test ran against a leaf with no
useful assertions to fail -- a false green. With NODE naming the main
class explicitly, the right class must load regardless of definition
order, and the same contract as apart.py must genuinely hold."""

from solid_node.node import AssemblyNode
from .parts import Cube


class Helper(Cube):
    """Defined first -- reads like it could be the main class, and is
    exactly what the old loader would have picked."""
    pass


class Trap(AssemblyNode):
    """The actual node under test, defined SECOND: two unit cubes 10
    apart, same contract as Apart."""

    def __init__(self):
        self.a = Cube()
        self.b = Cube()
        super().__init__()
        self.b.translate([10, 0, 0])

    def render(self):
        return [self.a, self.b]


NODE = Trap
