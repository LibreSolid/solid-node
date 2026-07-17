# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase
from .peg_slot import FREE


class FlushKeyedStrictTest(TestCase):

    def test_peg_free_within_play(self):
        """Deliberately red: without volume_epsilon, the shoulder's
        flush-contact boolean noise reads as a real intersection at
        every angle within the genuine play window."""
        self.assertFreeWithin(
            self.flush_keyed_strict.peg, FREE, self.flush_keyed_strict.slot)
