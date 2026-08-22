# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .assembly_supported_floating import AssemblySupportedFloating


class AssemblySupportedFloatingTest(TestCase):
    node = AssemblySupportedFloating

    def test_floating_chain_is_reported(self):
        self.assertAssemblySupported(self.node.chain)

    def test_mutual_lean_without_ground_is_reported(self):
        self.assertAssemblySupported(self.node.leaning, max_drop=1.5)
