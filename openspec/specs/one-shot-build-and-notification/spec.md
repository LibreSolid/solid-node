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

### Requirement: Development build-ready callback

The system SHALL issue an empty HTTP POST to the supplied callback URL after
each complete successful normal-web development build, after artifacts are
published in the normal build directory.

### Requirement: Callback delivery is best effort

The system SHALL use a bounded timeout, log transport or non-success failures,
avoid retrying, and continue the development watch loop. Failed builds SHALL
not invoke the callback.
