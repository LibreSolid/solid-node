# ADR-044: Derived exact-geometry capability

**Status:** Accepted

**Date:** 2026-08-13

**Change:** `exact-brep-geometry`

**Depends on:**
- [ADR-004: Multi-CAD Backend Adapter Pattern](ADR-004-multi-cad-backend-adapter-pattern.md)
- [ADR-006: Mtime-Based STL Caching Strategy](ADR-006-mtime-based-stl-caching-strategy.md)
- [ADR-028: Cached Base Meshes and Single-Matrix World Composition](ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)

## Context

Every geometric assertion discarded the representation that produced a
CadQuery model and answered from its STL. Curved surfaces tessellate to
chords, so a nominally exact d=10 shaft in a d=10 bore reported
`0.12080618894740745 mm³` of interference after a 7° relative rotation. The
inverse error also occurred: two r=5 cylinders with a real `0.001 mm` radial
overlap passed when their inscribed facet phases did not meet.

CadQuery and OCCT are already hard dependencies. The missing architectural
fact was not another backend, but whether a node can preserve exact geometry
through the framework and let a consumer choose it without inventing a second
placement model.

## Decision

Every node exposes a read-only `exact` capability. It is derived from the
representation, never declared by a project:

- `CadQueryNode` is exact; the Solid2, OpenSCAD and JSCAD adapters are not.
- An internal node is exact only when every child is exact. Reading the
  property before children are linked raises, avoiding vacuous truth over the
  empty default collection.
- Exact nodes expose `shape()` in their own local frame. Consumers place that
  shape with the existing composed 4×4 matrices, so exact and faceted paths
  share ADR-028's kinematics rather than maintaining parallel transform
  semantics.

An exact rigid node persists its unplaced shape as a private `.brep` beside
its `.stl`. BREP currency uses ADR-006's mtime equality, and the in-memory
shape cache keys on `(path, mtime)` with stale-entry eviction. Viewer and
export documents continue to name only STL models.

Intersection-volume and connectivity assertions use OCCT whenever both
operands are exact. A Boolean that does not complete raises naming the
operation and pair; it never silently substitutes a mesh verdict. Mixed and
faceted pairs retain the Manifold/trimesh paths. The existing conservative
AABB broad phase remains ahead of either representation.

## Alternatives rejected

- **Project-declared exactness:** a faceted descendant could silently poison
  an exact claim.
- **Re-run the CadQuery backend on demand:** assertion cost and behavior would
  depend on live project execution instead of a current build artifact.
- **Implement OCCT-specific operation composition:** this would create a
  second kinematic truth beside ADR-028.
- **Fall back after a kernel failure:** the hardest geometry would receive the
  least trustworthy verdict while appearing exact to the caller.

## Consequences

- Nominal boundary contact produces no OCCT solid and is exactly empty;
  subfacet positive-volume interference is visible.
- `volume_epsilon` has no role on an exact comparison. Calls containing only
  exact comparisons warn and ignore it; a mixed call keeps it live for its
  faceted comparisons.
- Existing exact projects rebuild once to populate BREP artifacts. BREP is
  private build state and does not change the published document schema.
- On `v8-engine`, the full exact all-leaf adjacency sweep measured
  14.34–14.53 s per instant versus the 6.15 s faceted baseline. The retained
  broad phase bounds the cost to candidate pairs.
- ADR-004's accepted loss of CadQuery BREP features is partially addressed:
  exact geometry now serves composition and assertions, while faceted
  backends and general delivery still require OpenSCAD.

## Evidence

- `tests/test_exact_geometry.py` covers derivation, local shape framing,
  persistence and eviction, exact/faceted routing, kernel failure, broad-phase
  ordering, connectivity and epsilon behavior.
- Meta fixtures `exact_tight_fit` and `exact_subfacet_interference` prove both
  directions against the real build and test runner.
- `v8-engine` passed 31/31 tests; `snowman` passed 7/7; the Solid2
  `snowman-3` passed 3/3 with no BREP artifacts and OpenSCAD still invoked.

## References

- `solid_node/exact.py`
- `solid_node/node/base.py`, `internal.py`, `adapters/cadquery.py`
- `solid_node/test.py`
- OpenSpec archive `exact-brep-geometry`
