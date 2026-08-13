# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .bolt import RepeatedBolt
from .bushings import BushingA, BushingB


class PiecesAssembly(AssemblyNode):

    def render(self):
        return [
            RepeatedBolt().translate([0, 0, 0]),
            RepeatedBolt().translate([10, 0, 0]),
            RepeatedBolt().translate([20, 0, 0]),
            BushingA(),
            BushingB(),
        ]
