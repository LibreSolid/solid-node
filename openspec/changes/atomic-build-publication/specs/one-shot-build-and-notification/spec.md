## MODIFIED Requirements

### Requirement: One-shot conventional node build

The system SHALL provide `solid build <path>`, using the same node-path
resolution and ordinary build pipeline as `solid develop <path>`. It SHALL
produce the complete current model in the normal project build directory and
exit 0 without starting a watcher or viewer. Its exit status SHALL reflect
whether the model built, not whether it won a publication race with another
publisher of the same project.

#### Scenario: Build a package node

- **WHEN** a user runs `solid build root` from a project whose `root/`
  directory contains `__init__.py`
- **THEN** the command resolves `root/__init__.py`, completes the ordinary
  model build in the project's normal build directory, and exits 0

#### Scenario: Build publishes beside a running watch loop

- **WHEN** a user runs `solid build root` while `solid develop root` is
  watching the same project
- **THEN** the command does not fail with a publication error for a model
  that built correctly
