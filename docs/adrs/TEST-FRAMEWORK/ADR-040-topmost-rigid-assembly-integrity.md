# ADR-040: Topmost-Rigid Assembly Integrity

**Status:** Accepted
**Date:** 2026-08-10
**Revised:** 2026-08-11 — the whole-assembly volume certificate was removed
before release and is recorded below as a rejected alternative. One moving
decision on one topic, revised in place rather than superseded.
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

Positive-volume interference means material shared by some two solids. Any such
pair has overlapping conservative world bounds, so a *complete* broad phase
reduces the whole-assembly question to the pairs it emits — including triple
overlap and full containment, which are not special cases but consequences of
the same statement. This makes a spatial index sufficient on its own, provided
its completeness is established.

## Decision

Add `TestCase.assertNoSolidInterference(node)` and scaffold it beside
`assertNoDisconnectedSolids(node)` as an ordinary second test.

- Traverse the supplied subtree to the first rigid node on every branch and
  stop there. A leaf or fusion root therefore selects one printed solid and
  passes without accessing geometry.
- At the runner-selected keyframe, lazily place cached Manifolds with their
  freshly composed world matrices.
- Build conservative world AABBs once and use sweep-and-prune to emit only
  overlapping-box candidates. Exact Manifold intersection of those candidates
  names the first positive-volume offending pair. This spatial path is the
  sole verification path; no aggregate volume, union, or other whole-assembly
  measurement is computed.
- Empty and exactly zero-volume intersections pass. Every positive candidate
  volume fails. There is no public overlap epsilon and no private numerical
  tolerance: the assertion reads `is_empty()` and one intersection volume
  directly from the kernel, with no large-magnitude subtraction to classify.
- Broad-phase completeness — for any two placed solids whose exact
  intersection is non-empty, the index emits that pair — is a framework
  obligation proved by framework tests, not re-checked at runtime inside a
  project's assertion.
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
- Candidate work is output-sensitive rather than an unconditional
  `N*(N-1)/2` Python sweep, and nothing in the assertion is proportional to the
  assembly's total triangle count. Dense AABBs retain a quadratic candidate
  worst case, and an individual candidate boolean over intricate geometry is
  still paid in full.
- Warm-cache measurements on separated parts, 16 to 128 of them: 0.365 ms to
  2.859 ms on 12-triangle boxes, and 0.439 ms to 2.987 ms on 320-triangle
  icospheres, versus 5.273 ms to 355.793 ms for the deprecated sweep. With an
  offending pair first, the assertion localizes it in 0.911–3.589 ms; the
  deprecated method's early exit remains faster in that specific case
  (0.158–0.561 ms). These are bounded observations, not a universal complexity
  guarantee.
- Holding part count at 125 and raising per-part detail sixteenfold
  (40 000 to 640 000 triangles) leaves the assertion at 6.0 ms. Cost tracks
  interacting pairs, not model size.
- The computation stays in Manifold's CPU path; solid-node performs no GPU
  upload or GPU Boolean.
- Exact nominal contact is allowed, but functional clearance is not inferred.
  Makers must model production margins where separation is required.
- Correctness now rests entirely on broad-phase completeness. That is a
  deliberate concentration of risk onto a small, enumerable, separately proved
  component rather than a per-run cross-check.

## Alternatives rejected

### A whole-assembly batch-union volume certificate

Originally accepted in this ADR and removed before release. For closed solids,
`sum(volume(parts)) - volume(union(parts))` is zero exactly when no region of
positive volume belongs to more than one part, giving an order-independent
global certificate. Because exact float equality is unsound — transformed
separated solids differ by a few ulps — it carried a private scale-aware
uncertainty bound, and because it could not name an offending pair, the spatial
path ran regardless. Its sole function was to catch a hypothetical omission by
the broad phase.

Rejected on measurement. It cost more than the entire assertion it guarded, and
its cost was proportional to the assembly's total triangle count on every
passing run: at 125 parts, raising detail from 40 000 to 640 000 total
triangles took the removed operation from 14.0 ms to 236.5 ms while the
surviving path stayed at 6.0 ms. Every project paid that, on every run, to
re-verify roughly forty lines of framework interval arithmetic that do not
change between runs. Proving completeness once, in the framework's own suite
and against deliberately broken implementations, is both cheaper and stronger
evidence: the certificate could only observe an omission after the fact, on
whichever assembly a project happened to run, without identifying it.

Retaining it behind an opt-in parameter was also rejected: a public flag whose
only meaning is "distrust the framework" would go untested in practice and
invites projects to reason about which mode is authoritative.

### A seeded random-assembly generator for completeness

Considered as the replacement evidence and rejected. The defect space of the
culling predicate is about four equivalence classes — a reversed comparison, a
wrong axis index, an inverted strict/non-strict, an off-by-one in the
active-list prune — which can be enumerated directly rather than searched for
stochastically. A generator would also need seed capture, a replay override,
failure shrinking and bit-exact case dumping, all existing only to convert a
random failure back into the hardcoded case a boundary table already holds; and
seed replay silently stops reproducing a failure as soon as the generator's
draw sequence changes. A finite exhaustive lattice is complete over its
offsets rather than sampling them, and reproduces by construction. Hypothesis
was rejected for the same reason plus the new development dependency.

## Evidence

- Unit coverage in `tests/test_assembly_integrity.py` proves traversal,
  world-keyframe placement, contact/positive-volume semantics, diagnostics,
  sparse candidate work, triple overlap, containment, and that no
  whole-assembly union is computed.
- Broad-phase completeness in `tests/test_broad_phase_culling.py`: a named
  boundary table, a 64-placement exhaustive lattice checked against brute-force
  `itertools.combinations`, `_world_bounds` conservativeness under rotation,
  and a differential check over the module's existing fixtures. The lattice
  additionally pins the index against over-emission by comparing with an
  independently written box-overlap predicate.
- That coverage was verified against four deliberately broken implementations:
  a non-strict `_boxes_disjoint`, an untransformed `_world_bounds`, a
  `_boxes_disjoint` ignoring the Z axis, and an off-by-one active-list prune.
  All four are caught. Note which layer catches what: the lattice is
  load-bearing, the axis-dropping mutation is caught only by the
  over-emission comparison (it is conservative, so it breaks efficiency rather
  than correctness), and the boundary table catches none of the four — it
  earns its place as named regression documentation of the conditions, not as
  the proof.
- Meta fixtures `assembly_integrity_nested` (green),
  `assembly_integrity_contact` (green), `assembly_integrity_animated`
  (deliberately red), `assembly_integrity_triple` (deliberately red), and
  `assembly_integrity_contained` (deliberately red) exercise the real CLI, STL
  builder, runner instants, failure output, and fail-fast behavior.
- Scaffold acceptance builds a generated leaf project and reports exactly two
  passing tests.
- Measurements and methodology are recorded in
  `docs/performance-improvement.md`.

## References

- `solid_node/test.py`
- `solid_node/manager/templates/project/test.py`
- `tests/test_assembly_integrity.py`
- `tests/test_broad_phase_culling.py`
- `tests/test_meta.py`
- OpenSpec changes `default-assembly-integrity-test`,
  `drop-assembly-volume-certificate`
