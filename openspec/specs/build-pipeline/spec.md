# Build Pipeline Specification

## Purpose

How source files become STL artifacts: path-based node loading, the build
artifact layout, mtime-equality caching, concurrent render locking, and the
watch-rebuild loop. Encodes ADR-005 (path-based dynamic module loading),
ADR-006 (mtime-based STL caching), ADR-007 (watchdog filesystem monitoring),
ADR-018 (file-based error propagation, superseding the broker of
ADR-016/017), and the loader rules of ADR-026.

Code: `solid_node/core/loader.py`, `solid_node/core/builder.py`,
`solid_node/node/base.py` (artifact/caching layer).
## Requirements
### Requirement: Path-based node loading

The system SHALL load nodes by filesystem path: the loader imports the `.py`
file and returns the single `AbstractBaseNode` subclass defined in it. When a
file defines multiple node classes, the module MUST set a module-level
`NODE = <Class>` marker naming a class defined in that same file; otherwise
the loader raises `AmbiguousNodeError`. Companion tests are discovered as
`test_<file>.py` for module nodes and `test.py` for package nodes.

#### Scenario: Ambiguous module

- **WHEN** a file defines two node classes and no `NODE` marker
- **THEN** loading raises `AmbiguousNodeError`

#### Scenario: Imported classes are ignored

- **WHEN** a file imports node classes but defines exactly one of its own
- **THEN** the loader picks the locally defined class

### Requirement: Build artifact layout

The system SHALL write build artifacts under `$SOLID_BUILD_DIR` (default
`_build`), mirroring the source file's directory, with basename
`<script-name>-<uniq_id>`. Artifacts per node: `.scad` (base geometry,
no transforms), `.stl` (rendered), and `.stl.lock` during rendering.
World-space spatial math does not use on-disk artifacts — the `mesh`
property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). The build path itself SHALL be a symlink to a
versioned sibling directory holding the published artifact set; it SHALL
behave as a directory for ordinary reads, and consumers SHALL reach artifacts
through it without knowing the versioned name.

#### Scenario: Custom build dir

- **WHEN** `SOLID_BUILD_DIR` is set in the environment
- **THEN** all artifacts, and `errors.json`, are written under that
  directory instead of `_build`

#### Scenario: Consumer reads through the build path

- **WHEN** a consumer opens the published viewer snapshot at the build path
- **THEN** it reads the artifact set currently published there without
  resolving or naming the versioned directory

### Requirement: Mtime-equality caching

The system SHALL treat an artifact as up to date iff it exists AND its mtime
equals the node's `mtime`, where `node.mtime` is the maximum source-file
mtime across all files tracked for the node (`node.files`, aggregated
recursively from children). After generating an artifact the system SHALL
back-date its mtime to the source mtime via `os.utime` so the equality holds.
A change to any contributing source file invalidates all ancestor artifacts.

A node's tracked files SHALL include its own source together with the
project-local modules that source imports, transitively. Modules outside the
project tree SHALL NOT be tracked. Where the contributing set cannot be
determined exactly, the system SHALL track more files rather than fewer, so
that an uncertain dependency causes an unnecessary rebuild rather than a stale
artifact.

#### Scenario: Source edit invalidates ancestors

- **WHEN** a leaf's source file is modified
- **THEN** the leaf's STL and every ancestor STL report not-up-to-date and
  are regenerated on the next build

#### Scenario: Imported project module edit invalidates dependants

- **WHEN** a node's source imports a project module that defines no node, and
  that module is modified
- **THEN** the node's artifact reports not-up-to-date and is regenerated with
  the new values on the next build

#### Scenario: A library change does not invalidate

- **WHEN** a node imports a module from outside the project tree
- **THEN** that module is not part of the node's tracked files

#### Scenario: Unchanged sources skip rendering

- **WHEN** `generate_stl` runs and the STL mtime equals `node.mtime`
- **THEN** no OpenSCAD process is launched

### Requirement: Concurrent render locking

The system SHALL guard STL generation with a `.stl.lock` file containing the
rendering process PID, and SHALL treat a lock as stale when that PID is no
longer alive (`os.kill(pid, 0)` fails). A locked node skips generation.

#### Scenario: Stale lock

- **WHEN** a lock file references a dead PID
- **THEN** the node is not considered locked and rendering proceeds

### Requirement: Asynchronous STL render protocol

The system SHALL launch OpenSCAD renders as subprocesses
(`openscad <scad> -o <stl> --export-format binstl`) signalled by raising
`StlRenderStart`, which carries the process, target file, mtime, and lock
file. `build_stls()` SHALL loop, waiting on each started render
(`job.wait()`), until no renders remain; finishing a render stamps the STL
mtime and removes the lock. Non-rigid nodes SHALL be skipped.

#### Scenario: Full build

- **WHEN** `build_stls()` runs on a tree with several stale rigid nodes
- **THEN** each stale STL is rendered exactly once and the call returns with
  all locks removed and mtimes stamped

### Requirement: Watch-rebuild loop

The system SHALL rebuild on change via a single-shot builder: it loads and
assembles the node, watches each file in `node.files` individually
(non-recursive, via watchdog), renders pending STLs, and exits when a watched
`.py` file changes — the develop loop respawns it. Directory events and
`__pycache__` changes are ignored.

#### Scenario: Edit triggers rebuild cycle

- **WHEN** a watched source file is saved during `solid develop`
- **THEN** the builder logs the change, exits, and is respawned to rebuild
  with the new source

### Requirement: File-based build error propagation

The system SHALL report build errors by writing `{"error": ..., "tstamp":
...}` to `errors.json` in the build dir (no broker or socket IPC — ADR-018).
On a successful load the errors file is cleared. An initial-launch failure
SHALL exit non-zero (develop terminates); a failure during reload SHALL NOT
kill the loop — the builder falls back to watching the project directory
recursively, writes the traceback to `errors.json`, and exits cleanly on the
next save so development continues.

#### Scenario: Syntax error during development

- **WHEN** a reload hits a SyntaxError in the edited file
- **THEN** the traceback lands in `errors.json`, the web viewer can surface
  it, and fixing the file resumes building without restarting `solid develop`

#### Scenario: Broken project at launch

- **WHEN** the first build after `solid develop` fails to load the node
- **THEN** develop tears down its child processes and exits non-zero

### Requirement: Build completion is observable

The build pipeline SHALL distinguish a complete successful model publication
from an intermediate render pass, a watched source change, and a failed build.
Command and development lifecycle consumers SHALL use only complete successful
publication as the ready boundary for external observation. A complete
publication SHALL include the viewer snapshot and every model artifact it
references.

#### Scenario: A model needs multiple render passes

- **WHEN** generating a model requires more than one render pass
- **THEN** the pipeline does not report a complete successful publication
  until all current model artifacts and the current viewer snapshot are
  available

### Requirement: Last successful artifacts survive a failed later build

The pipeline SHALL keep the normal project build directory at its last
complete successful artifact state when a later load, assemble, or render
attempt fails.

#### Scenario: Rendering fails after a previous build

- **WHEN** a later render attempt fails after a project has a complete build
- **THEN** consumers of the normal project build directory can continue to
  read the prior complete artifact state

### Requirement: Uninterrupted build path for readers

The system SHALL publish a completed candidate by atomically replacing the
build path, so a concurrent reader never observes it missing and never
observes a mixture of the previous and the newly published artifact sets.
Publication SHALL use only operations that are atomic on POSIX platforms, so
the same behavior holds wherever the framework runs.

#### Scenario: Reader polls across a publication

- **WHEN** a consumer repeatedly reads the published viewer snapshot while a
  build is published
- **THEN** every read returns either the previous complete snapshot or the
  new complete snapshot, and never a missing build path

#### Scenario: Project built before this layout existed

- **WHEN** a project whose build path is still a plain directory is published
  for the first time under this layout
- **THEN** the build path is migrated to the published layout and later
  publications are atomic

### Requirement: Overlapping publications do not fail a correct build

The system SHALL tolerate a second publisher racing the same build path: a
publication SHALL either install its own complete artifact set or leave the
other publisher's complete artifact set in place. A publication that loses
such a race SHALL be reported through the ordinary build error channel and
SHALL NOT raise an unhandled exception out of the builder process. Removing a
superseded artifact set SHALL NOT remove an artifact set published by another
publisher.

#### Scenario: Verification build overlaps a watch loop

- **WHEN** a one-shot build publishes at the same moment as a development
  watch loop publishes the same project
- **THEN** the build path afterwards resolves to one publisher's complete
  artifact set, with no mixture of the two

#### Scenario: A publication loses the race

- **WHEN** a publication cannot install its candidate because another
  publisher already replaced the build path
- **THEN** the outcome is a reported build failure rather than a traceback
  escaping the builder process

### Requirement: Build artifacts stay out of version control

The system SHALL keep published build artifacts untracked by Git without
requiring the user to act. A scaffolded project SHALL ignore the build path
and its versioned directories. For a project whose ignore rules do not
already cover them, the system SHALL record the exclusion in the repository's
local exclude file rather than in a tracked ignore file, and SHALL do nothing
when it cannot.

#### Scenario: Scaffolded project

- **WHEN** a user creates a project with `solid new` and builds it
- **THEN** neither the build path nor its versioned directories appear as
  untracked files

#### Scenario: Existing project whose ignore rules predate this layout

- **WHEN** a project whose tracked ignore file does not cover the versioned
  directories is built
- **THEN** the exclusion is recorded locally, no tracked file is modified,
  and the working tree does not become dirty

#### Scenario: Ignore rules already cover the artifacts

- **WHEN** the project's tracked ignore file already covers the build path
  and its versioned directories
- **THEN** no local exclusion is recorded

