# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Geometry for the perturbation-assertions fixtures (assertBlockedBeyond
/ assertFreeWithin, issue #6): a square peg in a square pocket, the
same torque-fit shape as the gearbox's D-bore/D-shaft, simplified to a
square so the play angle is exact and easy to reason about.

Peg half-side is 0.5. A default Slot opening of 1.2 (half-width 0.6)
lets the peg rotate before a corner touches a wall: contact happens
where 0.5*(cos(t) + sin(t)) == 0.6, at t ~= 13.05deg. BLOCKED/FREE are
picked with generous margins either side of that (no knife-edge
angles). An opening of 2.0 (half-width 1.0) exceeds the peg's
half-diagonal (~0.707), so the peg never touches at any angle -- the
gamed fit the red fixture exercises.
"""

from solid_node.node import Solid2Node
from solid2 import cube


PEG_SIZE = 1.0
SLOT_OPENING = 1.2
SLOT_OPENING_LOOSE = 2.0
SLOT_OUTER = 3.0
SLOT_HEIGHT = 1.0

BLOCKED = 25.0  # well beyond the ~13.05deg play: must foul, both directions
FREE = 5.0      # well within the ~13.05deg play: must clear, both directions


class Peg(Solid2Node):
    """A square peg, side 1, centered: the torque-fit member."""

    def render(self):
        return cube(PEG_SIZE, center=True)


class Slot(Solid2Node):
    """A square pocket of side `opening` cut through a block: the
    peg's mating pocket."""

    def __init__(self, opening=SLOT_OPENING):
        self.opening = opening
        super().__init__(opening=opening)

    def render(self):
        block = cube([SLOT_OUTER, SLOT_OUTER, SLOT_HEIGHT], center=True)
        hole = cube([self.opening, self.opening, SLOT_HEIGHT + 0.5],
                   center=True)
        return block - hole
