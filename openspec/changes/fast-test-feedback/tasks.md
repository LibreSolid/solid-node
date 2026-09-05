## 1. Defer the exact stack out of the test framework

- [ ] 1.1 Red: add a test asserting that `import solid_node.test` in a fresh
      interpreter leaves `cadquery` absent from `sys.modules`, alongside the
      existing loader import-cost tests in
      `tests/test_lazy_test_framework.py`. Confirm it fails today.
- [ ] 1.2 Red: add a test asserting a faceted-only project's `solid test` run
      completes with the same results and without importing `cadquery`,
      using an existing faceted meta fixture.
- [ ] 1.3 Red: add a test asserting an exact comparison still imports the
      stack and returns today's verdict, and one asserting a name patched on
      `solid_node.test` before any exact comparison is the object the exact
      path uses, and one asserting the same after a comparison has already
      resolved the name.
- [ ] 1.4 Replace the module-scope `from solid_node.exact import (...)` in
      `solid_node/test.py` with module-scope deferred callables that import
      `solid_node.exact` on first call, rebind the global unless it has been
      patched, and call through. Turn 1.1-1.3 green without touching any of
      the five call sites.
- [ ] 1.5 Measure and record: `import solid_node.test` wall time before and
      after, and the framework suite's total wall time before and after.

## 2. Cache exact placements

- [ ] 2.1 Red: add a test asserting the same `(shape, matrix)` placement is
      constructed once and reused, and that a different matrix constructs a
      new placement.
- [ ] 2.2 Red: add a test asserting a shape rebuilt under a new
      `(brep_file, mtime)` identity is never served a placement built from
      the old identity.
- [ ] 2.3 Implement the placement and bounding-box cache in
      `solid_node/exact.py` beside `_shape_cache`, keyed on the shape cache
      key and the matrix bytes, skipping shapes with no file identity.
- [ ] 2.4 Turn 2.1-2.3 green and confirm `tests/test_exact_geometry.py` and
      the exact meta tests still pass unchanged.

## 3. Memoize intersection verdicts

- [ ] 3.1 Red: add tests for each spec scenario — repeated comparison served
      from cache with no boolean run; a moved pair recomputed; a pair moved
      together by one rigid transform served from cache; a rebuilt part
      invalidating its entries; a `.mesh`-only node never cached.
- [ ] 3.2 Red: add a test asserting flush contact keeps its non-empty,
      exactly-0.0 mm³ verdict through the cache and still reports the foul at
      the strict `volume_epsilon=0` default (guarding ADR-025/ADR-029).
- [ ] 3.3 Red: add a test asserting a faceted entry never serves an exact
      comparison or the reverse.
- [ ] 3.4 Implement the memo in `_intersection_stats` and
      `_placed_intersection`: key on both geometry identities, the
      evaluation path, and the exact bytes of `inv(M1) @ M2`; bounded by
      insertion order; entries evicted when a geometry identity changes, on
      the same discipline as the existing mesh and Manifold caches.
- [ ] 3.5 Turn 3.1-3.4 green.

## 4. Prove the numbers and close the open questions

- [ ] 4.1 Instrument a counted run and record the EXACT-BYTE hit rate on the
      v8-engine suite. If it falls materially short of the spike's rounded
      54%, stop and return the finding to the pilot rather than loosening
      the key.
- [ ] 4.2 Answer the design's second open question from the same counters:
      whether `assertNoSolidInterference`'s candidate sweep benefits from the
      memo or already visits each pair once per instant.
- [ ] 4.3 Re-run the full v8-engine suite and record wall time before and
      after, with all tests still passing and identical verdicts.
- [ ] 4.4 Re-run the full framework suite (`pytest tests`) and record wall
      time before and after, all green.

## 5. Record the result

- [ ] 5.1 Update `docs/performance-improvement.md` with a section for this
      cycle: the measured costs, what changed, what was measured after, and
      the two rejected options (triangle mid-phase, GPU) with their numbers.
- [ ] 5.2 Extract ADRs for the decisions that proved architectural — the
      relative-placement memo key and its exact-byte comparison, and the
      test framework's deferral of the exact stack — and update
      `docs/architecture.md` and the ADR index if the synthesis changed.
- [ ] 5.3 Update `spike/interference/FINDINGS.md` with the measured
      after-numbers, so the spike record states both what it predicted and
      what the implementation actually delivered.
