## Why

The same three.js renderer exists three times — the export widget, the shop
floor viewer, and the development-loop app — and a capability added to one does
not reach the others. `solid_node/viewers/widget` is the smallest and most
complete of the three, but it is an application entry point rather than a
reusable package: `mount()` returns nothing to control the instance with, its
options cover only initial animation state, and importing it auto-mounts as a
side effect. Nothing outside an export page can host it. Making it a real
package with the interface its three consumers need is what lets the later
cycles delete the other two copies.

## What Changes

- Split the package into a reusable viewer core and a thin auto-mount entry.
  The core exports `mount()` and never touches the document on import; the
  entry keeps the published auto-mount contract and is what the bundle builds.
- Return a handle from `mount()` instead of nothing: `dispose()`, `view()`,
  `reload()`, and `apiVersion`. **BREAKING** for in-repo callers of the current
  `Promise<void>` signature; the published bundle, its global, its auto-mount
  attribute, and its query parameters are unchanged.
- Add the mount options the three consumers require: a mesh base URL separate
  from the snapshot URL; an animation presentation mode covering an always
  visible inline bar, a bar behind a persistent toggle, no controls, and
  externally driven time; a camera view to restore instead of fitting; and a
  CSS class plus ARIA attributes for the canvas.
- Load either published document. `viewer.json` and `manifest.json` now share
  one schema, so the loader reads the shared fields and takes model rooting
  from the caller rather than branching on the document.
- Declare an API version in one place in the package and expose it on the
  handle and on the browser global, so a host that receives an incompatible
  bundle can say so instead of rendering a blank pane.
- Extend the package's vitest suite to the new options and the handle, keeping
  the existing export, Sphinx, and end-to-end widget coverage green.
- Keep the package private, keep the directory `solid_node/viewers/widget`, and
  keep `solid-widget.js`, `data-solid-widget`, and `SolidNodeWidget`.

Adds no rendering capability beyond today's parity plus the options above. It
does not change how the bundle is delivered or built into a distribution, does
not add a CLI accessor, and does not touch the shop floor or the
development-loop app; those are the cycles that follow.

## Capabilities

### New Capabilities

- `viewer-package`: the reusable viewer's mount interface — source and mesh
  rooting, animation presentation, camera fitting and view restoration,
  material inheritance, canvas chrome, the returned handle, and the declared
  API version.

### Modified Capabilities

- `export`: the embeddable-widget requirement narrows to the export channel's
  obligation — ship the auto-mounting bundle under its published names and
  honour the page query parameters — while renderer semantics move to
  `viewer-package`.

## Impact

Affects `solid_node/viewers/widget/` (`src/widget.ts` split into an auto-mount
entry over a new core, `src/tree.ts`, `src/types.ts`, `build.mjs`,
`package.json`, `tsconfig.json`, and the vitest suite). Exercises but does not
modify `solid_node/core/export.py`, `solid_node/manager/export.py`, and
`solid_node/sphinx.py`, which continue to consume `dist/solid-widget.js` and
`index.html` by their current paths. Regression surface is
`tests/test_export.py`, `tests/test_sphinx_ext.py`, `tests/test_widget_e2e.py`,
and the `-W` documentation build with its V8 example export.

Consumers arriving later depend on this cycle's output: `viewer-bundle-delivery`
reads the declared API version, and `floor-uses-framework-viewer` and
`dev-viewer-on-shared-package` mount through this interface.
