# ADR-110: The Compiled Program Is Published in the Document, Under a Version an Old Consumer Refuses

**Status:** Accepted
**Date:** 2026-09-13
**Extends:**
- [ADR-034: Shared node-tree document schema across export and build snapshots](./ADR-034-shared-node-tree-document-schema.md)
- [ADR-080: A shared subexpression is named once](./ADR-080-a-shared-subexpression-is-named-once.md)
**Depends on:**
- [ADR-104: A third time base — elapsed seconds that never wrap](../NODE/ADR-104-a-third-time-base-elapsed-seconds-that-never-wrap.md)
- [ADR-105: The run owns the coordinates and binds them](../NODE/ADR-105-the-run-owns-the-coordinates-and-binds-them.md)
- [ADR-106: One law, two readings](../NODE/ADR-106-one-law-two-readings.md)
- [ADR-107: A jump is located inside the tick and subtracted](../NODE/ADR-107-a-jump-is-located-inside-the-tick-and-subtracted.md)
- [ADR-108: A range is a physical stop that stops the connected group](../NODE/ADR-108-a-range-is-a-physical-stop-that-stops-the-connected-group.md)
- [ADR-109: A range bound may be an expression evaluated at the committed state](../NODE/ADR-109-a-range-bound-may-be-an-expression-evaluated-at-the-committed-state.md)
**Cites:**
- [ADR-051: Producer-owned animation time in node documents](./ADR-051-producer-owned-animation-time-in-node-documents.md)
- [ADR-068: Optional viewer package behind a process boundary](./ADR-068-optional-viewer-package-behind-a-process-boundary.md)
**OpenSpec change:** `publish-the-mechanical-program`

## Context and Problem Statement

ADR-104 to ADR-109 built a machine that RUNS: the simulation owns a bank
of every driver and every joint coordinate, a law is integrated along the
tick rather than read at its end, a jump is located inside the tick and
subtracted, and a declared range is a physical stop. All of it is Python.

None of it reaches a consumer. Cycle 1 promised deliberately that "a
running root's document is BYTE-IDENTICAL to an undeclared root's", which
means its pose expressions are the law evaluated ABSOLUTELY at the driver
values. The acceptance project shows what that costs. The Pascaline
module's `viewer.json`, built before this change, publishes the whole
carry law as the tens register's rotation:

```text
/Pascaline/tens/drum  ["r", "_b58", [1, 0, 0]]
_b58 = (36.0 * tens_entry) + 65.54 * floor(((36.0 * units_entry) - 114.9) / 360.0) + …
```

Fifty-seven of its 147 bindings are that one law, written as a pose. A
consumer moving `units_entry` reads the law AT the new value instead of
integrating ALONG the movement, so the register snaps back at every carry
window, and the `floor` it carries is a jump nothing subtracts. An
absolute reading is exactly what the campaign exists to replace, and an
old consumer cannot tell that it cannot.

So: what does a running root's document have to say, and how does a
consumer that cannot execute it find out?

## Decision Drivers

- A consumer must be able to RUN the machine, not re-derive it. The
  Python run's decisions are already made at compile time; two
  independent implementations of them would be two things to keep in
  step.
- The document's existing expression language, `bindings` table and name
  grammar are a settled contract (ADR-080). Nothing here may need new
  syntax.
- A version bump that is not additive must be refused loudly by a
  consumer that cannot read it, not partially rendered (ADR-034).
- The framework is Apache-2.0 and the viewer AGPL-3.0-only, running as a
  separate process (ADR-068). Nothing of the consumer may be imported to
  decide any of this.

## Considered Options

1. **Publish the pose expressions over driver ids as today** and let a
   consumer map drivers to coordinates. That IS the absolute reading, and
   it is the defect.
2. **Publish a second table of "coordinate → pose expression"** beside
   the tree, leaving the tree's operations over drivers. Every pose
   published twice, and a consumer holding both cannot tell which to
   believe.
3. **Publish the compiled program, and pose the geometry from a
   committed bank.**

## Decision

**A running root's document declares `version: 5` and carries a
top-level `program` object holding what COMPILE TIME decided about the
machine, and nothing the tick computes.**

`program` carries the coordinate table (one entry per bank id, in program
order, with its kind, the rest pose's value, a joint coordinate's
declared unit and a `domain`), the intermediates, the compiled edges IN
PROGRAM ORDER with their law expressions, per-driven-end `affine` flags
and jump plans, a wiring's `factor`, a formula's and a check's
coefficients and slot, the spans, the candidate `sources` table, the
program `identity`, the `clock` name and the five constants the
algorithm is defined by — `agreement` included, so a consumer cannot
silently differ from the producer about when two increments are equal.

What the TICK computes is DERIVED, not published: every bank value after
the initial one, the determiner inversion, the partition, a stop's `t*`,
whether an input pushes a stopped coordinate, the statuses. The rule is
"publish what compile time decided; derive what the tick computes", with
one corollary that settles the two cases the rule alone does not — a
projection of published data with no decision inside it is derived, and
one whose computation embeds a decision is published, which is why
`sources` travels although it could be recomputed.

An INPUT entry repeats nothing the `drivers` table already publishes, and
the two tables name exactly the same set of ids. An input's `domain` is
`null`: a driver declaration states a default, a range, a unit, a dtype
and a scale, and no domain, and deriving one from the unit string would
be a guess the framework makes nowhere else.

**Under a running root a COMMITTED BANK poses the geometry.** The
serialization binds every joint coordinate of the linked tree to a
symbolic token of its own qualified id, beside every driver's, through
the same internal delivery a run's own `set_state` uses and never through
the numeric door. So a joint's placement publishes as that coordinate's
id, a plain port, a derived coordinate and a flexible leaf's `params`
publish as expressions over whatever bank ids drive them, and a consumer
evaluates per frame exactly the expressions it evaluates for any other
document — from a scope holding the bank it just committed. No second
table of poses is published, and flexible parts follow unchanged.

`time` leaves the document with it: under a running root it publishes as
the free name `time`, declared as `program.clock`, which a runtime binds
to elapsed simulation seconds and a consumer with no run binds to zero.
`$t` keeps its one meaning, the 0..1 animation fraction. Every reading of
an unbound `time` OUTSIDE the document producer is untouched.

**The version is a property of the ROOT'S DECLARATION.** The ladder below
5 is read off the content, because flexible leaves and shared
subexpressions are properties of the tree; a compiled program is a
property of what the root declares, and a running root with a trivial
program is still a machine a version 4 consumer would animate wrongly. An
untimed or looping root never reaches 5 and its document is unchanged in
every byte.

**The bump is not additive**, so a consumer that cannot read it refuses
by name. The framework asks the installed viewer what it renders through
the existing `solid_node.viewer` entry point — `documentVersions`, read
as `[1, 2, 3, 4]` when the field is absent, which is every viewer
released before it existed. `solid build`, `solid develop` and `solid
export` publish the document and WARN once; the Sphinx directive warns
about a committed export it embeds, off the manifest it already opened
and with no CAD runtime loaded; `solid snapshot --renderer web` REFUSES
before the browser starts, because a capture is a one-shot whose failure
would otherwise surface as an opaque non-zero exit from a headless page.

Two smaller decisions follow from the same place. The `instructions`
table publishes BOTH forms under version 5 and goes on omitting the
relative one below it, because the shipped viewer reads `targets` off
every entry. And `solid snapshot` gains `--drive NAME=VALUE`: a still of
a running root is the untimed REST POSE at the requested driver values,
which is the state a simulation itself starts from; a `--drive` naming a
joint coordinate is refused by name, because with no run to own it the
enumeration that binding runs recomputes the coordinate from the drivers
and the value is lost.

## Consequences

- A consumer can execute a published machine without a second compiler.
  The program it receives is the program the Python run executes: the
  producer compiles it through the run's own construction, so the
  identity in the document is the run's by construction rather than by
  two implementations agreeing.
- The acceptance project's register poses as the single name
  `tens.drum.turn`, and its carry law lives in `program`, where it is
  integrated. The document grew 8% (30,529 → 32,994 bytes) and its
  binding table shrank from 147 entries to 50.
- Branch placeholders become a published name kind, minted at publication
  across the WHOLE document (`_j0`, `_j1`, … in edge order then postorder,
  under a lengthening prefix). The compiler names them per plan, which
  would let three plans each calling their first jump `$j0` share one
  binding entry between three different jump nodes — measured on the
  acceptance project before the rule was written.
- Publication runs over a tree a live run owns and leaves no trace: the
  publication binder is admitted over a run-owned slot, and every slot's
  value, binder and freshness marks are restored with its joint
  re-placed. The run's bank is untouched and it advances as if nothing
  had happened.
- A running root the run REFUSES — one whose rest render leaves a joint
  coordinate unbound — no longer builds or exports, with the run's own
  message. The program a document publishes is the program the run
  executes, and a root with no program has none to publish.
- The `program` object and every name it mints are ordered
  deterministically, so republishing an unchanged running model produces
  a byte-identical document and the builder's own byte comparison keeps
  working.
- A `Driver` still declares no `domain`, so every input entry publishes
  `null` there. Adding one is strictly additive and is carried as an open
  question.
