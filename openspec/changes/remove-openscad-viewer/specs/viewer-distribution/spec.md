## MODIFIED Requirements

### Requirement: The viewer is an optional extra

The framework SHALL declare the `viewer` extra, installing the
`solid-node-viewer` distribution, and the `web-snapshot` extra, installing
`solid-node-viewer[snapshot]`. The framework's own dependencies SHALL NOT
include the viewer, and every framework operation that does not open, embed or
photograph through the browser viewer SHALL work in an installation without
it. Interactive development through `solid develop` SHALL require the viewer
extra unless the caller explicitly selects the `--no-web` watch loop.

#### Scenario: A plain installation retains non-viewer operations

- **WHEN** `pip install solid-node` runs without the extra
- **THEN** building, testing, exporting without the widget, snapshotting
  through OpenSCAD, and developing with `--no-web` work, while ordinary
  `solid develop` fails naming the viewer extra

#### Scenario: The extra brings the interactive viewer

- **WHEN** `pip install "solid-node[viewer]"` runs
- **THEN** `solid viewer` reports the installed bundle and `solid develop`
  opens the browser viewer by default
