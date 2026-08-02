# ADR-036: Snapshot-served shared viewer shell

**Status:** Accepted
**Date:** 2026-08-02
**Depends on:**
- [ADR-013: React frontend framework](ADR-013-react-frontend-framework.md)
- [ADR-015: FastAPI + Uvicorn HTTP stack](../IPC/ADR-015-fastapi-unified-stack-for-http-services.md)
- [ADR-034: Shared node-tree document schema](../EXPORT/ADR-034-shared-node-tree-document-schema.md)
- [ADR-035: Reusable viewer core and declared API](../EXPORT/ADR-035-reusable-viewer-core-and-declared-api.md)

## Context

The development viewer previously loaded project Python at web-server startup,
constructed a recursive `/node` API, and carried a second browser renderer.
That renderer duplicated tree traversal, operation composition, expression
evaluation, animation, and reload-race handling already delivered by the
shared viewer package. It also rendered less faithfully than the export,
Sphinx, and shop surfaces.

The normal build now atomically publishes `viewer.json` and all referenced
model files, and the framework distribution now carries the shared bundle.

## Decision

The development server serves the published build directory below `/build/`
and the installed viewer bundle at `/_viewer/bundle.js`. `/_viewer` reports
availability, API version, and the remedy for an absent bundle. The React app
remains a small shell: it loads that bundle as a script, mounts it against
`/build/viewer.json` with inline autoplay controls, names the tab from the
snapshot, and calls the mount handle's `reload()` after the existing reload
channel reports a successful build.

The server never imports the project model. The recursive NodeAPI, the
snapshot-backed imitation of it, and the development app's local renderer are
retired. React and Create React App remain for the shell; replacing them is a
separate change.

## Alternatives considered

- Keep the per-node API behind a snapshot façade. This preserves an interface
  no consumer needs and retains the duplicate walk.
- Import viewer-package source into the CRA app. CRA cannot compile it without
  ejection, it would bundle a second three.js copy, and it requires an install
  inside framework worktrees.
- Replace the shell with a static page. This would expand the change into a
  CRA, packaging, and `--web-dev` migration without helping viewer sharing.

## Consequences

- Development, export, Sphinx, and the shop use one rendering implementation.
- A build error or absent build leaves the server, reload socket, and error
  pane available; an absent bundle displays its build remedy.
- The development page gains the shared viewer's colours, lighting, fitted
  camera, and inline animation controls.
- ADR-014's recursive NodeAPI and ADR-027's local browser composition are
  superseded for the development viewer. The shared package owns composition.
- React remains only as a lifecycle and error/reload shell; CRA migration debt
  remains explicit rather than being silently folded into this change.

## References

- `openspec/changes/archive/2026-08-02-dev-viewer-on-shared-package/`
- `solid_node/viewers/web/viewer.py`
- `solid_node/viewers/web/app/src/viewerShell.ts`
