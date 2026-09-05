## MODIFIED Requirements

### Requirement: Project root discovery and model reference

The system SHALL determine a project's root by walking upward from a discovery
origin to the nearest ancestor `pyproject.toml` containing a
`[tool.solid-node]` table, and SHALL treat the directory holding that file as
the project root.

When the table has no `models` sub-table, its `model` key SHALL hold an
entry-point object reference naming the project's model node, in the form
`package.module:ClassName`, and the project SHALL have that one model.

When the table has a `models` sub-table (`[tool.solid-node.models]`), each of
its keys SHALL be a model name and each value an entry-point object reference
in the form `package.module:ClassName`. A model name SHALL be one word of
letters, digits, underscores and hyphens, starting with a letter or underscore,
and SHALL NOT equal the name of a directory at the project root, because that
directory's artifacts mirror into the same place. The table SHALL NOT be
empty. The `model` key MAY then name the project's default model and, when
present, SHALL equal one of the table's keys; a manifest whose `model` holds
anything else beside a `models` table is malformed. A project with the table
and no `model` key has no default model.

A manifest that violates any of these rules SHALL cause a command that needs a
node to fail with an actionable error naming the manifest and the rule.

The discovery origin SHALL be the referenced file when the reference names a
path, because a path identifies a project as surely as it identifies a file.
It SHALL be the working directory when there is no reference, or when the
reference is a qualifier or a declared model name, which carry no location.

The discovered root — never the working directory — SHALL anchor the import
path used to load project modules, the dotted module name computed for a file
loaded by path, the boundary of a node's tracked source closure, and the
project's build root. A command SHALL therefore resolve the same node, the
same source closure, and the same artifact paths from any directory.

When no ancestor `pyproject.toml` carries the table, a command that needs a
node SHALL fail with an actionable error naming the origin it searched from.

#### Scenario: Command run from a subdirectory

- **WHEN** a user runs a node-scoped command from a subdirectory of a project
  whose `pyproject.toml` declares `[tool.solid-node] model`
- **THEN** the project root is discovered from that manifest
- **AND** the node's tracked source closure is the same set it would be from
  the project root

#### Scenario: A path outside the working directory's project

- **WHEN** a user names a path in a different project from the one containing
  the working directory
- **THEN** the root is discovered from that path, and the node is resolved
  against its own project

#### Scenario: No manifest above the origin

- **WHEN** a node-scoped command runs with no argument and no ancestor
  `pyproject.toml` carries a `[tool.solid-node]` table
- **THEN** the command exits nonzero with an error naming the search origin

#### Scenario: A manifest declares several models and a default

- **WHEN** a manifest declares `[tool.solid-node.models]` with
  `wall_clock_01 = "design.wall_clock_01.clock:WallClock01"` and
  `wall_clock_02 = "design.wall_clock_02.clock:WallClock02"`, and
  `model = "wall_clock_01"`
- **THEN** the project has two models named `wall_clock_01` and
  `wall_clock_02`, and its default model is `wall_clock_01`

#### Scenario: The default must be a declared name

- **WHEN** a manifest declares a `models` table and
  `model = "design.wall_clock_01.clock:WallClock01"`
- **THEN** a command that needs a node fails naming the manifest and stating
  that `model` must name one of the declared models

#### Scenario: A model name that shadows a source directory

- **WHEN** a manifest declares a model named `design` and the project root
  contains a directory `design/`
- **THEN** a command that needs a node fails naming the manifest, the name and
  the directory

#### Scenario: A single-model manifest is unchanged

- **WHEN** a manifest declares only `model = "windmill.windmill:Windmill"`
- **THEN** the project has one model, that reference, exactly as before

### Requirement: Build artifact layout

The system SHALL write build artifacts under a build directory, mirroring the
source file's directory, with basename `<script-name>-<uniq_id>`. The
project's **build root** is `$SOLID_BUILD_DIR` (default `_build`): a relative
value, and the default, SHALL resolve against the discovered project root and
never against the working directory, and an absolute value SHALL be used as
given.

For a project that declares no models, the build directory SHALL be the build
root itself, exactly as today. For a declared model, the build directory SHALL
be `<build root>/<name>/`, so that each declared model has its own published
`viewer.json`, its own `errors.json`, its own build lock and its own artifact
sweep, and publishing one model neither replaces nor removes another's
artifacts. A reference that is not a declared model — a sub-node named by
qualifier or path — SHALL build in the build root, as it does today, and the
build root's artifact sweep SHALL NOT descend into a declared model's
directory. A build lock file that lies inside a build directory SHALL be spared
by that directory's sweep.

Whichever directory a command was run from, a project therefore has one build
directory per model and — because the build lock is derived from it — one
build lock per model.

Artifacts per node: `.scad` (base geometry,
no transforms), `.stl` (rendered), and `.stl.lock` during rendering. A node
that is exact under the `exact-geometry` capability SHALL additionally write
`.brep`, holding that node's unplaced exact geometry under the same basename.
World-space spatial math does not use on-disk artifacts — the `mesh`
property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). Every build directory SHALL be an ordinary directory
that every builder writes into directly; the system SHALL NOT publish through
a symlink, a versioned sibling directory, or a private candidate copy. A build
path left as a symlink by an earlier layout SHALL be converted to an ordinary
directory holding the artifacts it referenced.

The `.brep` artifact SHALL be private to the build. No viewer snapshot, export
manifest, or other published document SHALL reference it, and its presence
SHALL NOT alter any document's schema.

#### Scenario: Custom build dir

- **WHEN** `SOLID_BUILD_DIR` is set in the environment
- **THEN** all artifacts, and `errors.json`, are written under that
  directory instead of `_build`

#### Scenario: One build directory whatever the working directory

- **WHEN** a project is built from its root and then from a subdirectory
- **THEN** both builds publish into the same build directory and contend for
  the same build lock

#### Scenario: Consumer reads through the build path

- **WHEN** a consumer opens the published viewer snapshot at the build path
- **THEN** it reads the snapshot without resolving a symlink or naming any
  other directory

#### Scenario: Project published under the previous layout

- **WHEN** a project whose build path is a symlink to a versioned directory is
  built
- **THEN** the build path becomes an ordinary directory holding those
  artifacts, and the versioned siblings are removed

#### Scenario: An exact node writes exact geometry beside its mesh

- **WHEN** an exact rigid node is built
- **THEN** a `.brep` artifact sits beside its `.stl` under the same basename

#### Scenario: A faceted node writes no exact artifact

- **WHEN** a rigid node that is not exact is built
- **THEN** no `.brep` artifact is written for it

#### Scenario: Published documents do not name exact geometry

- **WHEN** a build publishes its viewer snapshot for a project of exact nodes
- **THEN** the document references only `.stl` models and names no `.brep`

#### Scenario: Two declared models publish side by side

- **WHEN** a project declares models `wall_clock_01` and `wall_clock_02` and
  both are built
- **THEN** `_build/wall_clock_01/viewer.json` and
  `_build/wall_clock_02/viewer.json` both exist, each naming only artifacts
  under its own directory, and building the second removed nothing from the
  first

#### Scenario: Declared models do not share a lock

- **WHEN** a build of `wall_clock_01` is rendering
- **THEN** a build of `wall_clock_02` in the same project acquires its own
  lock and does not wait

#### Scenario: A sub-node build does not sweep the models

- **WHEN** a project declaring models builds a sub-node by qualifier, and its
  publication into the build root sweeps unreferenced artifacts
- **THEN** every artifact under the declared models' directories is still
  there

#### Scenario: A single-model project's directory is unchanged

- **WHEN** a project that declares no models is built
- **THEN** its artifacts, `viewer.json` and `errors.json` are written in the
  build root itself, at the paths they have today
