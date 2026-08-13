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

The manifest SHALL retain the document name `manifest.json` and SHALL declare
`format: "solid-node-export"`, `version: 1`, `animation: {fps, frames}`, and a
`root` tree with the same observable schema and child-name behavior as the
normal-build `viewer.json`. A rigid node SHALL emit one `model` reference and
stop recursion; a non-rigid node whose render result is a list or tuple SHALL
recurse into its children. Each node SHALL carry `name`, `type`, `color`,
`mtime`, and its operations as raw unevaluated expression strings so `$t`
animation is preserved verbatim. A rigid model reference SHALL remain rooted
beneath the export's `models/` directory and SHALL resolve to a copied artifact
so the export remains portable and self-contained. Changes to the shared tree
shape or operation serialization are breaking and MUST bump `version` and
update every producer and consumer of the shared schema together.

#### Scenario: Animated operations survive export

- **WHEN** an assembly's rotation is `$t * 360`
- **THEN** the manifest stores that expression as a string, not a baked
  numeric pose

#### Scenario: Linked names and additive metadata survive export

- **WHEN** an assembly returns children held by named attributes or list/tuple
  attributes
- **THEN** `manifest.json` uses their established linked names and includes
  each node's `mtime`, matching the shared node fields emitted in `viewer.json`

#### Scenario: A rendered child is recreated and rebound

- **WHEN** an assembly recreates a logical child and stores it on an attribute
  during each render
- **THEN** `manifest.json` and normal-build `viewer.json` publish the same
  attribute-derived child name

#### Scenario: A rendered child is reachable only through internal children state

- **WHEN** a child is reachable only through the parent's public `children`
  list when document serialization links it
- **THEN** both documents publish its established `children-<index>` name

#### Scenario: A rendered child has no parent attribute

- **WHEN** a child is not referenced by any parent attribute
- **THEN** its existing class-name fallback remains unchanged

#### Scenario: Export paths remain portable

- **WHEN** a rigid node is exported
- **THEN** its manifest model path is rooted beneath `models/` and resolves to
  the copied deduplicated STL within the export directory

### Requirement: Model deduplication

The system SHALL copy one STL per distinct rigid artifact into `models/`,
keyed by the STL path relative to the build dir — identical instances share
one file, and same-named scripts in different directories do not collide.

#### Scenario: Repeated part

- **WHEN** an assembly instantiates the same parameterized part four times
- **THEN** `models/` contains that part's STL once and all four tree nodes
  reference it

### Requirement: Embeddable widget behavior
The export channel SHALL ship the framework's viewer as an auto-mounting bundle,
so an export directory renders on any static host with no solid-node process
running. It SHALL keep its published names — the bundle `solid-widget.js`, the
auto-mount attribute `data-solid-widget="<manifest url>"`, and the browser
global `SolidNodeWidget` — and SHALL auto-mount every element carrying that
attribute once the page is ready, presenting animation as an always-visible
inline bar. The page query string SHALL set the initial state: `?t=<0..1>` for
time, `?autoplay=0` to start paused. How the model itself is rendered — tree
composition, camera, colour, and animation semantics — is the
`viewer-package` capability, which the export channel embeds rather than
reimplements.

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

### Requirement: Export manifests carry the piece inventory

The exported `manifest.json` SHALL include the printed-piece inventory defined
by the `printed-pieces` capability, with each piece's `models` references rooted
beneath the export's `models/` directory so they resolve to the copied artifacts
inside the export. The export SHALL therefore remain self-contained: a consumer
reading the inventory from a static host resolves every piece without a
solid-node process and without any path outside the export directory.

Model deduplication is unchanged — one copied STL per distinct rigid artifact —
and the inventory SHALL be reported on top of it, so several deduplicated
artifacts with identical content still resolve to a single piece.

#### Scenario: An export publishes its pieces

- **WHEN** a node is exported
- **THEN** `manifest.json` contains a `pieces` list beside `root`, every rigid
  node carries a `piece` id present in that list, and every model the inventory
  names is a copied artifact beneath `models/`

#### Scenario: Distinct artifacts with identical content are one piece

- **WHEN** an export copies two distinct rigid artifacts whose STL content is
  identical
- **THEN** `models/` still contains both copied files and the inventory reports
  one piece whose `models` names both, with a count covering every instance of
  either

