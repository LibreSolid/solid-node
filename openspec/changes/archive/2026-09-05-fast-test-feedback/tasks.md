## 1. Defer the exact stack out of the test framework

- [x] 1.1 Red: add a test asserting that `import solid_node.test` in a fresh
      interpreter leaves `cadquery` absent from `sys.modules`, alongside the
      existing loader import-cost tests in
      `tests/test_lazy_test_framework.py`. Confirm it fails today.
- [x] 1.2 Red: add a test asserting a faceted-only project's `solid test` run
      completes with the same results and without importing `cadquery`,
      using an existing faceted meta fixture.
- [x] 1.3 Red: add a test asserting an exact comparison still imports the
      stack and returns today's verdict, and one asserting a name patched on
      `solid_node.test` before any exact comparison is the object the exact
      path uses, and one asserting the same after a comparison has already
      resolved the name.
- [x] 1.4 Replace the module-scope `from solid_node.exact import (...)` in
      `solid_node/test.py` with module-scope deferred callables that import
      `solid_node.exact` on first call, rebind the global unless it has been
      patched, and call through. Turn 1.1-1.3 green without touching any of
      the five call sites.
- [x] 1.5 Measure and record: `import solid_node.test` wall time before and
      after, and the framework suite's total wall time before and after.
      MEASURED: import 2.84 s -> 0.79 s; framework suite 269.2 s -> 200.5 s
      (1209 passed). Three `SimulationBrokenExport` tests re-pointed: they
      read a broken exact stack through `solid_node.simulation.ScenarioTest`,
      a chain this change removes, so the guard now springs on first USE of a
      kernel name on `solid_node.test`.

## 2. Cache exact placements

- [x] 2.1 Red: add a test asserting the same `(shape, matrix)` placement is
      constructed once and reused, and that a different matrix constructs a
      new placement.
- [x] 2.2 Red: add a test asserting a shape rebuilt under a new
      `(brep_file, mtime)` identity is never served a placement built from
      the old identity.
- [x] 2.3 Implement the placement and bounding-box cache in
      `solid_node/exact.py` beside `_shape_cache`, keyed on the shape cache
      key and the matrix bytes, skipping shapes with no file identity.
      NOTE: the key is looked up by `id(shape)` through `_shape_keys`, which
      is safe ONLY because `_shape_cache` holds the shape alive for exactly
      as long as the entry lives. A `cq.Shape` cannot be the key itself:
      `Shape.__eq__` is `isSame()`, which ignores location, so a shape and a
      differently placed copy compare equal.
- [x] 2.4 Turn 2.1-2.3 green and confirm `tests/test_exact_geometry.py` and
      the exact meta tests still pass unchanged.

## 3. Memoize intersection verdicts

- [x] 3.1 Red: add tests for each spec scenario — repeated comparison served
      from cache with no boolean run; a moved pair recomputed; a pair moved
      together by one rigid transform served from cache; a rebuilt part
      invalidating its entries; a `.mesh`-only node never cached.
- [x] 3.2 Red: add a test asserting flush contact keeps its non-empty,
      exactly-0.0 mm³ verdict through the cache and still reports the foul at
      the strict `volume_epsilon=0` default (guarding ADR-025/ADR-029).
- [x] 3.3 Red: add a test asserting a faceted entry never serves an exact
      comparison or the reverse.
- [x] 3.4 Implement the memo in `_intersection_stats` and
      `_placed_intersection`: key on both geometry identities, the
      evaluation path, and the exact bytes of `inv(M1) @ M2`; bounded by
      insertion order; entries evicted when a geometry identity changes, on
      the same discipline as the existing mesh and Manifold caches.
- [x] 3.5 Turn 3.1-3.4 green.

## 4. Prove the numbers and close the open questions

- [x] 4.1 Instrument a counted run and record the EXACT-BYTE hit rate on the
      v8-engine suite. If it falls materially short of the spike's rounded
      54%, stop and return the finding to the pilot rather than loosening
      the key.
      MEASURED: 21% (6398 of 30227 keyed evaluations). It DOES fall short,
      and the finding is returned to the pilot unloosened: the spike's 54%
      keyed on part names and ignored that a flexible part's geometry
      changes with the instant, so it counted comparisons that are not the
      same question. The key stays exact.
- [x] 4.2 Answer the design's second open question from the same counters:
      whether `assertNoSolidInterference`'s candidate sweep benefits from the
      memo or already visits each pair once per instant.
      ANSWERED: `_placed_intersection` is called ZERO times by the v8 suite.
      That project asserts through `assertNotIntersecting` and the
      deprecated pairwise sweep, never `assertNoSolidInterference`, so the
      question is unanswered BY THIS PROJECT rather than settled. The memo
      is wired into that path and unit-tested; no project measurement
      exercises it.
- [x] 4.3 Re-run the full v8-engine suite and record wall time before and
      after, with all tests still passing and identical verdicts.
      MEASURED: 1687.0 s -> 1622.8 s (4%), all tests passing, exit 0,
      verdicts identical. The proposal predicted the memo alone was worth
      1108 s; it is worth 64 s, for the reason 4.1 records. 1499 s of the
      remainder is 6120 comparisons involving the 16 flexible ValveSpring
      leaves, uncacheable by construction: ~50 ms evaluating the spring and
      ~380 ms in the exact kernel returning EMPTY on a pair the broad phase
      cannot cull. Returned to the pilot with the cycle's real merits; see
      spike/interference/FINDINGS.md Finding 5 and Finding 6.
- [x] 4.4 Re-run the full framework suite (`pytest tests`) and record wall
      time before and after, all green.
      MEASURED: 269.2 s -> 179.1 s (33%), 1224 passed — 18 more tests than
      the 1206 baseline, the 15 added by this cycle plus 3 re-pointed. This
      supersedes the intermediate 200.5 s / 1209 recorded in 1.5, taken
      before groups 2 and 3 were finished.

## 5. Record the result

- [x] 5.1 Update `docs/performance-improvement.md` with a section for this
      cycle: the measured costs, what changed, what was measured after, and
      the two rejected options (triangle mid-phase, GPU) with their numbers.
      Added "Cycle `fast-test-feedback`", including the deferred mesh-default
      option the measurements surfaced.
- [x] 5.2 Extract ADRs for the decisions that proved architectural — the
      relative-placement memo key and its exact-byte comparison, and the
      test framework's deferral of the exact stack — and update
      `docs/architecture.md` and the ADR index if the synthesis changed.
      ADR-069 (BUILD, extends 059) records the deferred callables and why
      PEP 562 does not reach a module's own call sites. ADR-070
      (TEST-FRAMEWORK, extends 029) records relative placement as the
      identity of an intersection question, and why the key carries no
      tolerance. Both sections of `docs/architecture.md` updated and the
      index cross-linked in both directions.
- [x] 5.3 Update `spike/interference/FINDINGS.md` with the measured
      after-numbers, so the spike record states both what it predicted and
      what the implementation actually delivered.
      Finding 5 records what moved and where the remaining cost is.
      Finding 6 records the mesh-path measurement the pilot asked for, and
      closes finding 3's mid-phase for good rather than reopening it.
