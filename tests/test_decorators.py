# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
# Aliased on import: pytest's default python_functions prefix ("test")
# would otherwise try to collect these factories themselves as tests,
# since they're plain module-level callables whose names start with it.
from solid_node.test import testing_steps as make_steps, testing_instant as make_instant


class TestingStepsTest(TestCase):

    def test_default_start_end(self):
        def method(): pass
        method = make_steps(3)(method)

        self.assertEqual(method.testing_instants, [0, 0.5, 1])

    def test_respects_nonzero_start(self):
        # Regression for B5: instants were computed as `i * step`,
        # entirely ignoring `start`, so a non-zero start was silently
        # dropped and the range was shifted back to [0, ...].
        def method(): pass
        method = make_steps(3, start=0.5, end=1.0)(method)

        instants = method.testing_instants
        self.assertEqual(len(instants), 3)
        for actual, expected in zip(instants, [0.5, 0.75, 1.0]):
            self.assertAlmostEqual(actual, expected)

    def test_last_instant_lands_exactly_on_end(self):
        # Float drift from repeated addition of `step` must not leave
        # the last instant short of (or past) `end`.
        def method(): pass
        method = make_steps(7, start=0.1, end=0.7)(method)

        self.assertAlmostEqual(method.testing_instants[-1], 0.7)

    def test_testing_instant_single_value(self):
        def method(): pass
        method = make_instant(0.3)(method)

        self.assertEqual(method.testing_instants, [0.3])
