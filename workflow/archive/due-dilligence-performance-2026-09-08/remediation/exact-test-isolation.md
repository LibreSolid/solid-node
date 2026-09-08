# Exact cache test isolation correction

## Finding

The independent review's [AR-01 finding](adversarial-review.md#ar-01----stale-exact-shape-side-identities-make-the-test-suite-flaky)
identified a historical test-isolation defect in the three fixtures at
`tests/test_tessellation_precision.py:151`,
`tests/test_tessellation_precision.py:466`, and
`tests/test_exact_geometry.py:175`. They cleared `_shape_cache` but left the
id-keyed `_shape_keys` registry and its bounds and placement dependants alive.
The review's same-interpreter probe deterministically left one retained shape,
16 shape keys (15 stale), and 11 placements; a later wrong-volume symptom
additionally depended on CPython id reuse.

This is not a WP8 placement-LRU defect: planning head `4bcf4cb5` already had
the paired cache invariant and the incomplete test cleanup, while production
`exact._evict()` already removes paired entries coherently.

## Correction

`tests/exact_test_support.py` supplies a test-only
`clear_exact_shape_caches()` helper. It clears `_shape_keys`, `_bounds_cache`,
and `_placement_cache` while fixtures still own any shape references, then
clears `_shape_cache`. The three affected setup methods use that helper.
No production API or placement-cache policy changed.

`tests/test_exact_test_isolation.py` is the deterministic regression: it
populates all four caches, resets them, proves every side registry empty, and
proves a held formerly cached shape is again classified and placed as uncached
raw geometry.

## Evidence

The red proof is recorded in [exact-test-isolation-red.log](exact-test-isolation-red.log).
The focused green proof and two fresh ordered 306-pass repetitions are in
[exact-test-isolation-green.log](exact-test-isolation-green.log). Root's WP4
tests may have run concurrently; this correction makes no timing or causation
claim from that concurrency.
