# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cylinder


class SimplePipe(Solid2Node):

    def render(self):
        return cylinder(r=10, h=100) - cylinder(r=8, h=100)
