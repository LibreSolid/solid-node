## Why

`solid_node/test.py` imports `manifold3d` at module scope and builds one
`manifold3d.Manifold` per selected solid before any exact-kernel shortcut, so a
project whose model is entirely exact cannot run *any* geometric assertion
without the compiled mesh engine — even though every one of its comparisons is
decided by the OCCT boundary-representation kernel and never reads a Manifold.
This is the same blanket-dependency mistake ADR-046 already corrected for the
OpenSCAD binary, and the `openscad-dependency` capability already promises that
"a project whose model is entirely exact under the `exact-geometry` capability
SHALL build, test, and publish" without it. `manifold3d` quietly reinstates the
blanket requirement one layer down.

Originating evidence: the `browser-engine` spike,
`openspec/changes/prove-solid-node-runs-in-browser/design.md` "Upstream findings
for the framework" item 4, and `evidence/fixture-host-verification.md` (run F and
"Framework findings" item 6). Its all-exact rail-slide fixture keeps 17 contracts
green against a fail-by-name `manifold3d` stand-in and loses only its deliberate
faceted marker — proving the assertion *logic* is already exact-only, while the
*plumbing* is not. `manifold3d` ships no WebAssembly wheel, so on that surface
the dependency is not merely inconvenient but unavailable.

Both layers reproduce at this cycle's base (`0fbaaf84`):

```
# manifold3d absent from the interpreter: the whole module dies
  File ".../solid_node/test.py", line 13, in <module>
    from manifold3d import Manifold, Mesh
ModuleNotFoundError: No module named 'manifold3d'

# manifold3d importable but unusable (the spike's fail-by-name stand-in),
# all-exact assembly, tests/meta_project/exact_tight_fit.py:
  File ".../solid_node/test.py", line 1073, in assertNoSolidInterference
    solids = _placed_assembly_solids(node)
  File ".../solid_node/test.py", line 180, in _placed_assembly_solids
    manifold, local_bounds, shape = _solid_geometry(solid)
  File ".../solid_node/test.py", line 156, in _solid_geometry
    manifold, local_bounds = _cached_manifold(solid.stl_file)
  File ".../solid_node/test.py", line 67, in _cached_manifold
    manifold = Manifold(mesh=Mesh(
RuntimeError: Mesh is unavailable: this operation needs the compiled
dependency 'manifold3d', which is not installed

Ran 1 tests in 0.12 seconds: 0 passed, 1 failed
```

The spike's stub masked the first layer by making `manifold3d` importable. In a
real environment without the wheel, `import solid_node.test` fails outright, so
`assertNotIntersecting`, `assertJoined` and `assertNoDisconnectedSolids` — all of
which already have complete exact paths — are lost too.

## What Changes

- Introduce `manifold3d` as a **conditional dependency of the faceted mesh
  path**, on the ADR-046 model: resolved once per process at the operation that
  uses it, with one actionable error naming what needed it and why, instead of
  an import-time hard requirement. New module `solid_node/mesh_engine.py`,
  mirroring `solid_node/openscad.py`.
- Build the cached `manifold3d.Manifold` for a selected solid only when a
  comparison actually routes faceted. `assertNoSolidInterference` over an
  all-exact assembly performs no mesh-engine work at all.
- Keep every per-solid check that does *not* need the mesh engine eager and
  unchanged: local bounds and the watertightness validation that raises a
  `ValueError` naming a non-watertight STL both come from the already-cached
  trimesh base mesh, so no diagnostic is deferred or lost.
- Keep the broad phase's bounds source unchanged (the STL's cached base mesh),
  so no candidate set, verdict, support seed, or virtual floor moves.
- State plainly that `assertAssemblySupported` still requires the mesh engine for
  every multi-solid assembly, exact or not: ADR-049 extracts contact patches from
  faceted intersections by design. It now fails with the named error instead of
  an import-time `ModuleNotFoundError`.
- No packaging change: `manifold3d` stays a declared runtime dependency in
  `pyproject.toml`. A host that cannot install it — a WebAssembly runtime — omits
  it deliberately, exactly as the spike's `pip install --no-deps` already does.

Not breaking: no assertion signature, verdict, error message for an existing
failure mode, tolerance, or artifact changes. Every path that has `manifold3d`
available behaves identically, including performance on the faceted path (the
Manifold is still built at most once per `(stl_file, mtime)`).

## Capabilities

### New Capabilities

- `mesh-engine-dependency`: `manifold3d` as a conditional dependency — the exact
  operations that require it, the guarantee for operations that do not, and the
  actionable failure contract when it is unavailable.

### Modified Capabilities

- `test-framework`: the *Accelerated intersection evaluation* requirement's
  faceted fast path gains the point at which its Manifold is built (first faceted
  use, not solid selection), while watertightness validation and bounds stay
  eager; the *Whole-assembly solid interference assertion* requirement gains the
  guarantee that an all-exact assembly is verified with no mesh-engine work; the
  *Whole-assembly gravity support assertion* requirement states that its
  frictionless-statics phase is faceted and therefore requires the mesh engine
  even for exact solids.

## Impact

- `solid_node/mesh_engine.py` (new) — one cached resolver and one
  `MeshEngineUnavailable` error, mirroring `solid_node/openscad.py`.
- `solid_node/test.py` — module-scope `from manifold3d import Manifold, Mesh`
  removed; `_cached_manifold` and `_virtual_floor` acquire the engine through the
  resolver; `_solid_geometry` reads bounds and watertightness from a new
  trimesh-only cache; `_place_solid` records a deferred placed Manifold that
  `_placed_intersection` forces only on the faceted branch and the statics phase
  forces as it does today.
- `tests/test_mesh_engine_dependency.py` (new) — red-first proof that the module
  imports and that an all-exact assembly asserts, with `manifold3d` absent, and
  that faceted and gravity-support paths fail naming it.
- `tests/test_manifold_cache.py` — red-first unit proof that no Manifold is built
  for an all-exact assembly; existing `_cached_manifold` stubs keep working.
- `tests/test_meta.py`, `tests/meta_project/` — end-to-end verdict parity for the
  all-exact fixture under an absent mesh engine.
- `docs/` — the conditional dependency stated where the OpenSCAD one is.
- Unaffected: `pyproject.toml`, `requirements.txt`, every assertion signature,
  `solid_node/exact.py`, `solid_node/node/base.py`, the builder, the viewer, and
  the export path.
- Out of scope, recorded as adjacent findings rather than absorbed: `rtree` for
  `assertInside`/`assertClose`/`assertFar` (spike finding 6); `solid_node/cli.py`
  requiring the FastAPI server stack (spike finding 5); `solid_node.exact`
  importing cadquery and OCP unconditionally (the symmetric constraint on a
  faceted-only project); and `trimesh.boolean`'s own engine selection, which
  `assertJoined`'s faceted branch and faceted `FusionNode` rendering rely on and
  which trimesh, not this framework, is entitled to report.
