# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The expression vocabulary: one semantics, three faces.

Everything here computes under BOTH of AssemblyNode.time's two faces,
and under the declarative parameter algebra as well:

- numeric, under set_keyframe() (tests, keyframe renders): self.time
  is a plain float, and these functions compute with Python's stdlib
  math -- in DEGREES, matching the OpenSCAD language (sin(90) == 1.0,
  asin(0.5) == 30.0, atan2 returns degrees).

- symbolic, in the viewer/build path: time and drivers carry native
  shared graphs behind an OpenSCADConstant-compatible facade. These
  functions recognize both native values and legacy SolidPython constants,
  returning call nodes over operand references, never expanded text.
  Publication emits the existing degree-in/degree-out scalar vocabulary,
  so the symbolic and numeric computations are the same function deferred.

- declarative, in a node class body: an argument is a declared
  parameter token or a formula over them, and the result is a formula
  carrying this function's dimension rule, evaluated numerically -- by
  the numeric face above -- when the node is constructed.

Only used for genuinely non-linear kinematics; a linear expression in
self.time (e.g. `720.0 * self.time`) already survives symbolically
through the graph facade's operator overloads and needs none of this.

Two layers, and the distinction between them matters:

PRIMITIVES are the functions the module emits as an OpenSCAD call --
the degree trigonometry, `sqrt`, and the six direct builtins `abs`,
`floor`, `ceil`, `sign`, `min` and `max`. Each carries its own
dimension rule in `solid_node.parameters.function_formula`. Every name
one may emit is in SYMBOLIC_BUILTINS below, and `_symbolic_call`
refuses any other, so the parity corpus's coverage check has one list
to read and nobody keeps a second.

COMPOSITIONS -- `clamp`, `clamp01`, `ramp`, `lerp`, `wrap`,
`piecewise`, `bump` and the vector helpers -- are built out of the
primitives and ordinary arithmetic, and carry NO dimension rule.
That is deliberate: a rule would give each of them two definitions,
and the declared face would stop being the same function as the other
two. Their dimension behaviour is a consequence of the primitives'
rules plus the algebra's own. One consequence worth knowing:
`clamp01(a_length)` and `max(a_length, 0.0)` raise, because a plain
number is dimensionless -- the same refusal `a_length + 1` gives.

What is deliberately absent, and why:

- `round`. OpenSCAD rounds a half away from zero, JavaScript's
  Math.round rounds a half toward +infinity, and Python rounds a half
  to even. Three runtimes, three answers, on a value a timeline lands
  on constantly. `floor(x + 0.5)` is the half-up all three agree on.

- `mod`. OpenSCAD has no mod() function -- it spells the operation as
  the `%` operator -- and Python's `%` takes the sign of the divisor
  where OpenSCAD's and JavaScript's take the sign of the dividend.
  `wrap` is built on `ceil` instead, which every runtime agrees on.

These names deliberately shadow Python builtins in a module that
imports them (`from solid_node.math import floor, min, max`), exactly
as `from math import floor` does. The builtins this module needs
itself are bound privately below, before anything shadows them.
"""

import math as _math

from solid2.core.object_base import OpenSCADConstant
from solid_node.scad_expression import GraphValue, call as expression_call

from solid_node.parameters import Expression, function_formula

# The builtins this module shadows, kept before the shadowing so its
# own numeric faces can still reach them (`abs` calling `abs` would
# otherwise recurse).
_abs = abs
_min = min
_max = max


#: Every OpenSCAD builtin this module may emit as a call. It is the one
#: inventory: `_symbolic_call` refuses a name absent from it, and the
#: parity corpus's coverage check reads it rather than keeping a list of
#: its own, so a new symbolic function cannot reach a published document
#: without a fixture case behind it (ADR-022).
SYMBOLIC_BUILTINS = (
    'sin', 'cos', 'tan',
    'asin', 'acos', 'atan', 'atan2',
    'sqrt',
    'abs', 'floor', 'ceil', 'sign', 'min', 'max',
)


def _is_symbolic(value):
    return isinstance(value, OpenSCADConstant)


def _is_formula(value):
    """A declared quantity or a formula over them: the third face.

    Under the declarative node API a class body derives parameters
    through these same names (windmill's gear layer takes an `atan`, a
    `sqrt` and a `cos`), and the result is a formula carrying the
    function's dimension rule, evaluated numerically -- through the
    numeric branch below -- when the node is constructed.

    The parameter layer is imported at module scope: it reaches nothing
    else in the framework, so naming it costs this module nothing on any
    path. It used to be imported on use, when the algebra lived inside
    the node package and reaching it dragged that package in.
    """
    if isinstance(value, (int, float)) or _is_symbolic(value):
        return False
    return isinstance(value, Expression)


def _describe(value):
    """How an operand reads in an error."""
    if isinstance(value, GraphValue):
        return repr(value)
    if _is_symbolic(value):
        return str(value)[:200]
    name = getattr(value, '_name', None)
    if name:
        return f'{type(value).__name__} {name!r}'
    return f'{type(value).__name__} {value!r}'


def _face(name, *args):
    """Which of the three faces a call takes.

    A call mixing a symbolic value with a declared parameter has no
    answer: a formula evaluates against an instance's bound values, and
    there is no instance at the moment an expression is serialized
    symbolically. Left alone it would render the declaration's repr()
    into the published expression string -- `atan2($t, <Length ? =
    3.0>)` -- which the viewer would then be asked to parse. Nothing a
    correct model does reaches here: a declared parameter read through
    `self` is a plain number by the time any render() runs.
    """
    symbolic = [arg for arg in args if _is_symbolic(arg)]
    formulas = [arg for arg in args if _is_formula(arg)]
    if symbolic and formulas:
        raise TypeError(
            f"{name}({_describe(symbolic[0])}, ...): cannot combine the "
            f"symbolic value {_describe(symbolic[0])} with the declaration "
            f"{_describe(formulas[0])}. A declared parameter is resolved to "
            f"a number when its node is constructed, so it never meets "
            f"animation time or a driver; read it as an attribute of the "
            f"node instead.")
    if symbolic:
        return 'symbolic'
    if formulas:
        return 'formula'
    return 'numeric'


def _symbolic_call(name, *args):
    if name not in SYMBOLIC_BUILTINS:
        raise ValueError(
            f"{name!r} is not in SYMBOLIC_BUILTINS, so it cannot be emitted: "
            f"every name this module puts on the wire is listed there, and "
            f"the parity corpus reads that list to know what it must cover.")
    return expression_call(name, *args)


def _formula(name, numeric, *args):
    return function_formula(name, numeric, *args)


##############################################
# Primitives: the degree trigonometry


def sin(x):
    """sin of an angle in DEGREES."""
    face = _face('sin', x)
    if face == 'symbolic':
        return _symbolic_call('sin', x)
    if face == 'formula':
        return _formula('sin', sin, x)
    return _math.sin(_math.radians(x))


def cos(x):
    """cos of an angle in DEGREES."""
    face = _face('cos', x)
    if face == 'symbolic':
        return _symbolic_call('cos', x)
    if face == 'formula':
        return _formula('cos', cos, x)
    return _math.cos(_math.radians(x))


def tan(x):
    """tan of an angle in DEGREES."""
    face = _face('tan', x)
    if face == 'symbolic':
        return _symbolic_call('tan', x)
    if face == 'formula':
        return _formula('tan', tan, x)
    return _math.tan(_math.radians(x))


def asin(x):
    """arcsine, returned in DEGREES."""
    face = _face('asin', x)
    if face == 'symbolic':
        return _symbolic_call('asin', x)
    if face == 'formula':
        return _formula('asin', asin, x)
    return _math.degrees(_math.asin(x))


def acos(x):
    """arccosine, returned in DEGREES."""
    face = _face('acos', x)
    if face == 'symbolic':
        return _symbolic_call('acos', x)
    if face == 'formula':
        return _formula('acos', acos, x)
    return _math.degrees(_math.acos(x))


def atan(x):
    """arctangent, returned in DEGREES."""
    face = _face('atan', x)
    if face == 'symbolic':
        return _symbolic_call('atan', x)
    if face == 'formula':
        return _formula('atan', atan, x)
    return _math.degrees(_math.atan(x))


def atan2(y, x):
    """Two-argument arctangent, returned in DEGREES."""
    face = _face('atan2', y, x)
    if face == 'symbolic':
        return _symbolic_call('atan2', y, x)
    if face == 'formula':
        return _formula('atan2', atan2, y, x)
    return _math.degrees(_math.atan2(y, x))


def sqrt(x):
    """Square root (no degree semantics to speak of)."""
    face = _face('sqrt', x)
    if face == 'symbolic':
        return _symbolic_call('sqrt', x)
    if face == 'formula':
        return _formula('sqrt', sqrt, x)
    return _math.sqrt(x)


##############################################
# Primitives: the direct builtins
#
# Each is a name OpenSCAD and JavaScript's Math both carry, with the
# same semantics on every input a model can produce -- which is why
# four projects never needed the `sqrt(x * x)` clamp kit they wrote,
# and four clock models never needed to import solid2's private
# OpenSCADConstant to emit `floor`.


def abs(x):
    """Absolute value; keeps its argument's dimension."""
    face = _face('abs', x)
    if face == 'symbolic':
        return _symbolic_call('abs', x)
    if face == 'formula':
        return _formula('abs', abs, x)
    return _abs(x)


def floor(x):
    """The greatest whole number at or below `x` (-3 for -2.5, in every
    runtime). Dimensionless: a whole number bears no dimension, so the
    whole number of steps in a length is `floor(length / step)`."""
    face = _face('floor', x)
    if face == 'symbolic':
        return _symbolic_call('floor', x)
    if face == 'formula':
        return _formula('floor', floor, x)
    return _math.floor(x)


def ceil(x):
    """The least whole number at or above `x` (-2 for -2.5)."""
    face = _face('ceil', x)
    if face == 'symbolic':
        return _symbolic_call('ceil', x)
    if face == 'formula':
        return _formula('ceil', ceil, x)
    return _math.ceil(x)


def sign(x):
    """-1, 0 or 1: which side of zero `x` is on, with no branch."""
    face = _face('sign', x)
    if face == 'symbolic':
        return _symbolic_call('sign', x)
    if face == 'formula':
        return _formula('sign', sign, x)
    return (x > 0) - (x < 0)


def min(a, b):
    """The smaller of two values.

    Exactly two arguments: OpenSCAD's min accepts a vector or a varying
    number of arguments depending on version and JavaScript's is
    variadic, so two is the arity every runtime agrees on. A three-way
    minimum is `min(min(a, b), c)`.
    """
    face = _face('min', a, b)
    if face == 'symbolic':
        return _symbolic_call('min', a, b)
    if face == 'formula':
        return _formula('min', min, a, b)
    return _min(a, b)


def max(a, b):
    """The larger of two values; exactly two arguments, as `min`."""
    face = _face('max', a, b)
    if face == 'symbolic':
        return _symbolic_call('max', a, b)
    if face == 'formula':
        return _formula('max', max, a, b)
    return _max(a, b)


##############################################
# Compositions
#
# No dimension rule of their own, and exactly one definition each: the
# declared face is the same composition the numeric and symbolic ones
# are, so a change here cannot make the three disagree.


def clamp(x, low, high):
    """`x` held between `low` and `high`."""
    return min(max(x, low), high)


def clamp01(x):
    """`x` held between 0 and 1. Four projects wrote this as
    `(|x| - |x - 1| + 1) / 2` over `sqrt(x * x)`, for a `min`/`max` the
    viewer's evaluator and OpenSCAD both had all along."""
    return clamp(x, 0.0, 1.0)


def ramp(x, start, end):
    """How far `x` has travelled from `start` to `end`, held in [0, 1]:
    0 at and before `start`, 1 at and after `end`."""
    if (not _is_symbolic(start) and not _is_formula(start)
            and not _is_symbolic(end) and not _is_formula(end)
            and start == end):
        raise ValueError(
            f"ramp(x, {start!r}, {end!r}): the two ends are the same value, "
            f"so the ramp has no width to travel over.")
    return clamp01((x - start) / (end - start))


def lerp(a, b, u):
    """`a` at u=0, `b` at u=1, straight through -- and beyond, since
    this does NOT clamp. `ramp` and `piecewise` are the clamped ones."""
    return a + (b - a) * u


def wrap(value, period=360.0):
    """`value` folded into (-period/2, period/2]: wrap(180) == 180,
    wrap(181) == -179, wrap(-180) == 180.

    Built on `ceil`, not on a modulo: OpenSCAD has no mod() function,
    and Python's `%` takes the sign of the divisor where OpenSCAD's and
    JavaScript's `%` take the sign of the dividend.
    """
    if not _is_symbolic(period) and not _is_formula(period):
        # `isinstance(True, int)` is True, and a period of True would
        # silently fold everything into (-0.5, 0.5].
        if (isinstance(period, bool)
                or not isinstance(period, (int, float))
                or period <= 0):
            raise ValueError(
                f"wrap(value, {period!r}): a period is a positive number of "
                f"units per turn.")
    return value - period * ceil((value - period / 2) / period)


def piecewise(x, points):
    """Linear interpolation through (x, y) waypoints, held flat at the
    first y below the first waypoint and at the last y above the last.

    A sum of clamped ramps, so it has no branch and is exact at every
    waypoint. Its cost is length: n waypoints put n - 1 clamp terms on
    the wire.

    The waypoints' x COORDINATES are plain numbers in strictly
    increasing order: they are the breakpoints, so the shape of the
    expression depends on them and they are authored data, never a
    driver expression. `x` itself and the waypoints' y values may each
    be symbolic or a declared formula, and compose as any other operand
    does.
    """
    points = list(points)
    if len(points) < 2:
        raise ValueError(
            f"piecewise(x, points): {len(points)} waypoint(s) given, and a "
            f"path needs at least two to interpolate between.")
    for (xa, _), (xb, _) in zip(points, points[1:]):
        if not isinstance(xa, (int, float)) or not isinstance(xb, (int, float)):
            raise ValueError(
                f"piecewise(x, points): waypoint positions are plain "
                f"numbers, got {xa!r} and {xb!r}.")
        if xb <= xa:
            raise ValueError(
                f"piecewise(x, points): the waypoints at {xa!r} and {xb!r} "
                f"do not increase, so the path doubles back or has no width "
                f"there.")
    result = points[0][1]
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        result = result + (yb - ya) * clamp01((x - xa) / (xb - xa))
    return result


def bump(u):
    """A smooth 0-1-0 pulse over u in [0, 1], zero outside: 16p^2(1-p)^2
    over p = clamp01(u). Zero slope at each end, exactly 1 at u = 0.5.

    A polynomial rather than `sin(180 * clamp01(u))^2`, because `sin`
    requires an Angle and a pulse's argument is dimensionless -- the
    trigonometric form has no declared face at all. A project wanting
    that exact curve writes the `sin` out; this one is a pulse, and
    exact rational arithmetic every runtime agrees on with no
    transcendental call.
    """
    p = clamp01(u)
    return 16 * p * p * (1 - p) * (1 - p)


##############################################
# Vector helpers
#
# Composition over the scalar functions above and nothing else, so a
# symbolic component or a declared formula rides through untouched --
# which is what the projects' own copies could not do, two of them
# having been written against Python's stdlib and so numeric-only.
# Angles are degrees, positive counter-clockwise, as everywhere else.


def polar(radius, angle):
    """The point at `radius` on the ray `angle` about the origin."""
    return (radius * cos(angle), radius * sin(angle))


#: The default centre of `turn`, recognised by identity so a turn about
#: the origin builds no subtraction at all -- which keeps the expression
#: short on the wire, and keeps a turn of a declared Length from meeting
#: a bare dimensionless 0.0.
_ORIGIN = (0.0, 0.0)


def turn(point, angle, about=_ORIGIN):
    """A 2D `point` turned by `angle` about the centre `about`."""
    c, s = cos(angle), sin(angle)
    if about is _ORIGIN:
        return (point[0] * c - point[1] * s,
                point[0] * s + point[1] * c)
    dx = point[0] - about[0]
    dy = point[1] - about[1]
    return (about[0] + dx * c - dy * s,
            about[1] + dx * s + dy * c)


def rotate_x(point, angle):
    """A 3D `point` turned by `angle` about the X axis, right-handed."""
    c, s = cos(angle), sin(angle)
    return (point[0],
            point[1] * c - point[2] * s,
            point[1] * s + point[2] * c)


def rotate_y(point, angle):
    """A 3D `point` turned by `angle` about the Y axis, right-handed."""
    c, s = cos(angle), sin(angle)
    return (point[0] * c + point[2] * s,
            point[1],
            point[2] * c - point[0] * s)


def rotate_z(point, angle):
    """A 3D `point` turned by `angle` about the Z axis, right-handed."""
    c, s = cos(angle), sin(angle)
    return (point[0] * c - point[1] * s,
            point[0] * s + point[1] * c,
            point[2])


__all__ = [
    'SYMBOLIC_BUILTINS',
    'sin', 'cos', 'tan',
    'asin', 'acos', 'atan', 'atan2',
    'sqrt',
    'abs', 'floor', 'ceil', 'sign', 'min', 'max',
    'clamp', 'clamp01', 'ramp', 'lerp', 'wrap', 'piecewise', 'bump',
    'polar', 'turn', 'rotate_x', 'rotate_y', 'rotate_z',
]
