# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Degree-based trig (and sqrt) that works under BOTH of
AssemblyNode.time's two faces:

- numeric, under set_keyframe() (tests, keyframe renders): self.time
  is a plain float, and these functions compute with Python's stdlib
  math -- in DEGREES, matching the OpenSCAD language (sin(90) == 1.0,
  asin(0.5) == 30.0, atan2 returns degrees).

- symbolic, in the viewer/build path (a fresh node.assemble(), no
  set_keyframe): self.time is solid2's $t, an OpenSCADConstant
  (ScadValue) that only knows how to build an expression string, not
  evaluate one. Python's stdlib math.asin(...) et al. raise
  `TypeError: must be real number, not OpenSCADConstant` the moment a
  non-linear expression touches a symbolic time. These functions
  detect that case (any argument is an OpenSCADConstant) and instead
  return a NEW OpenSCADConstant whose expression is the equivalent
  OpenSCAD builtin call over the rendered sub-expressions, e.g.
  `asin((0.25 * sin((720.0 * $t))))` -- OpenSCAD's own trig builtins
  are degree-in/degree-out too, so the symbolic expression and the
  numeric computation are the same function, just deferred.

Only used for genuinely non-linear kinematics; a linear expression in
self.time (e.g. `720.0 * self.time`) already survives symbolically
through solid2's own operator overloads and needs none of this.
"""

import math as _math

from solid2.core.object_base import OpenSCADConstant


def _is_symbolic(value):
    return isinstance(value, OpenSCADConstant)


def _is_formula(value):
    """A declared quantity or a formula over them: the third face.

    Under the declarative node API a class body derives parameters
    through these same names (windmill's gear layer takes an `atan`, a
    `sqrt` and a `cos`), and the result is a formula carrying the
    function's dimension rule, evaluated numerically -- through the
    numeric branch below -- when the node is constructed. Imported on
    use so this module stays as light as it is on every other path.
    """
    if isinstance(value, (int, float)) or _is_symbolic(value):
        return False
    from solid_node.node.declarative import Expression
    return isinstance(value, Expression)


def _formula(name, numeric, *args):
    from solid_node.node.declarative import function_formula
    return function_formula(name, numeric, *args)


def _render(value):
    """Renders a value (numeric or symbolic) as an OpenSCAD
    sub-expression string. OpenSCADConstant.__repr__ returns its
    `.value` expression string verbatim (and str() falls back to
    __repr__ since OpenSCADConstant defines no __str__); plain numbers
    render the same way solid2's own py2openscad renders them."""
    return str(value)


def _symbolic_call(name, *args):
    rendered = ', '.join(_render(arg) for arg in args)
    return OpenSCADConstant(f'{name}({rendered})')


def sin(x):
    """sin of an angle in DEGREES."""
    if _is_symbolic(x):
        return _symbolic_call('sin', x)
    if _is_formula(x):
        return _formula('sin', sin, x)
    return _math.sin(_math.radians(x))


def cos(x):
    """cos of an angle in DEGREES."""
    if _is_symbolic(x):
        return _symbolic_call('cos', x)
    if _is_formula(x):
        return _formula('cos', cos, x)
    return _math.cos(_math.radians(x))


def tan(x):
    """tan of an angle in DEGREES."""
    if _is_symbolic(x):
        return _symbolic_call('tan', x)
    if _is_formula(x):
        return _formula('tan', tan, x)
    return _math.tan(_math.radians(x))


def asin(x):
    """arcsine, returned in DEGREES."""
    if _is_symbolic(x):
        return _symbolic_call('asin', x)
    if _is_formula(x):
        return _formula('asin', asin, x)
    return _math.degrees(_math.asin(x))


def acos(x):
    """arccosine, returned in DEGREES."""
    if _is_symbolic(x):
        return _symbolic_call('acos', x)
    if _is_formula(x):
        return _formula('acos', acos, x)
    return _math.degrees(_math.acos(x))


def atan(x):
    """arctangent, returned in DEGREES."""
    if _is_symbolic(x):
        return _symbolic_call('atan', x)
    if _is_formula(x):
        return _formula('atan', atan, x)
    return _math.degrees(_math.atan(x))


def atan2(y, x):
    """Two-argument arctangent, returned in DEGREES."""
    if _is_symbolic(y) or _is_symbolic(x):
        return _symbolic_call('atan2', y, x)
    if _is_formula(y) or _is_formula(x):
        return _formula('atan2', atan2, y, x)
    return _math.degrees(_math.atan2(y, x))


def sqrt(x):
    """Square root (no degree semantics to speak of)."""
    if _is_symbolic(x):
        return _symbolic_call('sqrt', x)
    if _is_formula(x):
        return _formula('sqrt', sqrt, x)
    return _math.sqrt(x)


__all__ = [
    'sin', 'cos', 'tan',
    'asin', 'acos', 'atan', 'atan2',
    'sqrt',
]
