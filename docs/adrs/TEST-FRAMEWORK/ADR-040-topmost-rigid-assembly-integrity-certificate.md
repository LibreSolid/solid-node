# ADR-040: Topmost-Rigid Assembly Integrity Certificate

**Status:** Accepted
**Date:** 2026-08-10
**Depends on:**
- [ADR-003: Rigid vs Non-Rigid Node Distinction](../NODE/ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-011: Animation Testing Decorators](./ADR-011-animation-testing-decorators.md)
- [ADR-029: Manifold Cache and AABB Broad-Phase](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)
- [ADR-039: Solid Integrity at the Topmost Rigid Node](../NODE/ADR-039-solid-integrity-at-the-topmost-rigid-node.md)

**Supersedes in part:**
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md) — its all-leaf adjacency sweep remains available but is deprecated for new whole-assembly tests

## Context

New projects already declare a solid-integrity test over every topmost rigid
node. The complementary assembly question is whether those printed solids
occupy the same material volume after assembly. The existing
`assertNoPairwiseIntersections` answers a different and poorly scaling
question: it visits every pair of leaves, including ingredients inside a rigid
fusion, and exposes a volume epsilon that can hide production interference.

For closed solids, `sum(volume(parts)) - volume(union(parts))` is zero exactly
when no region of positive volume belongs to more than one part. This gives an
order-independent global certificate. Exact floating-point equality is not
sound, however: transformed separated solids can differ by a few ulps, and a
certificate alone does not name the offending parts.

## Decision

Add `TestCase.assertNoSolidInterference(node)` and scaffold it beside
`assertNoDisconnectedSolids(node)` as an ordinary second test.

- Traverse the supplied subtree to the first rigid node on every branch and
  stop there. A leaf or fusion root therefore selects one printed solid and
  passes without accessing geometry.
- At the runner-selected keyframe, lazily place cached Manifolds with their
  freshly composed world matrices. Stably sum their Manifold volumes and
  compare that value with one direct Manifold batch union. Do not round-trip
  through Trimesh or mix volume sources.
- Build conservative world AABBs once and use sweep-and-prune to emit only
  overlapping-box candidates. Exact Manifold intersection of those candidates
  names the first positive-volume offending pair.
- Empty and exactly zero-volume intersections pass. Every positive candidate
  volume fails. There is no public overlap epsilon.
- A private scale-aware uncertainty bound classifies aggregate arithmetic but
  is never an acceptance threshold: candidate verification always runs, and a
  clearly inconsistent unreconciled certificate fails.
- Preserve `assertNoPairwiseIntersections(node, volume_epsilon=0.0)` unchanged
  except for a caller-directed `DeprecationWarning`. Do not alias it to the new
  topmost-rigid semantics.

The assertion owns neither animation scheduling nor manufacturing allowance.
Projects use `@testing_instant`/`@testing_steps` for motion. Required running
clearance belongs in geometry and pair-specific length-based contracts; a
permitted overlap volume is not a production margin.

## Consequences

- A single root-level test covers nested assembly growth while the companion
  solid-integrity test continues to catch disconnected geometry within each
  printed part.
- Sparse candidate work is output-sensitive rather than an unconditional
  `N*(N-1)/2` Python sweep. The batch union still depends on total triangle and
  Boolean complexity, and dense AABBs retain a quadratic candidate worst case.
- Warm-cache measurements on separated 12-triangle boxes from 16 to 128 parts
  grew from 0.624 ms to 4.435 ms, versus 6.368 ms to 451.253 ms for the
  deprecated sweep. On 320-triangle icospheres the new path grew from 2.257 ms
  to 10.875 ms, versus 6.659 ms to 445.972 ms. Conversely, with an offending
  pair first, the deprecated method failed in 0.170–0.635 ms while the global
  certificate took 1.627–23.484 ms. These are bounded observations, not a
  universal complexity guarantee.
- The computation stays in Manifold's CPU path; solid-node performs no GPU
  upload or GPU Boolean.
- Exact nominal contact is allowed, but functional clearance is not inferred.
  Makers must model production margins where separation is required.

## Evidence

- Unit coverage in `tests/test_assembly_integrity.py` proves traversal,
  world-keyframe placement, same-kernel batch union, uncertainty behavior,
  contact/positive-volume semantics, diagnostics, and sparse candidate work.
- Meta fixtures `assembly_integrity_nested` (green),
  `assembly_integrity_contact` (green), and `assembly_integrity_animated`
  (deliberately red) exercise the real CLI, STL builder, runner instants,
  failure output, and fail-fast behavior.
- Scaffold acceptance builds a generated leaf project and reports exactly two
  passing tests.
- Measurements and methodology are recorded in
  `docs/performance-improvement.md`.

## References

- `solid_node/test.py`
- `solid_node/manager/templates/project/test.py`
- `tests/test_assembly_integrity.py`
- `tests/test_meta.py`
- OpenSpec change `default-assembly-integrity-test`
