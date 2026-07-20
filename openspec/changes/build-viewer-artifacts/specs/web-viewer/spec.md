## MODIFIED Requirements

### Requirement: Recursive NodeAPI
The system SHALL mount a sub-API per node under `/node`, with URLs mirroring the tree (e.g. `/node/arm/elbow/`). `GET` on a node path returns its state: serialized `operations`, `type`, `name`, `color`, `mtime`, and either `children` (names) for non-rigid nodes or `model` (STL filename) for rigid nodes. Rigid nodes SHALL serve their STL with `Last-Modified` / `If-Modified-Since` (304) handling, and an STL request for a file still being built SHALL wait for the file to appear rather than erroring. The same API SHALL be constructible from a completed build viewer snapshot without loading the project module.

#### Scenario: STL requested before build completes
- **WHEN** the browser requests a rigid node's STL while OpenSCAD is still rendering it
- **THEN** the response blocks (polling the filesystem) and streams the file once it exists

#### Scenario: A completed build is served without source loading
- **WHEN** a host creates NodeAPI from a completed build viewer snapshot
- **THEN** its recursive state and STL endpoints are available without a project-model import
