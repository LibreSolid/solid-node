# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import Solid2Node
from solid2 import cylinder


class BushingA(Solid2Node):
    """Two differently-named classes producing identical geometry: the
    gearbox shape, minimised. uniq_id treats these as two artifacts;
    piece identity must fold them into one printed piece."""

    def render(self):
        return cylinder(r=6, h=12) - cylinder(r=4, h=12)


class BushingB(Solid2Node):

    def render(self):
        return cylinder(r=6, h=12) - cylinder(r=4, h=12)
