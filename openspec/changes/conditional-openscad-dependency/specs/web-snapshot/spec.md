## MODIFIED Requirements

### Requirement: The renderer is selected explicitly and never substituted

The system SHALL let a caller choose between the OpenSCAD renderer and the web
renderer, defaulting to OpenSCAD. When the web renderer is requested but cannot
run, the system SHALL fail with an error identifying what is missing, and SHALL
NOT render with the other renderer instead.

The rule SHALL hold symmetrically. When the OpenSCAD renderer is requested —
including by the default — and the OpenSCAD binary is unavailable, the system
SHALL fail with an error identifying the missing binary and naming the web
renderer as the alternative, and SHALL NOT render with the web renderer
instead.

The default renderer SHALL NOT vary with the availability of either renderer,
nor with whether the project's model is exact. A default that followed
availability would be substitution by another name, and one that followed the
project's backends would silently change the appearance of snapshots taken of
an existing project.

#### Scenario: The default renderer

- **WHEN** a maker renders a snapshot without choosing a renderer
- **THEN** the OpenSCAD renderer produces the image

#### Scenario: The browser is unavailable

- **WHEN** the web renderer is requested and its browser dependency is not
  installed
- **THEN** the command fails, naming both the package to install and the
  browser download step, and writes no image

#### Scenario: The viewer bundle is unavailable

- **WHEN** the web renderer is requested in an installation whose built viewer
  bundle is absent
- **THEN** the command fails with the same remedy the export command gives for
  that bundle, and writes no image

#### Scenario: The renderer is run by the superuser

- **WHEN** the web renderer is requested by a process running as root
- **THEN** the command fails with an error explaining that the browser cannot
  be sandboxed as root, and writes no image

#### Scenario: The OpenSCAD binary is unavailable

- **WHEN** the OpenSCAD renderer is requested, by default or explicitly, and
  the binary is not on the PATH
- **THEN** the command fails naming the missing binary and the web renderer as
  the alternative, and writes no image

#### Scenario: The default is unchanged by an exact model

- **WHEN** a snapshot is rendered without choosing a renderer for a project
  whose model is entirely exact
- **THEN** the OpenSCAD renderer is selected, exactly as for any other project
