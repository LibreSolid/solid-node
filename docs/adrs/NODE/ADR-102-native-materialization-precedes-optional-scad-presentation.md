# ADR-102: Native materialization precedes optional SCAD presentation

**Status:** Accepted

**Date:** 2026-09-11

**Change:** [remove-openscad-broker](../../../openspec/changes/archive/2026-09-11-remove-openscad-broker/)

**Amends:** [ADR-002](ADR-002-template-method-pattern-for-node-lifecycle.md),
[ADR-004](ADR-004-multi-cad-backend-adapter-pattern.md),
[ADR-045](ADR-045-exact-fusion-composition.md),
[ADR-046](ADR-046-conditional-openscad-dependency.md), and the artifact
currency rules of ADR-006/060/071/081.

## Context

OpenSCAD remained the framework's implicit geometry broker after exact leaves
learned to write native BREP/STL artifacts. Structure discovery and artifact
production still happened inside a recursively constructed SolidPython tree,
and every faceted fusion still sent already-produced child meshes through
OpenSCAD. Curta Type I-3x made that coupling visible after expression graphs
removed the preceding memory failure. The pilot requires OpenSCAD to remain a
supported modeller, output and viewer, but not the core representation.

## Decision

The framework-owned lifecycle first prepares the existing node tree. Preparation
renders and validates structure, links and names children, aggregates their
source scopes, and asks each adapter to materialize its backend-owned artifacts.
It does not construct assembly SCAD. Geometry-only export, testing, web
publication and browser development stop at that native boundary.

`assemble()`, `as_scad()`, `scad_code` and `generate_scad()` remain the SCAD
compatibility consumer. Ordinary builds still request that output; OpenSCAD
development and snapshots retain their policy. Solid2 and raw OpenSCAD leaves
still use OpenSCAD where it is their actual backend. A project leaf that
explicitly overrides the old `as_scad()` seam selects a declared legacy bridge;
failures in native production never trigger a fallback.

A faceted `FusionNode` unions its current child STL meshes directly with
manifold3d in the fusion's local frame. Exact fusion remains OCCT. The engine
judges input and output; the framework does not repair, retry through OpenSCAD,
or concatenate on failure. Disconnected valid results remain permitted.

Artifact currency carries a private producer recipe. A missing or changed
recipe is a hard miss before timestamp/content-restamp shortcuts. Faceted
fusion recipes include child production recipes, so nested caches migrate
without changing public node identity or artifact filenames.

## Consequences

- OpenSCAD is retained, but native geometry and portable documents no longer
  require assembly-wide SCAD or use it to fuse meshes.
- Native adapter errors remain visible and deterministic; there is no backend
  substitution policy.
- Faceted fusion bytes and derived piece ids may change within the declared
  tessellation tolerance. Existing legacy caches rebuild once.
- `manifold3d` is now required by faceted fusion as well as faceted comparison;
  all-exact preparation does not resolve either it or OpenSCAD.
- Preparation and SCAD presentation have separate per-instance memo state;
  the node tree and operation list remain the sole structure and placement
  authorities.

## Evidence

The linked change records red-first boundary tests, analytic and historical
fusion comparisons, the full framework suite, OpenSCAD-positive controls,
Curta warm/fresh aggregate memory, and a 3DPrintedClocks build with OpenSCAD
unreachable. Missing JSCAD integration prerequisites are reported there rather
than represented by mocked coverage.
