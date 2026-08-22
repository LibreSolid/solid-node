# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Green fixture proving the exact route: an assembly whose solids all
expose boundary-representation geometry has its drops intersected by the
kernel rather than by faceted Manifolds. A round boss resting on a round
plate is the shape whose facets would be an approximation.
"""

import cadquery as cq

from solid_node.node import AssemblyNode, CadQueryNode


class ExactPlate(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').circle(10).extrude(2)


class ExactBoss(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').circle(3).extrude(2)


class AssemblySupportedExact(AssemblyNode):

    def __init__(self):
        self.plate = ExactPlate()
        self.boss = ExactBoss()
        super().__init__()
        self.boss.translate([0, 0, 2])

    def render(self):
        return [self.plate, self.boss]
