# CLI

## MODIFIED Requirements

### Requirement: Develop command

The system SHALL provide `solid develop [reference]`, orchestrating the
builder and a viewer process. Without a viewer flag the web viewer runs when
the `solid-node-viewer` package is installed and the OpenSCAD GUI viewer runs
otherwise. `--web` requests the web viewer explicitly and SHALL fail, before
starting development processes, naming `pip install "solid-node[viewer]"`
when the viewer is not installed; `--openscad` requests the OpenSCAD GUI
explicitly (PID tracked in `.openscad.pid`); the two MAY be combined; a
requested viewer is never substituted by the other. `--no-web` runs the
builder watch loop alone and SHALL NOT bind `SOLID_NODE_PORT`. The web viewer
SHALL run as the installed viewer package's `serve` command on the project's
build directory, in a separate process; `--web-dev` SHALL ask that process to
also start the viewer's own npm dev server and proxy to it; `--debug-builder`
runs the builder once in-process for breakpoints. `--no-web` SHALL be
rejected with a clear argument error when combined with a flag that
explicitly requests the web viewer (`--web`, `--web-dev`), and SHALL be
accepted with `--openscad`. Each rebuild cycle SHALL respawn the builder and
restart the web viewer process when one is running; Ctrl-C exits 0.

#### Scenario: Default develop session

- **WHEN** a user runs `solid develop` in an installation with
  `solid-node-viewer`
- **THEN** the builder and the web viewer start on the project model, and the
  model is viewable at `http://localhost:<SOLID_NODE_PORT>`

#### Scenario: Default develop session without the viewer

- **WHEN** a user runs `solid develop` in an installation without
  `solid-node-viewer` and with `openscad` on the PATH
- **THEN** the builder starts and the model opens in the OpenSCAD GUI, and no
  listener is bound on `SOLID_NODE_PORT`

#### Scenario: Neither viewer can open

- **WHEN** a user runs `solid develop` with no viewer flag in an installation
  without `solid-node-viewer` and without `openscad` on the PATH
- **THEN** the command fails before starting development processes, naming
  both `pip install "solid-node[viewer]"` and installing OpenSCAD

#### Scenario: The web viewer is requested but not installed

- **WHEN** a user runs `solid develop --web` without `solid-node-viewer`
- **THEN** the command fails naming the extra and does not open OpenSCAD in its
  place

#### Scenario: Headless develop session

- **WHEN** a user runs `solid develop --no-web`
- **THEN** the builder watch loop runs and rebuilds on source changes, and no
  listener is bound on `SOLID_NODE_PORT`

#### Scenario: Web viewer requested and suppressed at once

- **WHEN** a user runs `solid develop --no-web --web-dev`
- **THEN** the command exits with a clear argument error before starting
  development processes

#### Scenario: The web viewer runs in its own process

- **WHEN** `solid develop` runs the web viewer
- **THEN** the viewer is the installed viewer package's `serve` command,
  launched through the interpreter running `solid` on the project's build
  directory, and it is restarted after each rebuild cycle

### Requirement: Snapshot command

The system SHALL provide `solid snapshot [reference]` rendering a PNG, with
options: `-o/--output` (defaulting to a file name derived from the resolved
node), `--time` (0.0–1.0, validated, default
0.0, applied via `set_keyframe`), `--camera` (gimbal or vector spec),
`--autocenter`, `--viewall`, `--imgsize` (default `1920x1080`, validated),
`--projection` (`ortho`|`perspective`), `--colorscheme` (the 11 OpenSCAD
schemes, default Cornfield), mutually exclusive `--render`/`--preview`,
`--view` (comma-separated of axes, crosshairs, edges, scales, wireframe), and
`--renderer` (`openscad`|`web`, default `openscad`).

The default renderer SHALL remain `openscad` regardless of whether the
project's model is exact, regardless of whether the binary is installed, and
regardless of whether the viewer package is installed. Choosing a renderer by
availability, or by the project's backends, would change the appearance of
snapshots taken of existing projects; the renderer is selected explicitly and
never substituted, as the web-snapshot capability requires.

With `--renderer openscad` the image is produced by the OpenSCAD CLI; without a
`DISPLAY` it SHALL wrap the render under `xvfb-run -a`, and error clearly if
xvfb is also unavailable. When the OpenSCAD binary itself is unavailable the
command SHALL fail naming it and naming `--renderer web` as the alternative,
and SHALL write no image.

With `--renderer web` the image is produced by the installed viewer package's
capture, run as a separate process on a staging directory the framework
prepares, with a transparent background, as specified in the web-snapshot
capability, and no X display is required. `--projection`, `--colorscheme`,
`--view`, `--render`, and `--preview` are OpenSCAD-only: supplying any of
them together with `--renderer web` SHALL fail with an error naming them
rather than ignoring them. Options with renderer-independent meaning —
`-o/--output`, `--time`, `--imgsize`, `--camera` — SHALL behave equivalently
under either renderer, and `--autocenter` and `--viewall` describe what the
web renderer does by default. When the viewer package is not installed,
`--renderer web` SHALL fail naming `pip install "solid-node[viewer]"` and
write no image.

Node preparation SHALL hold the project build lock, and SHALL release it before
the render begins, so a snapshot never blocks a rebuild while an image is being
produced.

#### Scenario: Headless snapshot

- **WHEN** an agent runs `solid snapshot --time 0.5 -o pose.png` on a
  machine with no X display but xvfb installed
- **THEN** a PNG of the project model at `$t = 0.5` is written to `pose.png`

#### Scenario: Snapshotting a sub-assembly

- **WHEN** an agent runs `solid snapshot windmill.windmill:Sail` with no `-o`
- **THEN** the image is written to a file derived from the resolved node, not
  to a fixed default name

#### Scenario: A snapshot does not block a rebuild

- **WHEN** a snapshot has finished preparing its node and is rendering the image
- **THEN** another process can acquire the project build lock and rebuild the
  same project

#### Scenario: Transparent snapshot for a host

- **WHEN** an agent runs `solid snapshot --renderer web -o card.png` with the
  viewer installed
- **THEN** a PNG of the assembly with a transparent background is written to
  `card.png`

#### Scenario: An OpenSCAD-only option with the web renderer

- **WHEN** an agent runs `solid snapshot --renderer web --colorscheme
  Metallic`
- **THEN** the command fails, reporting that `--colorscheme` is not supported
  by the web renderer, and writes no image

#### Scenario: The OpenSCAD binary is missing

- **WHEN** an agent runs `solid snapshot` on an all-exact project on a
  machine with no `openscad` on the PATH
- **THEN** the command fails naming the missing binary and `--renderer web`,
  and writes no image

#### Scenario: The default does not follow the project's backends

- **WHEN** a snapshot is taken of an all-exact project without choosing a
  renderer, on a machine where OpenSCAD is installed
- **THEN** the OpenSCAD renderer produces the image, as it does for any other
  project

#### Scenario: The default does not follow the viewer's presence

- **WHEN** a snapshot is taken without choosing a renderer in an installation
  with `solid-node-viewer`
- **THEN** the OpenSCAD renderer produces the image

#### Scenario: The web renderer without the viewer

- **WHEN** an agent runs `solid snapshot --renderer web` in an installation
  without `solid-node-viewer`
- **THEN** the command fails naming the extra, and writes no image

### Requirement: Viewer command

The system SHALL provide `solid viewer`, a command that takes no node path and
prints one JSON object on standard output with the absolute path of the
installed viewer bundle, the absolute path of its standalone export page, its
integer API version and the viewer package version. When the viewer package is
not installed it SHALL print nothing on standard output, name
`pip install "solid-node[viewer]"` on standard error, and exit 1.

#### Scenario: Viewer command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `viewer`

#### Scenario: A consumer reads the installed viewer

- **WHEN** a program runs `solid viewer` against an installation with
  `solid-node-viewer`
- **THEN** it parses one JSON object carrying the bundle path, export page,
  API version and package version, and the command exits 0

#### Scenario: No bundle installed

- **WHEN** a user runs `solid viewer` in an installation without
  `solid-node-viewer`
- **THEN** the command exits 1 and standard error names the extra

## ADDED Requirements

### Requirement: The OpenSCAD GUI viewer

`solid develop --openscad` SHALL open the project in OpenSCAD, retaining its
PID lifecycle behaviour: a develop restart while the recorded PID is alive
SHALL NOT open a second window. Opening the GUI is one of the paths that
require the OpenSCAD binary under the `openscad-dependency` capability. When
the flag is given and the binary is unavailable, the system SHALL report that
the OpenSCAD viewer was requested and the binary is missing, rather than
failing at the subprocess launch, and SHALL NOT open the web viewer in its
place.

#### Scenario: Viewer already open

- **WHEN** develop restarts while the recorded OpenSCAD PID is alive
- **THEN** it does not open a second window

#### Scenario: The viewer is requested without the binary

- **WHEN** `solid develop --openscad` runs and no `openscad` is on the PATH
- **THEN** it reports the requested viewer and the missing binary, and does
  not continue with the web viewer instead
