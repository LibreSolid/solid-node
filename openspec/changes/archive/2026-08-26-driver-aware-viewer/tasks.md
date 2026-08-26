# Tasks: driver-aware viewer

Red-first throughout: vitest for the widget, pytest for the producer.
No UI chrome anywhere in this change.

## 1. Producer: instructions table

- [x] 1.1 Red pytest: exported/build documents carry the
  `instructions` table (qualified names, design-unit targets keyed by
  qualified driver id, duration, verbatim from declarations; empty
  table for instruction-less trees; sibling instances publish
  `x_axis.Home` / `y_axis.Home`)
  — `tests/test_document_drivers.py::InstructionTableTest` (7 tests) and
  the shared-schema assertion in
  `test_export.py::ExportBuildSnapshotParityTest`. Red: `ImportError:
  cannot import name 'instructions_table'` and `KeyError:
  'instructions'` on both documents.
- [x] 1.2 Implement in the serializer/export/builder via the tree-walk
  enumeration (one walk with the drivers table); update the manifest
  fixture types in `widget/src/types.ts`
  — `serializer.symbolic_document` collects instructions through
  `drive_tree`'s `visit` hook (one descent, no second walk);
  `instructions_table` qualifies targets through the same `driver_id`
  that keyed the driver table. `symbolic_drivers` kept as a wrapper, so
  no existing caller or test changed. Export, builder and the browser
  snapshot (empty, by construction) publish the key; `types.ts` gained
  `ManifestInstruction`. Green: 24 passed.

## 2. Evaluator: driver scope and free variables

- [x] 2.1 Red vitest: `evalExpr` evaluates dotted qualified ids
  through a nested driver map alongside `$t`; degree trig and `^`
  unchanged; bare root-driver ids work
  — `evaluator.test.ts` "evalExpr over a driver scope". Red: 12 of 14
  failing. The three pre-existing cases changed call shape only
  (`evalExpr(expr, {time})`), per design D1 — same expressions, same
  expected values.
- [x] 2.2 Red vitest: free-variable extraction off the cached parse —
  static / `$t`-only / driver-only / mixed separation; `Member` chains
  collapse to dotted names; `Call` callees never counted; a driver
  named `total` is not found by substring
  — `evaluator.test.ts` "freeVariables". Red: `freeVariables is not a
  function`.
- [x] 2.3 Implement both; replace `isAnimated` consumers
  (`tree.ts:operationIsAnimated`, `TreeNode.animated`) with
  free-variable classification (time-driven vs driver-driven vs
  static)
  — `isAnimated` deleted. `WidgetTree.update(scope, changed)` recomputes
  a node when time advanced and it reads `$t`, or when a changed driver
  is in its cached free set; `animated` now means time-driven only.
  Red evidence for the tree half: 3 failures in `tree.test.ts`
  "WidgetTree driver-aware updates" (a driver change re-evaluated every
  operation; `animated` unavailable). Green: 18 passed. Selective
  re-evaluation is proved by spying on the real `evalExpr` through
  `vi.mock`+`importOriginal`, so the evaluator under test is the shipped
  one.

## 3. Loader and driver state

- [x] 3.1 Red vitest: a non-empty-table document mounts and renders at
  declared defaults (gate inversion — rewrite the stage-3a gate tests
  to the new consumer contract, citing the export delta); an
  expression referencing an undeclared id fails loudly naming it;
  empty-table documents behave exactly as v1
  — `document.test.ts` rewritten, citing the export delta's
  producer/consumer clause and design D8 in its header. Red: 4 failures
  (a legal driver document was still refused; an undeclared id was not
  detected). Green: 7 passed.
- [x] 3.2 Red vitest: per-mount driver state — `drivers()` verbatim,
  `driver(id)`, `setDriver` (unknown id loud with known ids listed; no
  range clamp; only referencing operations re-evaluate),
  `onDriverChange` (per-frame coalescing, synchronous on `setDriver`,
  unsubscribe)
  — `drivers.test.ts` "DriverStore state" / "change notification". Red:
  `Cannot find module './drivers'`. The "only referencing operations
  re-evaluate" half is pinned at the tree level (task 2.3).
- [x] 3.3 Implement the state store, handle methods, and dirty-driver
  re-evaluation in the render loop
  — new `drivers.ts` (`DriverStore`): native units, no clamp, loud
  unknown id listing the declared ones, nested `scope()` with bare root
  ids at the top level, `tick()` returning the frame's changed ids.
  `viewer.ts` holds one store per mount, reconciles it on republish
  (keeping the values of surviving ids), and the handle delegates
  `drivers`/`driver`/`setDriver`/`onDriverChange`. Green: 92 passed
  across the widget suite; `tsc --noEmit` clean.

## 4. Instructions: trigger and ramps

- [x] 4.1 Red vitest: `instructions()` verbatim; `trigger` converts
  design-unit targets to native (scale + integer-dtype rounding
  matching `Driver.native`), ramps linearly from current value over
  duration, whole intermediate values for int dtypes, exact landing;
  last-wins replacement; `done` resolves on landing and on `cancel()`;
  unknown name loud with known qualified names; `dispose()` cancels
  — `drivers.test.ts` "toNative" / "DriverStore instructions" /
  "DriverStore ramps". Red: 14 failures (`toNative is not a function`,
  `drivers.trigger is not a function`). The ramp code had been written
  ahead of this red run and was removed from `drivers.ts` before it, so
  the failures are against a store that genuinely lacked the feature.
- [x] 4.2 Implement ramps in the animation loop (wall-clock elapsed,
  endpoint-exact)
  — `Ramp`/`Run` in `drivers.ts`; `viewer.ts` calls `drivers.tick()`
  each frame and feeds the changed ids to `tree.update`. Integer dtypes
  floor the distributed delta (mirroring `RampProgram`'s `//`) and the
  landing frame returns the target itself. `toNative` rounds half to
  EVEN, matching Python's `round`; one test expectation of mine was
  wrong about a float (`0.01875/0.0125` is `1.4999999999999998`, so
  Python answers 1) and was corrected against verified interpreter
  output before it ever passed. Green: 28 passed.

## 5. Parity under test

- [x] 5.1 Add a checked-in Python generator producing the parity
  fixture JSON from the spike expression corpus (linear, scaled,
  degree trig, `^`, mixed `$t`+driver, design→native conversions for
  int dtypes) with producer-computed expected values; commit the
  fixture
  — `widget/tools/generate_parity_fixture.py` →
  `widget/src/parity-fixture.json`. Expected values are producer
  values, not a reimplementation: the spike's two-axis machine is
  serialized twice (numerically bound, then symbolically) and the two
  structurally identical walks are zipped. 182 expression cases, 14
  containing `^`, 22 conversions — the same 182/14 the spike recorded.
- [x] 5.2 Red vitest: the fixture runs against the SHIPPED evaluator
  module; verify the suite fails with the `^` rewrite disabled; then
  green. Note in `spike/expressions/FINDINGS.md` that seam 7 is closed
  and `parity_harness.js` is superseded as the parity authority
  — `parity-fixture.test.ts` imports `./evaluator` directly. Red
  evidence: with `powify` removed from `tokensFor`, 14 cases fail, worst
  deviation `0.1862511823824271` — the spike's recorded 0.186. The
  evaluator was restored and byte-compared against its pre-experiment
  copy. Green: 7 passed. FINDINGS.md carries a dated addendum; nothing
  earlier was rewritten.

## 6. Records and validation

- [x] 6.1 Revise ADR-022: single evaluator, defect fixed, parity
  enforced by the fixture, driver-map evaluation in scope; update its
  status/date discipline and the ADR index if its status line changes
  — status now `Accepted, revised 2026-08-26`; the stale four-runtime
  section and the KNOWN DEFECT section are marked superseded/fixed in
  place rather than deleted (they are the context the decision was
  taken against), and a `Revision (2026-08-26)` section records the
  three changes plus the scope extension to driver expressions.
  `docs/adrs/README.md` line updated.
- [x] 6.2 Full validation: widget vitest suite; full framework pytest
  suite (zero regressions from the producer change); v8-engine 33/33
  via `solid test` (driverless documents byte-identical); both spike
  runners exit 0
  — widget vitest **99 passed / 9 files** (43 baseline); pytest
  **879 passed + 44 subtests** (872 baseline + the 7 new producer
  tests, zero regressions); v8-engine **33 passed, 0 failed** in
  198.77s; `spike/expressions/run_spike.py` exit 0 with parity
  unchanged (2.487e-14 scalar, 4.302e-16 matrix, `^` worth 0.186) and
  `spike/axis/scenario.py` exit 0, all five verdicts validated.
  `tsc --noEmit` clean.
- [x] 6.3 Visual sanity check (evidence, not deliverable): serve the
  spike machine's document, drive `setDriver` and
  `trigger('x_axis.Home')` from the console, confirm motion and
  record the observation in the cycle notes
  — Run by the caller after implementation: the implementing agent
  correctly reported the bench's `widget/dist` symlink stale
  (2026-08-18, pre-3a) and off-limits, so the caller built a fresh
  bundle to a temp path with the widget's own esbuild config (no write
  under `dist/` or the primary checkout), exported the spike machine
  (`version: 2`, drivers `x_axis.motor`/`y_axis.motor`, instructions
  `x_axis.Home`/`y_axis.Home`), served it locally, and drove it in
  headless chromium via playwright. Observed: mount clean;
  `setDriver('x_axis.motor', 4000)` reads back; `trigger('x_axis.Home')`
  produced 121 `onDriverChange` samples, all whole µsteps,
  monotone 3997 → exactly 0; `y_axis.motor` held 8000; before/after
  screenshots differ; zero page errors. The shipped `dist` bundle is
  still rebuilt at the packaging step.
- [x] 6.4 Update `docs/architecture.md` (viewer driving API, gate
  inversion, instructions table, parity fixture) and ADR-056
  (implementation status; open questions: viewer evaluation resolved;
  UI chrome and G-code remain); archive the change and sync baseline
  specs
  — **Documentation done; archive deliberately not done.**
  `docs/architecture.md`: the instructions table beside the drivers
  table, the handle's driving API and free-variable re-evaluation, the
  MATH section rewritten to three runtimes with enforced parity, the
  stale "export-widget parity defect" and "no parity enforcement" gaps
  replaced by the one that remains (OpenSCAD is outside the fixture),
  and two invariants updated. ADR-056: a stage 3b implementation-status
  entry, the two resolved open questions moved out of "still open", and
  UI chrome recorded as the deferred one. Archived and baseline specs synced by the caller after
  independent verification: 879 pytest + 44 subtests, widget vitest
  99/99, v8-engine 33/33 via solid test, both spike runners exit 0,
  tsc clean, and the live headless-browser drive recorded in 6.3.
