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
that operates on a node (all except `new`, `viewer` and `models`). When the
positional is given, it SHALL be a node reference in any of the four spellings
the loader accepts: a declared model name, `package.module:Class`,
`path/to/file.py`, or `path/to/file.py:Class`. A bare word that equals a name
declared in the project manifest's `[tool.solid-node.models]` table SHALL
resolve to that model; a bare word that is not a declared name SHALL be read
as a module qualifier exactly as today, and a reference containing `:`, `/` or
`.` is never a model name.

When the positional is omitted, the command SHALL operate on the project's
default model: the model named by `[tool.solid-node] model`, whether that key
holds a reference or, beside a `models` table, a declared name. When the
project declares models and no default, the command SHALL exit nonzero with an
error listing the declared names, and SHALL NOT pick one.

The system SHALL NOT rewrite a directory argument to `<dir>/__init__.py`. A
directory is not a node reference and SHALL be reported as an error naming the
accepted spellings.

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

#### Scenario: A declared name is a reference

- **WHEN** a user runs `solid build wall_clock_02` in a project whose manifest
  declares `wall_clock_02 = "design.wall_clock_02.clock:WallClock02"`
- **THEN** the command builds `WallClock02` into that model's build directory

#### Scenario: No argument uses the default among declared models

- **WHEN** a user runs `solid develop` in a project declaring models and
  `model = "wall_clock_01"`
- **THEN** the session opens on `wall_clock_01`

#### Scenario: No argument and no default

- **WHEN** a user runs `solid build` in a project declaring models and no
  `model` key
- **THEN** the command exits nonzero listing the declared model names and
  builds nothing

#### Scenario: A bare word that is not a declared name

- **WHEN** a user runs `solid build sail` in a project whose `models` table
  has no `sail` key
- **THEN** the reference is read as the module qualifier `sail`, as before

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
- **THEN** the builder and the browser viewer start on the project model, and the
  model is viewable at `http://localhost:<SOLID_NODE_PORT>`

#### Scenario: Default develop session without the viewer

- **WHEN** a user runs `solid develop` in an installation without
  `solid-node-viewer`, whether or not OpenSCAD is installed
- **THEN** the command fails before starting development processes, naming
  `pip install "solid-node[viewer]"`, and does not open OpenSCAD

#### Scenario: The web viewer is requested but not installed

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

### Requirement: Build command

The system SHALL provide `solid build [reference]` as a node-scoped command
using the command-first grammar and shared node reference resolution. On success
it SHALL publish the complete build directory of the resolved model, including
the viewer snapshot and its referenced model artifacts. When the reference
cannot be resolved to a node class, the command SHALL report it on standard
error and exit with the model-not-found status.

`solid build --all` SHALL build every declared model in declaration order,
each into its own build directory, and SHALL NOT accept a reference beside the
flag. A model whose build fails SHALL NOT stop the walk: the command SHALL go
on to the next model, report each model's outcome on standard error as it
settles, and exit nonzero when any model failed and zero when every model is
current. In a project that declares no models, `--all` SHALL fail with an
error saying so.

#### Scenario: Build command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `build`

#### Scenario: Build output is available to a viewer host

- **WHEN** a user runs `solid build` successfully
- **THEN** a framework viewer host can read the completed build directory
  without importing project code

#### Scenario: Unresolvable reference

- **WHEN** a user runs `solid build windmill.windmill:NoSuchClass`
- **THEN** the command reports the reference on standard error and exits with
  the model-not-found status

#### Scenario: Every declared model is built

- **WHEN** a user runs `solid build --all` in a project declaring
  `wall_clock_01` and `wall_clock_02`
- **THEN** both models are published, each in its own build directory, and
  the command exits 0

#### Scenario: One model fails, the rest still build

- **WHEN** `solid build --all` runs and `wall_clock_01` fails to assemble
  while `wall_clock_02` builds
- **THEN** `wall_clock_02` is published, `wall_clock_01`'s directory carries
  its `errors.json`, the report names both outcomes, and the command exits
  nonzero

#### Scenario: A model whose module does not import

- **WHEN** `solid build --all` runs and `wall_clock_01`'s module raises on
  import while `wall_clock_02` builds
- **THEN** the failure is recorded in `wall_clock_01`'s `errors.json`, the
  walk goes on to publish `wall_clock_02`, and the command exits nonzero

#### Scenario: All in a single-model project

- **WHEN** a user runs `solid build --all` in a project that declares no
  models
- **THEN** the command exits nonzero saying the project declares no models

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
- **THEN** the command starts the builder watch loop without a browser viewer and
  POSTs the callback after each complete successful build

### Requirement: Test command

The system SHALL provide `solid test [reference]` with `--failfast`, the
mutually exclusive kernel selectors `--exact` and `--faceted`,
`--volume-epsilon MM3`, and `--placement-quantum MM`, accepting a node
reference in any accepted spelling, or the path of a companion test file,
which resolves to the node module it exercises. Without a selector the kernel
comes from `SOLID_TEST_KERNEL`, without `--volume-epsilon` a faceted run's
epsilon comes from `SOLID_TEST_VOLUME_EPSILON`, and without
`--placement-quantum` the run's placement quantum comes from
`SOLID_TEST_PLACEMENT_QUANTUM`, else the framework's default — all read
through the same `.env` rule as the other `SOLID_*` settings. Unlike the
volume epsilon, the placement quantum is accepted under both kernels. Runner
behavior, the resolution order and the errors are specified in the
test-framework capability.

`solid test --all` SHALL run, as one test run reported once, the tests of every
declared model in declaration order, each model built in its own build
directory. A model that fails reference resolution, load, construction,
initial keyframe binding, render, assembly, or artifact generation SHALL be
reported and counted once as a failure of that declared model. Its tests SHALL
NOT run, and the runner SHALL proceed to the next declared model unless
`--failfast` is given. The final report and exit status SHALL include every
model failure and test result observed before the run completed or stopped.
The command SHALL NOT accept a reference beside the flag and SHALL fail in a
project that declares no models.

#### Scenario: Test file as argument

- **WHEN** a user runs `solid test windmill/test_gear.py`
- **THEN** the runner resolves and builds the nodes defined in
  `windmill/gear.py` and runs their tests

#### Scenario: One node by qualifier

- **WHEN** a user runs `solid test windmill.gear:Gear`
- **THEN** the runner builds `Gear` and runs its own test methods and the test
  cases bound to it

#### Scenario: A developer runs the fast kernel by flag

- **WHEN** a user runs `solid test --faceted --volume-epsilon 0.5`
- **THEN** the runner compares every pair on meshes with that epsilon and
  labels the run as faceted

#### Scenario: Both selectors together are refused

- **WHEN** a user runs `solid test --exact --faceted`
- **THEN** argument parsing fails naming the two flags as mutually exclusive

#### Scenario: A developer sets the placement quantum

- **WHEN** a user runs `solid test --placement-quantum 0`
- **THEN** the run's verdict memo keys on the exact bytes of the relative
  placement, under whichever kernel the run selected

#### Scenario: Every declared model is tested

- **WHEN** a user runs `solid test --all` in a project declaring two models,
  each with companion tests
- **THEN** one run executes both models' tests, the summary counts all of
  them, and the exit status is nonzero iff any test failed

#### Scenario: A model build failure is aggregated

- **WHEN** the first declared model fails during construction, render,
  assembly, or artifact generation and a later declared model can build
- **AND** the user runs `solid test --all` without `--failfast`
- **THEN** the first model is named and counted once as failed
- **AND** the later model's tests run
- **AND** one final report covers both models and the command exits nonzero

#### Scenario: A model build failure honors failfast

- **WHEN** the first declared model fails to build and a later declared model
  can build
- **AND** the user runs `solid test --all --failfast`
- **THEN** the first model is named and counted once as failed
- **AND** the later model does not build or run tests
- **AND** one final report covers the failure and the command exits nonzero

### Requirement: Snapshot command

The system SHALL provide `solid snapshot [reference]` rendering a PNG, with
options: `-o/--output` (defaulting to a file name derived from the resolved
node), `--time` (0.0–1.0, validated, default
0.0, applied via `set_keyframe`), `--camera` (gimbal or vector spec),
`--autocenter`, `--viewall`, `--imgsize` (default `1920x1080`, validated),
`--projection` (`ortho`|`perspective`), `--colorscheme` (the 11 OpenSCAD
schemes, default Cornfield), mutually exclusive `--render`/`--preview`,
`--view` (comma-separated of axes, crosshairs, edges, scales, wireframe),
`--renderer` (`openscad`|`web`, default `openscad`), and `--drive NAME=VALUE`
(repeatable).

`--drive` SHALL bind a DECLARED DRIVER by its qualified id, to a value parsed
as a number and checked by the declaration exactly as `set_state` checks it,
after the node is loaded and before it is keyframed and assembled, under
either renderer. It is distinct from `--set`, which reaches the root's
declared parameters; a driver is not a parameter and a parameter is not a
driver. A name that is not a declared driver of the tree SHALL fail listing
the drivers the tree publishes, and nothing SHALL be rendered.

A `--drive` naming a JOINT COORDINATE of a running root SHALL be REFUSED by
name, saying that a coordinate's value is what the run makes of it and
naming the drivers that can be set instead. The refusal states a fact rather
than a preference: with no run to own it, the enumeration that binding runs
immediately recomputes that coordinate from the drivers, so the value would
be silently discarded.

Under a running root the image is therefore the untimed REST POSE at the
requested driver values — the state a simulation itself starts from, and
admissible by construction. A state carrying HISTORY is not posed from the
command line: only a run knows which banks are reachable.

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

#### Scenario: A driver posed for a still

- **WHEN** an agent runs `solid snapshot --drive units_entry=3` on a project
  declaring that driver
- **THEN** the image shows the machine posed at that driver value, and the
  drivers left unnamed stand at their declared defaults

#### Scenario: A coordinate is not a driver

- **WHEN** an agent runs `solid snapshot --drive units.drum.turn=108` on a
  running root
- **THEN** the command fails naming that id as a joint coordinate the run
  owns, lists the declared drivers, and writes no image

#### Scenario: A name that is neither

- **WHEN** `--drive crnak=3` names no declared driver
- **THEN** the command fails listing the drivers the tree publishes, and
  writes no image

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

### Requirement: Snapshot time under a declared time base

`solid snapshot --time` SHALL keep its meaning as a 0.0–1.0 position on the
animation timeline under either renderer. When the snapshotted root declares
a time base, the command SHALL keyframe the node at `time * loop` seconds
before rendering, so the image shows the same instant the viewer shows at
that slider position; when the root declares none it SHALL keyframe the
fraction as before. Validation of the option does not change.

When the snapshotted root declares `time = Time.running()` there is no
timeline to be a position on: elapsed simulation seconds never wrap and the
document publishes no loop. A non-zero `--time` on such a root SHALL be
REFUSED by name, saying that a running root has no timeline and naming
`--drive` as the way to pose it; `--time 0.0`, the default, SHALL be
accepted and SHALL keyframe zero, which is the instant the rest pose is
defined at.

#### Scenario: A fraction lands on the declared instant

- **WHEN** `solid snapshot --time 0.5` runs on a project whose root declares
  `time = Time(loop=43200)`
- **THEN** the node is keyframed at 21600 seconds and the image shows the
  machine half a loop in

#### Scenario: An undeclared root is keyframed at the fraction

- **WHEN** `solid snapshot --time 0.5` runs on a project whose root declares
  no time base
- **THEN** the node is keyframed at `0.5`, exactly as before

#### Scenario: A running root has no timeline

- **WHEN** `solid snapshot --time 0.5` runs on a project whose root declares
  `time = Time.running()`
- **THEN** the command fails saying a running root has no timeline, naming
  `--drive`, and writes no image

#### Scenario: The default time is accepted on a running root

- **WHEN** `solid snapshot` runs on a running root with no `--time`
- **THEN** the node is keyframed at zero and the image shows the rest pose

### Requirement: New command

The system SHALL provide `solid new <name>` scaffolding a project offline from
templates packaged in the wheel. It SHALL normalize the input basename to an
ASCII Python package identifier `<package>` by replacing non-alphanumeric or
underscore characters with underscores, removing boundary underscores, and
using `project` when nothing remains. If that sanitized name starts with a
digit or is a Python keyword, the command SHALL prefix it with `project_`.
After deriving `<ClassName>` from that final package identifier, it SHALL
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
and SHALL print next steps for entering the generated directory and running
`solid develop`. It SHALL NOT predict a viewer kind or endpoint; the develop
command owns viewer selection, configured ports, and dependency diagnostics.

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

#### Scenario: Digit-leading project is made identifier-safe

- **WHEN** a user runs `solid new 3d-printer`
- **THEN** the command creates `project_3d_printer` with package
  `project_3d_printer`, class `Project3dPrinter`, and a matching manifest
- **AND** its generated source compiles, builds, and tests without edits

#### Scenario: Python-keyword project is made identifier-safe

- **WHEN** a user runs `solid new class`
- **THEN** the command creates `project_class` with package `project_class`,
  class `ProjectClass`, and a matching manifest
- **AND** its generated source compiles, builds, and tests without edits

#### Scenario: Next steps defer viewer details to develop

- **WHEN** `solid new my-project` succeeds in any viewer installation or port
  configuration
- **THEN** its next steps name the generated directory and `solid develop`
- **AND** they do not claim a browser URL or viewer kind

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

### Requirement: Models command

The system SHALL provide `solid models`, a command that takes no node reference
and lists the project's models without importing project code. For each model
it SHALL report the name (absent for a project that declares no models), the
reference, whether it is the default, the build directory, and a state judged
from that directory alone: `failed` when it holds an `errors.json`, `published`
when it holds a `viewer.json` and no `errors.json`, and `unbuilt` otherwise.
Models SHALL be listed in declaration order.

Without a flag the command SHALL print one line per model on standard output.
With `--json` it SHALL print exactly one JSON object holding the project root,
the build root, the default model's name or `null`, and the list of models
with the fields above, so a host can read a project's models the way it reads
`solid viewer`. A malformed manifest SHALL be reported on standard error with
exit status 1 and no standard output.

#### Scenario: Models command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `models`

#### Scenario: A multi-model project is listed

- **WHEN** a user runs `solid models` in a project declaring `wall_clock_01`
  (the default, built) and `wall_clock_02` (never built)
- **THEN** the output lists `wall_clock_01` as default and `published` and
  `wall_clock_02` as `unbuilt`, in that order

#### Scenario: A host reads the models

- **WHEN** a program runs `solid models --json` in a project declaring models
- **THEN** it parses one JSON object whose `models` array carries each model's
  `name`, `reference`, `default`, `build_dir` and `state`, and the command
  exits 0 without having imported the project's modules

#### Scenario: A single-model project is listed

- **WHEN** a user runs `solid models --json` in a project declaring only
  `model = "windmill.windmill:Windmill"`
- **THEN** the object's `models` array holds one entry with `name` null, that
  reference, `default` true and the build root as its `build_dir`

#### Scenario: A model that failed to build

- **WHEN** a declared model's build directory holds an `errors.json`
- **THEN** `solid models` reports that model's state as `failed`

### Requirement: Import-step command

The system SHALL provide `solid import-step FILE [--into PACKAGE_DIR]
[--model NAME]`, a one-shot scaffold that reads a STEP document's assembly
structure and writes project-owned source the pilot then edits. It SHALL
take no node reference and SHALL NOT load a node.

`--into` names the package directory the source is written into and SHALL
default to the current directory; the command SHALL create it when it does
not exist and SHALL write an `__init__.py` into it when it holds none, so
the generated modules are importable as a package. `--model` names the
model and SHALL default to a name derived from the document's root product,
or from the STEP file's stem when that product is unnamed.

The command SHALL write exactly two files into that directory, `parts.py`
and `assembly.py`, whose content is specified in the step-assembly
capability.

The command SHALL never overwrite. When either file already exists it SHALL
write nothing, report which file stopped it, and exit 1, so a pilot's edits
to generated source can never be lost.

The command SHALL write nothing when the reader reports any placement of
the document improper. It SHALL name each improper occurrence with its
determinant and scale factor and exit 1, because the framework's rest
operations cannot express that placement.

The command SHALL NOT modify `pyproject.toml`. It SHALL print the manifest
lines that declare the generated model, for the pilot to add, together with
the next steps for building it.

The command needs the exact-geometry kernel, as every exact path does. When
`cadquery` or the STEP reader cannot be imported it SHALL report that the
command needs them, name the extra that installs them, and exit 1, rather
than fail with an import traceback.

A `FILE` that does not exist, or that the STEP reader cannot read or
transfer, SHALL be reported on standard error with exit status 1 and no
file written.

#### Scenario: The command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `import-step` with its docstring help

#### Scenario: A vendor assembly is scaffolded

- **WHEN** a user runs `solid import-step vendor/actuator.stp --into
  actuator --model actuator` in an empty project
- **THEN** `actuator/parts.py` and `actuator/assembly.py` are written, one
  leaf class per part of the document and one assembly class per assembly
  product, and the command prints the manifest lines declaring the model
  and exits 0

#### Scenario: Generated source is never overwritten

- **WHEN** the command is run a second time into a directory that already
  holds `parts.py`
- **THEN** neither file is written, the message names `parts.py`, and the
  command exits 1

#### Scenario: An improper placement stops the scaffold

- **WHEN** the document places a product through a mirrored or scaled
  transform
- **THEN** no file is written, the message names that occurrence with its
  determinant and scale factor, and the command exits 1

#### Scenario: The manifest is printed, not edited

- **WHEN** the command completes in a project holding a `pyproject.toml`
- **THEN** the file is unchanged on disk and the lines that would declare
  the generated model are printed for the user to add

#### Scenario: The kernel is missing

- **WHEN** the command is run in an installation without the exact-geometry
  kernel
- **THEN** it reports that `import-step` needs it, names the extra that
  installs it, exits 1, and writes nothing

#### Scenario: An unreadable file is reported

- **WHEN** `FILE` does not exist or is not a STEP document the reader can
  transfer
- **THEN** the failure is reported on standard error, nothing is written,
  and the command exits 1
