# ADR-028: Cached Base Meshes and Single-Matrix World Composition for `.mesh`

**Status:** Accepted
**Date:** 2026-07-18
**Depends on:**
- [ADR-006: Mtime-Based STL Caching Strategy](./ADR-006-mtime-based-stl-caching-strategy.md)
- [ADR-023: Kinematic Operations Model and Driver-Tagged Idempotent Renders](./ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

**Related to:**
- [ADR-027: Absolute World-Matrix Composition for Viewer Transforms](../VIEWER-WEB/ADR-027-absolute-matrix-composition-for-viewer-transforms.md)
- [ADR-029: Manifold Cache and AABB Broad-Phase for Intersection Assertions](../TEST-FRAMEWORK/ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)

*Characterization ADR: the implementation landed in solid-node (branch
`perf-cache`, commit `1c92147`, merged `0745951`) ahead of this record,
driven by `docs/performance-improvement.md` fix 1; this ADR characterizes
the decision after the fact.*

## Context and Problem Statement

`AbstractBaseNode.mesh` is the world-coordinate truth every spatial
assertion consumes (ADR-009/025) and the semantics the viewer mirrors
(ADR-023/027). Its original implementation paid full price on every
access: `trimesh.load(self.stl_file)` from disk, then one full-vertex
`apply_transform` pass **per operation** while walking node → ancestors.

Measured on the v8-engine benchmark (53 STLs, 113 MB): one STL load costs
100 ms–1.05 s (660k-face camshaft), and each per-operation pass ~45 ms at
that size. A test suite reads `.mesh` thousands of times —
`assertNoPairwiseIntersections` is O(leaves²) and `@testing_steps(N)`
multiplies everything by N — so almost all of the suite's wall time was
redundant recomputation of identical intermediate products.

Two facts make caching subtle here:

- The **base geometry** is immutable per built STL, but callers mutate the
  returned mesh (trimesh transforms apply in place).
- The **placement** is not stable: operation values can be solid2 animated
  expressions that change with the keyframe, and `node.operations` is
  mutated in place by design (assembly re-renders per ADR-023; the ADR-025
  perturbation assertions insert an operation and remove it in a
  `finally`).

## Decision Drivers

- **Amortize the immutable part, never the volatile part.** Disk load and
  STL parsing are pure functions of the built artifact; placement is not.
- **Reuse ADR-006's invalidation currency.** The framework already defines
  artifact freshness by mtime; the cache must follow the same signal so a
  rebuilt STL is picked up with no new invalidation concept.
- **One placement semantics across consumers.** ADR-027 fixed the viewer to
  absolute world-matrix composition; the Python side should compute the
  same fold rather than an equivalent-but-different per-pass walk.
- **Semantic no-op.** `.mesh` results must be bit-for-bit equivalent in
  verdict terms; this is a performance fix, not a behavior change.

## Considered Options

1. **Cache nothing** — the shipped prior design.
2. **Cache the final world-placed mesh** — invalid, since placement changes
   with keyframes and in-place operation mutation.
3. **Cache the immutable base mesh; recompose placement absolutely on
   every access** (chosen).

## Decision Outcome

Chosen: **base-mesh cache + fresh single-matrix composition** (solid-node
commit `1c92147`, "Cache loaded meshes; compose operations into one world
matrix").

- `_base_mesh_cache`, module-level, keyed `(stl_file, mtime)` — ADR-006's
  freshness signal. On a miss, any stale entry for the same path (old
  mtime) is evicted first, so a rebuild loop does not accumulate one cached
  mesh per rebuild. The cached object is the shared immutable base;
  `_cached_base_mesh()` documents that mutating callers must `.copy()`.
- `Rotation.matrix()` / `Translation.matrix()` (a fourth consumer surface
  on the ADR-023 operation objects): the operation's 4×4 homogeneous
  matrix, resolving animated values through `as_number()` **at access
  time**, never cached.
- `_compose_world_matrix(node)`: folds the node's own operations (list
  order) then each ancestor's — exactly the order the old while-loop
  applied them — premultiplying each operation's matrix so later operations
  are outermost, mirroring ADR-027's `composeOperations`. Computed fresh on
  **every** call, deliberately uncached: a cached matrix would silently
  miss keyframe changes and the perturbation assertions' in-place
  operation injection.
- `AbstractBaseNode.mesh` becomes: copy of the cached base mesh, one
  `apply_transform` of the composed matrix.

## Pros and Cons of the Options

### Cache nothing (rejected)

- Good: trivially correct.
- Bad: 100 ms–1 s of disk load per `.mesh` access plus one vertex pass per
  operation in the chain; measured 2.3× suite speedup left on the table
  from this fix alone, before the ADR-029 fixes stack on top.

### Cache the world-placed mesh (rejected)

- Good: would amortize everything.
- Bad: placement is volatile by design (keyframes, driver sweeps,
  perturbation injection); any such cache either misses those changes
  (wrong verdicts) or needs an invalidation protocol tracking every
  `operations` mutation — far more surface than the problem warrants.

### Cache base mesh, recompose placement absolutely (chosen)

- Good: caches exactly the immutable object; the volatile part is
  recomputed from declared state on every access — the same
  "recompute absolutely, never track mutations" shape as ADR-023's
  driver sweep and ADR-027's viewer recomposition.
- Good: mtime keying inherits ADR-006 invalidation; stale-entry eviction
  bounds the cache at one entry per file.
- Good: single composed matrix replaces N per-operation vertex passes.
- Bad: a module-level cache holds every distinct STL's mesh for the
  process lifetime (bounded by project size; acceptable for suite runs).
- Bad: callers get a copy per access — correct, but the copy itself has a
  cost; ADR-029's fast path avoids even that for assertion booleans.

## Consequences

- **`.mesh` semantics are unchanged** — same world pose, own-ops-first then
  ancestors, later operations outermost — but the disk load happens once
  per `(stl_file, mtime)` and placement is one transform pass. Fix 1 alone
  measured 2.3× on the v8-engine pairwise workload.
- **Operations now have four consumer surfaces**: `.scad()`, `.mesh()`,
  `.serialized`, and `.matrix()`. A new operation type must implement all
  four (plus `.reversed`) or a runtime silently diverges — this extends
  ADR-023's parity obligation.
- **Python and viewer now share the composition idea** (ADR-027): both fold
  the operation chain into one premultiplied world matrix from scratch each
  time.
- **ADR-029 builds directly on this**: its Manifold cache is filled from
  `_cached_base_mesh` (no second disk read) and its broad-phase and lazy
  placement consume `_compose_world_matrix`.
- **Verification**: `tests/test_node_mesh_cache.py` (TDD'd red-first) pins
  cache hits/eviction, copy semantics, keyframe freshness, and equivalence
  of composed-matrix placement with the old per-operation walk.

## References

- `solid_node/node/base.py` — `_base_mesh_cache`,
  `_cached_base_mesh`, `_compose_world_matrix`, the rewritten `mesh`
  property
- `solid_node/node/operations.py` — `Rotation.matrix()`,
  `Translation.matrix()`
- `tests/test_node_mesh_cache.py`
- `docs/performance-improvement.md` — measurements, fix 1, spike
  and landed-code benchmarks
- Commit `1c92147` (fix 1), merge `0745951`
