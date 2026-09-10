# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The one-coordinate lower pairs: `Revolute` and `Prismatic`.

A joint says WHERE a body may move, next to the body, once. A joint
declared in a class body is the body's own statement about itself, so its
axis and anchor are read in that body's OWN REST FRAME -- the frame its
own `render()` states its geometry in, one rest placement away from the
parent's -- which is MuJoCo's rule. The framework transforms nothing:
there is no carry, because a joint's operations were always placed
INNERMOST, before every rest operation, in the body's own frame.

Thor is the evidence and the pinned number: `art2.py` states the elbow
directly in the forearm's own frame as `ELBOW_PIVOT_AXIS = (0, 1, 0)` and
`ELBOW_PIVOT = (0, 0, 81.5)`, and the fixture in `tests/joint_project/`
declares the same joint the same way, with nothing to invert. If the two
ever disagree, this file says so.

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

from solid_node.motion.joints import (Free, Joint, JointRangeError, Orbit,
                                      Prismatic, Revolute,
                                      declared_joints)
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

        for name in ('Joint', 'Revolute', 'Prismatic', 'Orbit', 'Free',
                     'JointRangeError', 'declared_joints'):
            with self.subTest(name=name):
                self.assertTrue(hasattr(joints, name), name)
                self.assertIn(name, joints.__all__)

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
# 1.1-1.3 A joint is stated in the frame of whoever declares it

class OwnFrameTest(BaseNodeTest):
    """The rule itself: a class-body joint's `axis` and `at` are read in
    the declaring body's OWN rest frame, with `at` defaulting to that
    body's own origin, and nothing the framework does depends on where
    the parent places the body."""

    def test_a_joint_through_the_bodys_own_origin_needs_no_anchor(self):
        """A pinion on its own bearing: the parent moves it, the joint
        does not have to know where to."""

        class Pinion(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Bracket(AssemblyNode):
            pinion = Pinion()

            def render(self):
                self.pinion.translate([40, 25, 0])

            def simulate(self):
                self.pinion.turn = 30

        bracket = Bracket()
        bracket.render()

        operations = serialized(bracket.pinion)
        self.assertEqual([operation[0] for operation in operations],
                         ['r', 't'])
        self.assertEqual(operations[0][1], '30')
        self.assertEqual(list(operations[0][2]), [0, 0, 1])
        # The pinion's own origin does not move: only the rest placement
        # carries it, and the rotation leaves it exactly there.
        self.assertEqual(numbers(operations[1]), [40.0, 25.0, 0.0])

    def test_one_class_several_placements_one_declaration(self):
        """The V8's four timing gears and Thor's thirteen: one class
        placed at several different points resolves ONE set of joint
        arguments, and each copy spins about the line through its own
        placed origin."""

        class Gear(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Block(AssemblyNode):
            gears = [Gear(), Gear(), Gear(), Gear()]

            def render(self):
                for index, point in enumerate(
                        [[10, 0, 0], [0, 10, 0], [-10, 0, 0], [0, -10, 0]]):
                    self.gears[index].translate(point)

            def simulate(self):
                for gear in self.gears:
                    gear.turn = 45

        block = Block()
        block.render()

        arguments = {Gear.turn.arguments(gear) for gear in block.gears}
        # All four copies resolve the identical joint arguments: no copy
        # needed an anchor its class could not know.
        self.assertEqual(len(arguments), 1)
        for gear in block.gears:
            with self.subTest(gear=gear.name):
                operations = serialized(gear)
                self.assertEqual([operation[0] for operation
                                  in operations], ['r', 't'])
                self.assertEqual(list(operations[0][2]), [0, 0, 1])

    def test_the_line_turns_with_the_body(self):
        """A body its parent ROTATES carries its joint line WITH it: the
        line is the body's own, not the parent's."""

        class Cog(Solid2Node):
            spin = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Tilted(AssemblyNode):
            cog = Cog()

            def render(self):
                self.cog.rotate(90, [1, 0, 0])

            def simulate(self):
                self.cog.spin = 20

        tilted = Tilted()
        tilted.render()

        rotation = [operation for operation in serialized(tilted.cog)
                    if operation[0] == 'r'][0]
        self.assertEqual(list(rotation[2]), [0, 0, 1])

    def test_two_instances_placed_differently_resolve_identical_arguments(
            self):
        class Leaf(Solid2Node):
            turn = Revolute(axis=(0, 1, 0), at=(0, 0, 10), unit='deg')

            def render(self):
                return cube(2, center=True)

        class First(AssemblyNode):
            leaf = Leaf()

            def render(self):
                self.leaf.rotate(30, [0, 0, 1]).translate([5, 5, 5])

            def simulate(self):
                self.leaf.turn = 40

        class Second(AssemblyNode):
            leaf = Leaf()

            def render(self):
                self.leaf.rotate(-70, [1, 0, 0]).translate([-20, 0, 3])

            def simulate(self):
                self.leaf.turn = 40

        first, second = First(), Second()
        first.render()
        second.render()

        self.assertEqual(Leaf.turn.arguments(first.leaf),
                         Leaf.turn.arguments(second.leaf))
        first_motion, second_motion = (
            [operation.serialized for operation in motions(first.leaf)],
            [operation.serialized for operation in motions(second.leaf)])
        self.assertEqual(first_motion, second_motion)

    def test_a_joints_line_survives_a_change_to_the_rest_placement(self):
        class Leaf(Solid2Node):
            turn = Revolute(axis=(0, 1, 0), at=(0, 0, 10), unit='deg')

            def render(self):
                return cube(2, center=True)

        leaf = Leaf()
        leaf.turn = 25
        first = [operation.serialized for operation in motions(leaf)]

        leaf.rotate(45, [1, 0, 0]).translate([9, -3, 2])
        leaf.turn = 25
        second = [operation.serialized for operation in motions(leaf)]

        self.assertEqual(first, second)

    def test_a_symbolic_rest_placement_no_longer_refuses_a_joint(self):
        """The fixture behind the deleted refusal "an unresolvable rest
        placement is refused": a rest placement the framework cannot
        evaluate numerically no longer stands in a joint's way, because
        nothing inverts it."""

        class Leaf(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Symbolic(AssemblyNode):
            leaf = Leaf()

            def render(self):
                # `self.time` never resolves to a plain number outside a
                # keyframe: the fixture the deleted `_carry` refused on,
                # since its `matrix()` could not be composed numerically.
                self.leaf.translate([self.time, 0, 0])

            def simulate(self):
                self.leaf.turn = 15

        symbolic = Symbolic()
        symbolic.render()

        operations = serialized(symbolic.leaf)
        self.assertEqual(operations[0][0], 'r')
        self.assertEqual(list(operations[0][2]), [0, 0, 1])


##############################################
# 1.4 The declared frame, on Thor's numbers

class FrameCarryTest(BaseNodeTest):
    """Thor's elbow, stated directly in the forearm's OWN rest frame:

        axis    (0, 1, 0)
        anchor  (0, 0, 81.5)

    which is exactly `ELBOW_PIVOT_AXIS = (0, 1, 0)` and
    `ELBOW_PIVOT = (0, 0, 81.5)` in Thor's own `art2.py` -- now written
    where the project writes them, with nothing inverted to get there.
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

    def test_the_anchor_does_not_follow_the_parents_reach(self):
        """The anchor is the forearm's own statement about itself: it no
        longer depends on how far out the parent's `render()` reaches to
        place it -- the opposite of what a parent-frame anchor would do,
        and the point of rewriting the fixture at all."""
        default_arm = Arm()
        stretched_arm = Arm(reach=180.0)

        default_arm.set_state(angle=15)
        stretched_arm.set_state(angle=15)

        default_centring = numbers(serialized(default_arm.forearm)[0])
        stretched_centring = numbers(serialized(stretched_arm.forearm)[0])
        self.assertEqual(default_centring, stretched_centring)
        self.assertAlmostEqual(default_centring[2], -81.5, places=9)


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
        # The slide runs along the carriage's OWN x: the quarter turn
        # the parent applies is a rest operation and does not enter the
        # joint's own frame at all.
        self.assertEqual(operations[0], ['t', ['120', '0', '0']])

    def test_the_slides_idle_components_stay_plain_zero(self):
        """What the old parent-frame test protected, isolated: the two
        components the slide's own axis does not reach are the plain
        number 0, not an expression multiplied by zero -- observable
        only once the bound value is itself symbolic."""

        class SymbolicGantry(Gantry):
            def simulate(self):
                self.carriage.travel = self.time * 10

        gantry = SymbolicGantry()
        gantry.render()

        translation = serialized(gantry.carriage)[0][1]
        self.assertIn('$t', translation[0])
        self.assertEqual(translation[1], '0')
        self.assertEqual(translation[2], '0')

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
        """With no carry left to leave any, the one remaining source of
        floating-point residue is the normalization of a declared axis:
        `(0, 0, 3)` publishes `[0, 0, 1]` exactly, and an axis an
        author's own formula could produce without meaning anything but
        a unit direction -- `1 / 3 * 3` is `0.9999999999999999` in
        double precision -- publishes no `e-` and no residue either."""

        class Scaled(Solid2Node):
            turn = Revolute(axis=(0, 0, 3), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Formulaic(Solid2Node):
            turn = Revolute(axis=(1 / 3 * 3, 0, 0), unit='deg')

            def render(self):
                return cube(2, center=True)

        scaled = Scaled()
        scaled.turn = 40
        self.assertEqual(list(serialized(scaled)[0][2]), [0, 0, 1])

        formulaic = Formulaic()
        formulaic.turn = 40
        axis_components = list(serialized(formulaic)[0][2])
        self.assertEqual(axis_components, [1, 0, 0])
        for component in axis_components:
            with self.subTest(component=component):
                self.assertNotIn('e-', str(component))

    def test_an_anchor_is_published_as_written(self):
        """An anchor is not snapped: it is what the author wrote, not
        what the axis is. A `3e-17` anchor still omits the centring pair
        (the module's own `1e-9` zero test), and `81.49999999999999`
        reaches the document unrounded."""

        class NearZero(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), at=(3e-17, 0, 0), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Unrounded(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), at=(0, 0, 81.49999999999999),
                            unit='deg')

            def render(self):
                return cube(2, center=True)

        near_zero = NearZero()
        near_zero.turn = 10
        self.assertEqual([operation[0] for operation
                          in serialized(near_zero)], ['r'])

        unrounded = Unrounded()
        unrounded.turn = 10
        operations = serialized(unrounded)
        self.assertEqual([operation[0] for operation in operations],
                         ['t', 'r', 't'])
        self.assertEqual(numbers(operations[2]), [0.0, 0.0, 81.49999999999999])


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
        # Hinge's `at=(0, 10, 0)` is its own frame's statement now, so
        # this rest translate no longer cancels it: the joint's run is
        # the full three operations, innermost, then the rest translate.
        hinge = Hinge()
        hinge.translate([0, 10, 0])

        hinge.swing = 45

        self.assertIsNone(_phase.current())
        self.assertEqual([operation.serialized[0] for operation
                          in hinge.operations], ['t', 'r', 't', 't'])
        rotation = hinge.operations[1]
        self.assertTrue(rotation._motion)
        self.assertFalse(hasattr(rotation, '_animator'))

    def test_an_untagged_binding_survives_an_unrelated_sweep(self):
        hinge = Hinge()
        hinge.translate([0, 10, 0])
        hinge.swing = 45
        other = Bench()
        other._animated_nodes = {hinge}

        _sweep(other)

        # The joint's off-origin anchor makes ONE binding three
        # operations; what this guards is that a sweep tagged with a
        # DIFFERENT node drops none of them.
        self.assertEqual(len(motions(hinge)), 3)

    def test_an_untagged_binding_is_replaced_not_accumulated(self):
        hinge = Hinge()
        hinge.translate([0, 10, 0])

        hinge.swing = 45
        hinge.swing = -45

        self.assertEqual(len(motions(hinge)), 3)
        rotation = [operation for operation in hinge.operations
                   if operation.serialized[0] == 'r'][0]
        self.assertEqual(rotation.serialized[1], '-45')

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
# anchor -- stated in the body's OWN frame, away from its own origin, so
# the pivot produces three operations and not one.
TWO_FREEDOM_LIFT = [0, 0, 4]
PIVOT_AT = (0, 30, -4)


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


def _turn_about(at, degrees, axis):
    """A revolute's own contribution, read directly in the body's own
    frame: no carry, because there is nothing left to carry through."""
    anchor = np.array(at, dtype=float)
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
            @ _turn_about(PIVOT_AT, angle, (0, 0, 1)))


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
SPIN_AT = (0, 0, 20)
ORBIT_AT = (0, 0, -6)


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
BASE_A_AT = (0, 30, -4)
SUB_A_AT = (0, 50, -4)
C_AT = (0, 0, 6)


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
    swing = Revolute(axis=(0, 0, 1), at=(0, 30, -4), unit='deg')
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


# Cycle 1's contract over a joint whose run is exactly ONE operation and
# whose kind differs from the joint beside it. ADR-093 states the rule
# over "the operations a joint's placement produces", a contiguous run
# of ANY length; an `Orbit` is the first joint whose run is one.
SPUN_LIFT = [0.0, -2.5, 0.0]
SPUN_SPIN_AT = (3.0, 0.0, 0.0)


class SpunAndCarried(Solid2Node):
    """A three-operation revolute declared first, a one-operation orbit
    declared second: the disk spins about a bore 3 mm from its own
    placed origin and is carried round the parent's axis. The two do not
    commute -- `test_the_two_joints_of_the_orbit_fixture_do_not_commute`
    fails loudly if they ever do."""

    spin = Revolute(axis=(0, 0, 1), at=SPUN_SPIN_AT, unit='deg')
    # `at` is the OWN-FRAME point that lands on the world's origin once
    # `render()` applies `SPUN_LIFT` -- the parent's axis, restated in
    # this body's own frame so the fixture's world-frame line is
    # unchanged; `carries` keeps its default, the disk's own origin.
    carry = Orbit(axis=(0, 0, 1), at=(0, 2.5, 0), unit='deg')

    def render(self):
        return cube(2, center=True)


def _spun_and_carried_pose(angle, carry):
    """Where `SpunAndCarried` lands when the contract holds: the spin
    innermost, the orbit's single translation outside it, the rest
    placement outside both."""
    return (_translation(SPUN_LIFT)
            @ _translation(_orbit_delta((0, 0, 1), (0, 0, 0),
                                        SPUN_LIFT, carry))
            @ _turn_about(SPUN_SPIN_AT, angle, (0, 0, 1)))


class SpinFirstBench(AssemblyNode):
    """Binds the first-declared joint first."""

    angle = Driver(default=0.0, unit='deg')
    carry = Driver(default=0.0, unit='deg')

    disk = SpunAndCarried()

    def render(self):
        self.disk.translate(SPUN_LIFT)

    def simulate(self):
        self.disk.spin = self.angle
        self.disk.carry = self.carry


class OrbitFirstBench(SpinFirstBench):
    """The same bench binding the two joints the other way round."""

    def simulate(self):
        self.disk.carry = self.carry
        self.disk.spin = self.angle


class SlideSwingCarry(Solid2Node):
    """A prismatic, a three-operation revolute and an orbit: the
    contiguity case cycle 1's task 1.8 wrote the guard for."""

    lift = Prismatic(axis=(0, 0, 1), unit='mm')
    swing = Revolute(axis=(0, 0, 1), at=(0, 30, -4), unit='deg')
    # `at`, own-frame, is the point that lands on the world's origin
    # once `render()` translates by `[0, 0, 4]`; `carries` keeps its
    # default, the disk's own origin -- the same nonzero radius the
    # fixture always had, now stated rather than inherited by accident
    # of the rest placement.
    carry = Orbit(axis=(0, 1, 0), at=(0, 0, -4), unit='deg')

    def render(self):
        return cube(2, center=True)


class OrbitContiguityBench(AssemblyNode):
    """Binds the three joints out of declaration order, with a
    hand-written rotation in the middle of the run."""

    body = SlideSwingCarry()

    def render(self):
        self.body.translate([0, 0, 4])

    def simulate(self):
        self.body.carry = 25
        self.body.rotate(7, [1, 0, 0])
        self.body.swing = 35
        self.body.lift = 12


# Cycle 1's contract over the hardest joint it has: one that places
# several operations AND owns six coordinates. ADR-093 states the rule
# over "the operations a joint's placement produces", a contiguous run
# of any length, so a `Free` between a `Prismatic` and an off-origin
# `Revolute` is what says whether the rule is about joints or about
# operations. `Free` is declared here rather than in the free joint's
# own section because these are cycle 1's fixtures.
STACK_LIFT = [0.0, 0.0, 4.0]
STACK_SPIN_AT = (0.0, 30.0, -4.0)


class SlideFloatSpin(Solid2Node):
    """A one-operation prismatic, a free joint and a three-operation
    revolute, in that declaration order."""

    slide = Prismatic(axis=(1, 0, 0), unit='mm')
    pose = Free(angle_unit='deg', length_unit='mm')
    spin = Revolute(axis=(0, 0, 1), at=STACK_SPIN_AT, unit='deg')

    def render(self):
        return cube(2, center=True)


def _slide_float_spin_pose(offset, roll, yaw, height, angle):
    """Where `SlideFloatSpin` lands when the contract holds: the slide
    innermost, the free joint's whole run next, the revolute outside
    both, the rest placement outside everything."""
    return (_translation(STACK_LIFT)
            @ _turn_about(STACK_SPIN_AT, angle, (0, 0, 1))
            @ _free_pose(roll, 0.0, yaw, (0.0, 0.0, height))
            @ _translation((offset, 0, 0)))


class ScrambledStackBench(AssemblyNode):
    """Binds the coordinates of the three joints in an order the class
    body does not show."""

    body = SlideFloatSpin()

    def render(self):
        self.body.translate(STACK_LIFT)

    def simulate(self):
        self.body.pose.yaw = 25
        self.body.spin = 35
        self.body.pose.z = 60
        self.body.slide = 12
        self.body.pose.roll = 15


class InterruptedStackBench(ScrambledStackBench):
    """The same coordinates in another order, with a hand-written
    rotation applied in the middle of the binding."""

    def simulate(self):
        self.body.slide = 12
        self.body.pose.roll = 15
        self.body.rotate(7, [1, 0, 0])
        self.body.spin = 35
        self.body.pose.z = 60
        self.body.pose.yaw = 25


class FloatAndCarry(Solid2Node):
    """Cycle 2's `SpunAndCarried` shape with a `Free` declared FIRST:
    the orbit's single translation stays outside the free joint's
    run."""

    pose = Free(angle_unit='deg', length_unit='mm')
    # Own-frame `at`, the point that lands on the world's origin once
    # `render()` translates by `SPUN_LIFT` -- the same nonzero radius as
    # `SpunAndCarried.carry`, stated rather than inherited by accident.
    carry = Orbit(axis=(0, 0, 1), at=(0, 2.5, 0), unit='deg')

    def render(self):
        return cube(2, center=True)


class FloatAndCarryBench(AssemblyNode):

    body = FloatAndCarry()

    def render(self):
        self.body.translate(SPUN_LIFT)

    def simulate(self):
        self.body.carry = 40
        self.body.pose.yaw = 25
        self.body.pose.z = 60


class CompositionOrderTest(BaseNodeTest):
    """The joints declared on one class compose in DECLARATION order,
    innermost first, whatever order they are bound in."""

    def test_the_fixture_joints_do_not_commute(self):
        pivot = _turn_about(PIVOT_AT, 35, (0, 0, 1))
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
                    @ _turn_about(ORBIT_AT, 40, (0, 1, 0))
                    @ _turn_about(SPIN_AT, -20, (0, 1, 0)))
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
                    @ _turn_about(C_AT, 15, (1, 0, 0))
                    @ _translation((0, 12, 0))
                    @ _turn_about(SUB_A_AT, 35, (0, 0, 1)))
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

        # lift (1 op), swing's off-origin anchor (3), twist's DEFAULT
        # anchor -- genuinely the body's own origin now, with nothing to
        # carry it off zero (1), the hand-written rotate (1), the rest
        # placement (1).
        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 't', 'r', 't', 'r', 'r', 't'])
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
    # 2. Cycle 1's contract, with an orbit in it (ADR-093)

    def test_an_orbit_composes_with_a_turn_of_the_same_body(self):
        """A three-operation `Revolute` declared first and a
        one-operation `Orbit` declared second: the same operations and
        the same pose whichever order they are bound in."""
        first = SpinFirstBench()
        second = OrbitFirstBench()

        first.set_state(angle=35, carry=40)
        second.set_state(angle=35, carry=40)

        self.assertEqual([operation[0] for operation
                          in serialized(first.disk)],
                         ['t', 'r', 't', 't', 't'])
        self.assertEqual(serialized(first.disk), serialized(second.disk))
        expected = _spun_and_carried_pose(35, 40)
        for bench in (first, second):
            with self.subTest(bench=type(bench).__name__):
                assert_allclose(_compose_world_matrix(bench.disk), expected,
                                rtol=0, atol=1e-9)

    def test_the_two_joints_of_the_orbit_fixture_do_not_commute(self):
        spin = _turn_about(SPUN_SPIN_AT, 35, (0, 0, 1))
        carry = _translation(_orbit_delta((0, 0, 1), (0, 0, 0), SPUN_LIFT, 40))

        self.assertFalse(np.allclose(carry @ spin, spin @ carry))

    def test_an_orbit_in_the_middle_keeps_every_run_contiguous(self):
        bench = OrbitContiguityBench()
        bench.render()
        body = bench.body

        # lift (1) | swing (3) | carry (1) | the hand-written rotation
        # | the rest placement.
        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 't', 'r', 't', 't', 'r', 't'])
        swing = body.__dict__['_joint_motion']['swing']
        self.assertEqual(len(swing), 3)
        index = body.operations.index(swing[0])
        self.assertEqual(index, 1)
        self.assertEqual(body.operations[index:index + 3], swing)
        carry = body.__dict__['_joint_motion']['carry']
        self.assertEqual(len(carry), 1)
        self.assertEqual(body.operations.index(carry[0]), 4)
        # The hand-written rotation is outside the whole joint block.
        self.assertEqual(body.operations[5].serialized[1], '7')
        self.assertFalse(getattr(body.operations[6], '_motion', False))

    def test_re_binding_the_orbit_returns_it_to_its_own_slot(self):
        body = SpunAndCarried()
        body.translate(SPUN_LIFT)

        body.carry = 40
        body.spin = 35
        body.carry = -12

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t', 'r', 't', 't', 't'])
        self.assertEqual(len(body.__dict__['_joint_motion']['carry']), 1)
        self.assertEqual(len(motions(body)), 4)
        assert_allclose(_compose_world_matrix(body),
                        _spun_and_carried_pose(35, -12), rtol=0, atol=1e-9)

    ##############################################
    # 3. Cycle 1's contract, with a free joint in it (ADR-093)

    def test_a_free_joint_is_one_unbroken_run_at_its_own_slot(self):
        """Eight coordinates over three joints, bound in an order the
        class body does not show: the slide innermost, the free joint's
        whole run next, the revolute outside both."""
        bench = ScrambledStackBench()
        bench.render()
        body = bench.body

        # slide (1) | pose (3: roll, yaw, z -- its default anchor is
        # genuinely the body's own origin, pitch unbound and skipped, so
        # no centring pair) | spin (3) | the rest placement.
        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t',
                          'r', 'r', 't',
                          't', 'r', 't',
                          't'])
        run = body.__dict__['_joint_motion']['pose']
        self.assertEqual(len(run), 3)
        index = body.operations.index(run[0])
        self.assertEqual(index, 1)
        self.assertEqual(body.operations[index:index + 3], run)
        assert_allclose(_compose_world_matrix(body),
                        _slide_float_spin_pose(12, 15, 25, 60, 35),
                        rtol=0, atol=1e-12)

    def test_a_hand_written_rotation_sits_outside_the_free_joints_run(self):
        scrambled = ScrambledStackBench()
        interrupted = InterruptedStackBench()
        scrambled.render()
        interrupted.render()
        body = interrupted.body

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t',
                          'r', 'r', 't',
                          't', 'r', 't',
                          'r',
                          't'])
        run = body.__dict__['_joint_motion']['pose']
        index = body.operations.index(run[0])
        self.assertEqual(body.operations[index:index + 3], run)
        self.assertEqual(body.operations[7].serialized[1], '7')
        self.assertFalse(getattr(body.operations[8], '_motion', False))
        # The joint block is the same one the uninterrupted bench built.
        self.assertEqual(serialized(body)[:7],
                         serialized(scrambled.body)[:7])

    def test_re_binding_one_coordinate_returns_the_whole_run_to_its_slot(self):
        body = SlideFloatSpin()
        body.translate(STACK_LIFT)

        body.pose.yaw = 25
        body.spin = 35
        body.pose.z = 60
        body.slide = 12
        body.pose.roll = 15
        body.pose.roll = -40

        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['t',
                          'r', 'r', 't',
                          't', 'r', 't',
                          't'])
        self.assertEqual(len(body.__dict__['_joint_motion']['pose']), 3)
        self.assertEqual(len(body.__dict__['_joint_motion']['slide']), 1)
        self.assertEqual(len(body.__dict__['_joint_motion']['spin']), 3)
        self.assertEqual(len(motions(body)), 7)
        assert_allclose(_compose_world_matrix(body),
                        _slide_float_spin_pose(12, -40, 25, 60, 35),
                        rtol=0, atol=1e-12)

    def test_a_free_joint_composes_with_an_orbit_of_the_same_body(self):
        bench = FloatAndCarryBench()
        bench.render()
        body = bench.body

        # pose (2: one rotation, one translation -- its default anchor is
        # genuinely the body's own origin now, so no centring pair) then
        # the orbit's single translation, then the rest placement.
        self.assertEqual([operation[0] for operation in serialized(body)],
                         ['r', 't', 't', 't'])
        run = body.__dict__['_joint_motion']['pose']
        self.assertEqual(len(run), 2)
        self.assertEqual(body.operations.index(run[0]), 0)
        self.assertEqual(len(body.__dict__['_joint_motion']['carry']), 1)
        self.assertEqual(body.operations.index(
            body.__dict__['_joint_motion']['carry'][0]), 2)

        expected = (_translation(SPUN_LIFT)
                    @ _translation(_orbit_delta((0, 0, 1), (0, 0, 0),
                                                SPUN_LIFT, 40))
                    @ _free_pose(0.0, 0.0, 25.0, (0.0, 0.0, 60.0)))
        assert_allclose(_compose_world_matrix(body), expected,
                        rtol=0, atol=1e-9)


##############################################
# 1.6c The orbit: a point of the body carried round a line

# The cycloidal disk, placed 2.5 mm off the parent's axis: its own
# placed origin is the point the orbit carries, and neither the radius
# nor the phase is written anywhere.
ORBIT_LIFT = [0.0, -2.5, 0.0]

# The Internal Cycloidal Actuator's disk 1, read off its own
# `simulation/actuator/assembly.py`: the rest placement `render()`
# applies (a rotation about the document's +Y, then a translation), the
# bore's own-frame axis point the project's spec states, the rest bore
# centre the project DERIVES from those two, and the 8:1 reduction.
# Nothing here is measured by this file; the numbers are the project's.
DISK_REST_ANGLE = 15.042379656
DISK_REST_TRANSLATION = (0.897397081, -5.25, 3.895358836)
BORE_AXIS_POINT = (0.0, 0.0, -2.000)
REDUCTION = 8


def _rotate_y(point, angle):
    """The project's own Rodrigues-about-Y helper, written out."""
    radians = math.radians(angle)
    x, y, z = point
    return (x * math.cos(radians) + z * math.sin(radians),
            y,
            -x * math.sin(radians) + z * math.cos(radians))


#: The rest bore centre, DERIVED the way `_capture_disk_rest()` derives
#: it -- `R_r B + t` -- and never typed. The project's ratified spec
#: forbids writing it as a literal, and the two numbers below are its
#: own checks on the derivation, not its source: `_close()`'s recorded
#: (0.3783, -5.25, 1.9639) and the six-decimal value the change's tasks
#: quote. That quoted value is ROUNDED, and a rounded bore centre breaks
#: the algebraic identity at 3e-6 mm, which is why it is checked against
#: here rather than used.
DISK_1_BORE_CENTRE = tuple(
    centre + shift for centre, shift
    in zip(_rotate_y(BORE_AXIS_POINT, DISK_REST_ANGLE),
           DISK_REST_TRANSLATION))
DISK_1_BORE_CENTRE_RECORDED = (0.3783, -5.25, 1.9639)
DISK_1_BORE_CENTRE_QUOTED = (0.378316, -5.25, 1.963896)

#: The own-frame point of a disk placed by `rotate(DISK_REST_ANGLE,
#: [0, 1, 0])` then `translate(DISK_REST_TRANSLATION)` that lands on the
#: WORLD's origin -- the actuator axis, restated where `at` must state
#: it now that nothing carries a declared `(0, 0, 0)` there for free.
#: `R(-angle) . (-t)`, the inverse of the rest placement applied to the
#: world origin.
DISK_AXIS_POINT = tuple(
    -value for value in _rotate_y(DISK_REST_TRANSLATION, -DISK_REST_ANGLE))

# Where an orbit is read: 0 and 360 are the identity, 90 is where
# `cos` is 6.1e-17 rather than 0 in IEEE double, and 17 and 213.5 are
# ordinary angles in two different quadrants.
ORBIT_ANGLES = (0, 17, 90, 213.5, 360)


def _orbit_delta(axis, at, carried, degrees):
    """`R(degrees, axis, about at) . carried - carried`: the pure
    translation an orbit is, written out in NumPy so the expectation
    never comes from the code under test."""
    at = np.array(at, dtype=float)
    turned = (_translation(at) @ _rotation(degrees, axis)
              @ _translation(-at))
    point = np.array([carried[0], carried[1], carried[2], 1.0])
    return (turned @ point - point)[:3]


def _rest_matrix(node):
    """The node's placement with nothing bound: what the rotation block
    of every composed matrix below has to keep."""
    matrix = np.eye(4)
    for operation in node.operations:
        matrix = operation.matrix() @ matrix
    return matrix


class CarriedDisk(Solid2Node):
    """The default CARRIED point: the body's own placed origin. `at` is
    own-frame, `(0, 2.5, 0)`, the point that lands on the world's
    origin once the fixture's own `translate(ORBIT_LIFT)` is applied --
    the actuator's axis, restated where the body's own frame states
    it."""

    orbit = Orbit(axis=(0, 0, 1), at=(0, 2.5, 0), unit='deg')

    def render(self):
        return cube(2, center=True)


class BoredDisk(Solid2Node):
    """The actuator's disk: a rest placement with a non-trivial rotation
    part, and a carried point -- the bore, in the disk's OWN frame --
    that is NOT the body's own origin. `at`, own-frame, is the point
    that lands on the world's origin once the fixture's own rest
    rotation and translation are applied -- the line the ORBIT_FIXTURES
    entry states as `(0, 0, 0)` in the world, restated here directly."""

    orbit = Orbit(axis=(0, 1, 0), at=DISK_AXIS_POINT,
                 carries=BORE_AXIS_POINT, unit='deg')

    def render(self):
        return cube(2, center=True)


def _carried_disk():
    disk = CarriedDisk()
    disk.translate(ORBIT_LIFT)
    return disk


def _bored_disk():
    disk = BoredDisk()
    disk.rotate(DISK_REST_ANGLE, [0, 1, 0])
    disk.translate(list(DISK_REST_TRANSLATION))
    return disk


# The two fixtures, with the axis, anchor and carried point each states
# in the WORLD frame (the disk's rest placement being the identity for
# the first and a real rotation and translation for the second), so a
# test can compute by hand what the joint must do independently of how
# each disk's own declaration states the same physical line and point.
ORBIT_FIXTURES = (
    ('the placed origin, carried', _carried_disk, (0, 0, 1), (0, 0, 0),
     tuple(ORBIT_LIFT)),
    ('a derived bore centre, carried', _bored_disk, (0, 1, 0), (0, 0, 0),
     DISK_1_BORE_CENTRE),
)


class OrbitTest(BaseNodeTest):
    """An orbit carries a point of the body round a line and leaves the
    body's attitude alone.

    Two acceptances, and they are not the same acceptance:

    - the ATTITUDE is EXACT. The operation is a `Translation` and
      carries no rotation at all, so the rotation block of the composed
      matrix is the rest placement's, bit for bit, at every angle:
      `atol=0`.
    - the POSITION is not. `cos(90)` is 6.1e-17 in IEEE double, so
      `(cos t - 1) * v` at 90 degrees with `v = (10, 0, 0)` publishes
      -9.999999999999998 and not -10.0, and two different float
      expression trees over the same trigonometry differ by ~1e-15 mm.
      Positions are compared at `atol=1e-9`, the module's own `_SNAP`,
      and the tolerance is stated here rather than discovered by
      loosening a failing zero.
    """

    def test_carries_defaults_to_the_own_origin_and_resolves_early(self):
        """`carries` left unstated resolves to `(0, 0, 0)` -- the body's
        own origin -- at realization, before the body is placed, exactly
        like any other defaulted vector: no sentinel, no reading of the
        placement."""

        class Disk(Solid2Node):
            orbit = Orbit(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(2, center=True)

        disk = Disk()

        self.assertEqual(Disk.orbit.arguments(disk)[3], (0.0, 0.0, 0.0))

    def test_an_orbit_is_stated_in_the_bodys_own_frame(self):
        """A disk declaring `Orbit(axis=(0, 0, 1), at=(0, 2.5, 0))` with
        no `carries`: its own origin travels the circle its OWN frame
        states, wherever its parent places it."""

        class Disk(Solid2Node):
            orbit = Orbit(axis=(0, 0, 1), at=(0, 2.5, 0), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Carrier(AssemblyNode):
            disk = Disk()

            def render(self):
                self.disk.rotate(35, [1, 0, 0]).translate([12, -8, 4])

            def simulate(self):
                self.disk.orbit = 90

        carrier = Carrier()
        carrier.render()

        # Built independently of the framework's own operations list,
        # which by now also carries the bound orbit motion: the rest
        # placement `Carrier.render()` applies, and nothing else.
        rest = _translation([12, -8, 4]) @ _rotation(35, [1, 0, 0])
        composed = _compose_world_matrix(carrier.disk)
        # The attitude is untouched, whatever the parent did.
        assert_allclose(composed[:3, :3], rest[:3, :3], rtol=0, atol=0)
        # And the disk's own origin has travelled a quarter of the
        # circle of radius 2.5 about the line ITS OWN frame states --
        # not about a line the parent's placement would carry it to.
        # The delta is a displacement, computed in the disk's own frame;
        # comparing it against the WORLD-frame displacement means
        # turning it by the rest placement's own rotation block.
        local_delta = _orbit_delta((0, 0, 1), (0, 2.5, 0), (0, 0, 0), 90)
        expected_delta = rest[:3, :3] @ local_delta
        origin = np.array([0.0, 0.0, 0.0, 1.0])
        moved = composed @ origin - rest @ origin
        assert_allclose(moved[:3], expected_delta, rtol=0, atol=1e-9)

    def test_the_attitude_is_exactly_untouched(self):
        for label, factory, axis, at, carried in ORBIT_FIXTURES:
            rest = _rest_matrix(factory())[:3, :3]
            for angle in ORBIT_ANGLES:
                with self.subTest(fixture=label, angle=angle):
                    disk = factory()
                    disk.orbit = angle
                    composed = _compose_world_matrix(disk)
                    assert_allclose(composed[:3, :3], rest, rtol=0, atol=0)
                    # ... and the body DID move, or the assertion above
                    # would be satisfied by a joint that does nothing.
                    moved = np.max(np.abs(
                        composed[:3, 3] - _rest_matrix(factory())[:3, 3]))
                    if angle % 360:
                        self.assertGreater(moved, 0.1)
                    else:
                        self.assertLess(moved, 1e-9)

    def test_the_carried_point_lands_where_the_rotation_says(self):
        for label, factory, axis, at, carried in ORBIT_FIXTURES:
            rest = _rest_matrix(factory())
            # The carried point is a material point of the body: in the
            # body's own frame it is the rest placement inverted.
            local = np.linalg.inv(rest) @ np.array([*carried, 1.0])
            for angle in ORBIT_ANGLES:
                with self.subTest(fixture=label, angle=angle):
                    disk = factory()
                    disk.orbit = angle
                    landed = _compose_world_matrix(disk) @ local
                    expected = np.array(carried, dtype=float) + _orbit_delta(
                        axis, at, carried, angle)
                    assert_allclose(landed[:3], expected, rtol=0, atol=1e-9)

    def test_one_operation_and_it_is_a_translation(self):
        disk = _carried_disk()

        disk.orbit = 40
        self.assertEqual([operation[0] for operation in serialized(disk)],
                         ['t', 't'])
        self.assertEqual(len(motions(disk)), 1)

        disk.orbit = -12
        self.assertEqual([operation[0] for operation in serialized(disk)],
                         ['t', 't'])
        self.assertEqual(len(motions(disk)), 1)
        assert_allclose(numbers(serialized(disk)[0]),
                        _orbit_delta((0, 0, 1), (0, 0, 0), ORBIT_LIFT, -12),
                        rtol=0, atol=1e-9)

    def test_the_default_carried_point_is_the_placed_origin(self):
        """The default and the same point written out place the body
        identically. The default takes one derivation FEWER -- in the
        body's own frame the placed origin is exactly (0, 0, 0), with no
        inversion at all -- so the two need not be bit-identical in
        position; the attitude still is."""

        class StatedFlat(Solid2Node):
            orbit = Orbit(axis=(0, 0, 1), carries=tuple(ORBIT_LIFT),
                          unit='deg')

            def render(self):
                return cube(2, center=True)

        # Own-frame `at`: the point that lands on the world's origin
        # once this body's own rest rotation and translation are
        # applied -- the same actuator-axis point `BoredDisk` uses.
        TURNED_AT = DISK_AXIS_POINT

        class DefaultTurned(Solid2Node):
            orbit = Orbit(axis=(0, 1, 0), at=TURNED_AT, unit='deg')

            def render(self):
                return cube(2, center=True)

        class StatedTurned(Solid2Node):
            # `carries=(0, 0, 0)`, own-frame: the SAME point the default
            # resolves to -- the body's own origin -- written out.
            orbit = Orbit(axis=(0, 1, 0), at=TURNED_AT,
                          carries=(0.0, 0.0, 0.0), unit='deg')

            def render(self):
                return cube(2, center=True)

        def flat(klass):
            body = klass()
            body.translate(ORBIT_LIFT)
            return body

        def turned(klass):
            body = klass()
            body.rotate(DISK_REST_ANGLE, [0, 1, 0])
            body.translate(list(DISK_REST_TRANSLATION))
            return body

        cases = (('translate', flat, CarriedDisk, StatedFlat),
                 ('rotate+translate', turned, DefaultTurned, StatedTurned))
        for label, place, default_class, stated_class in cases:
            for angle in ORBIT_ANGLES:
                with self.subTest(placement=label, angle=angle):
                    default, stated = place(default_class), place(stated_class)
                    default.orbit = angle
                    stated.orbit = angle
                    one = _compose_world_matrix(default)
                    other = _compose_world_matrix(stated)
                    assert_allclose(one[:3, :3], other[:3, :3],
                                    rtol=0, atol=0)
                    assert_allclose(one[:3, 3], other[:3, 3],
                                    rtol=0, atol=1e-12)
                    if angle % 360:
                        self.assertGreater(
                            np.max(np.abs(one[:3, 3]
                                          - _rest_matrix(place(
                                              default_class))[:3, 3])),
                            0.1)

    def test_the_anchor_may_be_any_point_of_the_line(self):
        class Raised(Solid2Node):
            # `(0, 2.5, 40)`: the same own-frame LINE `CarriedDisk`
            # states -- `x=0, y=2.5` -- at a different point along it.
            orbit = Orbit(axis=(0, 0, 1), at=(0, 2.5, 40), unit='deg')

            def render(self):
                return cube(2, center=True)

        for angle in ORBIT_ANGLES:
            with self.subTest(angle=angle):
                origin, raised = _carried_disk(), Raised()
                raised.translate(ORBIT_LIFT)
                origin.orbit = angle
                raised.orbit = angle
                assert_allclose(_compose_world_matrix(raised),
                                _compose_world_matrix(origin),
                                rtol=0, atol=1e-9)
                if angle % 360:
                    self.assertGreater(
                        np.max(np.abs(_compose_world_matrix(raised)[:3, 3]
                                      - np.array(ORBIT_LIFT))), 0.1)

    def test_a_carried_point_on_the_axis_is_refused_by_name(self):
        """The V8's connecting rod: its big end is at the unit's origin,
        which is ON the crank axis, so the default carried point does
        not move and the author meant `carries`."""

        class ConRod(Solid2Node):
            orbit = Orbit(axis=(1, 0, 0), unit='deg')

            def render(self):
                return cube(2, center=True)

        rod = ConRod()

        with self.assertRaises(ValueError) as raised:
            rod.orbit = 30

        message = str(raised.exception)
        # The axis reads as the framework's own snapped exact value; the
        # anchor and the carried point are NOT snapped -- they are what
        # the author wrote (here, both the class-declared default) --
        # and both read as the same floats.
        for expected in ('ConRod', 'orbit', 'carries',
                         '(1, 0, 0)', '(0.0, 0.0, 0.0)', '0.0'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)
        self.assertEqual(motions(rod), [])

    def test_a_malformed_carries_fails_at_realization(self):
        built = []

        class Watcher(Solid2Node):
            def __init__(self, **kwargs):
                built.append(self)
                super().__init__(**kwargs)

            def render(self):
                return cube(1, center=True)

        def raising(node):
            raise RuntimeError('no such position')

        elsewhere = Length(5.0)
        elsewhere._name = 'elsewhere'

        cases = {
            'two components': (0, 5),
            'an undeclared token': (0, elsewhere, 0),
            'a callable that raises': raising,
        }
        for label, carries in cases.items():
            with self.subTest(case=label):
                built.clear()

                class Bad(AssemblyNode):
                    orbit = Orbit(axis=(0, 0, 1), carries=carries,
                                  unit='deg')

                    watched = Watcher()

                with self.assertRaises(ParameterError) as raised:
                    Bad()

                message = str(raised.exception)
                for expected in ('Bad', 'orbit', 'carries'):
                    self.assertIn(expected, message)
                self.assertEqual(built, [])

    def test_a_symbolic_binding_publishes_the_trigonometry(self):
        class Carrier(AssemblyNode):
            disk = CarriedDisk()

            def render(self):
                self.disk.translate(ORBIT_LIFT)

            def simulate(self):
                self.disk.orbit = self.time * 360

        carrier = Carrier()
        carrier.render()

        published = serialized(carrier.disk)[0]
        self.assertEqual(published[0], 't')
        components = list(published[1])
        self.assertIn('sin(', components[0])
        self.assertIn('$t', components[0])
        self.assertIn('cos(', components[1])
        self.assertIn('$t', components[1])
        # The component the circle does not reach is the plain number,
        # not an expression multiplied by zero.
        self.assertEqual(components[2], '0')

        carrier.set_keyframe(0.25)
        keyframed = list(serialized(carrier.disk)[0][1])
        for component in keyframed:
            with self.subTest(component=component):
                float(component)
        assert_allclose([float(component) for component in keyframed],
                        _orbit_delta((0, 0, 1), (0, 0, 0), ORBIT_LIFT, 90.0),
                        rtol=0, atol=1e-9)

        carrier.clear_keyframe()
        self.assertEqual(list(serialized(carrier.disk)[0][1]), components)

        document = serialize_node(carrier, lambda rigid: rigid.name)
        keys = set(document)
        for child in document.get('children', ()):
            keys.update(child)
        self.assertLessEqual(
            keys, {'name', 'type', 'color', 'mtime', 'operations', 'model',
                   'children', 'flexible', 'piece'})

    def test_a_relation_drives_an_orbit_and_inverts(self):
        class Shaft(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(2, center=True)

        class Machine(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')

            shaft = Shaft()
            disk = CarriedDisk()

            shaft.turn.drives(disk.orbit)

            def render(self):
                self.disk.translate(ORBIT_LIFT)

            def simulate(self):
                self.shaft.turn = self.angle

        class Geared(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')

            shaft = Shaft()
            disk = CarriedDisk()

            shaft.turn.drives(disk.orbit, ratio=-0.5)

            def render(self):
                self.disk.translate(ORBIT_LIFT)

            def simulate(self):
                self.shaft.turn = self.angle

        class Backwards(AssemblyNode):
            """The DRIVEN end bound, so the relation is solved
            backwards through the orbit's coordinate."""

            carry = Driver(default=0.0, unit='deg')

            shaft = Shaft()
            disk = CarriedDisk()

            shaft.turn.drives(disk.orbit, ratio=-0.5)

            def render(self):
                self.disk.translate(ORBIT_LIFT)

            def simulate(self):
                self.disk.orbit = self.carry

        machine = Machine()
        machine.set_state(angle=40)
        self.assertAlmostEqual(machine.disk.orbit.value, 40.0)
        assert_allclose(numbers(serialized(machine.disk)[0]),
                        _orbit_delta((0, 0, 1), (0, 0, 0), ORBIT_LIFT, 40.0),
                        rtol=0, atol=1e-9)

        geared = Geared()
        geared.set_state(angle=40)
        self.assertAlmostEqual(geared.disk.orbit.value, -20.0)

        backwards = Backwards()
        backwards.set_state(carry=-20.0)
        self.assertAlmostEqual(backwards.shaft.turn.value, 40.0)
        assert_allclose(numbers(serialized(backwards.disk)[0]),
                        _orbit_delta((0, 0, 1), (0, 0, 0), ORBIT_LIFT, -20.0),
                        rtol=0, atol=1e-9)

    def test_a_range_on_an_orbit_is_the_inherited_refusal(self):
        """A CHARACTERISATION test: `range` is `Joint`'s and this cycle
        writes no new code for it. It is here because no project has yet
        declared a range on an orbit, so nothing else pins the
        behaviour on this kind."""

        class Limited(Solid2Node):
            orbit = Orbit(axis=(0, 0, 1), at=(0, 2.5, 0), range=(-90, 90),
                         unit='deg')

            def render(self):
                return cube(2, center=True)

        limited = Limited()

        with self.assertRaises(JointRangeError) as raised:
            limited.orbit = 170

        message = str(raised.exception)
        for expected in ('Limited', 'orbit', '170', '-90', '90', 'deg'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)
        self.assertEqual(motions(limited), [])

        limited.orbit = -90
        limited.orbit = 90
        self.assertEqual(limited.orbit.value, 90)

    def test_the_orbit_is_enumerable_as_a_joint_and_as_a_port(self):
        # The export itself is asserted with the other kinds, in
        # `test_the_kinds_are_exported_from_the_joints_module`.
        self.assertEqual(list(declared_joints(CarriedDisk)), ['orbit'])
        self.assertIsInstance(declared_joints(CarriedDisk)['orbit'], Orbit)

        ports = declared_ports(CarriedDisk)
        self.assertIn('orbit', ports)
        self.assertIsInstance(ports['orbit'], RotationalPort)
        self.assertEqual(ports['orbit'].unit, 'deg')

        self.assertEqual(list(declared_joints(SpunAndCarried)),
                         ['spin', 'carry'])


##############################################
# 1.6d The four projects' own algebra, as fixtures

class ProjectAlgebraTest(BaseNodeTest):
    """What the projects that asked for the orbit then write, checked
    against the arithmetic they write today.

    Neither of these two fixtures is a measurement over a real machine:
    they reproduce a project's own numbers and its own hand-written
    composition inside this test file. The measurement over the machines
    themselves is the four projects' adoption at stage B, in their own
    repositories, and it is not this cycle's evidence.
    """

    def test_the_cycloidal_actuators_two_forms_are_one_transform(self):
        """The Internal Cycloidal Actuator's identity, in full.

        Writing `rest = T_t R_r`, `B = BORE_AXIS_POINT`,
        `c0 = R_r B + t` the rest bore centre and
        `sigma = -theta / 8 + mesh_phase`, the project's three
        hand-written operations give

            T_t R_r T_carry R_sigma T_(-B)

        and the orbit-plus-spin form gives

            T_Delta . T_c0 R_sigma T_(-c0) . T_t R_r

        Both are `T_c(theta) R_(r+sigma) T_(-B)`. The left-hand side is
        built here from the project's own `_rotate_y` helper; the
        right-hand side is the framework's, through a `spin` declared
        before an `orbit` on one class.
        """

        class CycloidalDisk(Solid2Node):
            # Declaration order IS composition order (ADR-093): the
            # spin is innermost, about the disk's own bore, and the
            # orbit carries that bore round the actuator axis. Both are
            # stated in the disk's OWN frame -- the project's own spec
            # literal, BORE_AXIS_POINT -- rather than the rest-placement
            # -derived DISK_1_BORE_CENTRE the two forms below reconcile.
            spin = Revolute(axis=(0, 1, 0), at=BORE_AXIS_POINT,
                            unit='deg')
            # `at`, own-frame: the actuator axis passes through the
            # world's origin, restated as the point that lands there
            # once this disk's own rest placement is applied.
            orbit = Orbit(axis=(0, 1, 0),
                          at=DISK_AXIS_POINT,
                          carries=BORE_AXIS_POINT, unit='deg')

            def render(self):
                return cube(2, center=True)

        def by_hand(theta, mesh_phase):
            """`_simulate_disk`, as the project writes it today: three
            operations composed INSIDE the rest placement."""
            centre = DISK_1_BORE_CENTRE
            sigma = -theta / REDUCTION + mesh_phase
            orbited = _rotate_y(centre, theta)
            delta = tuple(o - c for o, c in zip(orbited, centre))
            own_frame = _rotate_y(delta, -DISK_REST_ANGLE)
            carry = tuple(b + d for b, d in zip(BORE_AXIS_POINT, own_frame))
            rest = (_translation(DISK_REST_TRANSLATION)
                    @ _rotation(DISK_REST_ANGLE, (0, 1, 0)))
            return (rest @ _translation(carry)
                    @ _rotation(sigma, (0, 1, 0))
                    @ _translation(-np.array(BORE_AXIS_POINT)))

        rotations, positions = [], []
        for mesh_phase in (0.0, 4.5):
            for theta in (0.0, 17.0, 90.0, 213.5, 360.0):
                with self.subTest(mesh_phase=mesh_phase, theta=theta):
                    disk = CycloidalDisk()
                    disk.rotate(DISK_REST_ANGLE, [0, 1, 0])
                    disk.translate(list(DISK_REST_TRANSLATION))
                    disk.spin = -theta / REDUCTION + mesh_phase
                    disk.orbit = theta

                    framework = _compose_world_matrix(disk)
                    expected = by_hand(theta, mesh_phase)
                    rotations.append(
                        np.max(np.abs(framework[:3, :3] - expected[:3, :3])))
                    positions.append(
                        np.max(np.abs(framework[:3, 3] - expected[:3, 3])))
                    # Two acceptances, not one: the orbit adds NO
                    # rotation, so both sides carry exactly R_(r+sigma)
                    # and the rotation blocks agree bit for bit; the
                    # positions are two float expression trees over the
                    # same trigonometry and agree to 1e-9 mm.
                    assert_allclose(framework[:3, :3], expected[:3, :3],
                                    rtol=0, atol=0)
                    assert_allclose(framework[:3, 3], expected[:3, 3],
                                    rtol=0, atol=1e-9)
        # Recorded in the change's evidence.md, both of them.
        print(f'\nactuator identity: max rotation deviation '
              f'{max(rotations):.3e}, max position deviation '
              f'{max(positions):.3e} mm')

    def test_the_actuators_radius_and_phase_are_derived_not_typed(self):
        """The number that proves the derivation replaces what the
        project may not type: its ratified spec forbids writing the rest
        bore centre or the journal position as a literal, so the
        2.000 mm eccentricity and the -79.095935297 degree phase have to
        come out of the point and the line."""
        radius, phase = _derived_radius_and_phase(
            axis=(0, 1, 0), at=(0, 0, 0), carried=DISK_1_BORE_CENTRE,
            reference=(1, 0, 0))

        self.assertAlmostEqual(radius, 2.0000, places=4)
        self.assertAlmostEqual(phase, -79.095935297, places=3)
        # And the derived centre itself is the one the project records
        # and the one this change's tasks quote.
        for derived, recorded, quoted in zip(DISK_1_BORE_CENTRE,
                                             DISK_1_BORE_CENTRE_RECORDED,
                                             DISK_1_BORE_CENTRE_QUOTED):
            self.assertAlmostEqual(derived, recorded, places=3)
            self.assertAlmostEqual(derived, quoted, places=4)

    def test_the_dogs_swung_offset_is_what_an_orbit_publishes(self):
        """YouCanBuildDog's `R(theta) . s - s`, for the two spans its
        layout measures, against an `Orbit` anchored at the chassis
        pivot and carrying the knee pivot."""

        def swung_offset(angle, span):
            """`simulation/leg.py`, written out."""
            span_y, span_z = span
            radians = math.radians(angle)
            turned_y = span_y * math.cos(radians) - span_z * math.sin(radians)
            turned_z = span_y * math.sin(radians) + span_z * math.cos(radians)
            return turned_y - span_y, turned_z - span_z

        for label, pivot, span, radius, phase in DOG_LEGS:
            knee = (0.0, pivot[0] + span[0], pivot[1] + span[1])
            chassis = (0.0, pivot[0], pivot[1])

            class Shin(Solid2Node):
                carry = Orbit(axis=(1, 0, 0), at=chassis, carries=knee,
                              unit='deg')

                def render(self):
                    return cube(2, center=True)

            for angle in (0.0, 17.0, -35.0, 90.0):
                with self.subTest(leg=label, angle=angle):
                    shin = Shin()
                    # The five carried bodies of a leg have five
                    # different rest placements and ONE offset: this is
                    # why the knee pivot has to be named.
                    shin.translate([0.0, 12.0, -30.0])
                    shin.carry = angle

                    expected = swung_offset(angle, span)
                    published = numbers(serialized(shin)[0])
                    assert_allclose(published,
                                    [0.0, expected[0], expected[1]],
                                    rtol=0, atol=1e-9)

            derived_radius, derived_phase = _derived_radius_and_phase(
                axis=(1, 0, 0), at=chassis, carried=knee, reference=(0, 1, 0))
            with self.subTest(leg=label, derived='radius'):
                self.assertAlmostEqual(derived_radius, radius, places=4)
            with self.subTest(leg=label, derived='phase'):
                self.assertAlmostEqual(derived_phase, phase, places=3)


# YouCanBuildDog's two measured link spans, read off its own
# `simulation/layout.py`, with the chassis pivots they hang from and the
# radius and phase its reviewed proposal TYPED as `radius=`/`phase=`.
# Three legs span 40.0000 mm; the back-left leg is 0.076 mm short and is
# not the same part as its siblings.
#
# One number differs from that proposal by 7e-4 degrees: it typed
# -55.104 for the back-left leg where its own span (22.8404, -32.7450)
# is -55.1033 degrees, a transcription of the third decimal. The
# framework derives the span's own angle; the project's typed figure is
# the one that is slightly wrong, which is the argument for deriving it.
DOG_LEGS = (
    ('front (three of the four legs)', (-38.6569, -15.3431),
     (22.9431, -32.7661), 40.0000, -55.000),
    ('back-left (0.076 mm short)', (66.4458, -15.3642),
     (22.8404, -32.7450), 39.9239, -55.1033),
)


def _derived_radius_and_phase(axis, at, carried, reference):
    """The radius and the phase the FRAMEWORK derives, read off its own
    construction rather than recomputed here: `_orbit_frame` is the
    function `Orbit.placement` calls, and neither number is a declared
    argument anywhere.

    The phase is an angle about the line and needs a reference direction
    in the plane to be measured from; each project states its own, so
    the caller passes it. The positive sense is the joint's own: `b`,
    the axis crossed with the radius vector.
    """
    from solid_node.motion.joints import _orbit_frame

    axis = np.array(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    across, _quarter, radius = _orbit_frame(tuple(axis), at, carried)
    reference = np.array(reference, dtype=float)
    quarter = np.cross(axis, reference)
    phase = math.degrees(math.atan2(np.dot(across, quarter),
                                    np.dot(across, reference)))
    return radius, phase


##############################################
# 1.6d The free joint: six coordinates on one floating body

# The seven poses `evidence/probe_matrix.py` measured the hexapod's own
# four hand-written calls at, two of them at gimbal lock. The numbers
# there were taken BEFORE a line of `Free` existed, against a NumPy
# product, so this fixture inherits a target rather than inventing one.
FREE_POSES = [
    (0.0, 0.0, 0.0, 0.0),
    (12.0, 8.0, 25.0, 165.0),
    (-15.0, -15.0, 0.0, 70.0),
    (5.0, -3.0, 180.0, 120.0),
    (90.0, 0.0, 45.0, 100.0),
    (0.0, 90.0, 30.0, 60.0),
    (-33.3, 21.7, -119.9, 143.25),
]

# The six names, in declaration order, with the domain and the unit each
# carries under `angle_unit='deg'` and `length_unit='mm'`.
FREE_COORDINATES = (
    ('pose.roll', 'rotational', 'deg'),
    ('pose.pitch', 'rotational', 'deg'),
    ('pose.yaw', 'rotational', 'deg'),
    ('pose.x', 'translational', 'mm'),
    ('pose.y', 'translational', 'mm'),
    ('pose.z', 'translational', 'mm'),
)


class FloatingChassis(Solid2Node):
    """The hexapod's case: a body its parent does NOT place, so the rest
    placement is the identity and the default anchor is both the
    parent's origin and the body's own placed origin."""

    pose = Free(angle_unit='deg', length_unit='mm')

    def render(self):
        return cube(2, center=True)


class FloatingBench(AssemblyNode):
    """Binds the four freedoms the hexapod binds, in the order its own
    `simulate()` writes them, and leaves `x` and `y` alone."""

    roll = Driver(default=0.0, unit='deg')
    pitch = Driver(default=0.0, unit='deg')
    yaw = Driver(default=0.0, unit='deg')
    height = Driver(default=0.0, unit='mm')

    chassis = FloatingChassis()

    def render(self):
        pass

    def simulate(self):
        self.chassis.pose.roll = self.roll
        self.chassis.pose.pitch = self.pitch
        self.chassis.pose.yaw = self.yaw
        self.chassis.pose.z = self.height


class ReversedFloatingBench(FloatingBench):
    """The same four bound in the opposite order: the joint is one
    composition, so the pose may not notice."""

    def simulate(self):
        self.chassis.pose.z = self.height
        self.chassis.pose.yaw = self.yaw
        self.chassis.pose.pitch = self.pitch
        self.chassis.pose.roll = self.roll


# The anchored case: a body its parent DOES place, by a rotation and a
# translation, so a reader can tell the joint's own rest frame from the
# parent's -- and the anchor rides neither: it is read exactly as
# declared, with nothing carried in from either.
ANCHOR_TILT = 25.0
ANCHOR_LIFT = [0.0, 12.0, 4.0]
FREE_AT = (0.0, 30.0, 5.0)


class AnchoredFloat(Solid2Node):
    """A free joint whose rotations pass through a point of the body's
    OWN rest frame that is not its own origin -- stated directly, and
    unaffected by whatever its parent's `render()` does to place it."""

    pose = Free(at=FREE_AT, angle_unit='deg', length_unit='mm')

    def render(self):
        return cube(2, center=True)


class PlainFloat(Solid2Node):
    """The same body with the DEFAULT anchor.

    Its parent turns it but does NOT move it, so its placed origin IS
    the parent frame's origin and the default anchor carries to
    `(0, 0, 0)`: the case where the centring pair is not emitted at all.
    A `Free()` on a body its parent TRANSLATES turns about the parent's
    origin and does emit the pair, which is the default `at` doing
    exactly what every other joint's does."""

    pose = Free(angle_unit='deg', length_unit='mm')

    def render(self):
        return cube(2, center=True)


class AnchoredBench(AssemblyNode):

    body = AnchoredFloat()

    def render(self):
        self.body.rotate(ANCHOR_TILT, [1, 0, 0]).translate(ANCHOR_LIFT)


class PlainBench(AssemblyNode):

    body = PlainFloat()

    def render(self):
        self.body.rotate(ANCHOR_TILT, [1, 0, 0])


def _anchored_rest():
    """The rest placement `AnchoredBench.render()` applies, built here
    rather than read off the node: the expected matrices in this section
    have to be independent of the framework's own `operation.matrix()`."""
    return _translation(ANCHOR_LIFT) @ _rotation(ANCHOR_TILT, (1, 0, 0))


def _free_pose(roll, pitch, yaw, offset, anchor=(0.0, 0.0, 0.0)):
    """A free joint's own contribution, read directly in the declaring
    body's own rest frame: three rotations about that frame's FIXED
    directions through the anchor, then the offset along those same
    directions -- nothing carried in from the parent's frame, and
    nothing of the body's rest placement composed in here. As an
    application order, innermost first, that is
    `R(roll, x) . R(pitch, y) . R(yaw, z) . T(offset)`; a caller
    composes the body's rest placement OUTSIDE this, by hand, exactly as
    it would for any other joint's own contribution.
    """
    anchor = np.array(anchor, dtype=float)
    return (_translation(offset) @ _translation(anchor)
            @ _rotation(yaw, (0, 0, 1)) @ _rotation(pitch, (0, 1, 0))
            @ _rotation(roll, (1, 0, 0)) @ _translation(-anchor))


def _to_chassis(point, roll, pitch, yaw, height):
    """`Chassis._to_chassis`, transcribed unchanged from
    `projects/Robots/hexapod_spiderbot_model/simulation/spiderbot.py`
    lines 146-163, with the port reads replaced by arguments.

    Every leg solution in that model runs a foot target through this to
    reach the chassis's frame, so it is the project's own statement of
    what the composition IS, written before the framework had one.
    """
    from solid_node.math import cos, sin

    px, py, pz = point[0], point[1], point[2] - height

    cy, sy = cos(-yaw), sin(-yaw)
    px, py = px * cy - py * sy, px * sy + py * cy

    cp, sp = cos(-pitch), sin(-pitch)
    px, pz = px * cp + pz * sp, -px * sp + pz * cp

    cr, sr = cos(-roll), sin(-roll)
    py, pz = py * cr - pz * sr, py * sr + pz * cr

    return np.array([px, py, pz])


class FreeJointTest(BaseNodeTest):
    """A body with no parent to be jointed to: one declaration, six
    coordinates, and a composition fixed by the contract."""

    ##############################################
    # 1.2 The six coordinates

    def test_the_six_coordinates_enumerate_under_dotted_names(self):
        ports = declared_ports(FloatingChassis)

        self.assertEqual(list(ports),
                         [name for name, _domain, _unit
                          in FREE_COORDINATES])
        self.assertNotIn('pose', ports)
        for name, domain, unit in FREE_COORDINATES:
            with self.subTest(coordinate=name):
                self.assertIsInstance(ports[name], Port)
                self.assertEqual(ports[name].domain, domain)
                self.assertEqual(ports[name].unit, unit)
                self.assertEqual(ports[name].name, name)

        # One joint, one entry, whatever it owns.
        self.assertEqual(list(declared_joints(FloatingChassis)), ['pose'])
        self.assertIsInstance(declared_joints(FloatingChassis)['pose'], Free)

    def test_two_instances_read_their_own_six_slots(self):
        one = FloatingChassis()
        other = FloatingChassis()

        one.pose.roll = 12.0
        one.pose.z = 165.0

        self.assertEqual(one.pose.roll.value, 12.0)
        self.assertEqual(one.pose.z.value, 165.0)
        self.assertIsInstance(one.pose.roll, BoundPort)
        self.assertEqual(one.pose.roll.domain, 'rotational')
        self.assertEqual(one.pose.z.unit, 'mm')
        self.assertIsNone(other.pose.roll.value)
        self.assertIsNone(other.pose.z.value)

    def test_an_unknown_coordinate_is_refused_by_name(self):
        chassis = FloatingChassis()

        with self.assertRaises(AttributeError) as raised:
            chassis.pose.twist

        message = str(raised.exception)
        for expected in ('twist', 'pose', 'roll', 'yaw', 'z'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    ##############################################
    # 1.3 The composition

    def test_the_composition_is_the_one_the_hexapod_hand_inverts(self):
        worst = 0.0
        for roll, pitch, yaw, height in FREE_POSES:
            with self.subTest(pose=(roll, pitch, yaw, height)):
                bench = FloatingBench()
                bench.set_state(roll=roll, pitch=pitch, yaw=yaw,
                                height=height)

                placed = _compose_world_matrix(bench.chassis)
                expected = _free_pose(roll, pitch, yaw, (0.0, 0.0, height))
                worst = max(worst,
                            float(np.max(np.abs(placed - expected))))
                assert_allclose(placed, expected, rtol=0, atol=1e-12)
        self.assertLess(worst, 1e-12)

    def test_the_anchored_composition_is_read_in_the_bodys_own_frame(self):
        """The rest placement AnchoredBench.render() applies -- a real
        rotation and a real translation -- composes OUTSIDE the joint's
        own contribution, and does not enter it: the anchor and the
        three directions are exactly `FREE_AT` and the frame's own axes,
        with nothing conjugated through the rest placement to get
        there."""
        rest = _anchored_rest()
        worst = 0.0
        for roll, pitch, yaw, height in FREE_POSES:
            with self.subTest(pose=(roll, pitch, yaw, height)):
                bench = AnchoredBench()
                bench.render()
                body = bench.body
                body.pose.roll = roll
                body.pose.pitch = pitch
                body.pose.yaw = yaw
                body.pose.z = height

                placed = _compose_world_matrix(body)
                expected = rest @ _free_pose(
                    roll, pitch, yaw, (0.0, 0.0, height), anchor=FREE_AT)
                worst = max(worst,
                            float(np.max(np.abs(placed - expected))))
                assert_allclose(placed, expected, rtol=0, atol=1e-12)
        self.assertLess(worst, 1e-12)

    ##############################################
    # 1.4 The hexapod's own inverse

    def test_the_hexapods_own_inverse_round_trips(self):
        """The framework's composition is the one the project's leg
        solutions depend on: `_to_chassis` brings a point the `Free`
        carried back to where it started."""
        probe_point = np.array([37.0, -91.5, 12.25, 1.0])
        worst = 0.0
        for roll, pitch, yaw, height in FREE_POSES:
            with self.subTest(pose=(roll, pitch, yaw, height)):
                bench = FloatingBench()
                bench.set_state(roll=roll, pitch=pitch, yaw=yaw,
                                height=height)

                world = _compose_world_matrix(bench.chassis) @ probe_point
                back = _to_chassis(world[:3], roll, pitch, yaw, height)
                worst = max(worst,
                            float(np.max(np.abs(back - probe_point[:3]))))
                assert_allclose(back, probe_point[:3], rtol=0, atol=1e-9)
        self.assertLess(worst, 1e-9)

    ##############################################
    # 1.5-1.6 Unbound coordinates

    def test_unbound_coordinates_place_nothing_and_still_read_unbound(self):
        bench = FloatingBench()
        bench.set_state(roll=12.0, pitch=8.0, yaw=25.0, height=165.0)
        chassis = bench.chassis

        self.assertIsNone(chassis.pose.x.value)
        self.assertIsNone(chassis.pose.y.value)
        ports = declared_ports(FloatingChassis)
        self.assertIn('pose.x', ports)
        self.assertIn('pose.y', ports)

        translation = serialized(chassis)[-1]
        self.assertEqual(translation[0], 't')
        self.assertEqual(translation[1][0], '0')
        self.assertEqual(translation[1][1], '0')
        self.assertEqual(float(translation[1][2]), 165.0)

        # And the pose is the pose with those two bound to zero.
        bound = FloatingChassis()
        bound.pose.roll = 12.0
        bound.pose.pitch = 8.0
        bound.pose.yaw = 25.0
        bound.pose.x = 0.0
        bound.pose.y = 0.0
        bound.pose.z = 165.0
        assert_allclose(_compose_world_matrix(chassis),
                        _compose_world_matrix(bound), rtol=0, atol=0)

    def test_all_six_unbound_places_nothing_at_all(self):
        """Weakly red on the name alone: what it distinguishes is a
        placement that runs at realization, or one that publishes six
        identity operations for a body nobody posed."""
        chassis = FloatingChassis()

        self.assertEqual(motions(chassis), [])
        self.assertEqual(serialized(chassis), [])
        assert_allclose(_compose_world_matrix(chassis), np.eye(4),
                        rtol=0, atol=0)

    ##############################################
    # 1.7-1.8 Binding order and re-binding

    def test_the_binding_order_of_the_six_does_not_matter(self):
        forward = FloatingBench()
        backward = ReversedFloatingBench()

        forward.set_state(roll=12.0, pitch=8.0, yaw=25.0, height=165.0)
        backward.set_state(roll=12.0, pitch=8.0, yaw=25.0, height=165.0)

        self.assertEqual(serialized(forward.chassis),
                         serialized(backward.chassis))
        assert_allclose(_compose_world_matrix(forward.chassis),
                        _compose_world_matrix(backward.chassis),
                        rtol=0, atol=0)

        # And with all six bound, in declaration order and reversed.
        values = {'roll': 12.0, 'pitch': 8.0, 'yaw': 25.0,
                  'x': 3.0, 'y': -4.0, 'z': 165.0}
        names = ['roll', 'pitch', 'yaw', 'x', 'y', 'z']
        benches = []
        for order in (names, list(reversed(names)),
                      ['z', 'roll', 'y', 'yaw', 'x', 'pitch']):
            chassis = FloatingChassis()
            for name in order:
                setattr(chassis.pose, name, values[name])
            benches.append(chassis)
        for other in benches[1:]:
            with self.subTest(order='scrambled'):
                self.assertEqual(serialized(benches[0]), serialized(other))
                assert_allclose(_compose_world_matrix(benches[0]),
                                _compose_world_matrix(other),
                                rtol=0, atol=0)
        assert_allclose(_compose_world_matrix(benches[0]),
                        _free_pose(12.0, 8.0, 25.0, (3.0, -4.0, 165.0)),
                        rtol=0, atol=1e-12)

    def test_re_binding_one_coordinate_re_places_the_whole_joint(self):
        chassis = FloatingChassis()
        chassis.pose.roll = 12.0
        chassis.pose.pitch = 8.0
        chassis.pose.yaw = 25.0
        chassis.pose.x = 3.0
        chassis.pose.y = -4.0
        chassis.pose.z = 165.0

        before = serialized(chassis)
        first = _compose_world_matrix(chassis)

        chassis.pose.roll = -30.0

        self.assertEqual([operation[0] for operation in serialized(chassis)],
                         [operation[0] for operation in before])
        self.assertEqual(chassis.pose.pitch.value, 8.0)
        self.assertEqual(chassis.pose.yaw.value, 25.0)
        self.assertEqual(chassis.pose.z.value, 165.0)
        assert_allclose(_compose_world_matrix(chassis),
                        _free_pose(-30.0, 8.0, 25.0, (3.0, -4.0, 165.0)),
                        rtol=0, atol=1e-12)

        chassis.pose.roll = 12.0

        assert_allclose(_compose_world_matrix(chassis), first,
                        rtol=0, atol=0)
        self.assertEqual(len(motions(chassis)), 4)

    ##############################################
    # 1.8b The three directions are the body's own

    def test_the_three_directions_are_the_bodys_own_as_literals(self):
        """A `Free` on a body its parent ROTATES: the published
        rotations carry the frame's own three literal directions
        exactly, unaffected by whatever the parent did."""

        class Loose(Solid2Node):
            pose = Free(angle_unit='deg', length_unit='mm')

            def render(self):
                return cube(2, center=True)

        class Tilted(AssemblyNode):
            body = Loose()

            def render(self):
                self.body.rotate(37, [0, 1, 0]).rotate(52, [1, 0, 0])

            def simulate(self):
                self.body.pose.roll = 10.0
                self.body.pose.pitch = 20.0
                self.body.pose.yaw = 30.0

        tilted = Tilted()
        tilted.render()

        rotations = [operation for operation in serialized(tilted.body)
                    if operation[0] == 'r'][:3]
        axes = [list(operation[2]) for operation in rotations]
        self.assertEqual(axes, [[1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def test_a_floating_body_floats_along_its_own_axes(self):
        """A bound `x`, on a body whose rest placement is a rotation:
        the translation runs along the body's own rest-frame x, not
        along whatever the rotated body's parent would call x."""

        class Loose(Solid2Node):
            pose = Free(angle_unit='deg', length_unit='mm')

            def render(self):
                return cube(2, center=True)

        class Tilted(AssemblyNode):
            body = Loose()

            def render(self):
                self.body.rotate(90, [0, 0, 1])

            def simulate(self):
                self.body.pose.yaw = 40.0
                self.body.pose.x = 12.0

        tilted = Tilted()
        tilted.render()

        translation = [operation for operation in serialized(tilted.body)
                       if operation[0] == 't'][0]
        self.assertEqual(translation[1][0], '12.0')
        self.assertEqual(translation[1][1], '0')
        self.assertEqual(translation[1][2], '0')

    def test_a_defaulted_free_joint_on_a_translated_body_emits_no_centring(
            self):
        """The silent case, isolated: a `Free` with no `at` on a body
        its parent TRANSLATES turns about the body's OWN origin, not the
        parent's -- so it emits no centring pair at all, where the old
        parent-frame reading would have carried a nonzero local anchor
        and emitted one."""

        class Loose(Solid2Node):
            pose = Free(angle_unit='deg', length_unit='mm')

            def render(self):
                return cube(2, center=True)

        class Carried(AssemblyNode):
            body = Loose()

            def render(self):
                self.body.translate([15, -8, 3])

            def simulate(self):
                self.body.pose.yaw = 40.0

        carried = Carried()
        carried.render()

        self.assertEqual([operation[0] for operation
                          in serialized(carried.body)], ['r', 't'])

    ##############################################
    # 1.9 The anchor

    def test_an_anchored_free_joint_turns_about_its_anchor(self):
        anchored = AnchoredBench()
        anchored.render()
        anchored.body.pose.yaw = 40.0

        plain = PlainBench()
        plain.render()
        plain.body.pose.yaw = 40.0

        self.assertEqual([operation[0] for operation
                          in serialized(anchored.body)],
                         ['t', 'r', 't', 'r', 't'])
        self.assertEqual([operation[0] for operation
                          in serialized(plain.body)],
                         ['r', 'r'])

        assert_allclose(_compose_world_matrix(anchored.body),
                        _anchored_rest() @ _free_pose(
                            0.0, 0.0, 40.0, (0.0, 0.0, 0.0), anchor=FREE_AT),
                        rtol=0, atol=1e-12)
        assert_allclose(_compose_world_matrix(plain.body),
                        _rotation(ANCHOR_TILT, (1, 0, 0))
                        @ _free_pose(0.0, 0.0, 40.0, (0.0, 0.0, 0.0)),
                        rtol=0, atol=1e-12)
        # The anchored body's own placed origin stands off the line and
        # travels; the plain one's IS on it and does not.
        origin = np.array([0.0, 0.0, 0.0, 1.0])
        moved = _compose_world_matrix(anchored.body) @ origin
        self.assertGreater(
            float(np.linalg.norm(moved[:3] - np.array(ANCHOR_LIFT))), 10.0)
        assert_allclose((_compose_world_matrix(plain.body) @ origin)[:3],
                        [0.0, 0.0, 0.0], rtol=0, atol=1e-12)

    ##############################################
    # 1.10-1.11 The refusals

    def test_assigning_the_joint_as_a_whole_is_refused(self):
        chassis = FloatingChassis()

        with self.assertRaises(AttributeError) as raised:
            chassis.pose = 12.0

        message = str(raised.exception)
        for expected in ('pose', 'FloatingChassis', 'roll', 'pitch', 'yaw',
                         'x', 'y', 'z'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)
        self.assertEqual(motions(chassis), [])

    def test_an_axis_and_a_range_are_refused_at_the_declaration(self):
        for keyword, argument in (('axis', (0, 0, 1)),
                                  ('range', (-10, 10))):
            with self.subTest(keyword=keyword):
                with self.assertRaises(TypeError) as raised:
                    Free(**{keyword: argument})
                message = str(raised.exception)
                self.assertIn(keyword, message)
                for taken in ('at', 'angle_unit', 'length_unit'):
                    self.assertIn(taken, message)

    ##############################################
    # 1.12 `at` resolves against the instance

    def test_the_anchor_resolves_against_the_instance(self):
        """Characterisation of the inherited argument path: `at` is
        `Joint._vector`'s, and a `Free` neither adds to it nor takes
        anything from it. Red on the NAME only."""
        class Parametric(AssemblyNode):
            reach = Length(30.0)

            pose = Free(at=(0, reach, 2 * reach), angle_unit='deg',
                        length_unit='mm')

            box = Hinge()

        default = Parametric()
        wider = Parametric(reach=45.0)

        self.assertEqual(Parametric.pose.arguments(default)[1],
                         (0.0, 30.0, 60.0))
        self.assertEqual(Parametric.pose.arguments(wider)[1],
                         (0.0, 45.0, 90.0))

    def test_a_callable_anchor_is_called_with_the_realized_node(self):
        calls = []

        class Built(AssemblyNode):
            def _anchor(node):
                calls.append(node)
                return (1.0, 2.0, 3.0)

            pose = Free(at=_anchor, angle_unit='deg', length_unit='mm')

            box = Hinge()

        built = Built()

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0], built)
        self.assertEqual(Built.pose.arguments(built)[1], (1.0, 2.0, 3.0))

    def test_a_malformed_anchor_fails_at_realization(self):
        def raising(node):
            raise RuntimeError('no anchor here')

        elsewhere = Length(5.0)
        elsewhere._name = 'elsewhere'

        for label, at in (('two components', (0, 0)),
                          ('an undeclared token', (0, elsewhere, 0)),
                          ('a callable that raises', raising)):
            with self.subTest(anchor=label):
                class Bad(AssemblyNode):
                    pose = Free(at=at, angle_unit='deg', length_unit='mm')

                    box = Hinge()

                with self.assertRaises(ParameterError) as raised:
                    Bad()

                message = str(raised.exception)
                self.assertIn('Bad', message)
                self.assertIn('pose', message)
                self.assertIn('at', message)

    ##############################################
    # 1.13 The published document

    def test_a_symbolic_binding_publishes_ordinary_operations(self):
        class Floating(AssemblyNode):
            chassis = FloatingChassis()

            def render(self):
                pass

            def simulate(self):
                self.chassis.pose.roll = self.time * 90
                self.chassis.pose.pitch = self.time * 45
                self.chassis.pose.yaw = self.time * 180
                self.chassis.pose.x = self.time * 10
                self.chassis.pose.y = self.time * 20
                self.chassis.pose.z = self.time * 30

        floating = Floating()
        floating.render()

        published = serialized(floating.chassis)
        self.assertEqual([operation[0] for operation in published],
                         ['r', 'r', 'r', 't'])
        for operation in published[:3]:
            with self.subTest(operation=operation):
                self.assertIn('$t', operation[1])
        for component in published[3][1]:
            with self.subTest(component=component):
                self.assertIn('$t', component)

        document = serialize_node(floating, lambda rigid: rigid.name)
        keys = set(document)
        for child in document.get('children', ()):
            keys.update(child)
        self.assertLessEqual(
            keys, {'name', 'type', 'color', 'mtime', 'operations', 'model',
                   'children', 'flexible', 'piece'})

        floating.set_keyframe(0.5)
        numeric = serialized(floating.chassis)
        self.assertEqual(numeric[0][1], '45.0')
        self.assertEqual([float(component) for component in numeric[3][1]],
                         [5.0, 10.0, 15.0])

        floating.clear_keyframe()
        self.assertIn('$t', serialized(floating.chassis)[0][1])


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
        """`turn` needs no anchor at all now (the bearing IS the placed
        origin), but `pin` still does: a genuinely off-origin point read
        off the arbor's own built object, different per instance, which
        is exactly the callable-argument case this coverage is for."""
        stack = ArborStack()
        stack.set_state(rotation=30)

        for arbor in stack.arbors:
            with self.subTest(arbor=arbor.name):
                self.assertEqual([operation.serialized[0] for operation
                                  in arbor.operations][:1], ['r'])

        for arbor in stack.arbors:
            with self.subTest(arbor=arbor.name):
                arbor.pin = 20
                run = arbor.__dict__['_joint_motion']['pin']
                self.assertEqual([operation.serialized[0]
                                  for operation in run], ['t', 'r', 't'])
                expected = arbor.built.pin[arbor.index]
                self.assertAlmostEqual(numbers(run[0].serialized)[1],
                                       -expected[1], places=9)

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
