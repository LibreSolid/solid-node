# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .separated import Separated


class SeparatedTest(TestCase):
    node = Separated

    def test_no_pairwise_intersections(self):
        self.assertNoPairwiseIntersections(self.separated)
