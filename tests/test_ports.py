# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Domain-typed ports and the causal connect() binding.

A driver state is a number in the driver's own native unit -- a
stepper counts microsteps, not millimetres -- and the geometry that
consumes it works in design units. Ports are where that conversion is
declared once, next to the mechanism, instead of being open-coded into
every render(). They are kinematic only in this version: no flow
variable (torque, force) exists yet, by design.

The tests assert at operation level rather than through meshes: what a
port binding produces is a translation with a converted value, and the
serialized operation is that fact without an openscad build.
"""

from solid2 import cube

from solid_node.node import (AssemblyNode, RotationalPort, SignalPort,
                             Solid2Node, TranslationalPort)
from solid_node.node.ports import BoundPort, Port, declared_ports
from solid_node.simulation import Driver

from .base import BaseNodeTest


# Millimetres of carriage travel per motor microstep: a 200-step motor
# at 16 microsteps and a 8mm-per-turn leadscrew.
MM_PER_USTEP = 8.0 / (200 * 16)


def translations(node):
    return [op.serialized for op in node.operations
            if op.serialized[0] == 't']


class Motor(Solid2Node):
    """A stepper: its output port carries the shaft position in the
    only unit the motor actually has, whole microsteps."""

    shaft = RotationalPort(out=True, unit='ustep')

    def render(self):
        return cube(4, center=True)


class Carriage(Solid2Node):
    """The driven side: an input port in design units, declaring how
    much travel one microstep of whatever drives it is worth."""

    position = TranslationalPort(unit='mm', scale=MM_PER_USTEP)

    def render(self):
        return cube(6, center=True)


class Gantry(AssemblyNode):
    """Two declared ports of different domains, for the discovery case
    -- a consumer must be able to read both off the class."""

    lift = TranslationalPort(unit='mm', scale=2.0)
    enable = SignalPort()

    def render(self):
        return [Carriage()]


class Axis(AssemblyNode):
    """The whole seam in one render: the motor emits its driver state
    on its output port, connect() converts it into the carriage's
    design units, and the carriage is placed from the converted value.
    Nothing is stored between renders -- every tick rebinds.

    The driver is `usteps`, not `motor`, because `self.motor` is
    already the child node emitting it. A driver is read as an
    attribute of its node, so the two cannot share a name -- the
    declaration would be assigned over in __init__, which is an error
    the driver descriptor raises rather than a shadowing to discover
    later."""

    usteps = Driver(default=0, unit='ustep')

    def __init__(self):
        self.motor = Motor()
        self.carriage = Carriage()
        super().__init__()

    def render(self):
        self.motor.shaft.value = self.usteps
        self.connect(self.motor.shaft, self.carriage.position)
        self.carriage.translate([self.carriage.position.value, 0, 0])
        return [self.motor, self.carriage]


class PortDeclarationTest(BaseNodeTest):

    def test_two_instances_never_share_a_port_value(self):
        one = Motor()
        other = Motor()

        one.shaft.value = 10
        other.shaft.value = 20

        self.assertEqual(one.shaft.value, 10)
        self.assertEqual(other.shaft.value, 20)
        self.assertIsNot(one.shaft, other.shaft)

    def test_an_unbound_port_holds_no_value(self):
        self.assertIsNone(Motor().shaft.value)

    def test_the_same_slot_is_returned_on_every_access(self):
        motor = Motor()
        motor.shaft.value = 7

        self.assertIs(motor.shaft, motor.shaft)
        self.assertEqual(motor.shaft.value, 7)

    def test_declared_ports_are_discoverable_without_instantiating(self):
        ports = declared_ports(Gantry)

        self.assertEqual(sorted(ports), ['enable', 'lift'])
        self.assertEqual(ports['lift'].domain, 'translational')
        self.assertEqual(ports['lift'].unit, 'mm')
        self.assertEqual(ports['lift'].scale, 2.0)
        self.assertFalse(ports['lift'].out)
        self.assertEqual(ports['enable'].domain, 'signal')
        self.assertIsNone(ports['enable'].unit)
        self.assertIsNone(ports['enable'].scale)

    def test_a_declaration_is_readable_off_the_class(self):
        self.assertIsInstance(Motor.shaft, Port)
        self.assertEqual(Motor.shaft.domain, 'rotational')
        self.assertTrue(Motor.shaft.out)

    def test_ports_carry_no_flow_variable(self):
        """Ports are kinematic in this version. A torque/force slot is
        a future spec change, not something to half-provide now."""
        motor = Motor()

        for absent in ('torque', 'force', 'flow'):
            self.assertFalse(hasattr(Motor.shaft, absent))
            self.assertFalse(hasattr(motor.shaft, absent))


class PortConnectionTest(BaseNodeTest):

    def test_microsteps_drive_the_carriage_in_design_units(self):
        axis = Axis()

        axis.set_state(usteps=4000)

        self.assertEqual(axis.motor.shaft.value, 4000)
        self.assertEqual(axis.carriage.position.value, 10.0)
        self.assertEqual(translations(axis.carriage),
                         [['t', ['10.0', '0', '0']]])

    def test_rebinding_is_absolute_across_renders(self):
        axis = Axis()

        axis.set_state(usteps=4000)
        axis.set_state(usteps=1000)

        self.assertEqual(axis.motor.shaft.value, 1000)
        self.assertEqual(axis.carriage.position.value, 2.5)
        # One translation, holding this snapshot's value only: no
        # residue of the previous render anywhere.
        self.assertEqual(translations(axis.carriage),
                         [['t', ['2.5', '0', '0']]])

    def test_a_plain_number_can_drive_a_sink(self):
        axis = Axis()

        axis.connect(2000, axis.carriage.position)

        self.assertEqual(axis.carriage.position.value, 5.0)

    def test_a_sink_without_a_scale_takes_the_source_value(self):
        gantry = Gantry()
        motor = Motor()
        motor.shaft.value = 3

        gantry.connect(motor.shaft, gantry.enable)

        self.assertEqual(gantry.enable.value, 3)


class AssignedAxis(AssemblyNode):
    """The same seam as Axis, bound by assignment: the sink's scale
    applies exactly as it does through connect()."""

    usteps = Driver(default=0, unit='ustep')

    def __init__(self):
        self.motor = Motor()
        self.carriage = Carriage()
        super().__init__()

    def render(self):
        self.motor.shaft = self.usteps
        self.carriage.position = self.motor.shaft.value
        self.carriage.translate([self.carriage.position.value, 0, 0])
        return [self.motor, self.carriage]


class PortAssignmentTest(BaseNodeTest):

    def test_assignment_binds_with_scale(self):
        carriage = Carriage()

        carriage.position = 4000

        self.assertIsInstance(carriage.position, BoundPort)
        self.assertEqual(carriage.position.value, 10.0)

    def test_assignment_never_shadows_the_declaration(self):
        motor = Motor()

        motor.shaft = 90

        self.assertNotIn('shaft', vars(motor))
        self.assertIsInstance(motor.shaft, BoundPort)
        self.assertEqual(motor.shaft.value, 90)
        self.assertIsInstance(Motor.shaft, Port)

    def test_assignment_in_a_render_rebinds_absolutely(self):
        axis = AssignedAxis()

        axis.set_state(usteps=4000)
        axis.set_state(usteps=1000)

        self.assertEqual(axis.carriage.position.value, 2.5)
        self.assertEqual(translations(axis.carriage),
                         [['t', ['2.5', '0', '0']]])
