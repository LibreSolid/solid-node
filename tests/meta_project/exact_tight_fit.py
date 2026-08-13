# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import cadquery as cq

from solid_node.node import AssemblyNode, CadQueryNode


class ExactShaft(CadQueryNode):

    def render(self):
        return cq.Workplane("XY").circle(5).extrude(10)


class ExactBore(CadQueryNode):

    def render(self):
        return (
            cq.Workplane("XY")
            .circle(7)
            .circle(5)
            .extrude(10)
        )


class ExactTightFit(AssemblyNode):

    def __init__(self):
        self.shaft = ExactShaft()
        self.bore = ExactBore()
        super().__init__()
        self.shaft.rotate(7, [0, 0, 1])

    def render(self):
        return [self.shaft, self.bore]
