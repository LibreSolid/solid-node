# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .peg_slot import Peg, Slot, SLOT_OPENING_LOOSE


class KeyedLoose(AssemblyNode):
    """Red fixture: the gamed fit. The pocket opening (SLOT_OPENING_LOOSE,
    half-width 1.0) exceeds the peg's half-diagonal (~0.707), so the
    peg never fouls the slot at ANY rotation. assertBlockedBeyond must
    report this as a failure -- the meta harness asserts that failure
    is exactly what happens (the anti-gaming guarantee: an oversized
    pocket cannot pass as blocked)."""

    def __init__(self):
        self.peg = Peg()
        self.slot = Slot(opening=SLOT_OPENING_LOOSE)
        super().__init__()
        self.peg.translate([5, 0, 0])
        self.slot.translate([5, 0, 0])

    def render(self):
        return [self.peg, self.slot]
