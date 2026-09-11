# Design: several coordinates at one end of one relation

Everything measured below is measured on this branch
(`motion-catalogue-2`, base main `5b28510`, with cycle 1 / ADR-096 on
it and cycles 2, 3 and 4 in the tree in various states) by the probes in
`evidence/`, not read off the source.

## 1. Context: what a relation is today

ADR-089 fixed four things this cycle has to fit inside:

- **An end is ONE coordinate.** `coordinate_ref(value, role)`
  (`couplings.py:1224`) maps a class-body value to exactly one
  `CoordinateRef`, and refuses anything else by name. A tuple reaches
  that refusal today: `(<path one.turn>, <path two.turn>) is not a
  coordinate` (`evidence/probe_today.py`).
- **The law is a callable of two arguments**, called ONCE per record at
  realization, with the realized nodes that OWN the two coordinates,
  driver first — measured:
  `law called with ('OneToOne', 'Leaf')`. It returns an object with a
  callable `forward` and optionally `inverse`; a plain function is
  forward-only. **The framework inspects nothing else about it**, which
  ADR-089 states in as many words and ADR-096 restated when it refused
  a third law argument.
- **The solver orients each relation from whichever end is bound**, in a
  fixpoint, per instance (ADR-089), deferring to the whole-tree
  fixpoint what it cannot reach (cycle 4).
- **A broadcast is n records, one per copy**, each an ordinary record
  with `copy` set, and it is never read backwards (ADR-096).

And one thing the framework does NOT do, which decides half of this
design: it never compares or solves values. That is why an `Affine`
inverts (the framework owns the algebra) and a `law=` does not (the law
is opaque project code).

## 2. Where the verb can live for a group of sources

**The ratified sentence is not Python.** `(count, next_count).drives(…)`
asks `tuple` for a `drives` attribute. Measured:

```
(a, b).drives(...): AttributeError: 'tuple' object has no attribute 'drives'
tuple has drives: False
patching tuple: TypeError cannot set 'drives' attribute of immutable type 'tuple'
```

So the source side needs a spelling. Four were weighed.

| spelling | verdict |
|---|---|
| `(count & next_count).drives(…)` | **chosen** |
| `drives((count, next_count), pawl.swing, …)` — a free function | rejected by measurement |
| `Sources(count, next_count).drives(…)` — a wrapper noun | rejected |
| `pawl.swing.driven_by((count, next_count), …)` — a second verb | rejected |

**The free function is rejected because a class body may bind the
name.** `drives` is an ordinary word a machine uses for its drive units,
and InMoov's `Hand` — one of the four projects that must write this
sentence — declares `drives = Drive().repeat(5)` (`hand.py:213`).
Measured (`evidence/probe_today.py`):

```
a free `drives` inside a body that declares one:
    TypeError: 'list' object is not callable
```

The class body's own name wins, silently until the call, and the failure
names nothing. Injecting `drives` into the declaring namespace through
`_DeclaringNamespace.__missing__` would beat the shadow only by making
the name un-greppable and the shadow itself a mystery; it was not
pursued.

**The wrapper noun is rejected** because it adds an importable framework
name to a layer whose whole point is that the vocabulary is one verb
(ADR-089: "no second vocabulary to learn or to maintain"), and because
`Sources(a, b)` reads as an implementation, not as a machine.

**The second verb is rejected** for the same reason and one more: it
reverses the reading direction of every message and of the model itself.
The author states which coordinate drives which; the framework works out
which way to SOLVE it. A `driven_by` would put a second direction in the
model.

**`&` is chosen.** It adds no name and no import; `a & b` reads as "a
and b" and is the established shape for combining operands in a Python
DSL (Django's `Q`, SQLAlchemy). It is free on every declaration that
carries `drives` — measured: `TypeError: unsupported operand type(s) for
&: 'SignalPort' and 'SignalPort'` — so nothing existing can break. It
chains left-associatively into a flat group, so `x & y & z` is one group
of three, not a nested pair. Its precedence is right: `-`, `+`, `*` and
`/` all bind tighter, so `a & b - c` is `a & (b - c)` and the derived
coordinate algebra composes with it unparenthesised.

**The parenthesis trap is refused by name.** `count & next_count.drives(
pawl.swing, law=…)` binds `.drives` tighter than `&`, so it states a
ONE-source relation, records it on the class, and then asks
`count & <relation>`. `__and__` refuses a `Relation` operand naming the
relation and saying the parentheses are missing. The class fails to
build; there is no silent half-sentence.

**The driven side keeps the ratified tuple**, because a tuple written as
an argument is delivered to the framework intact — measured: the
existing refusal names both paths. `&` is accepted there too, since the
group and the tuple are one thing and refusing one of them at one
position would be a rule with no reason a reader could give.

### The two objects

- **`Coordinates`** — what `&` builds in a class body. It holds the raw
  operands in written order, carries `drives`, `__and__` (appending, so
  chains stay flat) and by-name refusals for the derived-coordinate
  arithmetic (`(a & b) - c`: "a formula has one value per term"). It is
  never imported by a project and is not exported.
- **`EndGroup`** — what `coordinate_ref` returns for a `Coordinates` or
  for a tuple, holding the members as `CoordinateRef`s. Conversion is
  late, in `relate()`, because `coordinate_ref` takes the ROLE and the
  role is not known until `drives` is called: the same member is
  refused differently as a source and as a driven end.

## 3. What the law is handed, and what it returns

**Chosen: the law callable keeps its two arguments, and each argument's
SHAPE follows the sentence.** A side naming one coordinate is handed
that coordinate's owning node, exactly as today. A side naming several
is handed the TUPLE of their owners, in the order written.

```python
def delta_rod(sources, rods):          # (x & y & z) drives (spin, lean, swing, rise)
    machine = sources[0]               # x, y and z are all the machine's drivers
    rod = rods[0]                      # all four ends are on the copy
    angle = TOWER_ANGLES[rod.index // 2]
    side = (-1, 1)[rod.index % 2]
    def law(x, y, z):
        ...
        return spin, lean, swing, rise
    return law
```

**Rejected: one positional argument per END, drivers then driven.** It
is the literal reading of the ratified sentence ("the law handed all
sources in the order written plus the driven node") and it was weighed
first. Against it:

- The arity is n+m, and the arguments are frequently duplicates,
  because the ends of one mechanism usually share owners. Kossel's law
  becomes `def delta_rod(machine, _y, _z, rod, _lean, _swing, _rise)`:
  seven parameters, five ignored. OpenFlexure's becomes
  `def leg_lean(body, _dy, leg, _tilt)`.
- ADR-089's "a CALLABLE of two arguments" would have to be rewritten
  rather than re-shaped.

For it: `lambda driver, driven:` written for a one-to-one relation and
attached by mistake to a three-source one fails loudly under BOTH
shapes — with a `TypeError` on arity under the rejected shape, and with
an `AttributeError` on the tuple inside the law's first line under the
chosen one, at realization either way.

**Rejected: de-duplicating the owners.** It would make a law's arity
depend on how many ends happen to share a node — a property of the tree,
not of the sentence — so the same law would need a different signature
in a machine whose rod carried its `rise` on a sub-part.

**Rejected: one driven node ("the driven node", singular).** There is no
such node when the m ends have different owners, and nothing in the
model forbids that (a differential's two outputs are two pinions).

**`forward` takes n values positionally and returns m.** Sources are
spread — `lambda x, y, z: …` is the mechanism's own function of its own
inputs — and the return is a SEQUENCE of exactly m values in the order
the ends were written. The asymmetry is Python's: arguments can be
spread and a return cannot, so no uniform rule was available and each
side is shaped for what reads best. For m = 1 the return is the value
itself, unchanged, and a one-source law's `forward(x)` is unchanged.

**The length is checked, by name, at every application.** Measured on
this tree, a law returning four values for one end binds the tuple:

```
the slot after one run: (1.0, 2.0, 3.0, 4.0)
the operations it produced: ['Rotation(1.0, 2.0, 3.0, 4.0)']
```

A pose nobody stated, refused by nothing. The check asks for a length
and refuses a return with no length, a `str`, or a length that is not m,
naming the relation, the law, the m ends as written and what came back.
It is safe against a symbolic value: measured, neither a `float`, an
`int` nor an `OpenSCADConstant` has `__len__`, `__iter__` or
`__getitem__`, so a single symbolic value can never be mistaken for a
sequence of several.

**No new error kind.** A wrong return shape is a `CouplingError`, where
ADR-089 already put "the law callable returned … which is not a law".
The three named refusals stay three.

**The check runs per application, not once at realization**, because the
law's return is only known when it is applied. It costs one `len()` on
the rare path where m > 1.

## 4. One direction, and why

A relation naming several ends is applied FORWARD only, and refuses
`NotInvertible` by name when the solver would need it backwards —
whatever its law offers, exactly as a broadcast does. The reason is the
same reason: reading it backwards would mean solving m values for n
unknowns, and the framework compares and solves nothing. It holds even
for n = m = 1 inside a group (`(a,)` is refused, so that case cannot
arise) and even when the law offers an `inverse`.

`Affine` is not a law for a group. `ratio=`/`offset=` with a group on
either side is refused at class definition — "an affine law relates one
value to one value" — and so is a group with NO `law=` at all, because
the default law is `Affine(1, 0)` and would return one value for m ends.
That is one rule read twice: several ends require a law that returns
several values.

## 5. The record: one record, all its ends

**Chosen: one `RelationRecord` holding a TUPLE of driver ends and a
TUPLE of driven ends**, of lengths n and m; the one-to-one relation is
the case n = m = 1 and its record is the same object it is today.

Rejected: m records of one end each. A single law call returns all m
values at once, so the m ends cannot be bound, refused or deferred
independently without calling the law m times or caching its return
behind the solver's back. They are one statement and they are one
record.

**Under a broadcast: one record per copy, each holding its copy's m
driven ends.** `(rods.spin & rods.lean & rods.swing & rods.rise)` over
`.repeat(6)` is **six records of four ends**, not twenty-four records
and not one record of twenty-four ends, and the law is called six times
— once per copy, with the copy's four owners. ADR-096's shape is
preserved with "one end each" read as "one END-SET each":
`resolve_declared_relations` still flattens into a flat list of records,
`_solved_formulas`, `_claim`, `_step_relation` and `_refuse` still see
one flat list, and a copy whose end is doubly bound is still refused
naming that copy while the other five still solve.

**Every driven broadcast end must fan out over the SAME repeated
segment.** Two broadcasts over `beads` reached through different parents
(`left.beads.travel` and `right.beads.travel`) name different copies, and
a broadcast end beside a plain end would bind the plain one n times. So
the rule is on the written path: every driven end that passes through a
repeat must pass through the same repeat at the same position, and a
driven side mixing a broadcast with a plain end, or two different
repeated segments, is refused at class definition naming both paths.
The zip is then total: `resolve_all` returns the same n for every end.

**The record's `copy` becomes the node the REPEATED SEGMENT realized**,
for one driven end or several. It is the only well-defined choice when
the m ends have different owners, and it is a small correction to
ADR-096's `copy = driven.node`: for every catalogue sighting
(`beads.travel`, `rods.spin`) the two are the same node, and they differ
only for a path that continues past the repeat (`legs.femur.lift`),
where the new value names the LEG the broadcast fans over rather than
the femur. The implementer confirms which cycle-1 test asserts that
message text and updates it with its reason.

**Reading a named relation off an instance is unchanged.** One record
for an ordinary relation, the tuple of per-copy records for a broadcast
— the count of ENDS does not change the count of RECORDS. `described()`
names the ends as written, comma-separated inside parentheses when there
are several, so a message reads `'rod_law' ((x, y, z) drives (rods.spin,
rods.lean, rods.swing, rods.rise), copy rods-3)`. `direction` is
`'forward'` or `None`, never `'backward'`.

## 6. The solver

`_step_relation` for a record with n driver ends and m driven ends:

| state | action |
|---|---|
| every driver end bound, no driven end bound | CLAIM all m, apply `forward`, check the return's shape, bind all m, `direction = 'forward'` |
| every driver end bound, some driven end bound | the claim raises `DoublyBound`, naming that driven end and both binders — per target, before anything is bound |
| some driver end unbound | no step; DEFER (cycle 4) |

**All m ends are claimed before any is bound**, so a doubly-bound target
never leaves a half-applied law behind: the m bindings of one law are one
event.

At the end of the enumeration's fixpoint, `_refuse`:

- some sources unbound, no driven end bound → `UnreachedCoordinate`
  naming **exactly the unbound sources**, not "nothing bound either
  end", which would be a lie when two of three sources are bound;
- some sources unbound, some driven end bound → `NotInvertible` naming
  the bound driven end, the unbound sources, and saying that a relation
  naming several ends is read forward only;
- n = m = 1 → every message is exactly what it is today.

**There is no partial application.** A law of three sources runs when
all three are bound and not before; a project whose third source is
sometimes absent binds it to a default in `simulate()`, which is the
rest-default guard cycle 4 keeps legal. The Pascaline's
`if next_count is None: next_count = 0` becomes exactly that binding, and
it must move from a local variable to a binding of the port — named in
the overlay task, because it is the one place a sighting's project code
must change shape rather than shrink.

**Deferral.** A record whose sources are not all bound defers under cycle
4's rule, in the position of its declaration, in tree order; the pass may
bind a missing source from anywhere in the tree, and only the end of the
pass refuses. Cycle 4's deferral list enumerates "a relation record with
neither end bound"; if that wording is still literal when this cycle is
implemented, this cycle's delta widens it in the same words used here.

## 7. What stays refused, and what it says

At CLASS DEFINITION, each naming the relation as written:

| form | refusal |
|---|---|
| `(beads.travel & x).drives(…)` | the existing repeated-source refusal, reached per member |
| `x.drives((beads.travel, other.turn))` | a driven side mixing a broadcast with a plain end |
| `x.drives((left.beads.travel, right.beads.travel))` | two different repeated segments |
| `(a & b).drives(c, ratio=2)` | an affine law relates one value to one value |
| `(a & b).drives(c)` | a relation naming several ends carries a `law=` |
| `x.drives(())` / `x.drives((a,))` | a group is two coordinates or more; one end is written without the group |
| `x.drives(((a, b), c))` | ends are named one by one; a group has no parts |
| `(a & a).drives(c, law=…)` | a coordinate names one end of a relation once |
| `(a & b).drives((b, c), law=…)` | a coordinate is a source or a driven end of one relation, not both |
| `(a & b) - c` | a formula has one value per term |
| `a & 3`, `a & some_node` | a group is a group of coordinates |
| `count & next_count.drives(…)` | the parentheses are missing |
| a `Driver` inside a driven group, a node with two joints, a path stopping on a multi-coordinate joint | the existing refusals, reached per member |

At REALIZATION: the law's return is not a law (existing). At every
APPLICATION: the return of `forward` is not a sequence of exactly m
(new).

**The bare-node rule is untouched.** A node whose class declares several
joints is still refused as an end, inside a group as outside it: several
ends are several COORDINATES named one by one, and a group is not a way
to say "that body's joints".

## 8. Why a derived coordinate is not this, and stays

A derived coordinate is already multi-source — `left = wrist + 2 * tool`
reads two coordinates — and it is invertible in both directions. It
stays exactly as it is, and the two are not competing spellings:

- a derived coordinate is LINEAR and the framework owns its algebra
  (ADR-089 keeps it a mapping from reference to coefficient, precisely
  so the backward solve is exact and cheap), so any ONE unknown term can
  be solved from the rest;
- a `law=` is opaque project code, so nothing can be solved from it.

And a derived coordinate produces ONE value and IS a coordinate — it can
be driven, it can drive, `declared_ports` reports it. A multi-source law
produces m values and is not a coordinate at all.

The guidance the docs carry from this: **if the combination is linear,
write a derived coordinate and keep both directions; if it is not, write
a law over several sources and lose the reverse.** OpenFlexure's
`leg_lean` (two `asin`s of a rotated projection) and kossel's
`delta_rod` (a square root of a difference of squares) are the second
kind; nothing in the catalogue writes a linear multi-source law that a
derived coordinate could have carried.

## 9. Symbolic values

Unchanged, and it is the reason `forward` spreads its sources rather
than boxing them: the law does ordinary arithmetic over n values, each
of which may be a number, a `DriverToken` or an expression in `$t`, and
the m results are published as m operations exactly as m hand bindings
would be (ADR-076, ADR-022). Nothing new is serialized: a relation is
not published, and the operations it lowers to are the ones the project
wrote by hand today.

Two things a project must know, both already true of a one-source law
and both stated in the docs passage: a law's `forward` may not BRANCH on
its arguments' values (a symbolic value is not comparable), and a
non-linear function of a symbolic value must come from `solid_node.math`
so it emits an OpenSCAD call. Kossel's `delta_rod` and `asin`/`cos`
already obey both.

## 10. InMoov: what the sighting really asks for

The sentence closes the sighting as written:

```python
(thumb & index & middle & ring & little).drives(fingers.drive, law=by_finger)

def by_finger(motors, finger):
    which = finger.index + 1              # FINGERS is MOTORS without the thumb
    return lambda *values: values[which]
```

**And the law it produces is a selector, not a mechanism.** Five
sources are handed to every copy so that each copy may use one of them.
That is worth saying plainly: the cleaner sentence is a per-copy SOURCE
— `index.drives(fingers[1].drive)`, one relation per copy, naming the
copy by its position — which is INDEXING A REPEAT IN A CLASS BODY, the
form cycle 1 listed as a non-goal and left open ("a structurally
different expression per copy is the Pascaline's finding and stays
open"). This cycle does not add it and should not: a per-copy index is a
declaration-layer question, and the selector law works today with the
copy's own `index` from ADR-096.

So InMoov's sighting is closed by this cycle in the sense that the ten
`connect()` calls become two sentences; it is NOT closed in the sense
that the sentence says what the machine does. Recorded in `warts.md` as
a residual want with the indexing finding it belongs to, not as a defect
of this design.

## 11. The Pascaline's carry stays out, and why

`Pascaline.counts()` (`pascaline.py:127-145`) builds each position's
count as a structurally different expression: the register, the
timeline's strokes, the stylus stroke, and then a nested loop over every
lower position `w < i` with a gate over every position between. Nothing
about it is one law applied to n copies:

- the eight positions are LIST-HELD (`positions = [Digit(...) × 8]`),
  and a list-held declaration is refused as a relation end at all, by a
  rule this cycle does not touch (its children carry their own
  arguments and are named one by one);
- each position's expression has a different SHAPE — position i reads
  i + 3 sources through i nested gates — so eight positions would need
  eight sentences and eight laws, which is longer than the loop that
  writes it today;
- the sources include `self.time`, `wheel` and `turn`, which the root
  reads directly.

Multi-source does not close it and was never meant to; it is the
Pascaline's own separate finding (a fan-out over list-held children with
a structurally different expression per copy), and it stays open in
`warts.md` with the cycle-1 non-goal it belongs to. What this cycle DOES
close in the Pascaline is the pawl, inside `Digit`, where the sources are
two ports of one class.

## 12. Risks / Trade-offs

- **`&` is not the ratified spelling.** → Measured impossible
  (§2); the driven side keeps the tuple verbatim; the pilot is asked in
  proposal (a).
- **A group hands a law arguments it does not use** (InMoov's four
  ignored motors, kossel's duplicated owners). → §3 and §10 say so; the
  alternative shape is written out and the pilot chooses.
- **One written line becomes m bindings and a reader counts them
  nowhere.** → Every message names the ends as written, the record
  holds them in order, and the return-shape refusal names m explicitly
  when a law disagrees.
- **The claim-then-bind order is new sequencing in the solver.** → It is
  covered by a test that binds one of four targets by hand and asserts
  that none of the other three moved.
- **A pose could move where a project already binds these coordinates by
  hand.** → Nothing in this cycle binds anything a project did not bind
  before; the proof is the pose comparison over every motion-layer
  project at base and head plus four overlays (tasks §7-8), not an
  argument.
- **`copy` changes meaning for a path that continues past the repeat.**
  → §5; one message, named in tasks, with its reason.

## 13. Migration

Additive. Every form this cycle gives a meaning to raises today
(measured, three of them in `probe_today.py`), so no project can have
depended on it. Rollback is reverting the cycle. No project code is
edited here; kossel is resumed at stage B in its own repository, and the
Pascaline, InMoov and OpenFlexure follow when an agent is free.

## 14. Open questions

For the pilot, none blocking:

1. **The law's argument shape** — proposal (b). Both shapes are written
   out in §3 with kossel's law in each.
2. **A coordinate on both sides of a ONE-to-one relation** — proposal
   (c): unrefused today, deadlocks, and widening the check is not
   measured against the catalogue here.
3. **Naming a group in a class body** — `sources = a & b` puts a
   `Coordinates` object in the namespace. It is harmless and untested;
   the contract says nothing about it.
4. **`&` on the driven side as well as the tuple.** Both are accepted.
   If the pilot would rather have one spelling per position, the tuple
   is the one to keep (it is the ratified one) and `&` becomes
   source-only.
5. **Whether a multi-target law should be allowed to bind a SUBSET** —
   returning a sentinel for "leave this one alone". No sighting wants
   it, and it would make "which binder bound this" answerable only at
   runtime. Not offered.

## 15. What contradicts the ratified direction, plainly

- §3.5 writes the source side as a TUPLE: `(count, next_count).drives(…)`.
  **It cannot be Python**, measured in `probe_today.py`: `tuple` has no
  `drives` and, being an immutable built-in type, cannot be given one.
  The cycle spells it `(count & next_count).drives(…)` and keeps the
  tuple on the driven side, where it works.
- §3.5 says "the law handed all sources in the order written plus the
  driven node as today". **The chosen shape hands the sources as a
  TUPLE**, in the order written, and the driven side as one node or a
  tuple by the same rule — because one positional argument per end
  gives kossel a seven-parameter law with five duplicated arguments
  (§3). The pilot is asked.
- §3.5's OpenFlexure sighting is written
  `z_motor.drives((legs.tilt, legs.lean), law=flexure)`. **The measured
  project cannot source it from `z_motor`**: a leg's lean is
  `k.leg_lean(dx, dy, angle)` over the stage's TWO coordinates, which
  come from `x_motor` and `y_motor`, and `z_motor` is the focus axis
  (`body/body.py:80-100`, `kinematics.py:104-119`). The sentence is
  `(stage.slide_x & stage.slide_y).drives((legs.lean, legs.tilt), law=leg_lean)`,
  stated in `MainBody` where both coordinates are reachable. The
  sighting's SHAPE — two rotations per leg from a multi-source law over
  repeated bodies — is exactly as ratified; only its source is
  corrected.
- §3.5 lists three sightings for the source side; **kossel has a
  fourth**, `(x & y & z).drives(towers.height, law=delta_carriage_law)`
  — several sources, ONE driven end, over a `.repeat(3)`. It costs
  nothing extra and it is the plainest test of n > 1 with m = 1.
- The finding table's row for the Pascaline reads "this drum and the
  next", which is right; the ROOT's eight-way carry in the same project
  is not covered and never was (§11), and `warts.md` already says so.
