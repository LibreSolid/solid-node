## Why

Static export and normal-build publication duplicate the same node-tree walk.
The export copy omits child linking, which is observably wrong when `render()`
recreates and rebinds a child: the export serializes the new instance with its
class fallback while the builder links and serializes it under the rebound
attribute name. Sprint 002 needs one additive document schema before every
viewer consumes it.

## What Changes

- Route export and build snapshot publication through one serializer that
  applies the established child-linking and rigid/non-rigid traversal rules.
- Make the shared node fields identical, including linked names, type, colour,
  serialized operations, and per-node `mtime`.
- Add `format: "solid-node-export"` to `viewer.json` and add per-node `mtime`
  to `manifest.json`, while retaining schema `version: 1`.
- Record in a new ADR that the shared format identifies tree-document schema,
  not portability, and amend the architecture implications of ADR-020 and
  ADR-031 accordingly.
- Keep `manifest.json` and `viewer.json` as distinct document names with their
  current consumers and path-rooting semantics: exports remain portable and
  deduplicated under `models/`; build publications remain build-root-relative
  and non-portable.
- Retire the duplicate export and builder serializer functions after focused
  red-first parity coverage proves the current linked-name disagreement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `export`: require attribute-derived child naming, per-node `mtime`, and node
  fields shared with normal-build viewer snapshots without changing export
  portability, document name, format, version, or model rooting.
- `build-viewer-artifacts`: require the shared published-document format and
  node fields while preserving `viewer.json`, build-root-relative model paths,
  atomic publication, and non-portable build output.

## Impact

The change affects `solid_node/core/export.py`,
`solid_node/core/builder.py`, a framework-owned shared serializer location,
and their canonical export, builder, Sphinx, web-viewer, and publication tests,
plus a framework ADR and architecture update.
It changes both JSON documents additively; it does not rename a public surface,
alter widget names, add a compatibility alias, publish a package, or make a
build publication self-contained.
