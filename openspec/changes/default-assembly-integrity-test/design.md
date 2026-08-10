## Context

`assertNoPairwiseIntersections` was added in July 2026 as a leaf sweep: collect
every leaf, materialize `itertools.combinations(leaves, 2)`, then use the
shared AABB/Manifold intersection helper on each pair. AABB culling makes most
individual visits cheap, but it does not remove the quadratic number of visits.
It also predates ADR-039's topmost-rigid-node boundary and can compare rigid
ingredients that are not independent printed parts.

The explicit solid-integrity change now gives a new project one ordinary test
over that correct boundary. The complementary maintainer need is a second
ordinary test over the assembled relationship between those solids. It must be
safe to scaffold while the generated project is still a single leaf, remain
valid as the model grows into nested assemblies, and evaluate the current
testing instant using the framework's existing world-matrix semantics.

In exact arithmetic, for closed solids `S_i`,

    sum(volume(S_i)) - volume(union(S_i))

is zero exactly when no point of positive volume belongs to more than one
solid. Triple and nested overlaps cannot cancel. Measurements against the
installed Trimesh/Manifold stack also established two implementation facts:
direct Manifold batch union is substantially cheaper than Trimesh 4.4's
cascaded conversion path, while even same-kernel measurements of separated,
transformed solids can differ by a few floating-point ulps. Exact float
equality therefore cannot be the only verdict mechanism.

## Goals / Non-Goals

**Goals:**

- Give projects one root-level assertion for positive-volume interference
  among the printed solids selected from an assembly subtree.
- Scale by total mesh/candidate complexity rather than unconditionally visiting
  every pair.
- Preserve actionable failure output by naming an offending pair and its
  measured intersection volume.
- Make numerical uncertainty trigger more proof rather than excuse overlap.
- Scaffold the assembly contract beside solid integrity for every new project,
  including projects whose root is currently a leaf or fusion.
- Provide a visible compatibility migration away from the old leaf sweep.

**Non-Goals:**

- Proving a manufacturing clearance, dimensional tolerance, running fit,
  press fit, or safety margin. Those are pair-specific, length-based contracts.
- Rejecting exact zero-volume boundary contact. This assertion proves absence
  of material interference, not separation by a positive distance.
- Automatically choosing animation coverage. The runner's default instant is
  0; projects use the existing decorators to select or sweep other instants.
- Removing `assertNoPairwiseIntersections` in this release.
- Introducing GPU execution, another mesh kernel, or a new project dependency.

## Decisions

### The public unit is the topmost rigid solid

`assertNoSolidInterference(node)` calls the shared `_topmost_rigid_nodes(node)`
traversal. It stops at the first rigid node on every branch, exactly as
`assertNoDisconnectedSolids` does, but then places those solids in the world
frame. Rigid descendants of a fusion are ingredients, not independent parts,
and are never compared.

Zero or one selected solid passes without loading or unioning geometry. Thus a
leaf root and a fusion root pass the assembly assertion while the separate
solid-integrity assertion still checks their connectivity. Passing a
subassembly scopes selection to it. The test runner sets the keyframe before
the assertion; the assertion neither accepts a keyframe argument nor mutates
time, so `@testing_instant` and `@testing_steps` remain the single execution
control.

### Interference means positive shared volume

The contract rejects positive-volume overlap and permits an empty or
zero-volume intersection. Permitting boundary contact follows directly from
the volume identity and accommodates legitimate seated shoulders, hard stops,
and other nominal contact. A project that needs free motion or production
allowance must state a positive distance/play contract for the relevant pair;
an overlap-volume waiver is not a manufacturing margin.

There is no public `volume_epsilon` parameter. A volume threshold is a poor
physical allowance: equal volumes can describe a broad numerical film or a
deep, narrow penetration. Any positive candidate intersection volume reported
by the kernel fails, even when small.

### One same-kernel batch-union certificate

For each selected solid, reuse the cached local Manifold and apply its freshly
composed world matrix lazily. Sum the local Manifold volumes with stable
floating-point summation (rigid placement preserves volume), batch-union the
placed Manifolds with Manifold's N-way add operation, and read the union volume
directly from Manifold. Do not convert the result back through Trimesh and do
not mix Trimesh input volumes with a Manifold result; that introduces a known
float32 conversion discrepancy.

The volume deficit is an assembly-wide certificate independent of pair order.
It replaces neither mesh validity checks nor the solid-integrity test: cached
Manifold construction continues to reject a non-watertight STL, and a
disconnected but non-overlapping solid remains the other test's concern.

*Alternative — Trimesh `boolean.union`.* Rejected because the pinned 4.4
implementation converts meshes and performs `N-1` balanced binary operations,
then converts back before volume measurement. The installed Manifold API
already exposes batch Boolean and direct volume measurement.

### Numerical uncertainty is a branch to verification, never a pass allowance

The implementation derives a private, scale-aware uncertainty bound from the
Manifold/kernel tolerance and floating-point accumulation scale. It is not a
public parameter and has no manufacturing meaning.

- A deficit clearly above the bound establishes interference; candidate search
  runs to identify a pair. If no pair reconciles a clearly positive global
  deficit, the assertion still fails with the aggregate measurement and an
  explicit numerical-inconsistency diagnostic.
- A deficit at, below, or inconsistently on the other side of the bound is not
  accepted merely because it is small. The spatial candidate path verifies the
  potentially interacting solids before the assertion passes.

This makes a conservative bound safe: increasing it may cause more diagnostic
work, but cannot legalize overlap. The kernel still has finite geometric
precision, as every tessellated CAD calculation does; the framework does not
offer a user knob that broadens it.

*Alternative — exact `deficit == 0`.* Rejected because separated transformed
solids have demonstrated nonzero deficits of a few ulps.

*Alternative — a public volume epsilon.* Rejected because it turns numerical
uncertainty into permitted material interference and can conceal physically
different defects with the same volume.

### Spatial indexing produces candidates and diagnostics

Build each selected solid's conservative world AABB once. A sweep-and-prune
index sorts intervals and emits only boxes overlapping on all three axes,
without materializing all combinations and without adding an `rtree`
dependency. Candidate generation is `O(N log N + K)` for ordinary sparse
assemblies, where `K` is the number of overlapping box pairs; the unavoidable
worst case is quadratic when every box overlaps every other box.

Candidate pairs use the existing cached Manifold/world-transform machinery.
The first positive-volume intersection fails naming both topmost rigid solids
and the measured volume. Empty and exactly zero-volume intersections do not.
Search stops at the first offending pair. The global certificate and candidate
path are intentionally independent: the certificate prevents an indexing bug
from silently establishing a pass, while the index supplies localization and
resolves the certificate's numerical uncertainty.

*Alternative — spatial candidates without the global certificate.* Simpler and
often cheaper, but makes the acceleration structure the only proof that no
pair was omitted. The chosen two-path design favors a root-level safety net
over eliminating the batch union.

### New projects declare both contracts as ordinary tests

The companion template contains, in order:

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)

    def test_assembly_integrity(self):
        self.assertNoSolidInterference(self.node)

Both are visible, editable, deletable, counted tests. At the default testing
instant they provide useful protection from the first leaf through a complete
assembly; adding an animation decorator is an ordinary project decision.

### The old leaf sweep is deprecated, not silently redefined

`assertNoPairwiseIntersections` retains its existing leaf traversal,
`volume_epsilon` argument, and verdicts for compatibility, but emits a standard
deprecation warning with `stacklevel=2` directing callers to
`assertNoSolidInterference`. Documentation marks the semantic difference and
stops recommending the old method. It is not implemented as an alias because
changing leaves to topmost rigid solids would silently change existing tests.
Removal requires a later breaking change; this proposal does not choose its
release.

## Risks / Trade-offs

- **[Batch union can be expensive for very detailed or adversarial geometry]**
  → Reuse cached Manifolds, lazy transforms, direct batch Boolean, no Trimesh
  round trip, and add representative scaling evidence before acceptance.
- **[The certificate and candidate verification duplicate work on a clean
  assembly]** → Keep candidate work output-sensitive through sweep-and-prune;
  benchmark the combined path against the deprecated sweep and report the
  trade-off rather than claiming an asymptotic guarantee from small fixtures.
- **[Finite mesh precision can still classify marginal geometry unexpectedly]**
  → No configurable waiver; uncertainty invokes the independent path, failure
  reports quantitative evidence, and project geometry should encode real
  clearances where contact is not intended.
- **[Legitimate press fits have positive nominal interference]** → The default
  test will fail them deliberately; projects must replace or scope the generic
  contract with an explicit fit contract rather than weaken all pairs.
- **[Deprecation warnings may be filtered by Python defaults]** → Also mark the
  API and documentation plainly and test the warning using an explicit warning
  capture.

## Migration Plan

1. Add and document `assertNoSolidInterference`; scaffold it for new projects.
2. Preserve the old method with a deprecation warning and its full historical
   behavior so upgrading does not immediately break existing suites.
3. Guide existing whole-assembly callers to the new assertion, noting the
   deliberate leaf-to-topmost-rigid scope change and removal of the epsilon.
4. Consider removal only in a separately ratified breaking release. Rolling
   back this change restores the old template/API guidance without project data
   migration because generated tests are ordinary source.

## Open Questions

None for ratification. The exact private uncertainty-bound formula is an
implementation detail constrained by the required fallback behavior and must
be justified by red/green numerical fixtures during apply.
