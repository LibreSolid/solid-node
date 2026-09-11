# ADR-101: Motion sharing begins at construction

**Status:** Accepted

**Date:** 2026-09-11

**Change:** [expression-graphs](../../../openspec/changes/archive/2026-09-11-expression-graphs/)

**Supersedes in part:** [ADR-080](../EXPORT/ADR-080-a-shared-subexpression-is-named-once.md)
— detecting sharing only after string construction, unchanged expanded SCAD
text, and the proposed eager-string-plus-graph follow-up. Its schema-4 table,
consumer semantics, version ladder and legacy fallback remain accepted.

**Depends on:** [ADR-022](ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
and [ADR-076](ADR-076-mechanism-laws-as-compositions-over-expression-math.md).

## Context

Curta Type I-3x composes arithmetic, carry engagement, spring spreading and
six flexible coordinates at multiple stations. Its old producer exhausted
memory before reaching ADR-080's binding pass: the failed process reached
7,857,084 KiB RSS. A carry expression of roughly 7.7 million characters was
repeated 35 times by one profile. More RAM would postpone the same growth.
The pilot wants OpenSCAD retained as a modelling technology, not as the
framework's mandatory motion broker. Removing the SCAD lifecycle and deciding
the OpenSCAD viewer's future are explicitly later questions.

## Decision

Native immutable scalar nodes retain references to literal/input/operator/call
operands. Construction does not render strings, recursively hash the graph, or
place graphs in a process-global strong registry. Live values own their graph;
compiler tables are local to a publication.

A separate SolidPython-compatible facade preserves the current arithmetic API,
including reflected operations, comparisons, `abs`, legacy constants and degree
math. Framework time and qualified driver reads produce that facade. Numeric
poses still rerun the original laws with numbers; declared parameter algebra
does not change. Symbolic truth and non-numeric `set_state` remain refused.

Build, export, browser staging and fixture generation collect native operation
and flexible-parameter roots, then compile directly into schema 4. Iterative
postorder structural interning and occurrence counts saturated at two account
for root multiplicity and repeated operand edges, but not discarded temporaries.
Verification compares graph structure against compact published expressions.
Diagnostics and flexible time-dependency checks do not first flatten graphs.

Standalone `str`, `.value`, operation serialization and SCAD output emit
self-contained scalar `let` closures when there is sharing. Local names avoid
free-input capture. Bare and unshared text retains its former spelling. A
restricted iterative parser imports these closures, resolves sequential local
bindings and nested scope, and removes the closures before viewer publication.
Unknown legacy syntax retains its verbatim fallback with a truncated warning.
This is not an OpenSCAD interpreter or a new viewer grammar.

## Alternatives considered

- Name only at motion-port boundaries: narrower, but one complicated law can
  still expand internally.
- Compact piecewise lookup: removes Curta's large multiplier, but not general
  duplication and would require a separate viewer contract.
- Retain eager strings alongside graphs: still allocates the failing text.
- Global interning: unnecessary to prevent reuse expansion and complicates
  ownership across repeated or concurrent builds.
- More RAM, baked poses or fewer controls: do not repair the growth contract.

## Consequences

The complete Curta machine now exports under the 8,000,000,000-byte aggregate
limit with all controls intact. Exact warm/cold peaks, source identities,
reproduction commands and limitations are recorded in the linked change's
`evidence.md`; the limit is not a hardware requirement. The export carries
9,969 bindings, and 33,254 values across 13 poses agree with the unchanged
viewer to within 1.8e-15. Browser photographs also show the carry spring moving.

Compound text is intentionally different: code parsing `repr`, comparing exact
expanded spelling or expecting standalone text without local bindings must
use the documented output boundary instead. Explicit third-party string
expansion remains outside the construction bound. Each SCAD output site may
contain its own compact closure. No geometry backend, dependency extra,
licensing boundary or assembly lifecycle is removed in this cycle. The
negative-remainder caveat in ADR-022 remains unchanged.
