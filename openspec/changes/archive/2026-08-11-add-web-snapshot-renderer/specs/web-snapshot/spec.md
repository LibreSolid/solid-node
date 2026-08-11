## ADDED Requirements

### Requirement: A snapshot can be rendered with a transparent background

The system SHALL render a node to a PNG carrying a real alpha channel, in which
every pixel not covered by the model is fully transparent, by displaying the
packaged browser viewer in a headless browser and capturing its canvas. The
rendered model SHALL be the published build of the node at the requested
animation time.

#### Scenario: A host composites a model onto its own surface

- **WHEN** a maker renders a snapshot with the web renderer
- **THEN** the PNG's background pixels are fully transparent and the model
  pixels are opaque, so a host may composite it over any surface without
  removing a background

#### Scenario: An enclosed light feature survives

- **WHEN** the model contains a light-coloured region enclosed by the
  silhouette
- **THEN** that region remains opaque in the PNG

### Requirement: The web renderer reads the existing build without rebuilding it

The web renderer SHALL obtain geometry from the project's published build,
rendering only artifacts that are out of date, and SHALL NOT copy mesh data to
present it to the viewer. Beyond rendering those artifacts it SHALL NOT alter
the published build: it SHALL describe the photographed node in its own staging
area rather than republishing the build's document, and SHALL leave artifacts
and recorded build errors that document names untouched. It SHALL hold the
project build lock only while bringing artifacts up to date and staging them,
and SHALL release it before the browser starts. Staged artifacts SHALL remain
readable for the whole capture even if the published build is republished
meanwhile.

#### Scenario: A snapshot of an already-built project

- **WHEN** every artifact of the node is already current
- **THEN** the renderer rebuilds nothing and the capture reads the existing
  artifacts

#### Scenario: A rebuild lands while the browser is capturing

- **WHEN** another process republishes the build and removes artifacts the
  previous publication referenced, after the renderer has staged them
- **THEN** the capture still reads the staged artifacts and produces a complete
  model

#### Scenario: A snapshot of one part of a project being developed

- **WHEN** a maker photographs a node other than the one the published build
  describes
- **THEN** the published document still describes the same model afterwards,
  the artifacts it names are still present, and a recorded build error is still
  recorded

#### Scenario: Another producer waits for the build lock

- **WHEN** another build starts while a web snapshot holds the build lock
- **THEN** it waits, and once it acquires the lock it re-evaluates whether the
  published build covers its loaded source rather than skipping its build

### Requirement: The renderer is selected explicitly and never substituted

The system SHALL let a caller choose between the OpenSCAD renderer and the web
renderer, defaulting to OpenSCAD. When the web renderer is requested but cannot
run, the system SHALL fail with an error identifying what is missing, and SHALL
NOT render with the other renderer instead.

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

### Requirement: A requested camera is honoured or refused, never approximated

The web renderer SHALL accept a camera specification in either OpenSCAD form —
eye and target, or translation, rotations, and distance — and SHALL present the
model from that viewpoint with the same field of view OpenSCAD uses, so the
same specification frames the model equivalently under either renderer. Options
the browser viewer cannot honour SHALL be refused with an error naming them,
rather than ignored.

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
