## MODIFIED Requirements

### Requirement: Backend server modes

The system SHALL serve the viewer as a FastAPI app via uvicorn on
`0.0.0.0:$SOLID_NODE_PORT` (default 8000). In static mode (default) it serves
the prebuilt React app from `app/build`; in dev mode (`--web-dev`) it proxies
page and JS requests to the npm dev server on `$SOLID_NODE_FRONTEND_PORT`
(default 3000). Starting the server SHALL NOT load or import the project
model. The server SHALL come up whether or not the project has ever built, so
the reload socket, the error endpoint, the snapshot routes and the bundle
route remain available.

#### Scenario: Broken node at viewer start

- **WHEN** the viewer process restarts while the project has a build error
- **THEN** the HTTP server starts anyway and the browser can poll
  `/_build_error` and reconnect the reload socket

#### Scenario: Viewer started before any build completed

- **WHEN** the viewer process starts in a project with no published build
  directory
- **THEN** the server starts, the snapshot routes report the snapshot as
  absent, and no project source is imported

### Requirement: Reload channel

The system SHALL expose a websocket at `/ws/reload` that sends the text
`"reload"` immediately on connect. Because develop restarts the viewer
process on each rebuild, the socket's close-and-reconnect cycle delivers the
reload signal. The client SHALL retry every 2 seconds when disconnected,
show an offline banner ("solid develop is not running") when the connection
drops or cannot be established, and on reconnect check `/_build_error` before
hiding the banner and refreshing the rendered model from the published
snapshot.

#### Scenario: Rebuild refreshes the browser

- **WHEN** a source edit completes a rebuild cycle
- **THEN** the browser's socket reconnects, receives `"reload"`, verifies no
  build error, and re-reads the published snapshot without a page refresh

## ADDED Requirements

### Requirement: The development viewer serves the published build snapshot

The system SHALL serve the published build directory's viewer snapshot and
its referenced model files over HTTP under a single documented prefix, so a
browser resolves every model path in the snapshot against the same prefix.
It SHALL serve whatever the build directory currently publishes, without
importing the project model or waiting for an artifact to appear, because the
builder publishes a snapshot and its models together. When no snapshot has
been published, a request for it SHALL report its absence rather than fail
the server.

#### Scenario: A completed build is served to the browser

- **WHEN** the browser requests the snapshot from a project whose build
  completed
- **THEN** it receives the published `viewer.json`, and every rigid model path
  in that document resolves to the published model file under the same prefix

#### Scenario: No build has been published yet

- **WHEN** the browser requests the snapshot before any build completed
- **THEN** the response reports the snapshot as absent and the server keeps
  serving the reload socket and the error endpoint

#### Scenario: Serving a project never imports it

- **WHEN** the viewer serves a snapshot for a project whose source raises on
  import
- **THEN** the snapshot and its models are served unchanged

### Requirement: The development viewer serves the installed viewer bundle

The system SHALL serve the viewer bundle of the running installation at a
documented URL, and SHALL report the API version the installation declares.
When the installation carries no built bundle, the response SHALL name the
remedy that builds it instead of serving an empty or partial script.

#### Scenario: An installation with a built bundle

- **WHEN** the browser requests the viewer bundle
- **THEN** it receives the installed bundle as JavaScript

#### Scenario: A source checkout with no built bundle

- **WHEN** the browser requests the viewer bundle from an installation that
  has none
- **THEN** the response reports the bundle as missing and names the command
  that builds it

### Requirement: The development page renders through the shared viewer package

The browser SHALL render the model by mounting the shared viewer package
against the served snapshot, and SHALL NOT carry its own tree walk, operation
composition, expression evaluation or animation clock. It SHALL name the
browser tab after the model. On a reload signal it SHALL refresh through the
mount handle so the maker's camera survives a rebuild, and on a build error it
SHALL show the error text instead of refreshing. When the bundle is
unavailable it SHALL show the reported remedy in the same pane.

#### Scenario: A built project is opened in the development loop

- **WHEN** a maker opens a completed project at the development viewer
- **THEN** the model renders with its declared colours, lit and framed, with
  the shared animation controls for an animated model

#### Scenario: A rebuild preserves the maker's viewpoint

- **WHEN** the maker has orbited the model and a rebuild completes
- **THEN** the refreshed model renders from the same camera position and orbit
  target

#### Scenario: A development page with no viewer bundle

- **WHEN** the page loads against an installation that has no built bundle
- **THEN** it shows the remedy naming the command that builds the bundle

## REMOVED Requirements

### Requirement: Recursive NodeAPI

**Reason**: The development viewer now serves the published build snapshot,
which the unified serializer produces for every consumer. A second, lazily
walked per-node representation of the same tree is the duplication this sprint
removes, and the snapshot-backed mode existed only to feed it.

**Migration**: Read the published `viewer.json` and its build-root-relative
model files from the build directory (`build-viewer-artifacts`). Hosts that
served a completed build through the framework viewer serve that directory
instead.

### Requirement: Absolute world-matrix composition

**Reason**: Browser-side pose composition now lives once in the shared viewer
package, which composes the same operation chains for every surface.

**Migration**: The composition contract and its parity with Python pose
composition are covered by the `viewer-package` and `kinematics`
capabilities.

### Requirement: Generation-based reload consistency

**Reason**: The generation counter guarded a lazily fetched per-node tree
whose STL callbacks could outlive a reload. The published snapshot is a single
document served with its models, and refreshing goes through the shared
viewer package's own reload.

**Migration**: Use the mount handle's reload, which rebuilds the tree from the
snapshot while preserving the view (`viewer-package`).

### Requirement: Client-side animation

**Reason**: Animation evaluation and the animation clock now live in the
shared viewer package for every surface.

**Migration**: The animation contract is covered by the `viewer-package` and
`kinematics` capabilities; the published snapshot carries `animation.fps` and
`animation.frames`.
