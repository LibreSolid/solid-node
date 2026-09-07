## MODIFIED Requirements

### Requirement: Development build-ready callback

The system SHALL issue an empty HTTP POST to the supplied callback URL after
each complete successful development build that changes externally visible
publication state, after artifacts are published in the normal build directory.
Removing a prior build error SHALL count as a publication-state change even
when the viewer document is byte-identical. A repeated successful build that
changes neither the document nor failure state SHALL remain a no-op and SHALL
NOT issue the callback. This SHALL hold whether the development session runs
the web viewer or suppresses it with `--no-web`.

#### Scenario: Build ready in a headless session

- **WHEN** a development session started with `--no-web --callback URL`
  completes a successful build and publishes the normal build directory
- **THEN** an empty POST is issued to that URL

#### Scenario: Recovery clears only the failure record

- **WHEN** a complete successful development build removes a prior error but
  its viewer document bytes already match the published document
- **THEN** an empty POST is issued after the error is removed

#### Scenario: Successful build changes no publication state

- **WHEN** a repeated successful development build changes neither the viewer
  document nor a prior failure record
- **THEN** no callback is issued
