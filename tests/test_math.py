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
