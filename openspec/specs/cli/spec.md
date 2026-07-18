# CLI Specification

## Purpose

The `solid` command-line interface: command-first grammar, environment
loading, and the five commands (`develop`, `test`, `snapshot`, `new`,
`export`). Encodes ADR-024 (command-first grammar and duck-typed command
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
on a node (all except `new`), and SHALL rewrite a directory path to
`<dir>/__init__.py` before loading.

#### Scenario: Package node

- **WHEN** a user runs `solid develop root` where `root/` is a package
- **THEN** the node is loaded from `root/__init__.py`

### Requirement: Develop command

The system SHALL provide `solid develop <path>`, orchestrating builder and
viewer processes: the web viewer runs by default and is suppressed only when
`--openscad` is passed alone; `--web-dev` additionally spawns the npm dev
server and puts the viewer in proxy mode; `--openscad` opens the project in
an OpenSCAD GUI (PID tracked in `.openscad.pid`); `--debug-builder` and
`--debug-web` run the respective component once in-process for breakpoints.
Each rebuild cycle SHALL respawn the builder and restart the web viewer
process; Ctrl-C exits 0.

#### Scenario: Default develop session

- **WHEN** a user runs `solid develop root`
- **THEN** the builder and the web viewer start, and the model is viewable at
  `http://localhost:<SOLID_NODE_PORT>`

### Requirement: Test command

The system SHALL provide `solid test <path>` with `--failfast`, accepting
either the node file or its companion test file (each resolves to the other).
Runner behavior is specified in the test-framework capability.

#### Scenario: Test file as argument

- **WHEN** a user runs `solid test root/test_gear.py`
- **THEN** the runner resolves and builds the node from `root/gear.py` and
  runs its tests

### Requirement: Snapshot command

The system SHALL provide `solid snapshot <path>` rendering a PNG via the
OpenSCAD CLI, with options: `-o/--output` (default `snapshot.png`), `--time`
(0.0–1.0, validated, default 0.0, applied via `set_keyframe`), `--camera`
(gimbal or vector spec), `--autocenter`, `--viewall`, `--imgsize` (default
`1920x1080`, validated), `--projection` (`ortho`|`perspective`),
`--colorscheme` (the 11 OpenSCAD schemes, default Cornfield), mutually
exclusive `--render`/`--preview`, and `--view` (comma-separated of axes,
crosshairs, edges, scales, wireframe). Without a `DISPLAY` it SHALL wrap the
render under `xvfb-run -a`, and error clearly if xvfb is also unavailable.

#### Scenario: Headless snapshot

- **WHEN** an agent runs `solid snapshot root --time 0.5 -o pose.png` on a
  machine with no X display but xvfb installed
- **THEN** a PNG of the assembly at `$t = 0.5` is written to `pose.png`

### Requirement: New command

The system SHALL provide `solid new <name>` scaffolding a project offline
from templates packaged in the wheel: `<name>/root/__init__.py` plus a
`.gitignore`. It SHALL refuse to overwrite an existing directory (exit 1) and
print next steps including `solid develop root`.

#### Scenario: Fresh project

- **WHEN** a user runs `solid new myproject` in an empty directory
- **THEN** `myproject/root/__init__.py` and `myproject/.gitignore` are
  created with no network access

### Requirement: Export command

The system SHALL provide `solid export <path>` with `-o/--output` (default
`export`), `--fps` (default 30), `--frames` (default 360), and `--no-widget`.
A node that fails to load reports to stderr and exits 1. Artifact contents
are specified in the export capability.

#### Scenario: Default export

- **WHEN** a user runs `solid export root -o docs/_exports/root`
- **THEN** the output directory contains `manifest.json`, `models/`, and the
  embeddable widget files
