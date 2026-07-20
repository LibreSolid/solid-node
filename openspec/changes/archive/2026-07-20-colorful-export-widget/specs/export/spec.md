## MODIFIED Requirements

### Requirement: Embeddable widget behavior
The widget SHALL auto-mount on every element with `data-solid-widget="<manifest
url>"` at DOMContentLoaded, render the tree as a Z-up three.js group hierarchy
with per-frame local matrices computed from operations (degrees→radians,
premultiplied in order), fit the camera to the model bounds, and provide orbit
controls. Node colors apply from the manifest, inherited from the parent when
unset. Models without an explicit or inherited color SHALL use the same
normal-based material as the development viewer. When any operation
expression contains `$t` the widget SHALL show a play/pause button and a 0..1
timeline slider (step `1/frames`), autoplaying by default at `frames / fps`
seconds per cycle; static models get no controls. Page query parameters SHALL
set the initial state: `?t=<0..1>` for time, `?autoplay=0` to start paused.

#### Scenario: Colorless assembly embed

- **WHEN** an export contains multiple model nodes with no explicit or
  inherited colors
- **THEN** the widget renders those models with the development viewer's
normal-based material

#### Scenario: Static pose embed

- **WHEN** the export's `index.html` is loaded with `?t=0.25&autoplay=0`
- **THEN** the model renders paused at `$t = 0.25`

#### Scenario: Serving requires no backend

- **WHEN** the export directory is served by any static file host or opened
  through an iframe
- **THEN** the widget renders and animates with no solid-node process running

#### Scenario: Explicit model colors

- **WHEN** an export supplies explicit or inherited node colors
- **THEN** the widget renders those colors rather than replacing them with a
  normal-based material
