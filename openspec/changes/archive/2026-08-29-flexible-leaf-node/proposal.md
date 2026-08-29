# Change: A flexible leaf node, with molejo as its first adapter

## Why

Machines contain parts whose *shape* is a function of machine state, not
just their placement: valve springs, timing belts, cable looms, filament.
The framework has no way to model them, and the gap is recorded in its own
words:

- `LeafNode.time` raises *"Implementing a FlexibleNode is in the roadmap"*
  (`solid_node/node/leaf.py`), and `docs/status-and-roadmap.rst` lists the
  FlexibleNode as roadmap item 3.
- ADR-003 and ADR-008 both record time-dependent leaf geometry as
  deliberately deferred, naming the STL-caching and topology concerns that
  deferred it.
- The v8-engine project designed *around* the absence:
  `increment-7-valvetrain.md` states that flexible springs cannot be
  modeled because "modeling an undeformed decorative spring would create
  false interference", and increment 8 lists belts and flexible nodes as
  out of scope for the same reason.
- Metamaquina2's belts are today a scalar `scale` on a port — correct
  kinematics with no body.

[molejo](https://github.com/LibreSolid/molejo) was built to close this
gap and is ready to be consumed: an analytic representation for swept
flexible parts whose spec is a serializable JSON document, with a Python
evaluator (exact deterministic meshes, STL), a JavaScript evaluator
(three.js buffers cheap enough to re-evaluate every animation frame, in
place), an optional OCCT B-rep evaluator (`molejo[brep]`), and shared
parity fixtures pinning the two runtimes to each other. Its own OpenSpec
change (`define-swept-shape-spec`, section 8) reserves consumer-side
validation for exactly this integration.

The concerns that deferred the FlexibleNode are now answerable:

- **STL caching**: a flexible part's viewer representation is its spec,
  not a mesh, so no per-frame artifact exists to cache; the only mesh
  files are per-binding snapshots for the OpenSCAD document path.
- **Mesh topology changes**: molejo's tessellation is fixed and declared
  in the spec — vertex count and ordering are parameter-independent by
  construction, which is what makes per-frame buffer reuse safe.
- **Per-frame evaluation in the browser**: the driver machinery
  (ADR-056, stages 1–3c) already delivers named scalar state to the
  widget and re-evaluates expressions per frame; flexible geometry is
  the same mechanism with `geometry = f(params)` instead of
  `matrix = f(params)`.

## What Changes

- **`FlexibleNode`** (`solid_node/node/flexible.py`): an abstract
  *non-rigid leaf* kind. Its geometry is a pure function of its declared
  ports' bound values; it cannot be fused, lives under assemblies, never
  produces a cached rigid artifact, and serializes to the shared document
  as a new `flexible` node shape carrying an embedded shape spec plus one
  expression string per parameter.
- **`MolejoNode`** (`solid_node/node/adapters/molejo.py`): the concrete
  adapter. `render()` returns a molejo `Shape`; each of the shape's
  parameters must match a declared port by name; the base evaluates
  meshes through molejo's Python evaluator, materializes per-binding
  snapshot STLs for the SCAD/OpenSCAD path, and exposes exact geometry
  through molejo's B-rep evaluator.
- **Document schema**: `viewer.json`/`manifest.json` gain the `flexible`
  node shape; a document containing one declares `version: 3`, a document
  containing none stays exactly `version: 2`. Consumers accept both.
- **Widget**: bundles molejo's JavaScript evaluator, evaluates each
  flexible node's parameter expressions in the existing evaluation scope,
  and re-evaluates geometry into reused buffers only on frames where a
  free variable of those expressions changed. The viewer API version is
  raised.
- **New capability `flexible-parts`**; deltas to `node-model`,
  `exact-geometry`, `build-pipeline`, `export`, and `viewer-package`.

## Dependencies

solid-node gains a dependency on the `molejo` Python package (with its
`brep` extra) and the widget on the `molejo` npm package. Neither is
published yet; development proceeds against local installs from the
molejo checkout, and the packaging-facing tasks are gated on the pilot's
explicit decision to publish molejo to PyPI and npm. Nothing in this
change publishes anything.

## Out of scope

- Belt/spline validation in real projects (v8-engine valve spring,
  Metamaquina2 belt) — that is project-side work consuming this change,
  recorded as molejo's section-8 evidence, not framework tasks here.
- Any change to molejo itself; findings feed back as molejo issues.
- Click-to-focus, controls, or any UI beyond rendering flexible geometry.
- OpenSCAD *animation* of flexible parts (snapshot substitution only,
  consistent with ADR-056's treatment of drivers).

## Impact

- Affected specs: `flexible-parts` (new), `node-model`, `exact-geometry`,
  `build-pipeline`, `export`, `viewer-package`.
- Affected code: `solid_node/node/` (new `flexible.py`, `leaf.py` message,
  `adapters/molejo.py`), `solid_node/core/serializer.py`,
  `solid_node/core/export.py`, `solid_node/viewers/widget/`
  (`types.ts`, `tree.ts`, new flexible geometry module, `package.json`,
  build banner), packaging metadata (`pyproject.toml`).
- Affected docs: `docs/architecture.md`, `docs/leaf-nodes.rst`,
  `docs/animation.rst`, `docs/status-and-roadmap.rst`, ADR index (one new
  ADR; ADR-003/ADR-008 gain a pointer), stale ADR-022-adjacent viewer API
  version sync (see design.md, incidental findings).
