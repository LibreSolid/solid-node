# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cylinder


class Hub(Solid2Node):
    color = '#cc4444'

    def render(self):
        return cylinder(r=8, h=6)
