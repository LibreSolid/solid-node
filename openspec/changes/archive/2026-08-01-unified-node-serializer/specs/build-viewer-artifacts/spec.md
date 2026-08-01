## MODIFIED Requirements

### Requirement: Complete builds publish a viewer snapshot

The builder SHALL publish the versioned viewer snapshot named `viewer.json` in
the normal build directory only after the current project model has assembled
and every required STL artifact is current. The document SHALL declare
`format: "solid-node-export"`, `version: 1`, an `animation` object with numeric
`fps` and `frames`, and a `root` with the same observable schema and child-name
behavior as export `manifest.json`. The root SHALL include node identity, type,
colour, `mtime`, serialized operations, child relationships, and
build-root-relative rigid-model paths. The shared format SHALL identify this
versioned tree-document schema without implying portability. The snapshot
and all referenced model files SHALL become visible together through the
normal atomic build publication. The build publication SHALL remain
non-portable: it SHALL NOT create an export-style `models/` directory or copy
models into one. Changes to the shared tree shape or operation serialization
are breaking and MUST bump `version` and update every producer and consumer of
the shared schema together.

#### Scenario: A complete model is built once

- **WHEN** `solid build <project>` completes successfully
- **THEN** its `_build` directory contains `viewer.json` with the shared format
  and node fields, and each rigid model path resolves relative to that same
  published build directory

#### Scenario: A completed animated model is published

- **WHEN** `solid build <project>` completes a model with a `$t` operation
- **THEN** its `viewer.json` contains numeric `animation.fps` and
  `animation.frames` values alongside the root tree

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
