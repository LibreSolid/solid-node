# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .assembly_supported_balanced import AssemblySupportedBalanced


class AssemblySupportedBalancedTest(TestCase):
    node = AssemblySupportedBalanced

    def test_bar_carried_at_both_ends_stands(self):
        self.assertAssemblySupported(self.node.spanning)

    def test_counterweighted_beam_stands(self):
        self.assertAssemblySupported(self.node.counterweighted)

    def test_cantilevered_pin_stands_on_its_couple(self):
        self.assertAssemblySupported(self.node.cantilevered, max_drop=0.5)
