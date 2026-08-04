# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Steering(AssemblyNode):
    """Green fixture for multi-driver kinematics: the SAME wheel
    instance is driven by two independent assemblies — this one
    (Steering) translates it along X, and its child (Axle) translates
    it along Z. At every instant t the wheel must sit at exactly
    (5t, 0, 3t) — both contributions current and additive.

    This is the adversarial twin of Slider/Nested: those drive a node
    from a single assembly. Here a car's front wheel is legitimately
    spun by its axle and steered by the steering assembly at once. A
    per-assembly snapshot-baseline restore lets the SECOND assembly to
    ever touch the wheel (Axle) capture the FIRST assembly's
    (Steering's) just-appended operation as its own restore baseline,
    then re-impose that stale value before every later render — the
    steering contribution freezes while the axle's own keeps
    updating."""

    def __init__(self):
        self.axle = Axle()
        super().__init__()

    def render(self):
        self.axle.wheel.translate([5 * self.time, 0, 0])
        return [self.axle]


class Axle(AssemblyNode):

    def __init__(self):
        self.wheel = Cube()
        super().__init__()

    def render(self):
        self.wheel.translate([0, 0, 3 * self.time])
        return [self.wheel]
