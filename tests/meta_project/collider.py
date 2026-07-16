# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node import AssemblyNode
from .parts import Cube


class Collider(AssemblyNode):
    """Red fixture for keyframe idempotency: a cube sliding to x = 6*t
    straight into an obstacle centered at x = 6.5 — at t = 1.0 they
    genuinely overlap, so the no-intersection test must FAIL.

    This is the adversarial twin of Slider: with the accumulation bug
    the slider overshoots PAST the obstacle at the second instant
    (x = 3 + 6 = 9) and the test passes — the runner reporting a
    collision-free mechanism that in fact collides."""

    def __init__(self):
        self.slider = Cube()
        self.obstacle = Cube()
        super().__init__()
        self.obstacle.translate([6.5, 0, 0])

    def render(self):
        self.slider.translate([6 * self.time, 0, 0])
        return [self.slider, self.obstacle]
