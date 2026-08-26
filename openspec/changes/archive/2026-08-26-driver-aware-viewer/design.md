# Design: driver-aware viewer

## Context

Stage 3b of ADR-056. After 3a, the document carries a `drivers` table
and qualified named-driver expressions; the widget refuses a non-empty
table (`viewer.ts:assertRenderable`). Current widget internals this
change extends:

- `evaluator.ts`: jokenizer with a cached token tree per expression,
  OpenSCAD degree-trig and `^`→`pow` shims, `evalExpr(expr, time)`
  binding `{...mathContext, $t: time}`; `isAnimated` =
  `includes('$t')`.
- `tree.ts`: `operationIsAnimated` → `TreeNode.animated` decides which
  subtrees recompute matrices per frame; `tree.update(time)` runs in
  the render loop.
- `viewer.ts`: `mount()` → `ViewerHandle` (imperative, chrome-free);
  the animation loop advances `time` on wall-clock elapsed and calls
  `tree.update`.
- Spike-proven facts: dotted ids parse as jokenizer `Member` access
  (nested context map, no grammar change); free variables read off the
  parsed tree separate static/driver/mixed and never mistake function
  names; parity with Python is 2.5e-14 over the spike corpus with the
  `^` rewrite load-bearing.
- The producer does not yet serialize instructions; `Sim` converts
  design-unit targets to native through `Driver.scale`/dtype and
  replaces an active program on re-trigger (last-wins).

## Goals / Non-Goals

**Goals**

- A v2 document with drivers loads, renders at declared defaults, and
  is drivable programmatically: `drivers()`, `instructions()`,
  `setDriver`, `driver`, `trigger` (ramp with exact landing, `done`
  promise, `cancel`, last-wins), `onDriverChange`.
- Driver changes re-evaluate only what references them.
- Evaluation semantics parity-pinned against the producer, in CI.
- Empty-table documents and driverless projects: behavior identical.

**Non-Goals**

- No UI chrome; no layout or styling changes.
- No determinism contract on the client ramp (Python `Sim` owns
  determinism); no fixed-dt client stepping.
- No range clamping anywhere.
- No sequencing, no G-code, no evaluation of anything but the
  document's own expressions.
- No Python behavior change outside the producer's instructions table.

## Decisions

### D1. Evaluation context: nested driver map + `$t`

`evalExpr(expr, scope)` where scope carries `time` and a nested driver
map built from qualified ids (`{x_axis: {motor: 8000}}`). Dotted ids
then resolve by jokenizer's existing member access — no evaluator
grammar change (spike). Root-declared bare ids sit at the top level.
Alternative (flat map with `__`-joined keys) rejected: it would
require rewriting the document's expressions, whose ids are the
ratified dotted form.

### D2. Free-variable sets replace `isAnimated`, cached beside tokens

One extra walk per distinct expression over the already-cached parse:
`Member` chains collapse to their dotted name, `Call` callees are
skipped. An operation is time-driven iff `$t` is free in it,
driver-driven iff any driver id is; `tree.update` recomputes a node's
matrix when time changed and the node is time-driven, or when a
changed driver's id intersects the node's free set. Alternative (keep
substring test plus driver substring) rejected: an author-chosen
driver name like `total` false-positives inside function names — the
defect the spike demonstrated.

### D3. Driver state lives on the mounted viewer, natively

One state object per mount, keyed by qualified id, initialized from
the table's `default`s, values in native driver units (what the
expressions consume and what `default`/`range` declare). `setDriver`
validates the id against the table (loud unknown-id error listing
known ids), stores, marks the id dirty for the next frame. No clamp.
`scale`/`unit` are published so hosts convert for presentation.
Alternative (design-unit API with internal conversion) rejected:
`driver(id)` and expression inputs would disagree, and integer dtypes
would round twice.

### D4. `trigger` replays `Sim`'s conversion and last-wins semantics

`trigger(id)` looks up the instruction (loud unknown-name error
listing known qualified names), converts each design-unit target to
native through the driver table (`scale`, dtype rounding — the same
arithmetic `Instruction`/`Driver.native` performs in Python), and
starts one ramp per target driver: linear from the driver's current
value, advanced by wall-clock elapsed in the existing animation loop,
value rounded per frame for integer dtypes, final frame exactly the
converted target. A new ramp on a driver replaces the active one from
the current value (Sim's program replacement). Returns `{done,
cancel()}`: `done` resolves when every target lands, `cancel()` stops
ramps where they are and resolves `done`. Disposal cancels active
ramps. Alternative (fixed-dt client stepping mirroring Sim tick for
tick) rejected: it would promise a determinism the render loop cannot
keep and 3b does not need; scenario truth stays in Python.

### D5. `onDriverChange` coalesces per frame

Listeners fire once per changed driver per animation frame while
ramps run, and synchronously on `setDriver`. Returns an
unsubscribe function. This is the minimum a host needs to bind
readouts without polling; richer event schemas wait for a real host.

### D6. Instructions are additive within document version 2

The producer adds `instructions`: qualified instruction name →
`{targets: {qualified driver id: design-unit value}, duration}`.
No version bump: a document carrying instructions necessarily carries
a non-empty `drivers` table (instructions target drivers), and every
pre-3b consumer already refuses non-empty tables loudly, so no
existing consumer can silently misread the new key. Alternative
(bump to v3) rejected as cost without protection — the gate that
matters is the drivers table, and it is already loud. Flagged in the
proposal for explicit ratification.

### D7. Parity is pinned against the real module

The evaluator's vitest suite gains a parity fixture: expression
strings plus Python-computed expected values (generated from the
spike corpus by a checked-in Python script, committed as JSON so the
TS tests run without Python). Tolerance per ADR-022 discipline: same
semantics, float rounding only. The spike's hand-copied
`parity_harness.js` note is superseded; seam 7 closes. ADR-022 is
revised in the same cycle.

### D8. The loader gate inverts, once

`assertRenderable`'s non-empty-table throw is replaced by evaluation.
The stage-3a gate tests are rewritten to the new consumer contract
(cite the export delta): a document whose expressions reference an id
missing from its table — a malformed document — still fails loudly.

## Risks / Trade-offs

- [Per-frame driver evaluation cost on large trees] → free-variable
  sets bound the work to referencing operations; token trees and free
  sets are cached once per distinct expression; the existing per-frame
  `$t` evaluation is the proven baseline.
- [Client/Python conversion drift on instruction targets] → one
  conversion rule, parity-tested: the fixture includes design→native
  conversions with integer dtypes, compared against `Driver.native`.
- [Wall-clock ramps look different across frame rates] → endpoints and
  duration are exact; only intermediate sampling varies. Recorded as
  intended behavior (animation, not simulation).
- [Additive `instructions` key surprises a strict v2 parser] → the
  only shipped consumers are this repo's; the export spec's
  producer/consumer lockstep rule covers external ones, and the
  drivers-table gate already forces pre-3b consumers to refuse such
  documents.
- [Bundle symlinked in this bench] → TS source + vitest carry the
  change; packaging rebuilds `dist` as in 3a. Verified at the
  packaging step, stated honestly in the completion record.

## Migration Plan

Single repository. Red-first per requirement (vitest for the widget,
pytest for the producer). Landing order: evaluator scope + free
variables → producer instructions table → loader inversion + state
store → trigger/ramps → parity fixture → ADR-022 revision. Callers
revalidate: full suite, v8-engine 33/33 (driverless documents
unchanged), both spike runners; closing evidence: the spike machine
driven through the new API in a live viewer (visual sanity check).
Rollback is reverting the implementation commit; no schema version
changes.

## Open Questions

- None blocking. Deferred by decision: UI chrome (next cycle), G-code
  programs in the `trigger` seat, `evalExpr` public API shape for
  third-party hosts (kept internal until a real external host exists).
