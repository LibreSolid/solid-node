# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .parts import Cube


class AssemblyIntegrityContact(AssemblyNode):
    """Two unit cubes sharing exactly one boundary face."""

    def __init__(self):
        self.left = Cube()
        self.right = Cube()
        super().__init__()
        self.right.translate([1, 0, 0])

    def render(self):
        return [self.left, self.right]
