## Why

The reusable viewer package now exists, but nothing delivers it. `packaging.py`
builds the CRA development app into every wheel and source distribution and does
nothing for the widget, whose `dist/solid-widget.js` is gitignored and built only
by npm. A wheel built from this checkout ships the widget's TypeScript sources
and no bundle, so a fresh installation has no viewer at all: `solid export`
fails to copy one, the Sphinx extension cannot complete a `--no-widget` export,
and no other program can obtain one.

That other program is the immediate reason. The shop floor is to stop carrying
its own copy of the renderer and show models through this viewer, and it reaches
the framework only through the `solid` command line — never by importing
`solid_node`. Delivering the bundle inside the distribution and reporting it
through the CLI is what makes a single shared viewer reachable at all.

## What Changes

- The widget bundle is built into source distributions and wheels the way the
  development app already is: always for an sdist, and for a wheel when the
  built bundle is absent from the checkout.
- `MANIFEST.in` carries the built bundle into the distribution instead of
  documenting its absence.
- A new `solid viewer` command reports the installed bundle's filesystem path
  and the viewer's declared API version, and fails with a remedy when the
  installation carries no bundle.
- One internal accessor locates the bundle and reads the declared API version;
  `solid export` and `solid_node/sphinx.py` stop each computing that path
  themselves.

Not in this change: publishing the package to a registry, renaming
`solid-widget.js`, TypeScript declaration files (no consumer typechecks against
the package: the shop serves the bundle as a static asset, and the development
app compiles the same repository's sources), and any change to floor.

## Capabilities

### New Capabilities

- `viewer-distribution`: the built viewer bundle is present in the framework's
  Python distributions, and an installed framework reports its location and
  declared API version to another program.

### Modified Capabilities

- `cli`: adds the `viewer` command to the command registry and help, as a
  command that takes no node path.

## Impact

- `solid_node/packaging.py` — builds the widget alongside the development app.
- `MANIFEST.in` — includes the built bundle.
- `solid_node/manager/viewer.py` (new) and `solid_node/cli.py` — the command.
- `solid_node/core/export.py`, `solid_node/sphinx.py` — consume the shared
  accessor instead of their own path constants.
- `tests/` — packaging and CLI coverage; existing export, Sphinx, and widget
  end-to-end tests must stay green.
- Consumers: the shop floor (a later sprint cycle) becomes able to obtain a
  viewer; the release workflow already builds the bundle in CI and gains a
  distribution that no longer depends on that step having run.
