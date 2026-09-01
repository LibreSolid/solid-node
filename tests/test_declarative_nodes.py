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

from solid2 import cube

from solid_node.node import (AssemblyNode, Count, Flag, Length, Ratio,
                             Scalar, Solid2Node, declared_children,
                             declared_parameters)
from solid_node.node.base import _build_uniq_id
from solid_node.node.declarative import ChildDeclaration, ParameterError

from .base import BaseNodeTest
from .declarative_project.engine import CylinderUnit, Cylinders, Engine
from .declarative_project.parts import Guard, LegacyPiston, Piston, Tower
from .declarative_project.windmill import Windmill


class Box(Solid2Node):

    size = Length(1.0, min=0)

    def render(self):
        return cube(self.size, center=True)


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
