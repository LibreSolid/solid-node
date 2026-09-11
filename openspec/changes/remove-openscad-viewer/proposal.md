## Why

OpenSCAD was solid-node's first reliable interactive viewer, but the browser
viewer has become the machine-facing surface while OpenSCAD can represent only
a diminishing subset of the framework's simulation model. Keeping a second,
less faithful viewer and an installation-dependent fallback now burdens the
v0.7 roadmap as independent drivers, instructions, and continuously evaluated
flexible parts develop further.

## What Changes

- **BREAKING**: remove `solid develop --openscad` and the OpenSCAD GUI viewer
  process/PID lifecycle.
- **BREAKING**: remove the automatic OpenSCAD fallback from `solid develop`;
  development opens the browser viewer by default and reports the `viewer`
  extra remedy when that package is absent.
- Retain `solid develop --no-web` as the watch-and-build route for a host that
  supplies its own viewer.
- Retain OpenSCAD as a supported modelling and output technology:
  `OpenScadNode`, `Solid2Node`, legacy SCAD adapters, generated SCAD, and the
  OpenSCAD-backed geometry paths continue to work.
- Retain `solid snapshot --renderer openscad` and its existing explicit
  renderer policy; removing the interactive GUI viewer does not change the
  snapshot renderer.
- Explain the historical transition and the breaking viewer change in the
  v0.7 release material and user documentation, including installation of
  `solid-node[viewer]` for interactive development.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: remove the OpenSCAD development-viewer flag and make browser viewing
  the sole interactive `develop` viewer.
- `openscad-dependency`: remove GUI viewing from the exact set of operations
  that require the OpenSCAD executable while preserving modelling, legacy
  evaluation, and snapshot requirements.
- `viewer-distribution`: make the viewer extra required for the interactive
  development viewer instead of treating OpenSCAD as the plain-install
  fallback.
- `backend-neutral-materialization`: retain SCAD modelling and output without
  retaining the OpenSCAD GUI or its development fallback.
- `user-documentation`: document the v0.7 viewer transition, its rationale,
  installation remedy, and the OpenSCAD capabilities that remain supported.

## Impact

This changes the public `solid develop` CLI, development-process topology,
OpenSCAD dependency boundary, installation guidance, and v0.7 release notes.
Likely implementation areas are `solid_node/manager/develop.py`, the obsolete
GUI wrapper in `solid_node/viewers/openscad.py`, their tests, package comments,
the architecture synthesis, and viewer/CLI/quickstart documentation. It does
not change the browser viewer's process contract or code, the node document
schema, CAD adapters, SCAD compatibility APIs, geometry production, or either
snapshot renderer.
