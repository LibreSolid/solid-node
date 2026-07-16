# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .hub import Hub
from .blade import Blade


class Spinner(AssemblyNode):
    """A hub with three blades spinning around Z: one full turn per
    animation cycle, blades at static 120/240 degree offsets."""

    def render(self):
        return [
            Hub(),
            Blade(name='b0').rotate(self.time * 360, [0, 0, 1]),
            Blade(name='b1')
                .rotate(120, [0, 0, 1])
                .rotate(self.time * 360, [0, 0, 1]),
            Blade(name='b2')
                .rotate(240, [0, 0, 1])
                .rotate(self.time * 360, [0, 0, 1]),
        ]
