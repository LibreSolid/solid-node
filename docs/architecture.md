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

1. **Geometry follows the strongest backend path available**
   (ADR-004/044/045/046/047). Every backend still produces SCAD and an STL.
   Solid2 and raw `.scad` leaves, and faceted fusions containing them, render
   through OpenSCAD. The OCCT backends — CadQuery and build123d — preserve
   BREP geometry, and all-exact fusions compose and tessellate in OCCT
   without OpenSCAD, whichever of the two produced each child. JSCAD produces
   its STL through its own `jscad` tool. OpenSCAD is therefore conditional on
   the paths that invoke it, not a universal framework prerequisite. The same
   rule governs the `manifold3d` mesh engine (ADR-052): it decides faceted
   geometry, so it is required by comparisons involving a part without exact
   geometry and by `assertAssemblySupported`, whose statics phase is faceted
   for every body — and by nothing else. Both are resolved once per process at
   the point of use and report by name when absent.
2. **The build artifact is the currency, mtime is its clock**
   (ADR-006/026/033/050). STLs are cached per parameter-hashed identity and
   validated by mtime *equality* against the max source mtime, in integer
   nanoseconds — never as a float, which cannot survive the `os.utime`
   round trip off a filesystem coarser than a nanosecond (ADR-050). Caches
   at every layer — meshes, Manifolds, HTTP responses — key on the same
   `(artifact, mtime)` signal, so artifact freshness is the one
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
`CadQueryNode` and `Build123dNode` (both export to STL and re-import),
`OpenScadNode` (`scad_source` + module call), `JScadNode` (shells out to the
`jscad` CLI). Every node exposes derived read-only exactness (ADR-044): the
OCCT adapters are exact, the other leaf adapters are faceted, and an
internal node is exact only when every child is. Exactness does not require
one backend — every exact adapter converts its render result to one shared
OCCT shape at the adapter boundary, so the exact layer holds a single type and
a fusion may mix CadQuery and build123d children (ADR-047). Because that
conversion makes everything after it backend-neutral, the contract itself —
`exact`, `shape()`, `as_scad()` — lives once on `ExactLeafNode`, the internal
base every exact adapter extends; each supplies only its `namespace` and any
validation its own API needs. Adapters remain distinct types regardless of the
bases they share. Because build123d
groups solids, sketches and curves under one namespace, `Build123dNode`
additionally rejects a render result that is not a solid, and accepts a
`BuildPart` builder by taking its finished `.part`.

One leaf kind names a *manufacturing method* rather than a backend.
`SheetLeafNode` — internal base, `Build123dSheetNode` its v1 adapter — is a
part cut from sheet stock, authored as a 2D `profile()` plus a declared
`thickness`. The base owns `render()`, which validates the profile and
extrudes it from the XY plane along +Z, so the solid in the tree and the file
a cutter consumes derive from one authored thing and cannot drift apart;
`profile()` is the only extension point (ADR-053). The profile contract is
the base's: exactly one planar face, one outer boundary with holes strictly
inside, on the XY plane, rejected naming the node and the offending type
before anything is written. `thickness` is required and positive at
construction, and as a constructor argument it keys artifacts like any other
parameter. The extrusion is an ordinary backend solid, so a sheet part is an
exact leaf in every respect above — `exact.py` needed no change, and a fusion
may mix a sheet part with any other exact child.

Exact nodes expose unplaced BREP geometry through
`shape()`; placement remains the caller's responsibility through the same
composed matrices as the mesh path. An exact `FusionNode` fuses its placed
children in OCCT and represents that fuse in both BREP and STL (ADR-045).
Each adapter still emits SCAD, but artifact production follows its backend:
Solid2 and raw OpenSCAD leaves use OpenSCAD, CadQuery and build123d — sheet
parts included — use OCCT, and JSCAD uses `jscad` (ADR-046). Emitting SCAD
does not itself require the OpenSCAD binary. A sheet leaf writes one artifact
the others do not: a nominal DXF of its profile, in millimeters with arcs
preserved, beside its `.stl` and `.brep` and under the same freshness rules,
which its skip guard also requires.

Identity is split three ways. `uniq_id` (class qualname + canonicalized
params, 12-hex sha256, readable prefix) keys build artifacts —
parameters change, artifacts change; `name` (explicit or derived from
the parent attribute holding the child) addresses the tree for tests
and the viewer, and never touches geometry (ADR-026). A **piece** id
(12-hex sha256 of the built STL's bytes) identifies one thing to print,
so solids factored into different classes but building identical geometry
are one piece, while handed variants are two (ADR-043). Each answers a
different question — rebuild needed, addressed how, same thing to print —
and conflating any two produces silently wrong answers.

### Kinematics (NODE · spec `kinematics`)

Transforms are first-class operation objects (ADR-023):
`Rotation`/`Translation` render for four consumers — `.scad()`,
`.mesh()`, `.serialized`, `.matrix()` (ADR-028) — plus `.reversed`.
`AssemblyNode` is the only animatable node: its `time` is OpenSCAD's
`$t` (0..1) symbolically, or a float under `set_keyframe()` (ADR-008).
Keyframing is reversible: `clear_keyframe()` drops the fixed time and
re-renders down the same subtree, so operations hold `$t` expressions
again (ADR-051). Re-rendering is what restores them — an operation
records whatever value `render()` computed, so a keyframed tree has no
symbolic form left to recover.

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

STL generation is normally asynchronous: `StlRenderStart` carries a spawned
`openscad` process, PID lock files guard concurrency, and
`build_stls()` loops until nothing is stale. Staleness is **mtime
equality** — generated files are back-dated with `os.utime` to the max
source mtime (ADR-006), taken over `node.files`: the node's own source
plus its project-local import closure, unioned upward from children
(ADR-033). Both sides of that equality are integer nanoseconds
(`st_mtime_ns`, `os.utime(ns=…)`), so the back-date is a fixed point at
whatever resolution the filesystem stores — a float stamp is not, and on a
millisecond-resolution filesystem it left every artifact permanently stale
and this loop non-terminating (ADR-050).

OpenSCAD availability is resolved once per process, at the first operation
that actually requires it (ADR-046). Mesh-backend STL rendering, faceted
fusion, Solid2 symbolic-value evaluation, the OpenSCAD GUI viewer, and the
OpenSCAD snapshot renderer are the complete requiring set. A missing binary
raises one actionable error naming the operation and remedy before subprocess
launch; an all-exact build never performs the check.

A rigid, optimizing **leaf** whose artifacts are current assembles by
importing its STL — `render()` and `as_scad()` never run (ADR-033), so
the check happens before the expensive work rather than after it.
Internal nodes always render: their file set is the union of their
children's and is only known by walking them. The adapters that write
their artifact inside `as_scad()` — CadQuery, build123d, sheet, JSCAD — carry
the same guard, for nodes that opt out of optimization.

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

An exact rigid node has a private `.brep` beside its `.stl` (ADR-044). Both
must match the node mtime for the build to be current; the BREP is spared by
the artifact sweep but is never named in a viewer or export document. An
all-exact fusion is the exception to the subprocess protocol: it writes its
BREP and tessellates its fused shape synchronously in process (ADR-045).

Publication enforces build mechanics and model validity, not project-selected
geometry contracts. It therefore does not count STL components or invoke
whole-solid connectivity assertions. The incomplete-render guard remains: a
manifest may not name a rigid artifact that has not been written, independently
of any geometric test (ADR-039, amended 2026-08-10).

### CLI (BUILD · spec `cli`)

`solid <command> <path>` — command-first grammar since 0.4, with an
exit-2 migration guard for the old order (ADR-024). Commands are a
duck-typed registry: `build`, `develop`, `test`, `snapshot`, `new` (offline
scaffold), `export`. Snapshot has an explicit renderer choice
(ADR-021/041/046): OpenSCAD remains the external-tool default with xvfb
fallback, while the
optional `web` renderer captures the packaged viewer in sandboxed headless
Chromium to produce a true-alpha PNG. Unsupported renderer-specific options
are rejected rather than ignored or substituted. If the default OpenSCAD
renderer is unavailable, the command names `--renderer web` but does not
select it silently. `./.env` is read with
`setdefault` semantics (real environment wins), carrying
`SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT` / `SOLID_BUILD_DIR`.

### Test framework (TEST-FRAMEWORK · spec `test-framework`)

Test-driven CAD is the framework's reason to exist: contracts about
geometry, checked on the real meshes. Tests live in companion files or
on the node via `TestCaseMixin` (ADR-010), run by `solid test` — which
builds first, then runs `test_` methods per declared animation instant
(`@testing_instant` / `@testing_steps`, ADR-011) with operation
checkpoints restored between instants.

Collision assertions (ADR-009/044) select the strongest shared representation:
intersection-volume and connectivity questions use placed OCCT shapes when
both operands are exact and retain trimesh/Manifold for mixed or faceted
pairs. That selection reaches the placement step too (ADR-052): a solid is
placed into the spatial index from its cached bounds alone, and its Manifold
is built only when a comparison really reads it, so an all-exact assembly
builds none and needs no mesh engine. Distance and containment assertions
remain mesh-sampled. This includes the
**paired kinematic fit contract** (ADR-025): `assertBlockedBeyond` +
`assertFreeWithin` perturb a part along its working degree of freedom
(rotational `axis=` or translational `along=`, injected in the local
pre-placement frame, always restored) — fit is certified only by the
pair. `volume_epsilon` separates real interference from boolean noise,
with a deliberately strict default: a flush contact that is non-empty
at exactly 0.0 mm³ **is** a foul until the test opts into an epsilon.

The shared intersection path (ADR-029/044) caches one Manifold per
`(stl_file, mtime)` (watertightness checked once, at fill), culls
provably disjoint pairs with a conservative world-AABB broad-phase,
and reads `is_empty()`/`volume()` straight off lazy-transformed Manifolds —
verdict-identical to the naive faceted path. Exact pairs share the same AABB
broad phase, then use OCCT common and interpret “contains no solid” as empty;
kernel failure raises and never falls back. `volume_epsilon` is ignored with a
warning when every comparison in a call was exact.

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

`assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0, ground=None,
supports=None, stability_margin=0.0)` asks the physical inverse over the same
selection and the same
placement (ADR-048): not whether two parts share material, but whether any part
is floating. A solid is directly supported by another when, displaced by
`max_drop` along the normalized gravity vector — one world-frame translation
folded into the placement matrix — it intersects that solid with positive
volume; zero-volume contact after the drop is not a hold. Those edges form a
support graph, seeded by the solids within `max_drop` of the assembly's
furthest extent along gravity (or by an explicit `ground`, resolved up from a
feature or down through an assembly), and groundedness propagates from
supporter to supported, so a mutual-lean cycle is grounded exactly when a
member reaches ground. `supports=[(supported, supporter), ...]` declares holds
the drop cannot prove — press fits, glue, friction — without grounding
anything by itself. The broad phase is the same sweep-and-prune, run over the
displaced and placed boxes at once so an emitted cross-half pair is exactly a
directed overlap; exact pairs still route to the kernel. Zero or one selected
solid passes without geometry work; a zero `gravity`, a non-positive
`max_drop`, a negative `stability_margin`, and an unresolvable
`ground`/`supports` entry are loud errors.

When reachability holds, a second phase proves frictionless static equilibrium
(ADR-049): that push-only normal forces over the detected interfaces balance
every non-anchored solid's weight and its torque about its own centre of mass,
decided by one deterministic `scipy.optimize.linprog` HiGHS solve of the
L1-relaxed feasibility program. Interfaces are extracted by meshing each
displaced intersection and classifying its faces to the supporter's boundary by
nearest surface, so contact points and normals sit on the supporter's real,
undisplaced surface; gravity-perpendicular faces are discarded as walls the
displacement drove into. Detection runs the drop sweep and a symmetric lift
sweep through the same broad phase, the lift contributing contacts only so a
snug hole's upper wall can complete a couple, never support-graph edges.
Contact extraction and mass properties (placed facets, uniform unit density, so
weight is volume) are faceted even for exact pairs, whose edge existence still
routes to the kernel. With `ground=None` a virtual floor slab in the gravity
frame is the sole anchored body, so a default seed must balance on its real
footprint; an explicit `ground` anchors exactly the resolved solids and no
floor exists. A declared `supports` edge carries a free six-component wrench.
`stability_margin` shrinks each patch toward its centroid first. The failure
names each unbalanced solid and whether force or torque does not close, and
points at `supports=`. The assertion now claims support reachability, force
balance, torque balance and toppling over the detected contacts; friction,
adhesion, purely lateral wall reactions, single-solid floor toppling and
dynamics remain outside it.

All three integrity assertions run only when ordinary project test source
calls them. `solid new` declares the connectivity and interference pair as two
counted companion tests; non-test commands do not load that companion. `assertJoined(a, b,
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

`solid export` (ADR-020/034/035/042) emits a self-contained static artifact:
`manifest.json` (`format: solid-node-export, version: 1` — a versioned
tree-document schema shared with `viewer.json`, not a portability claim),
deduplicated `models/*.stl`, and a
React-free three.js **widget** whose side-effect-free imperative core mounts a
published tree into a host and returns a lifecycle handle; its published entry
auto-mounts `data-solid-widget` containers, animates `$t` client-side (play/
pause + timeline when animated), and honors `?t=`/`?autoplay=0`. The browser
global exposes API version 4 so a host can check compatibility before mounting.
The handle exposes immutable assembly metadata and host-controlled subtree
focus and visibility by root-relative name path. Those inspection controls are
session state: they neither mutate nor unload the published tree, and valid
paths survive targeted updates while removed paths are discarded.
Hosts may supply camera position/target, an up direction, and field of view;
the latter two retain Z-up/50° defaults when absent. OpenSCAD camera conversion
is isolated as pure math and supplies the browser renderer with eye, target,
up, and OpenSCAD's 22.5° perspective field of view (ADR-041).
The tree
walk is the same rigid-stops/non-rigid-recurses rule as the NodeAPI;
operations ship as raw expression strings. Both producers use the same core
serializer, which links rendered children before recursion and includes
`mtime`; export alone maps and copies rigid models beneath `models/`.

The serializer is a pure walk: **which time a document is written in is a
producer decision** (ADR-051). `export_node` clears any keyframe before
serializing, so `manifest.json` carries `$t` whatever the caller did to the
node, and leaves it in symbolic time; the builder never keyframes; the browser
snapshot keyframes deliberately and bakes one instant through `math.py`, whose
degree semantics are the ADR-022 source of truth. A new producer states its own
time contract.

Every producer — export, build snapshot, browser snapshot — also publishes a
**printed-piece inventory** (ADR-043): a top-level `pieces` list beside `root`,
one entry per distinct built artifact content, carrying `id`, `name`,
contributing `sources` and `models`, `count`, bounding `size`, `volume`, and
`watertight`, with every rigid node carrying the `piece` id that resolves into
it. Facts are read from the artifact's own base mesh, so no pose or `$t` leaks
into them. The section is additive at `version: 1`; a consumer reading only the
tree is unaffected.

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
  mtime, compared as integer nanoseconds and never as a float
  (ADR-050); an exact node requires both STL and BREP current, and every
  cache keys on that signal (ADR-006/028/029/044). Equality, not
  tolerance: a window wide enough to absorb a filesystem's timestamp
  quantum is a window in which a real edit is invisible.
- A node's source set is its own file plus the project-local modules it
  imports, transitively — never the `__init__.py` of a package the walk
  merely traverses, which would make every node depend on every file
  (ADR-033). The set over-approximates on purpose: a spurious rebuild is
  cheap, a stale model is not.
- `name=` never influences geometry or `uniq_id`; any parameter change
  changes the artifact key (ADR-026). Piece identity is the converse: it
  derives from built content only, never from a class, its parameters, or
  its artifact path — an artifact that cannot be read gets no piece id
  rather than borrowing one (ADR-043).
- Re-rendering an instant is absolute, never cumulative; only
  driver-tagged operations are swept (ADR-023).
- All pose consumers compose own-ops-first, ancestors after, later
  operations outermost — Python and both browsers alike (ADR-027/028).
- A non-empty, zero-volume **faceted** flush contact fouls at
  `volume_epsilon=0`; exact boundary contact contains no solid and is empty.
  Kinematic fit still needs the Blocked **and** Free pair (ADR-025/029/044).
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
| Node model | `solid_node/node/`, `solid_node/exact.py` | `node-model`, `exact-geometry` | 001–004, 006, 026, 044–045, 047 |
| Kinematics | `node/operations.py`, `node/assembly.py`, `math.py` | `kinematics` | 008, 022, 023, 028 |
| Build pipeline | `solid_node/core/` | `build-pipeline` | 005–007, 018, 026 |
| CLI | `cli.py`, `solid_node/manager/` | `cli` | 021, 024 |
| Test framework | `solid_node/test.py`, `manager/test.py` | `test-framework` | 009–011, 025, 029, 040, 048 |
| Web viewer | `solid_node/viewers/web/` | `web-viewer` | 012–015, 018, 036 |
| Export & widget | `core/export.py`, `core/serializer.py`, `viewers/widget/` | `export` | 020, 034, 051 |
| Sphinx embedding | `solid_node/sphinx.py` | `sphinx-embedding` | 020 |
