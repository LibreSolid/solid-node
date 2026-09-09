# declarative-nodes Specification

## Purpose

Authoring a node by declaration: typed parameters (`Length`, `Angle`,
`Count`, `Ratio`, `Flag`, `Scalar`) with a dimension algebra checked on
import, derived parameters as class-body formulas, children declared by
constructing them in the class body with literal lists and `repeat()`,
realization top-down from the root with identity derived by the
framework, an internal `render()` that may return nothing, and `omit()`.
Encodes ADR-061 (a call in a class body is a declaration), ADR-062
(typed parameters and the exponent algebra), ADR-063 (identity from
resolved declared values) and ADR-064 (an internal render that returns
nothing, with structural omission). Additive beside the constructor form
the `node-model` capability specifies.

Code: `solid_node/node/declarative.py`, `solid_node/node/base.py`,
`solid_node/node/internal.py`, `solid_node/math.py`.
## Requirements
### Requirement: Typed parameter declarations

The system SHALL let a node class declare its parameters as class attributes
of typed kinds: `Length` (a linear dimension), `Angle` (in degrees), `Count`
(an integer), `Ratio` (a dimensionless fraction), `Flag` (a boolean) and
`Scalar` (an unchecked number). Those kinds, the `Quantity` base a project
subclasses to extend the ontology, the enumerator over a class's
declarations, and the errors a bad declaration raises SHALL be imported from
one dedicated module for build parameters, separate from the module that
exports node classes. A build parameter SHALL NOT be reachable from the node
package: reading one there SHALL raise as any unexported name does.

A declaration SHALL carry an optional
default and optional value constraints (`min=` and `max=` on numeric kinds).
A declaration without a default SHALL be supplied by the parent's
declaration or by the caller; instantiating without a value for it SHALL
raise naming the class and the parameter, never at class definition.

Read on an instance, a declared parameter SHALL be a plain Python value —
`float` for `Length`, `Angle`, `Ratio` and `Scalar`, `int` for `Count`,
`bool` for `Flag` — never a token. Read on the class it SHALL be the
symbolic token usable in formulas. Assigning to a declared parameter on an
instance SHALL raise. A declaration whose name would shadow a
non-declaration attribute of a base class SHALL be rejected at class
definition. Declared parameters SHALL be enumerable off the class without
instantiating it, base-first, a subclass redeclaration winning.

#### Scenario: A parameter is imported from the parameter module

- **WHEN** a node module declares `bore = Length(30.0, min=0)`
- **THEN** `Length` was imported from the build-parameter module, and the
  same import line does not carry a node class

#### Scenario: The node package does not answer for a parameter

- **WHEN** a module reads a parameter kind, the `Quantity` base or the
  parameter enumerator off the node package
- **THEN** `AttributeError` is raised naming the requested name, exactly as
  for any name that package does not export

#### Scenario: Defaults realize and read as plain values

- **WHEN** a leaf declares `bore = Length(30.0, min=0)` and is constructed
  with no arguments
- **THEN** `self.bore` inside `render()` is the float `30.0`

#### Scenario: A constraint is checked at instantiation

- **WHEN** a node declaring `count = Count(8, min=2)` is constructed with
  `count=1`, or `Count` receives `2.5`, or a `Flag` receives `1`
- **THEN** construction raises naming the class, the parameter and the
  violated constraint

#### Scenario: A parameter without a default must be supplied

- **WHEN** a node declares `height = Length()` and is constructed without
  `height`, by a parent's declaration or directly
- **THEN** construction raises naming the class and the parameter, and the
  class itself was defined without error

#### Scenario: Assignment is refused

- **WHEN** a `render()` body executes `self.bore = 5`
- **THEN** an error is raised and the declared value is unchanged

#### Scenario: A declaration cannot shadow a base attribute

- **WHEN** a class body declares `name = Length(1.0)` or `time = Angle(0.0)`
- **THEN** class definition raises naming the shadowed attribute

#### Scenario: Declared parameters are enumerable

- **WHEN** a consumer enumerates a class declaring two parameters and one
  derived formula
- **THEN** it receives all three by name with their kinds without
  constructing an instance

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

### Requirement: Derived parameters as class-body formulas

The system SHALL treat a bare formula over declared tokens assigned in a
node class body as a derived parameter: read on an instance it SHALL be the
value of the formula over that instance's resolved parameters, it SHALL be
usable in further formulas and as a child argument, it SHALL NOT be settable
from a parent, a caller or by assignment, and it SHALL be enumerable with
the declared parameters.

#### Scenario: A derived value follows its inputs

- **WHEN** a class declares `bore = Length(30.0)`, `wall = Length(0.3)` and
  `piston_diameter = bore - 2 * wall`, and an instance is realized with
  `bore=32.0`
- **THEN** `self.piston_diameter` reads `31.4`

#### Scenario: A derived parameter cannot be supplied

- **WHEN** that class is constructed with `piston_diameter=20.0`
- **THEN** construction raises naming it as derived

### Requirement: Class-body child declarations

The system SHALL treat a node constructed inside a node class body as a
declaration of a child, never as an instance: the class-body expression
`piston = Piston(diameter=piston_diameter)` records the child class and its
arguments, and each parent instance realizes its own child at construction.
Arguments to a declaration MAY be tokens and formulas, resolved against the
parent instance's values at realization, or plain values passed through;
`name=` passes through. A `Flag` token passed to a declaration SHALL resolve
to the parent instance's boolean at realization, exactly as a numeric token
does. A literal list of declarations SHALL declare enumerated children named
`<attr>-<index>`. A list comprehension in the class body over values the
comprehension can see — module-level names and literals — SHALL declare an
enumerated list exactly as a literal list does; the body is recognized while
the comprehension runs, and class-level names remain invisible to it as
Python defines. `.repeat(count)` on a declaration, where `count` is an
integer or a `Count` token, SHALL declare count-many identical children
named `<attr>-<index>`. Realization SHALL proceed top-down from the root's
bound values in declaration order, and by the time any `render()` runs
every parameter SHALL be a plain value.

A keyword argument whose VALUE is a port or joint declaration SHALL be a
WIRING rather than a parameter: it SHALL NOT be resolved as a parameter,
SHALL NOT be passed to the child's construction, and SHALL NOT enter the
child's identity, because it states which value reaches the child at each
instant and not what geometry is built. Every keyword whose value is not
such a declaration SHALL keep the meaning it has today, including the
`TypeError` an unknown one raises.

A wiring SHALL be validated at class definition, where both ends are
known: the value SHALL be a port or joint declared on the class whose body
holds the declaration, and the keyword SHALL name a port or a joint the
child class declares. A wiring failing either test SHALL be refused at
class definition, naming the declaring class, the child class, the keyword,
and the ports and joints the child does declare.

Two parent instances SHALL never share a realized child. A declared child
whose class is a non-declarative node SHALL be realized by calling its
constructor with the resolved arguments. Reading an attribute off a
declaration in a class body SHALL raise advising that the shared parameter
be declared on this class and passed to both children. Declared children
SHALL be enumerable off the class without instantiating it.

#### Scenario: Each parent realizes its own child

- **WHEN** two instances of a class declaring `piston = Piston()` are
  constructed and one translates its piston
- **THEN** the other instance's piston carries no operation and the two are
  distinct objects

#### Scenario: Tokens flow to children by reference

- **WHEN** `CylinderUnit` declares `bore = Length(30.0)` and
  `piston = Piston(diameter=bore - 0.6)`, and a parent realizes
  `CylinderUnit(bore=32.0)`
- **THEN** the realized piston's `diameter` reads `31.4`

#### Scenario: A flag flows to a child

- **WHEN** a parent declares `fitted = Flag(False)` and
  `supply = PowerSupply(fitted=fitted)`, and is realized with `fitted=True`
- **THEN** the realized supply's `fitted` reads `True`, and realized with
  the default it reads `False`

#### Scenario: A comprehension declares

- **WHEN** a class body assigns `boxes = [Box() for _ in TABLE]` over a
  module-level `TABLE` of two entries
- **THEN** the class declares two children `boxes-0` and `boxes-1`, two
  instances of the class realize distinct boxes, and a `render()` returning
  `None` yields both

#### Scenario: Identical units repeat

- **WHEN** a class declares `count = Count(8)` and
  `units = CylinderUnit(bore=bore).repeat(count)` and is realized with
  `count=6`
- **THEN** `self.units` holds six distinct instances named `units-0`
  through `units-5`, all with the same resolved parameters

#### Scenario: A legacy class is a valid child

- **WHEN** a declarative parent declares `guard = Guard(thickness=wall)`
  where `Guard` defines an ordinary `__init__(self, thickness, name=None)`
- **THEN** realization calls that constructor with the resolved thickness
  and the guard is linked and named as any child

#### Scenario: A sideways read is refused

- **WHEN** a class body declares `piston = Piston()` and then
  `con_rod = ConRod(pin_bore=piston.pin_bore)`
- **THEN** class definition raises naming both attributes and advising that
  the shared parameter be declared on this class and passed to both children

#### Scenario: A wired coordinate is not a parameter

- **WHEN** a class declaring `turn = Revolute(axis=(0, 0, 1), unit='deg')`
  and `index = Count(0)` declares `wheel = Arbor(index=index, turn=turn)`,
  where `Arbor` declares a `Count` parameter `index` and a
  `RotationalPort` `turn`
- **THEN** the realized `Arbor` was constructed with `index` only, its
  resolved parameters carry no `turn`, and two such parents differing only
  in what they bind to `turn` realize arbors sharing one `uniq_id`

#### Scenario: A wiring the child cannot receive fails at class definition

- **WHEN** a class body declares `wheel = Arbor(turn=turn)` where `Arbor`
  declares neither a port nor a joint named `turn`
- **THEN** class definition raises naming the declaring class, `Arbor`,
  `turn`, and the ports and joints `Arbor` declares

#### Scenario: A coordinate of another class is refused

- **WHEN** a class body declares `wheel = Arbor(turn=elsewhere)` where
  `elsewhere` is a port declared on an unrelated class
- **THEN** class definition raises naming the declaring class, the
  keyword and the class the coordinate belongs to

#### Scenario: An unknown keyword is still a TypeError

- **WHEN** a class body declares `wheel = Arbor(spin=1.0)` where `Arbor`
  declares no parameter `spin`
- **THEN** realization raises the `TypeError` it raises today, naming the
  class, the unknown keyword and the declared parameters
### Requirement: Realization at the root and framework-owned identity

The system SHALL realize a declarative root with its defaults when
constructed with no arguments, and SHALL rebind the root's declared
parameters from keyword arguments when given, every derived value and child
following. A declarative class SHALL reject positional arguments and unknown
keyword arguments with a `TypeError` that lists the declared names. Its
`uniq_id` SHALL be derived from the class and the resolved values of its
declared parameters, never from a hand-forwarded map, and `name` SHALL stay
out of it. Repeated identical children SHALL share one `uniq_id` and one
artifact. The loader SHALL construct the root with the caller's overrides,
or with none, and bind declared driver defaults exactly as it does today.

#### Scenario: One number moves the machine

- **WHEN** `Engine(bore=32.0)` is realized where `Engine` passes `bore` to
  `cylinders` and `block`
- **THEN** both subtrees read the same `32.0` and their leaves' `uniq_id`s
  differ from those of `Engine()`

#### Scenario: Unknown and positional arguments are rejected

- **WHEN** a declarative class is constructed as `Piston(31.0)` or
  `Piston(diamter=31.0)`
- **THEN** construction raises `TypeError` naming the class and, for the
  keyword, the unknown name and the declared ones

#### Scenario: Identity is complete by construction

- **WHEN** a declarative leaf with six declared parameters is realized twice
  with one value differing
- **THEN** the two `uniq_id`s differ, and two realizations with equal values
  share one `uniq_id` and one artifact set

#### Scenario: Coercion keeps one artifact per geometry

- **WHEN** a declarative leaf is realized once with `diameter=30` and once
  with `diameter=30.0`
- **THEN** both read `30.0` and share one `uniq_id`

#### Scenario: Repeated units are one part

- **WHEN** eight identical units are realized through `repeat(8)` and built
- **THEN** exactly one artifact set is produced for them and each of the
  eight carries its own placement

### Requirement: Instance checks

The system SHALL call `check()` on a declarative node instance once its
parameters are resolved and before any of its children is realized. An
exception raised by `check()` SHALL refuse the instance and propagate
unchanged, and the refused instance SHALL have realized no child. The base
implementation SHALL do nothing, so a subclass MAY chain `super().check()`.
The framework SHALL NOT call `check()` on a non-declarative instance.

#### Scenario: A cross-parameter guard refuses an instance

- **WHEN** a leaf declares `stem = Length(4.0)` and `stop = Length(6.0)` and
  a `check()` raising `ValueError` when `stop <= stem`, and is constructed
  with `stop=3.0`
- **THEN** construction raises that `ValueError`, and constructing with the
  defaults succeeds

#### Scenario: A refused parent realizes nothing

- **WHEN** an assembly declaring a child and a `check()` that raises is
  constructed
- **THEN** the child's class is never instantiated

#### Scenario: Checks chain

- **WHEN** a subclass defines `check()` calling `super().check()` and its
  base's `check()` raises for the supplied values
- **THEN** construction raises the base's error

### Requirement: An internal render that returns nothing

The system SHALL treat an internal node's `render()` that returns `None` as
returning the realized declared children in declaration order minus those
omitted during that render, so the method's job on a declarative class is
to position and select. Whether this substitution applies SHALL be determined
from the class's child declarations, independently of how many children those
declarations realize for one instance. A declared repeat that realizes zero
children and a render that omits every declared child SHALL therefore expose
an empty list to every consumer. A class with nothing to position SHALL need
no `render()`. A `render()` that returns a list or tuple SHALL keep its
existing contract unchanged. Every consumer of `render()` — the build, the
serializer, the driver walk and state propagation — SHALL see the substituted
list, never `None`. On an assembly the animator sweep SHALL run before the
author's `render()` exactly as it does today. A leaf `render()` returning
`None` SHALL remain an error.

#### Scenario: A grouping node needs no methods

- **WHEN** an `AssemblyNode` subclass declares three children and defines no
  method
- **THEN** rendering it yields those three children, linked and named after
  their attributes, and the serialized document lists them

#### Scenario: Positioning without a return

- **WHEN** an assembly's `render()` rotates a child by an expression in
  `self.time` and returns nothing, and the assembly is rendered at two
  keyframes
- **THEN** the child carries exactly one rotation after each render, for
  that instant, and both renders yield the declared children

#### Scenario: A returned list keeps its contract

- **WHEN** a declarative class's `render()` returns a hand-picked list
- **THEN** that list is what the framework builds, and declared children
  absent from it are not built

#### Scenario: A fusion positions its declared parts

- **WHEN** a `FusionNode` subclass declares two children and its `render()`
  translates one and returns nothing
- **THEN** the fusion is composed from both children with that placement

#### Scenario: A zero repeat remains declared structure

- **WHEN** a methodless `AssemblyNode` declares
  `parts = Part().repeat(count)` and its resolved `count` is zero
- **THEN** `render()` returns `[]`, assembly succeeds, and every consumer sees
  an empty child list rather than `None`

#### Scenario: Every declared child is omitted

- **WHEN** an `AssemblyNode` omits all of its declared children during its
  once-only render
- **THEN** assembly succeeds with no linked children and serialization
  publishes `children: []`

### Requirement: Structural omission

The system SHALL let `render()` call `omit()` on a declared child to remove
it from the machine for that realization: an omitted child SHALL NOT be
linked, built, exported, fused or serialized. Every child is always
declared; `render()` selects presence. Structure SHALL vary with parameters
only: `omit()` called during `simulate()` SHALL raise `StructureError`, and
on the legacy path, where `render()` re-runs, a render whose omitted set
differs from that instance's first render SHALL raise naming the node and
both sets. On a once-only `render()` the omitted set of the first run is the
instance's structure. An omitted list member SHALL leave its siblings'
indices and identities unchanged.

#### Scenario: A flag removes a part

- **WHEN** `Windmill` declares `guard_installed = Flag(True)` and its
  `render()` omits `self.guard` when the flag is false, and it is realized
  with `guard_installed=False`
- **THEN** the rendered children exclude the guard, the build produces no
  artifact for it, and the serialized document does not list it

#### Scenario: Omission under a fused solid

- **WHEN** a `FusionNode` subclass omits one declared child in `render()`
- **THEN** the fused solid is composed from the remaining children only

#### Scenario: Time cannot change structure

- **WHEN** a `render()` omits a child under a condition on a time-derived
  value and the assembly is rendered at two keyframes where the condition
  differs
- **THEN** the second render raises naming the node and the two omitted
  sets

#### Scenario: Indices never renumber

- **WHEN** `units-3` of eight repeated units is omitted
- **THEN** `units-4` is still named `units-4` and keeps its `uniq_id`

#### Scenario: Simulate cannot omit

- **WHEN** an assembly's `simulate()` calls `omit()` on a declared child
- **THEN** `StructureError` is raised naming the node and `simulate()`

#### Scenario: Omission holds across bindings

- **WHEN** a once-only `render()` omits a child under a `Flag` and the
  assembly is simulated under three bindings
- **THEN** every enumeration returns the same children without the omitted
  one

