# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The three pieces of circle geometry a linkage keeps asking for.

Where two arcs cross, what angle a triangle of three known sides makes,
and how high a rigid link stands when its ends are pulled apart. Each of
them was written out longhand in at least one project, numerically only,
and broke the first time a driver symbol reached it.

Coordinates are plain ``(x, y)`` 2-tuples in whatever plane the caller
is working in; angles are degrees.

``side``. A circle-circle intersection has two answers, and naming which
one by a sign is only meaningful against a stated direction. Here the
direction is from ``centre_a`` to ``centre_b``: ``side = 1`` is the
intersection to its left (counter-clockwise from it), ``side = -1`` to
its right. ``projects/3DPrintedClocks``'s grasshopper escapement calls
this its ``branch``, and its ``nib_position(pivot, arm, branch, radius)``
is ``circle_intersection((0, 0), radius, pivot, arm, branch)``.

No guards. An unreachable configuration -- circles too far apart or one
inside the other, a triangle whose sides do not close, a link shorter
than its offset -- reaches ``sqrt`` or ``acos`` of an out-of-range value
and raises numerically, exactly as ``solid_node.math`` raises, and
evaluates to NaN symbolically, exactly as OpenSCAD and the viewer do.
That is what the originating projects do and it is the honest answer: a
guard would have to invent a pose that does not exist.
"""

from solid_node.math import acos, sqrt


def circle_intersection(centre_a, radius_a, centre_b, radius_b, side=1):
    """The ``(x, y)`` at distance ``radius_a`` from ``centre_a`` and
    ``radius_b`` from ``centre_b``, on the side named.

    ``side = 1`` picks the intersection to the left of the direction
    from ``centre_a`` to ``centre_b``, ``side = -1`` the one to its
    right. See the module docstring.
    """
    ax, ay = centre_a
    bx, by = centre_b
    vx, vy = bx - ax, by - ay
    distance = sqrt(vx * vx + vy * vy)
    along = ((distance * distance - radius_b * radius_b + radius_a * radius_a)
             / (2 * distance))
    across = side * sqrt(radius_a * radius_a - along * along)
    unit_x, unit_y = vx / distance, vy / distance
    return (ax + along * unit_x - across * unit_y,
            ay + along * unit_y + across * unit_x)


def triangle_angle(opposite, adjacent_a, adjacent_b):
    """The angle, in degrees, of a triangle opposite the side
    ``opposite``, between the sides ``adjacent_a`` and ``adjacent_b``:
    the law of cosines, ``acos((a^2 + b^2 - opposite^2) / (2 a b))``.
    """
    return acos((adjacent_a * adjacent_a + adjacent_b * adjacent_b
                 - opposite * opposite)
                / (2 * adjacent_a * adjacent_b))


def link_rise(link, offset):
    """The height of a rigid link of length ``link`` whose ends are
    ``offset`` apart horizontally: ``sqrt(link^2 - offset^2)``.
    """
    return sqrt(link * link - offset * offset)
