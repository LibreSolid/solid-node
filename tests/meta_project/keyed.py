# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .peg_slot import Peg, Slot


class Keyed(AssemblyNode):
    """Green fixture for the perturbation assertions (issue #6): a
    square peg seated in its slot, both placed away from the world
    origin (x=5), so the mechanic under test -- rotating about the
    node's OWN axis, not the world origin -- is genuinely exercised.
    Blocked well beyond the fit's ~13deg play, free well within it.
    """

    def __init__(self):
        self.peg = Peg()
        self.slot = Slot()
        super().__init__()
        self.peg.translate([5, 0, 0])
        self.slot.translate([5, 0, 0])

    def render(self):
        return [self.peg, self.slot]
