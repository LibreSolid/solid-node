# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_steps

from .assembly_integrity_animated import AssemblyIntegrityAnimated


class AssemblyIntegrityAnimatedTest(TestCase):
    node = AssemblyIntegrityAnimated

    @testing_steps(3)
    def test_assembly_integrity(self):
        self.assertNoSolidInterference(self.node)
