# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase

from .unwelded import Unwelded


class UnweldedTest(TestCase):
    node = Unwelded

    def test_hub_and_boss_are_joined(self):
        # Deliberately red: the fusion is one body, but these two
        # features only reach each other through the bridge.
        self.assertJoined(self.unwelded.bracket.hub,
                          self.unwelded.bracket.boss)
