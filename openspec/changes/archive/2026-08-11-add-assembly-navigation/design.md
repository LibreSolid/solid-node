## Context

`viewer.json` and `manifest.json` already expose the authoritative nested
tree. The reusable widget creates a `WidgetTree` and deliberately keeps its
Three.js groups private; its public handle currently exposes lifecycle,
camera, animation, and targeted-update behaviour only. Studio is the
originating caller for an assembly navigator that must control the real
renderer without becoming a second renderer.

## Goals / Non-Goals

**Goals:**

- Expose a stable, serializable assembly representation with effective colours.
- Let hosts independently focus a subtree and hide or show a subtree.
- Preserve targeted-update and resource-lifecycle guarantees.

**Non-Goals:**

- Altering the source document, exporting per-part files, or persisting UI
  state in a CAD project.
- Exposing Three.js scene, mesh, camera, or controls objects.
- Selection highlighting, material editing, clipping, or authoring operations.

## Decisions

### Add an explicit viewer-handle contract and advance the API version

The handle gains `assembly()`, `setRoot(path | null)`, and
`setVisible(path, visible)`. `assembly()` returns immutable metadata only:
name, root-relative sibling-name path, effective colour or null, model-bearing
status, and children. A null root selects the published document root. Unknown
paths reject with a descriptive error. Because this is a new required host
capability, the declared viewer API advances from 3 to 4; hosts use their
existing API check rather than method feature-detection.

Exposing the document directly was rejected because it leaves effective colour
inheritance and renderer-specific path validation to every host. Exposing
Three.js objects was rejected because it makes implementation internals a
permanent public contract.

### Apply focus and visibility as non-destructive render filters

`setRoot` changes the visible traversal root and fits that rendered subtree;
`setVisible` toggles the target group's descendants without unloading meshes.
Visibility remains tracked by path against the full document, so it is
independent from focus and survives a focus change. Hidden root paths are valid
and result in an empty displayed subtree rather than silently restoring it.

### Reconcile state by path with targeted updates

The widget maintains focused and hidden paths outside the loaded document.
After `artifactChanged` and `manifestChanged`, it reapplies state for paths
that still resolve. A missing focus path becomes the full root; missing hidden
paths are discarded. This extends the existing name-based reconcile policy and
does not require a document schema change.

## Risks / Trade-offs

- [A focused hidden root produces an intentionally empty canvas] → The handle
  reports the resulting state; hosts identify it in their own controls.
- [Path names are only unique among siblings] → Use root-relative name arrays,
  never flat labels or model artifact identities.
- [Reapplying state after updates could refit unexpectedly] → Refit only when
  `setRoot` changes the effective focus, never for a targeted update retaining
  it.
