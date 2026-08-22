# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .assembly_supported_unbalanced import AssemblySupportedUnbalanced


class AssemblySupportedUnbalancedTest(TestCase):
    node = AssemblySupportedUnbalanced

    def test_one_end_supported_bar_is_reported(self):
        self.assertAssemblySupported(self.node.cantilever)

    def test_tippy_seed_is_reported(self):
        self.assertAssemblySupported(self.node.tippy)
