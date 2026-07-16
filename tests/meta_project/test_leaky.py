# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node.operations import Translation
from solid_node.test import TestCase, testing_steps


def leak(cube):
    """Append an operation WITHOUT cleaning it up — simulating a test
    that raises before its perturbation context manager exits, or one
    that simply forgets."""
    cube.operations.append(Translation([1, 0, 0], cube))


class LeakyTest(TestCase):
    """The runner must isolate state between tests AND between the
    instants of one test; a leaked operation or a clobbered checkpoint
    in one place must never poison a later assertion. Methods run in
    alphabetical order: test_a leaks and clobbers, test_b and test_c
    must not see any of it."""

    def test_a_leaks_and_clobbers_checkpoint(self):
        cube = self.leaky.cube
        leak(cube)
        # After the leak, save_checkpoint — a runner trusting the
        # node's own checkpoint index would now restore to a state
        # that INCLUDES the leaked operation.
        cube.save_checkpoint()

    def test_b_starts_clean_after_leaky_test(self):
        self.assertEqual(len(self.leaky.cube.operations), 0)

    @testing_steps(2, start=0, end=1)
    def test_c_each_instant_starts_clean(self):
        cube = self.leaky.cube
        self.assertEqual(len(cube.operations), 0)
        leak(cube)
