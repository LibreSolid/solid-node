# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class FlushContact(AssemblyNode):
    """Green fixture for volume_epsilon on assertNoPairwiseIntersections
    (skill-repo improvements.md #21): two unit cubes stacked along Z
    so their faces meet exactly at z=1.0 -- no real overlap. Through
    the real build pipeline (solid2 -> OpenSCAD -> STL -> trimesh)
    this legitimate flush abutment reproducibly comes back from
    trimesh.boolean.intersection as a non-empty sliver of exactly
    0.0mm^3 volume: `is_empty` cannot tell it apart from real
    interference (the same wart the v8-engine crankshaft's journal
    end faces hit, at ~1e-13mm^3 instead of an exact 0 -- both are
    pure boolean noise, floors apart from any real engagement volume).
    See flush_strict.py for the same geometry demonstrated red under
    the OLD default-epsilon strictness."""

    def __init__(self):
        self.a = Cube()
        self.b = Cube()
        super().__init__()
        self.a.translate([0, 0, 0.5])
        self.b.translate([0, 0, 1.5])

    def render(self):
        return [self.a, self.b]
