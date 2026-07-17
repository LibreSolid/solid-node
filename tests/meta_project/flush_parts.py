# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Geometry for the perturbation-assertions' volume_epsilon coverage
(skill-repo improvements.md #21): the peg_slot torque fit (issue #6)
plus a coaxial round "journal" shoulder with an off-axis keyway
notch, standing in for the v8-engine crankshaft's journal end faces
meeting flush at the station pitch.

The shoulder is round in cross-section, so the node's own z-rotation
(the perturbation axis) cannot move it out of registration with its
counterpart -- it stays flush-touching at every swept angle, the same
way a crankshaft's journal face stays flush with its neighbour
whatever the crank angle. Through the real build pipeline (solid2 ->
OpenSCAD -> STL -> trimesh) that flush contact reproducibly comes
back non-empty at a hair's-width volume once the peg carries ANY
rotation (verified: exactly 0.0mm^3 at every angle tried, vs. a clean
empty result at zero rotation) -- boolean noise, not real engagement,
same mechanism as flush.py/flush_strict.py. It sits well below any
real square-peg corner engagement (>=0.01mm^3 well past BLOCKED) and
well below volume_epsilon.

Peg/pocket dimensions and BLOCKED/FREE angles are the same as
peg_slot.py -- see that module's docstring for the ~13.05deg play
derivation.
"""

from solid_node.node import Solid2Node
from solid2 import cube, cylinder

from .peg_slot import (
    PEG_SIZE, SLOT_OPENING, SLOT_OUTER, SLOT_HEIGHT,
)

SHOULDER_RADIUS = 0.3
SHOULDER_HEIGHT = 1.0
KEYWAY_SIDE = 0.2
KEYWAY_OFFSET = 0.25


def _shoulder():
    """A round journal stub with an off-axis keyway notch: the CSG
    difference is what introduces the flush-contact boolean noise
    this fixture targets."""
    body = cylinder(r=SHOULDER_RADIUS, h=SHOULDER_HEIGHT, _fn=32,
                    center=True)
    keyway = cube([KEYWAY_SIDE, KEYWAY_SIDE, SHOULDER_HEIGHT + 0.2],
                 center=True).translate([KEYWAY_OFFSET, 0, 0])
    return body - keyway


class FlushPeg(Solid2Node):
    """The peg_slot square torque-fit peg, plus a round flush
    shoulder below it."""

    def __init__(self):
        # `part='peg'` is a no-op geometrically, but gives this class
        # a non-empty uniq_id distinct from FlushSlot's: two different
        # no-arg node classes defined in the SAME source file
        # otherwise share the bare-script-name basename (uniq_id is
        # derived only from constructor args, not from the class),
        # and would silently collide on one cached STL.
        super().__init__(part='peg')

    def render(self):
        peg = cube(PEG_SIZE, center=True)
        shoulder = _shoulder().translate(
            [0, 0, -(PEG_SIZE / 2 + SHOULDER_HEIGHT / 2)])
        return peg + shoulder


class FlushSlot(Solid2Node):
    """The peg_slot pocket block, plus the shoulder's mating
    counterpart -- coaxial with FlushPeg's shoulder and touching it
    exactly at rest."""

    def __init__(self):
        super().__init__(part='slot')

    def render(self):
        block = cube([SLOT_OUTER, SLOT_OUTER, SLOT_HEIGHT], center=True)
        hole = cube([SLOT_OPENING, SLOT_OPENING, SLOT_HEIGHT + 0.5],
                   center=True)
        slot = block - hole
        counterpart = _shoulder().translate(
            [0, 0, -(PEG_SIZE / 2 + SHOULDER_HEIGHT + SHOULDER_HEIGHT / 2)])
        return slot + counterpart
