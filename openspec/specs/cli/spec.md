# CLI Specification

## Purpose

The `solid` command-line interface: command-first grammar, environment
loading, and the commands (`develop`, `test`, `snapshot`, `new`, `export`,
`viewer`). Encodes ADR-024 (command-first grammar and duck-typed command
registry), ADR-021 (snapshot command for agent autonomy), and the process
orchestration retained after ADR-018.

Code: `solid_node/cli.py`, `solid_node/manager/{develop,test,snapshot,new,
export}.py`.
## Requirements
### Requirement: Command-first grammar with migration guard

The system SHALL parse `solid <command> <path> [options]` with one argparse
subparser per command, using each command's docstring as help. When invoked
with the pre-0.4 path-first order (`argv[1]` unknown but `argv[2]` a known
command), it SHALL exit with code 2 and the message "The CLI grammar changed
in 0.4: commands come first. Try: solid {command} {path} [options]". With no
subcommand it prints help.

#### Scenario: Legacy grammar

- **WHEN** a user runs `solid mynode.py develop`
- **THEN** the CLI exits with code 2 and prints the migration hint

### Requirement: Dotenv loading with environment precedence

The system SHALL read `./.env` from the current directory before every
command, applying `KEY=value` lines via `os.environ.setdefault` — real
environment variables always win. Recognized variables: `SOLID_NODE_PORT`
(backend, default 8000), `SOLID_NODE_FRONTEND_PORT` (npm dev server, default
3000), `SOLID_BUILD_DIR` (default `_build`).

#### Scenario: Worktree ports

- **WHEN** a worktree's `.env` sets `SOLID_NODE_PORT=8003`
- **THEN** `solid develop` run from that directory serves on port 8003,
  unless the variable was already set in the real environment

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

### Requirement: Callback mode validation

The `solid develop` command SHALL accept `--callback URL` in normal web mode
and in `--no-web` mode, and reject it with `--openscad` or `--web-dev` with a
clear argument error. `solid build` SHALL NOT accept a callback option.

#### Scenario: Callback requested for OpenSCAD mode

- **WHEN** a user runs `solid develop --openscad --callback URL`
- **THEN** the command exits with a clear argument error before starting
  development processes

#### Scenario: Callback for an external viewer host

- **WHEN** a user runs `solid develop --no-web --callback URL`
- **THEN** the command starts the builder watch loop without a web viewer and
  POSTs the callback after each complete successful build

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

### Requirement: New command

The system SHALL provide `solid new <name>` scaffolding a project offline from
templates packaged in the wheel. After normalizing `<name>` to an
identifier-safe package name `<package>` and deriving `<ClassName>`, it SHALL
create:

- `<package>/pyproject.toml`, declaring
  `model = "<package>.<package>:<ClassName>"`;
- `<package>/<package>/__init__.py`;
- `<package>/<package>/<package>.py`, defining the model node;
- `<package>/<package>/test_<package>.py`, defining a companion `TestCase`
  whose generated `test_solid_integrity` calls
  `assertNoDisconnectedSolids(self.node)` and whose generated
  `test_assembly_integrity` calls `assertNoSolidInterference(self.node)`; and
- `<package>/.gitignore`.

The node module and companion test filenames SHALL use the same normalized
package name, so the existing companion-file mapping discovers the tests
without a new loader convention. The generated tests SHALL be ordinary project
source: visible, editable, and deletable, with no registration or automatic
execution outside `solid test`. The assembly test SHALL use the runner's
default testing instant and SHALL remain valid when the generated model is a
single rigid node.

The command SHALL refuse to overwrite an existing target directory (exit 1)
and SHALL print next steps for entering the generated directory and running the
project.

#### Scenario: Fresh project includes both declared integrity tests

- **WHEN** a user runs `solid new my-project` in an empty directory
- **THEN** `my_project/my_project/my_project.py`,
  `my_project/my_project/test_my_project.py`, `my_project/pyproject.toml`, and
  `my_project/.gitignore` are created with no network access
- **AND** the companion test explicitly calls
  `assertNoDisconnectedSolids(self.node)` and
  `assertNoSolidInterference(self.node)` in separate named tests

#### Scenario: The scaffolded tests are discovered normally

- **WHEN** the user enters a freshly scaffolded project and runs `solid test`
- **THEN** the existing companion-test loader discovers `test_<package>.py`
  and the summary counts exactly the two generated integrity tests
- **AND** both pass for the generated single-rigid-node model

#### Scenario: Non-test commands do not execute the scaffolded tests

- **WHEN** a freshly scaffolded project is run with `solid build`,
  `solid develop`, or `solid snapshot`
- **THEN** the generated tests are not discovered or executed

#### Scenario: Existing target is preserved

- **WHEN** the normalized target directory already exists
- **THEN** `solid new` exits 1 without overwriting it

### Requirement: Export command

The system SHALL provide `solid export [reference]` with `-o/--output` (default
`export`), `--fps` (default 30), `--frames` (default 360), and `--no-widget`.
A node that fails to load reports to stderr and exits 1. Artifact contents
are specified in the export capability.

#### Scenario: Default export

- **WHEN** a user runs `solid export -o docs/_exports/windmill`
- **THEN** the output directory contains `manifest.json`, `models/`, and the
  embeddable widget files

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

### Requirement: Root parameter overrides

Every command that loads a node SHALL accept `--set name=value`, repeatable,
applied to the root node's declared parameters under the `declarative-nodes`
capability. A value SHALL be parsed by the parameter's declared kind — a
float for `Length`, `Angle`, `Ratio` and `Scalar`, an integer for `Count`,
`true` or `false` for `Flag` — and checked by the declared constraints
exactly as a Python caller's value would be. A name that is not a declared
parameter of the root, or names a derived parameter, SHALL fail listing the
root's settable parameters; a root that declares no parameters SHALL refuse
the flag naming the root. The develop command SHALL apply the same overrides
to every rebuild of its watch loop.

#### Scenario: A build at another bore

- **WHEN** `solid build engine.py --set bore=32.0` runs on a root declaring
  `bore = Length(30.0)`
- **THEN** the build realizes the root with `bore` at `32.0`, every
  dependent child follows, and the published artifacts are those of that
  parameter set

#### Scenario: A value the declaration refuses

- **WHEN** `--set count=1` names a `Count(8, min=2)`, or `--set
  guard_installed=maybe` names a `Flag`
- **THEN** the command fails naming the parameter and the violated
  constraint or the expected form, and nothing is built

#### Scenario: An unknown name

- **WHEN** `--set boar=32.0` names no declared parameter of the root
- **THEN** the command fails listing the root's settable parameters

#### Scenario: A node without a default is loaded directly

- **WHEN** `solid develop piston.py` loads a leaf declaring
  `diameter = Length()` without `--set diameter=...`
- **THEN** the command fails naming the class and the parameter, and
  `solid develop piston.py --set diameter=29.4` loads it

#### Scenario: Overrides survive a reload

- **WHEN** a develop session started with `--set bore=32.0` rebuilds after
  a source edit
- **THEN** the rebuilt root is realized with `bore` at `32.0`

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

