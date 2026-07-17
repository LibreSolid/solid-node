# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import math

from solid_node.test import TestCase, testing_steps


class ConrodTest(TestCase):

    @testing_steps(7, start=0.0, end=1.0)
    def test_rod_tip_follows_the_conrod_angle(self):
        t = self.conrod.time
        theta = math.radians(360.0 * t)
        swing = math.asin((self.conrod.r / self.conrod.l) * math.sin(theta))

        center = self.conrod.rod.mesh.center_mass
        self.assertAlmostEqual(center[0], 2 * math.cos(swing), delta=0.01)
        self.assertAlmostEqual(center[1], 2 * math.sin(swing), delta=0.01)
