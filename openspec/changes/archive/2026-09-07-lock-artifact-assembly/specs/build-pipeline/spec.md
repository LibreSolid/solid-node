## MODIFIED Requirements

### Requirement: Project build mutual exclusion

The system SHALL serialise builds of the same project across processes with an
advisory exclusive lock (`fcntl.flock`) on a lock file held beside the project's
published build directory. Every framework entry point that renders artifacts
for a project — the development watch loop, the one-shot build, the test
runner's build phase, and export — SHALL acquire that lock before any lifecycle
phase that can materialize SCAD, BREP, STL, or published documents, including
assembly, and SHALL release it as soon as that work is finished. Acquisition
SHALL block until the lock is available rather than fail or skip, and a wait
that does not resolve immediately SHALL be logged. The lock SHALL NOT be held
while a builder waits for a source change, invokes a completion callback, or
runs project test cases, and the lock file SHALL be excluded from version
control by the same rule that excludes published artifacts.

A holder that dies SHALL release the lock without any recovery step, because
the kernel releases it when the holding process ends.

#### Scenario: A second builder waits for the first

- **WHEN** a build is rendering a project and another process starts a build of
  the same project
- **THEN** the second process does not render or publish until the first has
  finished, and both report their own build outcome

#### Scenario: An assembly-time producer waits

- **WHEN** a cold exact or imported-file node starts through a framework entry
  point while another process holds its project build lock
- **THEN** no SCAD, BREP, or STL artifact is materialized until the lock is
  released, after which the entry point completes normally

#### Scenario: Test setup is locked and test execution is not

- **WHEN** the test runner builds a node and then executes its project test
  cases
- **THEN** keyframing, preliminary render, assembly, and STL generation occur
  while the project lock is held, and test-case execution begins after release

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
