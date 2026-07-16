# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class LongParamsTest(TestCase):

    def test_mesh_exists(self):
        self.assertIsNotNone(self.long_params.mesh)
