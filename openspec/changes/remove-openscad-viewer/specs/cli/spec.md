## MODIFIED Requirements

### Requirement: Develop command

The system SHALL provide `solid develop [reference]`, orchestrating the
builder and the browser viewer process by default. With no viewer flag, and
with the retained explicit `--web` spelling, it SHALL require the
`solid-node-viewer` package and fail before starting development processes,
naming `pip install "solid-node[viewer]"`, when that package is not installed.
The framework SHALL provide no OpenSCAD GUI viewer flag or fallback.

`--no-web` runs the builder watch loop alone and SHALL NOT require the viewer
package or bind `SOLID_NODE_PORT`. The browser viewer SHALL run as the installed
viewer package's `serve` command on the project's build directory, in a
separate process; `--web-dev` SHALL ask that process to also start the viewer's
own npm dev server and proxy to it; `--debug-builder` runs the builder once
in-process for breakpoints. `--no-web` SHALL be rejected with a clear argument
error when combined with a flag that explicitly requests the browser viewer
(`--web`, `--web-dev`). Each rebuild cycle SHALL respawn the builder and restart
the browser viewer process when one is running; Ctrl-C exits 0.

#### Scenario: Default develop session

- **WHEN** a user runs `solid develop` in an installation with
  `solid-node-viewer`
- **THEN** the builder and the browser viewer start on the project model, and
  the model is viewable at `http://localhost:<SOLID_NODE_PORT>`

#### Scenario: Default develop session without the viewer

- **WHEN** a user runs `solid develop` in an installation without
  `solid-node-viewer`, whether or not OpenSCAD is installed
- **THEN** the command fails before starting development processes, naming
  `pip install "solid-node[viewer]"`, and does not open OpenSCAD

#### Scenario: The browser viewer is requested but not installed

- **WHEN** a user runs `solid develop --web` without `solid-node-viewer`
- **THEN** the command fails naming the extra and starts no builder or viewer

#### Scenario: The removed OpenSCAD flag is rejected

- **WHEN** a user runs `solid develop --openscad`
- **THEN** command-line parsing rejects the unknown option and starts no
  development process

#### Scenario: Headless develop session

- **WHEN** a user runs `solid develop --no-web` without
  `solid-node-viewer`
- **THEN** the builder watch loop runs and rebuilds on source changes, and no
  listener is bound on `SOLID_NODE_PORT`

#### Scenario: Browser viewer requested and suppressed at once

- **WHEN** a user runs `solid develop --no-web --web-dev`
- **THEN** the command exits with a clear argument error before starting
  development processes

#### Scenario: The browser viewer runs in its own process

- **WHEN** `solid develop` runs the browser viewer
- **THEN** the viewer is the installed viewer package's `serve` command,
  launched through the interpreter running `solid` on the project's build
  directory, and it is restarted after each rebuild cycle

### Requirement: Callback mode validation

The `solid develop` command SHALL accept `--callback URL` in normal browser
mode and in `--no-web` mode, and reject it with `--web-dev` with a clear
argument error. `solid build` SHALL NOT accept a callback option.

#### Scenario: Callback requested for viewer-development mode

- **WHEN** a user runs `solid develop --web-dev --callback URL`
- **THEN** the command exits with a clear argument error before starting
  development processes

#### Scenario: Callback for an external viewer host

- **WHEN** a user runs `solid develop --no-web --callback URL`
- **THEN** the command starts the builder watch loop without a browser viewer
  and POSTs the callback after each complete successful build

## REMOVED Requirements

### Requirement: The OpenSCAD GUI viewer

**Reason**: OpenSCAD was solid-node's first reliable viewer, but it cannot
present the independent controls, instructions, and continuously evaluated
flexible parts that now define the machine experience. Maintaining its GUI and
PID lifecycle as a second viewer burdens the v0.7 simulation roadmap while
offering a progressively less faithful surface.

**Migration**: Install `solid-node[viewer]` and use `solid develop` or
`solid develop --web`. Use `solid develop --no-web` for the watch-and-build
loop without an interactive viewer. OpenSCAD modelling and
`solid snapshot --renderer openscad` remain supported.
