## MODIFIED Requirements

### Requirement: Build completion is observable
The build pipeline SHALL distinguish a complete successful model publication from an intermediate render pass, a watched source change, and a failed build. Command and development lifecycle consumers SHALL use only complete successful publication as the ready boundary for external observation. A complete publication SHALL include the viewer snapshot and every model artifact it references.

#### Scenario: A model needs multiple render passes
- **WHEN** generating a model requires more than one render pass
- **THEN** the pipeline does not report a complete successful publication until all current model artifacts and the current viewer snapshot are available
