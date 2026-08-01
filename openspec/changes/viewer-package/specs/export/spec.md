## MODIFIED Requirements

### Requirement: Embeddable widget behavior
The export channel SHALL ship the framework's viewer as an auto-mounting bundle,
so an export directory renders on any static host with no solid-node process
running. It SHALL keep its published names — the bundle `solid-widget.js`, the
auto-mount attribute `data-solid-widget="<manifest url>"`, and the browser
global `SolidNodeWidget` — and SHALL auto-mount every element carrying that
attribute once the page is ready, presenting animation as an always-visible
inline bar. The page query string SHALL set the initial state: `?t=<0..1>` for
time, `?autoplay=0` to start paused. How the model itself is rendered — tree
composition, camera, colour, and animation semantics — is the `viewer-package`
capability, which the export channel embeds rather than reimplements.

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
