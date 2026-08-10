# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .cross_part_weld import CrossPartWeld


class CrossPartWeldTest(TestCase):
    node = CrossPartWeld

    def test_separate_parts_are_joined(self):
        # Deliberately red: these are two different solids, held 40mm
        # apart by the assembly. Nothing about them is one part.
        self.assertJoined(self.cross_part_weld.left_bracket,
                          self.cross_part_weld.right_bracket)
