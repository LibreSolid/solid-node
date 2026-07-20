## ADDED Requirements

### Requirement: Complete builds publish a viewer snapshot
The builder SHALL publish a versioned viewer snapshot in the normal build directory only after the current project model has assembled and every required STL artifact is current. The snapshot SHALL contain the recursive viewer state for the root model: node identity, type, colour, serialized operations, child relationships, and build-root-relative rigid-model paths.

#### Scenario: A complete model is built once
- **WHEN** `solid build <project>` completes successfully
- **THEN** its `_build` directory contains a complete viewer snapshot whose rigid model paths resolve within that same published directory

### Requirement: The framework viewer can read a published snapshot
The framework SHALL provide its existing private viewer implementation a snapshot-backed mode that serves the same recursive node state and model files from a published build directory without importing the project model.

#### Scenario: A host serves a completed build
- **WHEN** a host constructs the private framework viewer from a completed build directory
- **THEN** the host can serve the root state and every referenced model without executing project Python

### Requirement: Failed later builds retain viewer state
A build failure after a successful publication SHALL leave the preceding viewer snapshot and all of its referenced model files available to snapshot consumers.

#### Scenario: A later project edit fails to build
- **WHEN** a later `solid develop` build fails after a completed publication
- **THEN** the callback is not emitted and the previous viewer snapshot remains readable from `_build`
