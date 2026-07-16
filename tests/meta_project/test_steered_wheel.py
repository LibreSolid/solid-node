# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_steps


class SteeringTest(TestCase):

    @testing_steps(2, start=0.5, end=1.0)
    def test_wheel_tracks_both_drivers(self):
        t = self.steering.time
        center = self.steering.axle.wheel.mesh.center_mass
        self.assertAlmostEqual(center[0], 5 * t, delta=0.01)
        self.assertAlmostEqual(center[2], 3 * t, delta=0.01)
