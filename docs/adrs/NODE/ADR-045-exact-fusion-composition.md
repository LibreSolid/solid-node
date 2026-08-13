# ADR-045: Exact fusion composition

**Status:** Accepted

**Date:** 2026-08-13

**Change:** `exact-brep-geometry`

**Depends on:**
- [ADR-003: Rigid vs Non-Rigid Node Distinction](ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-044: Derived Exact-Geometry Capability](ADR-044-derived-exact-geometry-capability.md)
- [ADR-043: Content-derived Printed-Piece Identity](../EXPORT/ADR-043-content-derived-printed-piece-identity.md)

## Context

A `FusionNode` promises one printed solid but historically fulfilled that
promise by importing child STLs into OpenSCAD and asking CGAL to union the
meshes. Once its children preserve BREP geometry, that round trip is both less
precise and more machinery than composing the shapes in OCCT.

The fusion's produced STL is also printed-piece identity. Changing the
composition kernel therefore changes a durable downstream identity even when
the physical result is equivalent.

## Decision

When every descendant is exact, `FusionNode.shape()` places each child's local
shape in the fusion frame using the existing solid-local matrices and fuses
the shapes in OCCT. Its STL is tessellated synchronously from that fused shape
at CadQuery's existing leaf deflection; it does not launch OpenSCAD or raise
`StlRenderStart`. Its BREP and STL receive the same source mtime.

A fusion containing any faceted descendant retains the OpenSCAD subprocess
protocol unchanged.

Fusion STL publication removes degenerate faces produced by tessellation.
Caller validation found that OCCT returned one valid fused solid for
`snowman`, while its STL writer added one zero-volume triangle that made a
mesh consumer report a second body. Removing that artifact preserves the
one-solid promise without changing leaf STL behavior.

## Alternatives rejected

- **Always keep OpenSCAD fusion:** discards exact topology in the middle of an
  otherwise exact subtree and preserves the facet-phase defect.
- **Compose exact children only for assertions:** makes `shape()` disagree
  with the printed artifact the fusion represents.
- **Run both kernels and compare:** doubles build work and leaves no single
  authoritative artifact when tessellations differ.
- **Treat the degenerate triangle as a caller problem:** violates the fusion's
  established one-body contract and breaks piece facts derived from the STL.

## Consequences

- Exact fusions build in process and accept coincident/overlapping BREP
  ingredients without a mesh round trip.
- Fused STL bytes and content-derived piece ids change. The validating
  `snowman` body's id changed from `21591f853132` (CGAL) to `d0a600876a4c`
  (exact fusion).
- The validating exact STL is watertight and one body. Its volume is
  `148824.06642339742 mm³` versus `148819.191868121 mm³` for CGAL; bounds are
  equivalent within the two tessellators' deflection, and face count fell from
  21,140 to 20,024.
- Faceted fusion behavior is unchanged; `snowman-3` exercised the OpenSCAD
  protocol and produced no BREP.

## Evidence

- `tests/test_exact_geometry.py` covers exact and mixed fusion protocols,
  coincident cylindrical faces, one-solid output and BREP/STL currency.
- `snowman` passed all seven project tests after the exact-fusion build and
  supplied the comparative geometry and piece-identity measurements above.
- `snowman-3` passed all three tests through the unchanged faceted path.

## References

- `solid_node/node/fusion.py`
- `solid_node/exact.py`
- OpenSpec archive `exact-brep-geometry`
