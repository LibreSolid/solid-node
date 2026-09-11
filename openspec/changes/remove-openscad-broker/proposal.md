## Why

Curta Type I-3x exposed that motion and machine composition were mediated by
OpenSCAD representations; expression sharing is now fixed and integrated at
`5e591474b5cf54c2b41f223400d2b6ee3cbb97ae`, but geometry preparation still
recurses through `as_scad()` and every faceted fusion still uses OpenSCAD.
The next step is to let solid-node compose machines and obtain geometry from
each modelling technology directly, with SCAD as a backend/output boundary.

## What Changes

- Separate tree preparation, native geometry/artifact production, and SCAD
  presentation. Browser publication and geometry tests do not construct a
  SCAD assembly as an intermediate representation.
- Preserve every current modelling adapter, project `render()`/`simulate()`
  API, placement semantics, exact geometry, and the schema-4 document contract.
- Preserve public `assemble()`'s SCAD result and SCAD output methods through a
  compatibility consumer of the prepared tree. Existing normal `solid build`
  SCAD deliverables and OpenSCAD viewing/snapshot choices remain supported.
- **BREAKING (geometry production/dependency):** a non-exact `FusionNode`
  unions its children's local mesh artifacts directly using `manifold3d`,
  instead of asking OpenSCAD to fuse their SCAD. Exact fusions retain OCCT.
  Mesh triangulation and therefore content-derived piece IDs can change;
  geometry acceptance must be proved, not inferred from successful export.
- Extend artifact currency with a narrowly scoped producer recipe revision
  so existing OpenSCAD-produced fusion caches cannot mask the engine change.
- Keep legacy SCAD-only adapter overrides usable at an explicit compatibility
  boundary; native adapters no longer have to implement SCAD conversion.
- Record actual warm/fresh-geometry peak memory, elapsed time, engine calls,
  cache behavior, and output sizes, including another complete Curta export.

OpenSCAD itself is not removed. Its GUI role, the default viewer selection,
snapshot defaults, package dependencies, and the optional AGPL browser
viewer's process boundary are not being redesigned in this cycle.

## Capabilities

### New Capabilities

- `backend-neutral-materialization`: obtain placed machine structure and
  backend-owned geometry without a universal SCAD assembly; direct faceted
  fusion and retained SCAD compatibility with explicit failure boundaries.

### Modified Capabilities

- `node-model`: separate the framework-owned preparation lifecycle from its
  SCAD compatibility result and remove mandatory `as_scad()` from native
  adapter participation, retaining authoring and validation guarantees.
- `openscad-dependency`: remove faceted fusion from the executable's requiring
  set; preserve actual OpenSCAD leaves, legacy evaluation, and viewer paths.
- `mesh-engine-dependency`: add direct faceted fusion to the conditional
  `manifold3d` requiring set without changing assertion-engine policy.
- `build-pipeline`: revise faceted-fusion production and qualify artifact
  freshness by the producer recipe while preserving locking, source-generation
  checks, atomic files, SCAD deliverables, and manifest-last publication.

## Impact

Framework only: `solid_node/node/` lifecycle and adapters, geometry helpers,
`core/builder.py`, artifact currency, geometry-building callers in export,
tests and snapshot staging, and SCAD output boundaries. No viewer source or
mechanical-project implementation changes belong here.

Origin: `workflow/docs/expression-graphs.md` and the archived
`2026-09-11-expression-graphs` cycle, validated on unchanged Curta Type I-3x.
This is a standalone, unratified proposal, not permission to implement.
Design choices, compatibility limits, opening identities, ADR conflicts and
proof gates are specified in `design.md`; work is enumerated in `tasks.md`.
