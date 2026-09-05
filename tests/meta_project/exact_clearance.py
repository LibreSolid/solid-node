# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Green fixture for the faceted kernel: an exact round fit with a real
0.2 mm radial clearance -- more than the 0.1 mm the STL tessellation may
deviate by -- so the parts' meshes never touch where the solids do not,
and the faceted kernel reaches the exact kernel's verdict at epsilon 0.
"""

import cadquery as cq

from solid_node.node import AssemblyNode, CadQueryNode


class ClearedShaft(CadQueryNode):

    def render(self):
        return cq.Workplane("XY").circle(4.8).extrude(10)


class ClearedBore(CadQueryNode):

    def render(self):
        return (
            cq.Workplane("XY")
            .circle(7)
            .circle(5)
            .extrude(10)
        )


class ExactClearance(AssemblyNode):

    def __init__(self):
        self.shaft = ClearedShaft()
        self.bore = ClearedBore()
        super().__init__()
        self.shaft.rotate(7, [0, 0, 1])

    def render(self):
        return [self.shaft, self.bore]
