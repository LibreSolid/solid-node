## Why

The development loop is the last surface with its own 3D renderer. `solid
develop` serves a per-node HTTP API that the CRA app walks lazily, flattening
every mesh into one scene with its own operation composition, its own
expression evaluator, and its own reload generation counter. That renderer has
no colours (`MeshNormalMaterial` with a `TODO use this.color`), no lights, and
no camera fit, while `solid export`, the Sphinx directive and the shop floor
all render the same models through the shared viewer package. An improvement to
how models are seen still has to be made twice.

The three cycles before this one removed the reasons to keep the duplicate: one
serializer publishes `viewer.json` and `manifest.json` with the same shape, the
viewer package covers every option its consumers need, and the built bundle now
ships inside the Python distribution. The development loop can now consume the
same document and the same bundle every other surface consumes.

## What Changes

- `solid develop`'s web viewer serves the published build snapshot
  (`viewer.json` and its model files) as static files instead of constructing a
  recursive per-node API from the loaded project model.
- The web viewer serves the installed viewer bundle, and reports the build
  remedy when an installation has no built bundle.
- The development React app becomes a shell: it mounts the shared viewer
  package against the published snapshot and calls the mount handle's
  `reload()` on the existing reload signal. It keeps the offline banner and the
  build-error pane.
- The development viewer gains inherited colours, lights, a fitted camera and
  the shared animation controls, because it now renders through the shared
  package.
- **BREAKING** (framework-internal): the per-node HTTP API under `/node`, the
  snapshot-backed `NodeAPI.from_build` / `SnapshotNodeAPI` mode, and the
  browser modules that consume them (`node.ts`, `evaluator.ts`, `animator.ts`,
  `viewer/STLViewer.tsx`, and the stubs beside them) are removed. No published
  document, URL under `/`, or CLI surface that another repository consumes
  changes; the shop floor reaches the framework only through `solid viewer` and
  the build directory.
- The development app drops the dependencies it kept solely for its own
  renderer (`three`, `@types/three`, `jokenizer`) and for removed panes
  (`re-resizable`, `react-ace`, `ace-builds`, `react-router-dom`).
- The jest tests that encode the flat-scene architecture are removed rather
  than ported; the reload tests survive, retargeted at the shell.

## Capabilities

### New Capabilities

None. This change moves an existing surface onto capabilities that already
exist (`viewer-package`, `viewer-distribution`, `build-viewer-artifacts`).

### Modified Capabilities

- `web-viewer`: the backend serves a published snapshot and the installed
  viewer bundle instead of a recursive per-node API; browser-side composition,
  reload-generation and animation requirements are removed because the shared
  viewer package owns that behavior; the reload channel, build-error surfacing
  and the OpenSCAD GUI viewer are unchanged.
- `build-viewer-artifacts`: the framework's private snapshot-backed viewer mode
  is replaced by the development viewer reading the published build directory
  directly.

## Impact

- Code: `solid_node/viewers/web/viewer.py`,
  `solid_node/viewers/web/app/src/` (App shell, reloader, removed modules and
  tests), `solid_node/viewers/web/app/package.json` and its lockfile.
- Consumes: `solid_node/viewers/bundle.py` (installed bundle path and API
  version) and the builder's published `viewer.json`.
- Tests: `tests/test_web_viewer.py` rewritten around the snapshot and bundle
  routes; a new browser test that the development page renders a built project
  with its declared colour; the app's jest suite reduced to the shell and
  reload behavior.
- Documentation: `docs/architecture.md` web-viewer synthesis; ADRs recording
  the retirement of the recursive NodeAPI and browser-side composition.
- Operational: an installation with no built viewer bundle gets a message
  naming the build command instead of a blank development page. Removing app
  dependencies regenerates `package-lock.json`, which must be produced in the
  primary framework checkout — never inside a worktree.
