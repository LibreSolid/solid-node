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
      dev loop, OpenSCAD snapshot,      (VIEWER-WEB, EXPORT,
      export models                      MATH)
```

Three architectural commitments shape almost every subsystem:

1. **OpenSCAD is the universal compilation target** (ADR-004). Every
   backend — solid2, CadQuery, raw `.scad`, JSCAD — funnels into SCAD
   text, and the `openscad` binary produces the STLs. This buys backend
   plurality at the price of OpenSCAD's CSG model being the common
   denominator.
2. **The build artifact is the currency, mtime is its clock**
   (ADR-006/026/033). STLs are cached per parameter-hashed identity and
   validated by mtime *equality* against the max source mtime. Caches
   at every layer — meshes, Manifolds, HTTP responses — key on the same
   `(artifact, mtime)` signal, so "the STL is fresh" is the one
   invalidation concept the whole system shares. The source set behind
   that clock is a node's own file plus the project-local modules it
   imports, transitively (ADR-033), so a contributing module edit
   invalidates the nodes that read it — and only those.
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
(non-rigid, animatable). Rigidity is static and determined by node type;
a fusion rejects any non-rigid child during validation, enforcing "fuse
solids, then assemble them" (ADR-039). Only rigid nodes produce STLs, which
is why rigid geometry must be time-invariant. A topmost rigid node is the
first rigid node on a branch below an assembly, or a rigid root itself; its
STL is the complete printed solid for that branch.

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

Nodes are addressed by **reference** — a qualifier
(`package.module:Class`), a filesystem path, or a path plus class —
dynamically imported and resolved against a project root discovered
from the nearest ancestor `pyproject.toml` carrying `[tool.solid-node]`
(ADR-005, superseded by project-manifest-node-references). A bare path
to a file defining several node classes must name the one meant in the
reference; implicit discovery remains limited to classes defined in the
loaded file. Artifacts remain keyed to the selected class's real
implementation source. The source set tracks that implementation/import
closure, so an edit to it invalidates and reloads the active node.
Artifacts land under `$SOLID_BUILD_DIR` (default `_build`, resolved
against the discovered project root rather than the working directory),
mirroring the source layout, basename `<script>-<uniq_id>`.

STL generation is asynchronous: `StlRenderStart` carries a spawned
`openscad` process, PID lock files guard concurrency, and
`build_stls()` loops until nothing is stale. Staleness is **mtime
equality** — generated files are back-dated with `os.utime` to the max
source mtime (ADR-006), taken over `node.files`: the node's own source
plus its project-local import closure, unioned upward from children
(ADR-033).

A rigid, optimizing **leaf** whose artifacts are current assembles by
importing its STL — `render()` and `as_scad()` never run (ADR-033), so
the check happens before the expensive work rather than after it.
Internal nodes always render: their file set is the union of their
children's and is only known by walking them. The adapters that write
their artifact inside `as_scad()` — CadQuery, JSCAD — carry the same
guard, for nodes that opt out of optimization.

The dev loop (ADR-007) is a **single-shot builder** under watchdog:
build, watch `node.files` per-file, exit on change, get respawned by
`solid develop` (which also restarts the viewer process). `solid build`
uses the same builder passes without a viewer or watch loop. Candidate
builds publish `viewer.json` with the versioned `solid-node-export` tree
schema, linked node names, per-node `mtime`, and build-root-relative model
paths, so private NodeAPI consumers can serve a completed build without
loading project Python (ADR-031/034). Sharing that schema marker with export
does not make a build publication portable: it copies no meshes and retains
its private `viewer.json` document boundary.
artifacts write directly into one ordinary build directory. Each artifact is
written to a temporary sibling and replaced with `os.replace`; OpenSCAD renders
to a temporary STL and publishes it only on completion. `viewer.json` is the
manifest and is written last, so it never names a partial artifact; a later
sweep removes files it no longer names. A build whose artifacts are all current
still republishes that manifest when it no longer matches the model, since the
pass that renders an artifact exits before writing the document. The project
lock serializes builders, while readers remain lock-free. This intentionally
permits a mixed model during a build and a failed build can leave partial new
work, but no reader sees a torn file (ADR-038, reversing ADR-030 and
superseding ADR-032). Errors go to an atomically written `errors.json` in the
build dir — file-based IPC, no broker
(ADR-018). A broken initial build kills develop; a broken reload falls back to
a broad recursive watch and keeps the loop alive.

Publication enforces build mechanics and model validity, not project-selected
geometry contracts. It therefore does not count STL components or invoke
whole-solid connectivity assertions. The incomplete-render guard remains: a
manifest may not name a rigid artifact that has not been written, independently
of any geometric test (ADR-039, amended 2026-08-10).

### CLI (BUILD · spec `cli`)

`solid <command> <path>` — command-first grammar since 0.4, with an
exit-2 migration guard for the old order (ADR-024). Commands are a
duck-typed registry: `build`, `develop`, `test`, `snapshot`, `new` (offline
scaffold), `export`. Snapshot has an explicit renderer choice (ADR-021/041):
OpenSCAD remains the dependency-free default with xvfb fallback, while the
optional `web` renderer captures the packaged viewer in sandboxed headless
Chromium to produce a true-alpha PNG. Unsupported renderer-specific options
are rejected rather than ignored or substituted. `./.env` is read with
`setdefault` semantics (real environment wins), carrying
`SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT` / `SOLID_BUILD_DIR`.

### Test framework (TEST-FRAMEWORK · spec `test-framework`)

Test-driven CAD is the framework's reason to exist: contracts about
geometry, checked on the real meshes. Tests live in companion files or
on the node via `TestCaseMixin` (ADR-010), run by `solid test` — which
builds first, then runs `test_` methods per declared animation instant
(`@testing_instant` / `@testing_steps`, ADR-011) with operation
checkpoints restored between instants.

Collision assertions (ADR-009) are trimesh/manifold booleans over world-space
meshes: intersection/containment/distance/volume checks, plus the
**paired kinematic fit contract** (ADR-025): `assertBlockedBeyond` +
`assertFreeWithin` perturb a part along its working degree of freedom
(rotational `axis=` or translational `along=`, injected in the local
pre-placement frame, always restored) — fit is certified only by the
pair. `volume_epsilon` separates real interference from boolean noise,
with a deliberately strict default: a flush contact that is non-empty
at exactly 0.0 mm³ **is** a foul until the test opts into an epsilon.

The shared intersection path (ADR-029) caches one Manifold per
`(stl_file, mtime)` (watertightness checked once, at fill), culls
provably disjoint pairs with a conservative world-AABB broad-phase,
and reads `is_empty()`/`volume()` straight off lazy-transformed
Manifolds — verdict-identical to the naive path, orders of magnitude
faster on real assemblies.

The root-level integrity boundary is the first rigid node on every branch
(ADR-039/040). Connectivity is deliberately solid-local.
`assertNoDisconnectedSolids(node)` explicitly checks that every printed solid
in a selected subtree is one connected body; it reads each topmost rigid
node's local STL. `assertNoSolidInterference(node)` is its world-space
assembly complement: zero or one selected solid passes without geometry work;
otherwise a sweep-and-prune index over conservative world AABBs emits the
potentially interacting pairs, and each is settled by an exact same-kernel
intersection — the sole verification path, with no whole-assembly measurement.
Exact zero-volume boundary contact passes, every positive candidate volume
fails, and no public volume epsilon or private numerical tolerance is exposed.
Correctness rests on the broad phase being complete, which is proved by
framework tests rather than re-checked at runtime (ADR-040). The old all-leaf
`assertNoPairwiseIntersections` sweep remains deprecated and
behavior-compatible.

Both integrity assertions run only when ordinary project test source calls
them. `solid new` declares them as two counted companion tests; non-test
commands do not load that companion. `assertJoined(a, b,
min_weld_volume=...)` checks the separate pairwise claim that two named
features meet directly. It composes operations only below their enclosing
topmost rigid node, excluding whole-solid placement and every animated
ancestor. That frame is meaningful only within one part, so the assertion
refuses a pair drawn from two different solids instead of comparing them at
their own origins. Collision remains world-framed and time-dependent.

### Viewers (VIEWER-WEB · spec `web-viewer`)

`solid develop` serves a FastAPI + Uvicorn app (ADR-015, post-018 the
only HTTP service): static React build by default, npm-proxy under
`--web-dev`. It serves the current atomically published build directory
under `/build/` and the installed shared viewer bundle under `/_viewer`.
The server does not import project source; an absent build or bundle leaves
the reload socket and build-error endpoint available, with a bundle remedy
for the browser shell to display.

The browser app is a small React shell (ADR-013, amended by ADR-036). It
loads the shared viewer bundle, mounts it against `/build/viewer.json` with
inline autoplay controls, names the tab from the snapshot, and uses the
mount handle's `manifestChanged()` after `/ws/reload` reports a successful
build. The shared viewer reconciles the document in place and refetches only
geometry whose `(model path, mtime)` identity changed (ADR-037); the canvas,
viewpoint, animation clock, and unchanged meshes survive. `reload()` remains
available for a host that explicitly needs a complete replacement.
Tree traversal, world-matrix composition, expression evaluation, animation,
stale-load disposal, and targeted-update failure containment live once in the
reusable viewer package (ADR-035/037), not in the development app.

A sibling OpenSCAD GUI viewer (`--openscad`) and the headless
snapshot renderers cover non-interactive cases. The browser snapshot renderer
renders any stale artifact of the photographed node, serializes that node's
tree into a temporary sibling and hardlinks its artifacts there, all while
holding the project build lock, then releases the lock and serves that pinned
staging tree on an ephemeral loopback port. It never republishes or sweeps the
build itself: the published document belongs to the producer serving it, so a
snapshot of one part leaves the rest of the project intact. Playwright
captures only the transparent canvas under Chromium/SwiftShader; staging is
removed after either success or failure (ADR-041).

### Export and embedding (EXPORT · specs `export`, `sphinx-embedding`)

`solid export` (ADR-020/034/035) emits a self-contained static artifact:
`manifest.json` (`format: solid-node-export, version: 1` — a versioned
tree-document schema shared with `viewer.json`, not a portability claim),
deduplicated `models/*.stl`, and a
React-free three.js **widget** whose side-effect-free imperative core mounts a
published tree into a host and returns a lifecycle handle; its published entry
auto-mounts `data-solid-widget` containers, animates `$t` client-side (play/
pause + timeline when animated), and honors `?t=`/`?autoplay=0`. The browser
global exposes API version 3 so a host can check compatibility before mounting.
Hosts may supply camera position/target, an up direction, and field of view;
the latter two retain Z-up/50° defaults when absent. OpenSCAD camera conversion
is isolated as pure math and supplies the browser renderer with eye, target,
up, and OpenSCAD's 22.5° perspective field of view (ADR-041).
The tree
walk is the same rigid-stops/non-rigid-recurses rule as the NodeAPI;
operations ship as raw expression strings. Both producers use the same core
serializer, which links rendered children before recursion and includes
`mtime`; export alone maps and copies rigid models beneath `models/`.

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
- A node's source set is its own file plus the project-local modules it
  imports, transitively — never the `__init__.py` of a package the walk
  merely traverses, which would make every node depend on every file
  (ADR-033). The set over-approximates on purpose: a spurious rebuild is
  cheap, a stale model is not.
- `name=` never influences geometry or `uniq_id`; any parameter change
  changes the artifact key (ADR-026).
- Re-rendering an instant is absolute, never cumulative; only
  driver-tagged operations are swept (ADR-023).
- All pose consumers compose own-ops-first, ancestors after, later
  operations outermost — Python and both browsers alike (ADR-027/028).
- A non-empty, zero-volume flush contact fouls at
  `volume_epsilon=0`; kinematic fit needs the Blocked **and** Free
  pair (ADR-025/029).
- The `solid-node-export` format/version identifies a shared tree-document
  schema; breaking its tree shape or operation serialization means bumping the
  version and updating every producer and consumer together. Portability stays
  producer-specific: `manifest.json` is copied and portable, `viewer.json` is
  build-root-relative and private (ADR-020/031/034).
- Every `$t` evaluator uses degree trig and treats `^` as power
  (ADR-022).
- Users never override `assemble()`; rigid geometry is time-invariant
  (ADR-002/003).
- A topmost rigid node is the boundary of one printed solid, not a guarantee
  that its geometry is connected. Whole-solid integrity is an explicit
  project assertion; connectivity uses the solid-local frame and collision
  uses the world frame (ADR-039, amended 2026-08-10).

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
| Test framework | `solid_node/test.py`, `manager/test.py` | `test-framework` | 009–011, 025, 029, 040 |
| Web viewer | `solid_node/viewers/web/` | `web-viewer` | 012–015, 018, 036 |
| Export & widget | `core/export.py`, `core/serializer.py`, `viewers/widget/` | `export` | 020, 034 |
| Sphinx embedding | `solid_node/sphinx.py` | `sphinx-embedding` | 020 |
