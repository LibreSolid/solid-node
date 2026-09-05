# ADR-070: Relative Placement as the Identity of an Intersection Question

**Status:** Accepted
**Date:** 2026-09-05
**Extends:**
- [ADR-029: Manifold Cache and AABB Broad Phase for Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)

**Related to:**
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)
- [ADR-040: Topmost-Rigid Assembly Integrity](./ADR-040-topmost-rigid-assembly-integrity.md)

## Context and Problem Statement

ADR-029 removed the redundant *construction* of geometry: one Manifold per
`(stl_file, mtime)`, one AABB broad phase before any boolean. It did not
address the redundant *asking*. A suite that sweeps a mechanism through
instants, or perturbs a fit in both directions at several magnitudes, asks the
kernel the same geometric question many times.

Measured on the v8-engine suite: 30 227 keyed intersection evaluations, 99% of
the suite's time inside them.

The question is what makes two of those evaluations the same question. Two
parts in the same relative pose share the same intersection, whatever world
frame the pair sits in — a whole subassembly rotated about the crank does not
change how its own members meet. So the identity cannot be the world matrices;
it has to be their relation.

## Decision Drivers

- The memo must never change a verdict. These assertions are manufacturing and
  safety contracts; a cache that answers "close enough" is worse than no cache.
- ADR-025 and ADR-029 rest on a flush abutment coming back **non-empty with
  exactly 0.0 mm³**. Zero volume must not be folded into emptiness anywhere,
  the cache included.
- Geometry changes during a run — a rebuilt part, a flexible leaf at a new
  binding. A stale entry is a wrong answer, not a slow one.

## Considered Options

1. **Key on both geometry identities, the evaluation path, and the exact bytes
   of `inv(M1) @ M2`** (chosen)
2. Key on the two world matrices directly
3. Key on the relative matrix rounded to a tolerance
4. Key on part names and placement, as the spike's census did

## Decision Outcome

Chosen: **exact relative placement.**

The key is `(identity₁, identity₂, path, bytes(inv(M₁) @ M₂))`, where each
identity is the geometry's `(file, mtime)` and `path` is `'exact'` or
`'faceted'`. A node with no file identity — a `.mesh`-only test double — yields
no key and is never cached. Entries are evicted when a geometry identity
changes, on the same discipline as ADR-029's Manifold cache. The exact and
faceted paths never serve one another, because they answer to different
tolerances.

### Why exact bytes and not a tolerance (option 3)

A tolerance on the key is a tolerance on the assertions. Rounding decides that
two placements differing by less than ε are the same question — which is
precisely the judgement `volume_epsilon` exists to let a *project* make, per
contract, in millimetres of material. Making it globally and invisibly in a
cache key would decide it for every project at once. A placement difference too
small to see is a different key, and costs exactly what it costs today.

### Why not the world matrices (option 2)

Correct but far weaker: it misses every pair carried together by a shared
parent, which is most of what a swept mechanism does.

### Why not part names (option 4)

The spike's census keyed this way and predicted a 54% repeat rate. It was
wrong, and instructively so: a flexible part's geometry is a function of the
driver binding, so two instants at the same relative placement are **not** the
same question. Name-keying counted them as repeats. Measured under the real
key, the rate is 21%.

## Consequences

- 21% of the v8 suite's keyed evaluations are served from the memo. The suite
  falls 1687 s → 1622.8 s; the framework's own suite is unaffected by this part.
- The estimate that justified the work was generous by more than a factor of
  two. The key was **not** loosened in response — the finding was returned to
  the pilot instead. This is recorded because the temptation to widen a key
  until it hits its forecast is exactly how a correct cache becomes a wrong one.
- Flexible parts are uncacheable by construction and stay that way. They carry
  1499 s of the remaining suite: ~50 ms evaluating the part and ~380 ms in the
  exact kernel, per comparison. That cost belongs to the choice of kernel, not
  to the memo, and is the subject of its own pending decision (see
  `docs/performance-improvement.md`).
- Exact placements and bounding boxes are cached alongside, per
  `(shape identity, matrix bytes)`. The shape cannot be the key: `cq.Shape.__eq__`
  is `isSame()`, which ignores location, so a shape and a differently placed
  copy compare equal. The lookup goes through `id(shape)`, which is sound only
  because `_shape_cache` holds the shape alive for exactly as long as the entry.
- The cache is per-run and bounded by insertion order. It is not a build cache:
  nothing survives the process.

## References

- `solid_node/test.py` — `_verdict_key`, `_record_key`, `_memoized`
- `solid_node/exact.py` — `shape_identity`, `_placement_cache`, `_bounds_cache`
- `tests/test_intersection_memo.py` — scenario tests, flush contact included
- `spike/interference/FINDINGS.md` — findings 4 and 5
- OpenSpec change `fast-test-feedback`, capability `test-framework`
