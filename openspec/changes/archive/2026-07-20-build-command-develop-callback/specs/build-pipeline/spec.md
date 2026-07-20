## ADDED Requirements

### Requirement: Build completion is observable
The build pipeline SHALL distinguish a complete successful model publication
from an intermediate render pass, a watched source change, and a failed
build.  Command and development lifecycle consumers SHALL use only complete
successful publication as the ready boundary for external observation.

#### Scenario: A model needs multiple render passes
- **WHEN** generating a model requires more than one render pass
- **THEN** the pipeline does not report a complete successful publication
until all current model artifacts are available

### Requirement: Last successful artifacts survive a failed later build
The pipeline SHALL keep the normal project build directory at its last
complete successful artifact state when a later load, assemble, or render
attempt fails.

#### Scenario: Rendering fails after a previous build
- **WHEN** a later render attempt fails after a project has a complete build
- **THEN** consumers of the normal project build directory can continue to
read the prior complete artifact state
