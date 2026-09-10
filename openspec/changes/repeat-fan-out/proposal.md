## Why

`.repeat(n)` says *one part, n placements*. Nothing says *one relation,
n copies*, so a machine whose repeated parts move is a machine whose
motion is written back out by hand. Six projects hit it, and the
couplings spec's own advice — "state the relation inside the repeated
class" — is unreachable for every one of them, because what the copies
follow is a coordinate of the PARENT, which the repeated class cannot
name.

`workflow/warts.md` carries the finding four times over. The sentences
the projects want, verbatim from their entries:

OpenCycloid (`Actuators/OpenCycloid`), four eccentric bearings, per-copy
sign:

```python
eccentric_bearings = RadialBearing(...).repeat(4)
eccentric_shaft.spin.drives(eccentric_bearings.orbit, law=per_copy_sign)
```

The abacus (`Vibecoded-demos/abacus`), four earth beads, the law reading
the rank:

```python
earth.drives(earth_beads.travel, law=earth_lift)   ... law(column, bead) reads bead.index
```

OpenFlexure (`Lab-Equipment/openflexure-microscope`), two gear-lock
screws following the shaft:

```python
shaft_pin.turn.drives(gear_screws.orbit)
```

What stands in their place today, measured on this tree
(`evidence/probe_refusals_today.py`):

| Written | Today |
|---|---|
| `earth.drives(beads.travel)` | `SidewaysReadError: … 'beads' is a repeated declaration … State the relation inside Bead instead` |
| `earth.drives(beads)` | `TypeError: a repeated declaration names many coordinates, and a relation has one driven end` |
| `drive.drives(column.beads.travel)` | `TypeError: 'column.beads' reaches a repeated declaration … a relation has one end` |
| `get_coordinate(node, 'pose.roll')` | `ImportError: cannot import name 'get_coordinate'` |

So `Column.simulate()` keeps
`for index, bead in enumerate(self.earth_beads): bead.translate(...)`
(`Vibecoded-demos/abacus/abacus/column.py:68-72`), `CycloidalDrive`
keeps its per-bearing sign loop
(`Actuators/OpenCycloid/simulation/actuator.py:96-107`), and
`MotorDrive` keeps `for screw in self.gear_screws: screw.orbit = …`
(`.../motors/motor_drive.py:64-67`). OpenCycloid and the abacus are
DEFERRED at stage A on this finding alone: refactoring them onto joints
while their copies stay hand-bound would be cosmetic.

The rider comes from the other end of the layer. ADR-095 made
`declared_ports` report a `Free`'s six coordinates under dotted names
(`pose.roll`), and `set_coordinate` binds one; there is no reader, so
the first consumer that enumerated those names — the campaign's own
`capture_poses.py` — recorded an error for all six. Fan-out's per-copy
laws are the next consumer of that enumerator, so the reader rides here.

## What Changes

- **A relation whose DRIVEN end passes through a repeated declaration is
  a BROADCAST: it resolves to n relations, one per realized copy.** The
  n records sit in the parent's fixpoint at the position the declaration
  was written, in copy order. Each is an ordinary relation from then on:
  its own binding, its own refusals, its own copy named in every message.
- **A path may pass through at most ONE repeated segment, wherever it
  sits.** `beads.travel`, `beads` (standing for the copies' one joint),
  `column.beads.travel` and `legs.femur.lift` are all one fan-out. Two
  repeated segments are **refused by name** at class definition, saying a
  broadcast fans out over one repeat.
- **The law is unchanged, and is called once per copy.** ADR-089 already
  hands `law=` the realized nodes that OWN the two coordinates; under a
  broadcast the owner of the driven coordinate is the copy, so
  `earth_lift(column, bead)` reads `bead.index` with no new argument and
  no new signature. `ratio=`/`offset=` give every copy the same affine
  law, resolved once against the declaring instance.
- **A copy realized by `.repeat(n)` carries `index`**, its 0-based
  position, on the realized node. It is NOT a declared parameter, does
  NOT enter `uniq_id`, and does NOT make the copies different parts:
  `repeat` still means one geometry and one cached artifact.
- **A repeated class that already answers to `index` is refused where
  the repeat is written**, naming the parent, the attribute, the class
  and what it found. Silence is the alternative: a declared parameter is
  a data descriptor, so a framework-set value behind one is invisible
  (`evidence/probe_shadow.py` — `h.__dict__['index'] = 3` while
  `h.index` reads `0`).
- **A repeated end is never a SOURCE and never inverted.** Named as the
  driver, it is refused at class definition — n copies hold n values and
  a source is one value. Named as the driven end and found already
  bound, the relation is not read backwards: `NotInvertible` names the
  broadcast and the copy and says why, rather than the law.
- **`get_coordinate(node, name)`**, exported from
  `solid_node.motion.ports` beside `set_coordinate`, returning the bound
  slot for any name the port enumerator reports — plain, or dotted like
  `pose.roll`. A name the enumerator does not report is refused by name,
  listing what it does report.
- **No new keyword on `.repeat()`.** The walkthrough listed
  `.repeat(n, travel=column.travel)` as the weakest identity form and
  the one to build first. Measured on this tree
  (`evidence/probe_wiring_repeat.py`), `Bead(travel=earth).repeat(4)`
  already binds all four copies through the fixpoint — it is the ports
  spec's own scenario "A repeated child is wired per instance". The one
  thing a wiring cannot do is take its source from a PATH, and that case
  is exactly a broadcast with the default ratio of one. A second
  spelling would buy nothing. **This is a departure from §3.1 as
  ratified; see `workflow/docs/motion-catalogue-2.md` §3.1, refined.**
- **Not in this cycle, and said plainly:** the Pascaline's eight-way
  carry (each copy a structurally different expression, list-held
  children — refused as today); OpenVMP's data-built children (cycle 3);
  and **InMoov's ten `connect()`s**, which the finding table lists under
  this cycle but which need a per-copy SOURCE — `Hand` drives each of
  its four repeated fingers from a different driver — and therefore
  close with cycle 5's tuple source, the law picking by `finger.index`.
  A `count` beside `index` on the copy: no sighting's law reads it, and
  the abacus already repeats a class that declares `count` of its own
  (`Frame.halves = FrameHalf(count=count, …).repeat(2)`), so reserving
  the name would refuse a model the catalogue contains.

## Capabilities

### New Capabilities

(none — a broadcast is multiplicity on the declaration layer, not a new
kind of pair or a new kind of coupling; see
`workflow/docs/motion-catalogue-2.md` §2)

### Modified Capabilities

- `couplings`: "Each end of a relation resolves to one coordinate" gains
  the broadcast end, the one-repeated-segment rule, the source refusal
  and the two-repeat refusal, and its scenario "A path through a
  repeated child is refused" changes body from a flat refusal to the
  source-side refusal; "The law of a relation is an affine pair, or
  project code passed in" gains the once-per-copy call; "Relations are
  solved from the bound side" gains the n-records ordering, the
  zero-count case and the named-relation record; "Three refusals" gains
  the broadcast's non-inversion.
- `declarative-nodes`: "Class-body child declarations" gains the copy's
  `index`, the identity rule that keeps it out of `uniq_id`, and the
  clash refusal, and its scenario "A path through a repeated child is
  refused" changes body to the broadcast reading.
- `ports`: "Domain-typed ports" gains the requirement that a name the
  enumerator reports is a name the framework can read back, with
  `get_coordinate` as the reader beside `set_coordinate` as the writer.

The `joints`, `node-model` and `simulation` specs are not changed: a
broadcast binds one coordinate of each copy through the one binding path
every other binder takes, so a copy's joints compose under ADR-093
exactly as they do when a parent's `simulate()` binds them by hand.

## Impact

- `solid_node/node/declarative.py` — `RepeatDeclaration.__getattr__`
  yields a broadcast reference instead of raising;
  `RepeatDeclaration.drives`, so naming the repeat itself as an end
  reaches the right refusal; `RepeatDeclaration.__set_name__` refuses a
  class that answers to `index`; `RepeatDeclaration.realize` stamps each
  copy's index.
- `solid_node/motion/couplings.py` — a `BroadcastRef` beside `PathRef`;
  `read_through` returns a repeated declaration as a place rather than
  refusing; `Relation.resolve` returns n records for a broadcast;
  `RelationRecord` names its copy; `_step_relation` never inverts a
  broadcast record and `_refuse` says so.
- `solid_node/motion/ports.py` — `get_coordinate`.
- `tests/test_couplings.py`, `tests/test_declarative_nodes.py`,
  `tests/test_ports.py` — a new broadcast section, the copy's index, the
  reader, and the refusals.
- `docs/driving.rst` (a fan-out passage), `docs/declaring.rst` ("drive
  variation is port feeding" becomes "drive variation is a broadcast
  relation, or port feeding"), `docs/api-reference.rst`
  (`get_coordinate`), `docs/changelog.rst` `Unreleased`,
  `docs/architecture.md` §Couplings, and a new ADR under
  `docs/adrs/NODE/` with its index row.
- `workflow/warts.md` — the fan-out finding and the dotted-reader
  finding marked fixed, with the InMoov sighting moved to cycle 5.
- `libresolid-studio/docs/motion-general-refactor.md` is the shop's
  tracker and is NOT touched from here.
- **Downstream, not in this cycle:** OpenCycloid and the abacus become
  refactorable at stage B; fender-bender and the V8 lose one of their
  remaining blockers each.
- No CLI change, no document format change, no viewer change, no
  serialization change: a broadcast lowers to the same operations n hand
  bindings produce. Nothing is deprecated, and no existing project's
  pose moves — proved by a pose comparison over every project that uses
  `.repeat()` with the motion layer (tasks §6).
