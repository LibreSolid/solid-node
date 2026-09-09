# ADR-089: `drives` Relates Two Coordinates

**Status:** Accepted
**Date:** 2026-09-09
**Extends:**
- [ADR-061: A call in a node class body is a declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-066: render() builds the machine at rest, simulate() moves it](./ADR-066-render-at-rest-simulate-per-instant.md)
**Depends on:**
- [ADR-022: Cross-runtime degree-trig parity for `$t` and driver expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
- [ADR-056: Signals, drivers, ports, and stepped simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md)
- [ADR-076: Mechanism laws as compositions over expression math](../MATH/ADR-076-mechanism-laws-as-compositions-over-expression-math.md)
- [ADR-080: A shared subexpression is named once](../EXPORT/ADR-080-a-shared-subexpression-is-named-once.md)
- [ADR-087: One module, one question](./ADR-087-one-module-one-question.md)
- [ADR-088: A joint owns one coordinate](./ADR-088-a-joint-owns-one-coordinate.md)
**OpenSpec change:** `couplings`

## Context and Problem Statement

Cycle 2 gave a body a place to move. Nothing said that one body's motion
IS another's, so every project wrote the transmission by hand — and wrote
it in the one direction it happened to need.

Wall clock 01 is the evidence for the hard direction.
`Movement.arbor_angles(seconds)` walks BACKWARDS from the escape wheel,
because the escapement is where the law is prescribed and the great
wheel is where the power comes in; each step of the walk is one affine
relation, `driven = A - (driver_teeth / driven_teeth) * driver`. The
framework already carried both readings of it —
`mechanisms.meshed_angle` and `mechanisms.driving_angle` are one law and
its algebraic inverse over the same six arguments — written out twice
because the project had to choose a direction. The clock then built a
dictionary of angles by hand and fanned it out through
`simulate_for_seconds`.

Thor is the evidence for the easy direction: seven root `Driver`s
forwarded by hand down five levels of ports, with `Art3`, `Art4` and
`Art56` declaring ports only to pass them on, each level multiplying by
a ratio. Two of its shapes are not plain ratios — the elbow belt is
anchored on the shoulder housing, so the arm turns by
`elbow - shoulder`, and the wrist differential is `wrist ± 2 * tool` —
and both are linear formulas over coordinates.

Neither project needed a vocabulary of mechanisms. Both needed one verb
relating two coordinates, a way to write the law as project code, and a
solver that does not care which end the author happened to bind.

## Decision Drivers

- One verb, wherever the two coordinates are in the tree, and no second
  vocabulary to learn or to maintain.
- The law is project code handed in; the framework never learns what a
  gear is and looks up no hook on any class.
- The author states the mechanical direction; the framework works out
  which way to solve it, per run, from what is actually bound.
- A root driver reaches a deep joint without a chain of forwarded ports.
- Everything stays symbolic, so a build publishes expressions the viewer
  already evaluates.
- Every failure fails by name, with the node paths, the relation as
  written, and the ends.

## Considered Options

1. `a.drives(b)` as a class-body STATEMENT with `law=` as a passed-in
   callable, ends of five kinds resolved at realization, and a per-run
   fixpoint solve at the end of the owning simulate phase.
2. A `law_for` (or similarly named) HOOK on the node class, looked up by
   the framework to discover what a relation between two nodes means.
3. One GLOBAL solve over the whole tree, at the root, after the walk.
4. A vocabulary of mechanism declarations — `Mesh(...)`, `Belt(...)`,
   `Differential(...)` — instead of one relation with a law.
5. Solving oriented by the author's declaration order, or by an explicit
   `direction=` on the relation.

## Decision Outcome

Chosen option 1.

**`drives` is a statement, and it is framework vocabulary.** Written
bare in a class body — `power.drives(centre, law=going_train)` — it is
recorded on the class being defined, through the same mechanism ADR-061
already built: `_DeclaringNamespace.__init__` puts a mutable list under
a private key, `drives` walks the stack for the nearest declaring
namespace and appends to it, and `NodeMeta.__new__` pops the list onto
the class. The list is created once and only appended to, never rebound:
inside a PEP 709 inlined comprehension the frame reports a plain `dict`
COPY of the namespace, and the copy holds the same list OBJECT, so an
append there still lands on the real one. Assigning the result,
`great = power.drives(centre)`, additionally NAMES the relation — read
off the class it is the declaration, read off an instance it is that
instance's record, including which way the last run solved it — and the
relation is recorded once, not twice. `declared_relations(cls)` walks the
MRO base-first: a relation is a statement, not a name, so a subclass ADDS
to its bases' relations rather than overriding them. `drives` with no
class body executing is refused by name, and a class that carries
relations and is not an assembly is refused when the class is created,
by a local import of `AssemblyNode` taken only by such a class — the
shape `Time.__set_name__` already uses.

**An end is a coordinate, and there are five kinds of end**: a port or
joint of the class stating the relation, a child declaration (standing
for its class's ONE joint), a path reference through declared children,
a `Driver` declaration (a SOURCE only), and a derived coordinate. Reading
a port, a joint, a derived coordinate or another child declaration off a
child declaration now yields a PATH REFERENCE rather than raising:
ADR-061's rule is extended, not reversed, and the substance of its
reasoning survives intact — a class body still may not read a sibling's
VALUE, because a parameter is a number belonging to a realized instance
and a class body has none, while a port is not a value but a place a
value will be, and naming a place is what a declaration has always done.
A driver read sideways stays refused: a driver is addressed by the
qualified id its position gives it (ADR-056), and a second address for
one value is what that qualification exists to prevent.

**What the classes alone decide is refused at class definition; what
depends on the instance is refused at realization.** A node end whose
class declares no joint or several, a driver as the driven end, a path
segment no class declares, a path through a repeated or list-held child,
`ratio=` together with `law=`, a non-linear formula: all refused where
they are written, because every class along a path is known there. A path
that does not resolve on the instance, and a `law=` callable returning a
non-law: refused at realization, naming the relation, the path as
written and the node the walk stopped at. Ends resolve at the END of the
instance's construction, after its children are realized — later than
cycle 2's joint arguments, because an end may be a child or a descendant
of one.

**The law is project code passed in, and the class hook was rejected**
(option 2, rejected explicitly by the pilot). `law=` takes a callable of
two arguments, called exactly ONCE per realized instance at realization
with the realized nodes that OWN the two coordinates, driver first; the
owner is the realized child for a node end, the realized descendant that
declares the named port or joint for a path end, and the declaring
instance itself for a port, a joint, a derived coordinate or a driver.
So a law reads `driver.built`, `driver.wheel_teeth`, an index, a
resolved parameter — which is exactly what the clock's going train
needs, since its tooth counts and gap angles come off a built library
movement and not out of a formula. The callable returns a LAW: anything
with a callable `forward`, and optionally `inverse`; a plain function is
taken as forward-only. The framework inspects nothing else — no
registry, no shape list, no hook of any name on a node class. A hook
would make "what an arbor drives" a property of a class the framework
has to look up, which is the vocabulary this whole layer was chosen to
avoid (option 4, rejected for the same reason: neither originating
project needs a vocabulary of mechanisms, and every shape either has is
one relation with a law). Calling the law once at realization rather
than per run is deliberate: a law is a property of the assembled machine
— tooth counts, registration, pitch radius — and nothing about it changes
between two instants.

**`Affine(ratio, offset)` is the one new importable name**, a frozen
dataclass computing `ratio * driver + offset` and
`(driven - offset) / ratio` by ORDINARY arithmetic, so a `DriverToken`
or `$t` builds the wire expression solid2 builds and a number gives a
number. A ratio of one and an offset of zero are skipped rather than
multiplied and added, so an identity publishes no `(x * 1)`. It is
invertible unless the ratio is a NUMBER equal to zero: a symbolic ratio
is taken as invertible, because the division is as well-formed as the
multiplication and refusing it would mean deciding a value the framework
does not have. `ratio=` and `offset=` on `drives` are its shorthand,
resolved per instance by the same `evaluate` a child declaration's
arguments use. The backward face leans on more of solid2's operator
surface than the forward one — `y - offset`, the number-on-the-left
forms, `/ ratio`, unary negation — so that dependency is PINNED by a
test that evaluates the PUBLISHED expression string through the same
helper the ADR-022 parity tests use and compares it with the numeric
answer.

**A derived coordinate is a linear formula, and it IS a coordinate.**
`relative = art3.elbow - shoulder`, `left = wrist + 2 * tool`: a mapping
from reference to coefficient plus a constant, accumulated by `+`, `-`,
unary `-`, and `*` or `/` by a number or a declared parameter. Keeping
the algebra to a mapping rather than an expression tree is what makes
the backward solve exact and cheap, and it is the shape MuJoCo writes as
a `tendon/fixed`. An intermediate formula FLATTENS into its base terms,
because `wrist + 2 * tool` builds `2 * tool` before anything names it and
a term no class declares would be one nothing ever solves. Multiplying
two coordinates, or any other operator or function over them, is refused
at class definition naming both operands and pointing at `law=`. Its
domain and unit come from its terms, and terms that disagree are refused
naming the two. It owns a `Port` as its coordinate exactly as a joint
does, so it reads on an instance as a bound slot and `declared_ports`
reports it beside the ports — the same duck-typed seam, no new
enumerator.

**Solving is oriented from the bound side, per run, at the end of the
owning instance's simulate phase.** The framework cannot know what is
bound until `simulate()` has run, so the solve happens inside
`_lifecycle_render` after `self.simulate()` returns and before the phase
is popped — which is what makes every motion a relation causes carry
that assembly's animator tag and be dropped by its next sweep, exactly
as a hand-written rotation there is. Relations of a class are solved for
each INSTANCE of that class, in that instance's own phase (option 3,
rejected: a global solve needs a second enumeration of a tree the render
already walks, has no phase to tag its motion with, breaks the
one-assembly-owns-its-motion rule ADR-066 rests on, and gives a relation
on a repeated child no per-instance identity). That ordering is the
useful one and it is stated rather than discovered: an ancestor's
relation reaching a deep coordinate by path binds it BEFORE the deep
node's own relations run, so the ancestor's value is the descendant's
boundary condition.

**Cycle 2's wirings are absorbed into that solve.** A wiring is the
forward-only identity relation it already was, binding through the same
path so the child end's declared scale still applies; it now takes part
in the same fixpoint instead of binding at a fixed point before it. The
clock forces this: a movement solves an arbor's coordinate through a
relation, and the arbor then wires that same coordinate down into the
wheel and the rod that turn with it. Bound before the relations, that
wiring finds its source unbound and refuses by cycle 2's own rule; bound
inside the fixpoint, it waits one iteration and binds. Cycle 2's other
rules are untouched: an unbound source when propagation has FINISHED is
still refused by name with the same message, a hand binding of a wired
child end is still refused, and a wiring is still a binder, so a
relation reaching the same child end is a double binding.

**Freshness is part of the rule, not an implementation detail.** A value
slot keeps what was put into it, and nothing else clears it — harmless
while an author binds everything by hand, and fatal to a solver: after
run 1 every coordinate still "holds a value", the fixpoint finds nothing
with exactly one bound end, and the train freezes at the first instant.
So at the START of an assembly's simulate phase, before the author's
`simulate()` runs, the framework clears the value and the binder record
of every coordinate THIS assembly bound through a wiring or a relation
in its previous run, from the record it kept when it bound them. What
survives is exactly what should: a value this author binds in the
current run, a value an ancestor already applied in this walk, and a
driver read. A value the author bound in an EARLIER run and not in this
one is NOT cleared — an author's binding is the author's responsibility,
as it is today.

**Three refusals, each its own kind, exported from the module.**
`UnreachedCoordinate` when a relation's ends are both still unbound once
nothing changes any more, and when a bound derived coordinate has two
unknown terms; `DoublyBound` when something else already bound the
coordinate a relation would bind — an author's `simulate()`, a wiring,
another relation — or when both ends were bound by others, which is how
an over-constrained loop surfaces; `NotInvertible` when the driven end is
the bound one and the law offers no inverse (or is an `Affine` whose
ratio is numerically zero). Two relations that would give the SAME value
are refused as well, and the message says why: the framework cannot
compare two values to decide whether a redundant statement agrees,
because they are ordinarily symbolic expression strings and two texts
that differ may or may not be equal. A silent first-writer-wins would
hide a real modelling mistake.

**Order within a pass is declaration order; the fixpoint makes the
result order-independent** (option 5, rejected: an explicit `direction=`
puts the framework's implementation question in the author's model, and
declaration order as the orienting rule would make the clock reorder its
train to read backwards). The determinism is there for the messages, not
for the answer: a train written power-first solves escape-first without
the author moving a line.

## Consequences

- `solid_node/motion/couplings.py` is filled: `Affine`, `ForwardOnly`,
  `CoordinateRef` and its kinds (`OwnRef`, `PathRef`, `DriverRef`),
  `DerivedCoordinate`, `Relation` and its per-instance `RelationRecord`,
  the three errors under a shared `CouplingError`, the solver
  (`solve_relations`, `clear_solved`) and the enumerators
  (`declared_relations`, `declared_derived`). Module scope imports
  `solid_node.motion.ports` and `dataclasses` and nothing else, so it
  costs exactly what importing ports costs — the ceiling ADR-087 set for
  the then-empty module, widened by the `cli-startup-cost` delta.
- `solid_node/motion/ports.py`: a `Coordinate` mixin carrying `drives`
  and the linear arithmetic, inherited by `Port` and by `Joint`;
  `BoundPort.binder`, and `bind` recording it from a `binding_as(...)`
  context — module state of exactly the shape `wiring_binding` already
  had, and for the same reason: `bind` is the one binding path, and what
  reaches it has to be able to say who it is.
- `solid_node/node/declarative.py`: the relations list on the declaring
  namespace, `record_relation` and `executing_body`, the `NodeMeta`
  hand-off and the non-assembly refusal, `ChildDeclaration.__getattr__`
  yielding a path reference, `ChildDeclaration.drives`, and
  `RepeatDeclaration.__getattr__` refusing an ambiguous path. An
  attribute read that names nothing keeps raising `SidewaysReadError`
  (an `AttributeError`) rather than becoming a `TypeError`, because
  `getattr(declaration, 'domain', None)` is how the framework itself
  asks whether a keyword value is a coordinate.
- `solid_node/node/qualified.py`: `drives` on `DriverDeclaration`.
- `solid_node/node/base.py`: `resolve_declared_relations` at the end of
  the constructor, after `realize_children`.
- `solid_node/node/assembly.py`: `_bind_wirings` is GONE, replaced by
  `clear_solved` before the author's `simulate()` and `solve_relations`
  after it. This is the one place cycle 3 reworks cycle 2's code rather
  than adding beside it.
- No new operation type, no serializer change, no schema version, no
  viewer change: a relation lowers to the same operations a hand binding
  produces, carrying whatever value — number or expression — it was
  solved with.
- A relation is not published in the document, so an exporter still has
  nothing to read. Recorded as future work with the joints table cycle 2
  left open, for the MuJoCo/Modelica emission discussion
  `workflow/motion/roadmap.md` defers.
- Recorded and not decided: whether a subclass may REMOVE an inherited
  relation; whether `DoublyBound` should have an explicit escape for a
  deliberately redundant model; whether a non-invertible law may declare
  a numeric inverse; whether a relation should be able to state a range
  or a backlash. Closed loops, stateful mechanisms and automatic
  driver-to-joint binding are out and stay out.
- Wall clock 01 and Thor are the originating projects and are NOT
  refactored here: they are refactored in their own repositories after
  this cycle. The evidence in this repository is
  `tests/coupling_project/` — a three-arbor going train solved backwards
  from its escapement through the project's own law, and an arm whose
  root driver reaches a joint two levels down by path and whose derived
  coordinate carries a belt anchored on the shoulder housing.
