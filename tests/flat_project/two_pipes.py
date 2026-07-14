# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .simple_pipe import SimplePipe


class TwoPipes(AssemblyNode):

    def render(self):
        return [
            SimplePipe(),
            SimplePipe().translate([100, 0, 0]),
        ]
