# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase
from .peg_slot import BLOCKED, FREE

VOLUME_EPSILON = 1e-6


class FlushKeyedTest(TestCase):

    def test_peg_blocked_beyond_play(self):
        """Genuine corner engagement (~0.0217mm^3) is well above the
        epsilon, in both directions -- must still be blocked."""
        self.assertBlockedBeyond(
            self.flush_keyed.peg, BLOCKED, self.flush_keyed.slot,
            volume_epsilon=VOLUME_EPSILON)

    def test_peg_free_within_play(self):
        """Only the shoulder's flush-contact boolean noise (0.0mm^3)
        is present within the real play -- with volume_epsilon it must
        read as free, in both directions."""
        self.assertFreeWithin(
            self.flush_keyed.peg, FREE, self.flush_keyed.slot,
            volume_epsilon=VOLUME_EPSILON)
