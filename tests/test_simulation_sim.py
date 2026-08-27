# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Instructions and the fixed-dt stepping loop.

The loop is what turns declarations into the snapshots the node layer
binds. Two properties are worth more than the rest and are pinned
hardest here: an instant is an integer tick count, never an
accumulated float, so a scenario written in seconds lands on the tick
it names or fails saying why; and a scheduled action is a DEFERRED
callable, because the ADR's original sketch --
`sim.at(2.5).assertEqual(sim.state['x'], 0)` -- evaluates its
arguments at registration time and asserts on the wrong instant
(spike/FINDINGS.md seam 3).

The instruction cases are the other spike seam: a maker states a
target in millimetres and the microstep driver has to receive whole
microsteps, converted once through the driver's declared scale.

These tests step real assemblies but build no meshes -- what a tick
produces is a snapshot, and the assertions here are about the
snapshot. Geometry is the scenario tests' subject.
"""

from solid_node.node import AssemblyNode
from solid_node.simulation import Driver, Instruction, Sim

from .base import BaseNodeTest
from .meta_project.machine import Machine
from .meta_project.parts import Cube


# GT2 belt on a 20-tooth pulley: 40mm/rev over 200 steps x 16 microsteps.
MM_PER_USTEP = 40.0 / (200 * 16)
DT = 0.02


class Carriage(AssemblyNode):
    """A microstep-counting axis with a home instruction stated, as a
    maker would state it, in millimetres."""

    # DESIGN-unit travel (240mm) beside native state, as ADR-056 stage
    # 3c pins it; the instruction targets below read the same way.
    motor = Driver(default=8000, range=(0, 240.0), unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)

    instructions = {
        'Home X': Instruction({'motor': 0.0}, duration=2.0),
        'Park X': Instruction({'motor': 50.0}, duration=2.0),
    }

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        self.cube.translate([self.motor * MM_PER_USTEP, 0, 0])
        return [self.cube]


def homing(sim):
    sim.at(0.0).trigger('Home X')
    sim.run(3.0)
    return sim


class SimConstructionTest(BaseNodeTest):

    def test_defaults_bind_before_the_first_render(self):
        node = Carriage()

        sim = Sim(node, DT)

        self.assertEqual(sim.state, {'motor': 8000})
        self.assertEqual(node.motor, 8000)
        self.assertEqual([op.serialized for op in node.cube.operations],
                         [['t', ['100.0', '0', '0']]])

    def test_two_simulations_of_one_class_stay_independent(self):
        first = Sim(Carriage(), DT)
        second = Sim(Carriage(), DT)

        first.at(0.0).trigger('Home X')
        first.run(1.0)
        second.at(0.0).trigger('Park X')
        second.run(1.0)

        self.assertEqual(first.state, {'motor': 4000})
        self.assertEqual(second.state, {'motor': 6000})
        self.assertNotEqual(first.trajectory, second.trajectory)
        self.assertEqual(Carriage.motor.default, 8000)

    def test_two_fresh_runs_compare_exactly_equal(self):
        first = homing(Sim(Carriage(), DT))
        second = homing(Sim(Carriage(), DT))

        self.assertEqual(len(first.trajectory), 150)
        self.assertEqual(first.trajectory, second.trajectory)

    def test_the_trajectory_records_every_tick(self):
        sim = homing(Sim(Carriage(), DT))

        self.assertEqual([tick for tick, _ in sim.trajectory],
                         list(range(1, 151)))
        self.assertEqual(sim.trajectory[0], (1, {'motor': 7920}))
        self.assertEqual(sim.trajectory[99], (100, {'motor': 0}))


class InstantValidationTest(BaseNodeTest):

    def test_a_non_whole_instant_is_rejected(self):
        sim = Sim(Carriage(), DT)

        with self.assertRaises(ValueError) as caught:
            sim.at(0.05)

        message = str(caught.exception)
        self.assertIn('0.05', message)
        self.assertIn('0.02', message)

    def test_a_non_whole_cadence_period_is_rejected(self):
        sim = Sim(Carriage(), DT)

        with self.assertRaises(ValueError) as caught:
            sim.every(0.05, lambda: None)

        self.assertIn('0.05', str(caught.exception))

    def test_a_whole_instant_of_an_awkward_dt_is_accepted(self):
        # 0.3/0.1 is 2.9999999999999996 in binary floating point: the
        # tolerance is what keeps a scenario written in round seconds
        # from being rejected for the arithmetic it never chose.
        sim = Sim(Carriage(), 0.1)
        seen = []

        sim.at(0.3).run(lambda s: seen.append(s.tick))
        sim.run(0.5)

        self.assertEqual(seen, [3])


class DeferredActionTest(BaseNodeTest):

    def test_a_deferred_action_runs_once_and_sees_the_stepped_state(self):
        sim = Sim(Carriage(), DT)
        seen = []

        sim.at(0.0).trigger('Home X')
        sim.at(0.5).run(lambda s: seen.append((s.tick, s.state['motor'])))
        sim.run(3.0)

        self.assertEqual(seen, [(25, 6000)])

    def test_an_action_sees_the_state_after_that_ticks_binding(self):
        sim = Sim(Carriage(), DT)
        seen = []

        sim.at(0.0).trigger('Home X')
        sim.at(2.0).run(lambda s: seen.append(s.node.motor))
        sim.run(3.0)

        self.assertEqual(seen, [0])

    def test_a_trigger_starts_the_ramp_at_its_own_tick(self):
        sim = Sim(Carriage(), DT)

        sim.at(1.0).trigger('Home X')
        sim.run(1.0)
        held = sim.state['motor']
        sim.run(2.0)

        self.assertEqual(held, 8000)
        self.assertEqual(sim.trajectory[50], (51, {'motor': 7920}))
        self.assertEqual(sim.state['motor'], 0)

    def test_an_unknown_instruction_is_reported_by_name(self):
        sim = Sim(Carriage(), DT)

        with self.assertRaises(KeyError) as caught:
            sim.trigger('Home Y')

        self.assertIn('Home Y', str(caught.exception))
        self.assertIn('Home X', str(caught.exception))


class CadenceTest(BaseNodeTest):

    def test_a_cadence_runs_at_its_own_ticks(self):
        sim = Sim(Carriage(), DT)
        ticks = []

        sim.every(0.1, lambda: ticks.append(sim.tick))
        sim.run(1.0)

        self.assertEqual(ticks, [5, 10, 15, 20, 25, 30, 35, 40, 45, 50])

    def test_a_cadence_action_receives_its_declared_arguments(self):
        sim = Sim(Carriage(), DT)
        seen = []

        sim.every(0.5, seen.append, 'checked')
        sim.run(1.0)

        self.assertEqual(seen, ['checked', 'checked'])

    def test_cost_is_accounted_per_slot(self):
        sim = Sim(Carriage(), DT)

        sim.every(0.1, lambda: None)
        sim.every(0.5, lambda: None)
        sim.run(1.0)

        costs = sim.cadence_costs
        self.assertEqual([cost.period_ticks for cost in costs], [5, 25])
        self.assertEqual([cost.calls for cost in costs], [10, 2])
        self.assertTrue(all(cost.seconds >= 0 for cost in costs))
        self.assertEqual(sim.assertion_stats[0], 12)

    def test_a_period_shorter_than_a_tick_is_rejected(self):
        sim = Sim(Carriage(), DT)

        with self.assertRaises(ValueError) as caught:
            sim.every(0.0, lambda: None)

        self.assertIn('0.02', str(caught.exception))

    def test_a_failing_cadence_assertion_stops_the_run(self):
        sim = Sim(Carriage(), DT)

        def check():
            raise AssertionError('interference')

        sim.every(0.1, check)

        with self.assertRaises(AssertionError):
            sim.run(1.0)

        self.assertEqual(sim.tick, 5)


class InstructionTest(BaseNodeTest):

    def test_a_millimetre_target_reaches_an_integer_microstep_driver(self):
        sim = homing(Sim(Carriage(), DT))

        self.assertEqual(sim.state['motor'], 0)
        self.assertTrue(all(type(states['motor']) is int
                            for _, states in sim.trajectory))

    def test_a_ramp_lands_on_the_converted_target(self):
        sim = Sim(Carriage(), DT)

        sim.at(0.0).trigger('Park X')
        sim.run(2.0)

        self.assertEqual(sim.state['motor'], 4000)
        self.assertEqual(sim.node.motor, 4000)

    def test_an_instruction_targeting_an_undeclared_driver_is_reported(self):
        class Broken(Carriage):
            instructions = {'Bad': Instruction({'spindle': 1.0}, duration=1.0)}

        sim = Sim(Broken(), DT)

        with self.assertRaises(KeyError) as caught:
            sim.trigger('Bad')

        self.assertIn('spindle', str(caught.exception))


class QualifiedSimTest(BaseNodeTest):
    """A machine whose drivers live only on duplicated children: the
    root declares nothing, so a root-class-only bank would be empty and
    the very first render would fail on an unbound driver."""

    def test_a_driverless_root_with_declaring_children_simulates(self):
        machine = Machine()

        sim = Sim(machine, DT)

        self.assertEqual(sim.state,
                         {'x_axis.motor': 8000, 'y_axis.motor': 8000})
        self.assertEqual(machine.x_axis.motor, 8000)

    def test_stepping_addresses_each_instance_independently(self):
        machine = Machine()
        sim = Sim(machine, DT)

        sim.drivers['x_axis.motor'].ramp_to(0, 10, 0)
        sim.run(10 * DT)

        self.assertEqual(sim.state,
                         {'x_axis.motor': 0, 'y_axis.motor': 8000})
        self.assertEqual(machine.x_axis.motor, 0)
        self.assertEqual(machine.y_axis.motor, 8000)

    def test_the_trajectory_is_keyed_by_qualified_id(self):
        sim = Sim(Machine(), DT)

        sim.run(2 * DT)

        tick, states = sim.trajectory[-1]
        self.assertEqual(tick, 2)
        self.assertEqual(sorted(states), ['x_axis.motor', 'y_axis.motor'])


class QualifiedInstructionTest(BaseNodeTest):

    def test_a_childs_instruction_homes_only_that_child(self):
        machine = Machine()
        sim = Sim(machine, DT)

        sim.at(0.0).trigger('x_axis.Home')
        sim.run(2.0)

        self.assertEqual(sim.state['x_axis.motor'], 0)
        self.assertEqual(sim.state['y_axis.motor'], 8000)

    def test_an_unknown_trigger_lists_the_known_qualified_names(self):
        sim = Sim(Machine(), DT)

        with self.assertRaises(KeyError) as caught:
            sim.trigger('Home')

        message = str(caught.exception)
        self.assertIn('x_axis.Home', message)
        self.assertIn('y_axis.Home', message)

    def test_a_root_declared_instruction_keeps_its_bare_name(self):
        sim = Sim(Carriage(), DT)

        sim.at(0.0).trigger('Home X')
        sim.run(2.0)

        self.assertEqual(sim.state['motor'], 0)


class SimulationClockTest(BaseNodeTest):
    """`time` is one driver among the rest, and under a simulation it is
    the stepped clock in SECONDS -- not the normalized 0..1 `$t` an
    animation sweeps, which a machine executing instructions has no
    period to normalize against."""

    def test_each_tick_binds_the_exact_instant(self):
        node = Carriage()
        sim = Sim(node, DT)

        sim.run(2.5)

        self.assertEqual(sim.tick, 125)
        self.assertEqual(node.time, 2.5)

    def test_a_deferred_action_reads_the_simulation_clock(self):
        node = Carriage()
        sim = Sim(node, DT)
        seen = []

        sim.at(2.5).run(lambda s: seen.append(s.node.time))
        sim.run(3.0)

        self.assertEqual(seen, [2.5])

    def test_the_clock_is_computed_from_the_tick_count_not_accumulated(self):
        node = Carriage()
        sim = Sim(node, DT)

        sim.run(1.0)

        self.assertEqual(node.time, 50 * DT)
        self.assertEqual([tick for tick, _ in sim.trajectory][-1], 50)

    def test_construction_opens_the_clock_at_zero(self):
        node = Carriage()

        Sim(node, DT)

        self.assertEqual(node.time, 0.0)

    def test_symbolic_time_returns_after_the_run(self):
        node = Carriage()
        sim = Sim(node, DT)
        sim.run(1.0)

        node.clear_keyframe()

        self.assertEqual(str(node.time), '$t')
