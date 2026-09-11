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
