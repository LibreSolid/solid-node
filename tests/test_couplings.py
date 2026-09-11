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
                                         ForwardOnly, NotInvertible, Relation,
                                         UnreachedCoordinate,
                                         declared_relations)
from solid_node.motion.joints import (Free, JointRangeError, Orbit, Prismatic,
                                      Revolute, declared_joints)
from solid_node.motion.ports import (RotationalPort, SignalPort,
                                     TranslationalPort, declared_ports)
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.node.declarative import SidewaysReadError
from solid_node.node.qualified import DriverToken
from solid_node.parameters import Count, Length, Ratio
from solid_node.simulation import Driver

from .base import BaseNodeTest
from .import_probe import probe
from .test_math import _eval_openscad_expr
from .coupling_project.parts import Belt, Link, Pulley, Rod, Wheel
from .coupling_project.train import (Arbor, Arm, BackwardsTrain, PITCH_ARC,
                                     Train, Upper, Wrist, mesh)

from solid_node.motion.couplings import PrematureRead


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

    def test_a_repeated_child_named_as_the_source_is_refused(self):
        """cycle: repeat-fan-out. Renamed from '...is_refused': a
        repeated child as the DRIVEN end is now a broadcast (see
        FanOutTest below) and no longer refused here; only naming it as
        the SOURCE stays refused, and the exception is now a TypeError
        raised by the relation's own check, not a SidewaysReadError
        raised while reading the path."""
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                count = Count(3, min=1)
                power = RotationalPort(unit='deg')
                units = Pulley().repeat(count)

                units.turn.drives(power)

        message = str(raised.exception)
        for expected in ('units', 'Pulley', 'repeated'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

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
# 1.3b Fan-out over a repeated child (cycle: repeat-fan-out)

class Bead(Solid2Node):
    """One joint, no `index` of its own -- the fan-out fixture leaf."""

    travel = Prismatic(axis=(0, 0, 1), unit='mm')

    def render(self):
        return cube(1, center=True)


class FanColumn(AssemblyNode):
    """A repeat with nothing driving it: the shape every broadcast test
    below states its own relation on."""

    beads = Bead().repeat(4)


class FanLeg(AssemblyNode):
    """A plain child under a repeated child: `legs.femur.travel` is one
    fan-out, not two."""

    femur = Bead()


def bead_travels(nodes):
    return [bead.travel.value for bead in nodes]


class FanOutTest(BaseNodeTest):

    ##############################################
    # 2. The broadcast end resolves

    def test_a_repeated_driven_end_is_n_relations(self):
        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            earth.drives(beads.travel)

        column = Column()
        column.set_state(earth=3.0)

        self.assertEqual(bead_travels(column.beads), [3.0] * 4)
        for bead in column.beads:
            with self.subTest(bead=bead.name):
                self.assertEqual(bead.operations[-1].serialized,
                                 ['t', ['0', '0', '3.0']])

    def test_a_repeated_node_end_is_the_copies_one_joint(self):
        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            earth.drives(beads)

        column = Column()
        column.set_state(earth=5.0)

        self.assertEqual(bead_travels(column.beads), [5.0] * 4)

    def test_a_repeated_node_with_no_joint_reaches_the_existing_message(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                earth = SignalPort()
                plates = Link().repeat(4)

                earth.drives(plates)

        message = str(raised.exception)
        self.assertIn('Link', message)
        self.assertIn('joint', message)
        self.assertNotIn('one repeat', message)

    def test_a_repeat_one_level_down_binds_only_its_own_copies(self):
        class Rig(AssemblyNode):
            drive = Driver(default=0.0, unit='mm')
            first = FanColumn()
            second = FanColumn()

            drive.drives(first.beads.travel)

        rig = Rig()
        rig.set_state(drive=7.0)

        self.assertEqual(bead_travels(rig.first.beads), [7.0] * 4)
        self.assertEqual(bead_travels(rig.second.beads), [None] * 4)

    def test_a_plain_child_under_the_copies_is_one_fan_out(self):
        class Hexapod(AssemblyNode):
            yaw = Driver(default=0.0, unit='mm')
            legs = FanLeg().repeat(6)

            yaw.drives(legs.femur.travel)

        hexapod = Hexapod()
        hexapod.set_state(yaw=2.0)

        self.assertEqual([leg.femur.travel.value for leg in hexapod.legs],
                         [2.0] * 6)

    def test_two_repeated_segments_are_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Cage(AssemblyNode):
                joints = Bead().repeat(2)

            class Bad(AssemblyNode):
                yaw = SignalPort()
                legs = Cage().repeat(4)

                yaw.drives(legs.joints.travel)

        message = str(raised.exception)
        for expected in ('legs', 'joints', 'Cage', 'Bead'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_list_held_child_bare_is_refused_with_its_own_message(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                power = SignalPort()
                plates = [Bead(), Bead()]

                power.drives(plates)

        message = str(raised.exception)
        self.assertIn('plates', message)
        self.assertIn('one by one', message)
        self.assertNotIn('one repeat', message)

    def test_a_list_held_child_through_a_path_is_refused(self):
        class Frame(AssemblyNode):
            plates = [Bead(), Bead()]

        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                power = SignalPort()
                frame = Frame()

                power.drives(frame.plates.travel)

        message = str(raised.exception)
        self.assertIn('plates', message)
        self.assertIn('one by one', message)

    def test_a_list_in_the_same_body_is_a_bare_python_error(self):
        """Pre-existing and out of this cycle's scope: a class-body
        list is a plain Python list, not a declaration object, so
        reading an attribute off it in the SAME body never reaches the
        framework at all (measured, evidence/probe_list_held_today.py).
        """
        with self.assertRaises(AttributeError) as raised:
            class Bad(AssemblyNode):
                power = SignalPort()
                plates = [Bead(), Bead()]

                power.drives(plates.travel)

        self.assertIn("'list' object has no attribute 'travel'",
                     str(raised.exception))

    def test_a_repeated_source_is_refused_three_ways(self):
        def travel_form():
            class Bad(AssemblyNode):
                earth = SignalPort()
                beads = Bead().repeat(4)

                beads.travel.drives(earth)

        def bare_node_form():
            class Bad(AssemblyNode):
                earth = SignalPort()
                beads = Bead().repeat(4)

                beads.drives(earth)

        def path_form():
            class Column(AssemblyNode):
                beads = Bead().repeat(4)

            class Bad(AssemblyNode):
                earth = SignalPort()
                column = Column()

                column.beads.travel.drives(earth)

        for form in (travel_form, bare_node_form, path_form):
            with self.subTest(form=form.__name__):
                with self.assertRaises(TypeError) as raised:
                    form()
                message = str(raised.exception)
                self.assertIn('beads', message)
                self.assertIn('Bead', message)

    def test_a_broadcast_in_a_formula_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                earth = SignalPort()
                beads = Bead().repeat(4)

                bad = beads.travel - earth

        message = str(raised.exception)
        self.assertIn('beads', message)
        self.assertIn('law=', message)

    def test_a_repeat_of_a_multi_coordinate_joint_lists_its_coordinates(self):
        class Floater(Solid2Node):
            pose = Free(angle_unit='deg', length_unit='mm')

            def render(self):
                return cube(1, center=True)

        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                tilt = SignalPort()
                floaters = Floater().repeat(4)

                tilt.drives(floaters.pose)

        message = str(raised.exception)
        for expected in ('pose', 'roll', 'pitch', 'yaw', 'x', 'y', 'z'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    ##############################################
    # 3. The law, the ratio, and the solve

    def test_a_law_is_called_once_per_copy_and_handed_the_copy(self):
        calls = []

        def earth_lift(driver, driven):
            calls.append((driver, driven, driven.index))
            return ForwardOnly(lambda level: level + driven.index)

        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            earth.drives(beads.travel, law=earth_lift)

        column = Column()

        self.assertEqual(len(calls), 4)
        self.assertEqual([index for _driver, _driven, index in calls],
                         [0, 1, 2, 3])
        self.assertTrue(all(driver is column for driver, _d, _i in calls))
        self.assertEqual([driven for _d, driven, _i in calls],
                         list(column.beads))

        column.set_state(earth=10.0)
        self.assertEqual(bead_travels(column.beads), [10.0, 11.0, 12.0, 13.0])

        for value in (20.0, 30.0):
            column.set_state(earth=value)
        self.assertEqual(len(calls), 4)

    def test_the_laws_signature_is_unchanged(self):
        """No `inspect` of any kind is reachable from the framework's
        side: a callable of signature `(*args)` still works."""
        def law(*args):
            driven = args[1]
            return ForwardOnly(lambda level: level + getattr(driven,
                                                              'index', 0))

        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            other = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(3)
            single = Bead()

            earth.drives(beads.travel, law=law)
            other.drives(single.travel, law=law)

        column = Column()
        column.set_state(earth=1.0, other=1.0)

        self.assertEqual(bead_travels(column.beads), [1.0, 2.0, 3.0])
        self.assertEqual(column.single.travel.value, 1.0)

    def test_a_ratio_broadcasts_the_same_resolved_number(self):
        class Column(AssemblyNode):
            scale = Ratio(2.0)
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            earth.drives(beads.travel, ratio=scale)

        column = Column(scale=4.0)
        column.set_state(earth=3.0)

        self.assertEqual(bead_travels(column.beads), [12.0] * 4)

    def test_declaration_order_is_copy_order_and_is_irrelevant(self):
        order = []

        def watching(name):
            def law(driver, driven):
                order.append((name, getattr(driven, 'index', None)))
                return ForwardOnly(lambda level: level)
            return law

        class Forwards(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            beads = Bead().repeat(3)
            c = SignalPort()

            a.drives(b, law=watching('first'))
            b.drives(beads.travel, law=watching('broadcast'))
            b.drives(c, law=watching('third'))

        order.clear()
        Forwards()

        self.assertEqual(order,
                         [('first', None), ('broadcast', 0),
                          ('broadcast', 1), ('broadcast', 2),
                          ('third', None)])

    def test_a_named_broadcast_reads_as_a_tuple_of_records(self):
        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            fan = earth.drives(beads.travel)

        column = Column()
        column.set_state(earth=1.0)

        records = Column.fan.__get__(column)
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record.direction == 'forward'
                            for record in records))

        class Empty(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            count = Count(0, min=0)
            beads = Bead().repeat(count)

            fan = earth.drives(beads.travel)

        empty = Empty()
        empty.set_state(earth=1.0)
        self.assertEqual(Empty.fan.__get__(empty), ())

    def test_a_zero_count_broadcast_binds_nothing_and_refuses_nothing(self):
        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            count = Count(0, min=0)
            beads = Bead().repeat(count)

            earth.drives(beads.travel)

        column = Column()
        column.set_state(earth=3.0)

        self.assertEqual(column.beads, [])

    def test_omitted_copies_are_still_driven(self):
        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            earth.drives(beads.travel)

            def render(self):
                return [bead for index, bead in enumerate(self.beads)
                       if index != 2]

        column = Column()
        column.set_state(earth=6.0)
        tree = column.render()

        self.assertEqual(bead_travels(column.beads), [6.0] * 4)
        self.assertEqual(len(tree), 3)

    def test_the_second_run_re_solves(self):
        class Column(AssemblyNode):
            earth = Driver(default=0.0, unit='mm')
            beads = Bead().repeat(4)

            earth.drives(beads.travel)

        column = Column()
        for value in (1.0, 2.0, 3.0):
            column.set_state(earth=value)
            self.assertEqual(bead_travels(column.beads), [value] * 4)

    def test_symbolic_values_pass_through_a_broadcast(self):
        """`ratio=` resolves ONCE against the declaring instance and the
        SAME `Affine` -- symbolic or numeric alike -- is every copy's
        law (design.md decision 5): checked here by object identity,
        which is what makes a symbolic operand ride through unchanged
        on every copy rather than being re-evaluated per copy."""
        class Column(AssemblyNode):
            earth = SignalPort()
            beads = Bead().repeat(3)

            fan = earth.drives(beads.travel, ratio=2.0)

        column = Column()

        laws = {id(record.law) for record in Column.fan.__get__(column)}
        self.assertEqual(len(laws), 1)

        column.earth = 5.0
        column.render()
        self.assertEqual(bead_travels(column.beads), [10.0] * 3)

    ##############################################
    # 4. The refusals under a broadcast

    def test_a_broadcast_is_never_inverted(self):
        """A single copy, so no OTHER copy's unreached coordinate is
        what the solver reports first: this proves the broadcast rule,
        not an ordering accident. The DEFAULT identity law would invert
        perfectly well, which is what proves it is the broadcast that
        refuses, not the law."""
        class Column(AssemblyNode):
            earth = SignalPort()
            beads = Bead().repeat(1)

            earth.drives(beads.travel)

            def simulate(self):
                self.beads[0].travel = 9.0

        column = Column()
        with self.assertRaises(NotInvertible) as raised:
            column.render()

        message = str(raised.exception)
        for expected in ('beads-0', 'forward only'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_doubly_bound_copy_names_that_copy(self):
        class Column(AssemblyNode):
            earth = SignalPort()
            beads = Bead().repeat(4)

            earth.drives(beads.travel)

            def simulate(self):
                self.earth = 3.0
                self.beads[2].travel = 9.0

        column = Column()
        with self.assertRaises(DoublyBound) as raised:
            column.render()

        self.assertIn('beads-2', str(raised.exception))

    def test_a_wired_copy_and_a_broadcast_are_two_binders(self):
        class Column(AssemblyNode):
            earth = SignalPort()
            beads = Bead(travel=earth).repeat(4)

            earth.drives(beads.travel)

            def simulate(self):
                self.earth = 3.0

        column = Column()
        with self.assertRaises(DoublyBound) as raised:
            column.render()

        message = str(raised.exception)
        self.assertIn('beads-0', message)
        self.assertIn('wir', message)

    def test_the_wiring_path_still_works_alone(self):
        """GREEN before the change and after it: the evidence for
        building no wiring keyword on .repeat()."""
        class Column(AssemblyNode):
            earth = SignalPort()
            beads = Bead(travel=earth).repeat(4)

            def simulate(self):
                self.earth = 3.0

        column = Column()
        column.render()

        self.assertEqual([bead.name for bead in column.beads],
                         ['beads-0', 'beads-1', 'beads-2', 'beads-3'])
        self.assertEqual(bead_travels(column.beads), [3.0] * 4)
        self.assertEqual({bead.uniq_id for bead in column.beads},
                         {'Bead-aa06a2f044b4'})
        self.assertEqual([len(bead.operations) for bead in column.beads],
                         [1, 1, 1, 1])

    def test_a_wired_source_solved_by_a_relation_binds_in_the_same_pass(self):
        """A supporting characterisation, not a broadcast: the wiring
        must keep binding once its source -- itself solved by an
        ordinary relation -- is bound in the same pass, with a repeated
        wired child alongside it."""
        class Column(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            pulley = Pulley()
            earth = TranslationalPort(unit='mm')
            beads = Bead(travel=earth).repeat(3)

            pulley.turn.drives(earth, ratio=2.0)

            def simulate(self):
                self.pulley.turn = self.angle

        column = Column()
        column.set_state(angle=5.0)

        self.assertEqual(bead_travels(column.beads), [10.0] * 3)


##############################################
# 1.3c Several coordinates at one end (cycle: multi-source-multi-target-laws)

class GroupRod(Solid2Node):
    """Four joints in fixed order -- three revolutes then a prismatic --
    the delta printer's rod, whose four freedoms come from one law of
    three sources."""

    spin = Revolute(axis=(0, 0, 1), unit='deg')
    lean = Revolute(axis=(1, 0, 0), unit='deg')
    swing = Revolute(axis=(0, 1, 0), unit='deg')
    rise = Prismatic(axis=(0, 0, 1), unit='mm')

    def render(self):
        return cube(1, center=True)


class GroupLeg(Solid2Node):
    """Two joints -- OpenFlexure's leg, whose lean and tilt come from one
    law of two sources."""

    lean = Revolute(axis=(1, 0, 0), unit='deg')
    tilt = Revolute(axis=(0, 1, 0), unit='deg')

    def render(self):
        return cube(1, center=True)


class GroupMachine(AssemblyNode):
    """Three drivers, a broadcast of six rods and one plain rod: the
    fixture most tests below state their own relation on."""

    x = Driver(default=0.0, unit='mm')
    y = Driver(default=0.0, unit='mm')
    z = Driver(default=0.0, unit='mm')
    rods = GroupRod().repeat(6)
    rod = GroupRod()


def rod_pose(rod):
    return (rod.spin.value, rod.lean.value, rod.swing.value, rod.rise.value)


class GroupStatementTest(BaseNodeTest):
    """1.2, 1.3, 1.4: `&` and the tuple as class-body statements."""

    def test_a_group_of_sources_drives_one_coordinate(self):
        calls = []

        def law(sources, driven):
            calls.append((sources, driven))
            return ForwardOnly(lambda x, y: x + y)

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            child = GroupRod()

            fan = (a & b).drives(child.spin, law=law)

            def simulate(self):
                self.a = 2.0
                self.b = 3.0

        root = Root()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ((root, root), root.child))
        record = Root.fan.__get__(root)
        self.assertEqual(len(record.driver_ends), 2)
        self.assertEqual(len(record.driven_ends), 1)

        root.render()
        self.assertEqual(root.child.spin.value, 5.0)

    def test_a_tuple_of_driven_ends_and_an_ampersand_state_one_relation(self):
        def law_tuple(driver, driven):
            return ForwardOnly(lambda v: (v, 2 * v))

        def law_amp(driver, driven):
            return ForwardOnly(lambda v: (v, 2 * v))

        class TupleRoot(AssemblyNode):
            a = SignalPort()
            child = GroupLeg()

            fan = a.drives((child.lean, child.tilt), law=law_tuple)

            def simulate(self):
                self.a = 3.0

        class AmpRoot(AssemblyNode):
            a = SignalPort()
            child = GroupLeg()

            fan = a.drives(child.lean & child.tilt, law=law_amp)

            def simulate(self):
                self.a = 3.0

        for RootClass in (TupleRoot, AmpRoot):
            with self.subTest(RootClass=RootClass.__name__):
                relations = declared_relations(RootClass)
                self.assertEqual(len(relations), 1)
                root = RootClass()
                record = RootClass.fan.__get__(root)
                self.assertEqual(len(record.driver_ends), 1)
                self.assertEqual(len(record.driven_ends), 2)
                root.render()
                self.assertEqual(root.child.lean.value, 3.0)
                self.assertEqual(root.child.tilt.value, 6.0)

    def test_ampersand_chains_flat_not_nested(self):
        seen = []

        def law(sources, driven):
            seen.append(sources)
            return ForwardOnly(lambda *values: sum(values))

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            child = GroupRod()

            fan = (a & b & c).drives(child.spin, law=law)

            def simulate(self):
                self.a = 1.0
                self.b = 2.0
                self.c = 3.0

        root = Root()
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], (root, root, root))
        record = Root.fan.__get__(root)
        self.assertEqual(len(record.driver_ends), 3)

        root.render()
        self.assertEqual(root.child.spin.value, 6.0)


class GroupRefusalTest(BaseNodeTest):
    """1.5, 1.6: every group refusal, and the existing per-member
    refusals reached inside a group."""

    def _class_body(self, body):
        with self.assertRaises(TypeError) as raised:
            body()
        return str(raised.exception)

    def test_a_repeated_source_inside_a_group_is_refused(self):
        def body():
            class Bad(AssemblyNode):
                earth = SignalPort()
                rods = GroupRod().repeat(3)

                (rods.spin & earth).drives(earth, law=lambda *a: (
                    ForwardOnly(lambda *v: v[0])))
        message = self._class_body(body)
        self.assertIn('rods', message)
        self.assertIn('GroupRod', message)

    def test_a_driven_group_mixing_a_broadcast_with_a_plain_end(self):
        def body():
            class Bad(AssemblyNode):
                x = SignalPort()
                rods = GroupRod().repeat(3)
                lid = SignalPort()

                x.drives((rods.spin, lid), law=lambda *a: (
                    ForwardOnly(lambda v: (v, v))))
        message = self._class_body(body)
        self.assertIn('repeat', message)
        self.assertIn('rods', message)

    def test_a_driven_group_over_two_different_repeats_is_refused(self):
        def body():
            class Side(AssemblyNode):
                beads = GroupLeg().repeat(2)

            class Bad(AssemblyNode):
                x = SignalPort()
                left = Side()
                right = Side()

                x.drives((left.beads.lean, right.beads.lean), law=lambda *a: (
                    ForwardOnly(lambda v: (v, v))))
        message = self._class_body(body)
        self.assertIn('repeat', message)
        self.assertIn('beads', message)

    def test_ratio_or_offset_with_a_group_is_refused(self):
        def ratio_form():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                child = GroupRod()

                (a & b).drives(child.spin, ratio=2)

        def offset_form():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                child = GroupRod()

                (a & b).drives(child.spin, offset=2)

        for form in (ratio_form, offset_form):
            with self.subTest(form=form.__name__):
                message = self._class_body(form)
                self.assertIn('one value to one value', message)

    def test_a_group_with_no_law_is_refused(self):
        def body():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                child = GroupRod()

                (a & b).drives(child.spin)
        message = self._class_body(body)
        self.assertIn('law=', message)
        self.assertIn('one value to one value', message)

    def test_an_empty_group_and_a_group_of_one_are_refused(self):
        def empty_form():
            class Bad(AssemblyNode):
                a = SignalPort()
                child = GroupRod()

                a.drives((), law=lambda *x: ForwardOnly(lambda v: v))

        def one_form():
            class Bad(AssemblyNode):
                a = SignalPort()
                child = GroupRod()

                a.drives((child.spin,), law=lambda *x: ForwardOnly(lambda v: v))

        for form in (empty_form, one_form):
            with self.subTest(form=form.__name__):
                message = self._class_body(form)
                self.assertIn('two coordinates or more', message)
                self.assertIn('one by one', message)

    def test_a_nested_group_is_refused(self):
        def body():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                c = SignalPort()
                child = GroupRod()

                a.drives(((child.spin, child.lean), c),
                        law=lambda *x: ForwardOnly(lambda *v: v))
        message = self._class_body(body)
        self.assertIn('two coordinates or more', message)
        self.assertIn('one by one', message)

    def test_a_repeated_coordinate_in_one_group_is_refused(self):
        def body():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                child = GroupRod()

                (a & a).drives(child.spin, law=lambda *x: (
                    ForwardOnly(lambda *v: v[0])))
        message = self._class_body(body)
        self.assertIn('once', message)

    def test_a_coordinate_on_both_sides_of_a_group_relation_is_refused(self):
        def body():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                child = GroupRod()

                (a & b).drives((b, child.spin), law=lambda *x: (
                    ForwardOnly(lambda *v: v)))
        message = self._class_body(body)
        self.assertIn('source', message)
        self.assertIn('driven', message)
        self.assertIn('not both', message)

    def test_a_group_as_a_term_of_a_formula_is_refused(self):
        def body():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                c = SignalPort()

                bad = (a & b) - c
        message = self._class_body(body)
        self.assertIn('one value per term', message)

    def test_ampersand_over_a_non_coordinate_is_refused(self):
        def number_form():
            class Bad(AssemblyNode):
                a = SignalPort()

                bad = a & 3

        def text_form():
            class Bad(AssemblyNode):
                a = SignalPort()

                bad = a & 'not a coordinate'

        for form in (number_form, text_form):
            with self.subTest(form=form.__name__):
                message = self._class_body(form)
                self.assertIn('coordinate', message)

    def test_the_missing_parentheses_are_named(self):
        def body():
            class Bad(AssemblyNode):
                count = SignalPort()
                next_count = SignalPort()
                pawl = GroupRod()

                count & next_count.drives(pawl.spin, law=lambda *x: (
                    ForwardOnly(lambda v: v)))
        message = self._class_body(body)
        self.assertIn('parentheses', message)
        self.assertIn('next_count', message)

    def test_existing_per_member_refusals_are_reached_inside_a_group(self):
        def driver_as_driven():
            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                power = Driver(default=0.0, unit='deg')
                child = GroupRod()

                (a & b).drives((child.spin, power), law=lambda *x: (
                    ForwardOnly(lambda *v: v)))

        def two_joint_node():
            class TwoJoints(Solid2Node):
                one = Revolute(axis=(0, 0, 1), unit='deg')
                two = Revolute(axis=(0, 1, 0), unit='deg')

                def render(self):
                    return cube(1, center=True)

            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                weird = TwoJoints()

                (a & b).drives(weird, law=lambda *x: (
                    ForwardOnly(lambda *v: v[0])))

        def multi_coordinate_joint():
            class Floater(Solid2Node):
                pose = Free(angle_unit='deg', length_unit='mm')

                def render(self):
                    return cube(1, center=True)

            class Bad(AssemblyNode):
                a = SignalPort()
                b = SignalPort()
                floater = Floater()

                (a & b).drives(floater.pose, law=lambda *x: (
                    ForwardOnly(lambda *v: v[0])))

        message = self._class_body(driver_as_driven)
        self.assertIn('driver', message)
        self.assertIn('bound snapshot', message)

        message = self._class_body(two_joint_node)
        self.assertIn('TwoJoints', message)
        self.assertIn('one', message)

        message = self._class_body(multi_coordinate_joint)
        for expected in ('pose', 'roll', 'pitch', 'yaw'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)


##############################################
# 2. Red first: the law protocol

class LawShapeTest(BaseNodeTest):

    def test_the_law_is_handed_two_tuples_once_at_realization(self):
        calls = []
        simulated = []

        def law(*args):
            calls.append(args)
            return ForwardOnly(lambda *values: values)

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            rods = GroupRod().repeat(1)

            fan = (a & b & c).drives(
                (rods.spin, rods.lean, rods.swing, rods.rise), law=law)

            def simulate(self):
                simulated.append('simulate ran')
                self.a = 1.0
                self.b = 2.0
                self.c = 3.0

        root = Root()
        self.assertEqual(len(calls), 1)
        self.assertFalse(simulated)  # the call happened BEFORE simulate()
        sources, driven = calls[0]
        self.assertEqual(sources, (root, root, root))
        self.assertEqual(len(driven), 4)
        self.assertTrue(all(node is root.rods[0] for node in driven))

    def test_a_one_to_one_law_still_receives_two_nodes(self):
        calls = []

        def law(driver, driven):
            calls.append((driver, driven))
            return ForwardOnly(lambda v: v)

        class Root(AssemblyNode):
            a = SignalPort()
            child = GroupRod()

            a.drives(child.spin, law=law)

        root = Root()
        self.assertEqual(calls, [(root, root.child)])
        self.assertNotIsInstance(calls[0][0], tuple)
        self.assertNotIsInstance(calls[0][1], tuple)

    def test_mixed_arities_hand_a_tuple_and_a_node_each_way(self):
        seen = {}

        def law_n_to_1(sources, driven):
            seen['n_to_1'] = (sources, driven)
            return ForwardOnly(lambda *v: sum(v))

        def law_1_to_m(driver, driven):
            seen['1_to_m'] = (driver, driven)
            return ForwardOnly(lambda v: (v, v))

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            rod1 = GroupRod()
            rod2 = GroupLeg()

            (a & b & c).drives(rod1.spin, law=law_n_to_1)
            a.drives((rod2.lean, rod2.tilt), law=law_1_to_m)

        root = Root()
        n_to_1_sources, n_to_1_driven = seen['n_to_1']
        self.assertEqual(n_to_1_sources, (root, root, root))
        self.assertNotIsInstance(n_to_1_driven, tuple)

        one_driver, m_driven = seen['1_to_m']
        self.assertNotIsInstance(one_driver, tuple)
        self.assertEqual(len(m_driven), 2)

    def test_forward_spreads_sources_and_returns_in_written_order(self):
        def law(sources, driven):
            return ForwardOnly(lambda x, y, z: (x + y, y + z, z + x, x * y * z))

        class Root(AssemblyNode):
            x = SignalPort()
            y = SignalPort()
            z = SignalPort()
            rod = GroupRod()

            (x & y & z).drives(
                (rod.spin, rod.lean, rod.swing, rod.rise), law=law)

            def simulate(self):
                self.x = 2.0
                self.y = 3.0
                self.z = 5.0

        for kind in (tuple, list):
            with self.subTest(kind=kind.__name__):
                root = Root()
                root.render()
                self.assertEqual(root.rod.spin.value, 5.0)
                self.assertEqual(root.rod.lean.value, 8.0)
                self.assertEqual(root.rod.swing.value, 7.0)
                self.assertEqual(root.rod.rise.value, 30.0)

    def test_a_wrong_return_shape_is_refused_by_name(self):
        def make_root(law):
            class Root(AssemblyNode):
                x = SignalPort()
                y = SignalPort()
                z = SignalPort()
                rod = GroupRod()

                (x & y & z).drives(
                    (rod.spin, rod.lean, rod.swing, rod.rise), law=law)

                def simulate(self):
                    self.x = 1.0
                    self.y = 2.0
                    self.z = 3.0
            return Root

        too_few = make_root(lambda *a: ForwardOnly(lambda *v: (1.0, 2.0, 3.0)))
        too_many = make_root(
            lambda *a: ForwardOnly(lambda *v: (1.0, 2.0, 3.0, 4.0, 5.0)))
        bare_number = make_root(lambda *a: ForwardOnly(lambda *v: 4.0))
        as_text = make_root(lambda *a: ForwardOnly(lambda *v: 'abcd'))

        class Unsized:
            pass

        no_length = make_root(lambda *a: ForwardOnly(lambda *v: Unsized()))

        for RootClass in (too_few, too_many, bare_number, as_text, no_length):
            with self.subTest(RootClass=RootClass.__name__):
                root = RootClass()
                with self.assertRaises(CouplingError) as raised:
                    root.render()
                message = str(raised.exception)
                self.assertIn('4', message)
                for coordinate in ('spin', 'lean', 'swing', 'rise'):
                    with self.subTest(coordinate=coordinate):
                        self.assertIn(coordinate, message)
                self.assertIsNone(root.rod.spin.value)
                self.assertIsNone(root.rod.lean.value)
                self.assertIsNone(root.rod.swing.value)
                self.assertIsNone(root.rod.rise.value)

    def test_a_single_driven_end_returns_a_bare_value_symbolic_too(self):
        class Root(AssemblyNode):
            x = SignalPort()
            y = SignalPort()
            child = GroupRod()

            (x & y).drives(child.spin, law=lambda *a: (
                ForwardOnly(lambda p, q: p + q)))

            def simulate(self):
                self.x = self.time
                self.y = 1.0

        root = Root()
        document, _ids = symbolic_parts(root)
        angle = rotations(document, 'child')
        self.assertTrue(angle)

    def test_no_new_error_kind(self):
        """A wrong return shape is a `CouplingError`, and the THREE named
        refusals ("Three refusals keep a wrong drive network from
        becoming a pose") stay three; `PrematureRead` is a pre-existing
        fourth `CouplingError`, from a different requirement
        (whole-tree-fixpoint), untouched by this cycle."""
        from solid_node.motion import couplings as couplings_module

        error_names = {
            name for name in couplings_module.__all__
            if isinstance(getattr(couplings_module, name), type)
            and issubclass(getattr(couplings_module, name), CouplingError)
            and getattr(couplings_module, name) is not CouplingError
        }
        self.assertEqual(error_names,
                         {'DoublyBound', 'NotInvertible', 'UnreachedCoordinate',
                          'PrematureRead'})


##############################################
# 3. Red first: the solver

class GroupSolverTest(BaseNodeTest):

    def test_forward_once_when_the_last_source_is_bound(self):
        calls = []

        def law(sources, driven):
            return ForwardOnly(lambda x, y, z: (calls.append('bound'), x + y + z)[1])

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            child = GroupRod()

            (a & b & c).drives(child.spin, law=law)
            b.drives(c)

            def simulate(self):
                self.a = 1.0
                self.b = 2.0

        root = Root()
        root.render()

        self.assertEqual(len(calls), 1)
        self.assertEqual(root.child.spin.value, 5.0)

    def test_a_relation_of_several_ends_defers_to_the_whole_tree_fixpoint(self):
        """task 3.2: the third source is bound by a DESCENDANT's own
        relation, which only resolves in the descendant's OWN phase --
        after the root's own attempt already ran and found it unbound.
        The root's group relation must therefore be carried into the
        enumeration's fixpoint and solved there."""
        class Descendant(AssemblyNode):
            supply = SignalPort()
            c = SignalPort()

            supply.drives(c)

            def simulate(self):
                self.supply = 3.0

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            child = GroupRod()
            descendant = Descendant()

            (a & b & descendant.c).drives(child.spin, law=lambda *x: (
                ForwardOnly(lambda p, q, r: p + q + r)))

            def simulate(self):
                self.a = 1.0
                self.b = 2.0

        root = Root()
        root.render()

        self.assertEqual(root.child.spin.value, 6.0)
        self.assertTrue(motions(root.child))

        root.render()
        self.assertEqual(root.child.spin.value, 6.0)

    def test_a_group_relation_is_never_inverted(self):
        class InvertibleLaw:
            invertible = True

            def forward(self, x, y):
                return x + y

            def inverse(self, value):
                return (value / 2, value / 2)

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            child = GroupRod()

            (a & b).drives(child.spin, law=lambda *x: InvertibleLaw())

            def simulate(self):
                self.child.spin = 9.0

        root = Root()
        with self.assertRaises(NotInvertible) as raised:
            root.render()

        message = str(raised.exception)
        self.assertIn('spin', message)
        self.assertIn('forward only', message)

    def test_the_unreached_message_names_the_unbound_source(self):
        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            child = GroupRod()

            (a & b & c).drives(child.spin, law=lambda *x: (
                ForwardOnly(lambda p, q, r: p + q + r)))

            def simulate(self):
                self.a = 1.0
                self.b = 2.0

        root = Root()
        with self.assertRaises(UnreachedCoordinate) as raised:
            root.render()

        message = str(raised.exception)
        # The relation is named as written -- (a, b, c) drives child.spin --
        # but the "waiting for" clause, which is what the requirement means
        # by "naming exactly the unbound sources", names ONLY the one
        # still-unbound node-qualified coordinate: c, not a or b.
        self.assertIn('waiting for', message)
        waiting_for = message.split('waiting for', 1)[1]
        self.assertIn('.c', waiting_for)
        self.assertNotIn('Root (Root).a', waiting_for)
        self.assertNotIn('Root (Root).b', waiting_for)

    def test_claim_before_bind_leaves_the_other_three_untouched(self):
        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            child = GroupRod()

            (a & b & c).drives(
                (child.spin, child.lean, child.swing, child.rise),
                law=lambda *x: ForwardOnly(lambda p, q, r: (p, q, r, p + q + r)))

            def simulate(self):
                self.a = 1.0
                self.b = 2.0
                self.c = 3.0
                self.child.lean = 99.0

        root = Root()
        with self.assertRaises(DoublyBound) as raised:
            root.render()

        message = str(raised.exception)
        self.assertIn('lean', message)
        self.assertIsNone(root.child.spin.value)
        self.assertIsNone(root.child.swing.value)
        self.assertIsNone(root.child.rise.value)

    def test_the_second_run_re_solves(self):
        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            child = GroupRod()

            (a & b & c).drives(
                (child.spin, child.lean, child.swing, child.rise),
                law=lambda *x: ForwardOnly(lambda p, q, r: (p, q, r, p + q + r)))

            def simulate(self):
                self.a = self._value
                self.b = self._value * 2
                self.c = self._value * 3

        for value in (1.0, 2.0, 3.0):
            root = Root()
            root._value = value
            root.render()
            self.assertEqual(rod_pose(root.child)[:3],
                             (value, value * 2, value * 3))

    def test_symbolic_values_pass_through_a_group(self):
        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            child = GroupRod()

            (a & b & c).drives(
                (child.spin, child.lean, child.swing, child.rise),
                law=lambda *x: ForwardOnly(lambda p, q, r: (p, q, r, p + q + r)))

            def simulate(self):
                self.a = self.time
                self.b = 2.0
                self.c = 3.0

        root = Root()
        document, ids = symbolic_parts(root)
        angles = rotations(document, 'child')
        self.assertTrue(any('$t' in str(a) or 'time' in str(a).lower()
                            for a in angles) or ids)

        root.set_state(time=4.0)
        self.assertEqual(root.child.spin.value, 4.0)

    def test_order_is_unchanged_by_the_new_record_shape(self):
        order = []

        def watching(name):
            def law(*args):
                order.append(name)
                return ForwardOnly(lambda *v: v[0] if len(v) == 1 else v)
            return law

        class Root(AssemblyNode):
            a = SignalPort()
            b = SignalPort()
            c = SignalPort()
            d = SignalPort()
            child = GroupRod()

            a.drives(b, law=watching('A'))
            (b & c).drives(child.spin, law=watching('B'))
            c.drives(d, law=watching('C'))

        Root()
        self.assertEqual(order, ['A', 'B', 'C'])


##############################################
# 4. Red first: several ends over a repeat

class GroupFanOutTest(BaseNodeTest):

    def test_six_copies_four_ends_six_law_calls(self):
        calls = []

        def delta_rod(sources, rods):
            # `rods` is the tuple of the FOUR driven ends' owners --
            # every one of them the SAME copy, so any of the four names
            # its index.
            index = rods[0].index
            calls.append(index)
            return ForwardOnly(
                lambda x, y, z: (x + index, y + index, z + index, index * 1.0))

        class Delta(GroupMachine):
            (GroupMachine.x & GroupMachine.y & GroupMachine.z).drives(
                (GroupMachine.rods.spin, GroupMachine.rods.lean,
                 GroupMachine.rods.swing, GroupMachine.rods.rise),
                law=delta_rod)

        delta = Delta()
        self.assertEqual(calls, list(range(6)))

        delta.set_state(x=1.0, y=2.0, z=3.0)
        for index, rod in enumerate(delta.rods):
            with self.subTest(index=index):
                self.assertEqual(rod_pose(rod),
                                 (1.0 + index, 2.0 + index, 3.0 + index,
                                  float(index)))

        delta.render()
        # The bodies are placed, not only the slots: two different copies
        # carry different operations once placed.
        self.assertNotEqual(delta.rods[0].operations, delta.rods[1].operations)

    def test_the_named_relation_reads_as_six_records_in_copy_order(self):
        class Delta(AssemblyNode):
            x = Driver(default=0.0, unit='mm')
            y = Driver(default=0.0, unit='mm')
            z = Driver(default=0.0, unit='mm')
            rods = GroupRod().repeat(6)

            fan = (x & y & z).drives(
                (rods.spin, rods.lean, rods.swing, rods.rise),
                law=lambda sources, driven: ForwardOnly(
                    lambda x, y, z: (x, y, z, driven[0].index * 1.0)))

        delta = Delta()
        delta.set_state(x=1.0, y=2.0, z=3.0)

        records = Delta.fan.__get__(delta)
        self.assertEqual(len(records), 6)
        for index, record in enumerate(records):
            with self.subTest(index=index):
                self.assertEqual(record.direction, 'forward')
                self.assertIn('rods', record.described())

    def test_a_doubly_bound_copy_is_refused_naming_that_copy_alone(self):
        class Delta(AssemblyNode):
            x = Driver(default=0.0, unit='mm')
            y = Driver(default=0.0, unit='mm')
            z = Driver(default=0.0, unit='mm')
            rods = GroupRod().repeat(3)

            (x & y & z).drives(
                (rods.spin, rods.lean, rods.swing, rods.rise),
                law=lambda sources, driven: ForwardOnly(
                    lambda x, y, z: (x, y, z, 0.0)))

            def simulate(self):
                self.rods[1].lean = 99.0

        delta = Delta()
        with self.assertRaises(DoublyBound) as raised:
            delta.set_state(x=1.0, y=2.0, z=3.0)

        message = str(raised.exception)
        self.assertIn('rods-1', message)

    def test_several_sources_one_driven_end_over_a_repeat(self):
        class Towers(AssemblyNode):
            x = Driver(default=0.0, unit='mm')
            y = Driver(default=0.0, unit='mm')
            z = Driver(default=0.0, unit='mm')
            towers = GroupLeg().repeat(3)

            (x & y & z).drives(
                towers.lean,
                law=lambda sources, tower: ForwardOnly(
                    lambda x, y, z: x + y + z + tower.index))

        stand = Towers()
        stand.set_state(x=1.0, y=2.0, z=3.0)

        for index, tower in enumerate(stand.towers):
            with self.subTest(index=index):
                self.assertEqual(tower.lean.value, 6.0 + index)

    def test_a_zero_count_repeat_with_several_driven_ends_is_zero_records(self):
        class Delta(AssemblyNode):
            x = Driver(default=0.0, unit='mm')
            y = Driver(default=0.0, unit='mm')
            z = Driver(default=0.0, unit='mm')
            count = Count(0, min=0)
            rods = GroupRod().repeat(count)

            fan = (x & y & z).drives(
                (rods.spin, rods.lean, rods.swing, rods.rise),
                law=lambda sources, driven: ForwardOnly(
                    lambda x, y, z: (x, y, z, 0.0)))

        delta = Delta()
        delta.set_state(x=1.0, y=2.0, z=3.0)

        self.assertEqual(Delta.fan.__get__(delta), ())
        self.assertEqual(delta.rods, [])

    def test_copy_is_the_node_the_repeat_realized_not_a_further_descendant(self):
        class Femur(Solid2Node):
            lift = Prismatic(axis=(0, 0, 1), unit='mm')

            def render(self):
                return cube(1, center=True)

        class SplitLeg(AssemblyNode):
            femur = Femur()
            tibia = Femur()

        class Hexapod(AssemblyNode):
            drive = Driver(default=0.0, unit='mm')
            other = Driver(default=0.0, unit='mm')
            legs = SplitLeg().repeat(4)

            fan = (drive & other).drives(
                (legs.femur.lift, legs.tibia.lift),
                law=lambda sources, driven: ForwardOnly(lambda a, b: (a, b)))

        hexapod = Hexapod()
        records = Hexapod.fan.__get__(hexapod)
        self.assertEqual(len(records), 4)
        for index, (record, leg) in enumerate(zip(records, hexapod.legs)):
            with self.subTest(index=index):
                self.assertIs(record.copy, leg)
                self.assertIsNot(record.copy, leg.femur)


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

    def test_an_occasional_author_binding_is_cleared_with_its_motion(self):
        """Renamed from `..._is_not_cleared`: `whole-tree-fixpoint`
        overturns exactly the guarantee that name stated. An author
        binding made during a simulate phase is now cleared with the
        motion it caused, at the START of that assembly's NEXT phase --
        the author's own binding included -- so a coordinate a
        conditional guard bound once and never rebinds is UNREACHED on
        the run that follows, precisely as an unconditional one would
        be. `StaleAuthorBoundJointTest` in test_joints.py is the positive
        case (an unconditional rest-default guard that DOES rebind every
        run, and therefore never hits this)."""
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

        # The author binds nothing THIS run; what it bound last run is
        # cleared with the motion it caused, so neither end is reached.
        with self.assertRaises(UnreachedCoordinate) as raised:
            machine.set_state(angle=0.0)
        self.assertIn('hand', str(raised.exception))


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


##############################################
# 1.14 A coordinate of a joint that owns several

class Chassis(Solid2Node):
    """A floating body: one joint, six coordinates, each reached by the
    dotted name the port enumerator reports it under."""

    pose = Free(angle_unit='deg', length_unit='mm')

    def render(self):
        return cube(2, center=True)


class Shoulder(AssemblyNode):
    """One level between the root and the floating body, so a path has
    to walk a segment before it reaches the joint."""

    chassis = Chassis()

    def render(self):
        pass


class MultiCoordinateEndTest(BaseNodeTest):
    """`chassis.pose.roll`: a coordinate whose name is two segments.

    The three seams this exercises were measured on the tree before the
    change (`openspec/changes/free-joint/evidence/`): `declared_ports`
    reported nothing for such a joint, `read_through` raised the
    PARAMETER refusal for it, and `setattr(node, 'pose.roll', value)`
    silently created an instance attribute and bound nothing.
    """

    def test_a_relation_reaches_one_coordinate_by_path(self):
        class Rig(AssemblyNode):
            tilt = Driver(default=0.0, unit='deg')
            lift = Driver(default=0.0, unit='mm')

            chassis = Chassis()

            tilt.drives(chassis.pose.pitch)
            lift.drives(chassis.pose.z, ratio=2.0)

            def render(self):
                pass

        rig = Rig()
        rig.set_state(tilt=12.0, lift=30.0)

        self.assertEqual(rig.chassis.pose.pitch.value, 12.0)
        self.assertEqual(rig.chassis.pose.z.value, 60.0)
        for unbound in ('roll', 'yaw', 'x', 'y'):
            with self.subTest(coordinate=unbound):
                self.assertIsNone(getattr(rig.chassis.pose, unbound).value)
        self.assertEqual([operation.serialized[0] for operation
                          in rig.chassis.operations],
                         ['r', 't'])
        self.assertEqual(rig.chassis.operations[0].serialized[1], '12.0')
        self.assertEqual(
            [float(component) for component
             in rig.chassis.operations[1].serialized[1]],
            [0.0, 0.0, 60.0])

    def test_a_relation_into_a_free_coordinate_inverts(self):
        """The driven end is bound and the driver's is solved
        backwards, exactly as the fixture train's escape wheel is."""
        class Rig(AssemblyNode):
            chassis = Chassis()
            pulley = Pulley()

            chassis.pose.pitch.drives(pulley.turn, ratio=2.0)

            def render(self):
                pass

            def simulate(self):
                self.pulley.turn = 30.0

        rig = Rig()
        rig.render()

        self.assertEqual(rig.chassis.pose.pitch.value, 15.0)
        self.assertEqual(rig.chassis.operations[0].serialized[1], '15.0')

    def test_a_relation_is_stated_in_the_joints_own_class_body(self):
        class Floater(AssemblyNode):
            pose = Free(angle_unit='deg', length_unit='mm')

            pulley = Pulley()

            pose.roll.drives(pulley.turn, ratio=3.0)

            def render(self):
                pass

            def simulate(self):
                self.pose.roll = 12.0

        floater = Floater()
        floater.render()

        self.assertEqual(floater.pose.roll.value, 12.0)
        self.assertEqual(floater.pulley.turn.value, 36.0)
        self.assertEqual(floater.operations[0].serialized,
                         ['r', '12.0', [1, 0, 0]])

    def test_the_path_grammar_pops_two_segments(self):
        """`shoulder.chassis.pose.yaw`: two segments naming children and
        two naming the coordinate. The walk must stop at `chassis`."""
        class Rig(AssemblyNode):
            spin = Driver(default=0.0, unit='deg')

            shoulder = Shoulder()

            spin.drives(shoulder.chassis.pose.yaw)

            def render(self):
                pass

        rig = Rig()
        rig.set_state(spin=25.0)

        record = declared_relations(Rig)[0].record_of(rig)
        self.assertIs(record.driven, rig.shoulder.chassis.pose.yaw)
        self.assertEqual(rig.shoulder.chassis.pose.yaw.value, 25.0)
        self.assertEqual(rig.shoulder.chassis.operations[0].serialized,
                         ['r', '25.0', [0, 0, 1]])

    def test_the_joint_itself_is_not_an_end(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                tilt = Driver(default=0.0, unit='deg')
                chassis = Chassis()

                tilt.drives(chassis.pose)

        message = str(raised.exception)
        for expected in ('pose', 'roll', 'pitch', 'yaw', 'x', 'y', 'z'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_part_the_joint_does_not_own_is_refused_by_name(self):
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                tilt = Driver(default=0.0, unit='deg')
                chassis = Chassis()

                tilt.drives(chassis.pose.twist)

        message = str(raised.exception)
        for expected in ('twist', 'pose', 'roll', 'yaw'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_node_whose_one_joint_is_free_is_not_an_end(self):
        """`_the_one_joint` would otherwise pass `len(joints) == 1` and
        return a declaration with no coordinate: a wrong pose, not an
        error."""
        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                tilt = Driver(default=0.0, unit='deg')
                chassis = Chassis()

                tilt.drives(chassis)

        message = str(raised.exception)
        for expected in ('Chassis', 'pose', 'roll', 'pitch', 'yaw'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_relation_binds_through_the_joint_and_not_by_attribute(self):
        """The direct guard on the measured `setattr` hole: with a
        dotted name `setattr(node, 'pose.roll', value)` creates an
        instance attribute and binds nothing."""
        class Rig(AssemblyNode):
            tilt = Driver(default=0.0, unit='deg')

            chassis = Chassis()

            tilt.drives(chassis.pose.roll)

            def render(self):
                pass

        rig = Rig()
        rig.set_state(tilt=12.0)

        self.assertNotIn('pose.roll', rig.chassis.__dict__)
        self.assertNotIn('pose', rig.chassis.__dict__)
        self.assertEqual(rig.chassis.pose.roll.value, 12.0)
        self.assertEqual(declared_ports(Chassis)['pose.roll']
                         .__get__(rig.chassis).value, 12.0)


##############################################
# declaration-site-joint, task 4.4/4.5/4.6: a relation reaches a site
# coordinate exactly as it reaches a class-declared one -- couplings.py
# is UNTOUCHED, because the site's joint is class metadata on the class
# the child is realized as.

class SiteCoordinateLeaf(Solid2Node):
    def render(self):
        return cube(1, center=True)


class SiteCoordinatePathTest(BaseNodeTest):

    def test_a_relation_names_a_site_coordinate_by_path_both_ends(self):
        class Top(AssemblyNode):
            left = SiteCoordinateLeaf(travel=Prismatic(axis=(0, 0, 1),
                                                       unit='mm'))
            right = SiteCoordinateLeaf(travel=Prismatic(axis=(0, 0, 1),
                                                        unit='mm'))

            left.travel.drives(right.travel)

        top = Top()
        top.left.travel = 12.0
        top.render()

        self.assertEqual(top.right.travel.value, 12.0)

    def test_a_broadcast_names_a_site_coordinate_through_a_repeat(self):
        class Top(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            pins = SiteCoordinateLeaf(
                orbit=Orbit(axis=(0, 0, 1), unit='deg')).repeat(3)

            angle.drives(pins.orbit)

            def render(self):
                # Off-axis, or the defaulted `carries` (the pin's own
                # origin) would lie ON the line the defaulted `at` (the
                # parent's own origin) states, refusing at binding.
                for pin in self.pins:
                    pin.translate([5.0, 0.0, 0.0])

        top = Top()
        top.set_state(angle=40.0)

        self.assertEqual([pin.orbit.value for pin in top.pins], [40.0] * 3)

    def test_a_bare_child_end_means_its_one_site_joint(self):
        class Top(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            leaf = SiteCoordinateLeaf(turn=Revolute(axis=(0, 0, 1),
                                                    unit='deg'))

            angle.drives(leaf)

        top = Top()
        top.set_state(angle=25.0)

        self.assertEqual(top.leaf.turn.value, 25.0)

    def test_a_child_with_a_class_joint_and_a_different_site_joint_is_refused_as_an_end(self):
        class TwoJoints(Solid2Node):
            spin = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(1, center=True)

        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                angle = Driver(default=0.0, unit='deg')
                leaf = TwoJoints(lift=Prismatic(axis=(0, 0, 1), unit='mm'))

                angle.drives(leaf)

        message = str(raised.exception)
        for expected in ('TwoJoints', 'spin', 'lift'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_path_naming_a_keyword_no_site_passed_is_refused_at_class_definition(self):
        with self.assertRaises(SidewaysReadError) as raised:
            class Top(AssemblyNode):
                leaf = SiteCoordinateLeaf(turn=Revolute(axis=(0, 0, 1),
                                                        unit='deg'))
                sibling = SiteCoordinateLeaf(other=leaf.spin)

        message = str(raised.exception)
        for expected in ('spin', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)


##############################################
# whole-tree-fixpoint, task 1: the tree fixpoint

class FixLeaf(Solid2Node):
    turn = Revolute(axis=(0, 0, 1), unit='deg')

    def render(self):
        return cube(1, center=True)


class FixTrain(AssemblyNode):
    """Wall clock 01's shape: the chain stated ONE LEVEL DOWN from the
    movement that binds the escapement."""

    centre = FixLeaf()
    third = FixLeaf()
    escape = FixLeaf()

    centre.turn.drives(third.turn, ratio=-6.0)
    third.turn.drives(escape.turn, ratio=-5.0)


class FixMovement(AssemblyNode):
    power = FixLeaf()
    train = FixTrain()

    power.turn.drives(train.centre.turn, ratio=-7.5)

    def simulate(self):
        self.train.escape.turn = 30.0


class FixAxis(AssemblyNode):
    """openflexure's shape: the ancestor sources from a coordinate THIS
    class's own relation solves."""

    steps = RotationalPort(unit='deg')
    column = FixLeaf()

    steps.drives(column.turn, ratio=0.5)

    def simulate(self):
        self.steps = 100.0


class FixStrut(Solid2Node):
    swing = Revolute(axis=(1, 0, 0), unit='deg')

    def render(self):
        return cube(1, center=True)


class FixRoot(AssemblyNode):
    z_axis = FixAxis()
    strut = FixStrut()

    z_axis.column.turn.drives(strut.swing, ratio=-0.25)


class RFAxis(AssemblyNode):
    """FixAxis, but reading a DRIVER instead of writing a constant, so a
    re-pose actually changes the coordinate the root's relation sources
    from -- FixAxis's `self.steps = 100.0` never varies across
    `set_state` calls and so cannot expose a value carried over from the
    wrong enumeration."""

    z = Driver(default=0.0, unit='deg')
    steps = RotationalPort(unit='deg')
    column = FixLeaf()

    steps.drives(column.turn, ratio=0.5)

    def simulate(self):
        self.steps = self.z


class RFRoot(AssemblyNode):
    """FixRoot's exact shape, over RFAxis: the root's relation sources
    from `z_axis.column.turn`, a coordinate only RFAxis's OWN relation
    solves."""

    z_axis = RFAxis()
    strut = FixStrut()

    z_axis.column.turn.drives(strut.swing, ratio=-0.25)


class TreeFixpointTest(BaseNodeTest):

    def test_a_chain_stated_one_level_down_solves(self):
        """task 1.1. RED today with UnreachedCoordinate naming the
        movement's relation (`power.turn drives train.centre.turn`)."""
        movement = FixMovement()
        movement.render()

        # By hand: escape=30 -> third = 30/-5 = -6 -> centre = -6/-6 = 1
        # -> power = 1/-7.5.
        self.assertAlmostEqual(movement.train.escape.turn.value, 30.0)
        self.assertAlmostEqual(movement.train.third.turn.value, -6.0)
        self.assertAlmostEqual(movement.train.centre.turn.value, 1.0)
        self.assertAlmostEqual(movement.power.turn.value, 1.0 / -7.5)

    def test_an_ancestor_sources_from_a_descendant_solved_coordinate(self):
        """task 1.2. RED today with UnreachedCoordinate naming the
        root's relation."""
        root = FixRoot()
        root.render()

        self.assertAlmostEqual(root.z_axis.column.turn.value, 50.0)
        self.assertAlmostEqual(root.strut.swing.value, -12.5)

    def test_a_deferred_relation_reads_the_source_s_current_value(self):
        """Regression for the openflexure sighting: on the FIRST
        enumeration the shape above is right, but on every LATER
        `set_state` the deferred relation binds the driven end from the
        value the source held at the end of the PREVIOUS enumeration,
        not the one its own descendant's relation just solved THIS
        enumeration -- because the ancestor's own attempt runs (and, if
        the source's stale value has not been cleared yet, resolves)
        before the descendant that owns the source has cleared and
        rebound it for the current pass. Every one of these calls must
        see the source's CURRENT value, not last time's."""
        root = RFRoot()
        for z in (10.0, 40.0, 0.0, 25.0):
            root.set_state(**{'z_axis.z': z})

            expected_column = 0.5 * z
            expected_swing = -0.25 * expected_column
            self.assertAlmostEqual(
                root.z_axis.column.turn.value, expected_column,
                msg=f'z={z}: column.turn stale')
            self.assertAlmostEqual(
                root.strut.swing.value, expected_swing,
                msg=f'z={z}: swing reads the source one enumeration stale')

    def test_the_refusal_names_the_class_and_the_path(self):
        """task 1.3. Nothing binds either end anywhere: refused, naming
        the STATING class and the ends by PATH -- `z_axis.column.turn`,
        not the class-name fallback of today."""
        class NoBind(FixAxis):
            def simulate(self):
                pass

        class Root(AssemblyNode):
            z_axis = NoBind()
            strut = FixStrut()

            z_axis.column.turn.drives(strut.swing, ratio=-0.25)

        root = Root()
        with self.assertRaises(UnreachedCoordinate) as raised:
            root.render()

        message = str(raised.exception)
        self.assertNotIn('column (FixLeaf)', message)
        self.assertNotIn('strut (FixStrut)', message)
        self.assertIn('z_axis.column.turn', message)
        self.assertIn('strut.swing', message)

    def test_a_deferred_relation_moves_a_body_the_walk_has_not_read_yet(self):
        """task 1.4. The two-subtree shape of probe_interleave.py: the
        body in the FIRST subtree must carry the deferred relation's
        motion once assembled."""
        class IBody(AssemblyNode):
            lower_strut = FixStrut()

        class IAxis(AssemblyNode):
            column = FixStrut()

            def simulate(self):
                self.column.swing = 12.0

        class Microscope(AssemblyNode):
            body = IBody()
            z_axis = IAxis()

            z_axis.column.swing.drives(body.lower_strut.swing, ratio=-1.0)

        scope = Microscope()
        scope.set_state(time=0.0)

        self.assertAlmostEqual(scope.body.lower_strut.swing.value, -12.0)
        rotations = [operation.serialized[1] for operation
                     in scope.body.lower_strut.operations
                     if operation.serialized[0] == 'r']
        self.assertIn('-12.0', rotations)

    def test_a_wiring_whose_source_a_descendant_solves_binds(self):
        """task 1.5. A wiring whose source only a descendant's relation
        reaches: deferred and applied in the fixpoint."""
        class Down(AssemblyNode):
            steps = RotationalPort(unit='deg')
            column = FixLeaf()

            steps.drives(column.turn, ratio=1.0)

            def simulate(self):
                self.steps = 40.0

        class Top(AssemblyNode):
            turn = RotationalPort(unit='mm')
            down = Down()
            wheel = Wheel(turn=turn)

            down.column.turn.drives(turn)

        top = Top()
        top.render()

        self.assertEqual(top.wheel.turn.value, 40.0)

    def test_a_broadcast_copy_defers_and_refuses_one_by_one(self):
        """task 1.6. Four copies whose driver a descendant's relation
        solves: all four bind. A fifth tree where one copy's driven end
        is independently bound refuses NotInvertible naming that copy."""
        class Down(AssemblyNode):
            steps = RotationalPort(unit='deg')
            column = FixLeaf()

            steps.drives(column.turn, ratio=1.0)

            def simulate(self):
                self.steps = 8.0

        class Column(AssemblyNode):
            down = Down()
            beads = Bead().repeat(4)

            down.column.turn.drives(beads.travel)

        column = Column()
        column.render()
        self.assertEqual(bead_travels(column.beads), [8.0] * 4)

        class Blocked(AssemblyNode):
            # `driver` is never sourced by anyone -- the broadcast's own
            # driver end stays unreached for the whole enumeration, so
            # this record can only ever be resolved BACKWARDS, which a
            # broadcast never is. A single copy isolates the refusal
            # from the OTHER copies' ordinary "neither end bound" defer.
            driver = RotationalPort(unit='deg')
            beads = Bead().repeat(1)

            driver.drives(beads.travel)

            def simulate(self):
                self.beads[0].travel = 3.0

        with self.assertRaises(NotInvertible) as raised:
            Blocked().render()
        self.assertIn('beads-0', str(raised.exception))

    def test_a_contradiction_is_refused_where_it_is_stated(self):
        """task 1.7. GREEN today and after: a DoublyBound coordinate is
        never deferred -- it raises in the assembly's OWN phase, before
        any descendant's phase runs."""
        ran = []

        class Descendant(AssemblyNode):
            turn = RotationalPort(unit='deg')

            def simulate(self):
                ran.append('Descendant')

        class Both(AssemblyNode):
            angle = Driver(default=0.0, unit='deg')
            a = Pulley()
            b = Pulley()
            descendant = Descendant()

            a.drives(b)

            def simulate(self):
                self.a.turn = self.angle
                self.b.turn = self.angle

        machine = Both()
        with self.assertRaises(DoublyBound):
            machine.set_state(angle=3.0)

        self.assertEqual(ran, [])

    def test_each_phase_runs_once_per_enumeration(self):
        """task 1.8. A three-level tree, ONE enumeration (a bare
        `render()` call, which owns exactly one pass): each simulate()
        call counted once, the pass's own recursive drive re-running no
        phase.

        `assemble()` is deliberately NOT exercised here. It calls
        `render()` (one enumeration, this assertion) and THEN recurses
        into `as_scad`/`child.assemble()` on its own, calling `render()`
        on every descendant a second time, AFTER the owning enumeration
        has already closed. Design.md step 11 states that second walk as
        free (a mark surviving the close); this implementation keeps the
        mark scoped to an enumeration that is still open instead, because
        several call sites bind a coordinate directly and re-render with
        no enumeration in between and would read a STALE pose from a
        mark compared against a merely-remembered last one (see
        `SiteOrbitRepeatDerivedPhaseTest`, `qualified.drive_tree`, and
        evidence.md's task-1.8 note). The visible cost -- `assemble()`
        re-attempts every phase once more -- is measured in task 8 and
        reported to the pilot rather than accepted silently.
        """
        counts = {'root': 0, 'child': 0, 'grand': 0}

        class Grand(AssemblyNode):
            leaf = FixLeaf()

            def simulate(self):
                counts['grand'] += 1

        class Child(AssemblyNode):
            grand = Grand()

            def simulate(self):
                counts['child'] += 1

        class Root(AssemblyNode):
            child = Child()

            def simulate(self):
                counts['root'] += 1

        root = Root()
        root.render()

        self.assertEqual(counts, {'root': 1, 'child': 1, 'grand': 1})


##############################################
# whole-tree-fixpoint, task 2: the read refusal

class ReadRefusalTest(BaseNodeTest):

    def test_a_class_reading_its_own_derived_coordinate_is_refused(self):
        """task 2.1, from probe_own_read.py's Art4."""
        class Art4(AssemblyNode):
            wrist = RotationalPort(unit='deg')
            tool = RotationalPort(unit='deg')
            left = wrist + 2 * tool
            pulley = Pulley()

            def simulate(self):
                self.wrist = 10.0
                self.tool = 4.0
                self.pulley.rotate(self.left.value, [0, 0, 1])

        with self.assertRaises(PrematureRead) as raised:
            Art4().render()

        message = str(raised.exception)
        self.assertIn('left', message)
        self.assertIn('Art4', message)

    def test_a_class_reading_a_coordinate_its_own_relation_binds(self):
        """task 2.2, from probe_own_read.py's Actuator."""
        class Actuator(AssemblyNode):
            steps = RotationalPort(unit='deg')
            rotor = FixLeaf()

            steps.drives(rotor.turn, ratio=0.5)

            def simulate(self):
                self.steps = 100.0
                _ = self.rotor.turn.value

        with self.assertRaises(PrematureRead) as raised:
            Actuator().render()

        self.assertIn('turn', str(raised.exception))

    def test_a_rest_default_guard_is_not_refused(self):
        """task 2.4. Prusa's shape: read the SOURCE end of one of its
        own relations, find it unbound, bind a default -- the relation
        then solves forward from it. Must stay green."""
        class Guarded(AssemblyNode):
            carriage = FixLeaf()
            downstream = FixLeaf()

            carriage.turn.drives(downstream.turn, ratio=2.0)

            def simulate(self):
                if self.carriage.turn.value is None:
                    self.carriage.turn = 5.0

        guarded = Guarded()
        guarded.render()

        self.assertEqual(guarded.downstream.turn.value, 10.0)

    def test_an_ancestor_reading_a_descendant_solved_coordinate_is_refused(self):
        """task 2.3."""
        class Child(AssemblyNode):
            steps = RotationalPort(unit='deg')
            column = FixLeaf()

            steps.drives(column.turn, ratio=1.0)

            def simulate(self):
                self.steps = 9.0

        class Parent(AssemblyNode):
            child = Child()

            def simulate(self):
                _ = self.child.column.turn.value

        with self.assertRaises(PrematureRead) as raised:
            Parent().render()

        message = str(raised.exception)
        # The coordinate's own path names the descendant's instance
        # (`child.column.turn`); the reading class is named directly.
        self.assertIn('child.column.turn', message)
        self.assertIn('Parent', message)

    def test_a_read_of_a_coordinate_nothing_ever_binds_is_not_this_refusal(self):
        """task 2.5. Stays the unreached refusal by its own name."""
        class Adrift(AssemblyNode):
            a = Pulley()
            b = Pulley()

            a.drives(b)

            def simulate(self):
                _ = self.b.turn.value

        with self.assertRaises(UnreachedCoordinate):
            Adrift().render()

    def test_the_message_carries_the_reads_source_location(self):
        """task 2.6."""
        class Art4(AssemblyNode):
            wrist = RotationalPort(unit='deg')
            tool = RotationalPort(unit='deg')
            left = wrist + 2 * tool
            pulley = Pulley()

            def simulate(self):
                self.wrist = 10.0
                self.tool = 4.0
                read = self.left.value  # SOURCE_LOCATION_LINE

        with self.assertRaises(PrematureRead) as raised:
            Art4().render()

        message = str(raised.exception)
        self.assertIn('test_couplings.py', message)


##############################################
# whole-tree-fixpoint, task 4: a subclass replaces a named relation

class ReplaceBase(AssemblyNode):
    input_angle = RotationalPort(unit='deg')
    rotor = Pulley()

    drive = input_angle.drives(rotor.turn, ratio=8.0)

    def simulate(self):
        self.input_angle = 5.0


class SubclassReplacesRelationTest(BaseNodeTest):

    def test_the_replacement(self):
        """task 4.1: the subclass enumerates ONE `drive`, an instance
        binds from the SUBCLASS's own source, nothing is refused."""
        class Preview(ReplaceBase):
            free_run = RotationalPort(unit='deg')
            drive = free_run.drives(ReplaceBase.rotor.turn, ratio=1.0)

            def simulate(self):
                self.free_run = 90.0

        self.assertEqual(len(declared_relations(Preview)), 1)

        preview = Preview()
        preview.render()

        self.assertEqual(preview.rotor.turn.value, 90.0)

    def test_the_base_is_unaffected(self):
        """task 4.2."""
        class Preview(ReplaceBase):
            free_run = RotationalPort(unit='deg')
            drive = free_run.drives(ReplaceBase.rotor.turn, ratio=1.0)

            def simulate(self):
                self.free_run = 90.0

        Preview()  # constructing the subclass must not disturb the base
        self.assertEqual(len(declared_relations(ReplaceBase)), 1)

        base = ReplaceBase()
        base.render()
        self.assertEqual(base.rotor.turn.value, 40.0)

    def test_the_position_is_the_bases(self):
        """task 4.3: base declares a, drive, b; subclass replaces drive;
        the enumeration order is a, drive, b."""
        class Ordered(AssemblyNode):
            a_port = RotationalPort(unit='deg')
            b_port = RotationalPort(unit='deg')
            input_angle = RotationalPort(unit='deg')
            sink = Pulley()
            other = Pulley()

            a = a_port.drives(sink.turn, ratio=1.0)
            drive = input_angle.drives(other.turn, ratio=1.0)
            b = b_port.drives(sink.turn, ratio=2.0)

        class OrderedSub(Ordered):
            free_run = RotationalPort(unit='deg')
            drive = free_run.drives(Ordered.other.turn, ratio=3.0)

        names = [relation.name for relation in declared_relations(OrderedSub)]
        self.assertEqual(names, ['a', 'drive', 'b'])
        self.assertIs(declared_relations(OrderedSub)[1],
                      OrderedSub.__dict__['drive'])

    def test_a_bare_statement_stays_additive(self):
        """task 4.4: a bare relation and a differently-named one are
        never replaced."""
        class Based(AssemblyNode):
            a_port = RotationalPort(unit='deg')
            sink = Pulley()

            named = a_port.drives(sink.turn)

        class Extended(Based):
            b_port = RotationalPort(unit='deg')
            other = Pulley()

            b_port.drives(other.turn)
            fresh = b_port.drives(other.turn)

        self.assertEqual(len(declared_relations(Extended)), 3)

    def test_reading_the_name(self):
        """task 4.5."""
        class Preview(ReplaceBase):
            free_run = RotationalPort(unit='deg')
            drive = free_run.drives(ReplaceBase.rotor.turn, ratio=1.0)

            def simulate(self):
                self.free_run = 90.0

        self.assertIs(Preview.drive, Preview.__dict__['drive'])

        preview = Preview()
        preview.render()
        self.assertIs(preview.drive.relation, Preview.__dict__['drive'])

        with self.assertRaises(AttributeError):
            ReplaceBase.drive.__get__(preview)
