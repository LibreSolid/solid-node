# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`a.drives(b)`: the relation between two coordinates.

One verb, stated in a class body, over ends of five kinds; a law that is
project code handed in and never looked up; a linear formula over
coordinates that is itself a coordinate; and a solver that orients each
relation from whichever end is bound at the moment it runs, at the end
of the owning assembly's simulate phase.

The evidence is `tests/coupling_project/`: wall clock 01's going train,
which binds only the escape wheel and has to be solved BACKWARDS through
the inverse of the project's own law, and Thor's arm, where a root
driver reaches a joint two levels down by path and a derived coordinate
carries the elbow belt anchored on the shoulder housing.
"""

import math
from unittest import TestCase

from solid2 import cube, get_animation_time

from solid_node.core.serializer import (bind_document, drivers_table,
                                        serialize_node, symbolic_document)
from solid_node.motion.couplings import (Affine, CouplingError,
                                         DerivedCoordinate, DoublyBound,
                                         NotInvertible, Relation,
                                         UnreachedCoordinate,
                                         declared_relations)
from solid_node.motion.joints import JointRangeError, Prismatic, Revolute
from solid_node.motion.ports import (RotationalPort, SignalPort,
                                     TranslationalPort, declared_ports)
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.node.declarative import SidewaysReadError
from solid_node.node.qualified import DriverToken
from solid_node.parameters import Count, Length
from solid_node.simulation import Driver

from .base import BaseNodeTest
from .import_probe import probe
from .test_math import _eval_openscad_expr
from .coupling_project.parts import Belt, Link, Pulley, Rod, Wheel
from .coupling_project.train import (Arbor, Arm, BackwardsTrain, PITCH_ARC,
                                     Train, Upper, Wrist, mesh)


# What the fixture train solves for, by hand, so a disagreement between
# the framework and the arithmetic the clock writes is visible here.
# escape = -8 * centre + 5, centre = -7.5 * power + 3.
def train_angles(escape):
    centre = (escape - 5.0) / -8.0
    power = (centre - 3.0) / -7.5
    return power, centre, escape


def motions(node):
    return [operation for operation in node.operations
            if getattr(operation, '_motion', False)]


##############################################
# 1.2 The statement

class RelationStatementTest(BaseNodeTest):

    def test_a_bare_statement_is_recorded_on_the_class(self):
        relations = declared_relations(Train)

        self.assertEqual(len(relations), 2)
        for relation in relations:
            self.assertIsInstance(relation, Relation)
        self.assertIs(relations[0].law, mesh)

    def test_the_verb_is_on_every_kind_of_end_with_no_import(self):
        class Every(AssemblyNode):
            knob = Driver(default=0.0, unit='deg')
            spin = RotationalPort(unit='deg')
            turn = Revolute(axis=(0, 0, 1), unit='deg')
            pulley = Pulley()
            belt = Belt()
            derived = turn + spin

            knob.drives(spin)
            spin.drives(turn)
            turn.drives(pulley)
            pulley.turn.drives(belt.travel)
            derived.drives(pulley.turn)

        self.assertEqual(len(declared_relations(Every)), 5)

    def test_a_named_relation_is_one_relation_named(self):
        class Named(AssemblyNode):
            power = Arbor(index=0)
            centre = Arbor(index=1)

            great = power.drives(centre)

        relations = declared_relations(Named)
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0].name, 'great')
        self.assertIs(Named.great, relations[0])

        machine = Named()
        record = machine.great
        self.assertIsNot(record, Named.great)
        self.assertIs(record.driver, machine.power.turn)
        self.assertIs(record.driven, machine.centre.turn)

    def test_a_relation_in_a_class_body_comprehension_is_recorded(self):
        class Comprehended(AssemblyNode):
            power = Arbor(index=0)
            centre = Arbor(index=1)

            [driver.drives(driven) for driver, driven in [(power, centre)]]

        self.assertEqual(len(declared_relations(Comprehended)), 1)

    def test_a_subclass_adds_to_its_bases_relations(self):
        class Base(AssemblyNode):
            power = Arbor(index=0)
            centre = Arbor(index=1)

            power.drives(centre)

        class Sub(Base):
            escape = Arbor(index=2)

            Base.centre.drives(escape)

        self.assertEqual(len(declared_relations(Base)), 1)
        self.assertEqual(len(declared_relations(Sub)), 2)
        self.assertIs(declared_relations(Sub)[0], declared_relations(Base)[0])

    def test_drives_outside_a_class_body_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            Pulley.turn.drives(Wheel.turn)

        message = str(raised.exception)
        self.assertIn('class body', message)
        self.assertIn('class metadata', message)

    def test_a_relation_on_a_leaf_is_refused_at_class_creation(self):
        with self.assertRaises(TypeError) as raised:
            class Leaf(Solid2Node):
                a = RotationalPort(unit='deg')
                b = RotationalPort(unit='deg')

                a.drives(b)

                def render(self):
                    return cube(1, center=True)

        message = str(raised.exception)
        self.assertIn('Leaf', message)
        self.assertIn('simulate', message)

    def test_every_instance_solves_its_own_relations(self):
        class Pair(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            left = Pulley()
            right = Pulley()

            left.drives(right, ratio=2.0)

            def simulate(self):
                self.left.turn = self.angle

        class Top(AssemblyNode):
            one = Pair()
            other = Pair()

        top = Top()
        top.set_state(**{'one.angle': 5.0, 'other.angle': 11.0})

        self.assertEqual(top.one.right.turn.value, 10.0)
        self.assertEqual(top.other.right.turn.value, 22.0)


##############################################
# 1.3 The ends

class RelationEndTest(BaseNodeTest):

    def test_a_node_end_is_its_one_joint(self):
        train = Train()
        record = declared_relations(Train)[0].record_of(train)

        self.assertIs(record.driver, train.power.turn)
        self.assertIs(record.driven, train.centre.turn)

    def test_a_path_of_three_segments_resolves(self):
        arm = Arm()
        record = declared_relations(Arm)[1].record_of(arm)

        self.assertIs(record.driven, arm.upper.art3.elbow)

    def test_a_node_with_two_joints_is_refused_at_class_definition(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                pulley = Pulley()
                wrist = Wrist()

                pulley.drives(wrist)

        message = str(raised.exception)
        for expected in ('wrist', 'Wrist', 'tool'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_node_with_no_joint_is_refused_at_class_definition(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                pulley = Pulley()
                link = Link()

                pulley.drives(link)

        message = str(raised.exception)
        for expected in ('link', 'Link'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_driver_as_the_driven_end_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                knob = Driver(default=0.0, unit='deg')
                pulley = Pulley()

                pulley.turn.drives(knob)

        message = str(raised.exception)
        self.assertIn('knob', message)
        self.assertIn('set_state', message)

    def test_a_misspelt_path_segment_is_refused_at_class_definition(self):
        with self.assertRaises(SidewaysReadError) as raised:
            class Bad(AssemblyNode):
                knob = Driver(default=0.0, unit='deg')
                upper = Upper()

                knob.drives(upper.art3.wist)

        message = str(raised.exception)
        for expected in ('upper.art3.wist', 'wist', 'elbow'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_path_through_a_repeated_child_is_refused(self):
        with self.assertRaises(SidewaysReadError) as raised:
            class Bad(AssemblyNode):
                count = Count(3, min=1)
                knob = Driver(default=0.0, unit='deg')
                units = Pulley().repeat(count)

                knob.drives(units.turn)

        message = str(raised.exception)
        self.assertIn('units', message)
        self.assertIn('repeated', message)

    def test_a_path_that_does_not_resolve_fails_at_realization(self):
        class Hollow(AssemblyNode):
            inner = Pulley()

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                del self.__dict__['inner']

        class Top(AssemblyNode):
            knob = Driver(default=0.0, unit='deg')
            hollow = Hollow()

            knob.drives(hollow.inner)

        with self.assertRaises(CouplingError) as raised:
            Top()

        message = str(raised.exception)
        self.assertIn('hollow.inner', message)

    def test_a_parameter_read_off_a_declaration_is_still_refused(self):
        with self.assertRaises(SidewaysReadError) as raised:
            class Bad(AssemblyNode):
                link = Link()
                other = Link(length=link.length)

        message = str(raised.exception)
        self.assertIn('length', message)
        self.assertIn('declare', message)

    def test_a_coordinate_of_another_class_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                pulley = Pulley()

                Rod.turn.drives(pulley.turn)

        message = str(raised.exception)
        for expected in ('Bad', 'Rod', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_driver_read_off_a_declaration_is_refused(self):
        with self.assertRaises(SidewaysReadError) as raised:
            class Bad(AssemblyNode):
                arm = Arm()
                pulley = Pulley()

                arm.elbow_driver.drives(pulley.turn)

        self.assertIn('elbow_driver', str(raised.exception))


##############################################
# 1.4 Affine

class AffineTest(TestCase):

    def test_forward_and_inverse_on_numbers(self):
        law = Affine(ratio=-3.5, offset=12.0)

        self.assertEqual(law.forward(4.0), -3.5 * 4.0 + 12.0)
        self.assertAlmostEqual(law.inverse(law.forward(4.0)), 4.0)
        self.assertTrue(law.invertible)

    def test_the_default_is_the_identity(self):
        law = Affine(ratio=1)

        self.assertEqual(law.forward(7), 7)
        self.assertEqual(law.inverse(7), 7)

    def test_a_zero_ratio_is_not_invertible(self):
        self.assertFalse(Affine(ratio=0).invertible)
        self.assertFalse(Affine(ratio=0.0).invertible)

    def test_a_symbolic_ratio_is_taken_as_invertible(self):
        self.assertTrue(Affine(ratio=get_animation_time()).invertible)

    def test_a_symbolic_operand_rides_through_both_faces(self):
        law = Affine(ratio=-3.5, offset=12.0)
        time = get_animation_time()

        forward = str(law.forward(360.0 * time))
        backward = str(law.inverse(360.0 * time))

        for instant in (0.0, 0.25, 0.5, 1.0):
            with self.subTest(instant=instant):
                self.assertAlmostEqual(
                    _eval_openscad_expr(forward, instant),
                    law.forward(360.0 * instant), places=9)
                self.assertAlmostEqual(
                    _eval_openscad_expr(backward, instant),
                    law.inverse(360.0 * instant), places=9)

    def test_the_repr_reads_like_the_law(self):
        self.assertIn('-3.5', repr(Affine(ratio=-3.5, offset=12.0)))


class AffineShorthandTest(BaseNodeTest):

    def test_a_ratio_token_resolves_per_instance(self):
        class Geared(AssemblyNode):
            teeth = Count(4, min=1)
            angle = Driver(default=0.0, unit='deg')
            driver = Pulley()
            driven = Pulley()

            driver.drives(driven, ratio=teeth)

            def simulate(self):
                self.driver.turn = self.angle

        class Top(AssemblyNode):
            small = Geared(teeth=2)
            big = Geared(teeth=5)

        top = Top()
        top.set_state(**{'small.angle': 10.0, 'big.angle': 10.0})

        self.assertEqual(top.small.driven.turn.value, 20.0)
        self.assertEqual(top.big.driven.turn.value, 50.0)

    def test_a_ratio_with_a_law_is_refused_at_class_definition(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                a = Pulley()
                b = Pulley()

                a.drives(b, ratio=2, law=mesh)

        self.assertIn('one law', str(raised.exception))


##############################################
# 1.5 The law protocol

class LawProtocolTest(BaseNodeTest):

    def test_the_law_is_called_once_with_the_two_realized_owners(self):
        seen = []

        def law(driver, driven):
            seen.append((driver, driven))
            return Affine(ratio=1.0)

        class Machine(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            spin = RotationalPort(unit='deg')
            upper = Upper()
            pulley = Pulley()
            belt = Belt()
            derived = spin + spin

            spin.drives(pulley, law=law)            # own port -> node
            upper.art3.elbow.drives(belt.travel, law=law)  # path -> path
            derived.drives(upper.shoulder, law=law)  # derived -> path

        machine = Machine()

        self.assertEqual(len(seen), 3)
        self.assertEqual(seen[0], (machine, machine.pulley))
        self.assertEqual(seen[1], (machine.upper.art3, machine.belt))
        self.assertEqual(seen[2], (machine, machine.upper))

    def test_a_law_reads_the_realized_arbors(self):
        train = Train()
        record = declared_relations(Train)[0].record_of(train)

        self.assertEqual(record.law.ratio, -60 / 8)
        self.assertEqual(record.law.offset, 3.0)

    def test_a_law_reads_a_value_off_the_realized_node(self):
        class Movement:
            """A stand-in for the clock's built library movement."""

            def __init__(self, teeth):
                self.wheel = teeth * 2

        class Wheel(AssemblyNode):
            teeth = Count(10, min=1)
            angle = Driver(default=0.0, unit='deg')
            spin = RotationalPort(unit='deg')
            driven = Pulley()

            spin.drives(
                driven,
                law=lambda driver, driven: Affine(
                    ratio=driver.built.wheel / 4))

            @property
            def built(self):
                return Movement(self.teeth)

            def simulate(self):
                self.spin = self.angle

        machine = Wheel(teeth=6)
        machine.set_state(angle=2.0)

        # The law was handed the realized OWNER of the driver end, so
        # `built` is read off a node that exists -- the clock's case,
        # where the tooth counts come off a built library movement and
        # not out of a formula over declarations.
        self.assertEqual(machine.driven.turn.value, 2.0 * (6 * 2 / 4))

    def test_a_returned_plain_function_is_forward_only(self):
        class Machine(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()

            a.drives(b, law=lambda driver, driven: (lambda x: x * 3))

            def simulate(self):
                self.a.turn = self.angle

        machine = Machine()
        machine.set_state(angle=4.0)

        self.assertEqual(machine.b.turn.value, 12.0)
        record = declared_relations(Machine)[0].record_of(machine)
        self.assertFalse(record.law.invertible)

    def test_a_returned_non_law_is_refused_at_realization(self):
        class Machine(AssemblyNode):
            a = Pulley()
            b = Pulley()

            a.drives(b, law=lambda driver, driven: 7)

        with self.assertRaises(CouplingError) as raised:
            Machine()

        message = str(raised.exception)
        self.assertIn('7', message)
        self.assertIn('forward', message)

    def test_twenty_instants_call_the_law_no_further_times(self):
        calls = []

        def law(driver, driven):
            calls.append(1)
            return Affine(ratio=2.0)

        class Machine(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()

            a.drives(b, law=law)

            def simulate(self):
                self.a.turn = self.angle

        machine = Machine()
        for step in range(20):
            machine.set_state(angle=float(step))

        self.assertEqual(len(calls), 1)
        self.assertEqual(machine.b.turn.value, 38.0)


##############################################
# 1.6 Derived coordinates

class DerivedCoordinateTest(BaseNodeTest):

    def test_the_linear_forms_build_one(self):
        class Formulas(AssemblyNode):
            a = Revolute(axis=(0, 0, 1), unit='deg')
            b = Revolute(axis=(0, 0, 1), unit='deg')

            difference = a - b
            weighted = a + 2 * b
            negated = -a
            halved = a / 2

        for name in ('difference', 'weighted', 'negated', 'halved'):
            with self.subTest(name=name):
                self.assertIsInstance(getattr(Formulas, name),
                                      DerivedCoordinate)

    def test_a_product_of_two_coordinates_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                wrist = Revolute(axis=(0, 0, 1), unit='deg')
                tool = Revolute(axis=(0, 1, 0), unit='deg')

                bad = wrist * tool

        message = str(raised.exception)
        for expected in ('wrist', 'tool', 'law='):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_function_of_a_coordinate_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                wrist = Revolute(axis=(0, 0, 1), unit='deg')

                bad = math.sin(wrist)

        self.assertIn('law=', str(raised.exception))

    def test_terms_of_different_domains_are_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                turn = Revolute(axis=(0, 0, 1), unit='deg')
                slide = Prismatic(axis=(1, 0, 0), unit='mm')

                bad = turn - slide

        message = str(raised.exception)
        for expected in ('turn', 'slide', 'rotational', 'translational'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_terms_of_different_units_are_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                degrees = RotationalPort(unit='deg')
                radians = RotationalPort(unit='rad')

                bad = degrees - radians

        message = str(raised.exception)
        for expected in ('degrees', 'radians', 'deg', 'rad'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_derived_coordinate_reads_as_a_bound_slot(self):
        wrist = Wrist()
        wrist.set_state(wrist_angle=10.0, tool_angle=3.0)

        self.assertEqual(wrist.left.value, 16.0)
        self.assertEqual(wrist.right.value, 4.0)
        self.assertEqual(wrist.left.domain, 'rotational')
        self.assertEqual(wrist.left.unit, 'deg')
        self.assertEqual(wrist.left.name, 'left')

    def test_declared_ports_reports_it(self):
        ports = declared_ports(Wrist)

        self.assertIn('left', ports)
        self.assertIn('right', ports)
        self.assertEqual(ports['left'].domain, 'rotational')

    def test_it_solves_backwards_through_one_unbound_term(self):
        arm = Arm()
        arm.set_state(shoulder_driver=10.0, elbow_driver=30.0)

        self.assertEqual(arm.upper.relative.value, 20.0)
        self.assertEqual(arm.upper.pulley.turn.value, 20.0)
        self.assertAlmostEqual(arm.upper.belt.travel.value,
                               20.0 * PITCH_ARC)

    def test_a_term_is_solved_from_the_derived_value(self):
        class Anchored(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            shoulder = Revolute(axis=(0, 0, 1), unit='deg')
            art3 = Pulley()
            source = Pulley()

            relative = art3.turn - shoulder

            source.drives(relative)

            def simulate(self):
                self.shoulder = 4.0
                self.source.turn = self.angle

        machine = Anchored()
        machine.set_state(angle=10.0)

        self.assertEqual(machine.relative.value, 10.0)
        self.assertEqual(machine.art3.turn.value, 14.0)

    def test_a_formula_written_straight_into_a_relation_solves(self):
        class Anonymous(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()
            pulley = Pulley()

            (a.turn - b.turn).drives(pulley.turn)

            def simulate(self):
                self.a.turn = self.angle
                self.b.turn = 1.0

        machine = Anonymous()
        machine.set_state(angle=7.0)

        self.assertEqual(machine.pulley.turn.value, 6.0)

    def test_two_unknown_terms_are_refused(self):
        class TooLoose(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()
            source = Pulley()

            relative = a.turn - b.turn

            source.drives(relative)

            def simulate(self):
                self.source.turn = self.angle

        machine = TooLoose()
        with self.assertRaises(UnreachedCoordinate) as raised:
            machine.set_state(angle=1.0)

        message = str(raised.exception)
        for expected in ('relative', 'a', 'b'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)


##############################################
# 1.7 Freshness across runs

class FreshnessTest(BaseNodeTest):

    def test_three_instants_each_produce_their_own_angles(self):
        train = Train()

        for escape in (24.0, 48.0, -12.0):
            with self.subTest(escape=escape):
                train.set_state(escape_angle=escape)
                power, centre, _ = train_angles(escape)
                self.assertAlmostEqual(train.centre.turn.value, centre)
                self.assertAlmostEqual(train.power.turn.value, power)

    def test_nothing_is_refused_as_doubly_bound_on_the_second_run(self):
        train = Train()
        train.set_state(escape_angle=24.0)
        train.set_state(escape_angle=25.0)

        self.assertNotAlmostEqual(train.power.turn.value,
                                  train_angles(24.0)[0])

    def test_an_author_binding_from_an_earlier_run_is_not_cleared(self):
        class Occasional(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            hand = Pulley()
            driven = Pulley()

            hand.drives(driven, ratio=2.0)

            def simulate(self):
                if self.angle:
                    self.hand.turn = self.angle

        machine = Occasional()
        machine.set_state(angle=6.0)
        self.assertEqual(machine.driven.turn.value, 12.0)

        # The author binds nothing this run; the value the author bound
        # last run is the author's, and stays.
        machine.set_state(angle=0.0)
        self.assertEqual(machine.hand.turn.value, 6.0)


##############################################
# 1.8 Wirings inside the fixpoint

class WiringInTheFixpointTest(BaseNodeTest):

    def test_a_wiring_whose_source_a_relation_solves_binds(self):
        class Solved(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            source = Pulley()
            turn = RotationalPort(unit='deg')

            wheel = Wheel(turn=turn)
            rod = Rod(turn=turn)

            source.turn.drives(turn, ratio=3.0)

            def simulate(self):
                self.source.turn = self.angle

        machine = Solved()
        machine.set_state(angle=5.0)

        self.assertEqual(machine.turn.value, 15.0)
        self.assertEqual(machine.wheel.turn.value, 15.0)
        self.assertEqual(machine.rod.turn.value, 15.0)

    def test_an_unbound_wiring_source_still_raises_cycle_twos_error(self):
        class Never(AssemblyNode):
            turn = RotationalPort(unit='deg')
            wheel = Wheel(turn=turn)

        machine = Never()
        with self.assertRaises(ValueError) as raised:
            machine.render()

        message = str(raised.exception)
        for expected in ('Never', 'wheel', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_relation_reaching_a_wired_child_end_is_doubly_bound(self):
        class Both(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            turn = RotationalPort(unit='deg')
            source = Pulley()

            wheel = Wheel(turn=turn)

            source.turn.drives(wheel.turn)

            def simulate(self):
                self.turn = self.angle
                self.source.turn = self.angle

        machine = Both()
        with self.assertRaises(DoublyBound) as raised:
            machine.set_state(angle=2.0)

        message = str(raised.exception)
        self.assertIn('wheel', message)
        self.assertIn('turn', message)

    def test_a_hand_binding_of_a_wired_coordinate_is_still_refused(self):
        class Top(AssemblyNode):
            turn = RotationalPort(unit='deg')
            wheel = Wheel(turn=turn)

            def simulate(self):
                self.turn = 5
                self.wheel.turn = 9

        top = Top()
        with self.assertRaises(ValueError) as raised:
            top.render()

        self.assertIn('wheel', str(raised.exception))


##############################################
# 1.9 The solver

class SolverTest(BaseNodeTest):

    def test_the_train_solves_backwards_from_the_escapement(self):
        train = Train()
        train.set_state(escape_angle=24.0)

        power, centre, escape = train_angles(24.0)
        self.assertAlmostEqual(train.escape.turn.value, escape)
        self.assertAlmostEqual(train.centre.turn.value, centre)
        self.assertAlmostEqual(train.power.turn.value, power)

    def test_every_arbors_body_is_placed(self):
        train = Train()
        train.set_state(escape_angle=24.0)

        for arbor in (train.power, train.centre, train.escape):
            with self.subTest(arbor=arbor.name):
                # One rotation, with the two centring translations when
                # the bearing is off the arbor's own placed origin.
                turns = [operation for operation in motions(arbor)
                         if operation.serialized[0] == 'r']
                self.assertEqual(len(turns), 1)
                self.assertEqual(float(turns[0].serialized[1]),
                                 arbor.turn.value)

    def test_the_declaration_order_is_irrelevant(self):
        forwards = Train()
        backwards = BackwardsTrain()
        forwards.set_state(escape_angle=24.0)
        backwards.set_state(escape_angle=24.0)

        self.assertAlmostEqual(forwards.power.turn.value,
                               backwards.power.turn.value)

    def test_the_direction_solved_is_recorded_on_the_instance(self):
        train = Train()
        train.set_state(escape_angle=24.0)

        for relation in declared_relations(Train):
            with self.subTest(relation=repr(relation)):
                self.assertEqual(relation.record_of(train).direction,
                                 'backward')

    def test_a_tooth_count_is_the_only_thing_that_changes(self):
        class Retoothed(Train):
            pass

        train = Train()
        train.set_state(escape_angle=24.0)
        before = train.power.turn.value

        other = Train()
        other.centre.__dict__['_parameters']['pinion_teeth'] = 10
        # The declared count is what the law reads; a fresh tree with a
        # different count is the honest comparison.
        class Recut(AssemblyNode):
            escape_angle = Driver(default=0.0, unit='deg')
            power = Arbor(index=0, wheel_teeth=60, pinion_teeth=8)
            centre = Arbor(index=1, wheel_teeth=48, pinion_teeth=10,
                           registration=3.0)
            escape = Arbor(index=2, wheel_teeth=30, pinion_teeth=6,
                           registration=5.0)

            power.drives(centre, law=mesh)
            centre.drives(escape, law=mesh)

            def simulate(self):
                self.escape.turn = self.escape_angle

        recut = Recut()
        recut.set_state(escape_angle=24.0)

        self.assertNotAlmostEqual(recut.power.turn.value, before)

    def test_the_motion_is_tagged_and_swept_with_the_assembly(self):
        train = Train()
        train.set_state(escape_angle=24.0)

        placed = motions(train.centre)
        for operation in placed:
            self.assertIs(operation._animator, train)

        train.set_state(escape_angle=48.0)
        self.assertEqual(len(motions(train.centre)), len(placed))

    def test_a_relation_on_a_repeated_assembly_solves_per_instance(self):
        class Stage(AssemblyNode):
            drive = RotationalPort(unit='deg')
            a = Pulley()
            b = Pulley()

            drive.drives(a.turn)
            a.turn.drives(b.turn, ratio=2.0)

        class Bank(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            count = Count(3, min=1)
            turn = RotationalPort(unit='deg')

            stages = Stage(drive=turn).repeat(count)

            def simulate(self):
                self.turn = self.angle

        bank = Bank()
        bank.set_state(angle=5.0)

        self.assertEqual([stage.b.turn.value for stage in bank.stages],
                         [10.0, 10.0, 10.0])
        self.assertEqual(len({id(stage.b.turn) for stage in bank.stages}), 3)

    def test_an_ancestors_relation_binds_before_the_descendant_solves(self):
        arm = Arm()
        arm.set_state(shoulder_driver=10.0, elbow_driver=30.0)

        self.assertEqual(arm.upper.shoulder.value, 10.0)
        self.assertEqual(arm.upper.art3.elbow.value, 30.0)
        self.assertEqual(arm.upper.relative.value, 20.0)


##############################################
# 1.10 The three refusals

class RefusalTest(BaseNodeTest):

    def test_a_coordinate_nothing_reaches_is_refused(self):
        class Adrift(AssemblyNode):
            a = Pulley()
            b = Pulley()

            great = a.drives(b)

        machine = Adrift()
        with self.assertRaises(UnreachedCoordinate) as raised:
            machine.render()

        message = str(raised.exception)
        for expected in ('great', 'a', 'b', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_an_author_binding_and_a_relation_are_two_binders(self):
        class Twice(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()

            a.drives(b)

            def simulate(self):
                self.a.turn = self.angle
                self.b.turn = self.angle

        machine = Twice()
        with self.assertRaises(DoublyBound) as raised:
            machine.set_state(angle=3.0)

        message = str(raised.exception)
        self.assertIn('b', message)
        self.assertIn('simulate()', message)

    def test_two_relations_reaching_one_coordinate_are_refused(self):
        class Redundant(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()
            c = Pulley()

            first = a.drives(c, ratio=1.0)
            second = b.drives(c, ratio=1.0)

            def simulate(self):
                self.a.turn = self.angle
                self.b.turn = self.angle

        machine = Redundant()
        with self.assertRaises(DoublyBound) as raised:
            machine.set_state(angle=3.0)

        message = str(raised.exception)
        for expected in ('first', 'second', 'compare'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_non_invertible_law_needed_backwards_is_refused(self):
        class Backwards(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()

            a.drives(b, law=lambda driver, driven: (lambda x: x * 3))

            def simulate(self):
                self.b.turn = self.angle

        machine = Backwards()
        with self.assertRaises(NotInvertible) as raised:
            machine.set_state(angle=3.0)

        message = str(raised.exception)
        self.assertIn('inverse', message)

    def test_a_zero_ratio_needed_backwards_is_refused(self):
        class Stuck(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()

            a.drives(b, ratio=0)

            def simulate(self):
                self.b.turn = self.angle

        machine = Stuck()
        with self.assertRaises(NotInvertible):
            machine.set_state(angle=3.0)

    def test_the_same_forward_only_law_used_forwards_passes(self):
        class Forwards(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()

            a.drives(b, law=lambda driver, driven: (lambda x: x * 3))

            def simulate(self):
                self.a.turn = self.angle

        machine = Forwards()
        machine.set_state(angle=3.0)

        self.assertEqual(machine.b.turn.value, 9.0)


##############################################
# 1.11 The symbolic and numeric faces

def symbolic_parts(node):
    """The serialized document and its driver ids, in symbolic mode."""
    with symbolic_document(node) as (declarations, _instructions):
        root = serialize_node(node, lambda rigid: rigid.name)
    return root, list(drivers_table(declarations).keys())


def find(document, name):
    if document['name'] == name:
        return document
    for child in document.get('children', ()):
        found = find(child, name)
        if found is not None:
            return found
    return None


def rotations(document, name):
    for child in document.get('children', ()):
        if child['name'] == name:
            return [operation[1] for operation in child['operations']
                    if operation[0] == 'r']
    raise AssertionError(f'no child {name}')


class SymbolicFaceTest(BaseNodeTest):

    def test_a_tree_of_relations_publishes_expressions(self):
        train = Train()
        document, _ids = symbolic_parts(train)

        angle = rotations(document, 'centre')[0]
        self.assertIn('escape_angle', angle)

    def test_a_derived_chain_publishes_the_driver_it_came_from(self):
        arm = Arm()
        arm.set_state(shoulder_driver=0.0, elbow_driver=30.0)
        self.assertEqual(arm.upper.relative.value, 30.0)

        document, _ids = symbolic_parts(arm)
        pulley = find(document, 'pulley')
        text = ' '.join(str(operation[1]) for operation
                        in pulley['operations'])

        # The pulley turns by the derived difference, which the belt's
        # own port then carries: a port moves no body, so the published
        # evidence of the chain is the pulley's rotation.
        self.assertIn('elbow_driver', text)
        self.assertIn('shoulder_driver', text)

    def test_set_state_carries_plain_numbers(self):
        train = Train()
        train.set_state(escape_angle=24.0)

        self.assertIsInstance(train.power.turn.value, float)

    def test_the_backward_solve_publishes_an_evaluable_expression(self):
        train = Train()
        document, ids = symbolic_parts(train)
        bindings = bind_document(document, ids)
        text = {entry['name']: entry['expression'] for entry in bindings}

        published = rotations(document, 'power')[0]
        for name, expression in text.items():
            published = published.replace(name, f'({expression})')
        for name, expression in text.items():
            published = published.replace(name, f'({expression})')

        for instant in (0.0, 12.0, -30.0):
            with self.subTest(instant=instant):
                numeric = _eval_openscad_expr(
                    published.replace('escape_angle', repr(instant)), 0.0)
                self.assertAlmostEqual(numeric, train_angles(instant)[0],
                                       places=9)

    def test_the_shared_subexpression_is_interned_once(self):
        train = Train()
        document, ids = symbolic_parts(train)

        bindings = bind_document(document, ids)

        self.assertTrue(bindings)
        published = rotations(document, 'power')[0]
        self.assertTrue(any(entry['name'] in published
                            for entry in bindings))

    def test_a_derived_formula_solved_backwards_stays_symbolic(self):
        class Anchored(AssemblyNode):
            knob = Driver(default=0.0, unit='deg')
            shoulder = Revolute(axis=(0, 0, 1), unit='deg')
            art3 = Pulley()
            source = Pulley()

            relative = art3.turn - shoulder

            source.drives(relative)

            def simulate(self):
                self.shoulder = 4.0
                self.source.turn = self.knob

        machine = Anchored()
        document, _ids = symbolic_parts(machine)
        angle = rotations(document, 'art3')[0]

        self.assertIn('knob', angle)
        evaluated = _eval_openscad_expr(angle.replace('knob', '10.0'), 0.0)
        self.assertAlmostEqual(evaluated, 14.0, places=9)

    def test_a_driver_token_rides_backwards_through_an_affine(self):
        law = Affine(ratio=-3.5, offset=12.0)
        token = DriverToken('art3')

        backward = str(law.inverse(token))
        evaluated = _eval_openscad_expr(backward.replace('art3', '9.0'), 0.0)

        self.assertAlmostEqual(evaluated, law.inverse(9.0), places=9)


##############################################
# 1.12 Cross-cycle

class CrossCycleTest(BaseNodeTest):

    def test_a_relation_into_a_scaled_port_converts_once(self):
        class Scaled(Solid2Node):
            turn = RotationalPort(unit='mm', scale=2.0)

            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            source = Pulley()
            scaled = Scaled()

            source.turn.drives(scaled.turn, ratio=3.0)

            def simulate(self):
                self.source.turn = self.angle

        top = Top()
        top.set_state(angle=5.0)

        self.assertEqual(top.scaled.turn.value, 30.0)

    def test_a_relation_past_a_joints_range_is_refused(self):
        class Ranged(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), range=(-135, 135), unit='deg')

            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            source = Pulley()
            ranged = Ranged()

            source.turn.drives(ranged.turn, ratio=2.0)

            def simulate(self):
                self.source.turn = self.angle

        top = Top()
        with self.assertRaises(JointRangeError):
            top.set_state(angle=100.0)

    def test_a_relation_drives_a_translational_port(self):
        arm = Arm()
        arm.set_state(shoulder_driver=0.0, elbow_driver=9.0)

        self.assertAlmostEqual(arm.upper.belt.travel.value, 9.0 * PITCH_ARC)

    def test_a_relation_drives_a_flexible_leafs_port(self):
        from .flexible_project.spring import Spring

        class Rig(AssemblyNode):
            lift = Driver(default=0.0, unit='mm')
            pulley = Pulley()
            spring = Spring()

            lift.drives(pulley.turn)
            pulley.turn.drives(spring.height, ratio=0.5)

        rig = Rig()
        rig.set_state(lift=8.0)

        self.assertEqual(rig.spring.height.value, 4.0)


##############################################
# 1.13 Import cost

MODULE_REPORT = (
    'import sys\n'
    "print(sorted(m for m in sys.modules\n"
    "             if m == 'solid_node' or m.startswith('solid_node.')))\n")


class CouplingImportCostTest(TestCase):

    def modules(self, snippet):
        result = probe(snippet + MODULE_REPORT).check()
        return set(eval(result.stdout.strip())), result

    def test_couplings_costs_what_ports_costs_and_no_more(self):
        ports, _ = self.modules('import solid_node.motion.ports\n')
        couplings, result = self.modules(
            'import solid_node.motion.couplings\n')

        self.assertEqual(couplings, ports | {'solid_node.motion.couplings'})
        for absent in ('cadquery', 'OCP', 'trimesh'):
            with self.subTest(absent=absent):
                self.assertFalse(result.imported(absent))
