# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_steps

from .assembly_supported_lifted import AssemblySupportedLifted


class AssemblySupportedLiftedTest(TestCase):
    node = AssemblySupportedLifted

    @testing_steps(3)
    def test_lifted_block_leaves_its_support(self):
        self.assertAssemblySupported(self.node)
