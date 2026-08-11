# Viewer Package Specification

## Purpose

The reusable, React-free browser viewer shared by static exports and future
framework hosts.

## Requirements

### Requirement: A host mounts the viewer and receives a handle

The viewer SHALL mount into a caller-supplied container against a published tree
document and resolve to a handle. The handle SHALL expose `dispose()` (stop
rendering, release resources and empty the container), `view()` (camera position
and orbit target), `reload()` (rebuild the document while preserving the view),
`artifactChanged(path)` and `manifestChanged()` (update only what changed),
assembly inspection and navigation operations, and the declared API version.
Loading the viewer core SHALL NOT modify the document; only an explicit mount
may do so.

#### Scenario: A host unmounts a viewer

- **WHEN** a host calls `dispose()`
- **THEN** rendering stops, the container is empty, and no later frame or
  resize callback runs

#### Scenario: A host remounts and keeps the maker's viewpoint

- **WHEN** a host captures `view()`, disposes, and supplies that view to a new
  mount
- **THEN** the new viewer uses the captured camera and orbit target rather
  than fitting again

#### Scenario: A host refreshes a changed model in place

- **WHEN** a source document changes and the host calls `reload()`
- **THEN** the new tree renders while camera position and orbit target remain
  unchanged

#### Scenario: Loading the core mounts nothing

- **WHEN** a host loads the core without calling `mount()`
- **THEN** no element is created, document fetched, or container modified

### Requirement: A host updates only what changed

The handle SHALL expose two targeted updates beside `reload()`.
`artifactChanged(path)` SHALL refetch the model file at that document-relative
path and replace the geometry of every node referencing it without adding or
removing nodes. `manifestChanged()` SHALL refetch the document and reconcile the
rendered tree in place, adding and removing nodes and applying changed operations
and colour. Both updates preserve the camera, orbit target, animation clock, and
every node the document still names.

#### Scenario: One artifact changes

- **WHEN** a host calls `artifactChanged()` with one model path
- **THEN** only that model is requested and replaced

#### Scenario: The model gains and loses parts

- **WHEN** a document adds one node and removes another, and the host calls
  `manifestChanged()`
- **THEN** the added node is rendered, the removed node and its resources are
  gone, and common nodes keep their meshes

#### Scenario: A placement edit costs no fetch

- **WHEN** a document changes only operations or colour
- **THEN** `manifestChanged()` updates the render without requesting a model

### Requirement: Geometry is refetched only when its identity changes

The viewer SHALL treat geometry as current only while both its model path and
`mtime` match the values it loaded, and SHALL refetch when either differs. A
node whose geometry `artifactChanged()` has just fetched SHALL count as current
for the `manifestChanged()` that immediately follows, even though the document
it fetches names a new `mtime` for that node, because the two calls loaded the
same bytes moments apart.

#### Scenario: A parameter change moves the model path

- **WHEN** a node's model path changes with an unchanged `mtime`
- **THEN** its geometry is refetched

#### Scenario: A source edit moves the mtime

- **WHEN** a node's `mtime` changes with an unchanged model path
- **THEN** its geometry is refetched

#### Scenario: A manifest update follows the artifact update it describes

- **WHEN** `manifestChanged()` names a new `mtime` for a node whose geometry
  `artifactChanged()` already replaced
- **THEN** `manifestChanged()` does not refetch that node's geometry

### Requirement: A failed update leaves the model standing

A targeted update that cannot fetch what it needs SHALL report the failure while
leaving the rendered model and camera in place; the handle remains usable for a
later update. The viewer SHALL fetch replacements before it removes any node.

#### Scenario: An artifact fetch fails

- **WHEN** `artifactChanged()` cannot fetch its model file
- **THEN** the previous model remains displayed and a later update can succeed

#### Scenario: A document fetch fails

- **WHEN** `manifestChanged()` cannot fetch or parse the document
- **THEN** the rendered tree is unchanged

### Requirement: One loader reads either published document

The viewer SHALL render either portable `manifest.json` or normal-build
`viewer.json`, reading their shared fields. The host supplies the document URL
and an optional mesh base; the base defaults to the document's directory. A
fetch or parse failure SHALL name the document and the reason.

#### Scenario: A build snapshot rooted elsewhere

- **WHEN** a host mounts a `viewer.json` with a mesh base unrelated to its
  document URL
- **THEN** models load from that base with the same tree, colours, and
  animation as the equivalent export

#### Scenario: A self-contained export

- **WHEN** a host mounts an export without supplying a mesh base
- **THEN** its model paths resolve beside the manifest and it renders

#### Scenario: An unreachable document

- **WHEN** the source document cannot be fetched
- **THEN** mounting fails with an error naming the document and failure

### Requirement: The host chooses how animation is presented

For a model with `$t` operations, the viewer SHALL present animation as an
always-visible inline play/pause and `0..1` timeline (`1/frames` step), the same
bar behind an initially collapsed accessible toggle, no controls, or externally
driven time with no controls. The host SHALL set initial time and autoplay.
Playback SHALL cycle every `frames / fps` seconds; scrubbing pauses it. Static
models SHALL present no controls.

#### Scenario: A shop floor hides the timeline until asked

- **WHEN** an animated model uses toggled presentation
- **THEN** the bar starts hidden behind a collapsed persistent toggle and the
  toggle reports its expanded state when activated

#### Scenario: A published export shows the bar

- **WHEN** an animated model uses inline presentation
- **THEN** play/pause and timeline are visible immediately

#### Scenario: A host drives time itself

- **WHEN** a host uses externally driven presentation and sets time
- **THEN** the viewer renders that pose with no controls

#### Scenario: A static model

- **WHEN** a model has no `$t` operation in any presentation mode
- **THEN** it creates no play/pause, timeline, or toggle

### Requirement: The camera fits the model unless the host restores a view

The viewer SHALL orient Z-up and, after meshes load, fit the model bounds with
orbit controls targeting its centre. A supplied view SHALL set position and
target instead, while near and far clipping continue to derive from bounds. A
host MAY additionally supply an up direction and a field of view; absent
either, the viewer SHALL keep its own Z-up orientation and default field of
view, so a host that supplies neither sees no change.

#### Scenario: A first look at a model

- **WHEN** a model mounts without a view
- **THEN** the whole model is framed and orbiting targets its centre

#### Scenario: A rebuild during a work session

- **WHEN** a model mounts with a supplied view
- **THEN** the camera is restored and the model is neither clipped nor beyond
  the far plane

#### Scenario: A host reproduces another renderer's framing

- **WHEN** a host mounts with a view, an up direction, and a field of view
- **THEN** the model is seen from that viewpoint, rolled to that up direction,
  and framed at that field of view

#### Scenario: An existing host is unaffected

- **WHEN** a host mounts without an up direction or field of view
- **THEN** the viewer frames the model exactly as it did before those options
  existed

### Requirement: Colour is inherited and falls back to a normal material

The viewer SHALL use a node colour or its nearest ancestor colour, and SHALL
use the framework's normal-based material when no colour is available.

#### Scenario: A part inherits its assembly's colour

- **WHEN** a node has no colour and an ancestor does
- **THEN** the part renders in the ancestor's colour

#### Scenario: A colourless assembly

- **WHEN** no node declares a colour
- **THEN** every model renders with the normal-based material

### Requirement: The host names the canvas for its own styles and assistive tools

The viewer SHALL apply a host-supplied CSS class, role, and accessible label to
the canvas. Absent a host choice, it SHALL add no such attributes.

#### Scenario: A shop floor labels the model view

- **WHEN** a host supplies a canvas class, role, and label
- **THEN** the canvas carries them for host styling and assistive tools

### Requirement: The viewer declares its API version

The package SHALL declare one API version, expose it on every mount handle and
the browser global, and make it readable without executing the bundle. It SHALL
be raised whenever the mount interface or handle changes incompatibly, and when
a capability a host may require is added to the handle. The declared version
SHALL be 3, reflecting the addition of host-supplied up direction and field of
view.

#### Scenario: A host checks compatibility before mounting

- **WHEN** a host reads the installed viewer API version
- **THEN** it obtains the package's single declared version without running a
  browser bundle

#### Scenario: A mounted viewer reports its version

- **WHEN** a host inspects a mount handle or the browser global
- **THEN** both report the same declared API version

#### Scenario: A host requires targeted updates

- **WHEN** a host needs `artifactChanged()` and `manifestChanged()`
- **THEN** the declared API version tells it whether they are available

#### Scenario: A host requires camera orientation control

- **WHEN** a host needs to supply an up direction and field of view
- **THEN** the declared API version tells it whether they are available
