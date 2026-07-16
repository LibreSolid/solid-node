# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class SteeringCollision(AssemblyNode):
    """Red fixture for multi-driver kinematics: same topology as
    Steering/Axle (steered_wheel.py), plus a static obstacle sitting
    exactly where the wheel genuinely arrives at t=1.0: (5, 0, 3). The
    no-intersection test must FAIL.

    This is the dangerous direction: with a snapshot-baseline restore,
    Axle is the second assembly to ever touch the wheel and freezes
    Steering's X contribution at whatever it was the first time Axle
    rendered — well short of 5 — so the broken framework reports this
    genuinely colliding mechanism as collision-free."""

    def __init__(self):
        self.axle = Axle()
        self.obstacle = Cube()
        super().__init__()
        self.obstacle.translate([5, 0, 3])

    def render(self):
        self.axle.wheel.translate([5 * self.time, 0, 0])
        return [self.axle, self.obstacle]


class Axle(AssemblyNode):

    def __init__(self):
        self.wheel = Cube()
        super().__init__()

    def render(self):
        self.wheel.translate([0, 0, 3 * self.time])
        return [self.wheel]


NODE = SteeringCollision
