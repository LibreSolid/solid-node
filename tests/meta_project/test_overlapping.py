# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class OverlappingTest(TestCase):

    def test_overlapping_cubes_reported(self):
        """Deliberately red: the cubes DO intersect, so this assertion
        must fail — the meta harness checks the runner says so."""
        self.assertNotIntersecting(self.overlapping.a, self.overlapping.b)
