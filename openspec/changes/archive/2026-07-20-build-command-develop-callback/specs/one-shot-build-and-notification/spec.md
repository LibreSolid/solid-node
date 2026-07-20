## ADDED Requirements

### Requirement: One-shot conventional node build
The system SHALL provide `solid build <path>`, using the same node-path
resolution and ordinary build pipeline as `solid develop <path>`.  It SHALL
produce the complete current model in the normal project build directory and
exit 0 without starting a watcher or viewer.

#### Scenario: Build a package node
- **WHEN** a user runs `solid build root` from a project whose `root/`
  directory contains `__init__.py`
- **THEN** the command resolves `root/__init__.py`, completes the ordinary
  model build in the project's normal build directory, and exits 0

### Requirement: Missing model is a distinct build outcome
The system SHALL exit 66, documented as `MODEL_NOT_FOUND`, when `solid build`
cannot find the resolved model path.  It SHALL print a clear missing-model
diagnostic; other load, assemble, and render failures SHALL retain generic
non-zero failure behavior.

#### Scenario: Build a missing conventional model
- **WHEN** a user runs `solid build __init__.py` and that file does not exist
- **THEN** the command exits 66 and reports that the model does not exist

### Requirement: Successful artifacts are published as a complete model
The system SHALL expose a build to external consumers as successful only after
the complete model artifacts have been published in the normal project build
directory.  If a later build fails, it SHALL retain the last complete
successful artifact state and SHALL NOT publish a partial replacement.

#### Scenario: Later build fails
- **WHEN** a project has a complete successful build and a later build fails
- **THEN** its normal build directory continues to contain the prior complete
  successful model artifacts

### Requirement: Development build-ready callback
The system SHALL accept `solid develop <path> --callback URL` in normal web
mode.  It SHALL issue an empty HTTP POST to the supplied URL after the
initial successful complete build and after every later successful complete
rebuild.  Each callback SHALL occur only after the corresponding artifacts
are published in the normal project build directory.

#### Scenario: Initial development build becomes ready
- **WHEN** a user starts `solid develop root --callback URL` and its initial
  build completes successfully
- **THEN** the system POSTs the supplied URL with no request body after the
  complete artifacts are published

#### Scenario: Edited model rebuilds successfully
- **WHEN** a watched source edit leads to a successful complete rebuild under
  `solid develop root --callback URL`
- **THEN** the system POSTs the supplied URL after publishing the rebuilt
  artifacts

### Requirement: Callback delivery is best effort
The system SHALL use a bounded short timeout for callback delivery.  A
transport failure or non-success response SHALL be logged, SHALL NOT be
retried, and SHALL NOT stop the development watch loop.  A failed build SHALL
NOT invoke the callback.

#### Scenario: Callback listener is unavailable
- **WHEN** a successful development build cannot deliver its callback
- **THEN** the system logs the delivery failure and continues watching the
  project

#### Scenario: Rebuild fails
- **WHEN** a watched source edit causes a build failure
- **THEN** the system sends no callback and continues its existing reload
  recovery behavior
