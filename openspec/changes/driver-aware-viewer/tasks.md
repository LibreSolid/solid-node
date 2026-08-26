# Tasks: driver-aware viewer

Red-first throughout: vitest for the widget, pytest for the producer.
No UI chrome anywhere in this change.

## 1. Producer: instructions table

- [ ] 1.1 Red pytest: exported/build documents carry the
  `instructions` table (qualified names, design-unit targets keyed by
  qualified driver id, duration, verbatim from declarations; empty
  table for instruction-less trees; sibling instances publish
  `x_axis.Home` / `y_axis.Home`)
- [ ] 1.2 Implement in the serializer/export/builder via the tree-walk
  enumeration (one walk with the drivers table); update the manifest
  fixture types in `widget/src/types.ts`

## 2. Evaluator: driver scope and free variables

- [ ] 2.1 Red vitest: `evalExpr` evaluates dotted qualified ids
  through a nested driver map alongside `$t`; degree trig and `^`
  unchanged; bare root-driver ids work
- [ ] 2.2 Red vitest: free-variable extraction off the cached parse —
  static / `$t`-only / driver-only / mixed separation; `Member` chains
  collapse to dotted names; `Call` callees never counted; a driver
  named `total` is not found by substring
- [ ] 2.3 Implement both; replace `isAnimated` consumers
  (`tree.ts:operationIsAnimated`, `TreeNode.animated`) with
  free-variable classification (time-driven vs driver-driven vs
  static)

## 3. Loader and driver state

- [ ] 3.1 Red vitest: a non-empty-table document mounts and renders at
  declared defaults (gate inversion — rewrite the stage-3a gate tests
  to the new consumer contract, citing the export delta); an
  expression referencing an undeclared id fails loudly naming it;
  empty-table documents behave exactly as v1
- [ ] 3.2 Red vitest: per-mount driver state — `drivers()` verbatim,
  `driver(id)`, `setDriver` (unknown id loud with known ids listed; no
  range clamp; only referencing operations re-evaluate),
  `onDriverChange` (per-frame coalescing, synchronous on `setDriver`,
  unsubscribe)
- [ ] 3.3 Implement the state store, handle methods, and dirty-driver
  re-evaluation in the render loop

## 4. Instructions: trigger and ramps

- [ ] 4.1 Red vitest: `instructions()` verbatim; `trigger` converts
  design-unit targets to native (scale + integer-dtype rounding
  matching `Driver.native`), ramps linearly from current value over
  duration, whole intermediate values for int dtypes, exact landing;
  last-wins replacement; `done` resolves on landing and on `cancel()`;
  unknown name loud with known qualified names; `dispose()` cancels
- [ ] 4.2 Implement ramps in the animation loop (wall-clock elapsed,
  endpoint-exact)

## 5. Parity under test

- [ ] 5.1 Add a checked-in Python generator producing the parity
  fixture JSON from the spike expression corpus (linear, scaled,
  degree trig, `^`, mixed `$t`+driver, design→native conversions for
  int dtypes) with producer-computed expected values; commit the
  fixture
- [ ] 5.2 Red vitest: the fixture runs against the SHIPPED evaluator
  module; verify the suite fails with the `^` rewrite disabled; then
  green. Note in `spike/expressions/FINDINGS.md` that seam 7 is closed
  and `parity_harness.js` is superseded as the parity authority

## 6. Records and validation

- [ ] 6.1 Revise ADR-022: single evaluator, defect fixed, parity
  enforced by the fixture, driver-map evaluation in scope; update its
  status/date discipline and the ADR index if its status line changes
- [ ] 6.2 Full validation: widget vitest suite; full framework pytest
  suite (zero regressions from the producer change); v8-engine 33/33
  via `solid test` (driverless documents byte-identical); both spike
  runners exit 0
- [ ] 6.3 Visual sanity check (evidence, not deliverable): serve the
  spike machine's document, drive `setDriver` and
  `trigger('x_axis.Home')` from the console, confirm motion and
  record the observation in the cycle notes
- [ ] 6.4 Update `docs/architecture.md` (viewer driving API, gate
  inversion, instructions table, parity fixture) and ADR-056
  (implementation status; open questions: viewer evaluation resolved;
  UI chrome and G-code remain); archive the change and sync baseline
  specs
