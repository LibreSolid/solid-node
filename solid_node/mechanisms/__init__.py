# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The mechanism laws a project should not have to write again.

A *mechanism law* here is textbook geometry, not a design decision: how
far a meshed gear has turned, how far a lead screw has advanced, where a
slider-crank's piston is, how high a delta's carriage stands, where two
circles cross. Thirteen `kinematics.py` files in this workspace wrote
some of these out, each in its own frame and sign convention, each
having to rediscover that convention against a rendered mesh, and the
numeric-only ones broke the moment a symbolic driver reached them.

**Two faces, from `solid_node.math`.** Every function here is a
composition of `solid_node.math` functions and ordinary arithmetic, and
has exactly one definition. So it computes a number when the node is
posed at a keyframe, and builds the equivalent deferred OpenSCAD
expression when its driving argument is animation time or a driver
symbol -- the same function either way, just deferred. Nothing here
emits an OpenSCAD builtin `solid_node.math` does not already emit, so
the cross-runtime parity corpus covers this package without extension.

**No third, declared face.** The laws carry degree literals: the mesh
adds `180`, the screw divides by `360`. In the dimension algebra a plain
number is dimensionless and `Angle` is its own axis, so `line + 180`
over a declared `Angle` raises, and it should -- there is no way to
spell "180 degrees" as a dimensioned constant today. A declared token
reaching a law therefore raises the algebra's own `DimensionError` at
class definition, which is loud and early. A class body that wants a
static mesh phase computes it over `.value` operands, the algebra's
stated escape hatch::

    class Train(AssemblyNode):
        wheel = Count(60)
        pinion = Count(8)
        phase = Angle(0.0)
        pinion_phase = meshed_angle(phase.value, wheel.value, pinion.value)

**Conventions.** Every angle is in degrees, positive by the right-hand
rule about the stated axis, matching `solid_node.math` and the node
transform API. Each family module states its frame, its zero and its
sign once, at the top, and maps them onto the project the law was lifted
from; read that module before calling into it. The names are unique
across families -- `crank_rod_angle`, not `rod_angle`; `delta_rod`, not
`rod_tilt` -- so the flat import says which family it came from.

The re-exports are eager: each family module imports only
`solid_node.math`, so there is nothing heavy to defer.
"""

from solid_node.mechanisms.cranks import (crank_pin, crank_rod_angle,
                                         piston_height)
from solid_node.mechanisms.deltas import delta_carriage, delta_rod
from solid_node.mechanisms.gears import driving_angle, meshed_angle
from solid_node.mechanisms.linkages import (circle_intersection, link_rise,
                                           triangle_angle)
from solid_node.mechanisms.screws import screw_angle, screw_travel

__all__ = [
    'meshed_angle', 'driving_angle',
    'screw_travel', 'screw_angle',
    'crank_pin', 'crank_rod_angle', 'piston_height',
    'delta_carriage', 'delta_rod',
    'circle_intersection', 'triangle_angle', 'link_rise',
]
