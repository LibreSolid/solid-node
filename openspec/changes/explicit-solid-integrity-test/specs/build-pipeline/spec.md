## ADDED Requirements

### Requirement: Publication runs no project geometry assertion

The build and publication pipeline SHALL NOT count connected components, read
an STL to evaluate a geometric contract, or invoke
`assertNoDisconnectedSolids`. A disconnected solid SHALL NOT by itself be a
build or publication failure.

The pipeline remains responsible for build mechanics and model validity —
render failures, missing artifacts, and structurally invalid trees such as a
fusion containing an assembly. Those are properties of a well-formed model, not
geometric contracts a project selected, and they SHALL continue to fail the
build.

#### Scenario: A fragmented solid publishes

- **WHEN** a build completes rendering and a topmost rigid node's STL has more
  than one connected solid, with no other failure
- **THEN** the viewer snapshot is published normally and no connectivity error
  is written

#### Scenario: The already-current path checks nothing either

- **WHEN** a builder finds the artifact set already current for a tree
  containing a fragmented solid
- **THEN** it publishes on its ordinary terms and reports no connectivity
  failure

#### Scenario: A declared test does not change build behavior

- **WHEN** a project declares a test method calling
  `assertNoDisconnectedSolids`
- **THEN** `solid build`, `solid develop` and `solid snapshot` neither discover
  nor execute it

## MODIFIED Requirements

### Requirement: Concurrent render locking

The system SHALL guard STL generation with a `.stl.lock` file containing the
rendering process PID, and SHALL treat a lock as stale when that PID is no
longer alive (`os.kill(pid, 0)` fails). A locked node skips generation.

Because the published manifest references every rigid node's STL by path, a
build that finishes with any rigid artifact still absent SHALL be reported as
an incomplete render rather than publishing, so a node whose lock another
builder holds makes the supervisor retry instead of advertising a file that is
not there. This requirement rests on manifest integrity alone and does not
depend on any geometric check.

#### Scenario: A locked node leaves the build incomplete

- **WHEN** a builder finishes triggering renders but a rigid node's STL is
  still absent because another process holds its lock
- **THEN** the build reports an incomplete render and nothing is published

#### Scenario: Stale lock

- **WHEN** a lock file references a dead PID
- **THEN** the node is not considered locked and rendering proceeds

## REMOVED Requirements

### Requirement: Every topmost rigid node is one connected body

**Reason**: The contract was sound but its lifecycle was not. Verification ran
inside `Builder`, which `solid test` never constructs, so a geometric contract
executed on `solid build`, `solid develop` and `solid snapshot` and never once
under the command whose purpose is running tests. Its failures were build
crashes rather than named, counted tests, were invisible in project source, and
were unreachable by `--failfast` and the animation-instant decorators.

**Migration**: Declare the contract as an ordinary test calling
`assertNoDisconnectedSolids(self.node)`; see the `test-framework` capability.
Newly scaffolded projects receive that declaration as source. A project that
declares nothing can publish a fragmented solid — the accepted consequence of
making the contract explicit.
