# ADR-029: Manifold Cache and AABB Broad-Phase for Intersection Assertions

**Status:** Accepted
**Date:** 2026-07-18
**Depends on:**
- [ADR-009: Trimesh-Based Mesh Assertions for CAD Testing](./ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md)
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)
- [ADR-028: Cached Base Meshes and Single-Matrix World Composition for `.mesh`](../NODE/ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)

*Characterization ADR: the implementation landed in solid-node (branch
`perf-cache`, commits `e292625` and `d725d23`, merged `0745951`) ahead of
this record, driven by `docs/performance-improvement.md` fixes 2–3; this
ADR characterizes the decisions — including one deviation from the
report's own semantics note — after the fact.*

## Context and Problem Statement

Every intersection-based assertion (`assertNotIntersecting`,
`assertIntersecting`, ADR-025's `assertBlockedBeyond`/`assertFreeWithin`,
and `assertNoPairwiseIntersections`) originally called
`trimesh.boolean.intersection` per check. Each call re-checks
watertightness of **both** meshes, re-converts both to
`manifold3d.Manifold`, runs the exact boolean, and converts the result
back to a trimesh — even when the caller reads only
`is_empty`/`volume`. Measured cost per pair on v8-engine geometry:
220 ms–1.06 s, **even when the result is empty**. The pairwise sweep is
O(leaves²) and `@testing_steps(N)` multiplies by N; the boolean engine
(manifold3d, exact, TBB-multithreaded) was never the bottleneck — the
per-call conversion ritual and the sheer number of invocations were.

Two structural observations unlock the fix:

- The trimesh→Manifold conversion and the watertightness check are pure
  functions of the built STL — cacheable under ADR-006/028's
  `(stl_file, mtime)` key. Placement is a lazy, near-free
  `Manifold.transform()`.
- In a real assembly most leaf pairs are nowhere near each other: a
  conservative world AABB test can prove the intersection empty in
  microseconds without any boolean.

The trap is verdict fidelity. The improvements.md #21 contract
(`volume_epsilon`, ADR-025) depends on a subtle signal: a legitimate flush
abutment reproducibly yields a **non-empty** intersection with **exactly
0.0 mm³** volume — and at the strict `volume_epsilon=0.0` default that
must still be reported as a foul, forcing an explicit epsilon opt-in.

## Decision Drivers

- **Amortize per-STL work to once per suite** (conversion, watertight
  check), leaving only the boolean core per check.
- **Cull provably empty pairs before any boolean** — but only with an
  exact-negative test that can never change a verdict.
- **Preserve ADR-025 verdict semantics bit-for-bit**, including the
  flush-contact non-empty/zero-volume case that `volume_epsilon`'s strict
  default is defined by.
- **Keep the slow path for mesh-only doubles**: unit tests drive the
  assertions with fake nodes exposing only `.mesh`; the fast path must be
  an optimization, not a new node contract.

## Considered Options

1. **Per-call trimesh booleans** — the shipped prior design.
2. **Fast path with the report's literal emptiness folding**
   (`is_empty() or volume() == 0` → empty) — rejected during
   implementation.
3. **Fast path with engine-native emptiness only** (chosen).

## Decision Outcome

Chosen: **shared `_intersection_stats` helper with Manifold cache, AABB
broad-phase, and engine-native emptiness** (solid-node commits `e292625`
fix 2, `d725d23` fix 3).

All intersection-based assertions route through
`_intersection_stats(node1, node2) -> (is_empty, volume)`:

- **Fast path** when both nodes expose `stl_file` (`_fast_geometry`):
  - `_cached_manifold(stl_file)` — module-level cache keyed
    `(stl_file, mtime)`, same stale-eviction as ADR-028, filled from
    ADR-028's `_cached_base_mesh` (no extra disk read). Watertightness is
    validated **once at cache fill** and failure raises a `ValueError`
    naming the STL, instead of an obscure error deep in the boolean
    engine.
  - **Broad-phase (fix 2):** each part's 8 local bounding-box corners are
    transformed by its composed world matrix (`_world_bounds`) — a
    conservative superset of the true world footprint. If the two boxes
    are disjoint (`_boxes_disjoint`), the exact intersection is provably
    empty: return `(True, 0.0)` with no boolean. Applies as skip/pass for
    `assertNotIntersecting`, `assertFreeWithin`,
    `assertNoPairwiseIntersections`, and as fail-fast (same messages) for
    `assertIntersecting` and `assertBlockedBeyond`.
  - **Narrow phase (fix 3):** place the cached Manifolds with lazy
    `.transform(matrix[:3, :4])`, intersect directly (`a ^ b`), read
    `is_empty()` and (only when non-empty) `volume()` off the result — no
    conversion back to trimesh.
- **Fallback** when either node lacks `stl_file` (e.g. the FakeNode
  doubles in `tests/test_assertions.py`): the original
  `trimesh.boolean.intersection` over `.mesh`, unchanged — no caching, no
  culling, identical verdict shape.

**Deviation from the report, flagged for ratification:** the report's
semantics note prescribed folding `volume() == 0` into emptiness. Built
against the real flush fixtures (`tests/meta_project/flush_strict.py`,
`flush_keyed_strict.py`), that folding regresses `VolumeEpsilonMetaTest`:
flush abutments are non-empty with exactly 0.0 mm³ in **both** engines,
and #21's strict default requires that foul to surface. Implemented
instead: `is_empty` is Manifold's own `is_empty()` alone (empirically
identical to trimesh's signal on this framework's geometry); a
`volume_epsilon > 0` comparison is unaffected either way since 0.0 ≤ any
positive epsilon.

## Pros and Cons of the Options

### Per-call trimesh booleans (rejected)

- Good: simplest possible; one code path.
- Bad: pays watertight checks + two conversions + a result round trip per
  check; thousands of redundant full-price cycles per suite (25 s for a
  56-pair × 2-instant workload).

### Fast path with literal zero-volume folding (rejected)

- Good: matches the report's note as written.
- Bad: **silently defeats the strict `volume_epsilon=0` contract** — every
  exact-zero-volume flush sliver would be reported as clear, un-ratifying
  ADR-025's anti-noise design. The spike's verdict-agreement check simply
  never exercised a non-empty/zero-volume case, which is why the report
  missed it.

### Fast path with engine-native emptiness (chosen)

- Good: verdict-identical to the trimesh path on all framework fixtures,
  including flush contacts; the #21 contract survives untouched.
- Good: conversion + watertight checks amortize to once per STL per
  suite; broad-phase culls most pairs in real assemblies (75% in the
  benchmark workload, growing with assembly size since contacts are O(n)
  against O(n²) pairs).
- Good: measured 13× cold-cache / 253× warm-cache on the landed code
  against the real v8-engine workload (spike: 41× without, 288× with
  broad-phase); all verdicts agreed with baseline.
- Bad: two code paths (fast + fallback) to keep verdict-equivalent; the
  fallback is exercised by the unit doubles, the fast path by the meta
  fixtures.
- Bad: watertightness now fails at cache fill rather than inside the
  boolean — a behavior surface change (deliberate: clearer error, earlier).
- Bad: new hard dependency on `manifold3d` in `test.py` (previously
  reached only indirectly as trimesh's boolean engine).

## Consequences

- **Assertion verdicts are unchanged; suite cost collapses** to the
  boolean core on genuinely adjacent pairs — one to two orders of
  magnitude on real suites, making TDD loops with `@testing_steps` sweeps
  interactive again.
- **The strict flush-contact semantics of ADR-025/#21 are load-bearing
  and now have an explicit guard**: any future emptiness-folding
  "simplification" must first re-ratify `VolumeEpsilonMetaTest`'s two
  strict-default tests.
- **`stl_file` is the fast-path capability signal.** Node-like objects
  without it (doubles, hypothetical mesh-only nodes) get the original
  path; anything exposing `stl_file` must have a watertight, built STL
  when spatial assertions run.
- **The fast path composes ADR-028's primitives** (`_cached_base_mesh`,
  `_compose_world_matrix`); the two caches share keying and eviction
  discipline, so ADR-006's mtime currency governs all of it.
- **Verification**: `tests/test_broad_phase_culling.py` (culling is
  exact-negative and message-preserving) and
  `tests/test_manifold_cache.py` (cache fill/eviction, watertight
  validation, verdict equivalence incl. flush fixtures), both TDD'd; plus
  the pre-existing `tests/test_assertions.py` (fallback path) and
  `tests/test_meta.py` end-to-end contracts, all green post-merge.

## References

- `solid_node/test.py` — `_manifold_cache`, `_cached_manifold`,
  `_fast_geometry`, `_world_bounds`, `_boxes_disjoint`,
  `_intersection_stats`, rewritten assertion bodies
- `tests/test_broad_phase_culling.py`,
  `tests/test_manifold_cache.py`
- `docs/performance-improvement.md` — measurements, fixes 2–3,
  the deviation note, spike and landed-code benchmarks
- `spike/mesh_manifold_cache.py` — the spike
- Commits `e292625` (fix 2), `d725d23` (fix 3), merge `0745951`
