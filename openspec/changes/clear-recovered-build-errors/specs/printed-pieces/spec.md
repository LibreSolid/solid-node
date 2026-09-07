## MODIFIED Requirements

### Requirement: Piece identity is stable and document-independent

A piece id SHALL depend only on the content of its built artifact. It SHALL NOT
depend on tree order, on the artifact's path, on which document publishes it,
or on the run that produced it. Republishing an unchanged model SHALL produce
an identical inventory.

#### Scenario: The same model published two ways agrees

- **WHEN** one model is published both as a normal build snapshot and as a
  static export
- **THEN** both documents report the same piece ids and the same counts, while
  keeping their own distinct model reference roots

#### Scenario: Rebuilding an unchanged model changes nothing

- **WHEN** a build runs again with no source change and no prior build error
- **THEN** the published document is byte-identical to the previous one and no
  consumer is notified of new work

#### Scenario: Recovering failure state preserves the document

- **WHEN** an unchanged successful build clears a prior build error
- **THEN** the published document and piece inventory remain byte-identical
  while the recovery can be reported as a publication-state change
