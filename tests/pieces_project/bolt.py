# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cylinder


class RepeatedBolt(Solid2Node):
    """One shape, placed several times by the assembly -- must remain
    one printed piece regardless of how many poses instantiate it."""

    def render(self):
        return cylinder(r=3, h=20)
