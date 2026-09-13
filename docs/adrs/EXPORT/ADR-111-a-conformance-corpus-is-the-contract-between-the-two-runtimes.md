# ADR-111: A Conformance Corpus Is the Contract Between the Two Runtimes

**Status:** Accepted
**Date:** 2026-09-13
**Depends on:**
- [ADR-110: The compiled program is published in the document](./ADR-110-the-compiled-program-is-published-in-the-document.md)
**Cites:**
- [ADR-022: Cross-runtime degree-trig parity for `$t` expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
- [ADR-068: Optional viewer package behind a process boundary](./ADR-068-optional-viewer-package-behind-a-process-boundary.md)
**OpenSpec change:** `publish-the-mechanical-program`

## Context and Problem Statement

ADR-110 publishes the compiled program so a second runtime can execute
it. That makes the run's semantics a CROSS-RUNTIME contract for the first
time, and a contract nothing enforces is a contract that drifts.

ADR-022 is the precedent and the warning: one `$t` semantics,
reimplemented in several runtimes that must agree function for function,
with nothing enforcing their agreement until
`generate_parity_fixture.py` closed it from the producer's side. The run
is the same problem one layer up, and worse: it has state. Two runtimes
can agree on every expression and still diverge on the third tick,
because one of them located a crossing a hair earlier, or called two
increments equal where the other did not.

The two runtimes are also in two repositories under two licences
(ADR-068), so neither can import the other to compare.

## Decision Drivers

- A disagreement must mean the CONSUMER drifted. An expected value
  recomputed a second way proves nothing about either runtime.
- State means the comparison is over a trajectory, not over points: a
  divergence that heals between two samples is a divergence.
- The width of what is pinned must be visible without running the tool
  that writes it, or it narrows silently when someone edits a list.
- The tolerance must be the run's own. A consumer inside the window
  within which the run itself declines to distinguish two increments
  cannot manufacture a disagreement.

## Considered Options

1. **Reimplement the run's assertions in the consumer's suite.** Two
   suites asserting two readings of one behaviour, agreeing by accident.
2. **Compare live, over a bridge.** A process boundary, a licence
   boundary and a network in the middle of a determinism test.
3. **A producer-generated fixture, replayed by both.**

## Decision

**The framework generates a JSON conformance corpus from its OWN run, and
both runtimes replay it.** `tools/generate_running_corpus.py` writes
`tests/running-corpus.json`; the framework's suite replays the committed
file, and the viewer commits a copy and replays it against its worker.

Every expected value in it is a value the framework's run PRODUCED, never
one recomputed a second way — the second half of ADR-022's pattern — so a
disagreement means the other runtime drifted.

The fixture carries, per machine: its name, its `dt`, the published
document's program-bearing keys verbatim; a SCRIPT of commands (moves by
a travel or to a value, rates, instruction triggers, a snapshot and a
restore), each naming the step it is applied before and the handle its
outcomes are reported under; and EVERY STEP of the run, oldest first,
each with the whole committed bank, the crossings and stops located in
that tick, and every command created so far with its status and admitted
travel. A sampled fixture is not accepted.

Agreement is **EXACT** for discrete state — tick numbers, command
statuses, every coordinate, relation, primitive, bound side and input
name, a crossing's surface level, and the ORDER of every list — and
within **`1e-9` RELATIVE** for floats: the bank's values, a crossing's or
stop's fraction of the tick, a stop's evaluated bound, a command's
admitted travel. That number is not new; it is `run.py`'s own
`_TOLERANCE`, the window inside which the run declines to distinguish two
increments, and the document publishes it as `program.limits.agreement`
so the fixture's tolerance and the algorithm's are one number.

**The generator refuses to write a corpus that misses a stated feature**:
each of the five discontinuous primitives, a multi-source law, a stop
located inside a tick, a bound stated as an expression, a command retired
`blocked`, a rate, a snapshot and a restore, an instruction in each of
its two forms, and a tick carrying both a crossing and a stop. The
refusal is under direct test in the framework's suite, so the corpus's
width is visible without running the generator at all.

A framework test also asserts that each fixture machine's REAL published
document reproduces the fixture's own program-bearing keys, so the
fixture cannot drift from the producer it claims to come from.

## Consequences

- The committed corpus is thirteen scenarios over eleven of the
  framework's own running fixtures, 260 ticks, 170 KB. It regenerates
  byte for byte in 1.3 seconds.
- A viewer change that breaks the run's semantics fails in the viewer's
  own suite, in the viewer's own repository, with no Python and no CAD
  stack — the same arrangement the parity fixture already has.
- The corpus is only as wide as its machines, and its machines are only
  as wide as the guard's list. The list is therefore stated in the export
  capability's specification, not only in the tool.
- Adding a run feature without adding a machine that exercises it is
  caught at regeneration, not at the next divergence.
