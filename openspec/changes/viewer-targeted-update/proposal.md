## Why

The viewer has one way to show a changed model: `reload()`, which refetches the
document, builds a whole new tree, waits for every mesh, and swaps it for the
old one. On `projects/v8-engine` that is 113 MB across 55 STLs re-parsed and
re-uploaded to the GPU to show a difference that usually touches one leaf — and
on a placement or colour edit, where no geometry changed at all, it is entirely
wasted. The maker sees the model stall and then jump.

Only the viewer can do better. It holds the manifest, so it alone can map an
artifact path back to the nodes referencing it, and it holds the tree, so it
alone can replace one node's geometry without disturbing the rest. The shop
cannot compute this from outside without duplicating the framework's data model,
and `solid develop` needs the identical behaviour — it reloads coarsely today
for exactly the same reason.

This is F3 of SPRINT-003, implementing PRD decisions D5 and D6. It has no
dependency on the build work and runs in parallel with F2.

## What Changes

- The mount handle gains two targeted updates:
  - `artifactChanged(path)` — refetch that one model file and swap the geometry
    into every node referencing it, leaving the rest of the scene, the camera
    and the animation clock untouched.
  - `manifestChanged()` — refetch the document, reconcile the tree in place
    (add, remove, re-parent, update operations and colour), and fetch geometry
    only where it is genuinely stale.
- Geometry staleness is keyed on `(model path, mtime)` together, so a parameter
  change that moves the model path and a source edit that moves the mtime are
  both caught, and an operations-only or colour-only edit costs no fetch at all.
- `mtime` becomes part of the manifest node type the viewer reads. The framework
  already writes it in both `viewer.json` and export `manifest.json`; the viewer
  simply ignores it today.
- A failed targeted update leaves the previously rendered model on screen and
  the handle usable, so one bad fetch can never wedge a viewer.
- `reload()` stays as it is, for hosts that want a full rebuild.
- The development page updates through `manifestChanged()` instead of
  `reload()`, so `solid develop` stops tearing down the scene on every edit.
- The declared viewer API version is raised to 2, so a host can require the
  targeted-update capability rather than feature-sniffing the handle.

## Capabilities

### New Capabilities

None. This extends the viewer package's existing mount handle.

### Modified Capabilities

- `viewer-package`: the handle gains targeted artifact and document updates
  beside `reload()`; geometry staleness and its key are stated; the API version
  rule covers additive capability changes.
- `web-viewer`: the development page refreshes through a targeted document
  update rather than rebuilding its tree.

## Impact

- `solid_node/viewers/widget/src/viewer.ts` — the handle grows the two update
  methods over the existing tree rather than replacing it.
- `solid_node/viewers/widget/src/tree.ts` — `WidgetTree` gains in-place
  reconciliation, per-node geometry keys, and geometry replacement that disposes
  what it drops.
- `solid_node/viewers/widget/src/types.ts` — `ManifestNode` carries `mtime`.
- `solid_node/viewers/widget/src/version.ts` and `package.json` — API version 2.
- `solid_node/viewers/web/app/src/viewerShell.ts` — the development shell calls
  the targeted update.
- Widget vitest suites and `tests/test_widget_e2e.py` — a real page proving the
  canvas and camera survive an update, which is the only assertion that
  distinguishes an in-place update from a reload.
- The shop consumes this in S2; nothing in this cycle depends on the shop.
