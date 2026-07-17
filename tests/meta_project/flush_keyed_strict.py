# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .flush_parts import FlushPeg, FlushSlot


class FlushKeyedStrict(AssemblyNode):
    """Red fixture: the exact same flush-shouldered torque fit as
    flush_keyed.py, but its test uses assertFreeWithin with the
    default volume_epsilon=0.0 -- the OLD `is_empty` strictness. The
    shoulder's boolean-noise sliver (0.0mm^3, no real engagement)
    still reads as an intersection at every free angle, so this must
    be reported as a failure -- demonstrating the wart
    improvements.md #21 fixes for the perturbation assertions."""

    def __init__(self):
        self.peg = FlushPeg()
        self.slot = FlushSlot()
        super().__init__()
        self.peg.translate([5, 0, 0])
        self.slot.translate([5, 0, 0])

    def render(self):
        return [self.peg, self.slot]
