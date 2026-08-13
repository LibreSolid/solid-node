# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .exact_subfacet_interference import ExactSubfacetInterference


class ExactSubfacetInterferenceTest(TestCase):
    node = ExactSubfacetInterference

    def test_real_subfacet_interference_is_reported(self):
        self.assertNoSolidInterference(self.node)
