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

The system SHALL require a `path` positional for every command that operates
on a node (all except `new` and `viewer`), and SHALL rewrite a directory path to
`<dir>/__init__.py` before loading.

#### Scenario: Package node

- **WHEN** a user runs `solid develop root` where `root/` is a package
- **THEN** the node is loaded from `root/__init__.py`

#### Scenario: A command that operates on the installation

- **WHEN** a user runs `solid viewer` with no further argument
- **THEN** the command runs and does not require or load a node

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

### Requirement: Build command

The system SHALL provide `solid build <path>` as a node-scoped command using
the command-first grammar and shared directory-to-`__init__.py` path
resolution. On success it SHALL publish the complete normal build directory,
including the viewer snapshot and its referenced model artifacts.

#### Scenario: Build command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `build`

#### Scenario: Build output is available to a viewer host
- **WHEN** a user runs `solid build root` successfully
- **THEN** a framework viewer host can read the completed `_build` directory
  without importing `root`

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

### Requirement: Test command

The system SHALL provide `solid test <path>` with `--failfast`, accepting
either the node file or its companion test file (each resolves to the other).
Runner behavior is specified in the test-framework capability.

#### Scenario: Test file as argument

- **WHEN** a user runs `solid test root/test_gear.py`
- **THEN** the runner resolves and builds the node from `root/gear.py` and
  runs its tests

### Requirement: Snapshot command

The system SHALL provide `solid snapshot <path>` rendering a PNG, with options:
`-o/--output` (default `snapshot.png`), `--time` (0.0–1.0, validated, default
0.0, applied via `set_keyframe`), `--camera` (gimbal or vector spec),
`--autocenter`, `--viewall`, `--imgsize` (default `1920x1080`, validated),
`--projection` (`ortho`|`perspective`), `--colorscheme` (the 11 OpenSCAD
schemes, default Cornfield), mutually exclusive `--render`/`--preview`,
`--view` (comma-separated of axes, crosshairs, edges, scales, wireframe), and
`--renderer` (`openscad`|`web`, default `openscad`).

With `--renderer openscad` the image is produced by the OpenSCAD CLI; without a
`DISPLAY` it SHALL wrap the render under `xvfb-run -a`, and error clearly if
xvfb is also unavailable.

With `--renderer web` the image is produced by the packaged browser viewer with
a transparent background, as specified in the web-snapshot capability, and no
X display is required. `--projection`, `--colorscheme`, `--view`, `--render`,
and `--preview` are OpenSCAD-only: supplying any of them together with
`--renderer web` SHALL fail with an error naming them rather than ignoring
them. Options with renderer-independent meaning — `-o/--output`, `--time`,
`--imgsize`, `--camera` — SHALL behave equivalently under either renderer, and
`--autocenter` and `--viewall` describe what the web renderer does by default.

#### Scenario: Headless snapshot

- **WHEN** an agent runs `solid snapshot root --time 0.5 -o pose.png` on a
  machine with no X display but xvfb installed
- **THEN** a PNG of the assembly at `$t = 0.5` is written to `pose.png`

#### Scenario: Transparent snapshot for a host

- **WHEN** an agent runs `solid snapshot root --renderer web -o card.png`
- **THEN** a PNG of the assembly with a transparent background is written to
  `card.png`

#### Scenario: An OpenSCAD-only option with the web renderer

- **WHEN** an agent runs `solid snapshot root --renderer web --colorscheme
  Metallic`
- **THEN** the command fails, reporting that `--colorscheme` is not supported
  by the web renderer, and writes no image

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

The system SHALL provide `solid export <path>` with `-o/--output` (default
`export`), `--fps` (default 30), `--frames` (default 360), and `--no-widget`.
A node that fails to load reports to stderr and exits 1. Artifact contents
are specified in the export capability.

#### Scenario: Default export

- **WHEN** a user runs `solid export root -o docs/_exports/root`
- **THEN** the output directory contains `manifest.json`, `models/`, and the
  embeddable widget files

### Requirement: Viewer command

The system SHALL provide `solid viewer`, a command that takes no node path and
prints one JSON object on standard output with the absolute path of the
installed viewer bundle and its integer API version. When no built bundle is
installed it SHALL print nothing on standard output, report the remedy on
standard error, and exit 1.

#### Scenario: Viewer command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `viewer`

#### Scenario: A consumer reads the installed viewer

- **WHEN** a program runs `solid viewer` against an installation with a built
  bundle
- **THEN** it parses one JSON object carrying the bundle path and API version,
  and the command exits 0

#### Scenario: No bundle installed

- **WHEN** a user runs `solid viewer` in an installation with no built bundle
- **THEN** the command exits 1 and standard error names how to obtain one
