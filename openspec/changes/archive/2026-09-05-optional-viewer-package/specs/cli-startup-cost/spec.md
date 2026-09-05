# CLI Startup Cost

## MODIFIED Requirements

### Requirement: The viewer command loads no geometry stack

The system SHALL answer `solid viewer` from the installed viewer package's
entry point alone. The invocation SHALL NOT import `cadquery`, `trimesh`,
`solid2`, or any node module, because none of them contributes to the bundle
path or its API version; and it SHALL NOT import the viewer package's server,
capture or rendering code, because the entry point answers without them.

#### Scenario: Reporting the bundle imports no CAD library

- **WHEN** `solid viewer` runs against an installation with `solid-node-viewer`
- **THEN** it prints the same single JSON object with the bundle path, export
  page, integer API version and package version, exits 0, and `cadquery` and
  `trimesh` are absent from the process's imported modules

#### Scenario: Reporting the bundle runs no viewer code

- **WHEN** `solid viewer` runs against an installation with `solid-node-viewer`
- **THEN** the viewer's server and capture modules are absent from the
  process's imported modules

#### Scenario: The missing-bundle path is unchanged

- **WHEN** `solid viewer` runs in an installation without `solid-node-viewer`
- **THEN** it prints nothing on standard output, names the extra on standard
  error, and exits 1
