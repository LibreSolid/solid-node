# User Documentation

## ADDED Requirements

### Requirement: The viewer's provenance and installation are stated

Every documentation page that installs, opens, embeds or photographs through
the browser viewer SHALL state that the viewer is the separate
`solid-node-viewer` package, licensed AGPL-3.0-only, installed with
`pip install "solid-node[viewer]"`, and SHALL state what the framework does
without it: `solid develop` opens OpenSCAD, `solid export --no-widget` and
the OpenSCAD snapshot renderer keep working, and the web-viewer commands name
the extra as their remedy. The README's installation section SHALL make the
licence difference visible before a reader installs the extra. Text that
tells a reader to build the viewer with npm inside the framework SHALL NOT
remain.

#### Scenario: A reader installs the framework

- **WHEN** a reader follows the README or quickstart installation steps
- **THEN** they see that the plain install has the OpenSCAD viewer, that the
  `viewer` extra adds the AGPL browser viewer, and that the licence differs

#### Scenario: A contributor looks for the viewer source

- **WHEN** a contributor reads the viewer or contributing pages
- **THEN** they are pointed at the solid-node-viewer repository and find no
  instruction to run npm inside solid-node
