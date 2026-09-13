## MODIFIED Requirements

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

A RUNNING SIMULATION is a binder kind of its own (the `ports`
capability's `RunBinder`), and the solver SHALL recognize it. A relation
ALL of whose driven ends are run-bound SHALL be recorded as solved BY THE
RUN, in neither direction, whatever its source ends hold: the run
integrated it, and applying it again would bind a coordinate the run
owns. A relation whose driven ends are not run-bound SHALL solve as
today from its bound side; where that would bind a run-bound SOURCE
backward it SHALL be refused as doubly bound naming the run as the other
binder. A wiring whose target is run-bound SHALL likewise be recorded as
applied by the run; a wiring whose target is a plain port SHALL apply
from a run-bound source as from any bound source. A derived coordinate
whose terms are run-bound SHALL be computed forward and bound as the
formula, exactly as today; the run checks the formula's consistency on
its own side. Every message that names a binder SHALL describe the run
as the running simulation.

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
applied in this enumeration, or by a driver read — and those a running
simulation binds. A run-bound slot SHALL be EXEMPT from the clear: the
run bound it outside any phase, owns its history and rebinds it on every
tick, so the freshness rule SHALL leave its value and binder alone
whatever enumeration last touched it, and an end that is run-bound SHALL
read as BOUND at every attempt, before any question of freshness is
asked.

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

A relation whose ends name SEVERAL coordinates SHALL be applied when
EVERY source end is bound and no driven end is, through the law's
`forward` over all its sources, binding all its driven ends together; it
SHALL NOT be applied while any source is unbound, and it SHALL NEVER be
applied backwards. All its driven ends SHALL be CLAIMED before any of
them is bound, so a driven end something else already bound is refused
without leaving part of one law applied.

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

#### Scenario: A relation of several ends waits for its last source

- **WHEN** a class states
  `(x & y & z).drives((rod.spin, rod.lean, rod.swing, rod.rise), law=delta_rod)`
  and its `simulate()` binds `x` and `y` while a relation elsewhere in
  the tree binds `z`
- **THEN** nothing was bound while `z` was unbound, and the four driven
  ends were bound together once it was

#### Scenario: One doubly bound target leaves the others untouched

- **WHEN** the same class's `simulate()` binds `rod.swing` by hand and
  all three sources are bound
- **THEN** solving raises the doubly-bound refusal naming `rod.swing`,
  the relation and the author's binding, and `rod.spin`, `rod.lean` and
  `rod.rise` were not bound by the relation

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

#### Scenario: A run-bound coordinate survives the freshness clear

- **WHEN** a running simulation binds every joint coordinate of a train
  whose rest render had solved them through relations, and the tree is
  enumerated at three successive ticks
- **THEN** no phase clears a run-bound slot, every relation into a
  run-bound coordinate is recorded as solved by the run, and nothing is
  refused as doubly bound or unreached

#### Scenario: A wiring into a run-bound joint is the run's

- **WHEN** an arbor's joint coordinate is run-bound and the arbor wires it
  down into a rod's joint and a wheel's plain port
- **THEN** the rod's joint is recorded as applied by the run and holds
  the run's value, and the wheel's port is bound from the run-bound source
  exactly as from any bound source

#### Scenario: A backward solve into a run-bound source is refused

- **WHEN** a relation's driven end is a plain port the author's
  `simulate()` binds and its source is a coordinate the run owns
- **THEN** solving raises the doubly-bound refusal naming the relation,
  the author's binding and the running simulation

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
  derived formula with two unknowns naming the formula and both. For a
  relation naming SEVERAL SOURCES the message SHALL name exactly the
  sources that are unbound, and not the relation's ends at large,
  because a relation whose other sources are bound is waiting for those
  and nothing else;
- a DOUBLY BOUND coordinate: a relation would bind a coordinate that
  something else already bound during this enumeration of the tree —
  the author's `simulate()`, a wiring, another relation, or the running
  simulation that owns it — or a relation both of whose ends were
  already bound by other binders, a relation all of whose driven ends the
  run owns excepted, since the run solved it. Two
  relations that would give the SAME value SHALL be refused as well:
  the framework SHALL NOT compare two values to decide whether a
  redundant statement agrees, because they are ordinarily symbolic
  expressions, and the message SHALL name both binders, the running
  simulation described as such when it is one of them;
- a NOT INVERTIBLE relation: the driven end is the bound one and the
  relation's law offers no inverse, or is an affine law whose ratio is
  numerically zero, or the relation is one copy of a BROADCAST, or the
  relation NAMES SEVERAL COORDINATES at either end — neither of the
  last two SHALL ever be read backwards whatever its law offers, because
  in both the values on one side cannot be recovered from the other
  without comparing or solving values, which the framework does not do.
  The message SHALL say which of those reasons applies, for a broadcast
  SHALL name the copy, and for a relation of several ends SHALL name the
  bound driven end and the sources still unbound.

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

#### Scenario: A relation of several sources names the unbound ones

- **WHEN** a relation of three sources has two of them bound and nothing
  reaches the third, and its driven ends are unbound
- **THEN** the enumeration raises the unreached-coordinate error naming
  the relation and the ONE unbound source, not all three

#### Scenario: A relation of several ends is never read backwards

- **WHEN** a relation of two sources and two driven ends has one driven
  end bound by the author and a source unbound
- **THEN** the enumeration raises the not-invertible error naming the
  relation, the bound driven end and the unbound source, and saying that
  a relation naming several ends is read forward only

#### Scenario: A forward-only law used forwards is fine

- **WHEN** the same relation has its DRIVER end bound instead
- **THEN** the driven end is bound through the law's forward face and
  nothing is refused

#### Scenario: The running simulation is named as a binder

- **WHEN** an assembly's `simulate()` binds a joint coordinate the running
  simulation owns
- **THEN** the doubly-bound refusal names the coordinate, the assembly's
  class and "the running simulation" as the two binders
