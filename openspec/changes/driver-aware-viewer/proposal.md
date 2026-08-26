# Proposal: driver-aware viewer

## Why

Stage 3b of ADR-056. Stage 3a made the serialized document carry a
driver table and named-driver expressions, but the shipped viewer can
only refuse such a document loudly — it evaluates `$t` alone. The
pilot's product goal (an app where clicking buttons triggers
instructions and the machine responds visibly) needs the viewer to
evaluate driver expressions and expose a programmatic driving API. No
visual elements: buttons and sliders are a later cycle (or the app's
own); this change is the API they will call. It also finally puts
cross-runtime evaluator parity under test — measured at 2.5e-14 by the
expression spike but unenforced since ADR-022 recorded the risk.

## What Changes

- **Driver-aware evaluation.** The widget evaluator takes a driver
  variable map alongside `$t` (nested map; dotted qualified ids
  resolve as member access — spike-proven, no grammar change), with
  degree-trig and `^` semantics unchanged.
- **Free-variable analysis replaces `isAnimated`.** The substring test
  (`includes('$t')`) becomes the free-variable set read off the parsed
  expression tree, separating static, time-driven, driver-driven, and
  mixed operations; a driver change re-evaluates only operations that
  reference it.
- **v2 documents with drivers load.** The stage-3a loud refusal of a
  non-empty `drivers` table is replaced by evaluation: driver state
  initializes from the table's defaults and the document renders at
  its default pose. Empty-table documents behave exactly as today.
- **The driving API on the viewer handle** (ratified interface, native
  driver units, ids verbatim from discovery): `drivers()`,
  `instructions()`, `setDriver(id, value)`, `driver(id)`,
  `trigger(id)` returning `{done, cancel()}`, and
  `onDriverChange(fn)`. `trigger` runs the client-side linear ramp
  over the instruction's duration — the degenerate simulator ADR-056
  planned as the seat of the future G-code interpreter — with exact
  landing and last-wins replacement of an active ramp, matching `Sim`.
  `range` is never clamped. `time` keeps its existing transport and
  enters evaluation as `$t`.
- **Instructions serialize into the document.** The export producer
  publishes declared instructions (qualified name, design-unit targets
  keyed by qualified driver id, duration); the client converts targets
  to native units through the driver table exactly as `Sim` does.
  **Decision for ratification:** the `instructions` key is additive
  within `version: 2` — any document carrying instructions also
  carries a non-empty `drivers` table, which every pre-3b consumer
  already refuses, so no consumer can misread it.
- **Parity under test.** Evaluation-semantics tests run against the
  real evaluator module (not the spike's hand copy), pinning agreement
  with producer numerics across the spike's expression corpus
  (degree trig, `^`, mixed, member access) — closing expression-spike
  seam 7.
- **ADR-022 revised** to the current reality: single evaluator, the
  recorded defect fixed, parity now enforced; driver-map evaluation
  added to its scope.
- **Ramp clock decision:** client ramps are wall-clock per animation
  frame with exact landing (rounded per frame for integer dtypes,
  final value exactly on target). Determinism claims remain exclusive
  to the Python `Sim`; the client is an animation, not a test
  artifact.

Out of scope: all UI chrome (buttons, sliders, transport panels — a
later cycle or the host app), G-code and instruction sequencing,
`Driver.scale`/`Port.scale` merge, range clamping, any Python
node/simulation behavior change (the framework side is done; only the
export producer gains the instructions table).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `viewer-package`: the handle gains the driver discovery/driving/
  instruction API; the document loader evaluates driver expressions
  instead of refusing non-empty driver tables; evaluation semantics
  are parity-pinned against the producer.
- `export`: the manifest contract adds the `instructions` table
  (additive within version 2) and re-scopes the consumer clause — a
  consumer SHALL either evaluate driver expressions or fail loudly,
  and the shipped viewer now evaluates.

## Impact

- TypeScript only, plus one Python producer addition:
  `viewers/widget/src/{evaluator,tree,assembly,viewer,types}.ts` (and
  tests), `core/serializer.py`/`core/export.py`/`core/builder.py` for
  the instructions table, with matching Python document tests.
- The widget bundle rebuild happens at the packaging step; in this
  bench `widget/dist` and `node_modules` are symlinks into the primary
  checkout, so the bundle is not rebuilt here (TS source + vitest
  carry the change), as in stage 3a.
- Callers: v8-engine documents are driverless (empty table) — byte-for
  byte unchanged behavior; the stage-3a gate tests change meaning and
  are updated to the new consumer contract, citing the export delta.
- Validation: widget vitest (red-first), Python document tests, both
  spike runners, full framework suite, v8-engine 33/33, and a closing
  visual sanity check of the spike machine driven through the new API
  (evidence, not a deliverable).
- Evidence chain: ADR-056 (app interface), `spike/expressions/`
  (parity corpus, seam 7), the stage-3a archived change, originating
  projects Metamaquina2 and v8-engine.
