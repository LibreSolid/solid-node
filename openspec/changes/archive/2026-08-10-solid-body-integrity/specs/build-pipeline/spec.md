## ADDED Requirements

### Requirement: Every topmost rigid node is one connected body

Before publishing, a builder SHALL verify that each topmost rigid node in the
loaded tree is exactly one connected solid. The count SHALL be taken from that
node's own built STL with no operations applied, and components SHALL be
counted without filtering to watertight ones, so a fragment that is itself
closed still counts as a body.

The sweep SHALL stop at each topmost rigid node and SHALL NOT descend into its
rigid descendants: geometry below a topmost rigid node is already composed into
its STL, and a leaf or nested fusion is free to be several separated pieces so
long as the enclosing solid joins them. No world matrix SHALL be composed for
this check, so no operation value can require resolution and an animated
subtree is verified exactly as a static one is.

Verification SHALL happen on every path that publishes, including the one that
finds the artifact set already current, so a model that arrives in pieces
cannot reach the maker by that route either. A violation SHALL prevent
publication and SHALL be reported through the same error channel as any other
build failure, naming the node and the number of bodies found, and leaving the
previously published artifacts in place.

#### Scenario: A fragmented model is not published

- **WHEN** a build completes rendering and a topmost rigid node's STL has more
  than one connected solid
- **THEN** no viewer snapshot is published and the failure is reported through
  `errors.json`, naming that node and the count found

#### Scenario: The already-current path is checked too

- **WHEN** a builder finds the published artifact set already current for a
  tree containing a fragmented topmost rigid node
- **THEN** it republishes nothing and reports the failure

#### Scenario: An animated part is verified like any other

- **WHEN** a topmost rigid node's placement is driven by an enclosing assembly,
  so its operations hold unresolved animation expressions
- **THEN** verification reads its STL directly, resolves no operation value,
  and publication proceeds when the STL is one body

#### Scenario: Pieces inside a solid are permitted

- **WHEN** a `FusionNode` joins two leaves that are each several separated
  solids, and the fused result is one connected body
- **THEN** the fusion passes, and neither leaf is checked

## MODIFIED Requirements

### Requirement: Concurrent render locking

The system SHALL guard STL generation with a `.stl.lock` file containing the
rendering process PID, and SHALL treat a lock as stale when that PID is no
longer alive (`os.kill(pid, 0)` fails). A locked node skips generation.

Because publication reads each topmost rigid node's STL, a build that finishes
with any rigid artifact still absent SHALL be reported as an incomplete render
rather than proceeding to verification, so a node whose lock another builder
holds makes the supervisor retry instead of failing on a missing file.

#### Scenario: A locked node leaves the build incomplete

- **WHEN** a builder finishes triggering renders but a rigid node's STL is
  still absent because another process holds its lock
- **THEN** the build reports an incomplete render and nothing is verified or
  published

#### Scenario: Stale lock

- **WHEN** a lock file references a dead PID
- **THEN** the node is not considered locked and rendering proceeds

## REMOVED Requirements

### Requirement: A declared body count is verified before publication

**Reason**: Verification was gated on an opt-in `bodies` declaration, so the
default was no contract, and it counted components on each node's world mesh.
Composing that world matrix pulled in operations authored by enclosing
assemblies, which hold the animated `$t` expression, so the check raised a type
error rather than a verdict for every animated part. The transform could never
have changed a component count in the first place.

**Migration**: Replaced by "Every topmost rigid node is one connected body",
which is unconditional, needs no declaration, and reads the local STL. Projects
that declared `bodies` delete the declaration; see the `node-model` removal
note for parts that genuinely comprise several separated pieces.
