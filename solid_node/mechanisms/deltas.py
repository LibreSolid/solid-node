# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Linear delta kinematics.

A linear delta has three towers standing on a circle about Z, a carriage
riding vertically on each, and a diagonal rod from each carriage to the
effector. A point of the effector becomes three carriage heights, and
each rod's pose follows from the same horizontal offset.

``radius`` is the horizontal distance from an effector joint to its
carriage joint when the effector is at the origin -- ``delta_radius``
in ``projects/kossel``. It is named that way because a delta has three
radii that are easy to confuse (the tower circle, the carriage joints,
the effector joints) and this is the one that closes the triangle: the
tower's own radius less the effector's arm. Getting it from a drawing
rather than from that difference is where every delta's conventions go
wrong.

``tower`` is the tower's azimuth about Z, in degrees, measured from +X.
The effector's joint plane sits at height ``plane``; carriage heights
are returned in the same frame.

Why two rotations. :func:`delta_rod` returns a *tilt* and an *azimuth*
rather than one angle about the perpendicular the lean actually happens
about, and that is a finding about this framework, recorded in
``projects/kossel``: a ``Rotation``'s axis is a constant, it cannot
carry a driver symbol. A rod leaning toward a moving effector would need
a computed axis, so instead it is posed by two rotations about constant
axes -- by ``-tilt`` about Y, then by ``azimuth`` about Z -- which is
the same pose and survives symbolically. The recipe works for a rod
authored along Z with either of its joints at the origin; translate to
that joint afterwards.

Nothing here guards an unreachable point: an effector further from a
carriage joint than the rod is long makes ``sqrt`` of a negative, which
raises numerically and is NaN symbolically, exactly as
``solid_node.math`` behaves.
"""

from solid_node.math import asin, atan2, cos, sin, sqrt


def _offset(x, y, radius, tower):
    """The horizontal vector from the carriage joint of the tower at
    ``tower`` to the effector joint at ``(x, y)``."""
    return x - radius * cos(tower), y - radius * sin(tower)


def delta_carriage(x, y, rod, radius, tower, plane=0.0):
    """The height of the carriage joint on the tower at azimuth
    ``tower``, for an effector at ``(x, y)`` whose joint plane is at
    height ``plane``: ``plane + sqrt(rod^2 - dx^2 - dy^2)``.

    The carriage rises as the effector moves toward its tower and falls
    as it moves away, which is the whole of a delta.
    """
    dx, dy = _offset(x, y, radius, tower)
    return plane + sqrt(rod * rod - dx * dx - dy * dy)


def delta_rod(x, y, rod, radius, tower):
    """The rod's ``(tilt, azimuth)`` for the tower at ``tower``.

    ``tilt`` is its lean from vertical, ``asin(sqrt(dx^2 + dy^2) /
    rod)``; ``azimuth`` is the direction of that lean about Z,
    ``atan2(dy, dx)``.

    Pose a rod authored along Z, with either joint at the origin, by
    rotating it ``-tilt`` about Y and then ``azimuth`` about Z, and
    translate to that joint. Two constant axes, for the reason in the
    module docstring.
    """
    dx, dy = _offset(x, y, radius, tower)
    return asin(sqrt(dx * dx + dy * dy) / rod), atan2(dy, dx)
