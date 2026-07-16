# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_steps


class SliderTest(TestCase):

    @testing_steps(2, start=0.5, end=1.0)
    def test_cube_at_absolute_position(self):
        expected = 10 * self.slider.time
        self.assertAlmostEqual(
            self.slider.cube.mesh.center_mass[0], expected, delta=0.01)
