# Web Viewer Specification

## Purpose

The development viewer serves published build artifacts and renders them through
the reusable viewer package. It retains the reload channel, build-error
surface, and sibling OpenSCAD GUI viewer.

## Requirements

### Requirement: Backend server modes

The system SHALL serve the viewer as a FastAPI app via uvicorn on
`0.0.0.0:$SOLID_NODE_PORT` (default 8000). In static mode it serves the
prebuilt React app; in `--web-dev` mode it proxies page and JS requests to the
npm dev server. Starting the server SHALL NOT load or import the project model,
and SHALL succeed whether or not a build has been published, leaving the reload
socket, error, snapshot, and bundle routes available.

#### Scenario: Broken node at viewer start

- **WHEN** the viewer restarts while the project has a build error
- **THEN** it remains available for the browser to poll `/_build_error` and
  reconnect the reload socket

#### Scenario: Viewer started before any build completed

- **WHEN** the viewer starts with no published build directory
- **THEN** the snapshot reports its absence and the server remains available

### Requirement: Reload channel

The system SHALL expose `/ws/reload`, immediately send `"reload"` on connect,
retry disconnected clients every 2 seconds, and show an offline banner while
the development process is unavailable. On reconnect, it SHALL check
`/_build_error` before refreshing the published snapshot.

#### Scenario: Rebuild refreshes the browser

- **WHEN** a source edit completes a rebuild cycle
- **THEN** the browser re-reads the published snapshot without a page refresh

### Requirement: The development viewer serves the published build snapshot

The system SHALL serve the published `viewer.json` and its referenced model
files below one fixed URL prefix, resolving every request from the current build
directory without importing project source or waiting for an artifact.

#### Scenario: A completed build is served to the browser

- **WHEN** a browser requests `/build/viewer.json`
- **THEN** it receives the snapshot and every named model resolves below
  `/build/`

#### Scenario: Serving a project never imports it

- **WHEN** the served project's source would raise on import
- **THEN** its published snapshot remains servable unchanged

### Requirement: The development viewer serves the installed viewer bundle

The system SHALL serve the running installation's bundle at a documented URL
and report its API version. When absent, it SHALL report the command that builds
it rather than serving an empty or partial script.

#### Scenario: An installation with a built bundle

- **WHEN** a browser requests the bundle route
- **THEN** it receives JavaScript and the reported API version

### Requirement: The development page renders through the shared viewer package

The browser SHALL mount the shared viewer package against the served snapshot;
it SHALL NOT carry its own tree walk, operation composition, expression
evaluation, or animation clock. It SHALL refresh a changed model through the
package's targeted document update rather than rebuilding its tree, preserving
the maker's viewpoint and avoiding refetch or re-upload of unchanged geometry.
It SHALL name the tab after the model and show build errors or the missing-bundle
remedy in its error pane.

#### Scenario: A built project is opened in the development loop

- **WHEN** a maker opens a completed project
- **THEN** it is coloured, lit, framed, and has shared animation controls when
  animated

#### Scenario: An edit refreshes without a teardown

- **WHEN** a rebuild completes and the reload channel signals the browser
- **THEN** the page updates the model through the targeted document update,
  keeping its canvas, camera, and unchanged meshes

### Requirement: Build error surfacing

The system SHALL expose `GET /_build_error`, returning `errors.json` or `{}`;
the browser SHALL show an active error instead of refreshing and self-heal once
the error clears.

#### Scenario: Error shown then cleared

- **WHEN** a reload finds a build error and a later save fixes it
- **THEN** the browser shows the error, then renders the next successful build

### Requirement: OpenSCAD GUI viewer

The system SHALL alternatively open a project in OpenSCAD with
`solid develop --openscad`, retaining its existing PID lifecycle behavior.

#### Scenario: Viewer already open

- **WHEN** develop restarts while the recorded OpenSCAD PID is alive
- **THEN** it does not open a second window
