## MODIFIED Requirements

### Requirement: Development build-ready callback

The system SHALL issue an empty HTTP POST to the supplied callback URL after
each complete successful development build, after artifacts are published in
the normal build directory. This SHALL hold whether the development session
runs the web viewer or suppresses it with `--no-web`.

#### Scenario: Build ready in a headless session

- **WHEN** a development session started with `--no-web --callback URL`
  completes a successful build and publishes the normal build directory
- **THEN** an empty POST is issued to that URL
