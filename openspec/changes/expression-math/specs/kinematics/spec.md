## MODIFIED Requirements

### Requirement: Degree-convention dual-mode math

The system SHALL provide `solid_node/math.py` as the single `$t` math
semantics — OpenSCAD's degree conventions (`sin(90) == 1.0`, `asin(0.5) ==
30.0`). Each function SHALL compute numerically when given a real number and
emit an equivalent deferred OpenSCAD expression when given a symbolic value.
Every runtime that evaluates `$t` and driver expressions (`math.py`, OpenSCAD,
and the one TypeScript evaluator in the viewer package) reproduces these
semantics function-for-function, treating `^` as exponentiation. That
agreement is enforced by the parity fixture, whose expected values are
producer values.

The module SHALL export, beyond the degree trigonometry and `sqrt`:

- **Direct builtins**, each emitting the OpenSCAD builtin of the same name in
  symbolic mode: `abs`, `floor`, `ceil`, `sign` of one argument, and `min`
  and `max` of exactly two arguments.
- **Compositions** over those primitives and the existing functions:
  `clamp(x, low, high)`, `clamp01(x)`, `ramp(x, start, end)`,
  `lerp(a, b, u)`, `wrap(value, period=360.0)`, `piecewise(x, points)` and
  `bump(u)`.

`clamp` SHALL return `x` bounded below by `low` and above by `high`;
`clamp01` SHALL be `clamp(x, 0.0, 1.0)`. `ramp` SHALL be the fraction of the
way `x` has travelled from `start` to `end`, clamped to `[0, 1]`, and SHALL
raise when `start` and `end` are equal numbers. `lerp` SHALL be
`a + (b - a) * u`, unclamped. `wrap` SHALL fold `value` into the half-open
interval `(-period/2, period/2]`, so `wrap(180) == 180`, `wrap(-180) == 180`
and `wrap(181) == -179`, for a `period` that is a positive number. `piecewise` SHALL interpolate
linearly through a sequence of at least two `(x, y)` waypoints whose `x`
coordinates are plain numbers in strictly increasing order, holding the first
`y` below the first waypoint and the last `y` above the last, and SHALL raise
naming the offending waypoints otherwise. `bump` SHALL be the smooth polynomial pulse
`16 p²(1-p)²` over `p = clamp01(u)`: zero at and below `0`, one at `0.5`,
zero at and above `1`, zero outside `[0, 1]`, and with zero slope at each
end. It SHALL NOT be built on the degree trigonometry, because `sin` requires
an `Angle` and a pulse's argument is dimensionless, which would leave the
function with no declared face.

A composition SHALL emit only expressions every runtime evaluates
identically. A function whose runtimes disagree SHALL NOT be exported: in
particular the module SHALL NOT export a rounding function, because OpenSCAD
rounds a half away from zero, JavaScript's `Math.round` rounds a half toward
positive infinity and Python rounds a half to even; and it SHALL NOT export a
modulo function, because OpenSCAD spells the operation as the `%` operator
rather than a `mod()` function and Python's `%` takes the sign of the divisor
where OpenSCAD's and JavaScript's take the sign of the dividend.

A composition's declared face is the composition itself, so a bound or a
period stated as a bare number against a dimensioned quantity SHALL be
refused there, in the same way `length + 1` is refused: `clamp01(length)`,
`max(length, 0.0)` and `wrap(angle)` on its bare default period all raise. A
declared call states the second operand as a quantity — `wrap(angle,
Angle(360.0))` — and the numeric and symbolic faces are unaffected, plain
numbers carrying no dimension to disagree about.

These names deliberately shadow Python builtins of the same name in a module
that imports them, exactly as `from math import floor` does; the module SHALL
retain its own access to the shadowed builtins.

A call that mixes a symbolic value with a declared parameter token or formula
SHALL raise, naming both operands, rather than rendering the declaration into
the emitted expression string.

#### Scenario: Dual-mode trig

- **WHEN** `math.sin` is called with a float under `set_keyframe`
- **THEN** it returns the numeric degree-convention result
- **WHEN** the same call receives a symbolic `$t` expression
- **THEN** it returns an OpenSCAD expression string for deferred evaluation

#### Scenario: A direct builtin emits the builtin's own call

- **WHEN** `floor`, `abs`, `ceil`, `sign`, `min` and `max` are each called
  with a symbolic argument
- **THEN** each returns a symbolic value whose string is exactly that
  OpenSCAD builtin applied to the rendered arguments — `floor($t)`,
  `min($t, 1.0)` — and never a `sqrt`-based stand-in

#### Scenario: The same function computes numerically

- **WHEN** the same six functions are called with plain numbers, including a
  negative argument
- **THEN** each returns the standard library's own result, and `floor(-2.5)`
  is `-3`, `ceil(-2.5)` is `-2` and `sign(0)` is `0`, agreeing with what
  OpenSCAD and the browser compute for the symbolic form

#### Scenario: A clamp needs no square root

- **WHEN** a project clamps a symbolic driver expression to `[0, 1]`
- **THEN** `clamp01` returns `min(max(<expr>, 0.0), 1.0)` and the project
  needs neither `sqrt(x * x)` nor a hand-rolled `OpenSCADConstant`

#### Scenario: An angle folds into one turn

- **WHEN** `wrap` is called with `180`, `181`, `-180`, `-181` and `540`
- **THEN** the results are `180`, `-179`, `180`, `179` and `180` — both edges
  of the interval pinned, the upper one closed and the lower one open — and
  the symbolic form of the same call evaluates to the same numbers at the
  same inputs

#### Scenario: A waypoint path interpolates and clamps

- **WHEN** `piecewise` is called with waypoints `[(0, 0), (10, 4), (20, 6)]`
  at `-5`, `0`, `5`, `15`, `20` and `40`
- **THEN** the results are `0`, `0`, `2`, `5`, `6` and `6`

#### Scenario: A malformed waypoint sequence is refused

- **WHEN** `piecewise` is called with one waypoint, or with waypoints whose
  `x` coordinates do not strictly increase
- **THEN** it raises naming the offending waypoints, at call time, rather
  than emitting an expression that divides by zero

#### Scenario: A pulse rises and falls

- **WHEN** `bump` is called at `-1`, `0`, `0.25`, `0.5`, `1` and `2`
- **THEN** the results are `0`, `0`, `0.5625`, `1`, `0` and `0` — the interior
  value pinning the curve's shape and not only its endpoints and peak — and
  the symbolic form agrees at every sampled value

#### Scenario: A declared period folds a declared angle

- **WHEN** a class body computes `wrap(bearing, Angle(360.0))` over a
  declared `Angle`, and `wrap(bearing)` on the bare default period
- **THEN** the first is a derived `Angle` and the second raises a dimension
  error, because the default period is a plain number and a plain number is
  dimensionless — the same refusal `clamp01(length)` gives

#### Scenario: Numeric and symbolic agree over the new vocabulary

- **WHEN** an expression composed from the new functions is built once
  symbolically and once numerically at a sampled instant
- **THEN** evaluating the symbolic string at that instant equals the numeric
  result

#### Scenario: A mixed symbolic and declared call is refused

- **WHEN** `min` is called with a symbolic `$t` expression and a declared
  parameter token
- **THEN** it raises naming both operands, rather than rendering the
  declaration's `repr()` into the expression

## ADDED Requirements

### Requirement: Expression-safe vector helpers

The system SHALL export from `solid_node.math` a small set of vector helpers
built only from that module's own scalar functions, so a symbolic value or a
declared parameter formula in any component rides through unchanged. Each
takes and returns plain tuples of scalars, and every angle is in degrees,
positive counter-clockwise, matching the node transform API and OpenSCAD.

- `polar(radius, angle)` SHALL return the 2-tuple `(radius * cos(angle),
  radius * sin(angle))`.
- `turn(point, angle, about=...)` SHALL return the 2-tuple that is the 2D
  `point` turned by `angle` about the centre `about`, whose default is the
  ORIGIN. Turning about that default SHALL build no centring terms at all,
  so the expression stays short and a `point` of declared quantities never
  meets a dimensionless zero. An explicitly given centre SHALL share the
  point's dimension, `(0.0, 0.0)` included.
- `rotate_x(point, angle)`, `rotate_y(point, angle)` and `rotate_z(point,
  angle)` SHALL each return the 3-tuple that is the 3D `point` turned by
  `angle` about that axis, right-handed.

These helpers SHALL introduce no dimension rule of their own: their
dimensions follow from the scalar functions they compose.

#### Scenario: A helper survives a symbolic component

- **WHEN** `rotate_x` is called on a point whose components are numbers and
  an angle that is a symbolic driver expression
- **THEN** each returned component is a symbolic expression composed from
  `sin` and `cos` calls, and nothing raises

#### Scenario: A helper agrees with itself numerically

- **WHEN** `turn((10, 0), 90)` and `turn((10, 0), 90, about=(10, 0))` are
  evaluated
- **THEN** the results are `(0, 10)` and `(10, 0)` within floating-point
  tolerance

#### Scenario: A turn about the default centre builds no centring terms

- **WHEN** `turn` is called with a symbolic angle and no centre
- **THEN** each component is the rotation alone — no `- 0.0` and no `0.0 +`
  — and a `point` of declared `Length` quantities turns about the default
  centre without a dimension error, while passing `about=(0.0, 0.0)`
  explicitly against that point raises one

#### Scenario: A helper carries declared dimensions

- **WHEN** a class body computes `polar(radius, angle)` from a declared
  `Length` and a declared `Angle`
- **THEN** both components are formulas of length dimension, and
  `polar(radius, radius)` raises a dimension error at class definition

### Requirement: The parity corpus covers every symbolic function

The system SHALL name, in one place in `solid_node/math.py`, every OpenSCAD
builtin the module may emit as a call, and every function that emits one
SHALL take its name from that inventory rather than spelling it a second
time. That inventory is the source of truth for what the corpus must cover;
no consumer SHALL keep a second, hand-maintained list of the same names.

The system SHALL pin every function `solid_node.math` can emit symbolically
in the cross-runtime parity corpus, so no exported symbolic name reaches a
published document without a fixture case behind it. The corpus SHALL keep
its existing discipline: an expected value is a producer value, obtained by
serializing one node tree twice — once bound to a numeric snapshot and once
symbolically — and pairing the two walks by structure, never by evaluating an
expression a second way.

Adding a symbolic function to the module SHALL therefore add at least one
case exercising it to the corpus. The corpus SHALL be extended by adding a
new tree beside the existing one rather than by altering the existing cases,
so a regeneration changes no expected value that was already pinned.

#### Scenario: Every emitted name is pinned

- **WHEN** the parity fixture is regenerated
- **THEN** it carries at least one case whose expression contains each name
  in the module's own inventory of emitted builtins, and the check that says
  so reads that inventory rather than a list of its own

#### Scenario: A new emitted name cannot slip through

- **WHEN** a function emitting a builtin absent from the corpus is added to
  the module and the fixture is regenerated
- **THEN** the regeneration fails naming the uncovered builtin

#### Scenario: Regeneration leaves the existing corpus alone

- **WHEN** the fixture is regenerated after the new corpus is added
- **THEN** every case the previous fixture carried is present unchanged,
  under the same key and with the same expected value
