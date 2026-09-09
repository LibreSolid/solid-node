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
its law, and which direction it was solved in on the last run.

A relation SHALL be recorded even when it is written inside a class-body
comprehension, where the executing frame reports a copy of the
declaring namespace rather than the namespace itself.

A class's relations SHALL be enumerable off the class without
constructing an instance, base-first through the inheritance chain: a
subclass ADDS to the relations of its bases rather than overriding
them, because a relation is a statement and not a name.

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

### Requirement: Each end of a relation resolves to one coordinate

The system SHALL resolve both ends of a relation to a coordinate. The
kinds of end SHALL be:

- a PORT or JOINT declared on the class stating the relation, resolving
  to that instance's own coordinate;
- a CHILD DECLARATION, resolving to the realized child's ONE joint's
  coordinate;
- a PATH REFERENCE — `anchor.turn`, `motion_works.cannon.turn`,
  `shoulder.art2.art3.wrist` — resolving to the coordinate of the
  realized descendant the path names;
- a `Driver` declaration, resolving to the driver's value, which SHALL
  be a SOURCE only;
- a DERIVED COORDINATE of the class.

A child declaration named as an end SHALL mean the one joint of that
child's class. A child whose class declares NO joint, or more than one,
SHALL be refused at class definition, naming the child attribute, its
class, and the joints that class declares, with the advice to name the
coordinate.

A `Driver` named as the DRIVEN end SHALL be refused at class
definition, naming the driver, because a driver's value belongs to the
bound snapshot and is set by `set_state`.

The ends SHALL resolve at realization, at the end of the instance's
construction and after its children are realized, since an end may be a
child or a descendant of one. Whatever the classes alone decide SHALL
be refused AT CLASS DEFINITION — an attribute no class along a path
declares, a node end with the wrong number of joints, a driver as a
driven end, a path through a repeated or list-held child, `ratio=` or
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
  `power.drives(units.turn)`
- **THEN** class definition raises naming the repeated declaration and
  advising that the relation be stated inside the repeated class

#### Scenario: A path that does not resolve on the instance fails at realization

- **WHEN** a path names a child of a class realized through an ordinary
  constructor that does not produce it
- **THEN** realization raises naming the relation, the path as written,
  the node the walk stopped at and what that node declares

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
child declaration's arguments are.

`law=` SHALL take a CALLABLE of two arguments, which the framework SHALL
call exactly ONCE for each realized instance of the declaring class, at
realization, with the realized nodes that OWN the two coordinates —
driver first, driven second. The owner of a coordinate SHALL be: the
realized child for a node end; the realized descendant that declares the
named port or joint for a path end, or the named node itself when the
path ends on a node; and the declaring instance itself for a port, a
joint, a derived coordinate or a driver of that class. A law function
MAY therefore read anything a realized node has — a built library
object, an index, a resolved parameter.

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

The system SHALL solve the relations of a class for one instance at the
end of that instance's simulate phase: after the author's `simulate()`
has returned and before the phase is popped — so that any motion a
relation causes is that assembly's motion, tagged with it and swept
before its next run, exactly as a hand-written rotation there is.

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
through a wiring or a relation in its previous run — which it recorded
when it bound them — so that the only values present when the solve
runs are those bound during the current walk of the tree: by this
author's `simulate()`, by an ancestor's wiring or relation already
applied in this walk, or by a driver read. A value an author's own code
bound in an earlier run and did not bind in this one SHALL NOT be
cleared: an author's binding is the author's responsibility, exactly as
it is today.

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

Because each class solves its own relations in its own instance's
phase, a relation declared on an ancestor and reaching a descendant's
coordinate by path SHALL be solved BEFORE that descendant's own
relations are, so an ancestor's value is a descendant's boundary
condition. A relation whose two ends lie in different subtrees SHALL be
solved by the class that states it, both ends resolving from that
instance.

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

#### Scenario: A relation places a repeated child

- **WHEN** an assembly stating a relation between two of its own
  coordinates is repeated, so several identical assemblies are realized
- **THEN** each realized assembly solves its own relation against its
  own bound values, and each places its own bodies

### Requirement: Three refusals keep a wrong drive network from becoming a pose

The system SHALL refuse, by name and at the moment the relations of an
instance are solved, each of the following, and SHALL name in every
message the node paths of the ends, the relation as written — its name
when it has one — and the coordinates involved:

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
- a NOT INVERTIBLE law: the driven end is the bound one and the
  relation's law offers no inverse, or is an affine law whose ratio is
  numerically zero.

Each error SHALL be of its own kind, exported from the couplings
module, so a project or a test can catch exactly one.

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

#### Scenario: A forward-only law used forwards is fine

- **WHEN** the same relation has its DRIVER end bound instead
- **THEN** the driven end is bound through the law's forward face and
  nothing is refused
