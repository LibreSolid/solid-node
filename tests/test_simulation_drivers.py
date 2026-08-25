# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Driver declarations, per-simulation state, and ramp programs.

A driver is the only holder of simulation state, and the spike
(spike/FINDINGS.md seam 2) showed what happens when the declaration
holds it: driver instances live as class attributes, so every node of
that class shares one value and the loop has to reset() its way out.
These tests pin the split instead -- the declaration is frozen class
metadata, the state is built per simulation -- and pin the integer
arithmetic that makes a stepped trajectory comparable with `==`.

Nothing here builds a mesh: what a declaration, a state bank and a ramp
produce is numbers, and an STL would only make the suite slower without
answering a single question asked below.
"""

from solid_node.node import AssemblyNode
from solid_node.simulation import Driver, RampProgram
from solid_node.simulation.driver import declared_drivers, driver_states

from .base import BaseNodeTest
from .meta_project.parts import Cube


# GT2 belt on a 20-tooth pulley: 40mm/rev over 200 steps x 16 microsteps.
MM_PER_USTEP = 40.0 / (200 * 16)


class Axis(AssemblyNode):
    """One discrete driver and one continuous one: the stepper counts
    whole microsteps and declares what a microstep is worth in design
    units, while the lift is millimetres all the way down."""

    motor = Driver(default=8000, range=(0, 19200), unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)
    lift = Driver(default=2.5, unit='mm')

    def __init__(self):
        self.cube = Cube()
        super().__init__()

    def render(self):
        self.cube.translate([self.state['motor'] * MM_PER_USTEP, 0,
                             self.state['lift']])
        return [self.cube]


class LongAxis(Axis):
    """A subclass redeclaring an inherited driver: the base-first walk
    must let this one win without disturbing the base class."""

    motor = Driver(default=0, range=(0, 38400), unit='ustep', dtype=int,
                   scale=MM_PER_USTEP)


class DriverDeclarationTest(BaseNodeTest):

    def test_declared_drivers_are_discoverable_without_instantiating(self):
        drivers = declared_drivers(Axis)

        self.assertEqual(sorted(drivers), ['lift', 'motor'])
        self.assertEqual(drivers['motor'].default, 8000)
        self.assertEqual(drivers['motor'].range, (0, 19200))
        self.assertEqual(drivers['motor'].unit, 'ustep')
        self.assertIs(drivers['motor'].dtype, int)
        self.assertEqual(drivers['motor'].scale, MM_PER_USTEP)
        self.assertEqual(drivers['lift'].default, 2.5)
        self.assertIsNone(drivers['lift'].range)
        self.assertIsNone(drivers['lift'].dtype)
        self.assertIsNone(drivers['lift'].scale)

    def test_a_subclass_redeclaration_wins_and_leaves_the_base_alone(self):
        self.assertEqual(declared_drivers(LongAxis)['motor'].default, 0)
        self.assertEqual(declared_drivers(LongAxis)['motor'].range, (0, 38400))
        self.assertEqual(declared_drivers(Axis)['motor'].default, 8000)

    def test_a_declaration_holds_no_mutable_state(self):
        declaration = declared_drivers(Axis)['motor']

        with self.assertRaises(Exception):
            declaration.default = 0

        self.assertFalse(hasattr(declaration, 'value'))
        self.assertFalse(hasattr(declaration, 'program'))

    def test_an_integer_driver_rejects_a_fractional_default(self):
        with self.assertRaises(TypeError):
            Driver(default=0.5, dtype=int)

    def test_a_design_unit_target_converts_through_the_declared_scale(self):
        motor = declared_drivers(Axis)['motor']

        self.assertEqual(motor.native(0.0), 0)
        self.assertEqual(motor.native(100.0), 8000)
        # Rounded once, to a whole microstep: 0.02mm is 1.6 microsteps
        # and no state between two microsteps exists on the machine.
        self.assertEqual(motor.native(0.02), 2)

    def test_a_driver_without_a_scale_takes_the_target_verbatim(self):
        self.assertEqual(declared_drivers(Axis)['lift'].native(1.25), 1.25)


class DriverStateTest(BaseNodeTest):

    def test_state_starts_at_the_declared_default(self):
        states = driver_states(Axis)

        self.assertEqual(states['motor'].value, 8000)
        self.assertEqual(states['lift'].value, 2.5)

    def test_two_state_banks_of_one_class_never_share_a_value(self):
        one = driver_states(Axis)
        other = driver_states(Axis)

        one['motor'].ramp_to(0, 100, 0)
        for tick in range(1, 101):
            one['motor'].advance(tick)

        self.assertEqual(one['motor'].value, 0)
        self.assertEqual(other['motor'].value, 8000)
        self.assertEqual(declared_drivers(Axis)['motor'].default, 8000)

    def test_a_driver_with_no_program_holds_its_state(self):
        states = driver_states(Axis)

        for tick in range(1, 11):
            states['lift'].advance(tick)

        self.assertEqual(states['lift'].value, 2.5)

    def test_a_completed_program_is_dropped(self):
        state = driver_states(Axis)['motor']
        state.ramp_to(0, 10, 0)

        for tick in range(1, 11):
            state.advance(tick)

        self.assertIsNone(state.program)
        self.assertEqual(state.value, 0)


class RampProgramTest(BaseNodeTest):

    def test_an_integer_ramp_lands_exactly_on_whole_steps(self):
        ramp = RampProgram(8000, 0, 100, dtype=int)

        values = [ramp.value_at(k) for k in range(101)]

        self.assertEqual(values[0], 8000)
        self.assertEqual(values[100], 0)
        self.assertTrue(all(type(value) is int for value in values))

    def test_an_indivisible_integer_ramp_still_lands_exactly(self):
        ramp = RampProgram(0, 7, 3, dtype=int)

        self.assertEqual([ramp.value_at(k) for k in range(4)], [0, 2, 4, 7])

    def test_a_float_ramp_lands_exactly_on_its_target(self):
        ramp = RampProgram(0.0, 2.5, 5)

        self.assertEqual([ramp.value_at(k) for k in range(6)],
                         [0.0, 0.5, 1.0, 1.5, 2.0, 2.5])

    def test_a_ramp_holds_its_target_past_completion(self):
        ramp = RampProgram(8000, 0, 100, dtype=int)

        self.assertEqual(ramp.value_at(140), 0)

    def test_a_zero_tick_ramp_arrives_immediately(self):
        self.assertEqual(RampProgram(10, 20, 0, dtype=int).value_at(0), 20)

    def test_the_same_ramp_produces_the_same_values_every_time(self):
        first = [RampProgram(8000, 0, 100, dtype=int).value_at(k)
                 for k in range(101)]
        second = [RampProgram(8000, 0, 100, dtype=int).value_at(k)
                  for k in range(101)]

        self.assertEqual(first, second)
