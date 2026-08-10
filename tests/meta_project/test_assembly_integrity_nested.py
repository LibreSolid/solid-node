# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .assembly_integrity_nested import AssemblyIntegrityNested


class AssemblyIntegrityNestedTest(TestCase):
    node = AssemblyIntegrityNested

    def test_assembly_integrity(self):
        self.assertNoSolidInterference(self.node)
