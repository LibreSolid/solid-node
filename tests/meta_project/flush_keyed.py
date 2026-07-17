# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .flush_parts import FlushPeg, FlushSlot


class FlushKeyed(AssemblyNode):
    """Green fixture for volume_epsilon on assertBlockedBeyond /
    assertFreeWithin (skill-repo improvements.md #21): the same
    torque fit as Keyed (peg_slot.py), but each part also carries a
    coaxial round shoulder (flush_parts.py) that stays flush-touching
    its counterpart at EVERY swept angle -- measured: an exact
    0.0mm^3 boolean-noise sliver at every angle within the real
    ~13.05deg play, and ~0.0217mm^3 of genuine corner engagement (on
    top of that same noise) at BLOCKED. Without volume_epsilon the
    noise alone makes assertFreeWithin see a false "intersection" at
    every free angle (see flush_keyed_strict.py for that red
    demonstration); with volume_epsilon it is correctly ignored while
    genuine engagement beyond BLOCKED is still caught in both
    directions."""

    def __init__(self):
        self.peg = FlushPeg()
        self.slot = FlushSlot()
        super().__init__()
        self.peg.translate([5, 0, 0])
        self.slot.translate([5, 0, 0])

    def render(self):
        return [self.peg, self.slot]
