## MODIFIED Requirements

### Requirement: The viewer's provenance and installation are stated

Every documentation page that installs, opens, embeds or photographs through
the browser viewer SHALL state that the viewer is the separate
`solid-node-viewer` package, licensed AGPL-3.0-only, installed with
`pip install "solid-node[viewer]"`. It SHALL state that interactive
`solid develop` requires that package, while a plain framework installation
can build, test, export without the widget, run `solid develop --no-web`, and
snapshot through OpenSCAD. Web-viewer operations SHALL name the extra as their
remedy. The README's installation section SHALL make the licence difference
visible before a reader installs the extra. Text that tells a reader to build
the viewer with npm inside the framework SHALL NOT remain.

The v0.7 release material SHALL explain that OpenSCAD was solid-node's first
reliable viewer, that the browser viewer progressively became the faithful
machine surface as simulation gained drivers, instructions and flexible
motion, and that maintaining the less capable OpenSCAD GUI now obstructs that
roadmap. It SHALL distinguish removal of the GUI viewer and fallback from the
retained `OpenScadNode`, `Solid2Node`, SCAD-output, legacy-evaluation, and
OpenSCAD snapshot-renderer capabilities.

#### Scenario: A reader installs the framework

- **WHEN** a reader follows the README or quickstart installation steps
- **THEN** they see that the `viewer` extra supplies the sole interactive
  development viewer, that the plain install has no interactive viewer, and
  that the packages have different licences

#### Scenario: A reader migrates from the OpenSCAD viewer

- **WHEN** a v0.7 reader previously used `solid develop --openscad` or relied
  on its fallback
- **THEN** the release material explains why it was removed and directs them
  to `solid-node[viewer]` with ordinary `solid develop`, or to `--no-web` for
  a viewerless watch loop

#### Scenario: A reader distinguishes modelling from viewing

- **WHEN** a reader authors OpenSCAD or SolidPython geometry after the viewer
  removal
- **THEN** the documentation says those node types and the fixed-pose OpenSCAD
  snapshot renderer remain supported, without calling OpenSCAD an interactive
  solid-node viewer

#### Scenario: A contributor looks for the viewer source

- **WHEN** a contributor reads the viewer or contributing pages
- **THEN** they are pointed at the solid-node-viewer repository and find no
  instruction to run npm inside solid-node
