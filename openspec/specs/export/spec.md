# Static Export Specification

## Purpose

The static export channel: `export_node` producing a self-contained,
offline, embeddable artifact (manifest + STL models + optional React-free
widget viewer). Encodes ADR-020 (static export and embeddable viewer
widget); the manifest is a versioned public contract shared by the exporter,
the widget, and the Sphinx extension.

Code: `solid_node/core/export.py`, `solid_node/manager/export.py`,
`solid_node/viewers/widget/`.

## Requirements

### Requirement: Export artifact contents

The system SHALL export a node by building all STLs and writing an output
directory containing `manifest.json`, a `models/` directory, and — unless
widget-less export is requested — `index.html` plus the prebuilt
`solid-widget.js` bundle. If the widget bundle is missing from the
installation, export SHALL fail with `WidgetBundleMissing` including the
npm build hint.

#### Scenario: Widget-less export

- **WHEN** export runs with `widget=False` (`--no-widget`)
- **THEN** only `manifest.json` and `models/` are written

### Requirement: Manifest contract

The manifest SHALL declare `format: "solid-node-export"`, `version: 1`,
`animation: {fps, frames}`, and a `root` tree serialized by the same
rigid/non-rigid walk as the NodeAPI: a rigid node emits a single `model`
reference and stops recursion; a non-rigid node recurses into its rendered
children. Each node carries `name`, `type`, `color`, and its operations as
raw unevaluated expression strings so `$t` animation is preserved verbatim.
Changes to the tree shape or operation serialization are breaking and MUST
bump `version` and update all three consumers (exporter, widget, Sphinx
extension) together.

#### Scenario: Animated operations survive export

- **WHEN** an assembly's rotation is `$t * 360`
- **THEN** the manifest stores that expression as a string, not a baked
  numeric pose

### Requirement: Model deduplication

The system SHALL copy one STL per distinct rigid artifact into `models/`,
keyed by the STL path relative to the build dir — identical instances share
one file, and same-named scripts in different directories do not collide.

#### Scenario: Repeated part

- **WHEN** an assembly instantiates the same parameterized part four times
- **THEN** `models/` contains that part's STL once and all four tree nodes
  reference it

### Requirement: Embeddable widget behavior

The widget SHALL auto-mount on every element with `data-solid-widget="<manifest
url>"` at DOMContentLoaded, render the tree as a Z-up three.js group
hierarchy with per-frame local matrices computed from operations
(degrees→radians, premultiplied in order), fit the camera to the model
bounds, and provide orbit controls. Node colors apply from the manifest,
inherited from the parent when unset, defaulting to `#8899aa`. When any
operation expression contains `$t` the widget SHALL show a play/pause button
and a 0..1 timeline slider (step `1/frames`), autoplaying by default at
`frames / fps` seconds per cycle; static models get no controls. Page query
parameters SHALL set the initial state: `?t=<0..1>` for time, `?autoplay=0`
to start paused.

#### Scenario: Static pose embed

- **WHEN** the export's `index.html` is loaded with `?t=0.25&autoplay=0`
- **THEN** the model renders paused at `$t = 0.25`

#### Scenario: Serving requires no backend

- **WHEN** the export directory is served by any static file host or opened
  through an iframe
- **THEN** the widget renders and animates with no solid-node process
  running
