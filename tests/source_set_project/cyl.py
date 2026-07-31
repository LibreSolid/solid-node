# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid2 import cylinder
from solid_node.node import Solid2Node

from .dimensions import HEIGHT, RADIUS


class Cyl(Solid2Node):
    """A leaf whose geometry comes from an imported project module."""

    def render(self):
        return cylinder(r=RADIUS, h=HEIGHT)
