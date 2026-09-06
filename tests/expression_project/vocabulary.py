# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Every symbolic name `solid_node.math` can emit, on the wire.

ADR-022 records one expression semantics that several runtimes must
reproduce function for function, and `parity-fixture.test.ts` enforces
it against producer values. That enforcement is only as wide as the
corpus, and the spike's two-axis machine
(`spike/expressions/machine_model.py`) covers the vocabulary as it was:
the degree trigonometry, `sqrt`, `^`, driver terms and port scales.

This tree covers the rest -- the six direct builtins and the
compositions over them -- so that no name in
`solid_node.math.SYMBOLIC_BUILTINS` reaches a published document
without a fixture case behind it. It is a corpus, not a machine: the
geometry is three markers, and what the operations are built to
exercise is the shape of the EXPRESSIONS.

It is a second tree rather than more operations on the spike's, on
purpose: editing that model would change the key and expected value of
every case already pinned, and a regeneration nobody can review is a
regeneration nobody checks.

Every call takes an argument that is symbolic under the document's
symbolic mode -- the driver or `$t` -- because a call on constants
alone would fold to a number and put no name on the wire at all.
"""

from solid2 import cube

import solid_node.math as m
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.simulation import Driver

#: The driver's native units per design unit: 100 native units is one
#: full sweep, so `self.drive * SCALE` runs 0..1 over the range.
SCALE = 0.01

#: A waypoint table, exactly the shape fender-bender's release path has.
WAYPOINTS = ((0.0, 0.0), (0.25, 4.0), (0.5, 6.0), (1.0, 1.0))


class Marker(Solid2Node):
    """A cube. The geometry is not the point."""

    def __init__(self, label, **kwargs):
        super().__init__(label, **kwargs)
        self.label = label

    def render(self):
        return cube([2, 2, 2])


class Vocabulary(AssemblyNode):
    """One driver, three markers, and one operation slot per function."""

    drive = Driver(default=0, range=(0, 100), unit='step', dtype=int,
                   scale=SCALE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.builtins = Marker('builtins')
        self.compositions = Marker('compositions')
        self.vectors = Marker('vectors')

    def render(self):
        return [self.builtins, self.compositions, self.vectors]

    def simulate(self):
        u = self.drive * SCALE
        t = self.time

        # -- the six direct builtins, including on negative arguments,
        #    which is where a runtime's floor, sign, min or max could
        #    disagree if any of them did.
        self.builtins.translate([
            m.abs(u - 0.5),
            m.floor(4.0 * u),
            m.ceil(3.0 * u),
        ])
        self.builtins.rotate(m.sign(u - 0.5) * 90.0, [0, 0, 1])
        self.builtins.translate([
            m.min(u, 0.5),
            m.max(u, 0.25),
            m.sqrt(m.abs(u)),
        ])

        # -- the compositions over them
        self.compositions.translate([
            m.clamp(u, 0.1, 0.9),
            m.clamp01(2.0 * u - 0.5),
            m.ramp(u, 0.2, 0.8),
        ])
        self.compositions.rotate(m.wrap(720.0 * t), [0, 1, 0])
        self.compositions.translate([
            m.lerp(2.0, 8.0, m.clamp01(u)),
            m.bump(u),
            m.piecewise(u, WAYPOINTS),
        ])

        # -- the vector helpers, and the trigonometry they compose
        x, y = m.polar(10.0, 360.0 * u)
        self.vectors.translate([x, y, 0])
        self.vectors.translate(list(m.turn((10.0, 4.0), 360.0 * t,
                                           about=(1.0, 2.0))) + [0])
        self.vectors.translate(list(m.rotate_x((1.0, 2.0, 3.0), 180.0 * u)))
        self.vectors.translate(list(m.rotate_y((1.0, 2.0, 3.0), 180.0 * t)))
        self.vectors.translate(list(m.rotate_z((1.0, 2.0, 3.0),
                                               90.0 + 180.0 * u)))

        # -- the inverse trigonometry and `tan`, each held inside its
        #    own domain by the clamps above them.
        self.vectors.rotate(
            m.atan2(m.sin(360.0 * t), 2.0 + m.cos(360.0 * u)), [1, 0, 0])
        self.vectors.rotate(
            m.asin(0.25 * m.sin(720.0 * t))
            + m.acos(m.clamp(u, -1.0, 1.0))
            + m.atan(u)
            + m.tan(30.0 * m.clamp01(u)),
            [0, 1, 0])
