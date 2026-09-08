# Implementation preflight findings

These are coordinator checks during implementation, not the independent
post-implementation adversarial review required by the ratified change.
They do not authorize synchronization, ADR promotion or archival.

## Source generation (WP1)

The implementer addressed these checks in the WP1 handoff:

- Project-only import interception must leave external custom import finders
  in their ordinary resolution path.
- Census cost must include canonical-path resolution, not count only explicit
  stat calls while repeating hidden filesystem work for every closure entry.
- A boundary must make one fresh distinct-path observation batch rather than
  separately checking overlapping generation and phase sets.
- Failed phase entry must restore context state; foreign binary digests must
  not retain every source's complete bytes unnecessarily.
- Consumed foreign-source identity must survive phase exit. Replacement
  between assembly and publication cannot be blessed by a new census over
  an already-assembled tree. Constructor-time STEP reads need the same
  pre/post read and retained-generation identity protection.
- Evidence must distinguish missing-new-API failures from a demonstrated
  legacy stale-bytecode or source-race failure.

The coordinator rerun of `tests/test_source_generation.py` and
`tests/test_source_census.py` passed all 21 tests in 3.04 seconds. The additional
JSCAD atomic-publication correction has deterministic red/green proof, not a
real CLI integration run. The broad integrated regression remains pending
other packages' shared publication/naming changes; see [WP1](wp1.md).

## Flexible working set (WP5)

The initial private-keyword expansion of public `base_mesh()` was removed.
The coordinator independently ran the 14 dedicated tests after that correction:
14 passed, one existing render/driver deprecation warning, 3.69 seconds.
Command, from the bench:

```sh
env PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 /home/asa/devel/libresolid-studio/.venv/bin/python -m pytest tests/test_flexible_cache_performance.py -q
```

Follow-up corrected: custom public `base_mesh` overrides remain honored and
uncached because the stock spec cannot certify arbitrary override geometry.
A 128-distinct-identity trajectory proves the default 64-entry bound and
recomputation on revisit. The combined coordinator rerun of flexible and
broad-phase dedicated tests passed 24 tests and 24 subtests, with one existing
warning, in 6.08 seconds. Task 6.2 is now verified.

## Adaptive broad phase (WP6)

The first local review requested explicit Z-separated scaling, independent
exhaustive overlap checks, broader randomized/rotated/permuted cases, axis tie
coverage and bounded-buffer/streaming proof. The implementer added these checks
and discards buffered pairs before streaming the legacy sweep. The coordinator
rerun above passed. Current real-project bounds remain explicitly pending WP10,
so task 7.2 is not yet marked complete.

## Exact placement retention (WP8)

The coordinator independently verified all 10 dedicated tests (2.80 seconds).
The first RSS probe rose despite bounded cache entries. The replacement probe
removes instrumentation retention and reports RSS after explicit garbage
collection, alongside the original observation; neither result establishes a
normal-runtime allocator plateau. See [WP8](wp8.md) for commands and limits.

## Evidence integrity

All implementation packages have now handed off. Additional coordinator runs:

- WP3 persistent facts, browser staging and lower mesh caches: 60 passed,
  one optional viewer-bundle skip, seven subtests, 7.79 seconds.
- WP4 deduplication plus source-generation/census: 31 passed, 4.20 seconds.
  This includes the correction for missing initial foreign sources entering
  the existing startup/reload error path instead of escaping its handler.
- WP7 naming and publication-order fixtures: 16 passed, ten subtests,
  1.33 seconds.

The independent reviewer separately records findings in
[adversarial-review.md](adversarial-review.md). AR-01 concerns historical exact
test setup clearing a shape cache without its paired identity registry. Its
test-only correction has deterministic red/green proof and independent green
re-review (28 tests, 12 subtests); no production change was needed. A passing
retry alone was not treated as resolution of that isolation defect.

The first full candidate suite subsequently completed with seven failures,
1,749 passes, 16 skips, 48 warnings and 353 passing subtests in 269.04 seconds.
The original failed run is preserved as `candidate-framework.xml` and `.log`.
SCAD/build-directory, snapshot-lock and adapter artifact-state failures are
assigned to Sol High for deterministic diagnosis and correction. The combined
validation and measurement gates remain open.

All 18 historical audit files still match the planning inventory after the
above implementation work. The measured planning baseline and its wrapper
remain immutable; post-change measurements require a new wrapper and a
cryptographic identity of the actual uncommitted candidate.
