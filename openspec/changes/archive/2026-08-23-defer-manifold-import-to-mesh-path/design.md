## Context

`solid_node/test.py` holds every geometric assertion. It reaches geometry by two
engines: the OCCT boundary-representation kernel through `solid_node.exact`, and
the `manifold3d` mesh engine for faceted geometry. ADR-029 introduced the
per-`(stl_file, mtime)` Manifold cache and the AABB broad phase; ADR-044/045 later
added exact geometry, and ADR-040 made `assertNoSolidInterference` route a pair of
exact solids straight to the kernel. The routing was done pair by pair, inside
`_placed_intersection`. The *placement* step ahead of it was never revisited, so
`_solid_geometry` still calls `_cached_manifold(solid.stl_file)` for every
selected solid regardless of what will decide its comparisons.

Two consequences, both reproduced at this cycle's base:

1. `from manifold3d import Manifold, Mesh` at `solid_node/test.py:13` makes the
   whole assertion module unimportable when the wheel is absent.
2. Even with `manifold3d` importable but unusable, `assertNoSolidInterference`
   over an all-exact assembly fails inside `_cached_manifold`, because a Manifold
   is constructed for every solid before the exact shortcut is reached.

ADR-046 already settled the architectural question for the OpenSCAD binary:
a heavy external dependency belongs to the operations that invoke it, resolved
once per process, with one actionable error. The `openscad-dependency`
capability's headline guarantee — an all-exact project builds, tests and
publishes without it — is precisely the guarantee `manifold3d` breaks.

The constraint that surfaced this is the `browser-engine` spike: `manifold3d`
publishes no WebAssembly wheel, so in a browser runtime it is not installable at
all. That is evidence for the requirement, not the requirement itself; the
requirement is that a dependency should be required by the paths that use it.

## Goals / Non-Goals

**Goals:**

- An all-exact project runs its full assertion surface —
  `assertNoSolidInterference`, `assertNotIntersecting`, `assertIntersecting`,
  the intersection-volume assertions, the perturbation assertions, `assertJoined`
  and `assertNoDisconnectedSolids` — with no `manifold3d` in the environment.
- A path that genuinely needs the mesh engine fails with one actionable error
  naming `manifold3d`, what needed it, and why, at the point of use.
- Byte-for-byte behavioral parity when `manifold3d` is present: same verdicts,
  same messages, same broad-phase candidate sets, same cache hit counts.

**Non-Goals:**

- Making `assertAssemblySupported` work without the mesh engine. ADR-049's
  contact extraction is faceted by design, for exact solids too; changing that is
  a physics decision, not a dependency one.
- Making `assertInside`, `assertClose` or `assertFar` work without `rtree`
  (spike finding 6) — a different dependency with a different contract.
- Substituting a pure-Python mesh boolean, vendoring a fallback engine, or
  degrading a faceted verdict when the engine is missing. A missing engine means
  the operation cannot be performed, never that it silently returns a weaker
  answer.
- Any packaging or dependency-declaration change.
- Removing the STL read from the exact path. Local bounds still come from the
  cached base mesh; see Decision 3.

## Decisions

### Decision 1 — Conditional dependency at the point of use, not a lazy import alone

A bare lazy `import manifold3d` inside `_cached_manifold` would fix the import
crash but report a raw `ModuleNotFoundError` from framework internals. Instead a
new `solid_node/mesh_engine.py` mirrors `solid_node/openscad.py` exactly: one
`@lru_cache`d resolver, one `MeshEngineUnavailable(RuntimeError)` carrying
`needed_by` and `reason`, and one `require_mesh_engine(needed_by, reason)`
returning the `(Manifold, Mesh)` handles. Every construction site goes through it.

*Alternatives considered.* (a) Module-level `try/except ImportError` binding a
sentinel that raises on use — hides the point of failure inside numpy/Manifold
call sites and produces a different message per site. (b) A module-level
`__getattr__` shim — the same, plus surprising import semantics. (c) Leaving the
raw `ModuleNotFoundError` — no `needed_by`, no remedy, and diverges from the
established ADR-046 contract for exactly this class of problem.

### Decision 2 — Defer only the Manifold construction; keep bounds and watertightness eager

`_cached_manifold(stl_file)` today does four things at once: read the mtime, load
the cached base mesh, validate watertightness with a `ValueError` naming the
file, and construct the Manifold. Only the fourth needs `manifold3d`. The change
splits the first three into `_cached_local_bounds(stl_file)` — pure trimesh — and
leaves `_cached_manifold` with its existing signature and `(manifold, bounds)`
return, so the existing test doubles that patch it (`tests/test_manifold_cache.py`,
`tests/test_assembly_supported.py`) keep working unchanged.

`_solid_geometry` then reads bounds from the new cache, and `_place_solid` stores
a deferred placed Manifold instead of an eager one. `_placed_intersection` forces
it only on its faceted branch; the statics phase forces it as it already does.

This keeps the non-watertight-STL diagnostic eager for every selected solid,
exactly as today. Deferring it would have been simpler and would have silently
stopped reporting a bad STL that the broad phase culls out of every pair — a real
loss of diagnostic reach for no benefit.

*Alternatives considered.* (a) Defer the whole `_cached_manifold` call including
the watertightness check — loses the diagnostic described above. (b) Build the
Manifold eagerly but only for solids that are not `exact` — wrong: a mixed
assembly compares an exact solid against a faceted one through the mesh path, so
that exact solid still needs its Manifold. Laziness, not a static predicate, is
what matches the actual routing. (c) Precompute which pairs will route faceted
and build only those Manifolds — the broad phase already emits the pairs; forcing
at use is the same information with no second traversal.

### Decision 3 — Do not change where an exact solid's bounds come from

`_intersection_stats`'s exact branch already derives world bounds from
`shape().BoundingBox()`, and it is tempting to do the same in the assembly
placement so an exact solid touches no STL at all. This change deliberately does
not.

The placement records feed three consumers: the interference broad phase,
`assertAssemblySupported`'s grounded-seed selection, and `_virtual_floor`'s
placement and extent. OCCT's `BoundingBox()` is a conservative box with a gap
tolerance; the tessellated STL bounds are chordally inside a curved exact
surface. Swapping the source would shift the candidate set, the seed set, and the
floor slab — a physics-visible change smuggled in under a dependency fix. Keeping
the STL source means every candidate set, seed, floor and verdict is provably
unchanged, and the whole change reduces to *when* a Manifold is built.

Deriving exact bounds from the kernel remains available as a separate,
independently ratified optimization.

### Decision 4 — `assertAssemblySupported` requires the mesh engine, and says so

Its second phase extracts contact points and normals from meshed intersections
for every body, including a pair of exact solids (ADR-049; `_interface_contacts`
states this explicitly), and `_virtual_floor` builds a `Manifold.cube`. There is
no exact-only path to make available. The requirement therefore states the
dependency rather than hiding it, and the assertion fails with the named error.

Verified during investigation: `tests/meta_project/assembly_supported_exact.py`
is an all-exact assembly whose `assertAssemblySupported` passes today only
because Manifolds are built for it.

### Decision 5 — No packaging change

`manifold3d` stays in `pyproject.toml`'s `dependencies`. Moving it to an optional
extra would give every ordinary `pip install solid-node` a silently
faceted-broken installation, which is the opposite of the conditional-dependency
intent: ADR-046 could omit OpenSCAD from packaging only because it is a binary
that pip never installed in the first place. A host that cannot install the wheel
omits it deliberately — the spike already installs the framework with
`--no-deps` — and this change is what makes that omission survivable.

## Risks / Trade-offs

- **A deferred Manifold changes when an error surfaces on the faceted path.** →
  The construction moves from solid selection to the first comparison that reads
  it. Watertightness — the only diagnostic raised there — is kept eager, so the
  observable error set and its timing are unchanged for every solid the assertion
  selects. Proof obligation: an existing red faceted fixture must fail with the
  identical message.
- **The lazy placed-Manifold object could leak into a code path expecting a real
  Manifold.** → Every consumer is inside `solid_node/test.py` and enumerable:
  `_placed_intersection`, `_statics_body`, `_interface_contacts` via
  `dropped[...][1]` and `lifted[...][1]`, and `_virtual_floor`'s own record. The
  investigation probe confirmed the failure is loud and immediate (an
  unforced record raised at `to_mesh()`), not silent. Proof obligation:
  `tests/test_assembly_supported.py` and the `assembly_supported*` meta fixtures
  must stay green.
- **Caching regression: a lazily forced Manifold could be rebuilt per pair.** →
  Forcing routes through the unchanged `_cached_manifold`, whose
  `(stl_file, mtime)` cache is the single build point.
  `tests/test_manifold_cache.py::test_repeated_assertions_build_the_manifold_once`
  is the existing guard and must stay green.
- **`assertJoined`'s faceted branch calls `trimesh.boolean.union`, whose default
  engine is `manifold3d`.** → Out of this change's reach: trimesh selects and
  reports its own engines. Recorded as an adjacent finding; the new capability
  states the boundary rather than claiming coverage it does not have.
- **The reproduction environment has `manifold3d` installed, so the red-first
  tests must simulate its absence.** → Tests use a subprocess with a `sys.meta_path`
  blocker installed after trimesh is imported (trimesh treats `manifold3d` as one
  optional engine and copes; `solid_node.test` is what does not), which is the
  honest simulation of an environment without the wheel and is how the defect was
  reproduced at base.
