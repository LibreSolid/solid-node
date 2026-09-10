## ADDED Requirements

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

## MODIFIED Requirements

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
