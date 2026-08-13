## Context

Every geometric question the framework answers is mediated by a triangle mesh.
For a `CadQueryNode` project the geometry kernel that produced the part —
OCCT, via `cadquery==2.5.*`, already a hard dependency — could answer exactly,
but the answer is thrown away at STL export and reconstructed approximately.

The internal node algebra is remarkably small, which is what makes an exact
path cheap: `FusionNode` unions rigid children, `AssemblyNode` places them,
and operations are only `Rotation` and `Translation`. There is no cross-node
difference or intersection anywhere in the node model. A second composition
backend therefore needs exactly two verbs — fuse and place — not a CSG engine.

Measured on the primary caller, `v8-engine`, at one instant: 119 placed
solids, 449 candidate pairs after the existing AABB broad phase; 6.15 s via
Manifold against 12.2 s via the OCCT kernel (mean 27 ms/pair), identical
verdicts, no kernel failures across all 449. Artifact economics favour the
exact path too: for one gear, native BREP is 4 ms write / 2 ms read / 165 KiB
against the STL's 112 ms / 9 ms / 469 KiB.

## Goals / Non-Goals

**Goals:**

- Answer intersection-volume and connectivity questions exactly whenever the
  compared geometry is exact, so a nominally exact fit stops registering as
  interference.
- Keep the faceted path intact and unchanged for everything else, so no
  `Solid2Node` project changes behaviour.
- Compose a fusion in the kernel that produced its ingredients, removing one
  mesh round-trip from the middle of the build.
- Persist exact geometry so no consumer re-runs the geometry backend.

**Non-Goals:**

- Removing or weakening the OpenSCAD dependency. Making it conditional on
  backend is the next cycle; here it stays required and every faceted path
  keeps using it.
- Distance and containment assertions (`assertInside`, `assertClose`,
  `assertFar`). Their weakness is vertex sampling rather than tessellation;
  `BRepExtrema` replaces them in a later cycle.
- STEP or any other delivery artifact. `.brep` here is a private build cache.
- Any project-declarable exactness. `exact` is derived, never asserted.

## Decisions

**Exactness is a derived read-only property, type-derived at the leaf and
all-children at an internal node.** The alternative — a project declaring a
node exact — would let a project claim precision it does not have, and the
first faceted leaf underneath would silently poison the composition. Deriving
it means the answer is always true of the geometry.

This composition rule is deliberately the inverse of `rigid`, which node-model
ratifies as *not* recomputed from children. The two are different kinds of
statement: rigidity is a promise about output (a fusion is one solid whatever
lies below), exactness is a capability that depends on what lies below. The
delta records that rationale so the pair does not read as an inconsistency.

**Reading `exact` on an unassembled internal node raises.** `children`
defaults to an empty collection and is only populated in
`InternalNode.as_scad` during `assemble()`, so `all(child.exact ...)` over an
empty collection is vacuously true — a `FusionNode` full of `Solid2Node`
leaves would report exact until it rendered. Since routing hangs off this
property, answering wrongly is worse than refusing to answer. `rigid` has no
equivalent hazard because it is type-derived all the way down, which is why
`FusionNode.validate` can already check `child.rigid` before any geometry
exists.

**`shape()` returns unplaced geometry; the caller composes placement using the
existing matrices.** Considered and rejected: composing an OCCT transform
chain per operation. That would create a second placement semantics alongside
`_compose_world_matrix`, and ADR-028 exists precisely to keep mesh and viewer
placement on one composition. Feeding the existing composed matrix into
`gp_Trsf.SetValues` was verified safe: over chains of 5, 20, 50 and 200
composed rotations and translations, orthonormality drift reached only
2.0e-14 and OCCT accepted every one.

**Emptiness on the exact path means "contains no solid".** Two solids meeting
on coincident faces produce a result of lower dimension — faces, no volume.
Reading emptiness as the absence of any `TopAbs_SOLID` makes contact exactly
empty with zero volume, which reproduces today's ratified rule (empty and
zero-volume boundary contact pass, positive volume fails) without an epsilon,
and without the float-noise sliver the faceted path has to tolerate.

**`volume_epsilon` warns and is ignored on the exact path rather than raising.**
Ignoring it is verdict-neutral: a real block produces a volume far above the
epsilons in use (1e-6 mm³), and flush contact produces exactly zero either
way. Raising would force churn in `v8-engine`'s dozen call sites for no
verdict change. Silence would leave a test recording a tolerance it no longer
applies. Warning drives the cleanup the machinist skill already asks for and
makes the transition visible in test output.

**A kernel failure raises and never falls back to the mesh verdict.** A
fallback would answer from the imprecise representation exactly where the
kernel found the geometry hardest — the case most likely to be a real defect —
and would report a pass that looks identical to an exact one.

**`.brep` is private to the build, spared by the sweep by kind.** Naming it in
`viewer.json` would change a versioned document schema (ADR-034) shared by the
viewer, the export and the Sphinx extension, none of which can consume a
B-rep. Sparing it by suffix, as `.scad` already is, keeps the schema still.
The cost is that superseded `.brep` files are not swept; mtime-equality
caching means a superseded one is never read, and this matches existing
`.scad` behaviour.

**A fusion tessellates its own fuse instead of shelling out.** Once `shape()`
exists and fuses — which the interference path requires anyway — tessellating
the result is a few lines and strictly less machinery than the OpenSCAD
subprocess it replaces. Splitting it into a later cycle would be artificial.
It also improves the case CGAL handles worst: fusing children on exactly
coincident faces was verified to yield one solid in 4 ms.

## Risks / Trade-offs

- **Verdicts change in both directions.** Real sub-facet interference the mesh
  path missed now fails; nominally exact fits that failed on facet phase now
  pass. → Intended, and the reason for the change. Migration is per project
  and deliberate: `v8-engine`'s tessellation workarounds and epsilons are
  retired as evidence, not silently.

- **Fused piece identities change.** Printed-piece identity is the sha256 of
  the STL bytes (ADR-043), and a fusion's triangulation now comes from OCCT
  rather than CGAL. → Correct behaviour of that capability — the artifact
  genuinely changed — but any recorded piece id for a fusion goes stale on
  first rebuild. `snowman` is the only CadQuery project with a `FusionNode`
  and is the validating caller for this.

- **OCCT booleans can fail where mesh booleans grind through.** 449/449 v8
  pairs were clean, but pathological geometry exists. → The failure contract
  makes this loud and named rather than silent, and the faceted path remains
  available to a project that needs it by construction.

- **The exact path is roughly 2× the mesh path per candidate pair**, and a
  suite multiplies that by its testing instants. → The AABB broad phase, which
  is unchanged and runs ahead of every path, is what keeps this proportional
  to interacting pairs rather than to assembly size: 7021 raw pairs reduce to
  449 on `v8-engine`. If a suite's instant count makes this bite, escalation
  (mesh first, exact only inside a derived facet-scale uncertainty band) is
  available later without changing any ratified verdict.

- **Every existing build directory re-renders once**, because an exact node's
  artifacts are not current until its `.brep` exists. → One-time, about 37 s
  for `v8-engine`'s 24 distinct shapes.

- **`exact` derived from adapter type assumes a `CadQueryNode` renders true
  B-rep geometry.** CadQuery can import an STL, which would give a faceted
  shell claiming exactness. → Narrow enough to acknowledge rather than guard
  here; the claim is about the representation the adapter normally produces.

## Migration Plan

1. Land the capability with both paths live and the faceted path untouched, so
   a `Solid2Node` project sees no change at all.
2. Rebuild `v8-engine` and `snowman` once to populate `.brep` artifacts and,
   for `snowman`, to re-derive the fused piece id.
3. Retire project-side workarounds deliberately, per project, as evidence:
   the `result.val().mesh(...)` pre-tessellation calls in `v8-engine`'s
   `piston.py` and `con_rod.py`, its `volume_epsilon` call sites, and
   `american-windmill`'s `mesh_linear_tolerance` design parameter. These are
   project decisions and are not made by this change.

Rollback is the branch: nothing outside the build directory changes shape, and
`.brep` artifacts are inert to every consumer that does not ask for them.

## Open Questions

None blocking. The deferred items — conditional OpenSCAD, `BRepExtrema`
distance assertions, STEP delivery — are scoped to their own cycles.
