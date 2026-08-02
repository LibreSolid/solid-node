# ADR-037: Targeted in-place viewer updates

**Status:** Accepted
**Date:** 2026-08-02
**Change:** `viewer-targeted-update`

**Amends:**
- [ADR-035: Reusable viewer core and declared API version](../EXPORT/ADR-035-reusable-viewer-core-and-declared-api.md)
- [ADR-036: Snapshot-served shared viewer shell](ADR-036-snapshot-served-shared-viewer-shell.md)

## Context

The shared viewer previously had only `reload()`. Each successful development
build fetched the document, constructed a replacement tree, loaded every mesh,
and exchanged it for the old tree. That resets work which the document has
already identified as unchanged: an assembly with many artifacts re-parses and
re-uploads all geometry to show a one-part change. It also gives host shells no
way to apply a completed-artifact notification without reconstructing the
scene.

The tree document already supplies the information needed to update safely:
stable sibling names, model paths, `mtime`, operations, colour, and animation
metadata. The framework viewer owns that document and the rendered object tree;
asking each host to diff it would duplicate a framework interface and leave
`solid develop` behind the same coarse reload path.

## Decision

The reusable viewer handle provides two targeted update operations at API
version 2:

- `artifactChanged(path)` fetches and replaces geometry only for nodes that
  reference the named document-relative model path.
- `manifestChanged()` fetches the document and reconciles the existing tree by
  sibling name. It retains unchanged objects, updates operations and colour in
  place, adds and removes changed structure, and refetches geometry only when
  either its `(model path, mtime)` identity component changes.

Both operations fetch all required replacement geometry before mutating the
rendered tree. A failed fetch therefore reports an error while leaving the old
model, camera, orbit target, and usable handle intact. The development shell
uses `manifestChanged()` when its existing reload channel signals a completed
build; the channel protocol itself does not change. `reload()` remains available
for consumers that explicitly require a complete replacement.

## Alternatives considered

- Keep full-tree `reload()` for all updates. Rejected because its unnecessary
  mesh parsing and GPU upload visibly stalls large assemblies.
- Let every host compute its own diff and perform three.js mutations. Rejected
  because the document semantics and scene ownership belong to the framework,
  and this would make the shop and development loop drift.
- Use only an artifact event. Rejected because structural, operations, colour,
  and animation changes require the authoritative document.
- Key staleness by only model path or only `mtime`. Rejected because a parameter
  change can move a model without changing source mtime, while an ordinary
  source edit can change mtime at a stable model path.

## Consequences

- Hosts preserve their canvas, viewpoint, animation clock, and unchanged meshes
  across a targeted update.
- The viewer API declaration rises from 1 to 2, allowing a host to require this
  capability without method feature-sniffing.
- Reconciliation complexity stays in the shared viewer and is tested there,
  including failure containment; static export remains compatible because it
  does not call either update operation.

## References

- `openspec/changes/archive/2026-08-02-viewer-targeted-update/`
- `solid_node/viewers/widget/src/viewer.ts`
- `solid_node/viewers/widget/src/tree.ts`
- `solid_node/viewers/web/app/src/viewerShell.ts`
