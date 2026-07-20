# solid-node Architecture

This is the synthesis document: the current architecture of solid-node
in one place. It sits between two other records and is derived from
them:

- **[`openspec/specs/`](../openspec/specs/)** — the behavioral
  contracts: what the system observably does, requirement by
  requirement.
- **[`docs/adrs/`](adrs/README.md)** — the decision log: each ADR is a
  delta explaining *why* one piece is the way it is.

ADRs accumulate; this document integrates. When an OpenSpec change is
archived and it shifted the structure described here, updating this
document is part of landing the change — same rule as the specs.

## The big picture

A solid-node project is a **Python program that evaluates to a tree of
nodes**. Leaves generate solid geometry; internal nodes compose and
place it. From that single tree, the framework derives everything else:

```
                     your_project.py
                           │  load_node()                (BUILD)
                           ▼
                      node tree                          (NODE)
              render() → validate() → as_scad()
                           │
           ┌───────────────┼──────────────────┐
           ▼               ▼                  ▼
      .scad files     world meshes      serialized ops
      → openscad      (trimesh /        ($t expressions)
      → .stl cache    manifold3d)             │
      (BUILD)         (TEST-FRAMEWORK)        ▼
           │                            web viewer / widget
           ▼                            evaluate $t per frame
      dev loop, snapshot,               (VIEWER-WEB, EXPORT,
      export models                      MATH)
```

Three architectural commitments shape almost every subsystem:

1. **OpenSCAD is the universal compilation target** (ADR-004). Every
   backend — solid2, CadQuery, raw `.scad`, JSCAD — funnels into SCAD
   text, and the `openscad` binary produces the STLs. This buys backend
   plurality at the price of OpenSCAD's CSG model being the common
   denominator.
2. **The build artifact is the currency, mtime is its clock**
   (ADR-006/026). STLs are cached per parameter-hashed identity and
   validated by mtime *equality* against the max source mtime. Caches
   at every layer — meshes, Manifolds, HTTP responses — key on the same
   `(artifact, mtime)` signal, so "the STL is fresh" is the one
   invalidation concept the whole system shares.
3. **One kinematic truth, recomputed absolutely, consumed everywhere**
   (ADR-023/027/028). A node's placement is its operation list. Every
   consumer — SCAD output, world-space meshes for assertions, the two
   browser renderers — folds that same list, own-ops-first then
   ancestors, later operations outermost. Nothing tracks incremental
   mutations; every consumer recomputes pose from declared state, which
   is what makes re-renders idempotent and caching safe.

## Subsystems

### Node model (NODE · spec `node-model`)

`AbstractBaseNode` roots a composite tree (ADR-001): `InternalNode`
subclasses return child lists from `render()`, `LeafNode` subclasses
return one geometry object, and validation enforces the split on every
assembly. Users implement `render()`; the framework owns the
non-overridable `assemble()` pipeline — render → validate → `as_scad`
→ SCAD generation → optimized STL import → apply operations — memoized
per instance (ADR-002).

Two concrete internal nodes encode the **rigid/non-rigid** axis
(ADR-003): `FusionNode` (rigid union, no `time`) and `AssemblyNode`
(non-rigid, animatable). Rigidity propagates upward (`parent.rigid AND
child.rigid`); only rigid nodes produce STLs, which is why rigid
geometry must be time-invariant.

Leaf adapters (ADR-004) wrap the backends: `Solid2Node`,
`CadQueryNode` (exports to STL, re-imports), `OpenScadNode`
(`scad_source` + module call), `JScadNode` (shells out to the `jscad`
CLI).

Identity is split (ADR-026): `uniq_id` (class qualname + canonicalized
params, 12-hex sha256, readable prefix) keys build artifacts —
parameters change, artifacts change; `name` (explicit or derived from
the parent attribute holding the child) addresses the tree for tests
and the viewer, and never touches geometry.

### Kinematics (NODE · spec `kinematics`)

Transforms are first-class operation objects (ADR-023):
`Rotation`/`Translation` render for four consumers — `.scad()`,
`.mesh()`, `.serialized`, `.matrix()` (ADR-028) — plus `.reversed`.
`AssemblyNode` is the only animatable node: its `time` is OpenSCAD's
`$t` (0..1) symbolically, or a float under `set_keyframe()` (ADR-008).

Assembly `render()`s are wrapped for **driver-tagged idempotency**
(ADR-023): operations applied during a render are tagged with the
driving assembly, and each re-render sweeps only its own tags before
re-expressing pose absolutely. Static placements (untagged) survive;
independent drivers of one node don't disturb each other.

World pose is one composed 4×4 matrix — own operations then ancestors,
premultiplied (ADR-028) — recomputed on *every* access because
operation values can be animated expressions and the operations list
is mutated by design. The base mesh under it is cached per
`(stl_file, mtime)`.

### Build pipeline (BUILD · spec `build-pipeline`)

Nodes are addressed by **filesystem path**, dynamically imported
(ADR-005); a multi-class file needs a `NODE = Class` marker
(ADR-026). Artifacts land under `$SOLID_BUILD_DIR` (default `_build`),
mirroring the source layout, basename `<script>-<uniq_id>`.

STL generation is asynchronous: `StlRenderStart` carries a spawned
`openscad` process, PID lock files guard concurrency, and
`build_stls()` loops until nothing is stale. Staleness is **mtime
equality** — generated files are back-dated with `os.utime` to the max
source mtime (ADR-006).

The dev loop (ADR-007) is a **single-shot builder** under watchdog:
build, watch `node.files` per-file, exit on change, get respawned by
`solid develop` (which also restarts the viewer process). `solid build`
uses the same builder passes without a viewer or watch loop. Candidate
builds publish `viewer.json` with the recursive viewer state and build-relative
model paths, so private NodeAPI consumers can serve a completed build without
loading project Python (ADR-031).
artifacts build privately and replace the normal build directory only once
the complete tree is current, so a failed rebuild leaves the last successful
artifacts readable. Errors go to `errors.json` in the build dir — file-based
IPC, no broker (ADR-018). A broken initial build kills develop; a broken
reload falls back to a broad recursive watch and keeps the loop alive.

### CLI (BUILD · spec `cli`)

`solid <command> <path>` — command-first grammar since 0.4, with an
exit-2 migration guard for the old order (ADR-024). Commands are a
duck-typed registry: `build`, `develop`, `test`, `snapshot` (headless PNG via
OpenSCAD, xvfb fallback — the visual feedback channel for agents,
ADR-021), `new` (offline scaffold), `export`. `./.env` is read with
`setdefault` semantics (real environment wins), carrying
`SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT` / `SOLID_BUILD_DIR`.

### Test framework (TEST-FRAMEWORK · spec `test-framework`)

Test-driven CAD is the framework's reason to exist: contracts about
geometry, checked on the real meshes. Tests live in companion files or
on the node via `TestCaseMixin` (ADR-010), run by `solid test` — which
builds first, then runs `test_` methods per declared animation instant
(`@testing_instant` / `@testing_steps`, ADR-011) with operation
checkpoints restored between instants.

Assertions (ADR-009) are trimesh/manifold booleans over world-space
meshes: intersection/containment/distance/volume checks, plus the
**paired kinematic fit contract** (ADR-025): `assertBlockedBeyond` +
`assertFreeWithin` perturb a part along its working degree of freedom
(rotational `axis=` or translational `along=`, injected in the local
pre-placement frame, always restored) — fit is certified only by the
pair. `volume_epsilon` separates real interference from boolean noise,
with a deliberately strict default: a flush contact that is non-empty
at exactly 0.0 mm³ **is** a foul until the test opts into an epsilon.

The intersection path (ADR-029) caches one Manifold per
`(stl_file, mtime)` (watertightness checked once, at fill), culls
provably disjoint pairs with a conservative world-AABB broad-phase,
and reads `is_empty()`/`volume()` straight off lazy-transformed
Manifolds — verdict-identical to the naive path, orders of magnitude
faster on real assemblies.

### Viewers (VIEWER-WEB · spec `web-viewer`)

`solid develop` serves a FastAPI + Uvicorn app (ADR-015, post-018 the
only HTTP service): static React build by default, npm-proxy under
`--web-dev`. The **NodeAPI** (ADR-014) recursively mounts one sub-API
per tree node — URLs mirror the assembly; rigid nodes serve STLs (with
Last-Modified/304 and wait-for-file), non-rigid nodes list children.

The browser app (React + three.js, ADR-012/013) renders each mesh from
one absolute world matrix composed from the operation levels
(ADR-027 — same semantics as `node.mesh`), evaluates `$t` expressions
per frame with degree-convention trig and `^`→`pow()` (ADR-022), and
reloads through `/ws/reload`: the develop loop restarts the server per
rebuild, the socket reconnect delivers the signal, `/_build_error`
gates whether to show a traceback or reload the tree, and a generation
counter disposes superseded trees.

A sibling OpenSCAD GUI viewer (`--openscad`) and the headless
`snapshot` command cover the non-browser cases.

### Export and embedding (EXPORT · specs `export`, `sphinx-embedding`)

`solid export` (ADR-020) emits a self-contained static artifact:
`manifest.json` (`format: solid-node-export, version: 1` — a versioned
contract with three consumers), deduplicated `models/*.stl`, and a
React-free three.js **widget** that auto-mounts on
`data-solid-widget` containers, animates `$t` client-side (play/pause
+ timeline when animated), and honors `?t=`/`?autoplay=0`. The tree
walk is the same rigid-stops/non-rigid-recurses rule as the NodeAPI;
operations ship as raw expression strings.

The Sphinx extension (`.. solid-node:: <export-dir>`) embeds exports
as iframes, copies them at `html-collect-pages`, and completes missing
widget files from the installed package — docs build without the CAD
stack.

### Expression math (MATH · in spec `kinematics`)

There is exactly one `$t` semantics: **OpenSCAD's degree
conventions**, with `^` as power (ADR-022). `solid_node/math.py` is
the dual-mode source of truth (numeric under keyframes, deferred
OpenSCAD expressions when symbolic); the dev viewer's evaluator
reproduces it. Four runtimes must agree: math.py, OpenSCAD, dev
viewer, export widget.

## Load-bearing invariants

The short list that changes must not silently break:

- An artifact is fresh **iff** its mtime equals the node's max source
  mtime; every cache keys on that signal (ADR-006/028/029).
- `name=` never influences geometry or `uniq_id`; any parameter change
  changes the artifact key (ADR-026).
- Re-rendering an instant is absolute, never cumulative; only
  driver-tagged operations are swept (ADR-023).
- All pose consumers compose own-ops-first, ancestors after, later
  operations outermost — Python and both browsers alike (ADR-027/028).
- A non-empty, zero-volume flush contact fouls at
  `volume_epsilon=0`; kinematic fit needs the Blocked **and** Free
  pair (ADR-025/029).
- `manifest.json` format/version is a public contract; breaking it
  means bumping the version and updating exporter, widget, and Sphinx
  extension together (ADR-020).
- Every `$t` evaluator uses degree trig and treats `^` as power
  (ADR-022).
- Users never override `assemble()`; rigid geometry is time-invariant
  (ADR-002/003).

## Known gaps and tensions

- **Export-widget `$t` parity defect** (ADR-022): the widget evaluator
  uses radian trig and lacks the `^` rewrite — non-linear animated
  exports render wrong. Open; first in line for an OpenSpec change.
- **No automated cross-runtime parity enforcement** (ADR-022): the
  four-runtime agreement holds by discipline; a golden parity corpus
  or shared evaluator is the recorded way out.
- **Create React App is deprecated** (ADR-013): the dev viewer's
  toolchain carries migration debt (Vite or similar).
- **Sequential STL rendering**: `build_stls` renders one STL at a
  time; cold builds could parallelize `openscad` jobs
  (`docs/performance-improvement.md` §4–5, unscheduled).

## Map

| Subsystem | Code | Spec capability | ADRs |
|---|---|---|---|
| Node model | `solid_node/node/` | `node-model` | 001–004, 006, 026 |
| Kinematics | `node/operations.py`, `node/assembly.py`, `math.py` | `kinematics` | 008, 022, 023, 028 |
| Build pipeline | `solid_node/core/` | `build-pipeline` | 005–007, 018, 026 |
| CLI | `cli.py`, `solid_node/manager/` | `cli` | 021, 024 |
| Test framework | `solid_node/test.py`, `manager/test.py` | `test-framework` | 009–011, 025, 029 |
| Web viewer | `solid_node/viewers/web/` | `web-viewer` | 012–015, 018, 027 |
| Export & widget | `core/export.py`, `viewers/widget/` | `export` | 020 |
| Sphinx embedding | `solid_node/sphinx.py` | `sphinx-embedding` | 020 |
