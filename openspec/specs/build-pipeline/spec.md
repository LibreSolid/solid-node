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
`NODE = <Class>` marker naming the intended class; otherwise the loader raises
`AmbiguousNodeError`. An explicit marker MAY name a node class imported from
another project-local module, but MUST reject a non-node value or a class
defined outside the active project. Implicit discovery without a marker SHALL
consider only classes defined in the loaded file. The loaded entry-point file
and the selected class's project-local implementation/import closure SHALL all
contribute to the node's tracked source set. Companion tests are discovered as
`test_<file>.py` for module nodes and `test.py` for package nodes.

#### Scenario: Ambiguous module

- **WHEN** a file defines two node classes and no `NODE` marker
- **THEN** loading raises `AmbiguousNodeError`

#### Scenario: Imported classes are ignored implicitly

- **WHEN** a file imports node classes, defines exactly one of its own, and has
  no `NODE` marker
- **THEN** the loader picks the locally defined class

#### Scenario: Project package re-exports its node

- **WHEN** a project entry-point file sets `NODE` to an
  `AbstractBaseNode` subclass imported from another module in the same project
- **THEN** the loader instantiates the imported class
- **AND** the entry-point file and implementation source are both tracked

#### Scenario: Imported marker target is outside the project

- **WHEN** a project entry-point file sets `NODE` to a class defined outside
  the active project
- **THEN** loading raises an actionable `AmbiguousNodeError`

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

### Requirement: Project build mutual exclusion

The system SHALL serialise builds of the same project across processes with an
advisory exclusive lock (`fcntl.flock`) on a lock file held beside the project's
published build directory. Every framework entry point that renders artifacts
for a project — the development watch loop, the one-shot build, the test
runner's build phase, and export — SHALL acquire that lock before rendering or
publishing and SHALL release it as soon as that work is finished. Acquisition
SHALL block until the lock is available rather than fail or skip, and a wait
that does not resolve immediately SHALL be logged. The lock SHALL NOT be held
while a builder waits for a source change, and the lock file SHALL be excluded
from version control by the same rule that excludes published artifacts.

A holder that dies SHALL release the lock without any recovery step, because
the kernel releases it when the holding process ends.

#### Scenario: A second builder waits for the first

- **WHEN** a build is rendering a project and another process starts a build of
  the same project
- **THEN** the second process does not render or publish until the first has
  finished, and both report their own build outcome

#### Scenario: Watching does not hold the lock

- **WHEN** a development watch loop has published a build and is waiting for the
  next source change
- **THEN** another process can acquire the project build lock immediately

#### Scenario: A killed builder leaves nothing to reap

- **WHEN** a process holding the build lock is killed
- **THEN** the next builder acquires the lock with no stale-lock detection and
  no manual cleanup

#### Scenario: Independent projects do not serialise

- **WHEN** two projects with different build directories are built at the same
  time
- **THEN** neither build waits for the other

### Requirement: Superseded and redundant builds do not publish

Having acquired the build lock, a builder SHALL re-evaluate whether its work is
still needed before rendering or publishing, using the mtime-equality rule
already governing artifact currency.

- When the node's tracked source files on disk are newer than the source state
  the builder loaded, the builder SHALL publish nothing and SHALL report the
  same source-changed outcome an ordinary edit produces, so its lifecycle loop
  rebuilds from current source.
- When the published artifact set is already current for the loaded node, the
  builder SHALL publish nothing. A one-shot build SHALL report the model
  current; a watching builder SHALL go on waiting for the next source change
  rather than ending.

Currency SHALL be judged where a consumer reads artifacts — the published build
directory — and never from a builder's private candidate directory, whose
contents no consumer can reach. This decision SHALL be derived from source and
artifact mtimes; the system SHALL NOT record build state, generation counters,
or source identity inside published artifacts for this purpose.

#### Scenario: The newest source wins

- **WHEN** a build against older source finishes after a build against newer
  source has published the same project
- **THEN** the older build publishes nothing and the published model matches the
  newer source

#### Scenario: A redundant build publishes nothing

- **WHEN** a builder acquires the lock and the published artifact set is already
  current for its sources
- **THEN** no artifact is rendered, no publication occurs, and the outcome
  reports the model current

#### Scenario: Rendered but unpublished artifacts are not a publication

- **WHEN** a build needing several render passes has rendered artifacts into
  its candidate directory and the next pass acquires the lock
- **THEN** the artifacts are published, because no consumer can read a
  candidate directory

#### Scenario: A watching builder finds nothing to do

- **WHEN** a builder that watches for source changes acquires the lock and the
  published set is already current
- **THEN** it publishes nothing and keeps watching, and the development loop
  does not respawn it

#### Scenario: An ordinary change still builds

- **WHEN** a builder acquires the lock, its sources are the newest on disk, and
  the published set is not current for them
- **THEN** it renders and publishes exactly as it does without contention

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
