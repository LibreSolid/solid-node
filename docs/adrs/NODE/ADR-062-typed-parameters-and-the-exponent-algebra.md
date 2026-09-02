# ADR-062: Typed Parameters and the Exponent Algebra

**Status:** Accepted
**Date:** 2026-09-01
**Depends on:**
- [ADR-061: A Call in a Node Class Body Is a Declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-022: Cross-Runtime Degree Trig Parity for $t Expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md) — the degree-trig discipline the `Angle` kind makes a type fact

## Context and Problem Statement

A parameter declared in a class body is a symbolic token. Formulas over tokens
— `piston_diameter = bore - 2 * wall_clearance` — replace the derived values
projects froze as comment-documented constants (`PISTON_DIAMETER = 29.4  # bore
− 2 × 0.3`) and the hand-rolled validity checks of a root-parameter dataclass
(windmill's `parameters.py`: 27 of them). The question is what the formula
layer checks, and how far it reaches.

The corpus answers the second question against the reference's first draft:
windmill's gear layer derives `input_pitch_angle` with `atan`,
`outer_cone_distance` with `sqrt`, and `drive_axis_y` with `cos`, and those
values feed the bevel gear children. Arithmetic alone would have left that
parent with a hand-written `__init__`.

## Decision Drivers

- Catch mechanical mistakes at the earliest moment they are expressible: on
  `import`, before any geometry exists.
- Never make a value inexpressible; only inconvenient.
- Keep the engine small — the framework already fixes millimetres and degrees,
  so unit conversion has no place here.
- Stay extensible without the framework enumerating kinds.

## Considered Options

1. **Dimensions as exponent vectors; kinds as named points in that space;
   functions with their own exponent rules; no unit conversion** (chosen)
2. An enumeration of kinds with a hand-written result table
3. A full units library
4. Untyped parameters: identity and propagation only, no checking

## Decision Outcome

Chosen: **a quantity is a mapping from axis to integer exponent, and the
algebra is arithmetic on exponents.** Multiplication adds them, division
subtracts them, an integer power scales them, and addition, subtraction,
negation and comparison require equality. `Length` is `{'L': 1}`, `Angle`
`{'A': 1}` — its own quasi-dimension, so `phase + rotor_fraction` is refused
and trigonometry can demand an angle — and `Count`, `Ratio` and plain numbers
are `{}`. A mismatch raises `DimensionError` in the class body, on `import`.

The functions of `solid_node.math` gain a third face beside their numeric and
symbolic-time modes: on a token or formula they return a formula carrying the
function's rule — `sqrt` needs even exponents and halves them, `sin`/`cos`/
`tan` need an `Angle` and return dimensionless, the inverse functions take
dimensionless and return an `Angle`. The same names, so a gear layer reads as
it did in the dataclass.

Closure follows from the representation: `Length * Length` is a valid `{'L':
2}` whether or not anyone names an `Area`, and a project extends the ontology
by subclassing `Quantity` with its own mapping (`Torque = {'M': 1, 'L': 2,
'T': -2}`). The engine never lists kinds. `Scalar` is unchecked and any
operation involving one stays unchecked; `.value` on any expression yields the
unchecked form. `Flag` is outside the algebra entirely. Comparisons are refused
in a declaration: they belong in `render()`, on resolved values.

The same formula tree runs twice with one implementation — dimensions at class
definition, values at instantiation — and by the time any `render()` runs every
parameter is a plain `float`, `int` or `bool`. Coercion is part of resolution
(`Piston(diameter=30)` and `Piston(diameter=30.0)` are one part), constraints
(`min=`, `max=`, integrality) are checked then, and a declaration without a
default fails at instantiation — never at class definition — when neither the
parent nor the caller supplies it. A parameter is a data descriptor that
refuses assignment and refuses to shadow a base attribute, following
`DriverDeclaration` (ADR-056).

### What it does not claim

The algebra catches *dimensional* mistakes: wrong formula shape, forgotten
factor, mixed kinds. `Count` and `Ratio` share the dimensionless exponent, so
`teeth + fraction` passes, by decision — giving `Count` an axis would refuse
`teeth * module` yielding a plain length. Geometric and mechanical checks
(interference, clearance direction) are a later, second tier on the same
formula layer.

## Consequences

- Windmill's 27 validity checks reduce to declarations with `min=`/`max=` and
  a handful of formulas; the enumerable declarations are what the command line
  parses `--set` against (spec `cli`).
- `solid_node/math.py` imports the declaration layer on use, only when an
  argument is neither a number nor a symbolic value, so every other path pays
  nothing.
- A `Choice` kind was in the reference but never ratified; `Flag` is the only
  selector until a project shows the case.
- A `Flag` flows to a declared child like a numeric token, resolved to the
  parent's boolean at realization (change `declarative-node-api-fixes`); it
  still takes part in no formula and has no `.value`. Guards over several
  parameters at once are `check()` (ADR-065), not declarations.
- Trig in a declaration is degree trig, the same convention as `$t`
  expressions (ADR-022): there is one angle unit in the framework.

## References

- `solid_node/node/declarative.py` — `Expression`, `Formula`, `Quantity`,
  the kinds, `function_formula`, `resolve_parameters`
- `solid_node/math.py` — the formula face of each function
- `tests/test_declarative_algebra.py`
- OpenSpec change `declarative-node-api`, capability `declarative-nodes`
