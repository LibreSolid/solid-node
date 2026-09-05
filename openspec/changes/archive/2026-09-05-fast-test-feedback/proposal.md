## Why

A `solid test` run costs far more than the geometry it is asked to decide.
Measured on 2026-09-05 (evidence: `spike/interference/FINDINGS.md`):

- The v8-engine suite takes **1687 s**, and **1670 s of it — 99% — is spent
  inside intersection assertions**. Of the 36 347 calls to the shared
  `(is_empty, volume)` helper, **19 747 (54%) recompute a comparison the same
  run already decided**, worth **1108 s**. The cause is the animation sweep:
  `@testing_steps(73)` recompares an assembly's static structure at full
  price at every instant, though nothing about those pairs has moved.
- Importing `solid_node.test` costs **2.84 s**, of which `solid_node.exact`
  -> cadquery is **1.52 s** (0.32 s of that VTK, pulled in for visualization
  the framework never uses). The framework's own suite spends roughly
  **150 s of its 269 s** paying that import in the 52 `tests/test_meta.py`
  subprocesses, and every project pays 2.8 s on every `solid test` — even a
  project modelling entirely in solid2 that never constructs an exact shape.
- On the exact path, `placed_shape` costs **6-19 ms per solid per call** and
  is recomputed from scratch on every comparison, as is each shape's
  bounding box.

Fixes 1-3 of `docs/performance-improvement.md` made the faceted boolean
cheap (a `manifold3d` intersection of two 660k-face parts is 37 ms warm).
Nothing has yet addressed how often the framework asks for an answer it
already has, or what it loads to answer at all.

## What Changes

- The test framework stops importing the exact-geometry stack at module
  scope. `solid_node.test` reaches `solid_node.exact` on the exact path's
  first use instead, extending the deferral discipline the `cli-startup-cost`
  capability already holds for the loader, the node backends, the simulation
  package and the mesh library. No behaviour changes; an exact comparison
  imports exactly what it imports today, at first use.
- Intersection verdicts are memoized within a run, keyed on the compared
  geometry's identity, the pair's RELATIVE placement, and the evaluation
  path. Emptiness and volume are invariant under a common rigid transform,
  so a repeated key is provably the same verdict — this is a recomputation
  shortcut, never a verdict change.
- Placed exact shapes and exact bounding boxes are cached per
  `(shape, matrix)`, the same way the faceted path already caches its
  Manifolds per `(stl_file, mtime)`.
- No new dependency, no new public API, no assertion signature change, and
  no change to any verdict, message, or epsilon semantics.

Explicitly NOT in scope, and why (measured, in FINDINGS.md): a triangle-level
mid-phase between the AABB broad phase and the boolean (27 ms of numpy work
against a 37 ms boolean — manifold's own BVH already does it in C++), and any
GPU evaluation path (no GPU B-rep kernel exists, manifold dropped its CUDA
backend upstream, and the one GPU-shaped subproblem — a touch/no-touch
predicate — cannot produce the `volume` the assertions contract on).

## Capabilities

### New Capabilities

None. This change adds no capability; it constrains the cost of two that
exist.

### Modified Capabilities

- `test-framework`: the "Accelerated intersection evaluation" requirement
  gains a memoization contract — a repeated (geometry, relative placement,
  path) key SHALL be answered from the run's cache rather than recomputed —
  and an exact-placement caching contract, alongside the per-STL cache it
  already specifies.
- `cli-startup-cost`: the "The test framework is imported by the paths that
  run tests" requirement gains its counterpart — importing the test framework
  SHALL NOT itself import the exact-geometry stack; the exact path imports it
  on first use.

## Impact

- `solid_node/test.py` — the exact-kernel import site (line 22) and the five
  call sites that use it (298, 362-365, 872-876, 1196, 1473-1478), all of
  which already sit inside exact-path-only branches; plus the memoization in
  `_intersection_stats` / `_placed_intersection`.
- `solid_node/exact.py` — a placement/bounds cache beside the existing
  `_shape_cache`.
- `tests/test_lazy_test_framework.py`, `tests/test_broad_phase_culling.py`,
  `tests/test_exact_geometry.py`, `tests/test_meta.py` — new red-first
  coverage; `test_meta.py`'s 52 subprocess cases are also the change's own
  headline beneficiary.
- No dependency, packaging, CLI, viewer, or document-format change.
