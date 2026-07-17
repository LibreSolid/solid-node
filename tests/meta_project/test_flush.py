# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class FlushContactTest(TestCase):

    def test_flush_faces_pass_with_volume_epsilon(self):
        """The two cubes' faces meet exactly -- 0.0mm^3 real overlap,
        boolean noise aside. With volume_epsilon above that noise
        floor, the pairwise sweep must NOT report a false
        interference."""
        self.assertNoPairwiseIntersections(
            self.flush_contact, volume_epsilon=1e-6)
