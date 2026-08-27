# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Reading a declared driver off the node that declares it.

A driver is class metadata, exactly as a port is, and a port is read
`self.position` because `Port` is a descriptor. This makes the driver
read match: `x = Driver(...)` is read `self.x`, and that is the only
way to read it -- the `state` mapping the seam shipped with is gone,
so there is one surface and no string key to mistype.

The three failures this creates or keeps are all loud, and each is
tested here: reading an unbound driver, assigning to a driver, and
declaring one under a name the node class already carries. The last is
new. A driver name used to be confined to a mapping key and could
collide with nothing; now it lands in the node's attribute namespace,
where `render`, `color`, `mesh` and thirty-odd others already live,
and a collision would be silent.
"""

from solid_node.core.serializer import symbolic_drivers
from solid_node.node import AssemblyNode
from solid_node.node.qualified import DriverToken, declared_drivers_of
from solid_node.simulation import Driver

from .base import BaseNodeTest
from .meta_project.machine import Machine as QualifiedMachine
from .meta_project.parts import Cube


MM_PER_USTEP = 40.0 / (200 * 16)


class Lift(AssemblyNode):
    """One declared driver, read as an attribute by the render that
    depends on it."""

    height = Driver(default=0.0, unit='mm')

    def __init__(self, *args, **kwargs):
        self.platform = Cube(size=2.0)
        super().__init__(*args, **kwargs)

    def render(self):
        self.platform.translate([0, 0, self.height])
        return [self.platform]


class TallLift(Lift):
    """A subclass redeclaring an inherited driver: legal, and the
    subclass's declaration is the one discovery finds."""

    height = Driver(default=100.0, unit='mm')


class IdleLift(AssemblyNode):
    """Declares a driver its render never reads, so the snapshot can
    be cleared and inspected -- a render that CONSUMES a driver raises
    the moment clear_state re-renders it, which is the loud-unbound
    contract doing its job rather than something to test around."""

    height = Driver(default=0.0, unit='mm')

    def __init__(self, *args, **kwargs):
        self.platform = Cube(size=2.0)
        super().__init__(*args, **kwargs)

    def render(self):
        return [self.platform]


def translations(node):
    return [op.serialized for op in node.operations
            if op.serialized[0] == 't']


class DriverAttributeReadTest(BaseNodeTest):

    def test_declared_driver_reads_as_an_attribute(self):
        lift = Lift()
        lift.set_state(height=12.5)

        self.assertEqual(lift.height, 12.5)
        self.assertEqual(translations(lift.platform),
                         [['t', ['0', '0', '12.5']]])

    def test_rebinding_moves_the_pose_absolutely(self):
        lift = Lift()
        lift.set_state(height=12.5)
        lift.set_state(height=-3.0)

        self.assertEqual(lift.height, -3.0)
        self.assertEqual(translations(lift.platform),
                         [['t', ['0', '0', '-3.0']]])

    def test_sibling_instances_read_their_own_value(self):
        machine = QualifiedMachine()
        machine.set_state(**{'x_axis.motor': 8000,
                             'y_axis.motor': 2000,
                             'time': 0.0})

        self.assertEqual(machine.x_axis.motor, 8000)
        self.assertEqual(machine.y_axis.motor, 2000)

    def test_class_access_returns_the_declaration(self):
        self.assertIsInstance(Lift.height, Driver)
        self.assertEqual(Lift.height.default, 0.0)
        self.assertEqual(Lift.height.unit, 'mm')

    def test_declaration_discovery_is_unaffected(self):
        self.assertEqual(list(declared_drivers_of(Lift)), ['height'])
        self.assertIs(declared_drivers_of(Lift)['height'], Lift.height)

    def test_redeclaring_an_inherited_driver_wins_discovery(self):
        self.assertEqual(declared_drivers_of(TallLift)['height'].default,
                         100.0)
        self.assertIs(declared_drivers_of(TallLift)['height'],
                      TallLift.height)


class SymbolicAttributeReadTest(BaseNodeTest):

    def test_attribute_read_yields_the_token_and_reverts(self):
        machine = QualifiedMachine()
        machine.set_state(**{'x_axis.motor': 8000,
                             'y_axis.motor': 2000,
                             'time': 0.0})

        with symbolic_drivers(machine):
            token = machine.x_axis.motor
            self.assertIsInstance(token, DriverToken)
            self.assertEqual(str(token), 'x_axis.motor')

        self.assertEqual(machine.x_axis.motor, 8000)
        self.assertEqual(machine.y_axis.motor, 2000)


class UnboundDriverTest(BaseNodeTest):

    def test_unbound_read_names_the_driver_and_set_state(self):
        lift = Lift()

        with self.assertRaises(AttributeError) as caught:
            lift.height

        message = str(caught.exception)
        self.assertIn('height', message)
        self.assertIn('set_state', message)

    def test_clearing_state_makes_the_driver_unbound_again(self):
        lift = IdleLift()
        lift.set_state(height=4.0)
        self.assertEqual(lift.height, 4.0)

        lift.clear_state()

        with self.assertRaises(AttributeError):
            lift.height


class DriverAssignmentTest(BaseNodeTest):

    def test_assigning_a_driver_names_the_driver_and_set_state(self):
        lift = Lift()
        lift.set_state(height=4.0)

        with self.assertRaises(AttributeError) as caught:
            lift.height = 9.0

        message = str(caught.exception)
        self.assertIn('height', message)
        self.assertIn('set_state', message)
        self.assertEqual(lift.height, 4.0)


class ShadowingDeclarationTest(BaseNodeTest):

    def test_a_driver_shadowing_a_node_member_is_rejected(self):
        with self.assertRaises(TypeError) as caught:
            class Shadow(AssemblyNode):
                render = Driver(default=0.0)

        message = str(caught.exception)
        self.assertIn('render', message)

    def test_the_guard_names_the_time_collision_too(self):
        with self.assertRaises(TypeError) as caught:
            class Clock(AssemblyNode):
                time = Driver(default=0.0)

        self.assertIn('time', str(caught.exception))
