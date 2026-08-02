## ADDED Requirements

### Requirement: Artifacts become reachable through the manifest

The system SHALL treat the viewer snapshot as the only thing that makes an
artifact reachable, and SHALL order a publication accordingly: every artifact a
build produces SHALL be in place before the snapshot naming it is written, and
an artifact the new snapshot no longer names SHALL be removed only after that
snapshot is in place.

#### Scenario: A new part appears

- **WHEN** a build adds a node and publishes
- **THEN** the node's artifact is readable before the snapshot naming it
  becomes visible

#### Scenario: A part is removed

- **WHEN** a build removes a node and publishes
- **THEN** the snapshot without that node becomes visible before its artifact
  is removed

### Requirement: A successful build sweeps unreferenced artifacts

After a successful publication the system SHALL remove files in the build
directory that the current viewer snapshot does not reference, other than the
snapshot, the error file, `.scad` inputs, live render lock files, and
temporaries belonging to a build in progress. The sweep SHALL be confined to
the build directory.

#### Scenario: A renamed node leaves nothing behind

- **WHEN** a node is renamed and the project is rebuilt successfully
- **THEN** the artifact under the old name is gone from the build directory and
  the artifact under the new name is present and referenced

#### Scenario: A failed build sweeps nothing

- **WHEN** a build fails
- **THEN** no artifact is removed from the build directory

### Requirement: Error file lifecycle

The system SHALL write `errors.json` atomically, SHALL remove it after a
successful publication, and SHALL NOT remove it as a side effect of any other
operation. A consumer SHALL never observe a newly published model together with
the error file from the build that preceded it.

#### Scenario: A build succeeds after a failure

- **WHEN** a build succeeds after a previous build wrote `errors.json`
- **THEN** the new artifacts and snapshot are published and `errors.json` is
  gone

#### Scenario: A build fails after a success

- **WHEN** a build fails
- **THEN** `errors.json` describes that failure and no partially written error
  file is ever readable

## MODIFIED Requirements

### Requirement: Build artifact layout

The system SHALL write build artifacts under `$SOLID_BUILD_DIR` (default
`_build`), mirroring the source file's directory, with basename
`<script-name>-<uniq_id>`. Artifacts per node: `.scad` (base geometry,
no transforms), `.stl` (rendered), and `.stl.lock` during rendering.
World-space spatial math does not use on-disk artifacts — the `mesh`
property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). The build path SHALL be an ordinary directory that every
builder writes into directly; the system SHALL NOT publish through a symlink, a
versioned sibling directory, or a private candidate copy. A build path left as
a symlink by an earlier layout SHALL be converted to an ordinary directory
holding the artifacts it referenced.

#### Scenario: Custom build dir

- **WHEN** `SOLID_BUILD_DIR` is set in the environment
- **THEN** all artifacts, and `errors.json`, are written under that
  directory instead of `_build`

#### Scenario: Consumer reads through the build path

- **WHEN** a consumer opens the published viewer snapshot at the build path
- **THEN** it reads the snapshot without resolving a symlink or naming any
  other directory

#### Scenario: Project published under the previous layout

- **WHEN** a project whose build path is a symlink to a versioned directory is
  built
- **THEN** the build path becomes an ordinary directory holding those
  artifacts, and the versioned siblings are removed

### Requirement: Uninterrupted build path for readers

The system SHALL publish each artifact by writing a temporary file in the
artifact's own directory and atomically replacing the target, so a reader
observes an artifact either complete or absent, never partially written, and a
reader that has already opened an artifact SHALL be able to read it to
completion after it is replaced. Publication SHALL use only operations that are
atomic on POSIX platforms, so the same behavior holds wherever the framework
runs. The system SHALL NOT guarantee that concurrently readable artifacts come
from a single build.

#### Scenario: Reader polls across a publication

- **WHEN** a consumer repeatedly reads a model artifact while a build
  republishes it
- **THEN** every read returns a complete artifact — the previous one or the new
  one — and never a partial file or a missing path

#### Scenario: A reader holds an artifact being replaced

- **WHEN** an artifact is replaced while a consumer is reading it
- **THEN** the consumer reads the bytes it opened to completion

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

Currency SHALL be judged where a consumer reads artifacts — the build directory
itself, which is now the only place a builder writes. This decision SHALL be
derived from source and artifact mtimes; the system SHALL NOT record build
state, generation counters, or source identity inside published artifacts for
this purpose.

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

#### Scenario: A watching builder finds nothing to do

- **WHEN** a builder that watches for source changes acquires the lock and the
  published set is already current
- **THEN** it publishes nothing and keeps watching, and the development loop
  does not respawn it

#### Scenario: An ordinary change still builds

- **WHEN** a builder acquires the lock, its sources are the newest on disk, and
  the published set is not current for them
- **THEN** it renders and publishes exactly as it does without contention

### Requirement: Build artifacts stay out of version control

The system SHALL keep published build artifacts untracked by Git without
requiring the user to act. A scaffolded project SHALL ignore the build path and
the files the framework keeps beside it. For a project whose ignore rules do not
already cover them, the system SHALL record the exclusion in the repository's
local exclude file rather than in a tracked ignore file, and SHALL do nothing
when it cannot.

#### Scenario: Scaffolded project

- **WHEN** a user creates a project with `solid new` and builds it
- **THEN** neither the build path nor the project build lock appears as an
  untracked file

#### Scenario: Existing project whose ignore rules predate this layout

- **WHEN** a project whose tracked ignore file does not cover the build path is
  built
- **THEN** the exclusion is recorded locally, no tracked file is modified,
  and the working tree does not become dirty

#### Scenario: Ignore rules already cover the artifacts

- **WHEN** the project's tracked ignore file already covers the build path
- **THEN** no local exclusion is recorded

## REMOVED Requirements

### Requirement: Overlapping publications do not fail a correct build

**Reason**: The race it tolerated cannot occur. Every framework producer holds
the project build lock while it renders and publishes, so two publishers no
longer contend for the same build path, and there is no publication a builder
can lose.

**Migration**: None for users. A build that would previously have reported a
lost race now waits for the lock and publishes normally.

### Requirement: Last successful artifacts survive a failed later build

**Reason**: The guarantee depended on set-atomic publication through a private
candidate directory, which is what this change removes so that parts can appear
as they finish. A failed build now leaves a partially updated model.

**Migration**: Consumers detect failure through `errors.json`, which continues
to report it, rather than by assuming the artifacts they can read come from one
successful build.
