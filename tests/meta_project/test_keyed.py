# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase
from .peg_slot import BLOCKED, FREE


class KeyedTest(TestCase):

    def test_peg_blocked_beyond_play(self):
        self.assertBlockedBeyond(self.keyed.peg, BLOCKED, self.keyed.slot)

    def test_peg_free_within_play(self):
        self.assertFreeWithin(self.keyed.peg, FREE, self.keyed.slot)
