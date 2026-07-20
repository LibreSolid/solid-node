## MODIFIED Requirements

### Requirement: Build command
The system SHALL provide `solid build <path>` as a node-scoped command using the command-first grammar and shared directory-to-`__init__.py` path resolution. On success it SHALL publish the complete normal build directory, including the viewer snapshot and its referenced model artifacts.

#### Scenario: Build command appears in CLI help
- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `build`

#### Scenario: Build output is available to a viewer host
- **WHEN** a user runs `solid build root` successfully
- **THEN** a framework viewer host can read the completed `_build` directory without importing `root`
