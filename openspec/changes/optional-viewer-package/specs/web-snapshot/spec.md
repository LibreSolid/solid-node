# Web Snapshot

## MODIFIED Requirements

### Requirement: A snapshot can be rendered with a transparent background

The system SHALL render a node to a PNG carrying a real alpha channel, in which
every pixel not covered by the model is fully transparent, by describing the
node in a staging directory and having the installed viewer package display
that document in a headless browser and capture its canvas, as a separate
process. The rendered model SHALL be the published build of the node at the
requested animation time.

#### Scenario: A host composites a model onto its own surface

- **WHEN** a maker renders a snapshot with the web renderer
- **THEN** the PNG's background pixels are fully transparent and the model
  pixels are opaque, so a host may composite it over any surface without
  removing a background

#### Scenario: An enclosed light feature survives

- **WHEN** the model contains a light-coloured region enclosed by the
  silhouette
- **THEN** that region remains opaque in the PNG

### Requirement: The renderer is selected explicitly and never substituted

The system SHALL let a caller choose between the OpenSCAD renderer and the web
renderer, defaulting to OpenSCAD. When the web renderer is requested but cannot
run, the system SHALL fail with an error identifying what is missing, and SHALL
NOT render with the other renderer instead. A missing viewer package SHALL be
reported as `pip install "solid-node[viewer]"`; a missing browser SHALL be
reported with the viewer package's own remedy, which names its `snapshot`
extra and the browser download step.

The rule SHALL hold symmetrically. When the OpenSCAD renderer is requested —
including by the default — and the OpenSCAD binary is unavailable, the system
SHALL fail with an error identifying the missing binary and naming the web
renderer as the alternative, and SHALL NOT render with the web renderer
instead.

The default renderer SHALL NOT vary with the availability of either renderer,
with whether the viewer package is installed, nor with whether the project's
model is exact. A default that followed availability would be substitution by
another name, and one that followed the project's backends would silently
change the appearance of snapshots taken of an existing project.

#### Scenario: The default renderer

- **WHEN** a maker renders a snapshot without choosing a renderer
- **THEN** the OpenSCAD renderer produces the image

#### Scenario: The viewer package is unavailable

- **WHEN** the web renderer is requested in an installation without
  `solid-node-viewer`
- **THEN** the command fails naming the `viewer` extra, and writes no image

#### Scenario: The browser is unavailable

- **WHEN** the web renderer is requested and the viewer's browser dependency is
  not installed
- **THEN** the command fails with the viewer's remedy, naming both the package
  to install and the browser download step, and writes no image

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

### Requirement: A requested camera is honoured or refused, never approximated

The web renderer SHALL accept a camera specification in either OpenSCAD form —
eye and target, or translation, rotations, and distance — resolve it to an eye,
a target, an up direction and the field of view OpenSCAD uses, and hand those
to the viewer's capture, so the same specification frames the model
equivalently under either renderer. Options the browser viewer cannot honour
SHALL be refused with an error naming them, rather than ignored.

#### Scenario: A maker asks for a specific viewpoint

- **WHEN** a maker renders the same camera specification with each renderer
- **THEN** both images frame the model from the same viewpoint at the same
  scale

#### Scenario: A rotated camera

- **WHEN** the camera is specified as a translation, rotations, and a distance
- **THEN** the model appears with the orientation those rotations describe,
  including any roll

#### Scenario: An option the browser viewer cannot honour

- **WHEN** a maker requests the web renderer together with an OpenSCAD-only
  option
- **THEN** the command fails, naming the options that the web renderer does not
  support, and writes no image

#### Scenario: No camera requested

- **WHEN** no camera is specified
- **THEN** the whole model is framed automatically

## ADDED Requirements

### Requirement: The framework stages and the viewer photographs

The web renderer SHALL keep every step that knows what a node is — bringing
artifacts up to date under the build lock, serializing the photographed node
into its own staging directory, linking the models it names — and SHALL then
run the installed viewer package's capture command on that directory, through
the interpreter running the framework, passing the image size, the animation
time and the resolved camera. The framework SHALL NOT import the viewer's
capture code or its browser driver; a capture failure SHALL be reported with
the viewer's own message and SHALL write no image.

#### Scenario: The staged document is what the viewer photographs

- **WHEN** the web renderer runs
- **THEN** the viewer's capture is given a directory holding the staged
  `viewer.json` and the models it names, and nothing of the project's
  published build is handed over or altered

#### Scenario: The viewer's failure is the framework's failure

- **WHEN** the viewer's capture exits non-zero
- **THEN** the command fails with the viewer's message and writes no image
