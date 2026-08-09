## ADDED Requirements

### Requirement: A declared body count is verified before publication

Before publishing, a builder SHALL walk the loaded node tree and hold every
node that declares a `bodies` count to it. Verification SHALL happen on every
path that publishes, including the one that finds the artifact set already
current, so a model that arrives in pieces cannot reach the maker by that
route either. A violation SHALL prevent publication and SHALL be reported
through the same error channel as any other build failure, leaving the
previously published artifacts in place. Nodes that declare no count SHALL be
skipped without their meshes being read, so the check costs nothing until a
project asks for it.

#### Scenario: A fragmented model is not published

- **WHEN** a build completes rendering and a node's built mesh has a different
  number of connected solids than the node declares
- **THEN** no viewer snapshot is published and the failure is reported through
  `errors.json`

#### Scenario: The already-current path is checked too

- **WHEN** a builder finds the published artifact set already current for a
  node that violates its declared body count
- **THEN** it republishes nothing and reports the failure

#### Scenario: A project that declares nothing pays nothing

- **WHEN** a build runs on a tree in which no node declares a body count
- **THEN** no mesh is read for this check and publication proceeds as usual
