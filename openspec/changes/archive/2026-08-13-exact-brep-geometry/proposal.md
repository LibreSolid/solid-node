## Why

Every geometric question the framework answers is currently mediated by a
triangle mesh, even when the project's own geometry kernel could answer it
exactly. Curved surfaces tessellate to chords, so two parts that meet at a
nominally exact fit appear to interpenetrate as soon as their facet phases
differ — which is the normal state of an assembly, because assemblies rotate
parts relative to one another.

Reproduction (originating project: `v8-engine`, same failure reachable in
`gearbox`): a d=10 shaft in a d=10 bore. The OCCT Boolean common is empty,
0 mm³ — correct, this is surface contact. Rotate the shaft 7° and the mesh
Boolean reports 0.060 mm³ of interference. `assertNoSolidInterference` admits
no epsilon by design, so that is a failing test on a correct design.

The workarounds this forces have already leaked out of the tests and into the
durable project record, which is where the cost is no longer acceptable:

- `v8-engine/root/piston.py` and `con_rod.py` call
  `result.val().mesh(tolerance=0.001, angularTolerance=0.01)` inside
  `render()` — geometry authoring carrying a tessellation workaround.
- `american-windmill/docs/design.md` lists `mesh_linear_tolerance = 0.050`
  among its master parameters, described as "allowed measurement/tessellation
  loss". A pipeline artifact promoted to a drawing parameter.
- `windmill/docs/design.md` records a `1e-3 mm³` tessellation epsilon to
  absorb `3e-4 mm³` of noise "at coincident seating faces", noting it is
  "test mechanics, not a physical clearance".
- `v8-engine` threads `volume_epsilon=1e-6` through roughly a dozen assertion
  call sites.

The kernel that can answer these questions exactly is already installed:
`cadquery==2.5.*` is a hard dependency, and every substantial project in the
catalogue (`v8-engine`, `gearbox`, `american-windmill`, `guitar`,
`dutch-windmill`, `windmill`) is built entirely from `CadQueryNode` leaves.
The exact path costs about 2× the mesh path — measured on the full
`v8-engine` at one instant: 119 placed solids, 449 candidate pairs after the
existing AABB broad phase, 6.15 s via Manifold against 12.2 s via OCCT, with
identical verdicts and no kernel failures. The B-rep artifact is *cheaper* to
cache than the STL beside it: 4 ms write / 2 ms read / 165 KiB, against
112 ms / 9 ms / 469 KiB for the same part's STL.

ADR-004 accepted "OpenSCAD's CSG limitations prevent using advanced
NURBS/BREP features from CadQuery" as a known cost of the universal-target
design. This change is that cost coming due.

## What Changes

- **New**: a read-only `exact` property on every node. For a leaf it is
  determined by adapter type; for an internal node it is true when every child
  is exact. Reading it on an internal node before its children are linked
  raises, because the empty-children default would answer vacuously true.
- **New**: `shape()` on exact nodes, returning the node's own geometry as an
  OCCT solid in its local frame — implemented by `CadQueryNode`, and by
  `FusionNode` as the OCCT fuse of its children's shapes.
- **New**: a `.brep` build artifact written beside the `.stl` for every exact
  rigid node, under the same basename and the same mtime-equality caching
  rule. It is private to the build: no viewer or export document references
  it.
- **Modified**: a `FusionNode` whose subtree is exact produces its STL by
  tessellating its own fuse, synchronously, instead of launching an OpenSCAD
  subprocess over imported STLs. A fusion with any non-exact descendant is
  unchanged.
- **Modified**: every assertion that asks about intersection *volume* routes
  through the shared helper and uses exact Boolean intersection when both
  compared nodes are exact — `assertNotIntersecting`, `assertIntersecting`,
  `assertNoSolidInterference`, `assertBlockedBeyond`, `assertFreeWithin`, the
  deprecated pairwise sweep, and (newly routed through that helper)
  `assertIntersectVolumeAbove` / `assertIntersectVolumeBelow`. Non-exact pairs
  keep the existing Manifold path with unchanged verdicts.
- **Modified**: `assertJoined` requires the fuse of the two shapes to yield one
  solid; `assertNoDisconnectedSolids` counts solids in the shape rather than
  splitting the STL. Both fall back to the mesh computation for non-exact
  nodes.
- **Modified**: `volume_epsilon` has nothing to absorb on the exact path.
  When it is supplied and every comparison in that call routed exact, the
  assertion emits a warning and ignores it. In a mixed assembly where some
  pairs route faceted, it stays live for those pairs and no warning is
  emitted.
- A Boolean kernel failure raises, naming the pair. It SHALL NOT fall back to
  a mesh verdict — a silent fallback would hide exactly the interference this
  path exists to find.
- The three distance assertions — `assertInside`, `assertClose`, `assertFar` —
  are deliberately **out of scope** and keep reading meshes unchanged. Their
  weakness is vertex sampling rather than tessellation, and replacing them
  with `BRepExtrema` is separate follow-on work.

**BREAKING** (behavioural, not API): verdicts change in both directions. Real
sub-facet interference the mesh path missed now fails, and nominally exact
fits that failed on facet phase now pass. Projects retire their tessellation
epsilons deliberately, per project, as evidence.

**BREAKING** (identity): a fused solid's STL bytes change, because its
triangulation now comes from OCCT rather than CGAL. Printed-piece identity is
content-derived (ADR-043), so fused pieces receive new ids on first rebuild.
This is the capability behaving correctly — the artifact genuinely changed —
but any recorded piece id for a fusion goes stale.

## Capabilities

### New Capabilities

- `exact-geometry`: the representation-level contract — what makes a node
  exact, the `shape()` accessor and its frame, the `.brep` artifact and its
  currency, the fuse that composes exact children, and the kernel-failure
  rule. Cross-cutting, in the manner of `printed-pieces`.

### Modified Capabilities

- `node-model`: adds the exactness capability to the node contract and records
  why it composes from children while `rigid` deliberately does not; names
  which leaf adapters expose exact geometry.
- `build-pipeline`: `.brep` joins the artifact layout and the mtime-equality
  currency rule; the sweep spares it; the asynchronous STL render protocol no
  longer covers an exact fusion, which renders synchronously in-process.
- `test-framework`: exact routing for the intersection-volume assertions,
  `assertJoined` and `assertNoDisconnectedSolids`; the two
  `assertIntersectVolume*` assertions move onto the shared helper; the
  `volume_epsilon` warn-and-ignore rule; the distance assertions explicitly
  unchanged.

## Impact

- `solid_node/node/base.py` — `exact`, `shape()`, `.brep` path and currency.
- `solid_node/node/leaf.py`, `internal.py`, `fusion.py` — capability
  composition, fuse, synchronous fused STL.
- `solid_node/node/adapters/cadquery.py` — the one exact adapter.
- `solid_node/test.py` — assertion routing and the epsilon rule.
- `solid_node/core/builder.py` — artifact currency and the sweep.
- No new dependency: `cadquery==2.5.*` (OCCT via `cadquery-ocp`) is already
  required. OpenSCAD remains required; making it conditional on backend is
  deliberately deferred to the following cycle.
- Existing build directories re-render once on upgrade, because an exact
  node's artifacts are not current until its `.brep` exists — about 37 s for
  `v8-engine`'s 24 distinct shapes, one time.
- Validating callers: `v8-engine` (tessellation workarounds to retire) and
  `snowman` (the one CadQuery project with a `FusionNode`, so the one place a
  produced STL changes shape).
