# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Garage(AssemblyNode):
    """Green fixture for child-name derivation (skill-repo
    improvements.md #16): `left`/`right` are two same-class children
    held as plain attributes, and `posts` is a list attribute holding
    two more -- all four would collide on the single class name
    "Cube" under the old always-class-name default, and DO collide in
    the viewer's name-addressed tree. Placed apart so the fixture
    stays a genuinely clean mechanism too, even though its test only
    asserts names."""

    def __init__(self):
        self.left = Cube()
        self.right = Cube()
        self.posts = [Cube(), Cube()]
        super().__init__()
        self.right.translate([10, 0, 0])
        self.posts[0].translate([0, 10, 0])
        self.posts[1].translate([10, 10, 0])

    def render(self):
        return [self.left, self.right, self.posts[0], self.posts[1]]
