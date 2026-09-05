# Export

## MODIFIED Requirements

### Requirement: Export artifact contents

The system SHALL export a node by building all STLs and writing an output
directory containing `manifest.json`, a `models/` directory, and — unless
widget-less export is requested — `index.html` plus the prebuilt
`solid-widget.js` bundle, both copied from the installed viewer package. If
the viewer package is not installed, export SHALL fail with
`WidgetBundleMissing` naming `pip install "solid-node[viewer]"` and
`--no-widget` as the alternatives.

#### Scenario: Widget-less export

- **WHEN** export runs with `widget=False` (`--no-widget`)
- **THEN** only `manifest.json` and `models/` are written, whether or not the
  viewer is installed

#### Scenario: Export without the viewer

- **WHEN** export runs with the widget requested in an installation without
  `solid-node-viewer`
- **THEN** it fails naming the extra and `--no-widget`, and writes no output
  directory

### Requirement: Embeddable widget behavior
The export channel SHALL ship the installed viewer's bundle as an auto-mounting
bundle, so an export directory renders on any static host with no solid-node
process running. It SHALL keep its published names — the bundle
`solid-widget.js`, the auto-mount attribute
`data-solid-widget="<manifest url>"`, and the browser global
`SolidNodeWidget` — and SHALL auto-mount every element carrying that attribute
once the page is ready, presenting animation as an always-visible inline bar.
The page query string SHALL set the initial state: `?t=<0..1>` for time,
`?autoplay=0` to start paused. How the model itself is rendered — tree
composition, camera, colour, and animation semantics — is the
`viewer-package` capability of solid-node-viewer, which the export channel
embeds rather than reimplements.

#### Scenario: Static pose embed

- **WHEN** the export's `index.html` is loaded with `?t=0.25&autoplay=0`
- **THEN** the model renders paused at `$t = 0.25`

#### Scenario: Serving requires no backend

- **WHEN** the export directory is served by any static file host or opened
  through an iframe
- **THEN** the widget renders and animates with no solid-node process running

#### Scenario: An existing host page keeps working

- **WHEN** a hand-written page embeds an export by the documented bundle
  filename, auto-mount attribute, and browser global
- **THEN** it mounts and renders as before
