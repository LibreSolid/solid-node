## MODIFIED Requirements

### Requirement: Develop command

The system SHALL provide `solid develop <path>`, orchestrating builder and
viewer processes: the web viewer runs by default and is suppressed when
`--openscad` is passed alone or when `--no-web` is passed; `--no-web` runs the
builder watch loop alone and SHALL NOT bind `SOLID_NODE_PORT`; `--web-dev`
additionally spawns the npm dev server and puts the viewer in proxy mode;
`--openscad` opens the project in an OpenSCAD GUI (PID tracked in
`.openscad.pid`); `--debug-builder` and `--debug-web` run the respective
component once in-process for breakpoints. `--no-web` SHALL be rejected with a
clear argument error when combined with a flag that explicitly requests the web
viewer (`--web`, `--web-dev`, `--debug-web`), and SHALL be accepted with
`--openscad`. Each rebuild cycle SHALL respawn the builder and restart the web
viewer process when one is running; Ctrl-C exits 0.

#### Scenario: Default develop session

- **WHEN** a user runs `solid develop root`
- **THEN** the builder and the web viewer start, and the model is viewable at
  `http://localhost:<SOLID_NODE_PORT>`

#### Scenario: Headless develop session

- **WHEN** a user runs `solid develop root --no-web`
- **THEN** the builder watch loop runs and rebuilds on source changes, and no
  listener is bound on `SOLID_NODE_PORT`

#### Scenario: Web viewer requested and suppressed at once

- **WHEN** a user runs `solid develop root --no-web --web-dev`
- **THEN** the command exits with a clear argument error before starting
  development processes

### Requirement: Callback mode validation

The `solid develop` command SHALL accept `--callback URL` in normal web mode
and in `--no-web` mode, and reject it with `--openscad` or `--web-dev` with a
clear argument error. `solid build` SHALL NOT accept a callback option.

#### Scenario: Callback requested for OpenSCAD mode

- **WHEN** a user runs `solid develop root --openscad --callback URL`
- **THEN** the command exits with a clear argument error before starting
  development processes

#### Scenario: Callback for an external viewer host

- **WHEN** a user runs `solid develop root --no-web --callback URL`
- **THEN** the command starts the builder watch loop without a web viewer and
  POSTs the callback after each complete successful build
