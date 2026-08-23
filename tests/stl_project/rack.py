# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The representative caller: downloaded parts assembled and machined.

Two imported brackets are placed into a rack, which is the assembly a
maker gets for free once a mesh is a part. `PostedBracket` is the reason
the leaf exists at all: a piece authored in a CAD kernel and fused with
the imported mesh, so the new part is designed against the geometry of
the old one.
"""

from solid_node.node import AssemblyNode, FusionNode

from .originals import BRACKET_HEIGHT, Post
from .parts import Bracket


#: How far apart the two brackets sit on the rack.
BRACKET_SPACING = 30


class Rack(AssemblyNode):
    """Two imported parts, placed."""

    def __init__(self):
        self.near = Bracket()
        self.far = Bracket()
        super().__init__()
        self.near.translate([0, 0, BRACKET_HEIGHT])
        # Turned first, then placed: later operations are outermost, so a
        # rotation applied after the translation would swing the part
        # around the origin instead of about itself.
        self.far.rotate(90, [0, 0, 1])
        self.far.translate([BRACKET_SPACING, 0, 0])

    def render(self):
        return [self.near, self.far]


class PostedBracket(FusionNode):
    """One printed solid: the imported bracket with a post through its
    bore. The fusion is faceted, so it unions through the mesh path."""

    def __init__(self):
        self.bracket = Bracket()
        self.post = Post()
        super().__init__()

    def render(self):
        return [self.bracket, self.post]
