## ADDED Requirements

### Requirement: Artifact-derived piece facts are reused only for a verified artifact

The system MAY persist the artifact-derived full content digest, printable extents, volume, and watertightness in a private versioned fact record. It SHALL reuse those facts only when the artifact is current under its source-currency contract and its current real path, device, inode, byte size, integer-nanosecond mtime, and integer-nanosecond change time exactly match the artifact observation recorded when the facts were computed.

The record SHALL NOT supply tree-derived or document-derived values: display name, contributing sources, model references, count, hierarchy, placements, drivers, expressions, and document version SHALL be reconstructed from the current model on every publication. A missing, malformed, unknown-version, or mismatching record SHALL certify nothing. Recomputed facts SHALL come from the current artifact bytes rather than from a process-local mesh cached under a weaker identity. Hash and mesh facts SHALL derive from one coherent pinned artifact read whose open-file and path identities are validated before and after consumption. Any artifact bytes copied into an export or staging area SHALL come from the same pinned identity whose facts are published, whether or not the caller already holds the project build lock. A concurrent replacement SHALL yield one coherent old or new artifact/fact pair or force a retry, never a mixed pair. The fact record SHALL be published atomically only after successful complete computation and SHALL be swept with the artifact it describes.

The full SHA-256 SHALL distinguish inventory entries internally. The public piece id MAY remain its compatible truncated form, but two different full digests with the same public prefix SHALL be rejected with a deterministic collision error and SHALL NOT be merged.

#### Scenario: An unchanged artifact avoids mesh decoding

- **WHEN** a fresh builder publishes a current artifact whose complete observation matches a valid fact record
- **THEN** it reuses the artifact-derived digest, size, volume, and watertightness without decoding the mesh, while current tree metadata and placement are serialized normally

#### Scenario: A same-mtime replacement recomputes from current bytes

- **WHEN** an artifact is replaced in the same process by different same-size bytes and its mtime is restored
- **THEN** its filesystem identity or change time invalidates the fact record and any weaker process-local mesh entry, and recomputation returns facts and content identity for the replacement bytes

#### Scenario: A fresh process also rejects a replaced artifact

- **WHEN** a fresh process reads a fact record after the described artifact was replaced with a different artifact that preserved size and mtime
- **THEN** the observation mismatch forces current-byte recomputation rather than reusing the recorded facts

#### Scenario: Concurrent export replacement stays coherent

- **WHEN** an artifact path is atomically replaced while export derives or reuses facts and copies model bytes
- **THEN** the exported bytes and published digest/facts describe the same pinned artifact identity, or validation retries without publishing a mixed document

#### Scenario: New model metadata is never cached as an artifact fact

- **WHEN** source edits change a node's name, hierarchy, placement, or document metadata without changing its artifact bytes
- **THEN** publication reuses only the artifact-derived facts and emits the new model metadata in the document

#### Scenario: A truncated-id collision is loud

- **WHEN** two different complete artifact digests in one inventory share the same public id prefix
- **THEN** publication fails with a deterministic collision diagnostic rather than reporting them as one piece
