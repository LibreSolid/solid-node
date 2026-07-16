# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Nested(AssemblyNode):
    """Green fixture for keyframe propagation: the moving part lives
    inside a child assembly. set_keyframe on the root must reach it —
    otherwise the inner assembly keeps symbolic time and its children's
    meshes are unusable in tests."""

    def __init__(self):
        self.inner = Inner()
        super().__init__()

    def render(self):
        return [self.inner]


class Inner(AssemblyNode):

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        self.cube.translate([10 * self.time, 0, 0])
        return [self.cube]


NODE = Nested
