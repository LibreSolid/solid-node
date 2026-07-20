# Web Viewer Specification

## Purpose

The development web viewer: FastAPI backend, the recursive NodeAPI, the
reload channel, and the browser rendering contract. Encodes ADR-012
(three.js), ADR-013 (React), ADR-014 (recursive NodeAPI), ADR-015 (FastAPI +
uvicorn), ADR-018 (file-based error propagation), and ADR-027 (absolute
world-matrix composition).

Code: `solid_node/viewers/web/viewer.py`, `solid_node/viewers/web/app/src/`,
`solid_node/viewers/openscad.py` (the sibling OpenSCAD GUI viewer).

## Requirements

### Requirement: Backend server modes

The system SHALL serve the viewer as a FastAPI app via uvicorn on
`0.0.0.0:$SOLID_NODE_PORT` (default 8000). In static mode (default) it serves
the prebuilt React app from `app/build`; in dev mode (`--web-dev`) it proxies
page and JS requests to the npm dev server on `$SOLID_NODE_FRONTEND_PORT`
(default 3000). If the node fails to load at (re)start, the server SHALL
still come up so the reload socket and error endpoint remain available.

#### Scenario: Broken node at viewer start

- **WHEN** the viewer process restarts while the project has a build error
- **THEN** the HTTP server starts anyway and the browser can poll
  `/_build_error` and reconnect the reload socket

### Requirement: Recursive NodeAPI

The system SHALL mount a sub-API per node under `/node`, with URLs mirroring
the tree (e.g. `/node/arm/elbow/`). `GET` on a node path returns its state:
serialized `operations`, `type`, `name`, `color`, `mtime`, and either
`children` (names) for non-rigid nodes or `model` (STL filename) for rigid
nodes. Rigid nodes SHALL serve their STL with `Last-Modified` /
`If-Modified-Since` (304) handling, and an STL request for a file still being
built SHALL wait for the file to appear rather than erroring. The same API
SHALL be constructible from a completed build viewer snapshot without loading
the project module.

#### Scenario: STL requested before build completes

- **WHEN** the browser requests a rigid node's STL while OpenSCAD is still
  rendering it
- **THEN** the response blocks (polling the filesystem) and streams the file
  once it exists

#### Scenario: A completed build is served without source loading
- **WHEN** a host creates NodeAPI from a completed build viewer snapshot
- **THEN** its recursive state and STL endpoints are available without a
  project-model import

### Requirement: Reload channel

The system SHALL expose a websocket at `/ws/reload` that sends the text
`"reload"` immediately on connect. Because develop restarts the viewer
process on each rebuild, the socket's close-and-reconnect cycle delivers the
reload signal. The client SHALL retry every 2 seconds when disconnected,
show an offline banner ("solid develop is not running") when the connection
drops or cannot be established, and on reconnect check `/_build_error` before
hiding the banner and reloading the tree.

#### Scenario: Rebuild refreshes the browser

- **WHEN** a source edit completes a rebuild cycle
- **THEN** the browser's socket reconnects, receives `"reload"`, verifies no
  build error, and reloads the node tree without a page refresh

### Requirement: Build error surfacing

The system SHALL expose `GET /_build_error` returning the contents of the
build dir's `errors.json` (`{error, tstamp}`) or `{}` when clear; the browser
displays the error text instead of reloading while an error is active, and
self-heals when the error clears.

#### Scenario: Error shown then cleared

- **WHEN** a reload finds a build error and a later save fixes it
- **THEN** the browser shows the traceback, then on the next reload signal
  clears it and renders the updated model

### Requirement: Absolute world-matrix composition

The browser SHALL render each mesh with `matrixAutoUpdate = false`, copying a
single absolute world matrix folded from the full operation chain (level 0 =
own operations, deeper levels = ancestors'), premultiplying each operation's
matrix in encounter order so later operations are outermost. Rotations are
about a world axis through the origin (degrees converted to radians);
translations are world translations. Composition SHALL be recomputed from
scratch on every application (idempotent) and match the Python-side pose
composition for arbitrary operation orderings.

#### Scenario: Assembly rotation carries translated children

- **WHEN** an assembly-level rotation sits above already-translated children
- **THEN** the children orbit onto the rotated position (matching
  `node.mesh` in Python) rather than spinning in place

### Requirement: Generation-based reload consistency

The browser SHALL guard tree reloads with a generation counter: a reload
first validates the root is fetchable (a failed reload leaves the current
tree untouched), then clears the scene and rebuilds under a new generation;
nodes and late-arriving STL callbacks from a superseded generation are
disposed instead of adding orphan meshes.

#### Scenario: Rapid successive reloads

- **WHEN** a second reload begins before the first finished loading STLs
- **THEN** meshes from the superseded generation never appear in the scene
  and their resources are disposed

### Requirement: Client-side animation

The browser SHALL animate by evaluating each operation's raw expression
against a context where `$t` advances continuously 0→1 (30 fps, 360 frames,
wrapping), using OpenSCAD-compatible math: degree-convention trig and `^`
rewritten to `pow()` (see the kinematics capability for the parity
contract).

#### Scenario: Animated assembly in the dev viewer

- **WHEN** an assembly's rotation expression references `$t`
- **THEN** the model animates continuously in the browser without any
  backend re-render

### Requirement: OpenSCAD GUI viewer

The system SHALL alternatively open the project in an OpenSCAD GUI
(`solid develop --openscad`): the viewer spawns `openscad <scad-file>` once,
records its PID in `.openscad.pid`, detects liveness via `os.kill(pid, 0)`,
and can terminate it cleanly.

#### Scenario: Viewer already open

- **WHEN** develop restarts while the recorded OpenSCAD PID is alive
- **THEN** no second OpenSCAD window is spawned
