# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Scenario tests for the driven axis fixture.

This class is the portability claim of the scenario layer, which is
why it lives here rather than beside the framework's other tests: it
is a companion test of a node file, so `solid test tests/meta_project/
axis.py` runs it through the CLI, the loader, the builder and the
runner -- and tests/test_simulation_scenario.py imports this same
class so pytest runs it too. Neither runner is modified for it, and
nothing in it is written for one runner or the other.
"""

from solid_node.simulation import ScenarioTest

from .axis import Axis


class AxisScenarioTest(ScenarioTest):
    node = Axis
    dt = 0.02
    meshes = True

    def test_homing_stays_clear_of_the_stop(self):
        """The SCOPE scenario: home at t=0, check interference at a
        0.1s cadence, check the terminal state at t=2.5, run 3.0s."""
        sim = self.simulation()
        arrived = []

        sim.at(0.0).trigger('Home')
        sim.every(0.1, self.assertNoSolidInterference, self.node)
        sim.at(2.5).run(lambda s: arrived.append(s.state['x']))
        sim.run(3.0)

        self.assertEqual(arrived, [0])
        self.assertEqual(sim.assertion_stats[0], 30)
        self.assertAlmostEqual(self.node.carriage.mesh.center_mass[0], 6.0,
                               delta=0.01)

    def test_a_crash_is_caught_at_the_tick_it_appears(self):
        """The teeth of the scenario above: the same cadence assertion
        over an instruction that drives the carriage into the stop must
        stop the run, or the homing scenario proves nothing."""
        sim = self.simulation()

        sim.at(0.0).trigger('Crash')
        sim.every(0.1, self.assertNoSolidInterference, self.node)

        with self.assertRaises(AssertionError) as caught:
            sim.run(3.0)

        self.assertIn('should not interfere', str(caught.exception))
        # 1mm of clearance and 0.15mm of travel per tick: the carriage
        # first shares volume with the stop at tick 74, and the first
        # cadence check at or after that tick is the 75th.
        self.assertEqual(sim.tick, 75)

    def test_each_scenario_starts_from_the_declared_defaults(self):
        sim = self.simulation()

        self.assertEqual(sim.state, {'x': 800})
        self.assertEqual(self.node.x, 800)
