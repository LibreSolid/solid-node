# One-shot build and notification Specification

## Purpose

One-shot conventional node builds and build-ready notifications for local
artifact consumers.
## Requirements
### Requirement: One-shot conventional node build

The system SHALL provide `solid build <path>`, using the same node-path
resolution and ordinary build pipeline as `solid develop <path>`. It SHALL
produce the complete current model in the normal project build directory and
exit 0 without starting a watcher or viewer.

#### Scenario: Build a package node

- **WHEN** a user runs `solid build root` from a project whose `root/`
  directory contains `__init__.py`
- **THEN** the command resolves `root/__init__.py`, completes the ordinary
  model build in the project's normal build directory, and exits 0

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

