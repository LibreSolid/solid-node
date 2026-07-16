# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_instant


class NestedTest(TestCase):

    @testing_instant(0.5)
    def test_nested_cube_moves_with_time(self):
        self.assertAlmostEqual(
            self.nested.inner.cube.mesh.center_mass[0], 5.0, delta=0.01)
