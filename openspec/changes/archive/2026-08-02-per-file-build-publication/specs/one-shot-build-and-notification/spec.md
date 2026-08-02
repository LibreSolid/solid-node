## MODIFIED Requirements

### Requirement: One-shot conventional node build

The system SHALL provide `solid build <path>`, using the same node-path
resolution and ordinary build pipeline as `solid develop <path>`. It SHALL
produce the complete current model in the normal project build directory and
exit 0 without starting a watcher or viewer. Its exit status SHALL reflect
whether the model built. When its builder stands down because the source moved
while it waited for the project build lock, the command SHALL build again from
the source on disk rather than exiting, so what it publishes is the current
model.

#### Scenario: Build a package node

- **WHEN** a user runs `solid build root` from a project whose `root/`
  directory contains `__init__.py`
- **THEN** the command resolves `root/__init__.py`, completes the ordinary
  model build in the project's normal build directory, and exits 0

#### Scenario: Build publishes beside a running watch loop

- **WHEN** a user runs `solid build root` while `solid develop root` is
  watching the same project
- **THEN** the two builds serialise on the project build lock and the command
  exits 0 for a model that built correctly

#### Scenario: The source moves while the build waits

- **WHEN** the project source is edited while `solid build` is waiting for the
  project build lock
- **THEN** the command rebuilds from the edited source and exits 0 with the
  current model published
