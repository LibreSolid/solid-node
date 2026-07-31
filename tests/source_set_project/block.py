# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import cadquery as cq

from solid_node.node import CadQueryNode

from .dimensions import HEIGHT, RADIUS


class Block(CadQueryNode):
    """The suite's first CadQuery leaf.

    CadQuery leaves are the ones this matters for: the adapter writes
    the STL inside as_scad(), so a build that does not skip render()
    re-tessellates and re-exports on every run.
    """

    def render(self):
        return cq.Workplane('XY').box(RADIUS * 2, RADIUS * 2, HEIGHT)
