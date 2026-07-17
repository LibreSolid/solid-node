# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class FlushContactStrictTest(TestCase):

    def test_flush_faces_reported_without_epsilon(self):
        """Deliberately red: the flush faces produce a non-empty
        boolean-noise sliver, and default volume_epsilon=0.0 keeps
        exact is_empty strictness -- this assertion must fail, naming
        the intersection."""
        self.assertNoPairwiseIntersections(self.flush_contact_strict)
