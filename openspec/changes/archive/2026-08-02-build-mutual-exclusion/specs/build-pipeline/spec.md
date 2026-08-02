## ADDED Requirements

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
