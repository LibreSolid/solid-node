## Context

`assertNoSolidInterference` was ratified in `default-assembly-integrity-test`
(2026-08-10) and recorded as ADR-040. It runs two independent paths:

1. **Spatial** — one conservative world AABB per topmost rigid solid,
   sweep-and-prune over those boxes, and an exact Manifold intersection on each
   emitted candidate. This is the path that produces the verdict and names the
   offending pair.
2. **Certificate** — `sum(volume(placed_i)) - volume(batch_union(placed))`,
   with a private scale-aware uncertainty bound, failing if a clearly positive
   deficit is never reconciled to a candidate pair.

The certificate was adopted deliberately: *"The chosen two-path design favors a
root-level safety net over eliminating the batch union."* Its only function is
to catch a hypothetical omission by the broad phase — it cannot localize a
fault, so the spatial path runs regardless.

Measurement now shows the net costs more than the whole assertion. Warm-cache
`manifold3d` timings on a clean 5×5×5 lattice of 125 spheres, 8192 triangles
each (1.02M triangles, 300 sweep-and-prune candidate pairs, all disjoint):

| path | time |
| --- | --- |
| batch union + both volume readings + surface areas | 273 ms |
| all 300 candidate pairs through exact `^` and `is_empty()` | 2 ms |

Two structural facts behind those numbers:

- `manifold3d` is lazily evaluated. `Manifold.batch_boolean` returns
  immediately; the cost lands on the first `volume()`/`surface_area()` read,
  and it is proportional to total assembly triangle count.
- The same laziness plus Manifold's internal collider makes an empty pairwise
  intersection nearly free. A shaft-in-bore pair (heavily overlapping AABBs,
  disjoint geometry, ~1500 triangles) resolves `(a ^ b).is_empty()` in 0.23 ms.

So the certificate is a fixed tax proportional to model size, on the pass path,
for a property that does not change between runs. The spatial path is
output-sensitive and already behaves like a game engine's broad phase plus
narrow phase.

## Goals / Non-Goals

**Goals:**

- Make the spatial index the sole verification path for
  `assertNoSolidInterference`.
- Preserve every public verdict, message, and scope decision from ADR-040
  exactly.
- Move broad-phase completeness from a runtime cross-check to framework
  property tests that are stronger than the cross-check they replace.
- Revise ADR-040 in place, recording the certificate as a rejected alternative
  with its measurements.

**Non-Goals:**

- Changing selection (topmost rigid nodes), keyframe semantics, the
  contact-passes rule, or the absence of a public overlap epsilon.
- Introducing a length-based clearance contract, a collision library
  (FCL/GJK/SAT), convex decomposition, an `rtree` dependency, or GPU work.
- Touching `assertNoDisconnectedSolids` or the deprecated
  `assertNoPairwiseIntersections`.
- Optimising the narrow phase. At 0.23 ms per hard candidate it is not the
  bottleneck.

## Decisions

### The spatial index is the sole verification path

`assertNoSolidInterference` becomes: select topmost rigid nodes; return if
fewer than two; build one conservative world bound per solid; sweep-and-prune;
for each emitted pair take the exact placed Manifold intersection and fail on
the first positive volume. Nothing else.

The removed aggregate cannot contribute a verdict the pairwise path misses,
*provided the index is complete*. Positive-volume interference is by definition
shared material between some two solids, and any such pair has overlapping
conservative bounds. Triple overlap and full containment — the two cases the
certificate was intuitively protecting — both imply a pair with positive shared
volume, and both already have behavioral coverage through the public assertion.
Completeness therefore carries the whole argument, which is why it moves to
tests rather than disappearing.

*Alternative — keep the certificate behind an opt-in flag
(`certify=True`).* Rejected. It adds a public parameter whose only meaning is
"distrust the framework", it would go untested in practice, and it invites
projects to reason about which mode is authoritative. If the index is proven,
there is nothing to opt into.

*Alternative — keep the certificate but compute it lazily, only when the sweep
finds nothing.* Rejected: that is exactly the common case. A clean assembly is
the normal outcome of every passing test run, so laziness saves nothing.

*Alternative — keep the certificate as ratified.* Rejected on the measurements
above: 273 ms against 2 ms, growing with total triangle count, charged to every
project on every run, to re-verify forty lines of framework arithmetic that do
not change between runs.

### Numerical uncertainty leaves with the aggregate

The private uncertainty bound existed to classify floating-point accumulation
in `sum(volume) - volume(union)` — a subtraction of two large, nearly equal
quantities. The pairwise path has no such subtraction: it reads `is_empty()`
and, when non-empty, one intersection volume, each a direct kernel measurement.
Verdict semantics for those readings were settled by ADR-029 and ADR-040 and
are unchanged. Carrying a tolerance forward would introduce a de-facto overlap
epsilon that the ratified contract explicitly refuses.

The "certificate is inconsistent" failure and the non-finite-deficit failure go
with it. Neither can occur without an aggregate.

### Broad-phase completeness is proved by enumerated cases, not by search

The obligation is: for any two solids whose exact intersection is non-empty,
`_bounds_candidates` emits that pair. It rests on two properties:

- `_world_bounds` is conservative — the AABB of the eight transformed corners
  of the local bounding box encloses the placed geometry under any affine
  world matrix, and is a superset (not equal) under rotation. This is a
  theorem, not an empirical question: the local box contains the geometry, and
  an affine map carries the convex hull of the corners onto the convex hull of
  their images. Testing cannot make it more true; it can only detect the
  implementation drifting away from it.
- `_bounds_candidates` emits every overlapping-box pair — `_boxes_disjoint`
  uses strict `<`, so touching boxes stay candidates, and the sweep's
  active-list pruning on the X interval discards only boxes that provably
  cannot reach the current one.

The realistic defect space for that second property is small and enumerable: a
reversed comparison, a wrong axis index, a strict/non-strict inequality
inverted, or an off-by-one in the active-list prune. Coverage is therefore
three deterministic layers, chosen to cover those classes directly:

1. A named boundary table over placed pairs: fully separated; face, edge, and
   vertex contact; positive overlap; full containment; coincident bounds;
   separation on exactly one axis (each axis in turn); zero-extent bounds; and
   rotated placement. Roughly ten cases, each named for the condition it pins.
2. A small exhaustive lattice — unit boxes at half-integer offsets over a
   bounded grid — checked pairwise against brute-force `itertools.combinations`.
   Being finite and complete over those offsets, it covers the equivalence
   classes rather than sampling them, and runs in milliseconds.
3. A differential check over the assemblies the existing tests already build:
   the emitted candidate set contains every pair whose exact intersection is
   non-empty. This costs no new geometry and widens automatically as the suite
   grows.

All three assert containment, not equality: the index may emit extra pairs —
that is what "conservative" means — and asserting equality would forbid it.

*Alternative — a seeded random-assembly generator with failure shrinking and
case dumping.* Rejected. It searches, stochastically and slowly, a defect space
of about four equivalence classes that can simply be written down, and it
carries real cost of its own: seed capture, an env-var replay override, a
shrinker, and a bit-exact literal dump — machinery existing only to convert a
random failure back into the hardcoded case the boundary table already holds.
Seed replay is also fragile: it reproduces a failure only while the generator's
draw sequence is byte-identical, so it breaks silently under refactoring. A
finite exhaustive lattice is the stronger claim and is reproducible by
construction.

*Alternative — a Hypothesis-based property test.* Rejected for the same reason,
plus `hypothesis` is not a current framework test dependency (it is absent from
`requirements_dev.txt` and from the workspace venv) and this change should not
add one.

### Two end-to-end fixtures cover the geometries the certificate motivated

The certificate's intuitive appeal was triple overlap and full containment —
arrangements where a naive global comparison feels safer than pairwise work. In
fact both imply a pair with positive shared volume, so the spatial path catches
them, but the claim deserves evidence at the level a project actually runs.

Alongside the unit coverage, add two meta fixtures beside the existing
`assembly_integrity_*` set: one where three topmost rigid solids share a common
region, and one where a smaller solid lies wholly inside a larger one with no
surface crossing. Both are deliberately red, exercising the real CLI, STL
builder, runner instant, and failure text. Containment is the sharper of the
two: it is the case where surface-crossing intuition fails, and it must be
shown failing through the public assertion with both solids named.

### ADR-040 is revised, not superseded

ADR-040 is one day old and this reverses a decision inside it on the same
topic, before any release. Superseding would leave two accepted ADRs describing
one assertion and imply an architectural direction change that did not happen.
The revision retitles it (the assertion is no longer a "certificate"), rewrites
Decision and Consequences, adds an **Alternatives rejected** section carrying
the batch-union certificate with its measurements and its original rationale,
notes the revision date, and updates `docs/adrs/README.md`. Its
`Supersedes in part` relationship to ADR-025 and its dependencies are unchanged.

The superseded-ADR mechanism remains correct for a decision that has shipped or
for a genuinely new direction. Neither applies here.

## Risks / Trade-offs

- **[Removing the runtime net leaves a broad-phase bug undetected until it
  causes a missed interference in a real project]** → The enumerated coverage
  is the replacement and must land in the same change, red-first: it is written
  to fail against a deliberately broken `_boxes_disjoint` (non-strict
  comparison) and a deliberately non-conservative `_world_bounds` (local box,
  no transform) before the real implementation turns it green. Both mutations
  must be shown failing, since either alone would leave half the obligation
  unproved.
- **[Enumerated cases cover only the defect classes their author foresaw]** →
  Accepted, and stated plainly rather than papered over with sampling. The
  exhaustive lattice is finite and complete over its offsets, which bounds the
  gap for the geometric predicate; the residual risk is a defect class outside
  the lattice's shape, which random search over the same generator shapes would
  not have found either.
- **[Behavioral coverage for triple overlap and containment currently asserts
  on `_assembly_volume_certificate` directly and would be deleted with it]** →
  Do not delete the cases; rewrite them against the public assertion, which is
  where they should have been. Coverage of those geometries must not decrease.
- **[The measurements are synthetic lattices, not a real project assembly]** →
  Reproduce them during apply with the methodology already recorded in
  `docs/performance-improvement.md`, including the deprecated-sweep comparison
  ADR-040 used, and record both the clean-pass and first-offending-pair cases.
  Report them as bounded observations, not a complexity guarantee.
- **[Dense assemblies where every bound overlaps every other remain quadratic
  in candidates]** → Unchanged by this proposal and still true; the removal
  only takes away a cost that was quadratic-independent. Say so plainly in the
  ADR rather than implying the assertion is now cheap in all cases.

## Migration Plan

No project migration. `assertNoSolidInterference(node)` keeps its signature and
its verdicts, so generated and hand-written project tests are unaffected. The
change is internal to the framework and to the framework's own test suite.

Rollback is reverting the change: the certificate helper and its tests are
restored from history with no project-side data or API to undo.

## Open Questions

None for ratification. The exact membership of the boundary table and the
lattice's extent are implementation details constrained by the red-first
requirement above.
