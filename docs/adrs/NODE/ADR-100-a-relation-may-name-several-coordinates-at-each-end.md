# ADR-100: A Relation May Name Several Coordinates at Each End

**Status:** Accepted
**Date:** 2026-09-11
**Extends:**
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md)
**Depends on:**
- [ADR-096: A relation broadcasts over a repeated child](./ADR-096-a-relation-broadcasts-over-a-repeated-child.md)
**Cites:**
- [ADR-099: The enumeration's simulate phases are one tree pass](./ADR-099-the-enumerations-simulate-phases-are-one-tree-pass.md)
**OpenSpec change:** `multi-source-multi-target-laws`

## Context and Problem Statement

ADR-089 fixed a relation as ONE coordinate driving ONE coordinate. Five
sightings on the catalogue read several and move several: the Pascaline's
pawl deflects bilinearly in two drums; the Mini Kossel's delta rod has
four freedoms from three drivers, and a carriage's height from the same
three; OpenFlexure's four flexure legs lean two ways from two stage
coordinates; InMoov's hand drives four repeated fingers from five
drivers. Measured on this tree
(`openspec/changes/multi-source-multi-target-laws/evidence/probe_today.py`):

| Written | Today |
|---|---|
| `(a, b).drives(c, law=…)` | `AttributeError: 'tuple' object has no attribute 'drives'` |
| `(a & b).drives(c, law=…)` | `TypeError: unsupported operand type(s) for &` |
| `a.drives((b, c), law=…)` | `TypeError: (…) is not a coordinate, so it cannot be the driven end of a relation` |
| a law returning four values for one end | binds the TUPLE into the slot — `Rotation(1.0, 2.0, 3.0, 4.0)`, refused by nothing |

## Decision Drivers

- Say the sentence a mechanism actually is, without inventing a second
  vocabulary (ADR-089's own constraint, restated).
- The four sightings' laws are project code that already computes
  several values from several sources in one function; the framework
  should hand that function what it needs and check what it returns,
  not force it through several one-source relations that cannot express
  it.
- Reuse ADR-096's shape (one record per broadcast copy) rather than
  inventing a second one for "several ends per copy".

## Considered Options — the source-side spelling

The ratified sentence, `(count, next_count).drives(...)`, is not Python:
`tuple` has no `drives` and, being an immutable built-in, cannot be given
one (measured). Four spellings were weighed for the source side:

1. **`(a & b).drives(...)`.** Chosen. Adds no name and no import; free on
   every declaration that already carries `drives` — measured,
   `TypeError: unsupported operand type(s) for &` on each kind today, so
   nothing existing can break; chains flat and left-associative
   (`x & y & z` is one group of three); its precedence sits looser than
   `+`/`-`/`*`/`/` and tighter than nothing a class body writes, so
   `a & b - c` reads as `a & (b - c)`.
2. **A free function**, `drives((a, b), c, ...)`. Rejected by
   measurement: a class body may bind the name `drives` to its own
   value — InMoov's `Hand` declares `drives = Drive().repeat(5)`
   (`hand.py:213`) — and a free function of that name becomes
   `TypeError: 'list' object is not callable` inside such a body,
   silently until the call, naming nothing.
3. **A wrapper noun**, `Sources(a, b).drives(...)`. Rejected: an
   importable framework name on a layer whose whole point is one verb
   (ADR-089), and it reads as an implementation rather than a machine.
4. **A second verb**, `pawl.swing.driven_by((a, b), ...)`. Rejected: it
   reverses the reading direction ADR-089 fixed — the author states
   which coordinate drives which, the framework decides how to solve
   it — and is exactly the "second vocabulary" ADR-089 already refused.

The DRIVEN side keeps the ratified tuple verbatim — a tuple written as an
argument reaches the framework intact — and also accepts `&`, because the
tuple and the group mean one thing and refusing one spelling at one
position would be a rule with no reason a reader could give. `&` applied
to anything that is not a coordinate is refused by name; `&` applied to
an already-stated `Relation` says the parentheses are missing
(`count & next_count.drives(...)` binds `.drives` tighter than `&`).

## Considered Options — the law's argument shape

1. **Shaped: one argument per SIDE, each the owner or the TUPLE of
   owners.** Chosen. `def delta_rod(sources, rods):` reads
   `sources[0]`/`rods[0]`; the arity never depends on how many ends
   happen to share one node.
2. **Positional: one argument per END**, drivers then driven — the
   literal reading of the plan this ADR supersedes in that one detail.
   Rejected: the arity is n + m and frequently duplicated, because the
   ends of one mechanism usually share owners — Kossel's law becomes
   `def delta_rod(machine, _y, _z, rod, _lean, _swing, _rise)`, seven
   parameters, five ignored; OpenFlexure's becomes
   `def leg_lean(body, _dy, leg, _tilt)`. It would also require
   rewriting ADR-089's "a callable of two arguments" rather than
   re-shaping it.
3. **De-duplicating the owners.** Rejected: a law's arity would depend on
   how many ends happen to share a node — a property of the tree, not of
   the sentence.

`forward` is called with ONE POSITIONAL ARGUMENT PER SOURCE (spread, not
boxed — the law is the mechanism's own function of its own inputs) and
returns the value itself for one driven end, unchanged, or a SEQUENCE of
exactly m values, in written order, for several. The asymmetry is
Python's: arguments can be spread and a return cannot.

## Decision Outcome

**An end of a relation may be SEVERAL coordinates**, on the driven side
written as a tuple, on either side written with `&`. **The law is still a
callable of two arguments**, and what generalizes is their SHAPE: a side
naming one coordinate is handed that coordinate's owning node; a side
naming several is handed the TUPLE of their owners, in the order
written.

**A relation naming several ends is applied in ONE DIRECTION only**: when
every source is bound, binding every driven end together, and is NEVER
read backwards, whatever its law offers — for the reason a broadcast is
never read backwards (ADR-096): recovering n sources from m driven values
would mean comparing or solving values, which the framework does not do.
`ratio=`/`offset=` and the bare default law are refused with a group on
either side, naming the relation: an affine law relates one value to one
value, and a relation naming several ends carries a `law=`.

**One RECORD holds all of a relation's ends**, driver ends and driven
ends each a tuple of length n and m; the one-to-one relation is the case
n = m = 1 and is the same object it always was. Under a BROADCAST this is
one such record PER REALIZED COPY (ADR-096's shape, "one end each" read
as "one END-SET each"), and every driven end in a driven group must fan
out over the SAME repeated segment — a driven group mixing a broadcast
with a plain end, or two different repeats, is refused at class
definition naming both paths. **The record's `copy` becomes the node the
REPEATED SEGMENT itself realized**, not the coordinate's owner: a small
correction to ADR-096's `copy = driven.node`, the two differing only when
a broadcast path continues past the repeat (`legs.femur.lift`), where
`copy` now names the LEG rather than the femur.

**All m driven ends are CLAIMED before any is bound**, so a target
something else already bound is refused without leaving a half-applied
law; the claim, applied and refused messages are the SAME `_claim`,
`_step_relation` and `_refuse` a one-to-one relation always used,
generalized over n and m rather than replaced.

**The law's return is checked at every application, by name.** A return
that has no length, is text, or has a length other than m is refused —
naming the relation, the law, the driven ends as written and what came
back — rather than bound, because a value slot accepts whatever is put
into it and a mismatched sequence bound into one slot is a pose nobody
stated. This is a `CouplingError`, not a new error kind: the three named
refusals ("Three refusals keep a wrong drive network from becoming a
pose") stay three.

**A coordinate on both sides of one relation naming several ends is
refused**, at class definition, naming the relation. Widening that check
to a plain one-to-one relation (`a.drives(a)`, unrefused today, which
deadlocks into `UnreachedCoordinate`) is a strict improvement this cycle
does not measure against the catalogue and is not taken here.

## Consequences

- **A group hands a law arguments it may not use** (InMoov's four
  ignored motors when a per-copy selector reads only one; Kossel's
  duplicated machine owner across three sources). Accepted: the
  alternative (positional, one argument per end) was measured worse
  (Considered Options above).
- **InMoov's sighting is closed as a SELECTOR, not as the cleaner
  sentence.** `(thumb & index & middle & ring & little).drives(
  fingers.drive, law=by_finger)` replaces ten `connect()` calls with two
  relations, but the law picks one of five sources by the copy's own
  `index` rather than each copy naming its own one source — that needs
  INDEXING A REPEAT IN A CLASS BODY, which cycle 1
  (`repeat-fan-out`) named as a non-goal and this cycle does not add.
  Recorded in `workflow/warts.md` as a residual want.
- **The Pascaline's eight-way carry stays open.** Multi-source closes
  the pawl (two ports of one class); the root's carry is list-held
  children with a structurally different expression per position, a
  separate finding this ADR does not touch.
- **`&` is not the ratified spelling** the plan named
  (`workflow/docs/motion-catalogue-2.md` section 3.5). Measured
  impossible; the driven side keeps the ratified tuple verbatim, and the
  plan is corrected by this ADR and the change's own record.
- **Nothing existing moved.** Every form this cycle gives a meaning to
  raised a hard error before it (measured, three of them in
  `evidence/probe_today.py`), so no project can have depended on it; the
  proof is a pose comparison over every project on the motion layer at
  the base and at the head, maximum deviation zero
  (`openspec/changes/multi-source-multi-target-laws/evidence.md`), plus
  four read-only overlays proving the sentences above at the same
  tolerance.
- **kossel, the Pascaline, OpenFlexure and InMoov become refactorable at
  their own next stage**, in their own repositories' own cycles; this
  ADR does not edit a project.
