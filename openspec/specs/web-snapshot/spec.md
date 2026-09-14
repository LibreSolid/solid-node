# Web Snapshot Specification

## Purpose

Transparent PNG rendering through the packaged browser viewer.
## Requirements

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

#### Scenario: The viewer bundle is unavailable

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

### Requirement: A document the installed viewer cannot read is refused before the browser starts

The web renderer SHALL compare the schema version of the document it is about
to stage against the document versions the installed viewer reports it
renders, and SHALL REFUSE — naming the version the document needs, the
versions the viewer renders and the viewer's package version — before the
browser process starts, writing no image and leaving no staging directory
behind.

A capture is a one-shot: the viewer's own refusal would reach the caller as
an opaque non-zero exit from a headless page, and this capability's standing
rule is to fail with what is missing rather than substitute. It SHALL NOT
fall back to the OpenSCAD renderer, which is the same rule stated for a
missing viewer package and a missing browser.

When the installed viewer does report the version the document needs, the
capture SHALL proceed exactly as it does for any other document.

#### Scenario: A running model photographed by a viewer that cannot read it

- **WHEN** a maker runs the web renderer on a root declaring
  `time = Time.running()` in an installation whose viewer renders versions 1
  to 4
- **THEN** the command fails naming document version 5, the versions the
  viewer renders and the viewer's package version, no browser is started, no
  image is written, and no OpenSCAD render is attempted instead

#### Scenario: A viewer that can read it photographs it

- **WHEN** the same model is photographed in an installation whose viewer
  reports that it renders version 5
- **THEN** the staged document is handed to the viewer's capture and a PNG is
  written, exactly as for any other document

#### Scenario: An untimed model is unaffected

- **WHEN** a maker photographs a root declaring no time base with the web
  renderer
- **THEN** the version comparison passes and nothing about the capture
  changes
