# ADR-052: Conditional mesh-engine dependency

**Status:** Accepted

**Date:** 2026-08-23

**Change:** `defer-manifold-import-to-mesh-path`

**Depends on:**
- [ADR-046: Conditional OpenSCAD dependency](../NODE/ADR-046-conditional-openscad-dependency.md)
- [ADR-029: Manifold cache and AABB broad phase](ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)
- [ADR-040: Topmost-rigid assembly integrity](ADR-040-topmost-rigid-assembly-integrity.md)
- [ADR-044: Derived exact-geometry capability](../NODE/ADR-044-derived-exact-geometry-capability.md)
- [ADR-049: Static equilibrium as LP feasibility](ADR-049-static-equilibrium-as-lp-feasibility.md)

## Context

ADR-046 made the OpenSCAD binary conditional on the paths that invoke it, and
the `openscad-dependency` capability states the resulting guarantee: an
all-exact project builds, tests and publishes without it. ADR-044 and ADR-040
then routed exact geometry to the OCCT kernel, pair by pair, inside
`_placed_intersection`.

The placement step ahead of that routing was never revisited. `_solid_geometry`
built one `manifold3d.Manifold` per selected solid before any exact shortcut
could apply, and `solid_node/test.py` imported `manifold3d` at module scope. The
mesh engine therefore reinstated, one layer down and in a second technology, the
blanket dependency ADR-046 had removed — and more widely than the assertion
module alone, because `solid_node/core/loader.py` imports `solid_node.test`, so
`solid_node.cli` reached `manifold3d` transitively for *every* command.

`manifold3d` is a compiled wheel with no WebAssembly build, which is where this
became visible: the `browser-engine` spike found an all-exact fixture keeping 17
contracts green against a fail-by-name stand-in while only its deliberate
faceted marker failed — the assertion logic was already exact-only; the plumbing
was not.

## Decision

`manifold3d` is a conditional dependency, resolved at the operation that uses
it. `solid_node/mesh_engine.py` provides one `lru_cache`d resolver and one
`MeshEngineUnavailable` error carrying what needed the engine, why, and the
remedy — the same shape as `solid_node/openscad.py`.

The per-STL cache is split by what each half needs. A solid's local bounding box
and its watertightness verdict are read from the cached base mesh with no mesh
engine, eagerly, for every selected solid. The Manifold is built at the first
comparison that actually reads it, still exactly once per `(stl_file, mtime)`.
Placement records therefore carry a deferred placed Manifold that only faceted
consumers force.

The requiring set is exactly: any comparison whose pair is not two exact nodes,
and `assertAssemblySupported` for two or more solids.

`assertAssemblySupported` stays in that set deliberately. ADR-049 extracts
contact patches from meshed intersections for every body, exact solids included,
because statics needs a patch's extent and direction rather than Boolean
validity, and the virtual floor is a meshed slab. There is no exact-only route
to offer, so the assertion requires the engine up front and names itself in the
failure instead of failing obscurely inside the equilibrium program.

Bounds keep coming from the cached base mesh for every solid, exact or faceted.
Deriving an exact solid's bounds from `shape().BoundingBox()` would let it skip
its STL entirely, but those same bounds feed the grounded-seed selection and the
virtual floor's placement, so changing their source would move physics results
under cover of a dependency fix. That optimization is left to its own decision.

Packaging is unchanged: `manifold3d` remains a declared runtime dependency. An
environment that cannot install it omits it deliberately.

## Alternatives rejected

- **Lazy `import manifold3d` inside the cache, and nothing more:** fixes the
  import crash but still builds a Manifold for every selected solid, so an
  all-exact assembly still fails — and reports a bare `ModuleNotFoundError` from
  framework internals.
- **Module-level `try/except` binding a sentinel that raises on use:** moves the
  failure into numpy and Manifold call sites, with a different message at each.
- **Move `manifold3d` to an optional extra:** every ordinary `pip install`
  would then produce a silently faceted-broken installation. ADR-046 could omit
  OpenSCAD from packaging only because pip never installed it in the first
  place.
- **Build Manifolds eagerly for non-`exact` solids only:** wrong, because a
  mixed pair compares an exact solid against a faceted one through the mesh
  path, so that exact solid needs its Manifold too. Laziness, not a static
  predicate, is what matches the real routing.
- **Defer the watertightness check along with the Manifold:** would stop
  reporting a non-watertight STL belonging to a solid the broad phase culls out
  of every pair — a loss of diagnostic reach for no benefit, since the check
  needs only trimesh.

## Consequences

- An all-exact project runs `assertNoSolidInterference`, `assertNoDisconnectedSolids`,
  `assertJoined`, and every intersection-volume and perturbation assertion with
  no `manifold3d` installed, and `solid_node.test` imports without resolving it.
- Every CLI command stops requiring the mesh engine transitively through
  `core/loader.py`.
- Faceted behavior, verdicts, messages, broad-phase candidate sets and
  Manifold build counts are unchanged when the engine is present.
- `assertAssemblySupported` remains a requiring path for every multi-solid
  assembly and states it by name.
- The seam that counts Manifold construction moved from a module attribute to
  the resolver, and the seam that reports which solids were selected moved from
  the Manifold cache to the bounds cache. Three existing tests were re-targeted
  accordingly; their assertions are unchanged.
- `trimesh.boolean`'s own engine selection — used by `assertJoined`'s faceted
  union and by faceted fusion rendering — remains outside this contract and
  reports through trimesh. Giving `rtree`, on which `assertInside`,
  `assertClose` and `assertFar` depend, the same conditional treatment is the
  natural follow-on and is deferred.

## Evidence

- `tests/test_mesh_engine_dependency.py` runs the framework in a subprocess
  where `manifold3d` is genuinely unimportable, covering module import without
  resolution, the all-exact interference and connectivity assertions passing,
  and the faceted and gravity-support paths failing by name rather than with an
  import error.
- `tests/test_manifold_cache.py` pins that no Manifold is built for an exact
  assembly — including an overlapping pair that really is compared — that a
  mixed assembly builds one per solid a faceted pair reads and none for a solid
  no faceted pair reads, and that a culled non-watertight solid is still
  reported by name.
- The originating all-exact fixture `tests/meta_project/exact_tight_fit.py`
  went from `0 passed, 1 failed` to `1 passed, 0 failed` under an absent mesh
  engine; full suite 689 → 700 passed with no regression.

## References

- `solid_node/mesh_engine.py`
- `solid_node/test.py`
- OpenSpec archive `defer-manifold-import-to-mesh-path`
- `browser-engine` spike, "Upstream findings for the framework" item 4
