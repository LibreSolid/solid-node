# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The one-coordinate lower pairs: `Revolute` and `Prismatic`.

A joint says WHERE a body may move, next to the body, once. Its axis and
anchor are stated in the frame its parent places it in -- the frame
MuJoCo and Modelica state them in -- and the framework carries them into
the node's own frame by inverting the rest placement, which is the
arithmetic every arm in the catalogue writes by hand today.

Thor is the evidence and the pinned number: `simulation/placing.py` and
`art2.py` carry the elbow into the forearm's frame with
`ELBOW_PIVOT_AXIS = (0, 1, 0)` and `ELBOW_PIVOT = (0, 0, 81.5)`, and the
fixture in `tests/joint_project/` declares the same joint in the
parent's frame. If the two ever disagree, this file says so.

The assertions are at operation and document level rather than through
meshes: what a joint produces is ordinary rotations and translations
with possibly symbolic values, and the serialized operation is that fact
without an openscad build.
"""

import math
from unittest import TestCase

import numpy as np
from numpy.testing import assert_allclose
from solid2 import cube

from solid_node.motion.joints import (Joint, JointRangeError, Prismatic,
                                      Revolute, declared_joints)
from solid_node.motion.ports import (BoundPort, Port, RotationalPort,
                                     TranslationalPort, declared_ports)
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.node import phase as _phase
from solid_node.node.base import _compose_world_matrix
from solid_node.node.assembly import _sweep
from solid_node.core.serializer import serialize_node
from solid_node.parameters import Count, Length, ParameterError
from solid_node.simulation import Driver

from .base import BaseNodeTest
from .import_probe import probe
from .joint_project.arm import (Arbor, ArborStack, Arm, Forearm, Gantry,
                                BEARING_PITCH)
from .joint_project.parts import Carriage, Rod, Spool, Wheel


# What Thor's own placing.py computes by hand for the elbow, quoted so a
# disagreement between the project and the framework is visible here.
THOR_ELBOW_PIVOT_AXIS = (0, 1, 0)
THOR_ELBOW_PIVOT = (0, 0, 81.5)


def serialized(node):
    return [operation.serialized for operation in node.operations]


def motions(node):
    return [operation for operation in node.operations
            if getattr(operation, '_motion', False)]


def numbers(serialized_translation):
    return [float(component) for component in serialized_translation[1]]


class Hinge(Solid2Node):
    """The smallest joint declaration: plain numbers, no parameters."""

    swing = Revolute(axis=(0, 0, 1), at=(0, 10, 0), range=(-90, 90),
                     unit='deg')

    def render(self):
        return cube(2, center=True)


class WideHinge(Hinge):
    """A subclass redeclaring the inherited joint."""

    swing = Revolute(axis=(0, 0, 1), at=(0, 10, 0), range=(-180, 180),
                     unit='deg')


class Slider(Solid2Node):

    travel = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')
    spin = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube(2, center=True)


class Mixed(Solid2Node):
    """A plain port beside a joint: the enumerator reports both."""

    lift = TranslationalPort(unit='mm', scale=2.0)
    swing = Revolute(axis=(0, 0, 1), at=(0, 10, 0), unit='deg')

    def render(self):
        return cube(2, center=True)


##############################################
# 1.2 The declaration

class JointDeclarationTest(BaseNodeTest):

    def test_the_kinds_are_exported_from_the_joints_module(self):
        from solid_node.motion import joints

        for name in ('Joint', 'Revolute', 'Prismatic', 'JointRangeError',
                     'declared_joints'):
            with self.subTest(name=name):
                self.assertTrue(hasattr(joints, name), name)

    def test_a_class_carries_its_joints_without_being_constructed(self):
        self.assertIsInstance(Hinge.swing, Joint)
        self.assertEqual(Hinge.swing.axis, (0, 0, 1))
        self.assertEqual(Hinge.swing.at, (0, 10, 0))
        self.assertEqual(Hinge.swing.range, (-90, 90))
        self.assertEqual(Hinge.swing.unit, 'deg')
        self.assertEqual(Hinge.swing.name, 'swing')

    def test_the_units_have_defaults_per_kind(self):
        class Bare(Solid2Node):
            swing = Revolute(axis=(0, 0, 1))
            slide = Prismatic(axis=(1, 0, 0))

            def render(self):
                return cube(1, center=True)

        self.assertEqual(Bare.swing.unit, 'deg')
        self.assertEqual(Bare.slide.unit, 'mm')
        self.assertEqual(Bare.swing.at, (0, 0, 0))
        self.assertIsNone(Bare.swing.range)

    def test_declared_joints_walks_base_first_and_a_subclass_wins(self):
        self.assertEqual(sorted(declared_joints(Slider)), ['spin', 'travel'])
        self.assertEqual(sorted(declared_joints(WideHinge)), ['swing'])
        self.assertEqual(declared_joints(Hinge)['swing'].range, (-90, 90))
        self.assertEqual(declared_joints(WideHinge)['swing'].range,
                         (-180, 180))

    def test_a_joint_is_not_a_parameter_a_driver_or_a_child(self):
        from solid_node.node.declarative import declared_children
        from solid_node.node.qualified import declared_drivers_of
        from solid_node.parameters import declared_parameters

        self.assertEqual(declared_parameters(Hinge), {})
        self.assertEqual(declared_drivers_of(Hinge), {})
        self.assertEqual(declared_children(Hinge), {})

    def test_a_joint_and_a_port_cannot_share_a_name(self):
        with self.assertRaises(TypeError) as raised:
            class Clash(Solid2Node):
                turn = Revolute(axis=(0, 0, 1))
                turn = RotationalPort(unit='deg')

                def render(self):
                    return cube(1, center=True)

        message = str(raised.exception)
        self.assertIn('turn', message)
        self.assertIn('Clash', message)
        self.assertIn('joint', message)
        self.assertIn('port', message)

    def test_a_joint_shadowing_an_inherited_port_is_refused(self):
        class Base(Solid2Node):
            turn = RotationalPort(unit='deg')

            def render(self):
                return cube(1, center=True)

        with self.assertRaises(TypeError) as raised:
            class Derived(Base):
                turn = Revolute(axis=(0, 0, 1))

        self.assertIn('turn', str(raised.exception))


##############################################
# 1.3 The coordinate

class JointCoordinateTest(BaseNodeTest):

    def test_reading_a_joint_yields_its_unbound_coordinate(self):
        hinge = Hinge()

        self.assertIsInstance(hinge.swing, BoundPort)
        self.assertEqual(hinge.swing.domain, 'rotational')
        self.assertEqual(hinge.swing.unit, 'deg')
        self.assertIsNone(hinge.swing.value)

    def test_a_prismatic_coordinate_is_translational(self):
        self.assertEqual(Slider().travel.domain, 'translational')
        self.assertEqual(Slider().travel.unit, 'mm')

    def test_two_instances_read_their_own_slots(self):
        one, other = Hinge(), Hinge()

        one.swing = 10
        other.swing = 20

        self.assertEqual(one.swing.value, 10)
        self.assertEqual(other.swing.value, 20)
        self.assertIsNot(one.swing, other.swing)

    def test_assignment_binds_and_never_shadows_the_declaration(self):
        hinge = Hinge()

        hinge.swing = 30

        self.assertNotIn('swing', vars(hinge))
        self.assertIsInstance(hinge.swing, BoundPort)
        self.assertEqual(hinge.swing.value, 30)
        self.assertIsInstance(Hinge.swing, Joint)

    def test_declared_ports_reports_the_coordinate_beside_a_port(self):
        ports = declared_ports(Mixed)

        self.assertEqual(sorted(ports), ['lift', 'swing'])
        self.assertIsInstance(ports['swing'], Port)
        self.assertEqual(ports['swing'].domain, 'rotational')
        self.assertEqual(ports['swing'].unit, 'deg')
        self.assertEqual(ports['lift'].domain, 'translational')

    def test_a_joint_coordinate_carries_no_scale_and_no_direction(self):
        coordinate = declared_ports(Mixed)['swing']

        self.assertIsNone(coordinate.scale)
        self.assertFalse(coordinate.out)
        for absent in ('axis', 'at', 'range'):
            with self.subTest(absent=absent):
                self.assertFalse(hasattr(coordinate, absent))

    def test_a_duck_typed_coordinate_holder_is_enumerated(self):
        """The seam `declared_ports` uses is the `coordinate` attribute,
        not an isinstance check on `Joint`: joints.py imports ports, so
        ports cannot import joints back."""

        class Pairish:
            def __init__(self):
                # An instance attribute: a port is a data descriptor, so
                # a CLASS attribute would already have handed back a
                # bound slot rather than the declaration.
                self.coordinate = RotationalPort(unit='deg')

        class Odd(Solid2Node):
            hinge = Pairish()

            def render(self):
                return cube(1, center=True)

        self.assertIn('hinge', declared_ports(Odd))


##############################################
# 1.4 The frame carry, on Thor's numbers

class FrameCarryTest(BaseNodeTest):
    """Thor's elbow, computed by hand:

        rest    M = T(0, 241.5, 68) . Rx(90)
        axis    R^-1 . (0, 0, 1) = (0, 1, 0)
        anchor  M^-1 . (0, 160, 68) = R^-1 . (0, -81.5, 0) = (0, 0, 81.5)

    which is exactly `ELBOW_PIVOT_AXIS = (0, 1, 0)` and
    `ELBOW_PIVOT = (0, 0, 81.5)` in Thor's own `art2.py`.
    """

    def test_the_elbow_lands_on_thors_hand_written_constants(self):
        arm = Arm()

        arm.set_state(angle=30)

        operations = serialized(arm.forearm)
        self.assertEqual([operation[0] for operation in operations],
                         ['t', 'r', 't', 'r', 't'])

        centre_in, turn, centre_out = operations[:3]
        for component, expected in zip(numbers(centre_in),
                                       [-value for value in
                                        THOR_ELBOW_PIVOT]):
            self.assertAlmostEqual(component, expected, places=9)
        for component, expected in zip(numbers(centre_out),
                                       THOR_ELBOW_PIVOT):
            self.assertAlmostEqual(component, expected, places=9)

        self.assertEqual(turn[1], '30')
        # The axis is snapped, so the exact values reach the document.
        self.assertEqual(list(turn[2]), list(THOR_ELBOW_PIVOT_AXIS))
        for component, expected in zip(turn[2], THOR_ELBOW_PIVOT_AXIS):
            self.assertAlmostEqual(float(component), expected, places=9)

    def test_the_rest_placement_follows_the_joint_motion(self):
        arm = Arm()

        arm.set_state(angle=0)

        rest = serialized(arm.forearm)[3:]
        self.assertEqual(rest[0][0], 'r')
        self.assertEqual(rest[0][1], '90')
        self.assertEqual(list(rest[0][2]), [1, 0, 0])
        self.assertEqual(numbers(rest[1]), [0.0, 241.5, 68.0])

    def test_the_anchor_follows_the_parameter_per_instance(self):
        arm = Arm(reach=180.0)

        arm.set_state(angle=15)

        # The elbow is still 81.5 mm up the forearm: the rest placement
        # and the anchor moved together.
        self.assertAlmostEqual(numbers(serialized(arm.forearm)[0])[2], -81.5,
                               places=9)


##############################################
# 1.5 The degenerate case, the slide, numeric hygiene

class NumericHygieneTest(BaseNodeTest):

    def test_a_joint_through_the_placed_origin_needs_no_centring(self):
        stack = ArborStack()

        stack.set_state(rotation=45)

        for arbor in stack.arbors:
            with self.subTest(arbor=arbor.name):
                self.assertEqual([operation[0] for operation
                                  in serialized(arbor)][:2], ['r', 't'])
                self.assertEqual(serialized(arbor)[0][1], '45')
                self.assertEqual(list(serialized(arbor)[0][2]), [0, 0, 1])

    def test_a_slide_translates_along_its_carried_axis(self):
        gantry = Gantry()

        gantry.set_state(offset=120)

        operations = serialized(gantry.carriage)
        self.assertEqual([operation[0] for operation in operations],
                         ['t', 'r'])
        # A quarter turn about z carries the parent-frame x axis into
        # the carriage's own -y, and the two idle components are the
        # plain number 0 rather than an expression multiplied by zero.
        self.assertEqual(operations[0], ['t', ['0', '-120', '0']])

    def test_a_prismatic_anchor_changes_nothing(self):
        class Moved(Carriage):
            travel = Prismatic(axis=(1, 0, 0), at=(50, 60, 70),
                               range=(0, 200), unit='mm')

        class MovedGantry(Gantry):
            carriage = Moved()

        plain, moved = Gantry(), MovedGantry()
        plain.set_state(offset=120)
        moved.set_state(offset=120)

        self.assertEqual(serialized(plain.carriage)[0],
                         serialized(moved.carriage)[0])

    def test_residue_never_reaches_the_document(self):
        """A rest placement of three quarter turns leaves floating point
        residue in the inversion; nothing of it is published."""

        class Turned(AssemblyNode):
            hinge = Hinge()

            def render(self):
                self.hinge.rotate(90, [1, 0, 0])
                self.hinge.rotate(90, [0, 1, 0])
                self.hinge.rotate(90, [0, 0, 1])

            def simulate(self):
                self.hinge.swing = 20

        turned = Turned()
        turned.render()

        rotation = [operation for operation in serialized(turned.hinge)
                    if operation[0] == 'r'][0]
        for component in rotation[2]:
            with self.subTest(component=component):
                self.assertIn(component, (0, 1, -1))
        for translation in [operation for operation
                            in serialized(turned.hinge)[:3]
                            if operation[0] == 't']:
            for component in translation[1]:
                with self.subTest(component=component):
                    self.assertNotIn('e-', component)


##############################################
# 1.6 Motion discipline

class Bench(AssemblyNode):
    """Binds a child's joint and turns the same child by hand."""

    angle = Driver(default=0.0, unit='deg')

    hinge = Hinge()

    def render(self):
        self.hinge.translate([0, 0, 4])

    def simulate(self):
        self.hinge.rotate(10, [0, 0, 1])
        self.hinge.swing = self.angle


class SelfTurning(AssemblyNode):
    """An assembly binding its OWN joint from a value it was handed."""

    angle = Driver(default=0.0, unit='deg')

    swing = Revolute(axis=(0, 0, 1), at=(0, 0, 0), unit='deg')

    box = Hinge()

    def simulate(self):
        self.swing = self.angle


class MotionDisciplineTest(BaseNodeTest):

    def test_joint_motion_is_innermost_and_tagged(self):
        # `Bench` rotates the hinge by hand (10) and then binds its
        # joint (25). Until the joints declared on one class were given
        # a composition order this read ['r', 't', 'r', 't', 't'] -- the
        # hand-written rotation innermost, because it was applied first.
        # The joint block is now innermost as a whole, so the ANGLES are
        # asserted too: a coincidental match of kinds must not pass.
        bench = Bench()

        bench.set_state(angle=25)

        operations = bench.hinge.operations
        self.assertEqual([operation.serialized[0] for operation
                          in operations], ['t', 'r', 't', 'r', 't'])
        self.assertEqual([operation.serialized[1] for operation
                          in operations
                          if operation.serialized[0] == 'r'],
                         ['25', '10'])
        for operation in operations[:4]:
            self.assertTrue(getattr(operation, '_motion', False))
            self.assertIs(operation._animator, bench)
        self.assertFalse(getattr(operations[4], '_motion', False))
        self.assertFalse(hasattr(operations[4], '_animator'))

    def test_re_simulating_leaves_one_motion(self):
        # The joint's rotation is at index 1 -- the middle of its own
        # three-operation run, which is now the innermost thing on the
        # node. It sat at index 2 while the hand-written rotation was
        # applied first and therefore composed innermost.
        bench = Bench()

        bench.set_state(angle=25)
        bench.set_state(angle=25)
        bench.set_state(angle=40)

        self.assertEqual(len(motions(bench.hinge)), 4)
        self.assertEqual(bench.hinge.operations[1].serialized[1], '40')

    def test_the_rest_placement_is_never_swept(self):
        bench = Bench()

        bench.set_state(angle=25)
        rest = bench.hinge.operations[-1]
        bench.set_state(angle=40)

        self.assertIs(bench.hinge.operations[-1], rest)

    def test_binding_twice_in_one_simulate_leaves_the_last(self):
        class Twice(Bench):
            def simulate(self):
                self.hinge.swing = 10
                self.hinge.swing = 20

        twice = Twice()
        twice.render()

        rotations = [operation.serialized for operation
                     in twice.hinge.operations
                     if operation.serialized[0] == 'r']
        self.assertEqual([rotation[1] for rotation in rotations], ['20'])

    def test_binding_after_a_sweep_dropped_the_operations_succeeds(self):
        bench = Bench()
        bench.set_state(angle=25)

        _sweep(bench)
        bench.hinge.swing = 35

        self.assertEqual(len(motions(bench.hinge)), 3)

    def test_a_binding_outside_any_phase_is_motion_and_untagged(self):
        hinge = Hinge()
        hinge.translate([0, 10, 0])

        hinge.swing = 45

        self.assertIsNone(_phase.current())
        self.assertEqual([operation.serialized[0] for operation
                          in hinge.operations], ['r', 't'])
        rotation = hinge.operations[0]
        self.assertTrue(rotation._motion)
        self.assertFalse(hasattr(rotation, '_animator'))

    def test_an_untagged_binding_survives_an_unrelated_sweep(self):
        hinge = Hinge()
        hinge.translate([0, 10, 0])
        hinge.swing = 45
        other = Bench()
        other._animated_nodes = {hinge}

        _sweep(other)

        self.assertEqual(len(motions(hinge)), 1)

    def test_an_untagged_binding_is_replaced_not_accumulated(self):
        hinge = Hinge()
        hinge.translate([0, 10, 0])

        hinge.swing = 45
        hinge.swing = -45

        self.assertEqual(len(motions(hinge)), 1)
        self.assertEqual(hinge.operations[0].serialized[1], '-45')

    def test_a_joint_bound_by_the_nodes_own_simulate_moves_it(self):
        turning = SelfTurning()

        turning.set_state(angle=12)

        self.assertEqual(turning.operations[0].serialized[1], '12')
        self.assertIs(turning.operations[0]._animator, turning)

    def test_the_joint_block_is_innermost_of_hand_written_motion(self):
        # This test was `test_hand_written_and_joint_motion_coexist_in
        # _order` and asserted ['10', '25']: the two kinds of motion
        # composed in the order they were APPLIED, and `Bench` applies
        # the hand-written rotation first. A joint's operations now sit
        # inside every hand-written one, so the joint's 25 is innermost
        # and the hand-written 10 outside it. If this ever reads
        # ['10', '25'] again, that is a revert, not a coincidence.
        bench = Bench()

        bench.set_state(angle=25)

        self.assertEqual([operation.serialized[1] for operation
                          in bench.hinge.operations
                          if operation.serialized[0] == 'r'],
                         ['25', '10'])

##############################################
# 1.6b Composition order: several joints on one body

# The rest placement every bench in this section applies, and the pivot
# anchor stated in the PARENT's frame -- away from the body's placed
# origin, so the pivot produces three operations and not one.
TWO_FREEDOM_LIFT = [0, 0, 4]
PIVOT_AT = (0, 30, 0)


def _translation(vector):
    matrix = np.eye(4)
    matrix[:3, 3] = vector
    return matrix


def _rotation(degrees, axis):
    """Rodrigues, written out here on purpose: the expected matrices in
    this section have to be independent of the framework's own
    `operation.matrix()`, or a wrong composition could be confirmed by
    the code that produced it."""
    axis = np.array(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    angle = math.radians(degrees)
    cross = np.array([[0.0, -axis[2], axis[1]],
                      [axis[2], 0.0, -axis[0]],
                      [-axis[1], axis[0], 0.0]])
    matrix = np.eye(4)
    matrix[:3, :3] = (np.eye(3) + math.sin(angle) * cross
                      + (1 - math.cos(angle)) * cross @ cross)
    return matrix


def _turn_about(at, degrees, axis, lift):
    """A revolute's own contribution, in the body's frame: the anchor
    carried through the inverse of the rest placement `lift`."""
    anchor = np.array(at, dtype=float) - np.array(lift, dtype=float)
    return (_translation(anchor) @ _rotation(degrees, axis)
            @ _translation(-anchor))


class TwoFreedom(Solid2Node):
    """Two freedoms on one body, declared pivot-innermost.

    The pivot turns about z through a point 30 mm off the body's placed
    origin and the slide runs along y, so `T_slide . R_pivot` and
    `R_pivot . T_slide` are DIFFERENT transforms. That is deliberate: an
    assertion on the operations list alone cannot tell a right
    composition from a wrong one when the two operations commute, and
    `test_the_fixture_joints_do_not_commute` fails loudly if this
    fixture ever stops exercising the question.
    """

    pivot = Revolute(axis=(0, 0, 1), at=PIVOT_AT, unit='deg')
    slide = Prismatic(axis=(0, 1, 0), unit='mm')

    def render(self):
        return cube(2, center=True)


def _two_freedom_pose(angle, offset):
    """Where `TwoFreedom` lands when the contract holds: the pivot
    innermost, the slide outside it, the rest placement outside both."""
    return (_translation(TWO_FREEDOM_LIFT) @ _translation((0, offset, 0))
            @ _turn_about(PIVOT_AT, angle, (0, 0, 1), TWO_FREEDOM_LIFT))


class PivotFirstBench(AssemblyNode):
    """Binds the first-declared joint first."""

    angle = Driver(default=0.0, unit='deg')
    offset = Driver(default=0.0, unit='mm')

    body = TwoFreedom()

    def render(self):
        self.body.translate(TWO_FREEDOM_LIFT)

    def simulate(self):
        self.body.pivot = self.angle
        self.body.slide = self.offset


class SlideFirstBench(PivotFirstBench):
    """The same bench binding the two joints in the opposite order."""

    def simulate(self):
        self.body.slide = self.offset
        self.body.pivot = self.angle


# The cycloidal case: a spin and an orbit about parallel lines through
# different points, both driven from ONE shaft coordinate, so the order
# the solver reaches them in is the only thing that could decide the
# composition.
DISK_LIFT = [0, 0, 6]
SPIN_AT = (0, 0, 26)
ORBIT_AT = (0, 0, 0)


class Disk(Solid2Node):

    spin = Revolute(axis=(0, 1, 0), at=SPIN_AT, unit='deg')
    orbit = Revolute(axis=(0, 1, 0), at=ORBIT_AT, unit='deg')

    def render(self):
        return cube(2, center=True)


class Cycloidal(AssemblyNode):

    shaft = Driver(default=0.0, unit='deg')

    disk = Disk()

    shaft.drives(disk.spin, ratio=-0.5)
    shaft.drives(disk.orbit)

    def render(self):
        self.disk.translate(DISK_LIFT)


class CycloidalSwapped(AssemblyNode):
    """The same machine with the two relation STATEMENTS written the
    other way round: the class body's joints are unchanged, so the pose
    must be unchanged."""

    shaft = Driver(default=0.0, unit='deg')

    disk = Disk()

    shaft.drives(disk.orbit)
    shaft.drives(disk.spin, ratio=-0.5)

    def render(self):
        self.disk.translate(DISK_LIFT)


# Inheritance: a base declaring `a` then `b`, a subclass declaring `c`
# and redeclaring `a` at a different anchor.
THREE_LIFT = [0, 0, 4]
BASE_A_AT = (0, 30, 0)
SUB_A_AT = (0, 50, 0)
C_AT = (0, 0, 10)


class ThreeBase(Solid2Node):

    a = Revolute(axis=(0, 0, 1), at=BASE_A_AT, unit='deg')
    b = Prismatic(axis=(0, 1, 0), unit='mm')

    def render(self):
        return cube(2, center=True)


class ThreeSub(ThreeBase):

    a = Revolute(axis=(0, 0, 1), at=SUB_A_AT, unit='deg')
    c = Revolute(axis=(1, 0, 0), at=C_AT, unit='deg')


class OrderedBench(AssemblyNode):
    """One assembly binding BOTH joints by hand, with its binding order
    chosen by a driver.

    The obvious fixture -- one end bound by hand at one instant and by a
    relation at the next -- cannot be written: a coordinate a wiring or
    a relation binds may not also be bound by hand
    (`WiringTest::test_binding_a_wired_child_end_by_hand_is_refused`).
    A driver keeps the test's control explicit and off the time base.
    """

    order = Driver(default=0.0)
    angle = Driver(default=0.0, unit='deg')
    offset = Driver(default=0.0, unit='mm')

    body = TwoFreedom()

    def render(self):
        self.body.translate(TWO_FREEDOM_LIFT)

    def simulate(self):
        if self.order < 0.5:
            self.body.pivot = self.angle
            self.body.slide = self.offset
        else:
            self.body.slide = self.offset
            self.body.pivot = self.angle


class InnerSlide(AssemblyNode):
    """Animator B: binds the SECOND-declared joint of the shared body."""

    body = TwoFreedom()

    def render(self):
        self.body.translate(TWO_FREEDOM_LIFT)

    def simulate(self):
        self.body.slide = 12


class OuterPivot(AssemblyNode):
    """Animator A: binds the FIRST-declared joint of the same body, two
    levels down -- the wart's wheel spun by its axle and steered by the
    steering assembly."""

    inner = InnerSlide()

    def simulate(self):
        self.inner.body.pivot = 35


class ThreeSlot(Solid2Node):
    """A prismatic, a three-operation revolute, and a second revolute:
    the contiguity guard the stacked cycles rely on."""

    lift = Prismatic(axis=(0, 0, 1), unit='mm')
    swing = Revolute(axis=(0, 0, 1), at=(0, 30, 0), unit='deg')
    twist = Revolute(axis=(0, 1, 0), unit='deg')

    def render(self):
        return cube(2, center=True)


class ContiguityBench(AssemblyNode):
    """Binds the three joints out of declaration order, with a
    hand-written rotation in the middle of the run for good measure."""

    body = ThreeSlot()

    def render(self):
        self.body.translate([0, 0, 4])

    def simulate(self):
        self.body.twist = 15
        self.body.rotate(7, [1, 0, 0])
        self.body.swing = 35
        self.body.lift = 12


class BothSidesBench(AssemblyNode):
    """Hand-written motion on BOTH sides of the binding: the joint block
    is innermost and the two hand-written calls keep their call order
    outside it."""

    angle = Driver(default=0.0, unit='deg')

    hinge = Hinge()

    def render(self):
        self.hinge.translate([0, 0, 4])

    def simulate(self):
        self.hinge.rotate(10, [0, 0, 1])
        self.hinge.swing = self.angle
        self.hinge.translate([0, 3, 0])


class CompositionOrderTest(BaseNodeTest):
    """The joints declared on one class compose in DECLARATION order,
    innermost first, whatever order they are bound in."""

    def test_the_fixture_joints_do_not_commute(self):
        pivot = _turn_about(PIVOT_AT, 35, (0, 0, 1), TWO_FREEDOM_LIFT)
        slide = _translation((0, 12, 0))

        self.assertFalse(np.allclose(slide @ pivot, pivot @ slide))

    def test_two_joints_compose_in_declaration_order_either_way_round(self):
        first = PivotFirstBench()
        second = SlideFirstBench()

        first.set_state(angle=35, offset=12)
        second.set_state(angle=35, offset=12)

        self.assertEqual([operation[0] for operation
                          in serialized(first.body)],
                         ['t', 'r', 't', 't', 't'])
        self.assertEqual(serialized(first.body), serialized(second.body))
        expected = _two_freedom_pose(35, 12)
        for bench in (first, second):
            with self.subTest(bench=type(bench).__name__):
                assert_allclose(_compose_world_matrix(bench.body),
                                expected, atol=1e-12)

    def test_relation_bound_joints_ignore_the_solve_order(self):
        machine = Cycloidal()
        swapped = CycloidalSwapped()

        machine.set_state(shaft=40)
        swapped.set_state(shaft=40)

        expected = (_translation(DISK_LIFT)
                    @ _turn_about(ORBIT_AT, 40, (0, 1, 0), DISK_LIFT)
                    @ _turn_about(SPIN_AT, -20, (0, 1, 0), DISK_LIFT))
        self.assertEqual(serialized(machine.disk), serialized(swapped.disk))
        for node in (machine.disk, swapped.disk):
            with self.subTest(node=node.__class__.__name__):
                assert_allclose(_compose_world_matrix(node), expected,
                                atol=1e-12)

    def test_re_binding_one_joint_of_several_keeps_its_place(self):
        body = TwoFreedom()
        body.translate(TWO_FREEDOM_LIFT)

        body.pivot = 35
        body.slide = 12
        body.pivot = -20

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 'r', 't', 't', 't'])
        self.assertEqual(len(motions(body)), 4)
        assert_allclose(_compose_world_matrix(body),
                        _two_freedom_pose(-20, 12), atol=1e-12)

    def test_inherited_joints_compose_inside_a_subclasss_own(self):
        # Green before this cycle and load-bearing after it: the
        # enumerator's order IS the composition order, so a later
        # refactor of the walk would silently change geometry.
        self.assertEqual(list(declared_joints(ThreeSub)), ['a', 'b', 'c'])

        body = ThreeSub()
        body.translate(THREE_LIFT)
        body.c = 15
        body.b = 12
        body.a = 35

        expected = (_translation(THREE_LIFT)
                    @ _turn_about(C_AT, 15, (1, 0, 0), THREE_LIFT)
                    @ _translation((0, 12, 0))
                    @ _turn_about(SUB_A_AT, 35, (0, 0, 1), THREE_LIFT))
        assert_allclose(_compose_world_matrix(body), expected, atol=1e-12)

    def test_a_reversed_application_order_across_a_sweep_changes_nothing(self):
        bench = OrderedBench()

        bench.set_state(order=0, angle=35, offset=12)
        first = serialized(bench.body)
        first_matrix = _compose_world_matrix(bench.body)

        bench.set_state(order=1, angle=35, offset=12)

        self.assertEqual(serialized(bench.body), first)
        assert_allclose(_compose_world_matrix(bench.body), first_matrix,
                        rtol=0, atol=0)
        self.assertEqual(len(motions(bench.body)), 4)

    def test_two_animators_on_one_node_keep_the_declared_order(self):
        outer = OuterPivot()
        body = outer.inner.body

        outer.render()
        outer.inner.render()

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 'r', 't', 't', 't'])
        for operation in body.operations[:3]:
            self.assertIs(operation._animator, outer)
        self.assertIs(body.operations[3]._animator, outer.inner)

        outer.render()

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 'r', 't', 't', 't'])
        self.assertEqual(len(motions(body)), 4)
        assert_allclose(_compose_world_matrix(body),
                        _two_freedom_pose(35, 12), atol=1e-12)

    def test_a_three_operation_joint_is_one_unbroken_run_at_its_slot(self):
        bench = ContiguityBench()
        bench.render()
        body = bench.body

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 't', 'r', 't', 't', 'r', 't', 'r', 't'])
        run = body.__dict__['_joint_motion']['swing']
        self.assertEqual(len(run), 3)
        index = body.operations.index(run[0])
        self.assertEqual(index, 1)
        self.assertEqual(body.operations[index:index + 3], run)
        self.assertEqual(body.operations[index + 1].serialized[1], '35')

    def test_hand_written_motion_sits_outside_the_whole_joint_block(self):
        bench = BothSidesBench()

        bench.set_state(angle=25)

        operations = bench.hinge.operations
        self.assertEqual([operation.serialized[0] for operation
                          in operations],
                         ['t', 'r', 't', 'r', 't', 't'])
        self.assertEqual(operations[1].serialized[1], '25')
        self.assertEqual(operations[3].serialized[1], '10')
        self.assertEqual(numbers(operations[4].serialized), [0.0, 3.0, 0.0])
        self.assertFalse(getattr(operations[5], '_motion', False))

    def test_the_published_document_reads_innermost_first(self):
        bench = BothSidesBench()
        bench.set_state(angle=25)

        document = serialize_node(bench, lambda rigid: rigid.name)
        hinge = document['children'][0]

        self.assertEqual([operation[0] for operation
                          in hinge['operations']],
                         ['t', 'r', 't', 'r', 't', 't'])
        self.assertEqual(hinge['operations'][1][1], '25')
        self.assertEqual(hinge['operations'][3][1], '10')
        keys = set(document)
        for child in document.get('children', ()):
            keys.update(child)
        self.assertLessEqual(
            keys, {'name', 'type', 'color', 'mtime', 'operations', 'model',
                   'children', 'flexible', 'piece'})



##############################################
# 1.7 Symbolic values

class Spinner(AssemblyNode):
    """The joint bound from an expression in the animation time."""

    hinge = Hinge()

    def render(self):
        self.hinge.translate([0, 0, 5])

    def simulate(self):
        self.hinge.swing = self.time * 90


class SymbolicJointTest(BaseNodeTest):

    def test_an_expression_reaches_the_document_as_the_angle(self):
        spinner = Spinner()
        spinner.render()

        angle = spinner.hinge.operations[1].serialized[1]
        self.assertIn('$t', angle)

    def test_a_keyframe_makes_it_numeric_and_clearing_restores_it(self):
        spinner = Spinner()

        spinner.set_keyframe(0.5)
        self.assertEqual(spinner.hinge.operations[1].serialized[1], '45.0')

        spinner.clear_keyframe()
        self.assertIn('$t', spinner.hinge.operations[1].serialized[1])

    def test_a_driver_read_publishes_the_driver_token(self):
        from solid_node.core.serializer import symbolic_drivers

        class Driven(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            hinge = Hinge()

            def simulate(self):
                self.hinge.swing = self.angle

        driven = Driven()
        with symbolic_drivers(driven):
            driven.render()
            angle = driven.hinge.operations[1].serialized[1]

        self.assertEqual(angle, 'angle')


##############################################
# 1.8 The range

class RangeTest(BaseNodeTest):

    def test_an_out_of_range_binding_is_refused_by_name(self):
        arm = Arm()
        arm.set_state(angle=0)

        with self.assertRaises(JointRangeError) as raised:
            arm.set_state(angle=170)

        message = str(raised.exception)
        for expected in ('forearm', 'elbow', '170', '-135', '135', 'deg'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_refused_binding_leaves_the_node_unmoved(self):
        hinge = Hinge()
        hinge.translate([0, 10, 0])

        with self.assertRaises(JointRangeError):
            hinge.swing = 170

        self.assertEqual(len(motions(hinge)), 0)
        self.assertIsNone(hinge.swing.value)

    def test_an_unlinked_node_is_named_by_class(self):
        with self.assertRaises(JointRangeError) as raised:
            Hinge().swing = 170

        self.assertIn('Hinge', str(raised.exception))

    def test_the_bounds_are_inclusive(self):
        hinge = Hinge()

        hinge.swing = -90
        hinge.swing = 90

        self.assertEqual(hinge.swing.value, 90)

    def test_a_symbolic_binding_is_not_checked(self):
        spinner = Spinner()

        spinner.render()  # $t * 90 passes outside (-90, 90)

        self.assertIn('$t', spinner.hinge.operations[1].serialized[1])

    def test_a_joint_with_no_range_accepts_anything(self):
        class Free(Solid2Node):
            spin = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(1, center=True)

        free = Free()
        free.spin = 10_000

        self.assertEqual(free.spin.value, 10_000)


##############################################
# 1.9 Argument resolution

class ArgumentResolutionTest(BaseNodeTest):

    def test_a_callable_anchor_is_called_once_with_the_realized_node(self):
        calls = []

        class Counted(AssemblyNode):
            index = Count(1, min=0)

            def _anchor(node):
                calls.append(node)
                return (0.0, BEARING_PITCH * node.index, 0.0)

            turn = Revolute(axis=(0, 0, 1), at=_anchor, unit='deg')

            box = Hinge()

        counted = Counted()

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0], counted)
        counted.turn = 10
        self.assertEqual(len(calls), 1)

    def test_each_arbor_is_anchored_on_its_own_built_position(self):
        stack = ArborStack()
        stack.set_state(rotation=30)

        # Each arbor's own placement puts its bearing at its origin, so
        # the carry leaves nothing to centre.
        for arbor in stack.arbors:
            self.assertEqual([operation.serialized[0] for operation
                              in arbor.operations][:1], ['r'])

    def test_an_undeclared_token_fails_at_realization(self):
        elsewhere = Length(5.0)
        elsewhere._name = 'elsewhere'

        class Bad(AssemblyNode):
            swing = Revolute(axis=(0, 0, 1), at=(0, elsewhere, 0),
                             unit='deg')

            box = Hinge()

        with self.assertRaises(ParameterError) as raised:
            Bad()

        message = str(raised.exception)
        self.assertIn('Bad', message)
        self.assertIn('swing', message)
        self.assertIn('at', message)

    def test_a_malformed_argument_fails_at_realization(self):
        cases = {
            'short axis': dict(axis=(0, 0)),
            'zero axis': dict(axis=(0, 0, 0)),
            'short anchor': dict(axis=(0, 0, 1), at=(0, 0)),
            'reversed range': dict(axis=(0, 0, 1), range=(10, 0)),
        }
        for label, arguments in cases.items():
            with self.subTest(label=label):
                class Bad(AssemblyNode):
                    swing = Revolute(unit='deg', **arguments)

                    box = Hinge()

                with self.assertRaises(ParameterError) as raised:
                    Bad()
                self.assertIn('swing', str(raised.exception))

    def test_a_refused_instance_realized_no_child(self):
        built = []

        class Watcher(Solid2Node):
            def __init__(self, **kwargs):
                built.append(self)
                super().__init__(**kwargs)

            def render(self):
                return cube(1, center=True)

        class Bad(AssemblyNode):
            swing = Revolute(axis=(0, 0, 0), unit='deg')

            watched = Watcher()

        with self.assertRaises(ParameterError):
            Bad()

        self.assertEqual(built, [])

    def test_a_joint_argument_is_not_identity(self):
        class Anchored(Solid2Node):
            """The anchor comes off something outside the declared
            parameters, so two instances can differ in it while being
            the same printed part."""

            swing = Revolute(axis=(0, 0, 1),
                             at=lambda node: (0.0, float(len(node.name)), 0.0),
                             unit='deg')

            def render(self):
                return cube(1, center=True)

        one = Anchored(name='a')
        other = Anchored(name='bbb')
        one.swing = 10
        other.swing = 10

        self.assertEqual(one.uniq_id, other.uniq_id)
        self.assertNotEqual(serialized(one)[0], serialized(other)[0])


##############################################
# 1.10 Wiring

class WiringTest(BaseNodeTest):

    def test_one_coordinate_turns_two_children(self):
        stack = ArborStack()

        stack.set_state(rotation=30)

        for arbor in stack.arbors:
            self.assertEqual(arbor.wheel.turn.value, 30)
            self.assertEqual(arbor.rod.turn.value, 30)

    def test_a_wired_joint_moves_the_childs_body(self):
        stack = ArborStack()

        stack.set_state(rotation=30)

        rod = stack.arbors[0].rod
        self.assertEqual(rod.operations[0].serialized[1], '30')
        self.assertTrue(rod.operations[0]._motion)

    def test_a_wiring_is_rebound_absolutely_on_every_run(self):
        stack = ArborStack()

        stack.set_state(rotation=30)
        stack.set_state(rotation=-15)

        self.assertEqual(stack.arbors[0].wheel.turn.value, -15)
        self.assertEqual(len(motions(stack.arbors[0].rod)), 1)

    def test_a_repeated_wired_child_is_bound_per_instance(self):
        class Many(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            turn = Revolute(axis=(0, 0, 1), unit='deg')

            wheels = Wheel(turn=turn).repeat(3)

            def simulate(self):
                self.turn = self.angle

        many = Many()
        many.set_state(angle=20)

        self.assertEqual([wheel.turn.value for wheel in many.wheels],
                         [20, 20, 20])
        self.assertEqual(len({id(wheel.turn) for wheel in many.wheels}), 3)

    def test_a_wiring_reaches_two_levels_down(self):
        class Middle(AssemblyNode):
            turn = RotationalPort(unit='deg')
            wheel = Wheel(turn=turn)

        class Top(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            turn = RotationalPort(unit='deg')
            middle = Middle(turn=turn)

            def simulate(self):
                self.turn = self.angle

        top = Top()
        top.set_state(angle=7)

        self.assertEqual(top.middle.wheel.turn.value, 7)

    def test_a_wired_scale_converts(self):
        class Scaled(Solid2Node):
            turn = RotationalPort(unit='mm', scale=2.0)

            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            turn = RotationalPort(unit='deg')
            scaled = Scaled(turn=turn)

            def simulate(self):
                self.turn = self.angle

        top = Top()
        top.set_state(angle=10)

        self.assertEqual(top.scaled.turn.value, 20.0)

    def test_an_unbound_source_is_refused_by_name(self):
        class Top(AssemblyNode):
            turn = RotationalPort(unit='deg')
            wheel = Wheel(turn=turn)

        top = Top()
        with self.assertRaises(ValueError) as raised:
            top.render()

        message = str(raised.exception)
        for expected in ('Top', 'wheel', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_binding_a_wired_child_end_by_hand_is_refused(self):
        class Top(AssemblyNode):
            turn = RotationalPort(unit='deg')
            wheel = Wheel(turn=turn)

            def simulate(self):
                self.turn = 5
                self.wheel.turn = 9

        top = Top()
        with self.assertRaises(ValueError) as raised:
            top.render()

        message = str(raised.exception)
        for expected in ('Top', 'wheel', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)


##############################################
# 1.11 Wiring refusals

class WiringRefusalTest(BaseNodeTest):

    def test_a_keyword_the_child_cannot_receive_fails_at_definition(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                turn = RotationalPort(unit='deg')
                link = Wheel(spin=turn)

        message = str(raised.exception)
        for expected in ('Top', 'Wheel', 'spin', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_coordinate_of_another_class_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                wheel = Wheel(turn=Rod.turn)

        message = str(raised.exception)
        for expected in ('Top', 'turn', 'Rod'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_an_unknown_plain_keyword_is_still_a_type_error(self):
        class Top(AssemblyNode):
            spool = Spool(spin=1.0)

        with self.assertRaises(TypeError) as raised:
            Top()

        self.assertIn('spin', str(raised.exception))

    def test_a_wiring_is_absent_from_parameters_and_identity(self):
        class Arm2(AssemblyNode):
            turn = RotationalPort(unit='deg')
            spool = Spool(turn=turn)

        one = Arm2()
        other = Arm2()
        one.turn = 5

        self.assertNotIn('turn', one.spool.__dict__['_parameters'])
        self.assertEqual(one.spool.uniq_id, other.spool.uniq_id)


##############################################
# 1.12 The published document

class JointDocumentTest(BaseNodeTest):

    def document(self, node):
        return serialize_node(node, lambda rigid: rigid.name)

    def keys(self, document, found=None):
        found = set() if found is None else found
        found.update(document)
        for child in document.get('children', ()):
            self.keys(child, found)
        return found

    def test_the_joint_publishes_operations_and_no_new_key(self):
        arm = Arm()
        arm.set_state(angle=30)

        document = self.document(arm)
        forearm = document['children'][0]

        self.assertEqual([operation[0] for operation
                          in forearm['operations']],
                         ['t', 'r', 't', 'r', 't'])
        self.assertEqual(forearm['operations'][1][1], '30')
        self.assertLessEqual(
            self.keys(document),
            {'name', 'type', 'color', 'mtime', 'operations', 'model',
             'children', 'flexible', 'piece'})

    def test_the_document_is_symbolic_until_keyframed(self):
        spinner = Spinner()

        symbolic = self.document(spinner)
        self.assertIn('$t', symbolic['children'][0]['operations'][1][1])

        spinner.set_keyframe(0.25)
        numeric = self.document(spinner)
        self.assertEqual(numeric['children'][0]['operations'][1][1], '22.5')

    def test_the_pose_differs_between_two_instants(self):
        import numpy as np
        from solid_node.node.base import _compose_world_matrix

        arm = Arm()

        arm.set_state(angle=0)
        origin = np.array([0.0, 0.0, 0.0, 1.0])
        at_rest = _compose_world_matrix(arm.forearm.link) @ origin

        arm.set_state(angle=90)
        turned = _compose_world_matrix(arm.forearm.link) @ origin

        self.assertFalse(np.allclose(at_rest, turned))


##############################################
# 1.13 Import cost

MODULE_REPORT = (
    'import sys\n'
    "print(sorted(m for m in sys.modules\n"
    "             if m == 'solid_node' or m.startswith('solid_node.')))\n")


class JointImportCostTest(TestCase):

    def modules(self, snippet):
        result = probe(snippet + MODULE_REPORT).check()
        return set(eval(result.stdout.strip())), result

    def test_joints_costs_what_ports_costs_and_no_more(self):
        ports, _ = self.modules('import solid_node.motion.ports\n')
        joints, result = self.modules('import solid_node.motion.joints\n')

        self.assertEqual(joints, ports | {'solid_node.motion.joints'})
        for absent in ('cadquery', 'OCP', 'trimesh'):
            with self.subTest(absent=absent):
                self.assertFalse(result.imported(absent))

    def test_couplings_costs_what_ports_costs_too(self):
        """Cycle 3 filled `couplings`, and a relation relates two ports,
        so it costs exactly what `joints` costs (tests/test_couplings.py
        pins it from that side as well)."""
        ports, _ = self.modules('import solid_node.motion.ports\n')
        couplings, _ = self.modules('import solid_node.motion.couplings\n')

        self.assertEqual(couplings, ports | {'solid_node.motion.couplings'})
