# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Instance-qualified driver identity and the symbolic driver token.

A driver name is class-local, so two instances of one class collide in
every flat namespace that has to address a driver: the serialized
document, the simulation bank, `set_state`. The cure is an id derived
from the node's position in the LINKED tree -- `x_axis.motor` -- and a
token whose string IS that id, so ordinary solid2 arithmetic and
`solid_node.math`'s degree trig build the wire expression for free.

Nothing here is stored on a node: the id is computed from the
parent-derived names `_link_child` assigns, which is why a walk that
has not linked cannot qualify and must say so instead of falling back
to the bare local name (which is exactly the silent collision this
change exists to remove).
"""

import solid_node.math as sn_math
from solid_node.node.qualified import (
    DriverIdError, DriverToken, declared_drivers_of, driver_id,
    drive_tree, instance_path,
)

from .base import BaseNodeTest
from .meta_project.machine import Axis, ListMachine, Machine


class QualifiedIdTest(BaseNodeTest):

    def test_two_instances_of_one_class_qualify_distinctly(self):
        """Red before the change: `instance_path` does not exist, and
        the only name either instance answers to is the class name."""
        machine = Machine()
        found = drive_tree(machine, lambda node, path, name, declaration:
                           declaration.default)

        self.assertEqual(sorted(found), ['x_axis.motor', 'y_axis.motor'])
        self.assertEqual(instance_path(machine.x_axis, machine), ('x_axis',))
        self.assertEqual(instance_path(machine, machine), ())

    def test_a_root_declared_driver_keeps_its_bare_name(self):
        axis = Axis('x')
        found = drive_tree(axis, lambda node, path, name, declaration:
                           declaration.default)

        self.assertEqual(sorted(found), ['motor'])
        self.assertEqual(driver_id((), 'motor'), 'motor')

    def test_qualifying_an_unlinked_node_fails_loudly(self):
        """A child whose parent never linked it has no derived name, so
        its id is not computable. Falling back to the bare name is the
        silent collision, so this raises instead."""
        machine = Machine()

        with self.assertRaises(DriverIdError) as caught:
            instance_path(machine.x_axis, machine)

        message = str(caught.exception)
        self.assertIn('Axis', message)
        self.assertIn('linked', message)

    def test_an_illegal_id_segment_fails_loudly(self):
        """`axes-0` is a legal NODE name and an illegal identifier: the
        id would parse as a subtraction in both target runtimes."""
        machine = ListMachine()

        with self.assertRaises(DriverIdError) as caught:
            drive_tree(machine, lambda node, path, name, declaration:
                       declaration.default)

        message = str(caught.exception)
        self.assertIn('axes-0', message)
        self.assertIn('motor', message)

    def test_an_illegal_segment_is_never_sanitized(self):
        with self.assertRaises(DriverIdError):
            driver_id(('axes-0',), 'motor')

    def test_declarations_are_read_off_the_class(self):
        self.assertEqual(sorted(declared_drivers_of(Axis)), ['motor'])
        self.assertEqual(declared_drivers_of(Machine), {})


class DriverTokenTest(BaseNodeTest):
    """The six expression shapes the spike put on the wire: linear,
    port-scaled, degree trig, mixed with `$t`, a power term, and a sum
    whose leading term is negative."""

    def token(self):
        return DriverToken('x_axis.motor')

    def test_the_token_stringifies_as_the_qualified_id(self):
        self.assertEqual(str(self.token()), 'x_axis.motor')

    def test_linear_arithmetic_rides_solid2(self):
        self.assertEqual(str(self.token() * 0.1125), '(x_axis.motor * 0.1125)')

    def test_symbolic_degree_trig_accepts_the_token(self):
        angle = self.token() * 0.1125
        self.assertEqual(str(sn_math.asin(0.25 * sn_math.sin(angle))),
                         'asin((0.25 * sin((x_axis.motor * 0.1125))))')

    def test_a_power_term_serializes_openscad_exponentiation(self):
        angle = self.token() * 0.1125
        self.assertEqual(
            str(sn_math.sqrt(400.0 - (0.01 * angle) ** 2)),
            'sqrt((400.0 - ((0.01 * (x_axis.motor * 0.1125)) ^ 2)))')

    def test_a_leading_negative_term_is_written_as_the_sum_it_is(self):
        """A placement measured from a rest on the far side of the
        origin, which is how a negative literal comes to head a sum.

        Written plainly, because that is what the arithmetic is: the
        minus belongs to the twenty-five and not to the sum. Pinned on
        the producer's side because it is the producer that decides
        what a reader has to read, and a reader that binds the unary
        looser than the `+` returns `-(25.0 + term)` -- the same value
        at one driver setting and the wrong sign of the coefficient at
        every other.
        """
        self.assertEqual(str(-25.0 + self.token() * 0.0125),
                         '(-25.0 + (x_axis.motor * 0.0125))')

    def test_a_mixed_expression_carries_both_time_and_the_driver(self):
        from solid2 import get_animation_time
        mixed = 5.0 * sn_math.cos(360.0 * get_animation_time()) + \
            self.token() * 0.0125
        self.assertEqual(
            str(mixed),
            '((5.0 * cos((360.0 * $t))) + (x_axis.motor * 0.0125))')

    def test_a_bound_token_renders_qualified_expressions(self):
        """The end-to-end shape: tokens bound across a linked tree make
        every driven operation serialize its own instance's id."""
        machine = Machine()
        drive_tree(machine, lambda node, path, name, declaration:
                   DriverToken(driver_id(path, name)))

        self.assertEqual(
            [op.serialized for op in machine.x_axis.carriage.operations],
            [['t', ['(x_axis.motor * 0.0125)', '0', '0']]])
        self.assertEqual(
            [op.serialized for op in machine.y_axis.pulley.operations],
            [['r', '(y_axis.motor * 0.1125)', [0, 0, 1]]])
