# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The external spur-gear mesh.

A pair is meshed when a tooth of the driven gear points into a gap of
the driver along the line joining their centres. Turn the driver away
from that pose by some angle and the driven follows by the same angle
scaled by the tooth ratio, the other way round. That is the whole of the
law, and it is the whole of what depthing a train decides: an arbor's
own rotation is the only freedom each mesh has.

Frame. Both gears' angles and the line of centres are measured in one
common frame, in degrees, positive by the right-hand rule about the axis
both gears turn on (anticlockwise seen from +Z, which is what a node's
``rotate()`` does). ``line_of_centres`` is the direction from the
driver's centre to the driven's.

The seam: where a tooth sits at zero. Every gear library answers that
differently, so the law takes the answer as two plain angles rather than
reading any gear object:

- ``driver_gap`` -- the direction, in the driver's own frame at angle
  zero, of the centre of one of its gaps.
- ``driven_tooth`` -- the direction, in the driven's own frame at angle
  zero, of the tip of one of its teeth.

They are asymmetric on purpose: a tooth of the driven points into a gap
of the driver, so the driver is described by a gap and the driven by a
tooth. Both default to zero, so a caller with no convention states none.

Two recipes, from the projects this law was lifted from:

- **cq_gears** (``projects/sandbox/gearbox``) centres a tooth on local
  +X at angle zero, so a gap centre sits half a tooth pitch round:
  ``driver_gap = 180 / driver_teeth`` and ``driven_tooth = 0``. With
  those two values ``meshed_angle`` is that project's
  ``conjugate_angle(theta1, z1, z2, alpha)`` exactly.
- **MrBunsy's ``Gear``** (``projects/3DPrintedClocks``) starts
  ``get2D`` at a gap, so the first gap runs from zero to ``gap_angle``:
  a gap centre sits at ``gap_angle / 2`` and a tooth tip at
  ``gap_angle + tooth_angle / 2`` (both in degrees). A part the library
  turns over -- to print it, or to face a pinion the other way --
  mirrors every angle in it, so both references are negated. A lantern
  pinion has no cut profile at all: its leaves are trundles standing in
  holes at multiples of the tooth pitch beginning at zero, so its
  ``driven_tooth`` is zero. Those two lines in the caller are the whole
  of that library's convention; the law does not fork.

Getting a reference half a tooth wrong is the one error that looks like
nothing: a wheel's teeth are as wide as its gaps, so the leaves land on
the teeth instead of between them and every number still reads plausibly.
"""


def meshed_angle(driver_angle, driver_teeth, driven_teeth,
                 line_of_centres=0.0, driver_gap=0.0, driven_tooth=0.0):
    """The angle of the driven gear of an external spur pair.

    ``driven = line + 180 - driven_tooth
    - (driver_teeth / driven_teeth) * (driver_gap + driver_angle - line)``

    At the reference pose -- the driver standing so its referenced gap
    centre points along the line of centres, ``driver_angle = line -
    driver_gap`` -- this is ``line + 180 - driven_tooth``: the driven's
    referenced tooth tip pointing back along the line of centres, into
    that gap. Away from it the driven counter-rotates by the tooth
    ratio.

    See the module docstring for the frame and for the two reference
    angles.
    """
    return (line_of_centres + 180 - driven_tooth
            - (driver_teeth / driven_teeth)
            * (driver_gap + driver_angle - line_of_centres))


def driving_angle(driven_angle, driver_teeth, driven_teeth,
                  line_of_centres=0.0, driver_gap=0.0, driven_tooth=0.0):
    """The driver's angle for a driven gear already placed: the exact
    inverse of :func:`meshed_angle` over the same six arguments.

    Wanted walking a clock train backward from the escape wheel, which
    is the end the escapement fixes.
    """
    return (line_of_centres - driver_gap
            + (driven_teeth / driver_teeth)
            * (line_of_centres + 180 - driven_tooth - driven_angle))
