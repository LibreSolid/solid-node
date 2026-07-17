# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class FlushOverlapTest(TestCase):

    def test_real_overlap_still_reported_with_epsilon(self):
        """Deliberately red: a genuine 0.5mm^3 overlap, far above the
        epsilon -- volume_epsilon must not let real interference pass
        as noise."""
        self.assertNoPairwiseIntersections(
            self.flush_overlap, volume_epsilon=1e-6)
