# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cube


class Blade(Solid2Node):
    color = '#4477cc'

    def render(self):
        return cube([40, 4, 4])
