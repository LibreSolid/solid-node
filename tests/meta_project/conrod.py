# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from solid_node import math as snmath
from .parts import Cube


class Conrod(AssemblyNode):
    """Green fixture for genuinely non-linear symbolic kinematics
    (skill-repo improvements.md #19): the classic slider-crank conrod
    angle, swing = asin((r/l) * sin(theta)), theta = 360*t.

    AssemblyNode.time is numeric under set_keyframe() (tests) but
    symbolic ($t, a solid2 OpenSCADConstant) in the viewer/build path
    (a fresh node.assemble(), no set_keyframe -- see
    tests/test_conrod_symbolic.py). A plain math.asin(...) call
    raises TypeError the moment it touches the symbolic time -- the
    first non-linear mechanism kills `solid develop`. solid_node.math
    must compute the correct numeric swing under set_keyframe AND
    build the equivalent OpenSCAD asin(...) expression, unevaluated,
    when self.time is still symbolic.

    r=1, l=4: the crank sweeps a full revolution per animation cycle;
    the rod's swing angle is a genuine asin, never linearizable away.
    """

    r = 1.0
    l = 4.0

    def __init__(self):
        self.rod = Cube()
        super().__init__()

    def render(self):
        theta = 360.0 * self.time
        swing = snmath.asin((self.r / self.l) * snmath.sin(theta))
        self.rod.translate([2, 0, 0])
        self.rod.rotate(swing, [0, 0, 1])
        return [self.rod]


NODE = Conrod
