# ADR-104: A Third Time Base — Elapsed Seconds That Never Wrap

**Status:** Accepted
**Date:** 2026-09-13
**Extends:**
- [ADR-072: A declared time base](./ADR-072-a-declared-time-base.md)
**Cites:**
- [ADR-008: Time-based animation system for assemblies](./ADR-008-time-based-animation-system-for-assemblies.md)
**OpenSpec change:** `run-owns-the-coordinates`

## Context and Problem Statement

ADR-072 gave a root one thing to declare about time: `Time(loop=L)`, the
span of machine time one turn of the `$t` timeline covers. That is the
right sentence for a machine with a CYCLE — a clock, an engine, a
mechanism that repeats. It is the wrong sentence, and an unstatable one,
for a machine that is OPERATED: a Curta cranked twice, a Pascaline dial
advanced a step at a time, a printer executing a program that can pause
and resume. Such a machine has no period to normalize against, and its
pose depends on where it already stood.

Measured on this tree before the change: `Time` required `loop`
(`motion/ports.py`), `read_time` scaled `$t` by it
(`node/assembly.py`), `animation_block` published it
(`core/serializer.py`) and the snapshot manager multiplied by it
(`manager/snapshot.py`). A root had exactly two states — declared, or
undeclared — and a machine that runs had to pick a loop it does not have.

## Decision Drivers

- The declaration is what selects the execution mode; a model must be
  able to SAY "this machine runs" in the place it already says what its
  time means.
- Nothing about untimed or looping models may change: three producers
  read `loop`, and every existing document must stay byte-identical.
- The running mode's own symbolic form — elapsed seconds as an
  expression a viewer could evaluate — depends on publishing the
  compiled program, which is a later cycle. The base must be declarable
  before that exists, without publishing a form nothing can read.

## Considered Options

1. **`Time(running=True)`** — a second field, exclusive with the first,
   checked in `__post_init__`. Rejected: two spellings of one fact, and
   a declaration that reads as a flag rather than as the thing it
   declares.
2. **A separate `Running()` declaration class** — rejected: every
   consumer that reads `declared_time(cls)` would have to learn a second
   type, where a `mode` on one type costs them a string comparison.
3. **Refuse an unbound `time` read under a running root** — honest about
   the missing symbolic form, but it would fail a build whose
   `simulate()` reads `self.time` for a reason that lives entirely in
   the run. Rejected, and recorded as an open question for the export
   cycle.
4. **Publish elapsed seconds as some placeholder expression** —
   rejected: a document carrying a form no consumer can evaluate is
   worse than one carrying none.

## Decision

`Time` keeps its ONE field, `loop`, which becomes optional, and a
constructor per base tells them apart:

- `Time(loop=<seconds>)` is the LOOPING base, unchanged.
- `Time.running()` is the RUNNING base — a frozen instance whose `loop`
  is `None`, built without `__init__` because the field is deliberately
  absent there and validated here.
- `Time()` with neither is refused, as a `TypeError` naming both
  spellings, exactly as a missing required argument always was.
- `Time.mode` is a property reading `'loop'` or `'running'`, readable
  off the class through the declaration as `loop` is.

`__set_name__` is untouched, so both bases obey the same declaration
rules: only under the name `time`, only on an `AssemblyNode`, only on
the root of the tree they are read in.

Under the running base `self.time` reads, bound, the bound number — the
simulation binds `k*dt` seconds as it does today, and
`set_keyframe`/`set_state(time=)` state seconds — and, unbound, **bare
`$t`**, exactly what an undeclared root reads. Every producer that reads
the declaration treats `loop is None` as NO LOOP: `animation_block`
publishes no `loop` key, the snapshot manager keyframes the fraction,
and `read_time` leaves `$t` unscaled.

## Consequences

- A running root's document is byte-identical to an undeclared root's,
  so `solid build`, `solid export`, `solid develop` and `solid snapshot`
  keep working on one with no change anywhere in the export or viewer
  path.
- The preview of a running model plays it as if time ran from 0 to 1
  second. That is what an undeclared root shows, and it is the honest
  answer until the compiled program is published; the running behaviour
  lives in the simulation until then.
- `declared_time(cls)` keeps returning the declaration for both bases;
  a consumer that must tell them apart reads `.mode`, and one that must
  not care reads `.loop` and gets `None`.
- What the base CHANGES is stated by ADR-105 and ADR-106: what a
  simulation over the root owns, and which of a law's two readings it
  takes. Nothing else about the tree changes.
