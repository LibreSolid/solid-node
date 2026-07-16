# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class SeparatedOverlapTest(TestCase):

    def test_no_pairwise_intersections(self):
        """Deliberately red: LegA and the nested group's LegC share
        volume, a non-adjacent pair -- this assertion must fail,
        naming both leaves."""
        self.assertNoPairwiseIntersections(self.separated_overlap)
