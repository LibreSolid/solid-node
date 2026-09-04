# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The dimension algebra over declared parameters.

A declared quantity is a vector of dimension exponents. Multiplication
adds them, division subtracts them, and addition or comparison needs
them equal -- that rule is what catches `bore + pressure_angle` on
import, before any geometry exists. The functions of `solid_node.math`
take part with rules of their own, because windmill's parameter layer
derives gear dimensions through `atan`, `sqrt` and `cos`.

Everything here is symbolic: tokens and formulas, no node instances.
"""

from unittest import TestCase

from solid_node.math import acos, asin, atan, atan2, cos, sin, sqrt, tan
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.parameters import (Angle, Count, DimensionError, Flag, Length,
                                   Quantity, Ratio, Scalar)


class Torque(Quantity):
    """A project-declared kind: the engine never enumerates kinds."""

    dimension = {'M': 1, 'L': 2, 'T': -2}


class KindDimensionsTest(TestCase):

    def test_each_kind_declares_its_exponents(self):
        self.assertEqual(Length(1.0).dimension, {'L': 1})
        self.assertEqual(Angle(1.0).dimension, {'A': 1})
        self.assertEqual(Count(1).dimension, {})
        self.assertEqual(Ratio(1.0).dimension, {})
        self.assertEqual(Torque(1.0).dimension, {'M': 1, 'L': 2, 'T': -2})

    def test_scalar_is_unchecked(self):
        self.assertTrue(Scalar(1.0).unchecked)
        self.assertFalse(Length(1.0).unchecked)


class ArithmeticTest(TestCase):

    def test_mixed_kinds_fail_on_import(self):
        with self.assertRaises(DimensionError) as ctx:
            class Gear(Solid2Node):
                bore = Length(30.0)
                pressure_angle = Angle(20.0)
                wrong = bore + pressure_angle
        self.assertIn('bore', str(ctx.exception))
        self.assertIn('pressure_angle', str(ctx.exception))

    def test_subtraction_and_negation_need_equal_exponents(self):
        bore, angle = Length(30.0), Angle(20.0)
        with self.assertRaises(DimensionError):
            bore - angle
        self.assertEqual((-bore).dimension, {'L': 1})
        self.assertEqual((bore - Length(1.0)).dimension, {'L': 1})

    def test_products_and_quotients_close(self):
        teeth, module = Count(16), Length(2.0)
        bore, stroke = Length(30.0), Length(22.0)

        self.assertEqual((teeth * module).dimension, {'L': 1})
        self.assertEqual((bore / stroke).dimension, {})
        self.assertEqual((bore * bore).dimension, {'L': 2})
        self.assertEqual((bore ** 3).dimension, {'L': 3})
        self.assertEqual((Length(1.0) / (bore * bore)).dimension, {'L': -1})

    def test_plain_numbers_are_dimensionless_on_either_side(self):
        bore = Length(30.0)

        self.assertEqual((2 * bore).dimension, {'L': 1})
        self.assertEqual((bore / 2).dimension, {'L': 1})
        self.assertEqual((1.0 / bore).dimension, {'L': -1})
        with self.assertRaises(DimensionError):
            bore + 1
        with self.assertRaises(DimensionError):
            1 - bore

    def test_count_and_ratio_share_the_dimensionless_exponent(self):
        # Dimensionally sound, semantically odd, and deliberately not
        # refused: the algebra catches dimensional mistakes only.
        self.assertEqual((Count(4) + Ratio(0.5)).dimension, {})

    def test_a_project_kind_extends_the_ontology(self):
        torque, arm = Torque(5.0), Length(0.2)

        self.assertEqual((torque / arm).dimension,
                         {'M': 1, 'L': 1, 'T': -2})
        with self.assertRaises(DimensionError):
            torque + arm

    def test_the_escape_hatch_never_blocks(self):
        bore, angle = Length(30.0), Angle(20.0)

        loose = bore.value + angle.value
        self.assertTrue(loose.unchecked)
        self.assertTrue((Scalar(2.0) * bore).unchecked)
        self.assertTrue((bore + Scalar(1.0)).unchecked)

    def test_flag_is_outside_the_algebra(self):
        with self.assertRaises(TypeError):
            Flag(True) + 1
        with self.assertRaises(TypeError):
            Length(1.0) * Flag(True)

    def test_comparisons_are_refused_in_the_declaration_layer(self):
        bore, wall = Length(30.0), Length(0.3)
        with self.assertRaises(TypeError):
            bore < wall
        with self.assertRaises(TypeError):
            bore > 2 * wall

    def test_a_non_integer_power_is_refused(self):
        with self.assertRaises(TypeError):
            Length(4.0) ** 0.5


class FunctionsTest(TestCase):

    def test_sqrt_halves_even_exponents(self):
        z1, z2, module = Count(16), Count(32), Length(2.0)
        area = Length(4.0) * Length(9.0)

        self.assertEqual(sqrt(area).dimension, {'L': 1})
        self.assertEqual((module / 2 * sqrt(z1 * z1 + z2 * z2)).dimension,
                         {'L': 1})
        with self.assertRaises(DimensionError):
            sqrt(Length(4.0))

    def test_trig_demands_an_angle_and_returns_dimensionless(self):
        angle, bore = Angle(30.0), Length(30.0)

        for function in (sin, cos, tan):
            self.assertEqual(function(angle).dimension, {})
            with self.assertRaises(DimensionError):
                function(bore)
            with self.assertRaises(DimensionError):
                function(Count(3))

    def test_inverse_trig_takes_dimensionless_and_returns_an_angle(self):
        z1, z2, bore = Count(16), Count(32), Length(30.0)

        for function in (asin, acos, atan):
            self.assertEqual(function(z1 / z2).dimension, {'A': 1})
            with self.assertRaises(DimensionError):
                function(bore)
        self.assertEqual(atan2(z1, z2).dimension, {'A': 1})
        self.assertEqual(atan2(bore, Length(1.0)).dimension, {'A': 1})
        with self.assertRaises(DimensionError):
            atan2(bore, z2)

    def test_the_numeric_and_symbolic_modes_are_untouched(self):
        self.assertAlmostEqual(sin(90), 1.0)
        self.assertAlmostEqual(atan(1.0), 45.0)
        self.assertAlmostEqual(sqrt(16.0), 4.0)


class FormulaValuesTest(TestCase):
    """The same tree that carried dimensions at class definition
    evaluates to plain floats at instantiation."""

    def test_windmill_gear_layer_evaluates(self):
        class Bevel(AssemblyNode):
            module = Length(2.0, min=0)
            z1 = Count(16, min=1)
            z2 = Count(32, min=1)

            pitch_angle = atan(z1 / z2)
            cone_distance = module / 2 * sqrt(z1 * z1 + z2 * z2)
            axis_y = cone_distance * cos(pitch_angle)

        bevel = Bevel()

        self.assertAlmostEqual(bevel.pitch_angle, 26.565051177)
        self.assertAlmostEqual(bevel.cone_distance, 35.777087639)
        self.assertAlmostEqual(bevel.axis_y, 32.0)
        self.assertIsInstance(bevel.axis_y, float)
        self.assertEqual(Bevel.axis_y.dimension, {'L': 1})

    def test_a_derived_value_follows_a_rebound_input(self):
        class Bevel(AssemblyNode):
            module = Length(2.0, min=0)
            z1 = Count(16, min=1)
            z2 = Count(32, min=1)
            cone_distance = module / 2 * sqrt(z1 * z1 + z2 * z2)

        self.assertAlmostEqual(Bevel(module=4.0).cone_distance,
                               71.554175279)
