# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase
from .peg_slot import BLOCKED, FREE


class KeyedLooseTest(TestCase):

    def test_peg_blocked_beyond_play(self):
        """Deliberately red: the oversized pocket never fouls the peg
        at any angle, so this assertion must fail -- the meta harness
        checks the runner says so."""
        self.assertBlockedBeyond(
            self.keyed_loose.peg, BLOCKED, self.keyed_loose.slot)

    def test_peg_free_within_play(self):
        self.assertFreeWithin(
            self.keyed_loose.peg, FREE, self.keyed_loose.slot)
