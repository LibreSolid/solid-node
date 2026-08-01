# ADR-035: Reusable viewer core and declared API version

**Status:** Accepted

**Date:** 2026-08-01

**Change:** `viewer-package`

**Amends:**
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](ADR-020-static-export-and-embeddable-viewer-widget.md)

## Context

The React-free widget introduced by ADR-020 was an application entry point:
importing it auto-mounted every `data-solid-widget` container, and `mount()`
resolved to no value. The shop floor and development viewer therefore could not
host, unmount, refresh, or preserve a view through it, and each kept a separate
renderer. A host also had no way to compare the viewer bundle it received with
the interface it required before attempting to render.

The framework needs one imperative browser-viewer boundary that works for the
static export, the shop floor, and the development loop without coupling it to
either React version. The published export names remain a compatibility
contract: `solid-widget.js`, `data-solid-widget`, and `SolidNodeWidget`.

## Decision

`solid_node/viewers/widget/src/viewer.ts` is the reusable, side-effect-free
viewer core. It exports `mount()` and the public option, view, and handle types.
A mounted handle exposes `dispose()`, `view()`, `reload()`, `setTime()`, and
`apiVersion`. It accepts a source document and optional mesh base URL, animation
presentation, restored view, and canvas accessibility chrome. It loads either
shared tree document while leaving path rooting to the host.

`src/widget.ts` remains the published entry point and the esbuild IIFE entry.
It alone auto-mounts the documented attribute and query-string interface, and
re-exports `mount`, `apiVersion`, and `API_VERSION` on `SolidNodeWidget`.
Exports therefore retain their standalone, inline animation controls, while
other hosts can choose toggle, none, or externally driven presentation without
import-time document changes.

`package.json` declares `solidNodeViewerApi` as the single version source.
Both esbuild and vitest inject that declaration into the TypeScript core; Python
can inspect the field without building or executing JavaScript. The current
interface is API version 1, and an incompatible interface change must raise it.

## Alternatives considered

- **Keep one module with an auto-mount opt-out.** Rejected because import-time
  mounting happens before a host can provide that opt-out.
- **Expose Three.js scene, camera, and controls directly.** Rejected because
  implementation details would become a permanent public contract.
- **Ship a React component.** Rejected because the consumers span React 18,
  React 19, and no framework at all.
- **Declare the version in TypeScript or a generated sidecar.** Rejected
  because Python would need to parse source or require a build before it could
  report compatibility.

## Consequences

- Later floor and development-loop cycles share one renderer core while keeping
  their own host shells and styling.
- The export bundle remains compatible with existing hand-written pages, while
  its browser global now gives hosts an explicit compatibility check.
- The viewer package owns stable lifecycle and mounting behavior. Future
  incompatible changes require an API-version increment and consumer updates.
- The framework still carries the React development viewer until its later
  cycle adopts the shared core.

## References

- `solid_node/viewers/widget/src/viewer.ts`
- `solid_node/viewers/widget/src/widget.ts`
- `solid_node/viewers/widget/package.json`
- `openspec/changes/archive/2026-08-01-viewer-package/`
- ADR-020, ADR-034
