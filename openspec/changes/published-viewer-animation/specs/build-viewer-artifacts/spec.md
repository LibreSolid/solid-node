## MODIFIED Requirements

### Requirement: Completed builds publish a viewer snapshot
The builder SHALL publish a versioned viewer snapshot in the normal build
directory only after the current project model has assembled and every required
STL artifact is current. The snapshot SHALL contain the recursive viewer state
for the root model: node identity, type, colour, serialized operations, child
relationships, and build-root-relative rigid-model paths. It SHALL also contain
an `animation` object with numeric `fps` and `frames` values representing the
animation cadence used to evaluate raw `$t` operations. The snapshot and all
referenced model files SHALL become visible together through the normal atomic
build publication.

#### Scenario: A completed build publishes an animated viewer contract
- **WHEN** `solid build` completes a model that contains a `$t` operation
- **THEN** the published `viewer.json` includes its root tree and numeric
  `animation.fps` and `animation.frames` values without requiring a host to
  load project source

#### Scenario: A later build fails
- **WHEN** a later build fails after a complete viewer snapshot was published
- **THEN** the normal build directory retains the preceding snapshot, its
  animation cadence, and its referenced model files
