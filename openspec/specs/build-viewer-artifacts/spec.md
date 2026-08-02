# Build Viewer Artifacts Specification

## Purpose

Complete normal-build viewer state for private local framework consumers.

## Requirements

### Requirement: Complete builds publish a viewer snapshot
The builder SHALL publish the versioned viewer snapshot named `viewer.json` in
the normal build directory only after the current project model has assembled
and every required STL artifact is current. The document SHALL declare
`format: "solid-node-export"`, `version: 1`, an `animation` object with numeric
`fps` and `frames`, and a `root` with the same observable schema and child-name
behavior as export `manifest.json`. The root SHALL include node identity, type,
colour, `mtime`, serialized operations, child relationships, and
build-root-relative rigid-model paths. The shared format SHALL identify this
versioned tree-document schema without implying portability. The snapshot SHALL
be written after the model files it references, atomically, so that every path
it names is readable the moment the snapshot itself is. The build publication
SHALL remain non-portable: it SHALL NOT create an export-style `models/`
directory or copy models into one. Changes to the shared tree shape or operation
serialization are breaking and MUST bump `version` and update every producer and
consumer of the shared schema together.

#### Scenario: A complete model is built once
- **WHEN** `solid build <project>` completes successfully
- **THEN** its `_build` directory contains `viewer.json` with the shared format
  and node fields, and each rigid model path resolves relative to that same
  published build directory

#### Scenario: A completed animated model is published
- **WHEN** `solid build <project>` completes a model with a `$t` operation
- **THEN** its `viewer.json` contains numeric `animation.fps` and `animation.frames` values alongside the root tree

#### Scenario: Linked names match the portable export

- **WHEN** the same attribute-linked assembly is published as a normal build
  and as a static export
- **THEN** `viewer.json` and `manifest.json` contain the same linked node names,
  operations, colour, `mtime`, and rigid/non-rigid tree structure while
  retaining their distinct model path roots

#### Scenario: Build publication is not converted into an export

- **WHEN** a complete build is published
- **THEN** its document remains named `viewer.json`, references ordinary
  build-root-relative model files, creates no export-style `models/` tree, and
  copies no mesh

#### Scenario: Every path a new snapshot names is readable

- **WHEN** a consumer reads a newly published `viewer.json`
- **THEN** every model file it names is already present and complete

### Requirement: Failed later builds retain viewer state
A build failure after a successful publication SHALL leave a readable viewer
snapshot naming readable model files, and SHALL report the failure through
`errors.json`. The snapshot and models MAY reflect a partially updated model
rather than the preceding complete one.

#### Scenario: A later project edit fails to build
- **WHEN** a later `solid develop` build fails after a completed publication
- **THEN** the callback is not emitted, `errors.json` reports the failure, and
  the snapshot readable from `_build` still names model files that are present
  and complete

