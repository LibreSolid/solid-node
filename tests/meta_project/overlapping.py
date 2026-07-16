# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Overlapping(AssemblyNode):
    """Red fixture: two unit cubes sharing half their volume. Its test
    asserts they do NOT intersect — a genuinely violated contract —
    and the meta harness asserts the runner reports it as a failure,
    with an AssertionError naming the intersection."""

    def __init__(self):
        self.a = Cube()
        self.b = Cube()
        super().__init__()
        self.b.translate([0.5, 0, 0])

    def render(self):
        return [self.a, self.b]
