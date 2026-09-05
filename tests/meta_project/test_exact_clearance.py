# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .exact_clearance import ExactClearance


class ExactClearanceTest(TestCase):
    node = ExactClearance

    def test_cleared_round_fit_has_no_solid_interference(self):
        self.assertNoSolidInterference(self.node)
