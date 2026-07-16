# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Leaky(AssemblyNode):
    """Green fixture for runner state isolation: its tests deliberately
    leak operations onto the cube (and clobber its checkpoint), and
    assert that the runner still hands every instant and every test a
    clean node. The cube is static — the assembly applies no kinematic
    operations — so only the runner's own restore can clean the leaks."""

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        return [self.cube]
