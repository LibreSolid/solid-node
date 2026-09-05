## MODIFIED Requirements

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

### Requirement: Test command

The system SHALL provide `solid test [reference]` with `--failfast`, accepting
a node reference in any accepted spelling, or the path of a companion test file,
which resolves to the node module it exercises. Runner behavior is specified in
the test-framework capability.

`solid test --all` SHALL run, as one test run reported once, the tests of every
declared model in declaration order, each model built in its own build
directory. A model that fails to load or build SHALL be reported as a failure
of that model and SHALL NOT stop the run unless `--failfast` is given. The
command SHALL NOT accept a reference beside the flag and SHALL fail in a
project that declares no models.

#### Scenario: Test file as argument

- **WHEN** a user runs `solid test windmill/test_gear.py`
- **THEN** the runner resolves and builds the nodes defined in
  `windmill/gear.py` and runs their tests

#### Scenario: One node by qualifier

- **WHEN** a user runs `solid test windmill.gear:Gear`
- **THEN** the runner builds `Gear` and runs its own test methods and the test
  cases bound to it

#### Scenario: Every declared model is tested

- **WHEN** a user runs `solid test --all` in a project declaring two models,
  each with companion tests
- **THEN** one run executes both models' tests, the summary counts all of
  them, and the exit status is nonzero iff any test failed

## ADDED Requirements

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
