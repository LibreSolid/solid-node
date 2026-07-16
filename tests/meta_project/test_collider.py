# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_steps


class ColliderTest(TestCase):

    @testing_steps(2, start=0.5, end=1.0)
    def test_slider_never_hits_obstacle(self):
        """Deliberately red: at t=1.0 the slider is inside the
        obstacle. Must be reported as a failure."""
        self.assertNotIntersecting(
            self.collider.slider, self.collider.obstacle)
