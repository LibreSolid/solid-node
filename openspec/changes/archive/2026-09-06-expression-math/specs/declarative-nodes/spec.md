## MODIFIED Requirements

### Requirement: Dimension algebra over declared parameters

The system SHALL treat every declared quantity as a vector of dimension
exponents and SHALL check arithmetic over tokens and formulas by those
exponents: multiplication adds exponents, division subtracts them, an
integer power scales them, and addition, subtraction and unary negation
require equal exponents. `Length` and `Angle` SHALL be distinct axes;
`Count`, `Ratio` and plain numbers SHALL share the dimensionless exponent.
A dimension mismatch SHALL raise at class definition, before any instance
exists. The result of a formula SHALL be a valid quantity whether or not a
named kind exists for its exponents.

The `solid_node.math` functions SHALL accept tokens and formulas. Each
function that is a PRIMITIVE — one the module emits as a call in symbolic
mode — SHALL carry a dimension rule of its own:

- `sqrt` SHALL require even exponents and halve them.
- `sin`, `cos` and `tan` SHALL require an `Angle` and return a dimensionless
  quantity; `asin`, `acos`, `atan` and `atan2` SHALL require dimensionless
  arguments and return an `Angle`, and `atan2` SHALL require its two
  arguments to have equal dimensions.
- `abs` SHALL accept any dimension and preserve it.
- `min` and `max` SHALL require their two arguments to have equal dimensions
  and SHALL return that dimension.
- `floor` and `ceil` SHALL require a dimensionless argument and return a
  dimensionless quantity, because they compare a quantity against the
  integers and an integer bears no dimension; a caller who wants the whole
  number of steps in a length writes `floor(length / step)`, which states
  the unit the comparison assumes instead of hiding it.
- `sign` SHALL accept any dimension and return a dimensionless quantity,
  because it compares against zero, which every dimension shares.

Every other function the module exports is a COMPOSITION of those primitives
and ordinary arithmetic, and SHALL carry no dimension rule of its own. Its
declared face SHALL be the same composition its numeric and symbolic faces
are, so its dimension behaviour follows from the primitives' rules above and
from the algebra's own rules for addition, multiplication and division. The
behaviour a caller therefore experiences is:

- `clamp` requires its three arguments to have equal dimensions and returns
  that dimension, which is `min`'s and `max`'s rule applied twice.
- `clamp01` and `bump` require a dimensionless argument and return a
  dimensionless quantity; `ramp` requires its three arguments equal and
  returns a dimensionless quantity. `bump` is a polynomial over `clamp01` for
  exactly this reason: built on the degree trigonometry it would have no
  declared face at all, because `sin` requires an `Angle` and a pulse's
  argument is dimensionless.
- `lerp` requires its first two arguments equal and its third dimensionless,
  and returns the first two's dimension.
- `wrap` requires its value and its period equal and returns that dimension.
  Its default period is a plain number, so the declared face needs the period
  stated as a quantity — `wrap(bearing, Angle(360.0))`; `wrap(bearing)` on
  the default raises, exactly as `clamp01(length)` does.
- `piecewise` requires every waypoint's first coordinate to share the
  dimension of `x` and every waypoint's second coordinate to share one
  dimension with the others, and returns that second dimension.

Because a plain number is dimensionless, a bound, a period or a centre stated
as a bare number against a dimensioned quantity — `clamp01(length)`,
`max(length, 0.0)`, `wrap(angle)` on its default period, `turn(point, angle,
about=(0.0, 0.0))` on a point of quantities — SHALL raise, in the same way
`length + 1` raises today. Each is stated with a quantity instead:
`clamp(length, Length(0.0), Length(1.0))`, `wrap(angle, Angle(360.0))`, and
for a turn about the origin the default centre, which builds no centring
terms and so meets no bare zero at all.

The same names SHALL keep working on plain numbers and on symbolic time and
driver expressions exactly as they do today.

`Scalar` SHALL be unchecked: any operation involving a `Scalar` yields an
unchecked result, and `.value` on any token or formula SHALL yield the
unchecked form of the same expression. `Flag` SHALL be outside the
algebra: arithmetic on it raises. Comparison operators on tokens SHALL
raise. A project SHALL be able to extend the ontology by subclassing a kind
with its own exponent vector. The algebra checks dimensions only and SHALL
NOT convert units.

#### Scenario: Mixed kinds fail on import

- **WHEN** a class body computes `bore + pressure_angle` where `bore` is a
  `Length` and `pressure_angle` an `Angle`
- **THEN** class definition raises a dimension error naming both operands

#### Scenario: Products and quotients close

- **WHEN** a class body computes `teeth * module` (`Count` × `Length`),
  `bore / stroke` (`Length` ÷ `Length`) and `bore * bore`
- **THEN** the results are respectively a length, a dimensionless quantity
  and a quantity of length exponent two, and each is usable in a further
  formula or as a child argument

#### Scenario: Functions carry their own rules

- **WHEN** a class body computes `sqrt(z1 * z1 + z2 * z2) * module / 2`,
  `atan(z1 / z2)` and `cos(pitch_angle) * cone_distance` with the
  `solid_node.math` names
- **THEN** the results are respectively a length, an angle and a length,
  and `sqrt(bore)` or `cos(bore)` raises a dimension error at class
  definition

#### Scenario: A bound preserves its quantity

- **WHEN** a class body computes `clamp(reach, minimum_reach, maximum_reach)`
  over three declared `Length` parameters, and `abs(offset)` over a declared
  `Length`
- **THEN** both results are lengths, and `min(bore, pressure_angle)` raises a
  dimension error naming both operands

#### Scenario: A pulse of a declared ratio is a dimensionless formula

- **WHEN** a class body computes `bump(phase)` over a declared `Ratio`, and
  `bump(bore)` over a declared `Length`
- **THEN** the first is a dimensionless formula that evaluates on the
  instance's resolved value, and the second raises a dimension error naming
  `bore`

#### Scenario: A declared period folds a declared angle

- **WHEN** a class body computes `wrap(bearing, Angle(360.0))` and
  `wrap(bearing)` over a declared `Angle`
- **THEN** the first is a derived `Angle` and the second raises a dimension
  error naming the angle and the plain default period

#### Scenario: A composition carries no rule of its own

- **WHEN** a class body computes `clamp01(bore)` or `max(bore, 0.0)` over a
  declared `Length`
- **THEN** each raises a dimension error naming the length and the plain
  number, because a bare number is dimensionless and the primitive beneath
  requires equal dimensions — the same refusal `bore + 1` already gives — and
  the error comes from `min`/`max`, not from a rule registered for the
  composition

#### Scenario: A whole-number function refuses a dimensioned argument

- **WHEN** a class body computes `floor(bore)` over a declared `Length`
- **THEN** class definition raises a dimension error naming `bore` and its
  dimension, while `floor(bore / pitch)` over two lengths succeeds and is
  dimensionless

#### Scenario: A project kind extends the ontology

- **WHEN** a project subclasses the quantity base with exponents for torque
  and declares a parameter of that kind
- **THEN** the parameter participates in the algebra with those exponents
  and a `Length` cannot be added to it

#### Scenario: The escape hatch never blocks

- **WHEN** a class body computes `bore.value + pressure_angle.value`
- **THEN** class definition succeeds and the result is an unchecked
  quantity
