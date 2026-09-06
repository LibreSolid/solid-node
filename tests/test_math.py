# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""solid_node.math: dual-mode degree trig (issue #19).

AssemblyNode.time is numeric under set_keyframe() (tests) but
symbolic ($t, an OpenSCADConstant) in the viewer/build path. Plain
math.asin(...) et al. raise TypeError on the symbolic value the
instant a non-linear expression touches it, killing `solid develop`
at the first non-linear mechanism. solid_node.math must (a) match
OpenSCAD's own degree-in/degree-out trig semantics numerically, and
(b) build the equivalent OpenSCAD expression string when any argument
is symbolic, agreeing with the numeric computation at every sampled
instant.
"""

import math as pymath
import re
from unittest import TestCase

from solid2 import get_animation_time
from solid2.core.object_base import OpenSCADConstant

from solid_node import math as snmath
from solid_node.parameters import (Angle, DimensionError, Length, Ratio,
                                   Scalar)


ANGLES = [-180, -90, -60, -45, -30, 0, 30, 45, 60, 90, 120, 180, 270, 360]
UNIT_VALUES = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]


class NumericModeTest(TestCase):
    """All-numeric args compute with Python's math, in degrees."""

    def test_sin(self):
        for angle in ANGLES:
            self.assertAlmostEqual(
                snmath.sin(angle), pymath.sin(pymath.radians(angle)))

    def test_cos(self):
        for angle in ANGLES:
            self.assertAlmostEqual(
                snmath.cos(angle), pymath.cos(pymath.radians(angle)))

    def test_tan(self):
        for angle in (-60, -45, 0, 45, 60, 120):
            self.assertAlmostEqual(
                snmath.tan(angle), pymath.tan(pymath.radians(angle)))

    def test_asin(self):
        self.assertAlmostEqual(snmath.asin(0.5), 30.0)
        self.assertAlmostEqual(snmath.asin(1.0), 90.0)
        for value in UNIT_VALUES:
            self.assertAlmostEqual(
                snmath.asin(value), pymath.degrees(pymath.asin(value)))

    def test_acos(self):
        self.assertAlmostEqual(snmath.acos(0.5), 60.0)
        for value in UNIT_VALUES:
            self.assertAlmostEqual(
                snmath.acos(value), pymath.degrees(pymath.acos(value)))

    def test_atan(self):
        self.assertAlmostEqual(snmath.atan(1.0), 45.0)
        for value in [-2.0, -1.0, 0.0, 1.0, 2.0, 10.0]:
            self.assertAlmostEqual(
                snmath.atan(value), pymath.degrees(pymath.atan(value)))

    def test_atan2(self):
        self.assertAlmostEqual(snmath.atan2(1.0, 1.0), 45.0)
        self.assertAlmostEqual(snmath.atan2(1.0, 0.0), 90.0)
        for y in (-2.0, -1.0, 0.5, 1.0, 3.0):
            for x in (-2.0, -1.0, 0.5, 1.0, 3.0):
                self.assertAlmostEqual(
                    snmath.atan2(y, x),
                    pymath.degrees(pymath.atan2(y, x)))

    def test_sqrt(self):
        for value in (0.0, 1.0, 2.0, 4.0, 100.0):
            self.assertAlmostEqual(snmath.sqrt(value), pymath.sqrt(value))


class SymbolicModeTest(TestCase):
    """Any symbolic arg (an OpenSCADConstant, like solid2's $t) must
    return an OpenSCADConstant expression, never raise, and never
    silently fall through to Python's radians-based math."""

    def test_returns_openscad_constant(self):
        t = get_animation_time()
        for fn, name in [
            (snmath.sin, 'sin'), (snmath.cos, 'cos'), (snmath.tan, 'tan'),
            (snmath.asin, 'asin'), (snmath.acos, 'acos'),
            (snmath.atan, 'atan'), (snmath.sqrt, 'sqrt'),
        ]:
            result = fn(t)
            self.assertIsInstance(result, OpenSCADConstant)
            self.assertEqual(str(result), f'{name}($t)')

    def test_atan2_mixed_symbolic_and_numeric(self):
        t = get_animation_time()
        result = snmath.atan2(t, 1.0)
        self.assertIsInstance(result, OpenSCADConstant)
        self.assertEqual(str(result), 'atan2($t, 1.0)')

    def test_composed_nonlinear_expression(self):
        """The exact shape from the bug report: a linear expression in
        self.time survives symbolically through solid2's own operator
        overloads (720.0 * $t); wrapping it in sin/asin must nest
        correctly instead of raising."""
        t = get_animation_time()
        theta = 720.0 * t
        expr = snmath.asin(0.25 * snmath.sin(theta))
        self.assertIsInstance(expr, OpenSCADConstant)
        self.assertEqual(str(expr), 'asin((0.25 * sin((720.0 * $t))))')


def _eval_openscad_expr(expr, t):
    """Tiny degree-aware evaluator for the OpenSCAD expression strings
    solid_node.math generates, substituting a numeric $t. Used only to
    cross-check that the symbolic and numeric code paths agree -- it
    is NOT part of the framework."""
    py_expr = expr.replace('$t', repr(t))
    py_expr = re.sub(r'\bsin\(', 'DEGSIN(', py_expr)
    py_expr = re.sub(r'\bcos\(', 'DEGCOS(', py_expr)
    py_expr = re.sub(r'\btan\(', 'DEGTAN(', py_expr)
    py_expr = re.sub(r'\basin\(', 'DEGASIN(', py_expr)
    py_expr = re.sub(r'\bacos\(', 'DEGACOS(', py_expr)
    py_expr = re.sub(r'\batan2\(', 'DEGATAN2(', py_expr)
    py_expr = re.sub(r'\batan\(', 'DEGATAN(', py_expr)
    py_expr = re.sub(r'\bsqrt\(', 'DEGSQRT(', py_expr)

    env = {
        'DEGSIN': lambda x: pymath.sin(pymath.radians(x)),
        'DEGCOS': lambda x: pymath.cos(pymath.radians(x)),
        'DEGTAN': lambda x: pymath.tan(pymath.radians(x)),
        'DEGASIN': lambda x: pymath.degrees(pymath.asin(x)),
        'DEGACOS': lambda x: pymath.degrees(pymath.acos(x)),
        'DEGATAN2': lambda y, x: pymath.degrees(pymath.atan2(y, x)),
        'DEGATAN': lambda x: pymath.degrees(pymath.atan(x)),
        'DEGSQRT': pymath.sqrt,
        # The direct builtins need no renaming: they are spelled the same
        # in OpenSCAD, in JavaScript's Math and here, which is the whole
        # reason they are the ones the module emits.
        'abs': abs,
        'floor': pymath.floor,
        'ceil': pymath.ceil,
        'sign': lambda x: (x > 0) - (x < 0),
        'min': min,
        'max': max,
    }
    return eval(py_expr, {'__builtins__': {}}, env)


class NumericSymbolicAgreementTest(TestCase):
    """The two modes must agree: evaluating the generated symbolic
    expression at a sampled $t must equal calling the numeric-mode
    functions directly with the same time."""

    def test_composed_expression_matches_numeric_mode(self):
        t_symbol = get_animation_time()
        theta = 720.0 * t_symbol
        expr = snmath.asin(0.25 * snmath.sin(theta))

        for t in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
            evaluated = _eval_openscad_expr(str(expr), t)
            numeric_theta = 720.0 * t
            expected = snmath.asin(0.25 * snmath.sin(numeric_theta))
            self.assertAlmostEqual(evaluated, expected, places=9)

    def test_atan2_expression_matches_numeric_mode(self):
        t_symbol = get_animation_time()
        expr = snmath.atan2(snmath.sin(360.0 * t_symbol), 1.0)

        for t in (0.0, 0.2, 0.5, 0.8, 1.0):
            evaluated = _eval_openscad_expr(str(expr), t)
            expected = snmath.atan2(snmath.sin(360.0 * t), 1.0)
            self.assertAlmostEqual(evaluated, expected, places=9)


###############################################################################
# The expression vocabulary (OpenSpec change `expression-math`).
#
# Thirteen project kinematics modules rebuilt this arithmetic themselves --
# four of them over `sqrt(x * x)`, for a viewer limitation that never
# existed, and four clock models by reaching into solid2's OpenSCADConstant
# to emit `floor`. These pin the module's own vocabulary on all three faces.


DIRECT_BUILTINS = ('abs', 'floor', 'ceil', 'sign')


class SymbolicBuiltinStringTest(TestCase):
    """Each direct builtin emits the OpenSCAD builtin of its own name --
    the whole point of the change, since a stand-in built from `sqrt` is
    what the projects had to write."""

    def test_one_argument_builtins(self):
        t = get_animation_time()
        for name in DIRECT_BUILTINS:
            result = getattr(snmath, name)(t)
            self.assertIsInstance(result, OpenSCADConstant)
            self.assertEqual(str(result), f'{name}($t)')

    def test_two_argument_builtins(self):
        t = get_animation_time()
        for name in ('min', 'max'):
            result = getattr(snmath, name)(t, 1.0)
            self.assertIsInstance(result, OpenSCADConstant)
            self.assertEqual(str(result), f'{name}($t, 1.0)')

    def test_inventory_holds_every_emitted_name(self):
        """One inventory of emitted builtins, so the parity corpus check
        and this suite never keep a second list."""
        self.assertEqual(
            set(snmath.SYMBOLIC_BUILTINS),
            {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2', 'sqrt',
             'abs', 'floor', 'ceil', 'sign', 'min', 'max'})

    def test_an_uninventoried_name_cannot_be_emitted(self):
        t = get_animation_time()
        with self.assertRaises(ValueError) as caught:
            snmath._symbolic_call('round', t)
        self.assertIn('round', str(caught.exception))

    def test_no_rounding_or_modulo_is_exported(self):
        """OpenSCAD, JavaScript and Python round halves three different
        ways, and OpenSCAD spells modulo as an operator, not a function."""
        for name in ('round', 'mod'):
            self.assertFalse(hasattr(snmath, name), name)


class CompositionSymbolicStringTest(TestCase):
    """A composition puts only inventoried builtins and arithmetic on the
    wire: no `sqrt(x * x)` stand-in, no name a runtime cannot answer."""

    def test_clamp01(self):
        t = get_animation_time()
        self.assertEqual(str(snmath.clamp01(t)), 'min(max($t, 0.0), 1.0)')

    def test_clamp(self):
        t = get_animation_time()
        self.assertEqual(str(snmath.clamp(t, 2.0, 5.0)),
                         'min(max($t, 2.0), 5.0)')

    def test_wrap(self):
        t = get_animation_time()
        self.assertEqual(
            str(snmath.wrap(t)),
            '($t - (360.0 * ceil((($t - 180.0) / 360.0))))')

    def test_bump_carries_no_trigonometry(self):
        t = get_animation_time()
        rendered = str(snmath.bump(t))
        self.assertIn('min(max($t, 0.0), 1.0)', rendered)
        self.assertNotIn('sin(', rendered)
        self.assertNotIn('sqrt(', rendered)

    def test_no_composition_emits_an_unknown_name(self):
        import re
        t = get_animation_time()
        expressions = [
            snmath.clamp(t, 0.0, 1.0), snmath.clamp01(t),
            snmath.ramp(t, 0.2, 0.8), snmath.lerp(1.0, 2.0, t),
            snmath.wrap(t), snmath.bump(t),
            snmath.piecewise(t, [(0.0, 0.0), (1.0, 1.0)]),
        ]
        for expression in expressions:
            called = set(re.findall(r'([A-Za-z_]\w*)\(', str(expression)))
            self.assertLessEqual(called, set(snmath.SYMBOLIC_BUILTINS),
                                 str(expression))


class NumericBuiltinTest(TestCase):
    """The numeric face is the same function OpenSCAD and the browser
    evaluate, on the inputs where a runtime could disagree."""

    def test_abs(self):
        for value in (-2.5, -0.0, 0.0, 2.5):
            self.assertEqual(snmath.abs(value), abs(value))

    def test_floor(self):
        self.assertEqual(snmath.floor(-2.5), -3)
        self.assertEqual(snmath.floor(2.5), 2)
        self.assertEqual(snmath.floor(3.0), 3)

    def test_ceil(self):
        self.assertEqual(snmath.ceil(-2.5), -2)
        self.assertEqual(snmath.ceil(2.5), 3)
        self.assertEqual(snmath.ceil(3.0), 3)

    def test_sign(self):
        self.assertEqual(snmath.sign(0), 0)
        self.assertEqual(snmath.sign(-0.0), 0)
        self.assertEqual(snmath.sign(4.2), 1)
        self.assertEqual(snmath.sign(-4.2), -1)

    def test_min_and_max(self):
        self.assertEqual(snmath.min(2.0, 5.0), 2.0)
        self.assertEqual(snmath.max(2.0, 5.0), 5.0)
        self.assertEqual(snmath.min(-1.0, -1.0), -1.0)

    def test_min_and_max_take_exactly_two(self):
        """OpenSCAD's variadic and vector forms vary by version; two is
        the arity every runtime agrees on."""
        with self.assertRaises(TypeError):
            snmath.min(1.0, 2.0, 3.0)
        with self.assertRaises(TypeError):
            snmath.max(1.0, 2.0, 3.0)


class NumericCompositionTest(TestCase):

    def test_clamp(self):
        self.assertEqual(snmath.clamp(-5.0, 0.0, 10.0), 0.0)
        self.assertEqual(snmath.clamp(4.0, 0.0, 10.0), 4.0)
        self.assertEqual(snmath.clamp(40.0, 0.0, 10.0), 10.0)

    def test_clamp01(self):
        for value, expected in ((-1.0, 0.0), (0.0, 0.0), (0.25, 0.25),
                                (1.0, 1.0), (2.0, 1.0)):
            self.assertAlmostEqual(snmath.clamp01(value), expected)

    def test_ramp(self):
        for value, expected in ((0.0, 0.0), (0.2, 0.0), (0.5, 0.5),
                                (0.8, 1.0), (1.0, 1.0)):
            self.assertAlmostEqual(snmath.ramp(value, 0.2, 0.8), expected)

    def test_ramp_refuses_equal_endpoints(self):
        with self.assertRaises(ValueError) as caught:
            snmath.ramp(0.5, 0.3, 0.3)
        self.assertIn('0.3', str(caught.exception))

    def test_lerp_is_unclamped(self):
        self.assertAlmostEqual(snmath.lerp(2.0, 8.0, 0.0), 2.0)
        self.assertAlmostEqual(snmath.lerp(2.0, 8.0, 0.5), 5.0)
        self.assertAlmostEqual(snmath.lerp(2.0, 8.0, 2.0), 14.0)

    def test_wrap(self):
        for value, expected in ((180.0, 180.0), (181.0, -179.0),
                                (-180.0, 180.0), (-181.0, 179.0),
                                (540.0, 180.0), (0.0, 0.0)):
            self.assertAlmostEqual(snmath.wrap(value), expected)

    def test_wrap_over_another_period(self):
        for value, expected in ((5.0, 5.0), (6.0, -4.0), (-6.0, 4.0)):
            self.assertAlmostEqual(snmath.wrap(value, 10.0), expected)

    def test_wrap_refuses_a_non_positive_period(self):
        for period in (0.0, -360.0):
            with self.assertRaises(ValueError):
                snmath.wrap(10.0, period)

    def test_piecewise(self):
        points = [(0.0, 0.0), (10.0, 4.0), (20.0, 6.0)]
        for value, expected in ((-5.0, 0.0), (0.0, 0.0), (5.0, 2.0),
                                (10.0, 4.0), (15.0, 5.0), (20.0, 6.0),
                                (40.0, 6.0)):
            self.assertAlmostEqual(snmath.piecewise(value, points), expected)

    def test_piecewise_refuses_a_malformed_sequence(self):
        with self.assertRaises(ValueError) as caught:
            snmath.piecewise(1.0, [(0.0, 0.0)])
        self.assertIn('two', str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            snmath.piecewise(1.0, [(0.0, 0.0), (0.0, 1.0)])
        self.assertIn('0.0', str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            snmath.piecewise(1.0, [(0.0, 0.0), (5.0, 1.0), (2.0, 3.0)])
        self.assertIn('2.0', str(caught.exception))

    def test_bump(self):
        for value, expected in ((-1.0, 0.0), (0.0, 0.0), (0.25, 0.5625),
                                (0.5, 1.0), (1.0, 0.0), (2.0, 0.0)):
            self.assertAlmostEqual(snmath.bump(value), expected)

    def test_bump_has_zero_slope_at_both_ends(self):
        for edge in (0.0, 1.0):
            near = snmath.bump(edge + 1e-4 * (1 if edge == 0.0 else -1))
            self.assertLess(near, 1e-6)


def _composed(module, t):
    """One expression over the whole new vocabulary, built the same way
    on numbers and on symbolic time."""
    return (module.clamp(module.floor(4.0 * t) + module.abs(t - 0.5),
                         0.0, 3.0)
            + module.wrap(720.0 * t)
            + module.bump(t)
            + module.sign(t - 0.5)
            + module.min(t, 0.5) * module.max(t, 0.25)
            + module.ceil(3.0 * t)
            + module.lerp(2.0, 8.0, module.clamp01(t))
            + module.ramp(t, 0.2, 0.8)
            + module.piecewise(t, [(0.0, 0.0), (0.5, 4.0), (1.0, 1.0)]))


class VocabularyAgreementTest(TestCase):
    """The deferred expression and the numeric computation are the same
    function -- the property ADR-022 is about, over the new names."""

    def test_composed_expression_matches_numeric_mode(self):
        expression = str(_composed(snmath, get_animation_time()))
        for t in (0.0, 0.1, 0.25, 0.37, 0.5, 0.75, 0.9, 1.0):
            self.assertAlmostEqual(_eval_openscad_expr(expression, t),
                                   _composed(snmath, t), places=9)


class MixedFaceTest(TestCase):
    """A symbolic value and a declared parameter in one call would render
    the declaration's repr() into the published expression."""

    def test_min_refuses_the_mixture(self):
        t = get_animation_time()
        with self.assertRaises(TypeError) as caught:
            snmath.min(t, Length(3.0))
        message = str(caught.exception)
        self.assertIn('$t', message)
        self.assertIn('Length', message)

    def test_atan2_refuses_the_mixture(self):
        t = get_animation_time()
        with self.assertRaises(TypeError):
            snmath.atan2(t, Length(3.0))

    def test_a_composition_refuses_the_mixture(self):
        t = get_animation_time()
        with self.assertRaises(TypeError):
            snmath.clamp(t, Length(0.0), 1.0)


class VectorHelperTest(TestCase):
    """Layer 2: written per project in every frame convention, and two of
    the copies numeric-only, so a symbolic driver broke them."""

    def test_polar(self):
        x, y = snmath.polar(10.0, 90.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 10.0)

    def test_turn_about_the_origin_and_a_centre(self):
        x, y = snmath.turn((10.0, 0.0), 90.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 10.0)
        x, y = snmath.turn((10.0, 0.0), 90.0, about=(10.0, 0.0))
        self.assertAlmostEqual(x, 10.0)
        self.assertAlmostEqual(y, 0.0)

    def test_axis_rotations(self):
        x, y, z = snmath.rotate_x((0.0, 1.0, 0.0), 90.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(z, 1.0)
        x, y, z = snmath.rotate_y((0.0, 0.0, 1.0), 90.0)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(z, 0.0)
        x, y, z = snmath.rotate_z((1.0, 0.0, 0.0), 90.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 1.0)
        self.assertAlmostEqual(z, 0.0)

    def test_a_symbolic_angle_rides_through(self):
        t = get_animation_time()
        angle = 360.0 * t
        point = (0.0, 1.0, 2.0)
        for components, moving in (
                (snmath.polar(10.0, angle), (0, 1)),
                (snmath.turn((10.0, 0.0), angle), (0, 1)),
                (snmath.turn((10.0, 0.0), angle, about=(1.0, 2.0)), (0, 1)),
                (snmath.rotate_x(point, angle), (1, 2)),
                (snmath.rotate_y(point, angle), (0, 2)),
                (snmath.rotate_z(point, angle), (0, 1))):
            for index in moving:
                rendered = str(components[index])
                self.assertIn('$t', rendered)
                self.assertTrue('sin(' in rendered or 'cos(' in rendered,
                                rendered)

    def test_the_invariant_axis_passes_through(self):
        angle = 360.0 * get_animation_time()
        self.assertEqual(snmath.rotate_x((7.0, 1.0, 2.0), angle)[0], 7.0)
        self.assertEqual(snmath.rotate_y((7.0, 1.0, 2.0), angle)[1], 1.0)
        self.assertEqual(snmath.rotate_z((7.0, 1.0, 2.0), angle)[2], 2.0)

    def test_a_symbolic_component_rides_through(self):
        t = get_animation_time()
        x, y, z = snmath.rotate_z((t, 0.0, 0.0), 90.0)
        self.assertIn('$t', str(x))

    def test_symbolic_and_numeric_agree(self):
        t_symbol = get_animation_time()
        symbolic = [str(part)
                    for part in snmath.rotate_z((10.0, 4.0, 1.0),
                                                360.0 * t_symbol)]
        for t in (0.0, 0.2, 0.5, 0.9):
            expected = snmath.rotate_z((10.0, 4.0, 1.0), 360.0 * t)
            for rendered, value in zip(symbolic, expected):
                self.assertAlmostEqual(_eval_openscad_expr(rendered, t),
                                       value, places=9)


class TurnAboutTheOriginTest(TestCase):
    """A turn about the origin builds no subtraction: the terms would be
    `- 0.0` and `0.0 +`, which cost wire length for nothing."""

    def test_the_default_centre_emits_no_zero_terms(self):
        t = get_animation_time()
        x, y = snmath.turn((10.0, 4.0), 360.0 * t)
        self.assertNotIn('0.0)', str(x))
        self.assertEqual(str(x),
                         '((10.0 * cos((360.0 * $t))) - '
                         '(4.0 * sin((360.0 * $t))))')

    def test_an_explicit_centre_still_composes(self):
        x, y = snmath.turn((10.0, 0.0), 90.0, about=(10.0, 0.0))
        self.assertAlmostEqual(x, 10.0)
        self.assertAlmostEqual(y, 0.0)


class WrapPeriodTest(TestCase):
    """`isinstance(True, int)` is True, so a period of True would pass a
    plain numeric check and quietly fold everything into (-0.5, 0.5]."""

    def test_a_boolean_period_is_refused(self):
        for period in (True, False):
            with self.assertRaises(ValueError):
                snmath.wrap(5.0, period)
