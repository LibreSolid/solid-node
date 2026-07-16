# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Red-by-construction fixture (skill-repo improvements.md #14): two
node classes and no NODE marker. `solid test` must fail loudly at
node-class resolution -- naming this file, both candidate classes,
and the remedy (add NODE = <ClassName>) -- instead of silently
instantiating whichever one happens to be defined first."""

from solid_node.node import AssemblyNode
from .parts import Cube


class Unmarked(AssemblyNode):

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]


class AlsoANode(AssemblyNode):
    """A second node class -- with no NODE marker, the loader has no
    way to tell which of these two is the one under test."""

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]
