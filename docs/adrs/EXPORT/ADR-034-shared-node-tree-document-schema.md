# ADR-034: Shared node-tree document schema across export and build snapshots

**Status:** Accepted

**Date:** 2026-08-01

**Change:** `unified-node-serializer`

**Amends:**
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](ADR-020-static-export-and-embeddable-viewer-widget.md)
- [ADR-031: Published viewer snapshot](../BUILD/ADR-031-published-viewer-snapshot.md)

## Context

`manifest.json` and `viewer.json` independently walked the node tree. The
walks were intended to expose the same versioned tree, but their behavior had
already diverged: the builder linked a child before recursively serializing it,
while export did not. A `render()` that recreated and rebound `self.gear`
therefore emitted `Cube` in the portable manifest and `gear` in the build
snapshot. The documents also differed in additive metadata: the build tree had
per-node `mtime`; the manifest did not, and `viewer.json` lacked the shared
format marker.

ADR-020 made `manifest.json` a portable public export contract; ADR-031 made
`viewer.json` a private build-root-relative snapshot. The same
`solid-node-export` marker now identifies their shared versioned tree-document
schema, so the framework must make clear that schema identity does not erase
the existing portability boundary.

## Decision

The framework owns one recursive node serializer in `solid_node/core/`. It
emits `name`, `type`, `color`, `mtime`, and raw serialized `operations`; it
links every list/tuple child before recursion; rigid nodes emit one mapped
`model` and stop; a non-list/tuple non-rigid result retains the existing node
without model or children.

Each producer supplies only its rigid-model mapper:

- export records `models/<build-relative-stl>` and retains its existing copy
  and deduplication step, making `manifest.json` portable and self-contained;
- normal build records the STL path relative to the published build directory
  and copies nothing, keeping `viewer.json` private and non-portable.

Both documents declare `format: "solid-node-export"` and `version: 1` with
their existing animation metadata. `mtime` is additive to `manifest.json`; it
does not change tree shape or operation representation, so no version bump is
required. Re-generating committed exports will therefore create accepted
`mtime` churn and may cause Sphinx to rebuild documents that depend on those
manifests.

## Alternatives considered

- **Keep producer-local walkers.** Rejected because two implementations had
  already drifted at a user-visible naming boundary and would continue to
  duplicate every schema addition.
- **Call export from the builder.** Rejected because export's `models/` mapper
  and copying would accidentally make a normal build portable.
- **Use a mode flag in the shared serializer.** Rejected because it embeds
  producer policy in the common tree walk rather than keeping portability at
  the producer boundary.
- **Make every `solid-node-export` document portable.** Rejected because the
  build snapshot is atomically published private state, not a distribution
  artifact; its build-root-relative model references are intentional.

## Consequences

- Export and build snapshots have one observable node-tree schema and child
  naming behavior, including recreated-and-rebound children.
- Consumers may use the format/version pair to recognize the common tree
  schema, but must retain document-name and path-rooting knowledge when they
  need portable artifacts.
- Breaking changes to shared tree shape or raw operation serialization require
  a version bump and coordinated producer/consumer updates. Additive metadata
  follows the existing version-1 compatibility policy.
- `NodeAPI`, `SnapshotNodeAPI`, and the development viewer retain their live
  traversal for F4; this decision removes only the export and builder walks.

## References

- `solid_node/core/serializer.py`
- `solid_node/core/export.py`
- `solid_node/core/builder.py`
- `openspec/changes/archive/2026-08-01-unified-node-serializer/`
- ADR-020, ADR-031, ADR-026, ADR-030, ADR-032
