# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The planar slider-crank: crank, connecting rod, piston.

Everything here works in the crank's own plane, and says nothing about
which plane of a machine that is. The crank axis is normal to the plane.
The plane's two coordinates are *across* and *along*, in that order, and
*along* is the cylinder axis -- the line the small end is constrained
to. The crank angle is measured from the along axis, positive by the
right-hand rule about the crank axis, with zero at top dead centre.

A caller whose crank axis is not this plane's normal maps the results
with its own frame rotation. ``projects/v8-engine`` is this plane with
``across = y`` and ``along = z``: its crank turns about +X with the pin
at +Z at angle zero, and its ``pin_center_at``, ``rod_angle_at`` and
``piston_height_at`` are the three functions below verbatim. That
engine's bank offset and throw phases are not here -- they are the
angle it passes in, which is the right place for a machine's own
geometry.

The rod angle's sign is the one thing worth reading twice: it is the
*negative* arcsine, so that a rod authored along the cylinder axis and
turned by the returned angle in the same rotational sense puts its small
end exactly on that axis. That identity, not the sign, is what the
tests pin.
"""

from solid_node.math import asin, cos, sin, sqrt


def crank_pin(angle, crank_radius):
    """The crank pin's ``(across, along)`` position at crank ``angle``:
    ``(-crank_radius * sin(angle), crank_radius * cos(angle))``.

    At zero the pin is at top dead centre, ``(0, crank_radius)``; a
    positive rotation carries it toward -across.
    """
    return (-crank_radius * sin(angle), crank_radius * cos(angle))


def crank_rod_angle(angle, crank_radius, rod_length):
    """The connecting rod's tilt from the cylinder axis at crank
    ``angle``, in the same rotational sense as the crank angle:
    ``-asin((crank_radius / rod_length) * sin(angle))``.

    A rod authored along the cylinder axis, from the pin, and turned by
    this angle carries its small end exactly onto the axis. That is what
    the minus sign is for.
    """
    return -asin((crank_radius / rod_length) * sin(angle))


def piston_height(angle, crank_radius, rod_length):
    """The small end's *along* coordinate at crank ``angle``:
    ``crank_radius * cos(angle) + sqrt(rod_length^2 - (crank_radius *
    sin(angle))^2)``.

    Top dead centre is ``crank_radius + rod_length``, bottom dead centre
    ``rod_length - crank_radius``, and the asymmetry between them at
    quarter turns is the rod's obliquity, which is the whole reason this
    is not a sine.
    """
    lateral = crank_radius * sin(angle)
    return (crank_radius * cos(angle)
            + sqrt(rod_length * rod_length - lateral * lateral))
