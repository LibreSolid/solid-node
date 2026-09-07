## ADDED Requirements

### Requirement: Source metadata is shared only within a verified snapshot

The system SHALL allow overlapping node source closures to read a request-local census of contributor metadata. Each census SHALL resolve and stat a distinct source path at most once, while producing exactly the path identity, `mtime_ns`, source fingerprint, node-scoped digest inputs, and currency decisions that uncached reads of the same filesystem state produce.

A census SHALL be immutable after observation and SHALL be discarded when a fresh boundary check finds any contributor changed, missing, replaced, or newly selected. It SHALL NOT survive into another builder process or source generation. Module-package resolution SHALL retain the late-import behavior of this capability: a project module imported after the existing index or census was formed SHALL be incorporated rather than answered from stale absence.

#### Scenario: Overlapping closures share filesystem observations

- **WHEN** many nodes in one stable generation track overlapping sets of project files
- **THEN** one census observes each distinct path once and every node receives the same source closure, timestamp, fingerprint, digest input, and currency result it would receive without the census

#### Scenario: A later boundary observes edits afresh

- **WHEN** a contributor changes after one census was collected
- **THEN** the next source-generation boundary detects the change from a fresh observation and no cached census reports the old metadata current

#### Scenario: A late import extends the snapshot

- **WHEN** project assembly imports a module after initial source lookup
- **THEN** the source resolver incorporates that module and the sealed generation includes its file, exactly as a fresh scan would
