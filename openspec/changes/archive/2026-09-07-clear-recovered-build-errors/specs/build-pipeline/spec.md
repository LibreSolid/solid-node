## MODIFIED Requirements

### Requirement: File-based build error propagation

The system SHALL report build errors by writing `{"error": ..., "tstamp":
...}` to `errors.json` in the build dir (no broker or socket IPC — ADR-018).
A prior error SHALL remain visible until a complete successful build has loaded,
assembled, rendered or verified every artifact, and constructed its complete
viewer document. The successful build SHALL then clear the error even when the
constructed document is byte-identical to the published `viewer.json`. An
initial-launch failure SHALL exit non-zero (develop terminates); a failure
during reload SHALL NOT kill the loop — the builder falls back to watching the
project directory recursively, writes the traceback to `errors.json`, and exits
cleanly on the next save so development continues.

#### Scenario: Syntax error during development

- **WHEN** a reload hits a SyntaxError in the edited file
- **THEN** the traceback lands in `errors.json`, the web viewer can surface
  it, and fixing the file resumes building without restarting `solid develop`

#### Scenario: Broken project at launch

- **WHEN** the first build after `solid develop` fails to load the node
- **THEN** develop tears down its child processes and exits non-zero

#### Scenario: Byte-identical build recovers prior failure state

- **WHEN** a complete successful build constructs the same viewer document
  already on disk while its build directory contains a prior `errors.json`
- **THEN** the error file is removed without rewriting the byte-identical
  viewer document, and directory-derived model status is `published`

#### Scenario: Document construction still fails

- **WHEN** a build with a prior `errors.json` fails while constructing its
  viewer document
- **THEN** the prior error remains visible and the build does not report
  recovery
