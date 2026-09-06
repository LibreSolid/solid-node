# ADR-074: The Mesh Engine Judges Its Own Input

**Status:** Accepted
**Date:** 2026-09-06
**Amends:**
- [ADR-029: Manifold Cache and AABB Broad Phase for Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)

**Related to:**
- [ADR-052: Conditional mesh-engine dependency](./ADR-052-conditional-mesh-engine-dependency.md)
- [ADR-054: Imported meshes admitted, selected and corrected explicitly](../NODE/ADR-054-imported-meshes-admitted-selected-and-corrected-explicitly.md)
- [ADR-073: The comparison kernel is a property of the test run](./ADR-073-the-comparison-kernel-is-a-property-of-the-test-run.md)

## Context and Problem Statement

ADR-029 split the per-STL cache into a bounds half that needs no mesh
engine and a Manifold half built at the first faceted comparison, and made
the bounds half the watertight gate: trimesh's `is_volume`, checked for
every selected solid, so that a bad mesh is reported by file name once and
never fails deep inside a boolean, even for a solid the broad phase culls
out of every pair.

Three seed projects of the shop found the gate stricter than the engine it
guards. OpenSCAD 2021.01 exports snap-together parts with edges shared by
four faces where two features of one part meet (snappy-reprap: fifty leaves
trimesh calls non-watertight). build123d exports walls with T-junctions
between tessellated faces (fender-bender: seven upstream STLs). Vendor STEP
solids tessellate with degenerate or unshared triangles, and touching bodies
merge into one mesh (openvmp: 21 of 67 pieces). `manifold3d` builds every
OpenSCAD and build123d mesh with `NoError` and trimesh's own volume, and
builds the vendor pieces once the zero-area triangles are gone — which the
fused-solid export already dropped and the exact leaf export did not. Each
project wrote a private engine — Manifold called directly, or pairwise OCCT
commons — to ask the question the framework refused to ask, and one lost
`assertNoSolidInterference` on an assembly of exact leaves that never reads
a mesh at all, because the gate ran on selection.

## Decision Drivers

- A verdict is reached on the part as built; nothing is repaired or hulled.
- The framework's spatial contracts must be usable on a design's own parts,
  or projects will keep private engines.
- A gate must not be stricter than the engine it guards, and must not run
  on a path that never uses the engine.
- A refused mesh is still reported by name, with a reason a human can
  check.

## Considered Options

1. Keep trimesh's gate, relaxed from `is_volume` to `is_watertight`.
2. Let the engine judge: build the Manifold and read its `status()`.
3. Repair on the way in: drop degenerate triangles, merge vertices, sew.

## Decision Outcome

Option 2, with the export half of option 3 applied where the framework
owns the tessellation.

- `_cached_manifold` builds the Manifold and reads `status()`. Anything but
  `NoError` raises `ValueError` naming the STL, the engine's status and
  trimesh's watertightness verdict as a diagnostic; the refused Manifold is
  not cached. `_flexible_manifold` does the same for a flexible leaf's
  evaluated mesh, naming the node.
- `_cached_local_bounds` reads only bounds. Selecting a solid, placing it in
  the broad phase, or comparing it on the exact kernel never judges its
  mesh; only a faceted read asks the engine.
- `write_stl` always drops degenerate triangles and the vertices only they
  referenced, for an exact leaf as for a fused solid. The tessellation
  tolerances are unchanged.
- `StlNode`'s import-time `require_watertight` gate (ADR-054) is untouched.
  It asks whether a committed file is a solid to build from, with an
  explicit opt-out; this decision is about whether a built solid can be
  compared.

Option 1 was rejected because trimesh calls the four-face edges
non-watertight too: any trimesh predicate second-guesses the engine.
Repairing meshes (the rest of option 3) was rejected because a verdict on a
sewn or hulled mesh is a verdict on a different part.

## Consequences

- A solid the old gate refused at selection is refused, if at all, at its
  first faceted read, and the message says what the engine objected to. A
  suite that never compares the part faceted has nothing to complain about.
- The originating projects can use `assertNotIntersecting`,
  `assertBlockedBeyond`, `assertNoSolidInterference` and
  `assertAssemblySupported` on their parts; the caller check ran the
  framework's faceted comparison over snappy-reprap's doubted leaves with
  no gate error.
- Exact leaf artifacts change bytes where OCCT emitted zero-area triangles;
  the digest/mtime currency regenerates them.

Change record: `openspec/changes/archive/2026-09-06-trust-manifold-over-trimesh/`.
