# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .parts import Cube


class CrossPartWeld(AssemblyNode):
    """Red fixture guarding the dangerous direction of solid-local
    connectivity: two SEPARATE printed parts, 40mm apart, asserted to be
    welded together.

    Each cube sits directly under the assembly, so each is its own
    topmost rigid node -- its own solid. Placing each in its own solid's
    frame puts both at their part's origin and discards the distance the
    assembly holds between them, so a naive solid-local comparison
    reports two parts that share nothing as one body. `assertJoined`
    must refuse the question instead of answering it in the wrong
    frame."""

    def __init__(self):
        self.left_bracket = Cube()
        self.right_bracket = Cube()
        super().__init__()
        self.left_bracket.translate([-20, 0, 0])
        self.right_bracket.translate([20, 0, 0])

    def render(self):
        return [self.left_bracket, self.right_bracket]
