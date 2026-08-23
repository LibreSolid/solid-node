# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The representative caller for the sheet leaf: one panel of a laser-cut
printer frame.

Everything here is what the originating project actually needs -- a panel
of sheet stock, t-slot cutouts that receive a tab of the same stock, a nut
pocket crossing each slot, and round bolt holes. The slot width is derived
from the stock thickness rather than written down twice, which is the whole
point of a sheet part being one authored profile plus a declared thickness.
"""

from build123d import Circle, Pos, Rectangle

from solid_node.node import Build123dSheetNode


PANEL_WIDTH = 120
PANEL_HEIGHT = 80

#: The sheet stock this frame is cut from.
STOCK_THICKNESS = 6

#: How much wider than the stock a slot is cut, so the mating tab enters.
TAB_CLEARANCE = 0.2

SLOT_LENGTH = 20
SLOT_WIDTH = STOCK_THICKNESS + TAB_CLEARANCE
SLOT_X = 40
SLOT_Y = 25

#: The pocket that captures the nut, crossing the slot it tightens.
NUT_POCKET_DEPTH = 2.5
NUT_POCKET_LENGTH = 12

BOLT_RADIUS = 1.7
BOLT_HOLES = ((0, 25), (0, -25), (-15, 0), (15, 0))


class FramePanel(Build123dSheetNode):
    """A frame side panel: stock, t-slots, nut pockets and bolt holes."""

    thickness = STOCK_THICKNESS
    color = '#c8a165'

    def profile(self):
        panel = Rectangle(PANEL_WIDTH, PANEL_HEIGHT)

        for x in (-SLOT_X, SLOT_X):
            for y in (-SLOT_Y, SLOT_Y):
                panel -= Pos(x, y) * Rectangle(SLOT_LENGTH, SLOT_WIDTH)
                panel -= Pos(x, y) * Rectangle(NUT_POCKET_DEPTH,
                                               NUT_POCKET_LENGTH)

        for x, y in BOLT_HOLES:
            panel -= Pos(x, y) * Circle(BOLT_RADIUS)

        return panel
