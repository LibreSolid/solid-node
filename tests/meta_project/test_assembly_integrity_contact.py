# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .assembly_integrity_contact import AssemblyIntegrityContact


class AssemblyIntegrityContactTest(TestCase):
    node = AssemblyIntegrityContact

    def test_assembly_integrity(self):
        self.assertNoSolidInterference(self.node)
