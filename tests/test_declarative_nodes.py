# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Declared parameters, declared children, realization and identity.

A class body declares structure, parameters and ports; the framework
derives everything else. A call in a class body is a declaration, and
each parent instance realizes its own children when it is constructed,
top-down from the root's bound values. Identity is the class plus the
resolved declared values, so the forgotten-kwarg collision cannot
happen.

Leaves are Solid2Node cubes so nothing here needs a CAD kernel; where
a build is the evidence, OpenSCAD renders it.
"""

import os
import sys

from solid2 import cube

from solid_node.motion.joints import (Free, Orbit, Prismatic, Revolute,
                                      declared_joints)
from solid_node.motion.ports import RotationalPort, declared_ports
from solid_node.node import AssemblyNode, Solid2Node, declared_children
from solid_node.node.base import _build_uniq_id
from solid_node.node.declarative import ChildDeclaration, declared_child_nodes
from solid_node.parameters import (Count, Flag, Length, ParameterError, Ratio,
                                   Scalar, declared_parameters)

from .base import BaseNodeTest
from .declarative_project.engine import CylinderUnit, Cylinders, Engine
from .declarative_project.parts import Guard, LegacyPiston, Piston, Tower
from .declarative_project.windmill import Windmill


class Box(Solid2Node):

    size = Length(1.0, min=0)

    def render(self):
        return cube(self.size, center=True)


class Supply(Solid2Node):

    fitted = Flag(False)

    def render(self):
        return cube(1)


TABLE = (1, 2)


class ParameterDeclarationTest(BaseNodeTest):

    def test_defaults_realize_and_read_as_plain_values(self):
        piston = Piston()

        self.assertEqual(piston.diameter, 29.4)
        self.assertIsInstance(piston.diameter, float)
        self.assertEqual(piston.total_height, 30.0)

    def test_a_value_reads_as_a_plain_float_inside_render(self):
        seen = {}

        class Probe(Solid2Node):
            bore = Length(30.0, min=0)

            def render(self):
                seen['bore'] = self.bore
                return cube(self.bore)

        Probe().assemble()

        self.assertEqual(seen['bore'], 30.0)
        self.assertIs(type(seen['bore']), float)

    def test_the_class_reads_the_token(self):
        self.assertIsInstance(Piston.diameter, Length)
        self.assertEqual(Piston.diameter.dimension, {'L': 1})
        self.assertEqual(Piston.total_height.dimension, {'L': 1})

    def test_coercion_by_kind(self):
        class Kinds(AssemblyNode):
            length = Length(1.0)
            count = Count(2)
            ratio = Ratio(0.5)
            flag = Flag(True)
            loose = Scalar(3)

        node = Kinds(length=2, count=3, ratio=1, flag=False, loose=4)

        self.assertIs(type(node.length), float)
        self.assertIs(type(node.count), int)
        self.assertIs(type(node.ratio), float)
        self.assertIs(type(node.flag), bool)
        self.assertIs(type(node.loose), float)
        self.assertEqual((node.length, node.count, node.ratio, node.flag,
                          node.loose), (2.0, 3, 1.0, False, 4.0))

    def test_a_constraint_is_checked_at_instantiation(self):
        with self.assertRaises(ParameterError) as ctx:
            Cylinders(count=1)
        message = str(ctx.exception)
        self.assertIn('Cylinders', message)
        self.assertIn('count', message)
        self.assertIn('2', message)

        with self.assertRaises(ParameterError):
            Cylinders(count=2.5)
        with self.assertRaises(ParameterError):
            Windmill(guard_installed=1)
        with self.assertRaises(ParameterError):
            Windmill(rotor_fraction=1.5)
        with self.assertRaises(ParameterError):
            Piston(diameter=-1.0)

    def test_a_parameter_without_a_default_must_be_supplied(self):
        # The class itself defined without error (see the import above):
        # the error belongs to instantiation.
        with self.assertRaises(ParameterError) as ctx:
            Tower()
        self.assertIn('Tower', str(ctx.exception))
        self.assertIn('height', str(ctx.exception))

        self.assertEqual(Tower(height=300.0).height, 300.0)

    def test_a_parent_supplies_a_child_parameter_without_a_default(self):
        windmill = Windmill()

        self.assertEqual(windmill.tower.height, 400.0)
        self.assertAlmostEqual(windmill.rotor.radius, 144.0)

    def test_assignment_is_refused(self):
        piston = Piston()

        with self.assertRaises(AttributeError):
            piston.diameter = 5
        with self.assertRaises(AttributeError):
            piston.total_height = 5
        self.assertEqual(piston.diameter, 29.4)

    def test_a_declaration_cannot_shadow_a_base_attribute(self):
        for attribute, kind in (('name', Length), ('time', Length),
                                ('mesh', Ratio), ('children', Count),
                                ('color', Scalar), ('rigid', Flag)):
            with self.assertRaises(TypeError) as ctx:
                type('Bad', (AssemblyNode,), {attribute: kind(1)})
            self.assertIn(attribute, str(ctx.exception))

    def test_a_declaration_cannot_be_assigned_under_two_names(self):
        with self.assertRaises(TypeError) as ctx:
            class Aliased(AssemblyNode):
                bore = Length(30.0)
                diameter = bore
        self.assertIn('bore', str(ctx.exception))
        self.assertIn('diameter', str(ctx.exception))

    def test_an_inherited_parameter_may_be_redeclared(self):
        class Wide(Piston):
            diameter = Length(40.0, min=0)

        self.assertEqual(Wide().diameter, 40.0)
        self.assertEqual(declared_parameters(Wide)['diameter'].default,
                         40.0)

    def test_declared_parameters_are_enumerable(self):
        declared = declared_parameters(Piston)

        self.assertEqual(
            list(declared),
            ['diameter', 'crown_height', 'skirt_depth', 'slot_width',
             'slot_top', 'pin_bore', 'total_height'])
        self.assertIsInstance(declared['diameter'], Length)
        self.assertEqual(declared['diameter'].default, 29.4)
        self.assertEqual(declared['diameter'].min, 0)
        self.assertFalse(declared['diameter'].derived)
        self.assertTrue(declared['total_height'].derived)
        self.assertEqual(declared['total_height'].dimension, {'L': 1})
        self.assertEqual(declared_parameters(Guard), {})


class DeclarativeSheetPartTest(BaseNodeTest):
    """A sheet part's `thickness` is a class attribute of the sheet
    base, so it cannot be declared as a parameter -- the shadow guard
    refuses it -- and stays what it is: a per-class constant or a
    constructor argument. Everything else about the part can declare."""

    def test_thickness_stays_a_class_attribute(self):
        from solid_node.node import Build123dSheetNode

        with self.assertRaises(TypeError) as ctx:
            class Bad(Build123dSheetNode):
                thickness = Length(3.0)
        self.assertIn('thickness', str(ctx.exception))

    def test_a_sheet_part_declares_its_other_parameters(self):
        from build123d import Rectangle
        from solid_node.node import Build123dSheetNode

        class Panel(Build123dSheetNode):
            thickness = 3.0
            width = Length(40.0, min=0)

            def profile(self):
                return Rectangle(self.width, self.width)

        narrow, wide = Panel(), Panel(width=60.0)

        self.assertEqual(wide.thickness, 3.0)
        self.assertEqual(wide.width, 60.0)
        self.assertNotEqual(narrow.uniq_id, wide.uniq_id)
        wide.assemble()
        self.assertTrue(wide.exact)


class DerivedParameterTest(BaseNodeTest):

    def test_a_derived_value_follows_its_inputs(self):
        self.assertAlmostEqual(CylinderUnit().piston_diameter, 29.4)
        self.assertAlmostEqual(CylinderUnit(bore=32.0).piston_diameter, 31.4)

    def test_a_derived_parameter_cannot_be_supplied(self):
        with self.assertRaises(TypeError) as ctx:
            CylinderUnit(piston_diameter=20.0)
        self.assertIn('piston_diameter', str(ctx.exception))
        self.assertIn('derived', str(ctx.exception))


class ChildDeclarationTest(BaseNodeTest):

    def test_a_class_body_call_is_a_declaration(self):
        self.assertIsInstance(CylinderUnit.piston, ChildDeclaration)
        self.assertIs(CylinderUnit.piston.node_class, Piston)
        self.assertNotIsInstance(CylinderUnit.piston, Piston)

    def test_each_parent_realizes_its_own_child(self):
        one, other = CylinderUnit(), CylinderUnit()

        one.piston.translate([0, 0, 5])

        self.assertIsNot(one.piston, other.piston)
        self.assertEqual(other.piston.operations, [])
        self.assertIsInstance(one.piston, Piston)

    def test_tokens_flow_to_children_by_reference(self):
        self.assertAlmostEqual(CylinderUnit().piston.diameter, 29.4)
        self.assertAlmostEqual(CylinderUnit(bore=32.0).piston.diameter, 31.4)
        self.assertAlmostEqual(
            CylinderUnit(wall_clearance=0.5).piston.diameter, 29.0)

    def test_plain_values_and_names_pass_through(self):
        class Pair(AssemblyNode):
            left = Box(size=2.0, name='port_box')
            right = Box(size=3.0)

        pair = Pair()
        pair.render()

        self.assertEqual(pair.left.size, 2.0)
        self.assertEqual(pair.left.name, 'port_box')
        self.assertEqual(pair.right.name, 'right')

    def test_identical_units_repeat(self):
        cylinders = Cylinders(count=6)

        self.assertEqual(len(cylinders.units), 6)
        self.assertEqual(len({id(unit) for unit in cylinders.units}), 6)
        cylinders.render()
        self.assertEqual([unit.name for unit in cylinders.units],
                         [f'units-{index}' for index in range(6)])
        self.assertEqual({unit.bore for unit in cylinders.units}, {30.0})
        self.assertEqual({unit.uniq_id for unit in cylinders.units}.__len__(),
                         1)

    def test_repeat_takes_a_plain_integer_too(self):
        class Four(AssemblyNode):
            boxes = Box().repeat(4)

        self.assertEqual(len(Four().boxes), 4)

    def test_a_repeat_count_must_be_a_non_negative_integer(self):
        with self.assertRaises(ParameterError):
            Cylinders(count=-2)

    def test_a_literal_list_declares_enumerated_children(self):
        class Plates(AssemblyNode):
            width = Length(10.0)
            plates = [Box(size=width), Box(size=width / 2)]

        plates = Plates(width=8.0)
        plates.render()

        self.assertEqual([plate.size for plate in plates.plates], [8.0, 4.0])
        self.assertEqual([plate.name for plate in plates.plates],
                         ['plates-0', 'plates-1'])

    def test_a_legacy_class_is_a_valid_child(self):
        class Guarded(AssemblyNode):
            wall = Length(2.4, min=0)
            guard = Guard(thickness=wall)

        guarded = Guarded(wall=3.2)
        guarded.render()

        self.assertIsInstance(guarded.guard, Guard)
        self.assertEqual(guarded.guard.thickness, 3.2)
        self.assertEqual(guarded.guard.name, 'guard')

    def test_a_sideways_read_is_refused(self):
        with self.assertRaises(AttributeError) as ctx:
            class Unit(AssemblyNode):
                piston = Piston()
                rod = Box(size=piston.pin_bore)
        message = str(ctx.exception)
        self.assertIn('Piston', message)
        self.assertIn('pin_bore', message)
        self.assertIn('declare', message)

    def test_declared_children_are_enumerable(self):
        children = declared_children(Engine)

        self.assertEqual(list(children), ['cylinders', 'block'])
        self.assertIs(children['cylinders'].node_class, Cylinders)
        self.assertIn('units', declared_children(Cylinders))
        self.assertEqual(declared_children(Guard), {})

    def test_a_hybrid_init_sees_its_children_after_super(self):
        class Hybrid(AssemblyNode):
            size = Length(2.0)
            box = Box(size=size)

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.extra = self.box.size * 2

        self.assertEqual(Hybrid(size=3.0).extra, 6.0)

    def test_a_comprehension_over_module_values_declares(self):
        class Rack(AssemblyNode):
            boxes = [Box() for _ in TABLE]

        declared = declared_children(Rack)
        self.assertEqual(list(declared), ['boxes'])
        self.assertEqual(len(declared['boxes']), 2)
        self.assertTrue(all(isinstance(item, ChildDeclaration)
                            for item in declared['boxes']))
        first, second = Rack(), Rack()
        self.assertEqual([box.name for box in first.boxes],
                         ['boxes-0', 'boxes-1'])
        self.assertIsNot(first.boxes[0], second.boxes[0])
        self.assertEqual([child.name for child in first.render()],
                         ['boxes-0', 'boxes-1'])

    def test_a_comprehension_cannot_see_class_level_names(self):
        with self.assertRaises(NameError):
            class Rack(AssemblyNode):
                size = Length(2.0)
                boxes = [Box(size=size) for _ in TABLE]

    def test_a_flag_flows_to_a_child(self):
        class Cabinet(AssemblyNode):
            fitted = Flag(False)
            supply = Supply(fitted=fitted)

        self.assertIs(Cabinet().supply.fitted, False)
        self.assertIs(Cabinet(fitted=True).supply.fitted, True)

    def test_an_inline_flag_is_a_constant(self):
        class Cabinet(AssemblyNode):
            supply = Supply(fitted=Flag(True))

        self.assertIs(Cabinet().supply.fitted, True)

    def test_a_flag_declared_elsewhere_is_refused(self):
        class Other(AssemblyNode):
            fitted = Flag(True)

        class Cabinet(AssemblyNode):
            supply = Supply(fitted=Other.fitted)

        with self.assertRaisesRegex(ParameterError,
                                    "'fitted' is not declared"):
            Cabinet()


##############################################
# 1.2 (cycle: repeat-fan-out) The copy's index

class Bead(Solid2Node):
    """A rigid leaf: one joint, no `index` of its own."""

    travel = Prismatic(axis=(0, 0, 1), unit='mm')

    def render(self):
        return cube(1, center=True)


class RepeatColumn(AssemblyNode):
    beads = Bead().repeat(4)


class Ranked(Solid2Node):
    """A class that already answers to 'index' on its own."""

    index = Count(0, min=0)

    def render(self):
        return cube(1, center=True)


class Half(Solid2Node):
    """The abacus's own shape: a repeated class declaring `count`, not
    `index`, of its own (Vibecoded-demos/abacus/abacus/frame_half.py)."""

    count = Count(9, min=1)

    def render(self):
        return cube(1, center=True)


class Halves(AssemblyNode):
    """The abacus's own shape, one level up: a parent's own `count`
    passed by reference into a repeated child that declares a `count`
    of its own (Vibecoded-demos/abacus/abacus/frame.py:35-43)."""

    count = Count(2, min=1)
    halves = Half(count=count).repeat(2)


class RepeatIndexTest(BaseNodeTest):

    def test_a_copy_reads_its_position(self):
        column = RepeatColumn()

        self.assertEqual([bead.index for bead in column.beads],
                         [0, 1, 2, 3])

    def test_the_position_is_not_identity(self):
        column = RepeatColumn()
        plain = Bead()

        ids = {bead.uniq_id for bead in column.beads}
        self.assertEqual(ids, {plain.uniq_id})
        for bead in column.beads:
            with self.subTest(bead=bead):
                self.assertNotIn('index',
                                 bead.__dict__.get('_parameters', {}))

    def test_a_zero_repeat_still_carries_nothing(self):
        class Empty(AssemblyNode):
            beads = Bead().repeat(0)

        self.assertEqual(Empty().beads, [])

    def test_a_repeat_of_a_class_that_declares_index_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Parent(AssemblyNode):
                arbors = Ranked().repeat(4)

        message = str(raised.exception)
        for expected in ('Parent', 'arbors', 'Ranked'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_parent_declaring_index_is_not_refused(self):
        """InMoov's real shape: the PARENT declares `index`, the
        REPEATED class does not, so the check -- against the repeated
        class only -- lets it through."""
        class Hand(AssemblyNode):
            index = Count(0, min=0)
            fingers = Bead().repeat(4)

        hand = Hand()

        self.assertEqual(len(hand.fingers), 4)
        self.assertEqual(hand.index, 0)
        self.assertEqual([finger.index for finger in hand.fingers],
                         [0, 1, 2, 3])

    def test_halves_still_realizes(self):
        """The abacus's real shape is NOT refused: `Half` declares
        `count`, not `index`. If this goes red, the decision to stamp
        `index` and not `count` is wrong."""
        halves = Halves()

        self.assertEqual([half.count for half in halves.halves], [2, 2])
        self.assertEqual([half.index for half in halves.halves], [0, 1])

    def test_a_copys_index_does_not_become_a_child_name(self):
        column = RepeatColumn()

        self.assertEqual([bead.name for bead in column.beads],
                         [f'beads-{index}' for index in range(4)])
        self.assertEqual(len(declared_child_nodes(column)), 4)
        for bead in column.beads:
            with self.subTest(bead=bead.name):
                self.assertNotEqual(bead.name, 'index')


class InstanceCheckTest(BaseNodeTest):

    def test_a_cross_parameter_guard_refuses_an_instance(self):
        class Valve(Solid2Node):
            stem = Length(4.0, min=0)
            stop = Length(6.0, min=0)

            def check(self):
                if self.stop <= self.stem:
                    raise ValueError(
                        f'{self.name}: stop {self.stop} must exceed '
                        f'stem {self.stem}')

            def render(self):
                return cube(self.stem)

        Valve()
        with self.assertRaisesRegex(ValueError,
                                    'Valve: stop 3.0 must exceed stem 4.0'):
            Valve(stop=3.0)

    def test_a_refused_parent_realizes_nothing(self):
        built = []

        class Probe(Solid2Node):
            def __init__(self, **kwargs):
                built.append(self)
                super().__init__(**kwargs)

            def render(self):
                return cube(1)

        class Bad(AssemblyNode):
            size = Length(1.0)
            probe = Probe()

            def check(self):
                raise ValueError('never')

        with self.assertRaisesRegex(ValueError, 'never'):
            Bad()
        self.assertEqual(built, [])

    def test_checks_chain(self):
        class Base(Solid2Node):
            size = Length(1.0, min=0)

            def check(self):
                if self.size > 10:
                    raise ValueError('too big')

            def render(self):
                return cube(self.size)

        class Derived(Base):
            def check(self):
                super().check()

        Derived(size=5.0)
        with self.assertRaisesRegex(ValueError, 'too big'):
            Derived(size=11.0)

    def test_a_class_that_declares_nothing_is_not_checked(self):
        calls = []

        class Legacy(Solid2Node):
            def __init__(self, size=1.0, name=None):
                self.size = size
                super().__init__(size=size, name=name)

            def check(self):
                calls.append(self.size)

            def render(self):
                return cube(self.size)

        Legacy()
        self.assertEqual(calls, [])


class RealizationTest(BaseNodeTest):

    def test_one_number_moves_the_machine(self):
        default, wide = Engine(), Engine(bore=32.0)

        self.assertEqual({unit.bore for unit in wide.cylinders.units},
                         {32.0})
        self.assertEqual(wide.block.bore, 32.0)
        self.assertAlmostEqual(wide.cylinders.units[0].piston.diameter, 31.4)
        self.assertNotEqual(default.block.uniq_id, wide.block.uniq_id)
        self.assertNotEqual(default.cylinders.units[0].piston.uniq_id,
                            wide.cylinders.units[0].piston.uniq_id)

    def test_a_count_moves_the_structure(self):
        six = Engine(count=6)

        self.assertEqual(len(six.cylinders.units), 6)
        self.assertEqual(six.block.count, 6)
        self.assertAlmostEqual(six.block.length, 132.0)

    def test_positional_arguments_are_rejected(self):
        with self.assertRaises(TypeError) as ctx:
            Piston(31.0)
        self.assertIn('Piston', str(ctx.exception))

    def test_unknown_keywords_are_rejected_listing_the_declared(self):
        with self.assertRaises(TypeError) as ctx:
            Piston(diamter=31.0)
        message = str(ctx.exception)
        self.assertIn('diamter', message)
        self.assertIn('diameter', message)
        self.assertIn('pin_bore', message)

    def test_legacy_classes_keep_their_constructor(self):
        self.assertEqual(LegacyPiston(31.0).diameter, 31.0)
        self.assertEqual(Guard(2.0).thickness, 2.0)

    def test_by_render_time_every_parameter_is_a_plain_value(self):
        engine = Engine(bore=32.0)
        engine.render()

        for unit in engine.cylinders.units:
            self.assertIs(type(unit.piston.diameter), float)
        self.assertIs(type(engine.block.length), float)


class IdentityTest(BaseNodeTest):

    def test_identity_is_complete_by_construction(self):
        base = Piston()
        changed = Piston(slot_top=8.0)
        same = Piston()

        self.assertNotEqual(base.uniq_id, changed.uniq_id)
        self.assertEqual(base.uniq_id, same.uniq_id)
        self.assertEqual(base.stl_file, same.stl_file)

    def test_a_migrated_class_keeps_its_key(self):
        legacy = LegacyPiston()
        declared = Piston()

        forwarded = {
            'diameter': 29.4, 'crown_height': 18.0, 'skirt_depth': 12.0,
            'slot_width': 10.6, 'slot_top': 7.0, 'pin_bore': 6.6}
        # Both go through the one identity function with the same map;
        # the declarative class just never had to write it out.
        self.assertEqual(declared.uniq_id,
                         _build_uniq_id(Piston, (), forwarded))
        self.assertEqual(legacy.uniq_id,
                         _build_uniq_id(LegacyPiston, (), forwarded))

    def test_coercion_keeps_one_artifact_per_geometry(self):
        self.assertEqual(Piston(diameter=30).uniq_id,
                         Piston(diameter=30.0).uniq_id)

    def test_name_stays_out_of_identity(self):
        self.assertEqual(Piston(name='left').uniq_id, Piston().uniq_id)

    def test_a_derived_value_is_not_in_the_key(self):
        self.assertNotIn('total_height', Piston().uniq_id)

    def test_repeated_units_are_one_part(self):
        cylinders = Cylinders()
        cylinders.assemble()

        pistons = [unit.piston for unit in cylinders.units]
        self.assertEqual(len({piston.uniq_id for piston in pistons}), 1)
        self.assertEqual(len({piston.scad_file for piston in pistons}), 1)
        self.assertEqual(len({unit.uniq_id for unit in cylinders.units}), 1)
        # Each unit still carries its own placement.
        placements = [[op.serialized for op in unit.operations]
                      for unit in cylinders.units]
        self.assertEqual(len({str(p) for p in placements}), 8)

    def test_the_root_is_loadable_with_defaults(self):
        from solid_node.core.loader import load_node
        engine = load_node(os.path.join(
            self.basedir, 'declarative_project', 'engine.py:Engine'))

        self.assertEqual(engine.bore, 30.0)
        self.assertEqual(len(engine.cylinders.units), 8)


##############################################
# A joint declared at a DECLARATION SITE (declaration-site-joint)
#
# A joint passed as a keyword where a parent DECLARES a child declares a
# freedom on that child -- not a wiring (it declares a coordinate rather
# than binding one), not a parameter (it never reaches the child's
# constructor) and not identity (two children differing only in a site
# joint share one artifact).

class NamedWidget(Solid2Node):
    """A NON-declarative leaf: a positional parameter of its own
    `__init__`, exactly what OMX's `VisualPack` and openvmp's `Link`
    are -- the shape a site joint's keyword has to be stripped clean
    of before construction."""

    def __init__(self, size, name=None):
        self.size = size
        super().__init__(size=size, name=name)

    def render(self):
        return cube(self.size, center=True)


class PortedLeaf(Solid2Node):
    turn = RotationalPort(unit='deg')

    def render(self):
        return cube(1, center=True)


class DerivedLeaf(Solid2Node):
    a = Revolute(axis=(0, 0, 1), unit='deg')
    b = Revolute(axis=(0, 0, 1), unit='deg')
    combo = a - b

    def render(self):
        return cube(1, center=True)


class MethodicalLeaf(Solid2Node):
    def turn(self):
        return 'not a coordinate'

    def render(self):
        return cube(1, center=True)


class HouseholdLeaf(Solid2Node):
    guest = Box()

    def render(self):
        return cube(1, center=True)


class SiteJointIdentityTest(BaseNodeTest):

    def test_a_site_joint_is_not_a_parameter_and_not_identity(self):
        class Plain(AssemblyNode):
            widget = NamedWidget(4.0)

        class Jointed(AssemblyNode):
            widget = NamedWidget(4.0, turn=Revolute(axis=(0, 0, 1),
                                                    unit='deg'))

        plain, jointed, other = Plain(), Jointed(), Jointed()

        self.assertEqual(plain.widget.size, 4.0)
        self.assertEqual(jointed.widget.size, 4.0)
        self.assertEqual(plain.widget.uniq_id, jointed.widget.uniq_id)
        self.assertEqual(jointed.widget.uniq_id, other.widget.uniq_id)
        self.assertEqual(jointed.widget.scad_file, other.widget.scad_file)


class SiteJointStillAWiringTest(BaseNodeTest):

    def test_a_wiring_still_means_a_wiring(self):
        class Top(AssemblyNode):
            turn = RotationalPort(unit='deg')
            leaf = PortedLeaf(turn=turn)

        top = Top()
        top.turn = 12
        top.render()
        self.assertEqual(top.leaf.turn.value, 12)

        with self.assertRaises(TypeError) as raised:
            class Bad(AssemblyNode):
                turn = RotationalPort(unit='deg')
                leaf = PortedLeaf(spin=turn)

        self.assertIn('spin', str(raised.exception))


class SiteJointRefusalTest(BaseNodeTest):
    """Design decision 10. The four SHADOWING rows (a port, a derived
    coordinate, a declared parameter, a method or property, a child
    declaration) are refused by `Joint._refuse_shadowing`, run for
    free against the CHILD's own MRO the moment the specialization is
    built (design decision 6) -- its message names the CHILD class and
    the keyword, not the declaring class or the attribute, which is
    the cost decision 6 states explicitly rather than adding a second
    refusal path to say more. The remaining rows -- a non-declarative
    constructor parameter, a joint on a third class, and the two dotted
    coordinate collisions -- are this cycle's own checks and name
    fuller context."""

    def test_a_keyword_naming_a_port_the_child_declares_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = PortedLeaf(turn=Revolute(axis=(0, 0, 1), unit='deg'))

        message = str(raised.exception)
        for expected in ('PortedLeaf', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_keyword_naming_a_derived_coordinate_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = DerivedLeaf(combo=Revolute(axis=(0, 0, 1),
                                                  unit='deg'))

        message = str(raised.exception)
        for expected in ('DerivedLeaf', 'combo'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_keyword_naming_a_declared_parameter_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = Box(size=Revolute(axis=(0, 0, 1), unit='deg'))

        message = str(raised.exception)
        for expected in ('Box', 'size'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_keyword_naming_a_non_declarative_constructor_parameter_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = NamedWidget(4.0, size=Revolute(axis=(0, 0, 1),
                                                      unit='deg'))

        message = str(raised.exception)
        for expected in ('NamedWidget', 'size'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_keyword_naming_a_method_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = MethodicalLeaf(turn=Revolute(axis=(0, 0, 1),
                                                    unit='deg'))

        message = str(raised.exception)
        for expected in ('MethodicalLeaf', 'turn'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_keyword_naming_a_child_declaration_is_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = HouseholdLeaf(guest=Revolute(axis=(0, 0, 1),
                                                    unit='deg'))

        message = str(raised.exception)
        for expected in ('HouseholdLeaf', 'guest'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_joint_declared_on_a_third_class_is_refused(self):
        class Elsewhere(Solid2Node):
            turn = Revolute(axis=(0, 0, 1), unit='deg')

            def render(self):
                return cube(1, center=True)

        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = PortedLeaf(turn=Elsewhere.turn)

        message = str(raised.exception)
        for expected in ('Top', 'leaf', 'PortedLeaf', 'turn', 'Elsewhere'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_two_site_joints_of_one_dotted_name_are_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                leaf = Box(**{
                    'pose': Free(),
                    'pose.roll': Revolute(axis=(0, 0, 1), unit='deg'),
                })

        message = str(raised.exception)
        for expected in ('Box', 'pose.roll'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_site_joint_and_a_wiring_of_one_coordinate_are_refused(self):
        with self.assertRaises(TypeError) as raised:
            class Top(AssemblyNode):
                pose_roll = RotationalPort(unit='deg')
                leaf = Box(**{
                    'pose': Free(),
                    'pose.roll': pose_roll,
                })

        message = str(raised.exception)
        self.assertIn('pose.roll', message)


class SiteJointRepeatAndListTest(BaseNodeTest):

    def test_a_site_joint_on_a_repeat_and_on_a_literal_list(self):
        class Repeated(AssemblyNode):
            beads = Box(turn=Revolute(axis=(0, 0, 1), unit='deg')).repeat(3)

            def render(self):
                for index, bead in enumerate(self.beads):
                    bead.translate([0.0, float(index) * 5.0, 0.0])

        repeated = Repeated()
        repeated.render()
        for bead in repeated.beads:
            bead.turn = 20
        self.assertEqual([bead.turn.value for bead in repeated.beads],
                         [20, 20, 20])
        self.assertEqual(
            len({bead.uniq_id for bead in repeated.beads}), 1)

        class Listed(AssemblyNode):
            width = Length(3.0)
            pair = [Box(size=width, turn=Revolute(axis=(0, 0, 1),
                                                  unit='deg')),
                   Box(size=width / 2)]

        listed = Listed(width=6.0)
        listed.pair[0].turn = 15
        self.assertEqual(listed.pair[0].turn.value, 15)
        self.assertEqual(listed.pair[0].size, 6.0)
        self.assertEqual(listed.pair[1].size, 3.0)


class SiteJointCallableTest(BaseNodeTest):

    def test_a_callable_is_handed_the_declaring_parent(self):
        seen = []

        class LeftRight(AssemblyNode):
            side = Count(1, min=-1, max=1)
            leaf = Box(turn=Revolute(
                axis=lambda parent: (0.0, 0.0, float(parent.side)),
                unit='deg'))

        left = LeftRight(side=-1)
        right = LeftRight(side=1)

        left_axis = declared_joints(type(left.leaf))['turn'].arguments(
            left.leaf)[0]
        right_axis = declared_joints(type(right.leaf))['turn'].arguments(
            right.leaf)[0]
        self.assertEqual(left_axis, (0, 0, -1))
        self.assertEqual(right_axis, (0, 0, 1))

    def test_the_parents_render_has_not_run_when_the_callable_is_called(self):
        rendered = []

        class Probe(AssemblyNode):
            side = Count(1, min=-1, max=1)
            leaf = Box(turn=Revolute(
                axis=lambda parent: rendered.append(
                    getattr(parent, '_rendered', False)) or (0, 0, 1),
                unit='deg'))

            def render(self):
                self._rendered = True

        Probe()

        self.assertEqual(rendered, [False])

    def test_a_later_declared_sibling_is_not_yet_realized(self):
        def reads_later_sibling(parent):
            parent.later
            return (0, 0, 1)

        # A callable's failure is wrapped exactly as any other joint
        # argument's is (`Joint._vector`, unedited): ParameterError,
        # naming the class, the joint, the argument and the underlying
        # AttributeError.
        with self.assertRaises(ParameterError) as raised:
            class Probe(AssemblyNode):
                earlier = Box(turn=Revolute(axis=reads_later_sibling,
                                            unit='deg'))
                later = Box()

            Probe()

        message = str(raised.exception)
        for expected in ('turn', 'axis', 'AttributeError', 'later'):
            with self.subTest(expected=expected):
                self.assertIn(expected, message)

    def test_a_copys_index_is_not_reachable_from_a_site_callable(self):
        """Design decision 5: a `.repeat()` copy's `index` is stamped
        by `RepeatDeclaration.realize` AFTER the copy's construction --
        which is also after a site joint's arguments already resolved,
        against the PARENT, inside `ChildDeclaration.realize`. A site
        callable is handed the declaring parent and only the declaring
        parent; it has no copy to read `index` off at all."""

        def reads_index(parent):
            # The declaring parent has no 'index' of its own here, and
            # even if it did, it would not be the COPY's index -- there
            # is no copy in scope for this callable to name.
            parent.index
            return (0, 0, 1)

        with self.assertRaises(ParameterError) as raised:
            class Probe(AssemblyNode):
                beads = Box(turn=Revolute(axis=reads_index,
                                          unit='deg')).repeat(3)

            Probe()

        self.assertIn('AttributeError', str(raised.exception))


##############################################
# 4.2 declared_ports / declared_joints see a site joint

class SiteJointEnumerationTest(BaseNodeTest):

    def test_declared_ports_and_declared_joints_report_the_site(self):
        class Leaf(Solid2Node):
            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            leaf = Leaf(turn=Revolute(axis=(0, 0, 1), range=(-10, 10),
                                      unit='deg'))

        top = Top()
        leaf_class = type(top.leaf)

        self.assertIn('turn', declared_joints(leaf_class))
        self.assertEqual(declared_joints(leaf_class)['turn'].range,
                         (-10, 10))
        self.assertIn('turn', declared_ports(leaf_class))
        self.assertEqual(declared_ports(leaf_class)['turn'].domain,
                         'rotational')
        self.assertEqual(declared_ports(leaf_class)['turn'].unit, 'deg')
        # The WRITTEN class still reports only what IT declares.
        self.assertEqual(declared_joints(Leaf), {})
        self.assertEqual(declared_ports(Leaf), {})


##############################################
# 5. The specialization: what it must and must not be

class SpecializationIdentityTest(BaseNodeTest):

    def test_identity_is_unchanged_across_differently_jointed_sites(self):
        class Leaf(Solid2Node):
            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            plain = Leaf()
            one_joint = Leaf(turn=Revolute(axis=(0, 0, 1), unit='deg'))
            other_joint = Leaf(turn=Revolute(axis=(1, 0, 0), unit='deg'))

        top = Top()

        ids = {top.plain.uniq_id, top.one_joint.uniq_id,
               top.other_joint.uniq_id}
        self.assertEqual(len(ids), 1)
        self.assertEqual(
            {top.plain.scad_file, top.one_joint.scad_file,
             top.other_joint.scad_file}.__len__(), 1)
        self.assertEqual(
            {top.plain.stl_file, top.one_joint.stl_file,
             top.other_joint.stl_file}.__len__(), 1)


class SpecializationClassIdentityTest(BaseNodeTest):

    def test_isinstance_holds_and_the_class_reads_as_the_written_one(self):
        import inspect

        class ZScrew(Solid2Node):
            """A screw."""

            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            screw = ZScrew(turn=Revolute(axis=(0, 0, 1), unit='deg'))

        top = Top()

        self.assertIsInstance(top.screw, ZScrew)
        self.assertIsNot(type(top.screw), ZScrew)
        self.assertEqual(type(top.screw).__name__, 'ZScrew')
        self.assertEqual(type(top.screw).__qualname__, ZScrew.__qualname__)
        self.assertEqual(type(top.screw).__module__, ZScrew.__module__)
        self.assertEqual(inspect.getfile(type(top.screw)),
                         inspect.getfile(ZScrew))


class SpecializationSharingTest(BaseNodeTest):

    def test_one_specialization_per_declaration_site(self):
        class Leaf(Solid2Node):
            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            pack = Leaf(turn=Revolute(axis=(0, 0, 1), unit='deg')).repeat(6)

        top = Top()

        self.assertEqual(len({type(child) for child in top.pack}), 1)

        class TopTwo(AssemblyNode):
            leaf = Leaf(turn=Revolute(axis=(0, 0, 1), unit='deg'))

        one, other = Top(), TopTwo()
        # Two different sites declaring the SAME class with the SAME
        # joint text get two DIFFERENT specialized classes -- and still
        # share one artifact key.
        self.assertIsNot(type(one.pack[0]), type(other.leaf))
        self.assertEqual(one.pack[0].uniq_id, other.leaf.uniq_id)


class SpecializationDiscoveryTest(BaseNodeTest):

    def test_the_specialization_is_invisible_to_model_discovery(self):
        from solid_node.core.loader import _defined_classes
        from solid_node.node.base import AbstractBaseNode
        from solid_node.node.sources import node_classes_in

        module = sys.modules[__name__]
        path = module.__file__
        defined = {name for name, _klass
                  in _defined_classes(path, module, AbstractBaseNode)}
        self.assertIn('SpecializationDiscoveryLeaf', defined)
        # No specialized subclass -- of ANY declared joint above --
        # slipped into this module's own discovered set: every one is
        # named after the class it specializes, and none of THOSE
        # written names denote the specialization.
        top = SpecializationDiscoveryTop()
        self.assertIsNot(type(top.leaf), SpecializationDiscoveryLeaf)
        self.assertEqual(type(top.leaf).__name__,
                         'SpecializationDiscoveryLeaf')


class SpecializationDiscoveryLeaf(Solid2Node):
    def render(self):
        return cube(1, center=True)


class SpecializationDiscoveryTop(AssemblyNode):
    leaf = SpecializationDiscoveryLeaf(
        turn=Revolute(axis=(0, 0, 1), unit='deg'))


class SpecializationMetaclassTest(BaseNodeTest):

    def test_a_class_with_its_own_metaclass_specializes_through_it(self):
        from solid_node.node.declarative import NodeMeta

        class OwnMeta(NodeMeta):
            built_through = []

            def __new__(mcs, name, bases, namespace, **kwargs):
                cls = super().__new__(mcs, name, bases, namespace, **kwargs)
                OwnMeta.built_through.append(cls)
                return cls

        class Custom(Solid2Node, metaclass=OwnMeta):
            def render(self):
                return cube(1, center=True)

        OwnMeta.built_through.clear()

        class Top(AssemblyNode):
            leaf = Custom(turn=Revolute(axis=(0, 0, 1), unit='deg'))

        top = Top()

        self.assertIs(type(type(top.leaf)), OwnMeta)
        self.assertIn(type(top.leaf), OwnMeta.built_through)


class SpecializationOwnTypeGuardTest(BaseNodeTest):
    """Task 5.6: the one identity check the change loosens,
    `internal.py:166`'s guard against a render returning its own type,
    PINNED directly against `validate()` for the ordinary case it still
    catches -- unrelated to any site joint."""

    def test_the_ordinary_own_type_guard_still_fires(self):
        from solid_node.node.internal import InternalNode

        class Wrapper(InternalNode):
            def render(self):
                return []

        wrapper = Wrapper()
        with self.assertRaises(Exception) as raised:
            wrapper.validate([Wrapper()])
        self.assertIn('own type', str(raised.exception))


class SpecializationCacheBoundTest(BaseNodeTest):

    def test_class_keyed_caches_stay_bounded_by_declaration_sites(self):
        from solid_node.motion.joints import _declared_cache
        from solid_node.node.declarative import _children_cache
        from solid_node.parameters import _parameters_cache

        class Leaf(Solid2Node):
            def render(self):
                return cube(1, center=True)

        class Top(AssemblyNode):
            pack = Leaf(turn=Revolute(axis=(0, 0, 1), unit='deg')).repeat(5)

        # Pre-warm Top's OWN cache entry: realizing Top ALSO resolves
        # Top's (empty) joints, which is one legitimate entry this test
        # is not about, and must not be mistaken for a specialization
        # per realized child.
        declared_joints(Top)
        declared_children(Top)
        declared_parameters(Top)

        before_declared = len(_declared_cache)
        before_children = len(_children_cache)
        before_parameters = len(_parameters_cache)

        top = Top()
        for child in top.pack:
            declared_joints(type(child))
            declared_children(type(child))
            declared_parameters(type(child))

        # ONE specialized class realized five times: at most one new
        # entry per cache, not one per realized child.
        self.assertLessEqual(len(_declared_cache) - before_declared, 1)
        self.assertLessEqual(len(_children_cache) - before_children, 1)
        self.assertLessEqual(len(_parameters_cache) - before_parameters, 1)
