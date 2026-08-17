## MODIFIED Requirements

### Requirement: Node path resolution

The system SHALL accept an optional `reference` positional for every command
that operates on a node (all except `new` and `viewer`). When the positional is
omitted, the command SHALL operate on the model named by the project manifest's
`[tool.solid-node] model` key. When it is given, it SHALL be a node reference in
any of the three spellings the loader accepts.

The system SHALL NOT rewrite a directory argument to `<dir>/__init__.py`. A
directory is not a node reference and SHALL be reported as an error naming the
three accepted spellings.

#### Scenario: No argument uses the project model

- **WHEN** a user runs `solid build` anywhere inside a project whose manifest
  declares `model = "windmill.windmill:Windmill"`
- **THEN** the command builds that node

#### Scenario: Any node by qualifier

- **WHEN** a user runs a node-scoped command with `windmill.windmill:Sail`
- **THEN** the command operates on `Sail`, not on the project model

#### Scenario: A directory is not a reference

- **WHEN** a user passes a directory to a node-scoped command
- **THEN** the command exits nonzero with an error naming the accepted
  reference spellings

#### Scenario: A command that operates on the installation

- **WHEN** a user runs `solid viewer` with no further argument
- **THEN** the command runs and does not require or load a node

### Requirement: Develop command

The system SHALL provide `solid develop [reference]`, orchestrating builder and
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

- **WHEN** a user runs `solid develop`
- **THEN** the builder and the web viewer start on the project model, and the
  model is viewable at `http://localhost:<SOLID_NODE_PORT>`

#### Scenario: Headless develop session

- **WHEN** a user runs `solid develop --no-web`
- **THEN** the builder watch loop runs and rebuilds on source changes, and no
  listener is bound on `SOLID_NODE_PORT`

#### Scenario: Web viewer requested and suppressed at once

- **WHEN** a user runs `solid develop --no-web --web-dev`
- **THEN** the command exits with a clear argument error before starting
  development processes

### Requirement: Build command

The system SHALL provide `solid build [reference]` as a node-scoped command
using the command-first grammar and shared node reference resolution. On success
it SHALL publish the complete normal build directory, including the viewer
snapshot and its referenced model artifacts. When the reference cannot be
resolved to a node class, the command SHALL report it on standard error and exit
with the model-not-found status.

#### Scenario: Build command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `build`

#### Scenario: Build output is available to a viewer host

- **WHEN** a user runs `solid build` successfully
- **THEN** a framework viewer host can read the completed `_build` directory
  without importing project code

#### Scenario: Unresolvable reference

- **WHEN** a user runs `solid build windmill.windmill:NoSuchClass`
- **THEN** the command reports the reference on standard error and exits with
  the model-not-found status

### Requirement: Test command

The system SHALL provide `solid test [reference]` with `--failfast`, accepting
a node reference in any accepted spelling, or the path of a companion test file,
which resolves to the node module it exercises. Runner behavior is specified in
the test-framework capability.

#### Scenario: Test file as argument

- **WHEN** a user runs `solid test windmill/test_gear.py`
- **THEN** the runner resolves and builds the nodes defined in
  `windmill/gear.py` and runs their tests

#### Scenario: One node by qualifier

- **WHEN** a user runs `solid test windmill.gear:Gear`
- **THEN** the runner builds `Gear` and runs its own test methods and the test
  cases bound to it

### Requirement: Snapshot command

The system SHALL provide `solid snapshot [reference]` rendering a PNG via the
OpenSCAD CLI, with options: `-o/--output` (defaulting to a file name derived
from the resolved node), `--time` (0.0–1.0, validated, default 0.0, applied via
`set_keyframe`), `--camera` (gimbal or vector spec), `--autocenter`,
`--viewall`, `--imgsize` (default `1920x1080`, validated), `--projection`
(`ortho`|`perspective`), `--colorscheme` (the 11 OpenSCAD schemes, default
Cornfield), mutually exclusive `--render`/`--preview`, and `--view`
(comma-separated of axes, crosshairs, edges, scales, wireframe). Without a
`DISPLAY` it SHALL wrap the render under `xvfb-run -a`, and error clearly if
xvfb is also unavailable.

Node preparation SHALL hold the project build lock, and SHALL release it before
the OpenSCAD render begins, so a snapshot never blocks a rebuild while an image
is being produced.

#### Scenario: Headless snapshot

- **WHEN** an agent runs `solid snapshot --time 0.5 -o pose.png` on a machine
  with no X display but xvfb installed
- **THEN** a PNG of the project model at `$t = 0.5` is written to `pose.png`

#### Scenario: Snapshotting a sub-assembly

- **WHEN** an agent runs `solid snapshot windmill.windmill:Sail` with no
  `-o`
- **THEN** the image is written to a file derived from the resolved node, not
  to a fixed default name

#### Scenario: A snapshot does not block a rebuild

- **WHEN** a snapshot has finished preparing its node and is rendering the PNG
- **THEN** another process can acquire the project build lock and rebuild the
  same project

### Requirement: New command

The system SHALL provide `solid new <name>` scaffolding a project offline from
templates packaged in the wheel: a package directory and a model module both
named from `<name>`, plus `pyproject.toml` declaring `[tool.solid-node] model`
and a `.gitignore`. Hyphens in `<name>` SHALL become underscores in the package
and module names, and the generated class name SHALL be derived from `<name>` in
CamelCase. It SHALL refuse to overwrite an existing directory (exit 1) and print
next steps including `solid develop`.

#### Scenario: Fresh project

- **WHEN** a user runs `solid new myproject` in an empty directory
- **THEN** `myproject/myproject/myproject.py`, `myproject/pyproject.toml` and
  `myproject/.gitignore` are created with no network access
- **AND** the manifest declares `model = "myproject.myproject:Myproject"`

#### Scenario: A name that is not an identifier

- **WHEN** a user runs `solid new snowman-3`
- **THEN** the scaffold is `snowman_3/snowman_3/snowman_3.py` declaring
  `model = "snowman_3.snowman_3:Snowman3"`

### Requirement: Export command

The system SHALL provide `solid export [reference]` with `-o/--output` (default
`export`), `--fps` (default 30), `--frames` (default 360), and `--no-widget`.
A node that fails to load reports to stderr and exits 1. Artifact contents
are specified in the export capability.

#### Scenario: Default export

- **WHEN** a user runs `solid export -o docs/_exports/windmill`
- **THEN** the output directory contains `manifest.json`, `models/`, and the
  embeddable widget files
