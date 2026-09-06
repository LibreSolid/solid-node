# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Representative callers: imported STEP parts fused and assembled.

Mirrors `stl_project/rack.py`'s role for the STL leaf -- the STEP leaf
is only worth having if it composes with the rest of the framework, not
merely if it reads a file.
"""

import cadquery as cq

from solid_node.node import AssemblyNode, CadQueryNode, FusionNode

from .parts import ColouredPart, SingleProduct


class OverlappingBlock(CadQueryNode):
    """A modelled part overlapping the imported STEP part, so the fusion
    is genuine rather than two disjoint solids side by side."""

    def render(self):
        return cq.Workplane('XY').box(3, 3, 3)


class FusedWithStep(FusionNode):
    """The exact-fusion caller: a vendor STEP part fused with a piece
    designed to fit it."""

    def __init__(self):
        self.step_part = SingleProduct()
        self.block = OverlappingBlock()
        super().__init__()

    def render(self):
        return [self.step_part, self.block]


class ColouredPartHolder(AssemblyNode):
    """An ordinary assembly parent. Its own construction of the child
    must not be mistaken for the child declaring a colour of its own."""

    def __init__(self):
        self.child = ColouredPart()
        super().__init__()

    def render(self):
        return [self.child]


class TwoStepParts(AssemblyNode):
    """Two imported STEP parts, assembled with no external renderer."""

    def __init__(self):
        self.first = SingleProduct()
        self.second = SingleProduct()
        super().__init__()

    def render(self):
        return [self.first, self.second]
