# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.test import TestCase


class WrappedOverlapTest(TestCase):

    def test_wrapped_leaf_clears_reference(self):
        """Deliberately red: in world space the wrapped cube sits
        exactly on the reference. Must be reported as a failure."""
        self.assertNotIntersecting(
            self.wrapped_overlap.unit.cube, self.wrapped_overlap.reference)
