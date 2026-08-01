## ADDED Requirements

### Requirement: A host mounts the viewer and receives a handle

The viewer SHALL be mountable into a caller-supplied container element against a
published tree document, and SHALL resolve to a handle through which the host
controls that instance for its lifetime. The handle SHALL expose `dispose()`,
which stops rendering, releases the renderer and its observers, and leaves the
container empty; `view()`, which reports the current camera position and orbit
target; `reload()`, which rebuilds the tree from the source document while
preserving the camera the maker is currently looking through; and the declared
API version. Loading the viewer core SHALL NOT mount anything or otherwise
modify the document; mounting SHALL happen only when a host asks for it.

#### Scenario: A host unmounts a viewer

- **WHEN** a host calls `dispose()` on a mounted viewer's handle
- **THEN** rendering stops, the container holds none of the viewer's elements,
  and no further frame or resize callback runs

#### Scenario: A host remounts and keeps the maker's viewpoint

- **WHEN** a host captures `view()` from one mounted viewer, disposes it, and
  mounts a new one supplying that view
- **THEN** the new viewer shows the model from the captured camera position and
  orbit target rather than from a freshly fitted camera

#### Scenario: A host refreshes a changed model in place

- **WHEN** the source document changes and the host calls `reload()`
- **THEN** the viewer renders the new tree and the camera position and orbit
  target are unchanged

#### Scenario: Loading the core mounts nothing

- **WHEN** the viewer core is loaded by a host that has not called `mount()`
- **THEN** no element is created, no document is fetched, and no container is
  modified

### Requirement: One loader reads either published document

The viewer SHALL render from either published tree document — the portable
export `manifest.json` or the normal-build `viewer.json` — reading only the
fields the two share. The host SHALL supply the URL of the document and the base
that rigid model references resolve against, and that base SHALL default to the
document's own location so a self-contained export needs no extra
configuration. The viewer SHALL fail with a message naming the document and the
reason when it cannot be fetched or parsed.

#### Scenario: A build snapshot rooted elsewhere

- **WHEN** a host mounts against a `viewer.json` whose models are served from a
  route unrelated to the document's own location, supplying that route as the
  mesh base
- **THEN** the models load from that route and the assembly renders with the
  same tree, colours, and animation as the equivalent export

#### Scenario: A self-contained export

- **WHEN** a host mounts against an export `manifest.json` without supplying a
  mesh base
- **THEN** model references resolve beside the manifest and the export renders

#### Scenario: An unreachable document

- **WHEN** the source document cannot be fetched
- **THEN** mounting fails with an error naming the document and the failure

### Requirement: The host chooses how animation is presented

For a model whose operations contain `$t`, the viewer SHALL present animation in
the mode the host selects: an always-visible inline bar carrying play/pause and
a `0..1` timeline stepped at `1/frames`; that same bar behind a persistent
toggle control that starts collapsed and reports its expanded state
assistively; no controls at all; or externally driven, where the host sets the
animation time and the viewer renders no controls of its own. The host SHALL
also set the initial time within `0..1` and whether playback starts. In every
presented mode, playback SHALL advance one cycle per `frames / fps` seconds and
scrubbing the timeline SHALL pause playback. A model with no `$t` operation
SHALL present no animation controls in any mode.

#### Scenario: A shop floor hides the timeline until asked

- **WHEN** an animated model is mounted with the toggled presentation
- **THEN** the timeline bar is hidden, a persistent toggle is shown reporting
  itself as collapsed, and activating the toggle reveals the bar and reports it
  as expanded

#### Scenario: A published export shows the bar

- **WHEN** an animated model is mounted with the inline presentation
- **THEN** play/pause and the timeline are visible without further interaction

#### Scenario: A host drives time itself

- **WHEN** a model is mounted with externally driven animation and the host
  sets a time
- **THEN** the viewer renders that pose and presents no controls of its own

#### Scenario: A static model

- **WHEN** a model with no `$t` operation is mounted in any presentation mode
- **THEN** no play/pause, timeline, or toggle is created

### Requirement: The camera fits the model unless the host restores a view

The viewer SHALL orient the scene Z-up as in OpenSCAD and, once every mesh has
loaded, fit the camera to the loaded model bounds with orbit controls targeting
the model centre. When the host supplies a previously captured view, the viewer
SHALL adopt that camera position and orbit target instead of the fitted one,
while still deriving clipping from the model bounds so the model remains
visible.

#### Scenario: A first look at a model

- **WHEN** a model is mounted without a supplied view
- **THEN** the whole model is framed and orbiting rotates about its centre

#### Scenario: A rebuild during a work session

- **WHEN** a model is mounted with a supplied view
- **THEN** the camera is where the maker left it and the model is neither
  clipped nor beyond the far plane

### Requirement: Colour is inherited and falls back to a normal material

The viewer SHALL render each node with its own colour, or with the nearest
ancestor's colour when it declares none, and SHALL render a node with no colour
anywhere up the tree with the normal-based material the framework's viewers
already use.

#### Scenario: A part inherits its assembly's colour

- **WHEN** a node declares no colour and an ancestor does
- **THEN** the part renders in the ancestor's colour

#### Scenario: A colourless assembly

- **WHEN** no node in the tree declares a colour
- **THEN** every model renders with the normal-based material

### Requirement: The host names the canvas for its own styles and assistive tools

The viewer SHALL apply a host-supplied CSS class and host-supplied accessible
role and label to the rendered canvas, so a host page can style and describe the
model view within its own interface. Absent a host choice, the canvas SHALL
carry no class and no assistive attributes beyond what the renderer requires.

#### Scenario: A shop floor labels the model view

- **WHEN** a host mounts supplying a canvas class, role, and label
- **THEN** the canvas carries them and assistive tools announce the model view
  by that label

### Requirement: The viewer declares its API version

The package SHALL declare one API version, SHALL expose it on every mount handle
and on the browser global the published bundle installs, and SHALL make it
readable from the package without executing the bundle, so a host that ships
against a different version can report the mismatch as a sentence naming the
required and installed versions instead of rendering an empty pane. The version
SHALL be raised whenever the mount interface or handle changes incompatibly.

#### Scenario: A host checks compatibility before mounting

- **WHEN** a host reads the installed viewer's API version
- **THEN** it obtains the version the package declares, from a single declared
  source, without running the bundle in a browser

#### Scenario: A mounted viewer reports its version

- **WHEN** a host inspects a mount handle or the browser global
- **THEN** each reports the same declared API version
