## Context

Status: proposed, awaiting pilot ratification. Date: 2026-09-11.

Standalone cycle opening identities:

- Shop: `/home/asa/devel/libresolid-studio` (unrelated untracked state preserved).
- Framework primary/source and integration target:
  `/home/asa/devel/libresolid-studio/solid-node`, branch `main`.
- Verified clean base: `5e591474b5cf54c2b41f223400d2b6ee3cbb97ae`.
- Cycle branch: `remove-openscad-broker`.
- Bench: `/home/asa/devel/libresolid-studio/solid-node/WTs/remove-openscad-broker`;
  shop-managed slot 8, ports 8008/3008. No sprint membership.
- Prerequisite integrated by fast-forward: expression-graphs planning
  `446bc224720aa0f46cd89a5e125425b9543d6b4a` and implementation
  `5e591474b5cf54c2b41f223400d2b6ee3cbb97ae`, from base
  `e51d196c74f10e240ef0f3580c52f9abee66d63b`. Its clean bench was torn down
  after verification; the branch and archived evidence remain.
- Curta HEAD observed at handoff:
  `d80e7bf71da130295bacc1bd72971e1029e29f9d`. Its working tree now contains
  independent edits to simulation/change records, cover tests and a new
  cover-neighbor tool; none were made, staged or altered by this cycle.
  Implementation measurements must record the actual project content tested
  and must not label that dirty state as identical to the earlier export.
- Viewer observed clean at `6fb082ba9823fb0839631bd4a3ecbf4a41b33b64`.

The originating project is Curta Type I-3x, not a newly invented machine.
The first cycle's complete exports peaked at 831,078,400 bytes warm and
1,179,168,768 bytes with fresh geometry, measured at the kernel cgroup across
descendants. Those are historical measurements, not results for this proposal.
See `../archive/2026-09-11-expression-graphs/evidence.md` and
`../../../workflow/docs/expression-graphs.md`.

Inspection at the base found:

- `node/base.py:assemble()` obtains `self.model` from `as_scad()`, writes
  SCAD, then applies every placement as a SolidPython operation.
- `node/internal.py:as_scad()` links children, aggregates source closures and
  recursively assembles them while also constructing a SCAD union. Structural
  correctness and source discovery therefore depend on presentation.
- Exact, STL, JSCAD, sheet and flexible adapters do geometry/artifact work
  inside `as_scad()`, often only to return an STL-import wrapper.
- `core/export.py` calls `build_stls()`, whose `trigger_stl()` calls
  `assemble()`. Browser publication inherits that SCAD work.
- `FusionNode.generate_stl()` delegates every non-exact case to the base's
  OpenSCAD subprocess, even when every child already owns an STL.
- Currency records describe project sources. Merely changing the framework
  fusion engine does not currently make an unchanged project's cache stale.

## Goals / Non-Goals

Goals:

- Prepare and validate structure and motion without SCAD geometry objects.
- Produce each adapter's artifacts through its native path; compose faceted
  fusions without OpenSCAD mediation and exact fusions without loss of BREP.
- Keep existing modelling technologies and project authoring APIs useful.
- Preserve source-generation safety, artifact reuse, numerical motion parity,
  flexible-part semantics and current viewer documents.
- Measure actual resource cost and prove the remaining OpenSCAD call sites.

Non-goals:

- Removing OpenSCAD support, its GUI, its snapshot renderer, or their defaults.
- Requiring the browser viewer or changing its schema, entry point or process
  protocol; moving AGPL viewer code into the Apache framework is prohibited.
- Removing the SolidPython Python dependency or the expression compatibility
  facade accepted in ADR-101. A neutral core path is not a dependency-free
  installation, and legacy `scad_inline()` remains an OpenSCAD boundary.
- General CSG authoring, a new plugin registry, STEP export, new CAD adapters,
  parallel geometry builds, test-engine changes, mesh repair, or project
  mechanical corrections. No reduction of Curta's controls or parts.

## Decisions

### 1. The existing node tree is the machine representation

Do not introduce a second mutable scene tree. Extract a framework-owned
preparation path (working internal name `_prepare()`) from `assemble()`.
It links children, aggregates files/scopes, preserves render validation and
the whole-tree simulate/fixpoint order, and records native rendered values or
current artifact references. No stage needs a SolidPython union to discover
children, determine exactness, collect sources, or apply pose numerically.

Rigid geometry stays in the node's own local frame. The existing operation
list remains the single placement authority; references to artifacts never
bake the node's own or ancestor operations into its geometry. A fusion alone
consumes child-local placements to make its own local solid.

Preparation, artifact currency, and SCAD presentation have separate memo state.
Reusing current leaf geometry must still avoid calling its CAD `render()`;
re-enumerating simulation must still rebind flexible shape and motion without
stacking operations. Preserve empty assembly and rejected empty/non-rigid
fusion behavior. A native preparation request must not cache a symbolic pose
as a numeric one, or treat a changed binding as a new structural artifact.

Alternative rejected: changing `assemble()` to return a new public scene type.
Its current SCAD result is used directly and is specified. Keep that return
type through a compatibility consumer; do not make every caller migrate to
achieve an internal separation.

### 2. Adapter-owned materialization, SCAD-owned presentation

Factor an internal artifact-production hook out of each built-in adapter.
It consumes the validated native render result only when artifacts are stale.
The lifecycle owns sequencing and currency, not backend commands. Exact
adapters still write BREP before tessellating STL; sheet DXF remains required;
STL import preserves selection/adjust/admission; JSCAD keeps its own tool;
OpenSCAD and Solid2 render their authored geometry through OpenSCAD.

Flexible leaves carry their analytic specification and binding in the neutral
path, without manufacturing an otherwise unused snapshot STL. Numeric mesh
and exact access still evaluate through molejo. SCAD alone requests a
per-binding snapshot, with the existing time-fed omission and unbound-port
errors; this cycle does not pretend SCAD supports independent live controls.

SCAD output methods (`assemble`, `as_scad`, `scad_code`, `generate_scad`) remain
available. Their implementations delegate to a separate SCAD presentation
layer that consumes prepared structure and artifact references, uses the same
operation order and colours, and emits compact expression closures. Keep
native Solid2/OpenSCAD source output when its existing non-optimized path
requests it. Faceted fusion presentation references the canonical fused STL
instead of secretly computing a second, potentially different fusion.

An adapter implemented only by overriding the old `as_scad()` hook remains
supported through an explicit legacy bridge. The bridge is selected by its
declared/overridden capability, never by catching a native producer's error;
custom overrides must not be silently bypassed by an inherited native hook.
Opaque legacy geometry may still require OpenSCAD. The compatibility bridge
does not permit unrelated native children to fall back through SCAD.

Alternative rejected: leaving artifact work inside `as_scad()` but discarding
the returned object. That changes the spelling, not the dependency.

### 3. Choose output consumers without changing viewer policy

The existing normal `solid build` and direct SCAD APIs retain SCAD
deliverables. Their SCAD pass consumes the prepared model under the same
sealed generation/project lock; it is output work, not a prerequisite for
materializing geometry. Preserve last-occurrence SCAD coalescing, immediate
direct/flexible publication, and compare-before-replace semantics.

The geometry build requested by export, the test runner, web snapshots and
browser development does not request assembly SCAD sidecars or flexible
snapshot STLs. It still writes SCAD source where an actual OpenSCAD backend
needs it. Carry this internal output selection through the fresh builder
process boundary; no viewer-package protocol change or new public CLI flag
is required. The compatibility default for an ordinary standalone builder
remains the current SCAD-producing build.

`solid develop` chooses its viewer exactly as today; the OpenSCAD path requests
SCAD presentation, including when selected by the existing no-viewer-package
fallback. Snapshot's default remains OpenSCAD. Missing requested tools still
fail rather than selecting another viewer or geometry engine.

### 4. Faceted fusion uses Manifold, not a new universal geometry backend

After every rigid child artifact is current, a non-exact fusion reads each
child's base mesh, applies only that child's placement within this fusion,
and unions the results using `manifold3d` resolved at point of use. Nested
fusions consume their already-fused child artifacts, not all descendants
again. Exact children of a mixed fusion contribute their existing tessellation;
an all-exact fusion continues to compose BREP in OCCT. Never mesh the whole
assembly or discard exactness merely for a common type.

Use the mesh engine's own input/result status; errors name the fusion, the
offending input where identifiable, and the reason. Do not automatically
repair, change winding, fill holes, enlarge geometry, concatenate in place of
union, or retry through OpenSCAD. STL vertex indexing must follow the already
supported mesh-loading normalization, not a new user-visible repair policy.
Disconnected but valid union results remain allowed: connectivity is a
project assertion, not a newly imposed build gate.

This is a deliberate geometry-engine change, not byte-preserving refactoring.
The official [Manifold README](https://github.com/elalish/manifold/blob/master/README.md)
requires manifold input, and its [algorithm notes](https://github.com/elalish/manifold/wiki/Manifold-Library)
describe finite-precision and coincident-surface handling. These were checked
through Context7 on 2026-09-11; they motivate tests, not a claim that every
current OpenSCAD fusion will be equivalent. Pin the actually installed version
in evidence and use its supported API; no dependency upgrade is proposed.

Alternatives: retaining OpenSCAD for all faceted fusions leaves the broker in
place; mesh concatenation is not union; converting every mesh to OCCT invents
exactness and sacrifices the natural backend split. An engine selector or
automatic OpenSCAD fallback would add an unresolved geometry policy, so is
not part of this proposal. If compatibility evidence demands one, stop for
pilot direction and amend the proposal rather than adding it silently.

### 5. Producer recipe participates in currency

Introduce a private recipe identity in artifact currency, separate from
`uniq_id`, source digest and piece identity. Apply a new revision to faceted
fusion production and to presentation outputs whose recipe changes. A recipe
mismatch (including a missing legacy record for an affected producer) is a
hard cache miss before timestamp/content-restamp shortcuts. Propagate relevant
child production revisions into enclosing fusion artifact currency so a nested
engine change cannot reuse an enclosing old STL. Repeated instances still
share one produced artifact.

Unchanged native leaf and exact-fusion recipes retain their existing reuse
where their inputs/outputs did not change. Do not invalidate every CAD artifact
using the framework commit hash or change parameter-derived filenames. Source
metadata equality, scoped content verification, strong artifact observation,
atomic sidecars and sealed-generation checks all continue to apply.

### 6. Proof precedes acceptance

Before implementation, capture a small red regression on the integrated base:
an imported-mesh fusion with the OpenSCAD resolver blocked, and native export
with SCAD presentation patched to fail. Keep genuine SCAD leaves as positive
controls. Capture old geometry using OpenSCAD while it is available, under
separate evidence directories, before replacing the producer.

Required fusion comparisons: overlapping, contained, identical, disjoint,
face-touching, edge-touching and nearly coincident solids; transformed and
nested fusions; a curved mixed exact/faceted case; invalid/non-manifold inputs.
Use analytic volumes/bounds for elementary fixtures, old/new symmetric
difference and surface distances for mesh equivalence, and body counts,
orientation and engine status to expose topology changes. Set fixture-specific
tolerances from size/tessellation before examining candidate results; do not
use only volume equality or raise tolerances after a failure. Differences in
previously accepted real geometry require pilot review, not a green test
manufactured from the candidate's output.

Cover every built-in adapter, an actual JSCAD subprocess fixture (a mock alone
is insufficient), a legacy overridden adapter, exact-only runs with neither
OpenSCAD nor Manifold reachable, warm skips, stale sources, recipe migration,
failed producers, source changes during work, atomic publication and repeated
SCAD output stability. Verify SCAD output in OpenSCAD and the native export in
the unchanged browser viewer; compare motion and flexible coordinates using
the first cycle's independent numeric parity checks.

Repeat complete Curta export with warm and fresh geometry directories. Record
exact framework/project/viewer identities, installed tools, source checksums,
artifact inventory, engine invocation counts, elapsed time, output size,
actual aggregate peak memory and swap. Keep the previous 8,000,000,000-byte
limit as a safety ceiling, not a hardware claim or success metric. Report the
measured cost beside the first cycle, distinguishing changed geometry/cache
recipes from neutral traversal savings. Inspect whole-machine and spring
poses. Neither performance nor mechanical correctness is presumed in advance.

### 7. ADR disposition after proof

If ratified and confirmed by implementation, extract decisions for neutral
preparation/SCAD compatibility, faceted fusion, and recipe-aware currency.
Update `docs/architecture.md` and the ADR index at completion, not now.

- Partially supersede ADR-002's mandatory SCAD lifecycle and ADR-004's
  mandatory adapter SCAD contract; retain their framework-owned lifecycle
  and multi-backend intent.
- Amend ADR-045/046's faceted-fusion route and ADR-052's requiring set; retain
  exact fusion, conditional resolution, and no silent substitution.
- Amend ADR-047's placement of exact artifact work inside `as_scad()`, not
  its common OCCT currency or distinct adapter types.
- Extend ADR-006/060/071/081 currency rules with recipe qualification; preserve
  their historical measurements and source-scope rules.
- Preserve ADR-038/084 publication/generation guarantees and ADR-086's SCAD
  last-occurrence behavior when SCAD output is requested. Preserve ADR-057
  flexible-part rules and ADR-068's optional viewer boundary.
- ADR-101 graph ownership and schema-4 publication remain unchanged.

## Risks / Trade-offs

- Different fusion engine or intermediate tessellation changes shape → the
  paired geometry gate above; stop on unexplained compatibility differences.
- Preparation/presentation split repeats simulation or loses source closure →
  phase-order, naming, source-race and repeated-binding tests before migration.
- Legacy overridden hooks are bypassed → dedicated override dispatch tests;
  legacy support is explicit and scoped, not an exception-driven fallback.
- Old caches hide the changed producer → recipe mismatch and nested-cache
  migration tests, plus fresh-geometry project validation.
- In-process mesh union raises peak memory → record descendant-inclusive peaks
  and release per-fusion temporaries; do not claim savings without measurement.
- Broad lifecycle work grows beyond this cycle → preserve viewer/packaging
  policy and return any necessary wider choice to the pilot.

## Migration Plan

After ratification: validate and commit only this plan as commit 1, prove red,
implement and validate in this bench, record confirmed decisions, synchronize
specs, archive, and create one complete implementation commit 2. Integration
into `main` needs separate pilot authority and an unchanged clean base.

Built-in project source needs no migration. Document the engine/dependency
change, possible piece-ID changes, legacy adapter bridge and supported native
adapter seam. Affected caches rebuild automatically under the new recipe;
there is no user-wide cache deletion. Do not promise cross-version reuse on
rollback: use a separate build directory when testing the old release again
so an older reader cannot accept new engine artifacts under its weaker rules.

## Open Questions

No viewer-removal decision is requested here. Ratification must specifically
accept direct Manifold faceted fusion and its stated compatibility/proof gate.
Whether all current project meshes meet that gate is an implementation
question, not a settled fact. Failure of that gate returns the engine choice
or narrower cycle scope to the pilot before proceeding.

## Proposal validation

At proposal handoff, all four OpenSpec artifact groups exist and
`openspec validate --all --strict` passes all 32 items (31 baseline specs and
this change). The new branch still has zero commits above the integrated base;
only this unratified change directory is untracked. No implementation or
baseline specification was changed.

Post-integration smoke validation ran against that same framework content in
the new bench: `PYTHONPATH=$PWD` with the workspace venv, pytest over
`tests/test_expression_graphs.py`, `tests/test_expressions.py` and
`tests/test_openscad_dependency.py`: 70 passed, 24 subtests passed, 4 warnings
in 6.67 seconds. This checks the integrated first cycle, not the proposed
broker removal; the latter's red/green work has not started.
