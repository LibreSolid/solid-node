# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode

from .parts import Cube


class AssemblyIntegrityContained(AssemblyNode):
    """A smaller solid wholly inside a larger one, no surface crossing.

    The sharpest case for a pairwise interference check: nothing about
    the two surfaces intersects, so surface-crossing intuition would
    miss it entirely. The conservative world bounds still make the pair
    a candidate and the exact boolean still returns the inner solid.
    """

    def __init__(self):
        self.outer = Cube(size=4.0)
        self.inner = Cube(size=1.0)
        super().__init__()

    def render(self):
        return [self.outer, self.inner]
