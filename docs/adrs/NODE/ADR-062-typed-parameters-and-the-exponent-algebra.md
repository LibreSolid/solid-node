# ADR-062: Typed Parameters and the Exponent Algebra

**Status:** Accepted
**Date:** 2026-09-01
**Amended:** 2026-09-04 — the parameter vocabulary moved to its own
top-level module, `solid_node.parameters`
**Depends on:**
- [ADR-061: A Call in a Node Class Body Is a Declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-022: Cross-Runtime Degree Trig Parity for $t Expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md) — the degree-trig discipline the `Angle` kind makes a type fact

## Amendment (2026-09-04)

**Where these names are imported from is part of the decision, and it was
not stated.** The kinds shipped as exports of `solid_node.node`, beside
every node base class, so `from solid_node.node import CadQueryNode,
Length` gave a reader no way to tell that one of those names is a kind of
part and the other a knob on the machine. That distinction is the whole
content of the layer this ADR defines: a parameter is fixed for the life
of an instance, enters the build identity and may decide structure,
which is precisely what a driver is not.

So the vocabulary moves to **`solid_node/parameters.py`**, a top-level
module: `Quantity`, `Length`, `Angle`, `Count`, `Ratio`, `Scalar`,
`Flag`, `Expression`, `Formula`, `declared_parameters`, `DimensionError`
and `ParameterError`, together with the `Declaration` descriptor the
other declarations follow. `solid_node.node` no longer exports any of
them, with no re-export and no deprecation path — the surface had not
been released, and a second working path restores the ambiguity the move
exists to remove.

The module is chosen top-level, not `solid_node/node/parameters.py`,
because the framework's public surface is already split by concern above
the node package: `solid_node.simulation` holds drivers and instructions,
`solid_node.test` the test case. A parameter is a peer of those, and only
at that level does an import block state the contrast it is there to
state — parameters build the machine, drivers drive it:

    from solid_node.node import AssemblyNode, CadQueryNode
    from solid_node.parameters import Length, Flag
    from solid_node.simulation import Driver

The cut follows the existing dependencies rather than the topic. Three
names cross the boundary and all in one direction, structure importing
parameters: `Declaration`, which the declaring namespace tests against;
`evaluate`, which a child declaration resolves its arguments with; and
`declared_parameters`, which construction reads. Nothing in the
parameter half needs a name from the structure half, so the new module
imports nothing at all — not the framework, not a third party — which is
what makes it free to sit at the top of every node module in every
project, and why its names are bound eagerly where the node and
simulation packages defer theirs. `solid_node/node/declarative.py` keeps
the structural half: the child and repeat declarations, `NodeMeta`, the
declaring namespace, realization, and the structure errors.

The consequence recorded below about `solid_node/math.py` importing the
declaration layer *on use* is superseded: it now imports
`solid_node.parameters` at module scope, sideways rather than down into
the node package, because there is no longer a cost to defer.

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

- `solid_node/parameters.py` — `Declaration`, `Expression`, `Formula`,
  `Quantity`, the kinds, `function_formula`, `declared_parameters`
- `solid_node/node/declarative.py` — `resolve_parameters` and the
  structural declarations that borrow this layer
- `solid_node/math.py` — the formula face of each function
- `tests/test_declarative_algebra.py`
- OpenSpec changes `declarative-node-api` and `build-parameters-module`,
  capability `declarative-nodes`
