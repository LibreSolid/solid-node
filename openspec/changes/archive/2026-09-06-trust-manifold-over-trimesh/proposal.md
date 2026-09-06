## Why

The test framework refuses a solid for spatial assertions when trimesh's
`is_volume` says its STL is not watertight, before the mesh engine is ever
asked and even on runs whose every comparison is decided by the exact
kernel. That gate is stricter than the engine it guards: OpenSCAD 2021.01
exports snap-fit parts with edges shared by four faces, build123d exports
walls with T-junctions between tessellated faces, and vendor STEP files
tessellate with degenerate or unshared triangles — trimesh calls all of them
non-watertight, and `manifold3d` ingests them with `NoError` and the same
volumes. Three of the shop's seed projects (snappy-reprap, fender-bender,
openvmp) could not use `assertNotIntersecting`, `assertBlockedBeyond`,
`assertNoSolidInterference` or `assertAssemblySupported` on the design's
own parts and each wrote a private Manifold or OCCT engine instead. On top
of that, the exact leaf's STL export keeps the degenerate triangles OCCT's
tessellation emits, while the fused-solid export already strips them; four
of openvmp's vendor pieces close on that alone.

## What Changes

- The spatial assertions' admissibility verdict for a faceted comparison is
  the mesh engine's own: a Manifold is built from the cached base mesh and
  its `status()` decides. A mesh Manifold refuses raises a `ValueError`
  naming the STL (or, for a flexible leaf, the node) and the engine's status,
  with trimesh's watertightness as a diagnostic. A mesh trimesh
  calls non-watertight but Manifold accepts is compared like any other.
- Selecting a solid no longer validates its mesh. The bounds half of the
  per-STL cache reads only the bounding box, so an exact-kernel run whose
  comparisons all route exact never validates a mesh at all, and
  `assertNoSolidInterference`'s broad phase never rejects a solid it will
  not compare faceted.
- The exact leaf's STL export drops degenerate triangles, as the fused
  solid's export already does; the helper's default flips and the flag goes.
- **BREAKING** for tests that relied on the eager gate: a non-watertight STL
  on a solid no comparison reads faceted no longer raises. Nothing in the
  framework's own suite relied on it beyond the pinned scenario, which is
  rewritten.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `test-framework`: the "Accelerated intersection evaluation" requirement's
  per-STL cache split — validation moves from the bounds half (trimesh,
  eager, every selected solid) to the Manifold half (engine status, at first
  faceted read), and the non-watertight scenario becomes the engine's
  refusal.
- `exact-geometry`: an exact leaf's STL artifact carries no degenerate
  triangles.

## Impact

- `solid_node/test.py`: `_cached_local_bounds` (gate removed),
  `_cached_manifold` and `_flexible_manifold` (status check added).
- `solid_node/exact.py` `write_stl` and its two callers in
  `solid_node/node/exact_leaf.py` and `solid_node/node/fusion.py`.
- `tests/test_manifold_cache.py` (the pinned non-watertight scenario) and
  new tests for the accepted-though-non-watertight mesh, the exact run that
  never validates, and the exact leaf export.
- Originating projects: snappy-reprap (`simulation/test_snappy_reprap.py`
  `shared()`), fender-bender (`simulation/contracts.py`, the unverified
  support contract), openvmp (`simulation/don1/clearance.py`, the
  render-time tessellation in `parts.py`). Each drops its workaround once
  this integrates; that is project work, recorded in the shop's
  `docs/warts.md` plan.
- `StlNode`'s import-time `require_watertight` gate (ADR-054) is untouched:
  it judges a committed mesh at materialization with an explicit opt-out,
  a different question from whether a built solid can be compared.
