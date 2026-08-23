# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The parts the mesh fixtures come from.

A downloaded STL cannot be committed here, and the motivating reference
(Dragon R1) is far too big to be a test subject, so the framework
authors the part itself, exports its mesh, and then reads that mesh back
as a foreign one. Equivalence between this part and the `StlNode` that
wraps its export is what the round trip proves.
"""

import cadquery as cq

from solid_node.node import CadQueryNode


BRACKET_LENGTH = 20
BRACKET_WIDTH = 10
BRACKET_HEIGHT = 5
BRACKET_HOLE_DIAMETER = 4


class OriginalBracket(CadQueryNode):
    """A plate with a bore through it: planar faces the mesh reproduces
    exactly, plus one curved face whose tessellation is what a foreign
    mesh really carries."""

    def render(self):
        return (
            cq.Workplane('XY')
            .box(BRACKET_LENGTH, BRACKET_WIDTH, BRACKET_HEIGHT)
            .faces('>Z').workplane().hole(BRACKET_HOLE_DIAMETER)
        )


class Post(CadQueryNode):
    """The piece designed to fit the bracket: a pin through its bore,
    standing proud on both faces. Fusing it with the imported mesh is the
    design-a-piece-that-fits case."""

    def render(self):
        return (
            cq.Workplane('XY')
            .cylinder(BRACKET_HEIGHT * 3, BRACKET_HOLE_DIAMETER / 2)
        )
