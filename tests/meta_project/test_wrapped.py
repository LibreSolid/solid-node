# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class WrappedTest(TestCase):

    def test_leaf_mesh_is_at_world_position(self):
        self.assertAlmostEqual(
            self.wrapped.unit.cube.mesh.center_mass[0], 10.0, delta=0.01)

    def test_wrapper_placement_separates_the_parts(self):
        self.assertNotIntersecting(
            self.wrapped.unit.cube, self.wrapped.reference)
