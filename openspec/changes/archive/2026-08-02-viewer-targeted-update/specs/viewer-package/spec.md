## ADDED Requirements

### Requirement: A host updates only what changed

The handle SHALL expose two targeted updates beside `reload()`:

- `artifactChanged(path)` SHALL refetch the model file at that document-relative
  path and replace the geometry of every node referencing it, leaving all other
  geometry, the camera, the orbit target and the animation clock untouched. It
  SHALL NOT add or remove nodes.
- `manifestChanged()` SHALL refetch the published document and reconcile the
  rendered tree with it in place — adding nodes it introduces, removing nodes it
  drops, and applying changed operations and colour — while preserving the
  camera, the orbit target, the animation clock, and every node the document
  still names.

Both SHALL resolve when the update is applied.

#### Scenario: One artifact changes

- **WHEN** a host calls `artifactChanged()` with the path of one model file
- **THEN** that model's geometry is replaced, no other model file is requested,
  and the camera and orbit target are unchanged

#### Scenario: The model gains and loses parts

- **WHEN** a document adds one node and removes another, and the host calls
  `manifestChanged()`
- **THEN** the added node is rendered, the removed node and its resources are
  gone, and the nodes named by both documents keep their existing meshes

#### Scenario: A placement edit costs no fetch

- **WHEN** a document changes only operations or colour and the host calls
  `manifestChanged()`
- **THEN** the rendered model moves or recolours and no model file is requested

### Requirement: Geometry is refetched only when its identity changes

The viewer SHALL treat a node's geometry as current while the document's model
path and `mtime` for that node both match what the node already loaded, and
SHALL refetch when either differs. It SHALL NOT infer staleness from either
value alone.

#### Scenario: A parameter change moves the model path

- **WHEN** a node's `model` path changes while its `mtime` is unchanged
- **THEN** its geometry is refetched

#### Scenario: A source edit moves the mtime

- **WHEN** a node's `mtime` changes while its `model` path is unchanged
- **THEN** its geometry is refetched

#### Scenario: An unchanged node is left alone

- **WHEN** a node's `model` path and `mtime` are both unchanged
- **THEN** no request is made for that model and its existing mesh is kept

### Requirement: A failed update leaves the model standing

A targeted update that cannot fetch what it needs SHALL leave the previously
rendered model and camera in place, SHALL report the failure to the caller, and
SHALL leave the handle usable so a later update succeeds. The viewer SHALL NOT
remove a node before the geometry replacing it has arrived.

#### Scenario: An artifact fetch fails

- **WHEN** `artifactChanged()` cannot fetch the named model file
- **THEN** the call reports the failure, the previously rendered model is still
  displayed, and a later successful update renders normally

#### Scenario: A document fetch fails

- **WHEN** `manifestChanged()` cannot fetch or parse the document
- **THEN** the call reports the failure and the rendered tree is unchanged

## MODIFIED Requirements

### Requirement: A host mounts the viewer and receives a handle

The viewer SHALL mount into a caller-supplied container against a published tree
document and resolve to a handle. The handle SHALL expose `dispose()` (stop
rendering, release resources and empty the container), `view()` (camera position
and orbit target), `reload()` (rebuild the document while preserving the view),
`artifactChanged(path)` and `manifestChanged()` (update only what changed), and
the declared API version. Loading the viewer core SHALL NOT modify the
document; only an explicit mount may do so.

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

### Requirement: The viewer declares its API version

The package SHALL declare one API version, expose it on every mount handle and
the browser global, and make it readable without executing the bundle. It SHALL
be raised whenever the mount interface or handle changes incompatibly, and
whenever a capability a host may require is added to the handle.

#### Scenario: A host checks compatibility before mounting

- **WHEN** a host reads the installed viewer API version
- **THEN** it obtains the package's single declared version without running a
  browser bundle

#### Scenario: A mounted viewer reports its version

- **WHEN** a host inspects a mount handle or the browser global
- **THEN** both report the same declared API version

#### Scenario: A host requires targeted updates

- **WHEN** a host needs `artifactChanged()` and `manifestChanged()`
- **THEN** the declared API version tells it whether the installed viewer has
  them, without inspecting the handle
