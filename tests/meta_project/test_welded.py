# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase, testing_steps

from .welded import Welded


class WeldedTest(TestCase):
    node = Welded

    @testing_steps(4)
    def test_features_stay_joined_through_the_cycle(self):
        # The enclosing solid is rotated by $t and offset by the
        # assembly; neither can change whether its own features meet.
        self.assertJoined(self.welded.bracket.hub, self.welded.bracket.boss)

    def test_the_weld_meets_its_required_volume(self):
        self.assertJoined(self.welded.bracket.hub, self.welded.bracket.boss,
                          min_weld_volume=0.3)
