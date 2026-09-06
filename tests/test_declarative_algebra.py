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

import solid_node.math as snmath
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


class DirectBuiltinDimensionTest(TestCase):
    """The six direct builtins are PRIMITIVES: each carries a rule of
    its own, which is what a composition over them then inherits."""

    def test_abs_preserves_its_dimension(self):
        bore = Length(30.0)
        self.assertEqual(snmath.abs(bore).dimension, {'L': 1})
        self.assertEqual(snmath.abs(Angle(30.0)).dimension, {'A': 1})
        self.assertEqual(snmath.abs(Count(3)).dimension, {})

    def test_min_and_max_need_equal_dimensions_and_preserve_them(self):
        bore, wall = Length(30.0), Length(0.3)
        for function in (snmath.min, snmath.max):
            self.assertEqual(function(bore, wall).dimension, {'L': 1})
            self.assertEqual(
                function(Angle(1.0), Angle(2.0)).dimension, {'A': 1})
            with self.assertRaises(DimensionError):
                function(bore, Angle(30.0))
            with self.assertRaises(DimensionError):
                function(bore, 0.0)

    def test_floor_and_ceil_take_a_dimensionless_quantity(self):
        """A whole number bears no dimension, and the algebra checks
        dimensions, never units -- so `floor(30 mm)` is only meaningful
        if millimetres are assumed, which is what it refuses to do."""
        bore, pitch = Length(30.0), Length(2.0)
        for function in (snmath.floor, snmath.ceil):
            self.assertEqual(function(bore / pitch).dimension, {})
            self.assertEqual(function(Count(7) / Count(2)).dimension, {})
            with self.assertRaises(DimensionError) as caught:
                function(bore)
            self.assertIn('L', str(caught.exception))
            with self.assertRaises(DimensionError):
                function(Angle(30.0))

    def test_sign_takes_any_dimension_and_returns_dimensionless(self):
        """It compares against zero, which every dimension shares."""
        self.assertEqual(snmath.sign(Length(30.0)).dimension, {})
        self.assertEqual(snmath.sign(Angle(30.0)).dimension, {})
        self.assertEqual(snmath.sign(Count(3)).dimension, {})


class CompositionDimensionTest(TestCase):
    """A composition has no rule of its own: what it does to dimensions
    is a CONSEQUENCE of the primitives it composes and the algebra."""

    def test_clamp_preserves_and_ramp_flattens(self):
        reach, low, high = Length(5.0), Length(1.0), Length(9.0)
        self.assertEqual(snmath.clamp(reach, low, high).dimension, {'L': 1})
        self.assertEqual(snmath.ramp(reach, low, high).dimension, {})
        with self.assertRaises(DimensionError):
            snmath.clamp(reach, low, Angle(9.0))

    def test_clamp01_and_bump_are_dimensionless_both_ways(self):
        phase = Ratio(0.25)
        self.assertEqual(snmath.clamp01(phase).dimension, {})
        self.assertEqual(snmath.bump(phase).dimension, {})
        for function in (snmath.clamp01, snmath.bump):
            with self.assertRaises(DimensionError):
                function(Length(30.0))

    def test_lerp_carries_its_endpoints(self):
        self.assertEqual(
            snmath.lerp(Length(1.0), Length(9.0), Ratio(0.5)).dimension,
            {'L': 1})
        with self.assertRaises(DimensionError):
            snmath.lerp(Length(1.0), Angle(9.0), Ratio(0.5))
        with self.assertRaises(DimensionError):
            snmath.lerp(Length(1.0), Length(9.0), Length(0.5))

    def test_wrap_carries_its_value(self):
        self.assertEqual(snmath.wrap(Angle(400.0), Angle(360.0)).dimension,
                         {'A': 1})
        with self.assertRaises(DimensionError):
            snmath.wrap(Angle(400.0), Length(360.0))

    def test_wrap_needs_a_dimensioned_period_in_a_declaration(self):
        """The default period is the plain number 360.0, so a declared
        angle meets a dimensionless operand -- the same trap
        clamp01(length) sets, and the same cure."""
        bearing = Angle(400.0)
        with self.assertRaises(DimensionError) as caught:
            snmath.wrap(bearing)
        message = str(caught.exception)
        self.assertIn('180.0', message)
        self.assertIn('dimensionless', message)
        self.assertEqual(snmath.wrap(bearing, Angle(360.0)).dimension,
                         {'A': 1})

    def test_a_declared_wrap_evaluates(self):
        class Compass(Solid2Node):
            bearing = Angle(400.0)
            folded = snmath.wrap(bearing, Angle(360.0))

            def render(self):
                return None

        self.assertAlmostEqual(Compass.folded.evaluate({'bearing': 400.0}),
                               40.0)
        self.assertAlmostEqual(Compass.folded.evaluate({'bearing': 181.0}),
                               -179.0)

    def test_piecewise_carries_its_ordinate(self):
        lift = Length(5.0)
        points = [(0.0, Length(0.0)), (10.0, Length(4.0))]
        with self.assertRaises(DimensionError):
            # the waypoint positions are plain numbers, so a dimensioned
            # abscissa cannot match them
            snmath.piecewise(lift, points)
        travel = Ratio(0.5)
        self.assertEqual(snmath.piecewise(travel, points).dimension, {'L': 1})

    def test_no_composition_reaches_the_rule_table(self):
        """`function_formula` raises on a name it does not know, so a
        composition that acquired a rule branch would be caught here."""
        from solid_node.parameters import function_formula
        for name in ('clamp', 'clamp01', 'ramp', 'lerp', 'wrap',
                     'piecewise', 'bump', 'polar', 'turn',
                     'rotate_x', 'rotate_y', 'rotate_z'):
            with self.assertRaises(ValueError):
                function_formula(name, lambda *a: 0.0, Ratio(0.5))


class VectorHelperDimensionTest(TestCase):
    """Layer 2 introduces no rule either: its dimensions fall out of the
    trigonometry it composes."""

    def test_polar_yields_two_lengths(self):
        radius, angle = Length(10.0), Angle(30.0)
        x, y = snmath.polar(radius, angle)
        self.assertEqual(x.dimension, {'L': 1})
        self.assertEqual(y.dimension, {'L': 1})
        with self.assertRaises(DimensionError):
            snmath.polar(radius, radius)

    def test_a_rotation_keeps_its_point_s_dimension(self):
        angle = Angle(30.0)
        point = (Length(1.0), Length(2.0), Length(3.0))
        for function in (snmath.rotate_x, snmath.rotate_y, snmath.rotate_z):
            for component in function(point, angle):
                self.assertEqual(component.dimension, {'L': 1})
        for component in snmath.turn((Length(1.0), Length(2.0)), angle):
            self.assertEqual(component.dimension, {'L': 1})
        centred = snmath.turn((Length(1.0), Length(2.0)), angle,
                              about=(Length(0.5), Length(0.5)))
        for component in centred:
            self.assertEqual(component.dimension, {'L': 1})
        with self.assertRaises(DimensionError):
            # an EXPLICIT centre must share the point's dimension; the
            # default one builds no centring terms and so meets no zero
            snmath.turn((Length(1.0), Length(2.0)), angle, about=(0.0, 0.0))


class DeclaredPulseTest(TestCase):
    """The face the polynomial `bump` exists for: a class body deriving
    a pulse of a declared ratio."""

    def test_a_pulse_of_a_declared_ratio_evaluates(self):
        class Cam(Solid2Node):
            phase = Ratio(0.25)
            lift = snmath.bump(phase)

            def render(self):
                return None

        self.assertEqual(Cam.lift.dimension, {})
        self.assertAlmostEqual(Cam.lift.evaluate({'phase': 0.25}), 0.5625)
        self.assertAlmostEqual(Cam.lift.evaluate({'phase': 0.5}), 1.0)
        self.assertAlmostEqual(Cam.lift.evaluate({'phase': 2.0}), 0.0)
