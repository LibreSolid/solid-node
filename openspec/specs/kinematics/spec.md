# Kinematics and Animation Specification

## Purpose

How nodes move: the operation objects (rotations/translations), world-pose
composition, multi-driver state binding and the normalized animation
timeline over it, animator-tagged idempotent renders, and the
cross-runtime `$t` expression math contract. Encodes ADR-008 (time-based
animation), ADR-023 (kinematic operations and animator-tagged idempotent
renders; tag renamed by the 2026-08-25 multi-driver-state-seam change),
ADR-022 (cross-runtime degree-trig parity), ADR-028 (cached base meshes
and single-matrix world composition), and ADR-056 stage 1 (multi-driver
state binding).

Code: `solid_node/node/operations.py`, `solid_node/node/assembly.py`,
`solid_node/node/base.py`, `solid_node/math.py`.
## Requirements
### Requirement: Tri-consumer operation objects

The system SHALL represent transforms as first-class operation objects
(`Rotation(angle, axis, node)`, `Translation(vector, node)`) that each render
for three consumers: `.scad(obj)` (OpenSCAD wrap), `.mesh(mesh)` (trimesh
transform with animated values resolved to floats; rotation applied in
radians), and `.serialized` (wire form `['r', angle, axis]` / `['t',
vector]`). Each operation SHALL also provide `.reversed`, and `.matrix()` —
its 4×4 homogeneous world matrix, with animated values resolved through
`as_number()` at access time and never cached, so a keyframe change is always
reflected. The registry plus `unserialize()` SHALL round-trip the wire form.
A new operation type MUST implement all of these surfaces and register
itself.

#### Scenario: Wire round-trip

- **WHEN** an operation is serialized and passed through `unserialize()`
- **THEN** an equivalent operation object is reconstructed

### Requirement: Chainable transform API

The system SHALL expose `rotate(angle, axis)` and `translate(translation)` on
every node, each appending an operation to `node.operations` and returning
`self` for chaining. `save_checkpoint()`/`restore_checkpoint()` SHALL
snapshot and roll back the operations list.

#### Scenario: Chained placement

- **WHEN** a render calls `part.rotate(45, [0, 0, 1]).translate([10, 0, 0])`
- **THEN** both operations are queued on the part in that order

### Requirement: World-pose mesh composition

The system SHALL compute a node's world-space mesh (`node.mesh`) by applying
its own operations first, then each ancestor's operations up the `_parent`
chain, folded into a single composed 4×4 world matrix (each operation's
matrix premultiplied in encounter order — later operations outermost). This
composition is the single source of truth consumed by the test assertions and
mirrored by both browser renderers (ADR-027 pins the viewer to the same
semantics). The world matrix SHALL be recomposed from scratch on every
access — never cached — because operation values can be animated expressions
that change with the keyframe and `node.operations` can be mutated in place
(e.g. the perturbation assertions inject and remove an operation).

#### Scenario: Nested placement

- **WHEN** a translated leaf sits inside a rotated assembly
- **THEN** `leaf.mesh` reflects the translation carried by the assembly's
  rotation (own ops first, then ancestors')

#### Scenario: Keyframe change reflected without cache staleness

- **WHEN** `set_keyframe` moves an assembly and `node.mesh` is read again
- **THEN** the returned mesh reflects the new pose (the world matrix was
  recomposed at access time)

### Requirement: Base mesh caching

The system SHALL load a node's base STL geometry (no operations applied) at
most once per `(stl_file, mtime)` in a module-level cache, evicting stale
entries for the same file when the STL is rebuilt under a new mtime.
`node.mesh` SHALL return a fresh mutable copy of the cached base mesh with
the composed world matrix applied in a single transform pass; the cached
base mesh itself is never mutated.

#### Scenario: Repeated access skips disk

- **WHEN** a test suite reads `node.mesh` many times without the STL
  changing
- **THEN** the STL is loaded from disk once and each access returns an
  independent copy

#### Scenario: Rebuild invalidates the cache

- **WHEN** the STL is regenerated with a new mtime
- **THEN** the next `mesh` access loads the new geometry and the entry
  cached under the old mtime is evicted

### Requirement: Declared time base

A root assembly MAY declare its time base as a class attribute named `time`
holding a `Time(loop=<seconds>)` declaration, exported from
`solid_node.motion.ports` — the module that answers what moves, alongside
the port kinds — and no longer from `solid_node.node`.
`loop` SHALL be a positive finite number of seconds: the span of machine time
one turn of the animation timeline covers. The declaration SHALL be frozen
class metadata readable off the class (`Root.time.loop`); assigning
`self.time` SHALL fail naming `set_keyframe`.

A `Time` declaration SHALL be refused at class-definition time when it is
bound to any attribute name other than `time`, or when the declaring class is
not an `AssemblyNode`, each with an error naming the rule.

Under a declared time base `self.time` SHALL read machine time in seconds on
every path:

- unbound, it SHALL be the symbolic expression `$t * loop`, so the normalized
  0..1 `$t` timeline is unchanged and published expressions carry the
  multiplication verbatim (`(360 * ($t * 43200))` rather than a constant);
- bound by `set_keyframe(t)` or `set_state(time=t)`, it SHALL be exactly the
  bound number, which callers state in seconds;
- under a stepped simulation, it SHALL be the simulation clock in seconds
  exactly as the `simulation` capability already states.

The time base is a property of the root: every assembly below it SHALL read
the root's time base, whether or not it declares one itself. Reading `time`
on a linked descendant whose own class declares a `Time` SHALL fail naming
the descendant and the root, so a stray declaration can never silently scale
one subtree differently. An assembly that is itself the root of the tree it
is read in — including a sub-assembly loaded on its own — uses its own
declaration.

A root that declares no time base SHALL keep the normalized 0..1 behaviour
of the "Normalized animation time" requirement unchanged.

#### Scenario: Symbolic time carries the loop

- **WHEN** a root declares `time = Time(loop=43200)` and a nested assembly
  rotates a child by `360 * self.time / 3600`
- **THEN** the nested assembly reads the same `$t * 43200` expression as the
  root, and the serialized operation names `$t` with the loop inside the
  expression rather than a constant

#### Scenario: Keyframes bind seconds

- **WHEN** `set_keyframe(2700)` is called on a root declaring
  `Time(loop=43200)` containing a nested assembly
- **THEN** both assemblies read `time == 2700` as a float and their meshes
  resolve at the pose 2700 seconds into the loop

#### Scenario: Clearing restores the loop expression

- **WHEN** a root declaring a time base is keyframed and then cleared
- **THEN** `time` reads the symbolic `$t * loop` expression again and the
  nested child's operations serialize to the same strings a never-keyframed
  render produces

#### Scenario: A misnamed declaration is refused

- **WHEN** a class body binds `clock = Time(loop=60)`
- **THEN** class definition fails with an error naming `time` as the only
  name a time base may be bound to

#### Scenario: A declaration below the root is refused

- **WHEN** a root without a declaration links a child assembly whose class
  declares `time = Time(loop=60)` and that child's `simulate()` reads
  `self.time`
- **THEN** the read fails naming the child and the root

#### Scenario: A sub-assembly loaded alone uses its own declaration

- **WHEN** an assembly declaring `Time(loop=60)` is loaded as the root
- **THEN** its `time` reads `$t * 60`

#### Scenario: The declaration is readable off the class

- **WHEN** a producer reads `type(root).time` on a root declaring
  `Time(loop=43200)`
- **THEN** it gets the declaration and `loop == 43200.0`, without
  constructing the node

#### Scenario: An undeclared root is unchanged

- **WHEN** a root declares no time base
- **THEN** `self.time` is bare `$t` unbound and the keyframed fraction when
  bound, exactly as before

#### Scenario: The time base is imported from the motion package

- **WHEN** a root's module writes
  `from solid_node.motion.ports import Time` and declares
  `time = Time(loop=43200)`
- **THEN** the declaration behaves exactly as it did when `Time` came from
  `solid_node.node`, and `from solid_node.node import Time` raises
  `ImportError` naming `solid_node.motion.ports`

### Requirement: Normalized animation time

The system SHALL expose animation exclusively on `AssemblyNode` via a `time`
property. For a root that declares no time base it SHALL be normalized to
0..1: symbolic OpenSCAD `$t` in the build/viewer path, and a plain float once
`set_keyframe(time)` is set. For a root declaring a time base it SHALL read
seconds as the "Declared time base" requirement states; everything below
about keyframes, clearing, recursion and tolerance holds in both cases with
the bound number meaning whatever the root's time base says. `set_keyframe(time)`
SHALL be equivalent to `set_state(time=time)` — the time-only surface over
the multi-driver state snapshot — and SHALL recurse into rendered children so
nested assemblies also render numerically. All assemblies share the single
`$t` timeline; a root that declares no time base scales in code.

Keyframed time SHALL be reversible. `clear_keyframe()` SHALL be equivalent to
`clear_state('time')`: it SHALL drop the fixed time, re-render, and recurse
into rendered children exactly as `set_keyframe` does, returning the subtree
to symbolic time while leaving any other bound snapshot entries in place.
Because an assembly's re-render sweeps only the operations it drove, the
operations a cleared subtree carries SHALL be the same symbolic expressions a
never-keyframed render produces — including expressions built through
`solid_node.math` — while static placement applied outside any assembly
render SHALL survive unchanged and operations SHALL NOT accumulate across
repeated `set_keyframe`/`clear_keyframe` cycles. `clear_keyframe()` SHALL be
a no-op on non-animated nodes, mirroring `set_keyframe`.

Both `set_keyframe` and `clear_keyframe` SHALL tolerate an assembly whose
`render()` returns a value that is not a list or tuple, recursing into no
children rather than raising, matching the partial-node tolerance the document
serializer already has.

#### Scenario: Keyframe freezes a frame

- **WHEN** `set_keyframe(0.25)` is called on a root assembly containing a
  nested assembly
- **THEN** both assemblies render with `time == 0.25` as a float and
  `node.mesh` resolves numerically

#### Scenario: Clearing a keyframe restores symbolic time

- **WHEN** `set_keyframe(0.5)` is called on a root assembly containing a nested
  assembly and `clear_keyframe()` is then called on the root
- **THEN** both assemblies report symbolic `$t` for `time`, and the nested
  child's operations serialize to the same `$t` expression strings a
  never-keyframed render produces

#### Scenario: Clearing restores a non-linear symbolic expression

- **WHEN** an assembly whose rotation is built with `solid_node.math` (for
  example `asin((r/l) * sin(360 * $t))`) is keyframed and then cleared
- **THEN** its operation serializes to the deferred OpenSCAD expression string,
  identical to the one a fresh render produces, not to the numeric value the
  keyframe computed

#### Scenario: Keyframe cycles do not accumulate operations

- **WHEN** `set_keyframe` and `clear_keyframe` are alternated several times on
  the same assembly
- **THEN** each driven child holds exactly the operations one render applies,
  and static placement applied outside any assembly render is still present

#### Scenario: A non-list render result is tolerated

- **WHEN** `set_keyframe` or `clear_keyframe` is called on an assembly whose
  `render()` returns a single node rather than a list or tuple
- **THEN** the call completes without raising and recurses into no children

#### Scenario: Keyframe equivalence with state binding

- **WHEN** `set_keyframe(0.3)` is called on an assembly that already holds
  another bound snapshot entry
- **THEN** the effect is exactly `set_state(time=0.3)`: `time` reads `0.3`
  and the other entry is preserved

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

The corpus SHALL carry the document's `bindings` table beside its cases, and a
case's expression MAY be, or reference, a binding name. The coverage check
SHALL therefore read emitted builtin names across the bindings and the cases
together: an emitted name that appears only inside a binding SHALL count as
covered, and a name appearing in neither SHALL fail the regeneration. A corpus
whose cases were self-contained SHALL NOT be able to hide an emitted builtin
by moving it into the table.

Adding a symbolic function to the module SHALL therefore add at least one
case exercising it to the corpus. The corpus SHALL be extended by adding a
new tree beside the existing one rather than by altering the existing cases,
so a regeneration changes no expected value that was already pinned. An
existing case's expression MAY be rewritten to reference a binding where the
producer now shares a subexpression, because the expression is how the value
is written and not the value itself; its key and its expected value SHALL be
unchanged.

The corpus SHALL include at least one tree whose expressions repeat a
subexpression, so the fixture pins the table's own semantics: an entry
referring to an earlier entry, a binding referenced from more than one node,
and a binding over a driver id as well as over `$t`.

#### Scenario: Every emitted name is pinned

- **WHEN** the parity fixture is regenerated
- **THEN** it carries at least one case whose expression, or one binding the
  case reaches, contains each name in the module's own inventory of emitted
  builtins, and the check that says so reads that inventory rather than a list
  of its own

#### Scenario: A new emitted name cannot slip through

- **WHEN** a function emitting a builtin absent from the corpus is added to
  the module and the fixture is regenerated
- **THEN** the regeneration fails naming the uncovered builtin

#### Scenario: A name inside a binding is covered

- **WHEN** the corpus reuses a subexpression so that an emitted builtin ends
  up only inside a `bindings` entry and in no case's own expression
- **THEN** the regeneration succeeds and reports that builtin as covered

#### Scenario: The corpus pins the table

- **WHEN** the parity fixture is regenerated
- **THEN** it carries a `bindings` array holding at least one entry that names
  an earlier entry and at least one entry referenced from more than one case

#### Scenario: Regeneration leaves the existing corpus alone

- **WHEN** the fixture is regenerated after the new corpus is added
- **THEN** every case the previous fixture carried is present under the same
  key and with the same expected value, whether or not its expression was
  rewritten to reference a binding

### Requirement: Animator-tagged idempotent renders

The system SHALL make assembly re-simulation absolute, never cumulative.
Operations applied while an assembly's `simulate()` — or a legacy
`render()` that reads a driver — is on the phase stack are tagged with that
assembly as its animator, and before each run the assembly removes only
operations it applied (`op._animator is self`). Untagged operations (rest
placement applied in a once-only `render()`, in `__init__`, or outside any
phase) SHALL never be swept, and two independent assemblies animating the
same node SHALL not disturb each other's operations.

#### Scenario: Re-simulation expresses absolute pose

- **WHEN** an assembly rotating a wheel by `self.time * 360` in
  `simulate()` is simulated twice at the same keyframe
- **THEN** the wheel holds one rotation operation with the same angle, not
  two accumulated rotations

#### Scenario: Rest placement survives re-simulation

- **WHEN** a node was translated by its parent's once-only `render()`, or
  during construction, and its simulating assembly re-simulates
- **THEN** the translation remains in `node.operations`, after the motion

### Requirement: Render at rest, simulate per instant

The system SHALL split an assembly's lifecycle into a rest build and a
per-instant motion. `render()` SHALL build the machine at rest — structure,
`omit()`, and the placement of every part that does not move — and SHALL
read no driver, no animation time and no port. `AssemblyNode.simulate()`, a
no-op in the base, SHALL be run by the framework after `render()` on every
call that enumerates the assembly's children, under whatever binding is
current: symbolic `$t` when nothing is bound, plain numbers under
`set_state`, `set_keyframe`, the test runner, the snapshot tool and the
simulator. Drivers, time and ports SHALL be read and bound in `simulate()`,
and a joint's coordinate is a port for this purpose.

An operation applied during `simulate()` SHALL compose innermost: it is
inserted before every operation `render()` or construction applied to the
node, so the node moves in its own frame and is then carried by its rest
placement. Operations applied during `simulate()` SHALL be tagged with the
simulating assembly and swept before that assembly's next `simulate()`, so
poses are absolute and never accumulate; two assemblies simulating one node
SHALL keep their operations apart. A joint bound during `simulate()` SHALL
apply its motion as operations of the node the joint is declared on,
tagged with the assembly whose `simulate()` is running and swept with the
rest of that assembly's motion, whether the joint is that assembly's own or
one of a node below it.

The simulate phase of one assembly SHALL run in a fixed order: FIRST
the framework clears the value and the binder record of every
coordinate this assembly bound through a wiring or a relation in its
previous run, so the run that follows sees only values bound in the
current walk; THEN the author's `simulate()` runs; THEN the wirings and
the relations the class declared are solved together, each wiring
binding once its source is bound and each relation applied from
whichever of its ends is. All of it happens while the phase is still
that assembly's, so every motion it causes carries that assembly's tag
and is swept before its next run. A value the author's own code bound
in an earlier run and not in this one SHALL NOT be cleared: it is the
author's, as it is today. Because each class solves its own relations
in its own instance's phase, a relation stated on an ancestor and
reaching a descendant's coordinate by path SHALL be solved before that
descendant's own relations are.

An assembly whose first `render()` read nothing SHALL run that `render()`
once per instance: later calls SHALL return the same children and SHALL NOT
re-run the author's `render()`, and the operations it applied SHALL persist
unswept. `omit()` called during `simulate()` SHALL raise `StructureError`.

#### Scenario: Motion composes innermost

- **WHEN** an assembly's `render()` translates a child to `[10, 0, 0]` and
  its `simulate()` rotates the child by `90` degrees about z
- **THEN** the child's operations are the rotation then the translation,
  and its origin lands at `[10, 0, 0]` rather than `[0, 10, 0]`

#### Scenario: Rest render runs once

- **WHEN** an assembly whose `render()` reads nothing is rendered under
  three successive `set_state` bindings
- **THEN** the author's `render()` ran once, the placement operation
  objects are the same objects each time, and the `simulate()` operation
  holds the current binding's value with no accumulation

#### Scenario: Symbolic simulate in the build path

- **WHEN** an assembly is rendered with nothing bound
- **THEN** the operation `simulate()` applied carries the symbolic `$t`
  expression, `set_keyframe(0.25)` makes it numeric, and `clear_keyframe()`
  restores the symbolic form

#### Scenario: Two simulators of one node

- **WHEN** two assemblies each simulate the same node and one re-simulates
- **THEN** only that assembly's operation is replaced and the other's is
  untouched

#### Scenario: Joint motion is swept like any motion

- **WHEN** an assembly binds a child's joint in its `simulate()` and the
  tree is enumerated twice at different instants
- **THEN** the child carries one joint motion for the current instant,
  tagged with that assembly, and the rest placement its parent applied is
  untouched

#### Scenario: The phase solves the wirings and the relations together

- **WHEN** an assembly binds one joint in `simulate()`, declares a
  wiring whose source another relation of the same class solves, and
  states that relation
- **THEN** the relation is applied and the wiring binds from its solved
  source in the same solve, all the motion is tagged with that
  assembly, and all of it is swept before its next run

#### Scenario: A phase clears what it bound last run

- **WHEN** an assembly whose relations solve a train from one binding
  in `simulate()` is enumerated at three successive instants
- **THEN** each run cleared the coordinates it had bound in the
  previous one before the author's `simulate()` ran, and each run's
  solve produced that instant's angles rather than refusing or
  repeating the first instant's

#### Scenario: An ancestor's relation binds before the descendant solves

- **WHEN** a root states a relation reaching a joint declared two levels
  down, and that level's own class states relations over the same joint's
  neighbours
- **THEN** the root's relation bound the joint before the descendant's
  relations were solved, and the descendant solved against that value

#### Scenario: Structure cannot move

- **WHEN** `simulate()` calls `omit()` on a declared child
- **THEN** `StructureError` is raised naming the node
### Requirement: Reading a driver in render is deprecated, not refused

The system SHALL keep every current model working. An assembly whose
`render()` reads a declared driver, `self.time` or a port value SHALL keep
the previous behaviour for that instance — the author's `render()` re-runs
on every call, its operations are tagged and swept, and rest placement
applied outside any render survives — and the framework SHALL emit one
`FutureWarning` per class naming the class, the first read, and
`simulate()` as the new home. The decision SHALL be made on the instance's
first `render()`. Placement applied in `__init__` SHALL continue to
survive, composed before rest placement.

#### Scenario: A legacy assembly still animates

- **WHEN** an assembly rotates a child by `self.time * 360` in `render()`
  and is rendered at two keyframes
- **THEN** the child holds one rotation with the second keyframe's angle,
  and a `FutureWarning` was emitted once naming the class and `time`

#### Scenario: A port read in render warns

- **WHEN** an assembly reads a child's port value in `render()`
- **THEN** a `FutureWarning` names the class and the port, and the render
  keeps re-running per binding

### Requirement: Multi-driver state binding

The system SHALL let an `AssemblyNode` bind a snapshot of named numeric
driver values with `set_state(**states)`. Binding SHALL merge the given
entries into the assembly's current snapshot (an entry is replaced when
re-given, preserved otherwise), re-render the assembly, and recurse into
rendered children exactly as `set_keyframe` does — including tolerating
a `render()` result that is not a list or tuple by recursing into no
children. Snapshot values SHALL be plain numbers.

Entries SHALL be addressable by qualified id: an entry named with a
dotted instance path (`x_axis.motor`) SHALL be delivered only to the
addressed instance's subtree, with the consumed leading segment
stripped as propagation descends, so sibling instances of one class
hold independent values for a same-named driver. The propagation walk
SHALL link children before recursing, so qualification is computed
against the same names every linked pass derives. The `time` entry
SHALL remain global: it propagates flat and unmodified to every
descendant. A bare (unqualified) entry for a project driver SHALL
remain valid while exactly one declared driver in the subtree bears
that local name; when the bare name is ambiguous, binding SHALL fail
loudly listing the colliding qualified ids rather than delivering one
value to all of them.

Every bound name SHALL name a declared driver. A bare name that no
declared driver in the tree bears, and a dotted name that is not a
qualified id the tree publishes, SHALL both fail loudly naming the
rejected entry and the declared ids, because nothing can read an entry
with no declaration behind it. `time` is the one exception: it is a
snapshot entry with no declaration and SHALL remain bindable. A
refused binding SHALL leave the tree's snapshot exactly as it was, in
the same way an ambiguous binding does.

`render()` SHALL read a driver DECLARED on that node as an attribute of
the node, under the name the declaration was made with: a node
declaring `x = Driver(...)` reads its bound value as `self.x`. This
SHALL be the only surface for reading a driver value off a node; no
mapping view of the bound snapshot is exposed. The read SHALL yield
exactly the entry bound for that node under that local name, in
whichever binding mode is active — the plain number under a numeric
snapshot, the symbolic token under the document's symbolic mode.
Reading a declared driver whose entry is not bound SHALL raise an
error naming the driver and `set_state`, so a state-consuming assembly
rendered without a snapshot fails loudly rather than guessing.

Assigning to a declared driver on an instance SHALL raise an error
naming the driver and `set_state`. A driver's value belongs to the
bound snapshot, and an instance attribute of the same name would
shadow the declaration silently for every later read.

Declaring a driver under a name already carried by the node class from
any base SHALL raise at class-definition time, naming the collision, so
a driver cannot silently displace a node member such as `render` or
`time`. Redeclaring a driver inherited from a base SHALL remain legal,
which is how a subclass overrides an inherited declaration.

Animation time SHALL be read through the `time` property, which
returns the bound `time` entry and falls back to symbolic `$t` when
none is bound, preserving the ADR-008 animation path.

`clear_state(*names)` SHALL remove the named entries from the snapshot
— all entries when called with no names, accepting qualified names the
same way `set_state` does — re-render, and recurse the same way,
restoring symbolic `$t` behavior for `time`. Because re-renders sweep
only the operations the assembly drove, repeated
`set_state`/`clear_state` cycles SHALL NOT accumulate operations, and
static placement applied outside any assembly render SHALL survive,
exactly as the idempotent-render requirement already guarantees.

On nodes that do not animate (leaves, fusions), `set_state` and
`clear_state` SHALL be no-ops, mirroring `set_keyframe`.

#### Scenario: A declared driver reads as an attribute

- **WHEN** an assembly declaring `motor = Driver(default=0)` is bound
  with `set_state(motor=4000)` and its `render()` derives a
  translation from `self.motor`
- **THEN** `self.motor` reads `4000` and the assembly re-renders at
  the pose that value implies, absolutely

#### Scenario: Sibling instances read their own attribute value

- **WHEN** a parent holding `x_axis` and `y_axis` instances of one
  `motor`-declaring class binds `{'x_axis.motor': 8000,
  'y_axis.motor': 2000}`
- **THEN** `x_axis.motor` reads `8000` and `y_axis.motor` reads
  `2000`, the two poses differ accordingly, and no value is shared
  between the instances

#### Scenario: The declaration is still readable off the class

- **WHEN** a driver declared as `motor = Driver(default=8000, ...)` is
  read from the CLASS rather than from an instance
- **THEN** the declaration object itself is returned, and driver
  discovery, qualification, and the serialized driver table are
  unaffected

#### Scenario: Attribute read under symbolic binding

- **WHEN** a driver-declaring tree is walked in the document's
  symbolic mode and its `render()` reads the driver as an attribute
- **THEN** the read yields the symbolic driver token carrying the
  qualified id, and the restored numeric snapshot reads numbers again
  afterwards

#### Scenario: Unbound attribute read fails loudly

- **WHEN** an assembly whose `render()` reads `self.motor` is rendered
  with no snapshot bound
- **THEN** an error is raised naming `motor` and `set_state`

#### Scenario: Assigning to a driver fails loudly

- **WHEN** code assigns `node.motor = 5` on an instance whose class
  declares `motor` as a driver
- **THEN** an error is raised naming `motor` and `set_state`, and the
  bound snapshot is unchanged

#### Scenario: A shadowing driver name is rejected at declaration

- **WHEN** a node class declares a driver under a name its bases
  already carry, such as `render` or `time`
- **THEN** the class definition fails with an error naming the
  colliding name

#### Scenario: Redeclaring an inherited driver stays legal

- **WHEN** a subclass of a `motor`-declaring assembly redeclares
  `motor` with a different default
- **THEN** the class defines successfully and the subclass's
  declaration is the one discovery finds

#### Scenario: An undeclared bare name is refused

- **WHEN** `set_state(motr=4000)` is called on a tree whose only
  declared driver is `motor`
- **THEN** binding fails naming `motr` and listing the declared ids,
  and no entry is left bound anywhere in the tree

#### Scenario: An unknown qualified id is refused

- **WHEN** `set_state(**{'z_axis.motor': 100})` is called on a tree
  holding only `x_axis` and `y_axis`
- **THEN** binding fails naming `z_axis.motor` and listing the
  declared ids, and no entry is left bound anywhere in the tree

#### Scenario: Two named drivers bind numerically

- **WHEN** `set_state(motor=4000, lift=2.5)` is called on an assembly
  declaring both and deriving operations from `self.motor` and
  `self.lift`
- **THEN** the assembly re-renders with both values as plain numbers
  and `node.mesh` reflects the resulting pose absolutely

#### Scenario: Merging preserves unrelated entries

- **WHEN** `set_state(motor=4000)` is followed by `set_state(lift=1.0)`
- **THEN** the assembly reads `motor` as `4000` and `lift` as `1.0`

#### Scenario: Ambiguous bare name fails loudly

- **WHEN** `set_state(motor=1234)` is called on a tree where two
  sibling instances both declare `motor`
- **THEN** binding fails listing `x_axis.motor` and `y_axis.motor`,
  and neither instance's state changes

#### Scenario: Time stays global

- **WHEN** `set_state(time=0.25)` is called on a tree with colliding
  project-driver names
- **THEN** every descendant's `time` property reads `0.25`, with no
  qualification required

#### Scenario: State cycles do not accumulate operations

- **WHEN** `set_state` is called many times in sequence on the same
  assembly (as a stepping loop does every tick)
- **THEN** each driven child holds exactly the operations one render
  applies, and static placement applied outside any assembly render is
  still present

#### Scenario: Clearing state restores symbolic time and unbinds drivers

- **WHEN** `set_state(time=0.5, motor=100)` is followed by
  `clear_state()`
- **THEN** the assembly's `time` reports symbolic `$t` again and
  reading `self.motor` raises naming `motor` and `set_state`

#### Scenario: Leaf tolerance

- **WHEN** `set_state(motor=10)` propagation reaches a leaf node
- **THEN** the call is a no-op on that leaf

### Requirement: Instance-qualified driver identity

The system SHALL identify a driver instance by a qualified id: the
dotted instance path from the addressing root to the declaring node,
joined with the class-local driver name (`x_axis.motor`); a driver
declared on the root itself SHALL keep its bare local name. The id
SHALL be computed from the parent-derived linked child names — the
same names the serialized document publishes for nodes — during a walk
that links parents to children before recursing, and SHALL never be
stored on the node or the declaration.

A symbolic driver reference SHALL be represented by a token whose
string form is exactly the qualified id, interoperating with the
existing symbolic expression machinery: ordinary arithmetic on the
token SHALL produce well-formed expression strings, and the
degree-convention dual-mode math functions SHALL accept it in symbolic
mode unchanged.

Qualification SHALL fail loudly, naming the node and the cure, when it
would pass through a segment that is not computable (an unlinked
child) or not a legal expression identifier (a list-held child's
derived `<attr>-<index>` name). It SHALL NOT fall back to the bare
local name and SHALL NOT sanitize.

#### Scenario: Two instances of one class qualify distinctly

- **WHEN** one assembly class declaring driver `motor` is instantiated
  as attributes `x_axis` and `y_axis` of a parent, and a linked pass
  reads each instance's driver symbolically
- **THEN** the resulting expression strings reference `x_axis.motor`
  and `y_axis.motor` respectively

#### Scenario: Token rides ordinary arithmetic and symbolic trig

- **WHEN** a render computes `asin(0.25 * sin(token * 0.1125))` from a
  driver token in symbolic mode
- **THEN** the expression string is well-formed with the qualified id
  embedded, with no operator or math-function changes in project code

#### Scenario: Illegal id segment fails loudly

- **WHEN** a driver would qualify through a child held in a list
  (derived name `axes-0`)
- **THEN** the operation fails naming the node and the illegal
  segment, rather than emitting an expression that parses as
  subtraction or colliding on the bare name

