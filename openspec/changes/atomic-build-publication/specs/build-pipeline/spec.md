## MODIFIED Requirements

### Requirement: Build artifact layout

The system SHALL write build artifacts under `$SOLID_BUILD_DIR` (default
`_build`), mirroring the source file's directory, with basename
`<script-name>-<uniq_id>`. Artifacts per node: `.scad` (base geometry,
no transforms), `.stl` (rendered), and `.stl.lock` during rendering.
World-space spatial math does not use on-disk artifacts — the `mesh`
property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). The build path itself SHALL be a symlink to a
versioned sibling directory holding the published artifact set; it SHALL
behave as a directory for ordinary reads, and consumers SHALL reach artifacts
through it without knowing the versioned name.

#### Scenario: Custom build dir

- **WHEN** `SOLID_BUILD_DIR` is set in the environment
- **THEN** all artifacts, and `errors.json`, are written under that
  directory instead of `_build`

#### Scenario: Consumer reads through the build path

- **WHEN** a consumer opens the published viewer snapshot at the build path
- **THEN** it reads the artifact set currently published there without
  resolving or naming the versioned directory

## ADDED Requirements

### Requirement: Uninterrupted build path for readers

The system SHALL publish a completed candidate by atomically replacing the
build path, so a concurrent reader never observes it missing and never
observes a mixture of the previous and the newly published artifact sets.
Publication SHALL use only operations that are atomic on POSIX platforms, so
the same behavior holds wherever the framework runs.

#### Scenario: Reader polls across a publication

- **WHEN** a consumer repeatedly reads the published viewer snapshot while a
  build is published
- **THEN** every read returns either the previous complete snapshot or the
  new complete snapshot, and never a missing build path

#### Scenario: Project built before this layout existed

- **WHEN** a project whose build path is still a plain directory is published
  for the first time under this layout
- **THEN** the build path is migrated to the published layout and later
  publications are atomic

### Requirement: Overlapping publications do not fail a correct build

The system SHALL tolerate a second publisher racing the same build path: a
publication SHALL either install its own complete artifact set or leave the
other publisher's complete artifact set in place. A publication that loses
such a race SHALL be reported through the ordinary build error channel and
SHALL NOT raise an unhandled exception out of the builder process. Removing a
superseded artifact set SHALL NOT remove an artifact set published by another
publisher.

#### Scenario: Verification build overlaps a watch loop

- **WHEN** a one-shot build publishes at the same moment as a development
  watch loop publishes the same project
- **THEN** the build path afterwards resolves to one publisher's complete
  artifact set, with no mixture of the two

#### Scenario: A publication loses the race

- **WHEN** a publication cannot install its candidate because another
  publisher already replaced the build path
- **THEN** the outcome is a reported build failure rather than a traceback
  escaping the builder process

### Requirement: Build artifacts stay out of version control

The system SHALL keep published build artifacts untracked by Git without
requiring the user to act. A scaffolded project SHALL ignore the build path
and its versioned directories. For a project whose ignore rules do not
already cover them, the system SHALL record the exclusion in the repository's
local exclude file rather than in a tracked ignore file, and SHALL do nothing
when it cannot.

#### Scenario: Scaffolded project

- **WHEN** a user creates a project with `solid new` and builds it
- **THEN** neither the build path nor its versioned directories appear as
  untracked files

#### Scenario: Existing project whose ignore rules predate this layout

- **WHEN** a project whose tracked ignore file does not cover the versioned
  directories is built
- **THEN** the exclusion is recorded locally, no tracked file is modified,
  and the working tree does not become dirty

#### Scenario: Ignore rules already cover the artifacts

- **WHEN** the project's tracked ignore file already covers the build path
  and its versioned directories
- **THEN** no local exclusion is recorded
