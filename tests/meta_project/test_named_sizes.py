# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class NamedSizesTest(TestCase):

    def test_distinctly_named_cubes_get_correct_independent_geometry(self):
        self.assertAlmostEqual(
            self.named_sizes.small.mesh.volume, 1.0, delta=0.02)
        self.assertAlmostEqual(
            self.named_sizes.big.mesh.volume, 8.0, delta=0.05)
