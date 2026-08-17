# One-shot build and notification Specification

## Purpose

One-shot conventional node builds and build-ready notifications for local
artifact consumers.
## Requirements
### Requirement: One-shot conventional node build

The system SHALL provide `solid build [reference]`, using the same node
reference resolution and ordinary build pipeline as `solid develop
[reference]`. It SHALL
produce the complete current model in the normal project build directory and
exit 0 without starting a watcher or viewer. Its exit status SHALL reflect
whether the model built. When its builder stands down because the source moved
while it waited for the project build lock, the command SHALL build again from
the source on disk rather than exiting, so what it publishes is the current
model.

#### Scenario: Build the project model

- **WHEN** a user runs `solid build` from a project whose manifest declares
  `[tool.solid-node] model`
- **THEN** the command resolves that model, completes the ordinary model build
  in the project's normal build directory, and exits 0

#### Scenario: Build publishes beside a running watch loop

- **WHEN** a user runs `solid build` while `solid develop` is
  watching the same project
- **THEN** the two builds serialise on the project build lock and the command
  exits 0 for a model that built correctly

#### Scenario: The source moves while the build waits

- **WHEN** the project source is edited while `solid build` is waiting for the
  project build lock
- **THEN** the command rebuilds from the edited source and exits 0 with the
  current model published

### Requirement: Missing model is a distinct build outcome

The system SHALL exit 66, documented as `MODEL_NOT_FOUND`, when `solid build`
cannot find the resolved model path; other build failures remain generic
non-zero outcomes.

#### Scenario: Build target does not exist

- **WHEN** a user runs `solid build missing.py` and no such model path
  resolves
- **THEN** the command exits 66 and reports the unresolved model path

### Requirement: Development build-ready callback

The system SHALL issue an empty HTTP POST to the supplied callback URL after
each complete successful development build, after artifacts are published in
the normal build directory. This SHALL hold whether the development session
runs the web viewer or suppresses it with `--no-web`.

#### Scenario: Build ready in a headless session

- **WHEN** a development session started with `--no-web --callback URL`
  completes a successful build and publishes the normal build directory
- **THEN** an empty POST is issued to that URL

### Requirement: Callback delivery is best effort

The system SHALL use a bounded timeout, log transport or non-success failures,
avoid retrying, and continue the development watch loop. Failed builds SHALL
not invoke the callback.

#### Scenario: Callback endpoint is unreachable

- **WHEN** the callback POST fails or returns a non-success status
- **THEN** the failure is logged, is not retried, and the development watch
  loop continues

#### Scenario: A build fails

- **WHEN** a development build does not complete successfully
- **THEN** no callback is issued and the previously published build directory
  is left in place
