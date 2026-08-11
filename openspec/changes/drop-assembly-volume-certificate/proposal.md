## Why

`assertNoSolidInterference` runs two independent verification paths on every
call. The spatial path — conservative world AABBs, sweep-and-prune, and an
exact Manifold intersection per surviving candidate — is the path that finds
and names interference. The global batch-union volume certificate finds
nothing the spatial path does not; ADR-040 adopted it as a safety net against a
bug in the broad phase.

That net is charged to every project on every test run, and it is the dominant
cost. Warm-cache measurement on a clean 125-solid assembly of 8192 triangles
each (1.02M triangles total, 300 sweep-and-prune candidate pairs):

| path | time |
| --- | --- |
| batch-union volume certificate | 273 ms |
| sweep-and-prune + exact narrow phase over all candidates | 2 ms |

The certificate scales with total assembly triangle count whether or not
anything is wrong, so it removes exactly the output-sensitivity the spatial
path was built for. Its cost also grows with the model, which is the direction
every project moves.

The property it guards — that the broad phase never omits a pair that actually
intersects — is a property of a small amount of conservative interval
arithmetic in `_world_bounds`, `_boxes_disjoint`, and `_bounds_candidates`.
Proving it once in the framework's own suite, differentially against
brute-force `itertools.combinations`, is stronger evidence than a runtime
comparison, and it stops charging every project to re-test framework code that
is not changing.

## What Changes

- **BREAKING (internal)** Remove the global batch-union volume certificate from
  `assertNoSolidInterference`. The sweep-and-prune broad phase plus exact
  pairwise Manifold narrow phase becomes the sole verification path.
- Remove the private numerical uncertainty bound and the
  "certificate is inconsistent" aggregate-failure diagnostic. With no aggregate
  measurement there is no aggregate arithmetic to reconcile, and the narrow
  phase's `is_empty()`/`volume()` verdicts were never derived from it.
- Delete the private helper `_assembly_volume_certificate`.
- Add deterministic framework tests proving broad-phase completeness: a named
  boundary table (separation, face/edge/vertex contact, overlap, containment,
  coincident bounds, single-axis separation, zero-extent bounds, rotation), a
  small exhaustive lattice checked against brute force, and a differential
  check over the assemblies the suite already builds. No random generation —
  every case is reproducible by construction.
- Add two deliberately-red meta fixtures for the geometries the certificate was
  motivated by: triple overlap, and full containment with no surface crossing.
- Revise ADR-040 in place rather than superseding it: retitle it away from
  "certificate", restate the decision as broad phase plus exact narrow phase,
  and record the batch-union certificate as a rejected alternative with the
  measurements above. This is a moving decision on one topic within a release,
  not a new architectural direction.
- Update `docs/performance-improvement.md` with the new measurements and
  methodology.

No public API changes. `assertNoSolidInterference(node)` keeps its signature,
its topmost-rigid selection, its keyframe semantics, its pass/fail contract
(positive shared volume fails; empty and exactly zero-volume boundary contact
pass), its absence of a public overlap epsilon, and its failure message naming
both solids and the measured intersection volume. `assertNoDisconnectedSolids`
and the deprecated `assertNoPairwiseIntersections` are untouched.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: the whole-assembly solid interference requirement drops the
  batch-union comparison, the private uncertainty bound, and the unreconciled
  aggregate-deficit failure. It keeps the topmost-rigid selection, the spatial
  index over conservative world bounds, and every pass/fail verdict, and gains
  an explicit statement that the spatial index is the sole verification path
  and must be complete.

## Impact

- `solid_node/test.py` — `assertNoSolidInterference` and the removed private
  helper. The broad-phase and narrow-phase helpers are unchanged.
- `tests/test_assembly_integrity.py` — remove certificate-specific tests
  (`test_global_deficit_stays_positive_for_triple_overlap`,
  `test_containment_produces_a_positive_global_deficit`, the uncertainty
  patching tests, and `test_unreconciled_positive_certificate_fails`). Keep and
  extend the behavioral coverage: triple overlap, containment, and contact must
  still be proved through the public assertion.
- `tests/test_broad_phase_culling.py` — new deterministic coverage for
  broad-phase completeness.
- `tests/meta_project/` and `tests/test_meta.py` — two new red fixtures for
  triple overlap and containment.
- `docs/adrs/TEST-FRAMEWORK/ADR-040-*.md` and `docs/adrs/README.md` — in-place
  revision and index entry.
- `docs/performance-improvement.md`, `docs/testing.rst` — measurements and any
  wording that describes the union comparison to users.
- No dependency, CLI, builder, viewer, or project-template change. Existing
  project test files continue to work unchanged.
