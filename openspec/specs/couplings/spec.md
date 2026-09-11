# couplings Specification

## Purpose

The relation between two coordinates: what `a.drives(b)` states, where
it may be written, how each kind of end resolves to a coordinate, how a
law is handed to the framework as project code, how a linear formula
over coordinates becomes a coordinate of its own, and how the framework
orients each relation from whichever end is bound at the moment it
solves — with the three refusals that keep a wrong model from becoming
a pose. Encodes ADR-089, over ADR-061 (a call in a class body is a
declaration), ADR-066 (render at rest, simulate per instant), ADR-088
(a joint owns one coordinate) and ADR-076 (mechanism laws as
compositions over expression math).

Code: `solid_node/motion/couplings.py`.
## Requirements
### Requirement: A relation is stated by `drives` in a class body

The system SHALL provide `drives(other, ratio=None, offset=None,
law=None)` on every declaration that can name a coordinate — a child
declaration, a port declaration, a joint declaration, a `Driver`
declaration, a path reference and a derived coordinate — and SHALL
require no import to use it. `drives` SHALL be framework vocabulary and
the ONLY vocabulary for relating two coordinates: the framework SHALL
look up no method, attribute or hook of any name on a project's node
class to discover what a relation means.

`drives` SHALL be a STATEMENT: written bare in a class body, as
`power.drives(centre, law=going_train)`, it SHALL be recorded on the
class being defined, without being assigned to a name. Assigning its
result, `great = power.drives(centre)`, SHALL additionally name the
relation, so that a test can reach it and every message about it can
say its name; the same relation SHALL be recorded once, not twice. A
named relation read off the CLASS SHALL yield the declaration with its
two ends and its law as written; read off an INSTANCE it SHALL yield
that instance's record of the relation: its two resolved coordinates,
its law, and which direction it was solved in on the last run. A
relation that resolves to SEVERAL records — a broadcast over a repeated
child — SHALL read off an instance as the tuple of those records, in
copy order.

A relation SHALL be recorded even when it is written inside a class-body
comprehension, where the executing frame reports a copy of the
declaring namespace rather than the namespace itself.

A class's relations SHALL be enumerable off the class without
constructing an instance, base-first through the inheritance chain. A
relation written as a BARE STATEMENT has no name, and a subclass ADDS
such a relation to the relations of its bases rather than overriding
them, because a statement is not a name. A relation ASSIGNED to a name
is reachable by that name, and a subclass assigning a relation to a name
one of its bases already used SHALL REPLACE the base's: the subclass
SHALL enumerate the replacing relation and NOT the replaced one, and the
replacing relation SHALL keep the POSITION the base's held in the
enumeration, so the order of the solving pass does not shift under
inheritance — the rule a redeclared joint already obeys. The base SHALL
be unaffected: it SHALL still enumerate its own relation, and an
instance of the base SHALL still resolve, solve and record it. Reading
the name off the SUBCLASS SHALL yield the replacing declaration, and off
one of its instances that instance's record of the replacing relation;
the replaced relation SHALL never be resolved or recorded for an
instance of the subclass. A subclass names an inherited declaration
through the class that declares it — `Base.rotor.spin` — because the
base's declarations are not names of the subclass's own body, and the
framework SHALL add no other vocabulary for it.

`drives` called with no node class body executing SHALL be refused by
name, saying that a relation is class metadata. A class that carries
relations and is not an assembly SHALL be refused when the class is
created, naming the class, because only an assembly has the simulate
phase a relation is solved at the end of.

Relations declared on a class SHALL apply per instance of that class:
each realized instance SHALL resolve, solve and refuse its own,
independently of every other instance of that class.

#### Scenario: A bare statement is recorded on the class

- **WHEN** a class body contains `power.drives(centre, law=going_train)`
  with no assignment
- **THEN** the class carries that relation, enumerable off the class
  with its two ends and its law, and no instance was constructed

#### Scenario: A named relation is one relation

- **WHEN** a class body contains `great = power.drives(centre)`
- **THEN** the class carries exactly one relation, it is named `great`,
  reading `great` off the class yields the declaration, and reading it
  off a realized instance yields that instance's resolved record

#### Scenario: A subclass adds to its base's relations

- **WHEN** a class declaring two relations is subclassed by a class
  declaring a third
- **THEN** the subclass enumerates all three, base's first, and the
  base still enumerates its two

#### Scenario: A relation outside a class body is refused

- **WHEN** project code calls `drives` on a port declaration at module
  scope or inside a method
- **THEN** it raises by name, saying a relation is declared in a class
  body and is class metadata

#### Scenario: A relation on a leaf is refused

- **WHEN** a class body of a node that is not an assembly states a
  relation
- **THEN** class creation raises naming the class and saying that a
  relation is solved at the end of a simulate phase, which only an
  assembly has

#### Scenario: Every instance solves its own relations

- **WHEN** a class stating a relation is declared twice as two children
  of one parent, and the two are bound differently
- **THEN** each instance's relation resolves and solves against its own
  coordinates, and neither reads the other's values

#### Scenario: A subclass replaces a relation of its base by name

- **WHEN** a base declares `drive = input_angle.drives(rotor.spin,
  ratio=8.0)` and a subclass declares
  `drive = free_run.drives(Base.rotor.spin, ratio=1.0)`
- **THEN** the subclass enumerates ONE relation named `drive`, the
  replacing one, at the position the base's held; an instance of the
  subclass binds `rotor.spin` from `free_run` and nothing is refused as
  doubly bound; and the base still enumerates and solves its own

#### Scenario: A bare statement stays additive

- **WHEN** a base states two bare relations and a subclass states a
  third bare one and assigns a fourth to a name no base used
- **THEN** the subclass enumerates all four, the base's first, and
  nothing was replaced

### Requirement: The law of a relation is an affine pair, or project code passed in

The system SHALL provide `Affine(ratio, offset=0)`, exported from
`solid_node.motion.couplings`, as the law `driven = ratio * driver +
offset`, evaluated in the driven end's own unit. `Affine` SHALL compute
by ordinary arithmetic, so a symbolic driver value produces a symbolic
result and a number produces a number, and SHALL be invertible as
`driver = (driven - offset) / ratio` unless its ratio is a number equal
to zero.

`ratio=` and `offset=` on `drives` SHALL be shorthand for that law,
defaulting to a ratio of one and an offset of zero, and their values MAY
be plain numbers, declared-parameter tokens or derived formulas,
resolved against the declaring instance at realization exactly as a
child declaration's arguments are. Under a BROADCAST they SHALL be
resolved ONCE against the declaring instance and every copy SHALL get the
SAME affine law: a ratio names a value of the declaring class and has no
way to see a copy, and `law=` is what per-copy variation is stated with.

`law=` SHALL take a CALLABLE of two arguments, which the framework SHALL
call exactly ONCE for each relation it resolves to, at realization, with
the realized nodes that OWN the two coordinates — driver first, driven
second. The owner of a coordinate SHALL be: the
realized child for a node end; the realized descendant that declares the
named port or joint for a path end, or the named node itself when the
path ends on a node; the realized COPY for a broadcast end; and the
declaring instance itself for a port, a
joint, a derived coordinate or a driver of that class. A law function
MAY therefore read anything a realized node has — a built library
object, an index, a resolved parameter.

For an ordinary relation the callable SHALL be called once for each
realized instance of the declaring class; for a BROADCAST it SHALL be
called once per realized COPY, the copy being the node that owns the
driven coordinate, so a per-copy law reads the copy's own `index` and
needs no further argument. The callable's signature SHALL be unchanged
by a broadcast, and the framework SHALL inspect nothing about it to
decide what to pass.

The callable SHALL return a LAW: an object with a callable `forward`
taking the driver's value and returning the driven's, and OPTIONALLY a
callable `inverse` taking the driven's value and returning the
driver's. An `Affine` SHALL satisfy that protocol with both. A plain
function or lambda returned SHALL be taken as forward-only. The
framework SHALL inspect nothing else about a law: it holds no registry
of mechanism shapes, consults no attribute of a node class to find a
law, and never learns what a gear is.

A returned value that is not a law SHALL be refused at realization,
naming the relation, the callable and what it returned. `ratio=` or
`offset=` given together with `law=` SHALL be refused at class
definition.

#### Scenario: An affine relation written in place

- **WHEN** a class states `elbow_pulley.turn.drives(elbow_belt.travel,
  ratio=pitch_arc(117))` and the pulley's coordinate is bound to an
  angle
- **THEN** the belt's `travel` holds that angle multiplied by the ratio,
  in the belt's own unit

#### Scenario: A law reads the two realized arbors

- **WHEN** a class states `power.drives(centre, law=going_train)`, where
  `going_train(driver, driven)` returns
  `Affine(ratio=-driver.wheel_teeth / driven.pinion_teeth,
  offset=registration(driver.wheel_gap, driven.pinion_tip))`
- **THEN** the callable is called once per realized parent, with the two
  realized arbor nodes, and the returned `Affine` is the relation's law
  for that parent for every later run

#### Scenario: A law is called once per copy and is handed the copy

- **WHEN** a class declaring `beads = Bead().repeat(4)` states
  `earth.drives(beads.travel, law=earth_lift)`, where
  `earth_lift(driver, driven)` reads `driven.index`
- **THEN** the callable ran four times at realization, each call received
  that copy as its second argument and read its own index, and the four
  laws returned are the four copies' laws for every later run

#### Scenario: A ratio broadcasts unchanged to every copy

- **WHEN** the same class states `earth.drives(beads.travel, ratio=2.0)`
  and `earth` is bound to `3`
- **THEN** every copy's `travel` holds `6`, and the ratio was resolved
  once against the declaring instance

#### Scenario: A law runs once, not once per instant

- **WHEN** an assembly whose relation carries a `law=` callable is
  simulated at twenty instants
- **THEN** the callable ran once, at realization, and twenty runs used
  the law it returned

#### Scenario: An affine law inverts itself

- **WHEN** a relation carrying `Affine(ratio=-3.5, offset=12.0)` has
  only its DRIVEN end bound
- **THEN** the driver end is bound to `(driven - 12.0) / -3.5`, and the
  project wrote no second function for the reverse direction

#### Scenario: A law that is not a law is refused

- **WHEN** a `law=` callable returns a number
- **THEN** realization raises naming the relation, the callable and what
  it returned

#### Scenario: A ratio and a law together are refused

- **WHEN** a class body states `a.drives(b, ratio=2, law=some_law)`
- **THEN** class definition raises naming the relation and saying that
  a relation carries one law

### Requirement: A derived coordinate is a linear formula over coordinates

The system SHALL let a class body build a coordinate from other
coordinates with `+`, `-`, unary negation, and multiplication or
division by a number, a declared-parameter token or a derived formula:
`relative_elbow = art3.elbow - shoulder`, `left = wrist + 2 * tool`.
Multiplying or dividing two coordinates, and any other operator or
function over them, SHALL be refused at class definition naming both
operands and pointing at `law=`.

A derived coordinate SHALL BE a coordinate of the class: it SHALL carry
`drives` as every other end does, it SHALL be usable as either end of a
relation, it SHALL read on a realized instance as a bound value slot of
the same kind a declared port yields, and the class's port enumeration
SHALL report it under its name. Its domain SHALL be the domain its terms
share, and its unit the unit its terms state; terms whose domains
differ, or which state different units, SHALL be refused at class
definition naming the two terms that disagree.

The system SHALL solve a derived coordinate in both directions: its
value from its terms when every term is bound, and the one remaining
term from its value and the others when exactly one term is unbound.
Two unbound terms SHALL be refused by name, naming the formula and each
unbound term. Both directions SHALL be ordinary arithmetic, so a
symbolic term produces a symbolic result.

#### Scenario: A difference of two coordinates drives a pulley

- **WHEN** an upper arm declares `shoulder = Revolute(...)`, a child
  `art3` declaring `elbow`, and
  `relative_elbow = art3.elbow - shoulder`, then states
  `relative_elbow.drives(elbow_pulley.turn)`, and both joints are bound
- **THEN** the pulley's coordinate holds the difference, and reading
  `relative_elbow` on the instance yields that same value

#### Scenario: A derived coordinate solves backwards

- **WHEN** `relative_elbow = art3.elbow - shoulder` is bound by a
  relation and `shoulder` is bound by a driver, while `art3.elbow` is
  unbound
- **THEN** `art3.elbow` is bound to `relative_elbow + shoulder`, and the
  child's body is placed by it

#### Scenario: A differential is two formulas

- **WHEN** a wrist declares `wrist` and `tool` joints,
  `left = wrist + 2 * tool` and `right = wrist - 2 * tool`, and both
  joints are bound
- **THEN** the two derived coordinates hold the sum and the difference,
  and each may drive a pinion

#### Scenario: A non-linear formula is refused

- **WHEN** a class body writes `bad = wrist * tool`
- **THEN** class definition raises naming both operands and pointing at
  `law=`

#### Scenario: Two unknowns in one formula are refused

- **WHEN** a derived coordinate is bound while two of its terms are
  unbound and nothing else reaches them
- **THEN** solving raises naming the formula and both unbound terms

### Requirement: Relations are solved from the bound side, at the end of the owning simulate phase

The system SHALL ATTEMPT the relations of a class for one instance at
the end of that instance's simulate phase: after the author's
`simulate()` has returned and before the phase is popped — so that any
motion a relation causes is that assembly's motion, tagged with it and
swept before its next run, exactly as a hand-written rotation there is.
What that attempt cannot reach SHALL be DEFERRED to the enumeration's
own fixpoint rather than refused, under the requirement "Relations defer
to a whole-tree fixpoint". A relation the attempt CAN reach SHALL be
solved there and SHALL NOT be deferred, so nothing that solves in one
instance's phase moves out of it.

Every WIRING the class declared SHALL take part in the same solve, as a
forward-only relation carrying the identity law from the parent's
coordinate to the child's, binding through the same path and so
applying the child end's declared scale. A wiring SHALL therefore bind
in the same propagation as the relations rather than before it, so a
wiring whose source coordinate is itself solved by a relation — the
arbor coordinate a train solves, wired down into the wheel and the rod
that turn with it — binds once that relation has run, instead of
finding its source unbound. A wiring SHALL be a binder like any other:
a relation that would also bind its child end is a double binding, and
the rule that binding a wired child end by hand is refused is
unchanged.

Because a value slot keeps what was bound into it, the system SHALL
make freshness explicit. At the START of an assembly's simulate phase,
before the author's `simulate()` runs, the framework SHALL clear the
value and the binder record of every coordinate THIS assembly bound
DURING ITS PREVIOUS SIMULATE PHASE — which it recorded when it bound
them — whatever bound it there: a relation, a wiring, a derived formula,
or the author's own `simulate()`. The value and the MOTION of one
binding SHALL be dropped in the same moment and by the same rule, so a
coordinate can never go on holding a value whose operations the sweep
has already removed. The only values present when the solve runs are
therefore those bound during the current enumeration of the tree: by
this author's `simulate()`, by an ancestor's wiring or relation already
applied in this enumeration, or by a driver read.

Because a coordinate this instance's own attempt reads as an END is not
necessarily the current enumeration's value — tree order runs an
ancestor's own attempt before the descendant that owns a deferred
source has cleared and rebound it, so at the moment of the read that
source may still hold what the PREVIOUS enumeration left there — an end
whose value is not yet fresh for this enumeration SHALL read as UNBOUND
for as long as the assembly that bound it is still due to attempt again
before this pass concludes: that assembly's own attempt currently
running, or one of that assembly's own descendants'. It SHALL read as
bound, unchanged, when nothing left to run in this pass will touch it
again — a value bound outside any enumeration, or one whose binder's
assembly lies outside the subtree the current pass walks, exactly as a
node the walker revisits after its owning enumeration has already
closed is allowed to trust what is already there. This SHALL NOT change
which relation is deferred versus solved once a pass concludes, and
SHALL NOT change `_enum_marker`'s own meaning or the clear-with-the-
motion rule above: it decides only what one attempt, mid-pass, is
allowed to treat as already answered.

A binding made OUTSIDE any simulate phase — in `__init__`, in a test, or
through a `render()` no walker drove — SHALL NOT be recorded and SHALL
NOT be cleared, exactly as an operation applied outside a phase is never
swept. Two assemblies that bind coordinates of one node SHALL clear only
their own. Between one enumeration and the next a coordinate SHALL go on
reading what the last enumeration bound, so a test, a serializer or a
pose capture that reads a coordinate after a walk reads the pose that
walk produced.

Solving SHALL proceed as: INVENTORY, which of the coordinates the
class's relations and wirings name currently hold a value, and what
bound each; then PROPAGATE, applying every relation with exactly one
bound end from that end — through the law's `forward` when the driver
end is bound and through its `inverse` when the driven end is —
applying every wiring whose source is bound, and solving every derived
coordinate with at most one unknown, repeatedly, until nothing changes;
then REFUSE. Within one pass the order SHALL be declaration order, and
the result SHALL NOT depend on the order the author wrote the relations
in: a train written from the power arbor forwards SHALL solve
backwards from the one arbor `simulate()` bound, with no reordering.

A relation SHALL bind through the same path an author's binding takes,
so the driven end's declared scale applies as it always does, a joint's
declared range refuses an out-of-range numeric value as it always does,
and a joint's body is placed by the same operations, with the same
animator tag and the same sweep, as when an author binds it. The
framework SHALL perform no unit conversion of its own: what converts is
the ratio or law the author wrote.

A BROADCAST relation SHALL be resolved into ONE RELATION PER REALIZED
COPY, and those relations SHALL take part in the solve exactly as any
other relation does: each is bound, refused and recorded on its own. They
SHALL occupy the position of the declaration in the pass order, in COPY
ORDER within it, so declaration order remains the order of the pass. A
broadcast over a repeat that realized NO copies SHALL be zero relations:
it SHALL bind nothing and refuse nothing. A broadcast SHALL cover every
copy the repeat REALIZED, whether or not a `render()` later omitted it,
because the ends of a relation resolve at realization. A NAMED broadcast
read off a realized instance SHALL yield the tuple of its per-copy
records, in copy order, where a named ordinary relation yields one
record; every message about one of those records SHALL name the copy it
applies to as well as the relation as written.

Because each class attempts its own relations in its own instance's
phase, and every instance's phase runs before its children's, a relation
declared on an ancestor and reaching a descendant's coordinate by path
SHALL be solved BEFORE that descendant's `simulate()` runs and before
that descendant's own relations are attempted, so an ancestor's value is
a descendant's boundary condition. A relation whose two ends lie in
different subtrees SHALL be solved by the class that states it, both
ends resolving from that instance.

Values SHALL pass through a relation unresolved: a symbolic driver read
or animation-time expression driven through an `Affine` or a derived
formula SHALL publish an expression in the serialized document, which
the viewer evaluates with the expression math it already has, and
SHALL be a plain number under `set_state`, `set_keyframe` and the test
runner.

#### Scenario: A train solves backwards from the escapement

- **WHEN** an assembly declares four arbors and states
  `power.drives(centre, law=...)`, `centre.drives(third, law=...)` and
  `third.drives(escape, law=...)` in that order, and its `simulate()`
  binds only `escape.turn`
- **THEN** `third`, `centre` and `power` are each bound through the
  inverse of their law, every arbor's body is placed, and the order the
  relations were written in changed nothing

#### Scenario: A tooth count is the only thing that has to change

- **WHEN** one arbor's declared tooth count is changed and nothing else
  in the model is edited
- **THEN** every coordinate the train solves changes accordingly, and a
  test that reads the hands against elapsed time notices

#### Scenario: The second run re-solves from the author's binding

- **WHEN** the same train is enumerated at three successive instants,
  its `simulate()` binding only `escape.turn` each time
- **THEN** at each instant the coordinates this assembly solved in the
  previous run were cleared before the author's `simulate()` ran, the
  train re-solved from the fresh escapement value, and nothing was
  refused as doubly bound and nothing stayed frozen at the first
  instant's angles

#### Scenario: A wiring whose source a relation solves binds in the same pass

- **WHEN** an assembly solves an arbor's coordinate through a relation
  and that arbor declares wirings from that coordinate down into the
  wheel and the rod that turn with it
- **THEN** both children hold the solved value after the run, the
  wiring having bound once its source was solved rather than refusing
  an unbound source

#### Scenario: A relation runs with the wirings, after the author's simulate

- **WHEN** an assembly binds one joint in `simulate()`, declares a
  wiring into a child, and states a relation from that joint to another
  child's joint
- **THEN** the author's binding is present when the solve begins, the
  wiring and the relation are both applied in it, and the motion they
  cause is tagged with that assembly and swept before its next run

#### Scenario: A root driver reaches a joint three levels down

- **WHEN** a root declares `art3 = Driver(...)` and states
  `art3.drives(shoulder.art2.art3.elbow)`
- **THEN** the elbow is bound from the driver's value on every run, the
  forearm is placed about its own axis, and no intermediate class
  declares a port

#### Scenario: A relation publishes an expression

- **WHEN** a tree whose coordinates are related by `Affine` laws and a
  derived formula is serialized with nothing bound
- **THEN** the operations of every related body carry expressions in
  the driver ids and `$t`, `set_keyframe` makes them numeric and
  `clear_keyframe` symbolic again

#### Scenario: A relation into a scaled port converts once

- **WHEN** a relation drives a port that declares a scale
- **THEN** the port holds the relation's result multiplied by that
  scale, exactly as a wiring or a `connect()` gives, and the framework
  applied no other conversion

#### Scenario: A broadcast solves in declaration order, copy by copy

- **WHEN** a class declares a relation, then a broadcast over four
  copies, then a third relation, and the assembly is simulated
- **THEN** the six relations solved are the first, the four copies in
  index order, and the third, and reading the named broadcast off the
  instance yields four records in copy order

#### Scenario: A broadcast over an empty repeat states nothing

- **WHEN** a class declaring `beads = Bead().repeat(count)` with a
  resolved `count` of zero states `earth.drives(beads.travel)` and binds
  `earth`
- **THEN** the assembly simulates with nothing bound by that relation and
  nothing refused

#### Scenario: A relation places a repeated child

- **WHEN** an assembly stating a relation between two of its own
  coordinates is repeated, so several identical assemblies are realized
- **THEN** each realized assembly solves its own relation against its
  own bound values, and each places its own bodies

#### Scenario: A relation an ancestor's value reaches is not deferred

- **WHEN** a root states a relation binding a coordinate three levels
  down and that level's own class reads the coordinate in its
  `simulate()`
- **THEN** the root's relation was solved in the root's own phase, the
  descendant's `simulate()` read the bound value, and nothing was
  deferred to the enumeration's fixpoint

#### Scenario: A phase clears the value it bound by hand

- **WHEN** an assembly's `simulate()` binds a child's joint under an
  `if <coordinate> is None:` guard and the tree is enumerated three
  times
- **THEN** each run finds the coordinate unbound, binds it and places
  the body, so the body stands at the bound value on every run instead
  of standing at rest holding a stale number

#### Scenario: A deferred relation's source is read fresh on every re-pose

- **WHEN** a root states a relation sourced from a coordinate a
  descendant's own relation solves — the shape "An ancestor sources
  from a coordinate a descendant solves" — and the tree is re-posed
  three or more times with different values for whatever the descendant
  ultimately reads its source from
- **THEN** after EVERY re-pose the driven end equals the law applied to
  the source's CURRENT enumeration's value, never the value the source
  held at the end of the PREVIOUS enumeration, because the root's own
  attempt — which runs before the descendant has cleared and rebound
  that source this enumeration — reads a value still carrying the
  previous enumeration's mark as UNBOUND and defers, and the pass's own
  fixpoint solves it only once the descendant's fresh rebind has landed

### Requirement: Three refusals keep a wrong drive network from becoming a pose

The system SHALL refuse, by name, each of the following, and SHALL name
in every message the node paths of the ends, the relation as written —
its name when it has one — and the coordinates involved. A DOUBLY BOUND
coordinate SHALL be refused at the moment the relations of the instance
that would bind it are attempted: it is a contradiction and not a
question of timing, so its message stays next to the class that caused
it. The other two SHALL be refused at the END of the enumeration's
fixpoint, once every assembly's phase has run and nothing changes any
more, because until then a statement elsewhere in the tree may still
reach the coordinate:

- an UNREACHED COORDINATE: a coordinate a relation names that no
  binding and no relation reached when propagation stopped changing
  anything, its message saying what it was waiting for, and for a
  derived formula with two unknowns naming the formula and both;
- a DOUBLY BOUND coordinate: a relation would bind a coordinate that
  something else already bound during this enumeration of the tree —
  the author's `simulate()`, a wiring, or another relation — or a
  relation both of whose ends were already bound by other binders. Two
  relations that would give the SAME value SHALL be refused as well:
  the framework SHALL NOT compare two values to decide whether a
  redundant statement agrees, because they are ordinarily symbolic
  expressions, and the message SHALL name both binders;
- a NOT INVERTIBLE relation: the driven end is the bound one and the
  relation's law offers no inverse, or is an affine law whose ratio is
  numerically zero, or the relation is one copy of a BROADCAST — which
  SHALL never be read backwards whatever its law offers, because the
  copies hold one value each and one source cannot be derived from them
  without comparing values, which the framework does not do. The message
  SHALL say which of those reasons applies, and for a broadcast SHALL
  name the copy.

Each error SHALL be of its own kind, exported from the couplings
module, so a project or a test can catch exactly one.

Every message SHALL name the class that STATED the relation, whether the
relation was solved in its own instance's phase or in the enumeration's
fixpoint, and a message about a deferred relation SHALL say that it was
deferred until the descendants had solved.

#### Scenario: A coordinate nothing reaches is refused

- **WHEN** an assembly states a relation between two coordinates and
  binds neither, and no other relation reaches either
- **THEN** solving raises naming the relation, both node paths and both
  coordinates, and says nothing bound either end

#### Scenario: An author binding and a relation are two binders

- **WHEN** an assembly's `simulate()` binds a child's joint that a
  relation of the same class also drives
- **THEN** solving raises naming the coordinate, the relation and the
  author's binding as the two binders

#### Scenario: A wired coordinate driven by a relation is refused

- **WHEN** a class both wires its coordinate into a child's joint and
  states a relation driving that same joint
- **THEN** solving raises naming the wiring and the relation as the two
  binders

#### Scenario: Two relations reaching one coordinate are refused

- **WHEN** two relations of one class drive the same coordinate, even
  with laws that would give the same value
- **THEN** solving raises naming both relations and saying the framework
  does not compare two values to decide whether they agree

#### Scenario: A non-invertible law needed backwards is refused

- **WHEN** a relation carrying a forward-only `law=` has only its driven
  end bound
- **THEN** solving raises naming the relation, its law and both ends,
  and says the law has no inverse

#### Scenario: A broadcast is never read backwards

- **WHEN** a class states `earth.drives(beads.travel)` over four copies,
  leaves `earth` unbound, and its `simulate()` binds one copy's `travel`
- **THEN** solving raises the not-invertible error naming the relation,
  the copy, the bound coordinate and the fact that a broadcast is read
  forward only, and it says so even though the identity law it carries
  would invert

#### Scenario: A forward-only law used forwards is fine

- **WHEN** the same relation has its DRIVER end bound instead
- **THEN** the driven end is bound through the law's forward face and
  nothing is refused

### Requirement: Each end of a relation resolves to a coordinate, or to one per copy of a repeated child

The system SHALL resolve both ends of a relation to a coordinate — the
driven end to ONE COORDINATE PER REALIZED COPY when it passes through a
repeated child, which makes the relation a BROADCAST. The
kinds of end SHALL be:

- a PORT or JOINT declared on the class stating the relation, resolving
  to that instance's own coordinate;
- a CHILD DECLARATION, resolving to the realized child's ONE joint's
  coordinate;
- a PATH REFERENCE — `anchor.turn`, `motion_works.cannon.turn`,
  `shoulder.art2.art3.wrist` — resolving to the coordinate of the
  realized descendant the path names;
- a BROADCAST — a path one of whose segments is a REPEATED child
  declaration, `eccentric_bearings.orbit`, `column.beads.travel`,
  `legs.femur.lift` — resolving to ONE coordinate PER REALIZED COPY,
  and permitted as the DRIVEN end only;
- a `Driver` declaration, resolving to the driver's value, which SHALL
  be a SOURCE only;
- a DERIVED COORDINATE of the class.

A PATH REFERENCE SHALL be read segment by segment, and a COORDINATE at
its end SHALL occupy as many TRAILING SEGMENTS as the name the port
enumerator reports it under has dot-separated parts: one for a plain port
or the coordinate of a joint that owns one, and two for a coordinate of a
joint that owns several — `chassis.pose.roll` names the realized child
`chassis` and its coordinate `pose.roll`. Every segment before those
SHALL be a child the previous segment's class declares, as it is today.

A path MAY pass through AT MOST ONE repeated child declaration, at any
position, and a path that does SHALL be a BROADCAST: it names the same
coordinate of every copy that repeat realized, in copy order. A repeated
declaration named as an end without a further segment SHALL mean the ONE
joint of the repeated class, by the same rule a child declaration does.
A path through TWO repeated declarations SHALL be refused at class
definition, naming both repeated segments and saying that a broadcast
fans out over one repeat. A path through a LIST-HELD child SHALL stay
refused as it is today, naming the list and saying that its children are
named one by one.

A BROADCAST SHALL be refused at class definition when it is named as the
SOURCE end, naming the path as written, the repeated declaration and its
class, and saying that a relation's source is one value while the copies
hold one each. A BROADCAST SHALL likewise be refused as a term of a
derived coordinate, naming the formula and the path.

A path that STOPS on a joint owning several coordinates — `chassis.pose`
— SHALL be refused at class definition naming the joint and listing its
coordinates, with the advice to name one, because a relation has one end.
A path naming a part that such a joint does not own — `chassis.pose.twist`
— SHALL be refused the same way, listing what it does own.

A child declaration named as an end SHALL mean the one joint of that
child's class. A child whose class declares NO joint, or more than one,
SHALL be refused at class definition, naming the child attribute, its
class, and the joints that class declares, with the advice to name the
coordinate. A child whose class declares exactly one joint, that joint
owning several coordinates, SHALL be refused the same way, listing that
joint's coordinates.

A relation SHALL bind either end through the SAME path an author's
assignment takes, whatever the coordinate's name is: a coordinate whose
name has more than one segment SHALL be bound through the joint that owns
it, and never by setting an attribute of that name on the node.

A `Driver` named as the DRIVEN end SHALL be refused at class
definition, naming the driver, because a driver's value belongs to the
bound snapshot and is set by `set_state`.

The ends SHALL resolve at realization, at the end of the instance's
construction and after its children are realized, since an end may be a
child or a descendant of one. Whatever the classes alone decide SHALL
be refused AT CLASS DEFINITION — an attribute no class along a path
declares, a node end with the wrong number of joints, a driver as a
driven end, a path through a list-held child, a broadcast named as the
source end, a path through two repeated children, `ratio=` or
`offset=` given together with `law=` — and whatever depends on the
instance SHALL be refused AT REALIZATION, naming the relation, the path
as written, the node the walk stopped at and what that node declares.

#### Scenario: A node end is its one joint

- **WHEN** an assembly declares `power = TrainArbor(index=0)` and
  `centre = TrainArbor(index=1)`, `TrainArbor` declaring exactly one
  `Revolute` named `turn`, and states `power.drives(centre)`
- **THEN** the relation's ends are the two realized arbors' `turn`
  coordinates, and binding one places the other

#### Scenario: A node with two joints is refused

- **WHEN** a class body states `wrist.drives(tool)` where `tool`'s class
  declares two joints, or none
- **THEN** class definition raises naming the child attribute, its
  class and the joints it declares, with the advice to name the
  coordinate

#### Scenario: A path reaches a descendant's coordinate

- **WHEN** a root states `art3.drives(shoulder.art2.art3.wrist)`, three
  levels of declared children below it
- **THEN** the relation's driven end is the realized wrist coordinate
  of that descendant, and no intermediate class declared or forwarded a
  port for it

#### Scenario: A driver may not be driven

- **WHEN** a class body states `centre.turn.drives(some_driver)`
- **THEN** class definition raises naming the driver and saying its
  value belongs to the bound snapshot

#### Scenario: A path through a repeated child is refused

- **WHEN** a class declaring `units = Unit().repeat(count)` states
  `units.turn.drives(power)`, naming the repeated child as the SOURCE
- **THEN** class definition raises naming the path as written, the
  repeated declaration and its class, and saying that a relation's source
  is one value while the copies hold one each

#### Scenario: A repeated driven end is one relation per copy

- **WHEN** a class declaring `beads = Bead().repeat(4)` and a coordinate
  `earth` states `earth.drives(beads.travel)`, and `earth` is bound
- **THEN** four relations are solved, one per realized copy, each copy's
  `travel` holds the value and each copy's body is placed by it

#### Scenario: A repeated node end is the copies' one joint

- **WHEN** the same class states `earth.drives(beads)`, `Bead` declaring
  exactly one joint
- **THEN** the relation's driven ends are the four realized copies'
  coordinates, exactly as if the joint had been named

#### Scenario: A repeat one level down is one fan-out

- **WHEN** a root declaring `column = Column()`, `Column` declaring
  `beads = Bead().repeat(4)`, states `drive.drives(column.beads.travel)`
- **THEN** class definition succeeds and four relations are solved, one
  per copy of that realized column

#### Scenario: Two repeated segments in one path are refused

- **WHEN** a class states `yaw.drives(legs.joints.spin)`, where `legs`
  and `joints` are both repeated declarations
- **THEN** class definition raises naming both repeated segments and
  saying that a broadcast fans out over one repeat

#### Scenario: A list-held child is still refused

- **WHEN** a class states `power.drives(plates)`, or
  `power.drives(frame.plates.turn)` reaching a list-held declaration one
  level down
- **THEN** class definition raises naming the list-held declaration and
  saying its children carry their own arguments and are named one by
  one, and the message is not the two-repeat one

#### Scenario: A path that does not resolve on the instance fails at realization

- **WHEN** a path names a child of a class realized through an ordinary
  constructor that does not produce it
- **THEN** realization raises naming the relation, the path as written,
  the node the walk stopped at and what that node declares

#### Scenario: A path reaches one coordinate of a multi-coordinate joint

- **WHEN** a root declaring `chassis = Chassis()`, `Chassis` declaring
  `pose = Free()`, states `tilt.drives(chassis.pose.pitch)`
- **THEN** the relation's driven end is that realized chassis's
  `pose.pitch` coordinate, binding it places the chassis, and the other
  five coordinates are untouched

#### Scenario: A path stopping on a multi-coordinate joint is refused

- **WHEN** a class body states `tilt.drives(chassis.pose)`, or
  `tilt.drives(chassis.pose.twist)`
- **THEN** class definition raises naming the joint and listing the
  coordinates it owns, with the advice to name one of them

### Requirement: Relations defer to a whole-tree fixpoint

The system SHALL treat one ENUMERATION of a tree as one solve. An
enumeration begins when a `render()` is called with no enumeration in
progress; the assembly that call names OWNS the enumeration and SHALL
drive the simulate phase of every assembly in the subtree it renders,
parents before children and in declaration order among siblings, before
that `render()` returns. Each assembly's phase SHALL be exactly what it
is for one node today — sweep, rest, clear, the author's `simulate()`,
then the attempt at its own relations, wirings and derived coordinates —
and each SHALL run ONCE per enumeration.

An item its own instance's attempt could not resolve SHALL be DEFERRED
to the enumeration rather than refused. The system SHALL defer:

- a relation record with neither end bound;
- a relation record whose driven end is bound and whose law offers no
  inverse, and one copy of a broadcast whose driven end is bound;
- a derived coordinate that holds a value while more than one of its
  terms is unbound;
- a wiring whose source coordinate is unbound.

The system SHALL NOT defer a DOUBLY BOUND coordinate or a value a
joint's declared range refuses: neither is a question of timing.

Once every assembly's phase has run, the enumeration SHALL PROPAGATE
over every deferred item of the whole tree — applying each relation with
exactly one bound end from that end, each wiring whose source is now
bound, and each derived coordinate with at most one unknown —
repeatedly, until nothing changes; and only THEN refuse. Each deferred
item SHALL be applied under the phase of the assembly that STATED it, so
the motion it causes carries that assembly's animator tag, is swept
before that assembly's next run, and is cleared by that assembly's own
next phase, exactly as it would have been had the item resolved in its
own phase.

The order of that propagation SHALL be TREE ORDER — the order the
assemblies' phases ran — and within one assembly the declaration order
of its items, a broadcast's copies in copy order at the position of
their declaration. The result SHALL NOT depend on which assembly
deferred first.

Because the enumeration reads a body's geometry only after every phase
has run, a coordinate a deferred relation binds SHALL be bound before
anything in the enumeration reads the body it moves.

An assembly rendered ALONE — a component under test, or a subtree a
walker enters directly — SHALL own its own enumeration over its own
subtree, and a relation of that subtree that needs a coordinate outside
it SHALL be refused at the end of it, exactly as it is refused today.

#### Scenario: A chain stated one level down solves

- **WHEN** a movement states `power.drives(train.centre)` while the
  train's own class states `centre.drives(third)` and
  `third.drives(escape)`, and the movement's `simulate()` binds
  `train.escape.turn`
- **THEN** the train's three relations and the movement's one all solve
  from that one binding, every arbor is placed, and nothing is refused

#### Scenario: An ancestor sources from a coordinate a descendant solves

- **WHEN** a root states
  `z_axis.actuator.column.travel.drives(body.lower_strut.swing, law=…)`
  and `Axis`'s own relation is what binds `column.travel` from the step
  count its `simulate()` binds
- **THEN** the root's relation is deferred, solved once the axis has
  solved, and the strut is placed at every pose

#### Scenario: A deferred relation moves a body the walk has not read yet

- **WHEN** the root of a tree with two subtrees states a relation whose
  driven end is in the FIRST subtree and whose source a relation of the
  SECOND subtree solves, and the tree is assembled
- **THEN** the body in the first subtree carries the deferred relation's
  motion in the geometry the walk composed for it

#### Scenario: A wiring whose source a descendant solves binds

- **WHEN** an assembly wires its own coordinate down into a child and
  that coordinate is bound by a relation of a DESCENDANT
- **THEN** the wiring is deferred and applied in the enumeration's
  fixpoint, and the child holds the value rather than the wiring
  refusing an unbound source

#### Scenario: A contradiction is refused where it is stated

- **WHEN** an assembly's `simulate()` binds a child's joint that a
  relation of the same class also drives
- **THEN** the doubly-bound refusal is raised in that assembly's own
  phase, naming that class, and not deferred to the end of the
  enumeration

#### Scenario: Each phase runs once per enumeration

- **WHEN** a three-level tree is assembled
- **THEN** each assembly's `simulate()` ran exactly once, the
  enumeration's fixpoint ran once after all of them, and the walker's
  descent re-ran no phase

### Requirement: A read of a coordinate a relation binds is refused, never an empty slot

A coordinate a relation, a derived formula or a wiring binds is UNBOUND
while the `simulate()` of the class that states it runs, because
`simulate()` runs first and the relations are solved after it returns.
The system SHALL NOT let such a read pass silently as an empty slot.

The system SHALL RECORD every read of a coordinate slot holding no
value made while a simulate phase is running, with the coordinate's
declared name, the node that owns it, the class whose `simulate()` was
running, and the source location of the read. At the end of the
enumeration, a recorded read whose coordinate was AFTERWARDS bound by a
relation, a derived coordinate or a wiring SHALL be refused by name,
naming the coordinate, the class that read it, what bound it, and the
order: the author's `simulate()` runs first, the relations of that class
are solved after it returns, and a descendant's after that.

A recorded read whose coordinate the AUTHOR then bound SHALL NOT be
refused: reading a coordinate to discover that nothing has bound it and
binding it is a rest default, not a mistake. A recorded read of a
coordinate nothing ever bound SHALL NOT be refused by this rule either;
it is the unreached coordinate the solver already refuses by its own
name.

A coordinate a class's OWN relation binds and a DERIVED coordinate the
class declares SHALL be the same case, and so SHALL a coordinate a
DESCENDANT's relations solve, read from an ancestor's `simulate()`. The
whole-tree fixpoint SHALL NOT make any of them readable earlier: it
makes the SENTENCE statable, not the value early.

#### Scenario: A class reads its own derived coordinate

- **WHEN** a class declares `left = wrist + 2 * tool`, binds `wrist` and
  `tool` in its `simulate()`, and rotates a pulley by `self.left.value`
  in the same method
- **THEN** the enumeration refuses naming `left`, the class, the derived
  coordinate that bound it and the two-phase order, instead of turning
  the pulley by nothing

#### Scenario: A class reads a coordinate its own relation binds

- **WHEN** a class states `steps.drives(rotor.spin, ratio=0.5)`, binds
  `steps` in its `simulate()` and reads `self.rotor.spin.value` there
- **THEN** the enumeration refuses naming the coordinate, the relation
  that bound it and the same order

#### Scenario: A rest-default guard is not refused

- **WHEN** an assembly's `simulate()` reads a coordinate that is the
  SOURCE end of one of its own relations, finds it unbound and binds it
  to a default
- **THEN** nothing is refused, the relation solves forward from the
  default, and the body stands at it

#### Scenario: An ancestor reads a coordinate a descendant solves

- **WHEN** a parent's `simulate()` reads a coordinate that only a
  child's own relations bind
- **THEN** the enumeration refuses naming both classes and the order,
  rather than reordering the tree to make the read work

