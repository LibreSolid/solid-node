# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cube


class Cube(Solid2Node):
    """A centered cube, the only geometry the fixture projects need."""

    def __init__(self, size=1.0, name=None):
        self.size = size
        super().__init__(size=size, name=name)

    def render(self):
        return cube(self.size, center=True)
