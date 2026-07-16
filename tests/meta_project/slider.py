# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Slider(AssemblyNode):
    """Green fixture for keyframe idempotency: a cube sliding along X
    at 10 units per animation cycle. At every instant t the cube must
    sit at exactly x = 10*t — an ABSOLUTE position. If operations
    accumulate across set_keyframe() re-renders, the second sampled
    instant already drifts."""

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        self.cube.translate([10 * self.time, 0, 0])
        return [self.cube]
