# ADR-096: A Relation Broadcasts Over a Repeated Child

**Status:** Accepted
**Date:** 2026-09-10
**Extends:**
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md)
**Depends on:**
- [ADR-061: A call in a node class body is a declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-063: Identity from resolved declared values](./ADR-063-identity-from-resolved-declared-values.md)
- [ADR-093: The joints of one class compose in declaration order](./ADR-093-joints-of-one-class-compose-in-declaration-order.md)
**OpenSpec change:** `repeat-fan-out`

## Context and Problem Statement

`.repeat(n)` (ADR-061/ADR-063) says *one part, n placements*: it realizes
n identical copies of one declaration, sharing one `uniq_id` and one
cached artifact. `drives` (ADR-089) resolves each end of a relation to
exactly one coordinate, at realization, and solves the class's relations
in a fixpoint at the end of the declaring instance's simulate phase. The
two had never met: `read_through`, `coordinate_ref` and
`RepeatDeclaration.__getattr__` all refused a repeated declaration
outright, advising "state the relation inside the repeated class" — the
couplings spec's own advice.

That advice is unreachable for six sightings on this catalogue, because
what the copies follow is a coordinate of the PARENT (or a sibling), and
ADR-061's sideways-read rule is exactly what stops the repeated class
from naming it:

```python
# OpenCycloid (Actuators/OpenCycloid): four eccentric bearings, per-copy sign
eccentric_bearings = RadialBearing(...).repeat(4)
eccentric_shaft.spin.drives(eccentric_bearings.orbit, law=per_copy_sign)

# the abacus (Vibecoded-demos/abacus): four earth beads, the law reads the rank
earth.drives(earth_beads.travel, law=earth_lift)   # law(column, bead) reads bead.index

# OpenFlexure (Lab-Equipment/openflexure-microscope): two gear-lock screws
shaft_pin.turn.drives(gear_screws.orbit)
```

Measured on this tree (`openspec/changes/repeat-fan-out/evidence/probe_refusals_today.py`):

| Written | Today |
|---|---|
| `earth.drives(beads.travel)` | `SidewaysReadError: … 'beads' is a repeated declaration … State the relation inside Bead instead` |
| `earth.drives(beads)` | `TypeError: a repeated declaration names many coordinates, and a relation has one driven end` |
| `drive.drives(column.beads.travel)` | `TypeError: 'column.beads' reaches a repeated declaration … a relation has one end` |

So `Column.simulate()` keeps a hand-written
`for index, bead in enumerate(self.earth_beads): bead.translate(...)`,
`CycloidalDrive` keeps its per-bearing sign loop, and `MotorDrive` keeps
`for screw in self.gear_screws: screw.orbit = …`. OpenCycloid and the
abacus are deferred at stage A on this finding alone.

The rider: ADR-095 made `declared_ports` report a `Free`'s six
coordinates under dotted names, and `set_coordinate` binds one, with no
reader beside it — the first consumer that enumerated those names (the
campaign's own `capture_poses.py`) recorded an error for all six.
Fan-out's per-copy laws are the next consumer of that enumerator, so the
reader (`get_coordinate`) rides here.

## Decision Drivers

- One relation, written once in the parent's class body, drives every
  copy of a repeated child, with `law=` seeing the copy for a per-copy
  sign, phase or rank.
- No change to the law protocol ADR-089 fixed: the same two-argument
  callable, called once per thing it resolves to, never inspected.
- Every refusal keeps naming the relation and the path as written, and
  now also the copy.
- `repeat` still means one geometry, one build identity and one cached
  artifact (ADR-063): nothing a broadcast adds may enter identity.
- Nothing that is not rewritten moves: a pose comparison over every
  project that uses `.repeat()` with the motion layer.

## Considered Options

1. **A path through a repeated child is a BROADCAST, resolving to one
   relation per realized copy.** Chosen.
2. **One broadcast relation object holding n ends.** Rejected: every
   step of the solver (`_step_relation`, `_claim`, `_refuse`,
   `_binder_of`) would need a second shape, and ADR-089's "each realized
   instance SHALL resolve, solve and refuse its own" would stop being
   literally true of the relation's own object.
3. **A third argument (or an `index=` keyword sniffed by
   `inspect.signature`) handed to the law.** Rejected: ADR-089 forbids
   the framework inspecting anything about a law beyond
   `forward`/`inverse`, in as many words, and the copy already carries
   what the law needs as a plain attribute.
4. **Allowing only the FIRST segment of a path to be repeated.**
   Rejected: `column.beads.travel` would have stayed refused with no
   reason a reader could give, and the one-repeat-anywhere rule is not
   harder to state than the first-segment-only rule.
5. **A wiring keyword on `.repeat()`**,
   `.repeat(n, travel=column.travel)`. Rejected: measured
   (`evidence/probe_wiring_repeat.py`) to already work through the
   existing per-instance wiring mechanism when the source is a
   coordinate the declaring class itself declares; what a wiring cannot
   do is take its source from a PATH, and that case is exactly a
   broadcast relation with the default ratio of one. A second spelling
   would buy the first case nothing and the second case nothing either.
6. **A `count` alongside the copy's `index`.** Deferred, not decided;
   see Consequences.

## Decision Outcome

**A relation whose DRIVEN end passes through a repeated declaration is a
BROADCAST**, resolving to n `RelationRecord`s, one per realized copy, at
the position the declaration was written, in copy order:

- **`BroadcastRef`**, a `CoordinateRef` beside `PathRef` in
  `solid_node/motion/couplings.py`, sharing `PathRef`'s `(root, segments,
  terminal)` shape and validated at class definition exactly as
  `PathRef` is, because the classes are all known there and the repeat
  changes only how many realized instances the path lands on.
  `read_through` returns a `RepeatDeclaration` as a PLACE, the same
  relaxation ADR-095 made for a joint owning several coordinates, rather
  than refusing; `PathRef.__getattr__`, `ChildDeclaration.__getattr__`
  and `RepeatDeclaration.__getattr__` yield a `BroadcastRef` the moment
  they step onto one; `BroadcastRef.__getattr__` keeps walking and
  refuses a SECOND repeated segment by name, naming both.
- **The law's signature is unchanged.** `law=` is still "a callable of
  two arguments, called once for each thing the relation resolves to, at
  realization, with the realized nodes that OWN the two coordinates" —
  under a broadcast the owner of the driven coordinate is the COPY, so
  it is called once per copy, with the copy as the second argument, and
  the framework inspects nothing to decide that. `ratio=`/`offset=`
  resolve ONCE against the declaring instance and the resulting
  `Affine` is the SAME object shared by every copy's record: a ratio
  names a value of the declaring class and has no way to see a copy.
- **A copy carries `index`**, its 0-based position, stamped on
  `child.__dict__` AFTER construction (`RepeatDeclaration.realize`). Not
  a declared parameter, not in `identity_values`, not a child name: a
  repeat is still one geometry and one cached artifact whatever a copy's
  index is used for. A repeated class that already answers to `index` —
  a parameter, a port, a joint, a child, a property or a method — is
  refused where the repeat is written (`RepeatDeclaration.__set_name__`
  → `_check_index`), because a declaration wins over a framework-set
  instance attribute of the same name and the position would otherwise
  be silently invisible (measured,
  `evidence/probe_shadow.py`). Checked on the REPEATED class only: a
  PARENT that happens to declare its own `index` (InMoov's `Hand`,
  which declares `index = Driver(...)` for the index finger, on the
  parent of `fingers = Finger().repeat(4)`) is untouched.
- **A repeated end is a driven end only.** Named as the SOURCE — in any
  of the three spellings a path reaches it by — it is refused at class
  definition, naming the path as written, the repeated declaration and
  its class (`BroadcastRef.check('driver')`,
  `RepeatDeclaration.drives`). Named as a term of a derived coordinate,
  it is refused the same way (`BroadcastRef.terms()`). Bound already, it
  is never read backwards, whatever its law offers: `_step_relation`
  never inverts a broadcast record, and `_refuse` raises the existing
  `NotInvertible` — no new error kind — naming the relation, the COPY,
  the bound coordinate and the fact that a broadcast is read forward
  only, because n copies would have to agree on one source value and the
  framework does not compare values to decide that (ADR-089).
- **`get_coordinate(node, name)`**, exported from
  `solid_node.motion.ports` beside `set_coordinate` and mirroring it
  segment for segment: a name of one part is an attribute of the node, a
  name of several (`pose.roll`) is the head read and the tail taken off
  what it yields. Returns the bound SLOT, not the value, so an unbound
  coordinate reads back with `value is None` rather than being confused
  with a name that names no coordinate at all; a name `declared_ports`
  does not report is refused by name, checked against the enumerator
  rather than against `getattr`, so a declared parameter whose name
  resembles a coordinate's cannot answer for one.

**Where the n records sit.** `Relation.resolve` returns a LIST — one
record for an ordinary relation, n for a broadcast —
`resolve_declared_relations` flattens every relation's list in
declaration order, so the fixpoint's own flat iteration already puts a
broadcast's n records at the position of its declaration, in copy order,
with no separate ordering mechanism. A zero-count repeat is zero
records: it binds nothing and refuses nothing, stated rather than
discovered. `omit()` in `render()` does not shrink the count: ends
resolve at realization, so a broadcast covers every copy the repeat
REALIZED whether or not a later `render()` omits it. Reading a NAMED
broadcast off an instance yields the tuple of its records, in copy
order — empty for a zero-count repeat — where an ordinary named relation
still yields one record; `Relation.record_of` decides the shape from
whether the relation's DRIVEN end is a `BroadcastRef`, not from how many
records happen to exist at runtime.

**Serialization: nothing.** A broadcast lowers to the same operations n
hand bindings produce; ADR-089 already settled that a relation is not
published in the document, and this cycle adds no document key, no
schema version and no viewer change.

## Consequences

- **`index` is a plain attribute a future declaration could shadow.**
  Refused where the repeat is written, with the shadow itself as the
  reason in the message; surveyed against the whole catalogue
  (`design.md` Decision 3), nothing existing is refused, and InMoov's
  `Hand.index` (on the PARENT) is the reminder that `index` is an
  ordinary word a machine may already use.
- **A rigid leaf could read `index` in its own `render()`** and build n
  different shapes under one `uniq_id` and one cached artifact. Not
  detectable by the framework — it cannot tell a geometry read from a
  placement read — so the rule is stated in the spec rather than
  enforced at runtime. No sighting does it: every per-index render loop
  in the catalogue surveyed is the PARENT's, over the realized copies.
- **n law calls at realization instead of one**, realization-time only,
  never per instant. The largest repeat in the catalogue is Thor's 36
  bearing balls, which declares no relation.
- **A broadcast whose driven end is a WIRED coordinate of the copies**
  is refused per copy by the existing `_claim`, naming the wiring and
  the relation for that one copy; the message does not (yet) name all n
  copies a wiring/broadcast pair might affect. Left as is.
- **No `count` on the copy.** The abacus already repeats a class
  (`FrameHalf`) that declares a `count` of its own
  (`frame.py:35-43`, `frame_half.py:21`), and a framework-set `count`
  behind that declared parameter would be silently invisible for the
  same reason `index` would be — measured,
  `evidence/probe_shadow.py`. No sighting's law needs the copy's total
  count, only its `index`. Recorded, not decided: a second sighting can
  add it under a name chosen against the same survey (`repeat_count` is
  the obvious, ugly, candidate).
- **Nothing existing moved.** Every refusal a broadcast replaces was a
  hard error, so no project can have depended on it; the proof is a pose
  comparison over every project that uses `.repeat()` with the motion
  layer at the base and at the head, maximum deviation zero
  (`openspec/changes/repeat-fan-out/evidence.md`).
- **OpenCycloid and the abacus become refactorable at stage B**, in
  their own repositories' own cycles; fender-bender and the V8 lose one
  of their remaining blockers each. InMoov's ten `connect()` calls stay
  blocked: each of `Hand`'s four repeated fingers has its OWN driver, so
  the want is a per-copy SOURCE, which closes with a future tuple-source
  cycle, not this one.
- **Indexing a repeat in a class body** (`beads[2].travel`, a
  structurally different expression per copy — the Pascaline's eight-way
  carry) **stays open**, and so does the pre-existing, small hole a
  list-held child read in its OWN class body falls through — a bare
  `AttributeError: 'list' object has no attribute '…'`, because a
  class-body list is a Python list and not a declaration object
  (measured, `evidence/probe_list_held_today.py`; not this cycle's).
