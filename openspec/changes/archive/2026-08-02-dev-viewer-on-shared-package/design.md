## Context

`solid develop` runs a builder process and a FastAPI viewer process, restarting
both on every rebuild cycle. The viewer loads the project model in-process and
mounts a `NodeAPI` sub-application per node under `/node`, serving each node's
state and STL on demand; `SnapshotNodeAPI` reproduces that same API from a
completed build for hosts that have no project source. The CRA app walks those
URLs lazily (`node.ts`), flattens every mesh into one scene with an absolute
world matrix per mesh, evaluates `$t` expressions itself (`evaluator.ts`), runs
its own animation clock (`animator.ts`), and guards reloads with a generation
counter. It renders with `MeshNormalMaterial`, no lights and no camera fit.

Three cycles in this sprint removed the reasons that architecture existed:

- `unified-node-serializer` made `viewer.json` and `manifest.json` the same
  document shape, so one loader reads either.
- `viewer-package` turned `solid_node/viewers/widget` into the shared viewer
  with the options its consumers need, an API version, and a handle exposing
  `dispose()`, `view()`, `reload()` and `setTime()`.
- `viewer-bundle-delivery` builds that bundle into wheel and sdist and exposes
  it through `solid_node.viewers.bundle` and the `solid viewer` CLI accessor.

Constraints: the development app's `node_modules/` and `build/` are symlinked
from the primary checkout and `npm install` / `npm run build` must never run
inside a worktree; the shop floor reaches the framework only through the CLI
and the build directory, and does not use `/node`.

## Goals / Non-Goals

**Goals:**

- The development loop renders through the same bundle `solid export`, the
  Sphinx directive and the shop floor render through.
- The last per-node tree walk retires: `NodeAPI`, `SnapshotNodeAPI` and
  `node.ts` all go.
- The reload experience is preserved exactly: refresh after a successful
  build, offline banner while `solid develop` is down, build-error pane.
- Serving a development session stops depending on importing project source.

**Non-Goals:**

- Moving the development app off `react-scripts`, or replacing the React shell
  with a static page (see Decisions).
- Changing either published document's name, schema or path rooting.
- Changing the viewer package's mount interface or API version.
- Any new viewer capability beyond what the package already offers.

## Decisions

### Serve the published build directory under a fixed URL prefix

The viewer mounts the project's build directory as static files under `/build/`
and serves the snapshot at `/build/viewer.json`. Model paths inside
`viewer.json` are build-root-relative, so the browser resolves them against
that same prefix with no rewriting, and the mesh base is simply the document's
directory — the viewer package's default.

The prefix is fixed rather than derived from `SOLID_BUILD_DIR`, so the browser
contract does not change when a project renames its build directory. The
directory is resolved per request and the mount tolerates its absence, because
the builder publishes by replacing the directory and a session can start before
any build completed.

*Alternative rejected:* keep an HTTP API in front of the snapshot (a
`/node`-shaped façade over `viewer.json`). It would preserve a per-node
interface that no consumer wants and reintroduce the walk this cycle retires.

The old API's "wait for an STL still being rendered" behavior disappears with
it, and is not reimplemented: `build-viewer-artifacts` already guarantees a
published snapshot and all of its model files become visible together.

### Serve the installed bundle, and report its absence as a message

`GET /_viewer` returns `{available, apiVersion, remedy}` from
`solid_node.viewers.bundle`, and `GET /_viewer/bundle.js` serves
`bundle_path()`. The shell asks for status first; when the bundle is missing it
shows `missing_bundle_remedy()` in the pane that already shows build errors,
instead of a blank page and a console error.

This mirrors the shop floor's arrangement (obtain the bundle from the
framework, serve it from your own static route) while the development viewer,
being framework Python, reads it directly rather than through the `solid
viewer` CLI. The CLI accessor exists for out-of-process consumers.

### The shell loads the bundle as a script and uses the browser global

The app injects `<script src="/_viewer/bundle.js">` and mounts through
`window.SolidNodeWidget.mount(...)`, rather than importing the package into the
CRA build.

Reasons: CRA cannot compile TypeScript sources from outside `src/` without
ejecting; importing the package would put a second copy of three.js in the app
bundle, exactly the duplication this sprint removes; and the bundle is the
artifact that ships, so the development loop exercises what users get. It also
keeps the app's dependency list free of the renderer.

*Alternative rejected:* a workspace/relative import of the package sources.
It needs an install step inside worktrees, which this repository forbids.

### Presentation: the inline animation controls

The shell mounts with `animation: 'inline'` and `autoplay: true`. Today the
development viewer advances `$t` continuously with no controls; autoplay
preserves that, and the inline bar adds the play/pause and scrub that `solid
export` already shows.

*Alternative considered:* `animation: 'none'` with autoplay, which is exact
parity. Rejected because pausing and scrubbing a `$t` expression is precisely
what the development loop is for, and `inline` is an option the package
already ships rather than a new capability. This is a pilot-visible behavior
choice; ratification settles it.

### Keep the React shell and `react-scripts`

The app shrinks to a shell that owns the reload socket, the offline banner,
the error pane, the tab title and one mount call. That shell could be a static
`index.html` with a small script, which would delete React, CRA and an npm
build from `solid develop` entirely.

Rejected for this cycle: it would additionally change `packaging.py` (which
builds the CRA app into wheel and sdist), the `--web-dev` proxy contract in the
CLI spec, and the frontend directories `scripts/dev-env` symlinks — a blast
radius unrelated to sharing one viewer. It is the natural follow-up change once
this cycle proves the shell is that small.

### The shell reads the snapshot once for the tab title

Naming the browser tab after the model is existing behavior. The shell fetches
`/build/viewer.json` for `root.name` rather than asking the mount handle for
the tree.

*Alternative rejected:* extending the handle to expose the loaded tree. That
changes a ratified viewer-package interface, and would raise its API version,
for a page title.

### Tests are replaced, not ported

`node.test.ts`, `composeOperations.test.ts` and `evaluator.test.ts` encode the
flat-scene architecture and go with it; the behavior they covered is covered by
the package's own vitest suite. `reloader.test.ts` and `reload.test.ts` survive,
retargeted at the shell: the socket lifecycle, banner and error pane are
unchanged behavior, and the reload callback now drives the mount handle.

Python-side, `tests/test_web_viewer.py` is rewritten around the snapshot and
bundle routes. The red the cycle starts from is a browser test: the development
page rendering a built fixture project shows its declared colour, which today's
`MeshNormalMaterial` renderer cannot produce. It reuses the skip conditions
`tests/test_widget_e2e.py` already established for the bundle, a headless
chromium and Pillow.

### ADR dispositions, after implementation

Expected: ADR-014 (recursive NodeAPI) superseded; ADR-027 (absolute
world-matrix composition) superseded or narrowed to the shared package;
ADR-013 (React in the development viewer) amended to record React as a shell
around a framework-agnostic viewer. Written only once the implementation
confirms the final design, per the framework's ADR discipline.

## Risks / Trade-offs

- **A source checkout with no built bundle now shows a message instead of a
  model.** → The remedy names the exact command; `scripts/dev-env` symlinks
  `widget/dist` from the primary checkout, and distributions carry the bundle,
  so the case is a fresh clone that has not run the widget build.
- **The build directory is replaced while the server holds it.** → The path is
  resolved per request and the viewer process restarts on each rebuild cycle;
  a missing directory is a reported absence, not a crash.
- **Removing app dependencies regenerates `package-lock.json`, which must be
  produced in the primary checkout whose `node_modules` every bench shares.** →
  Sequence it as the last implementation step, while this cycle is the only
  open framework bench — the sprint serializes the framework viewer cycles for
  this reason — and rerun the app's tests and build afterwards.
- **Deleting jest tests loses coverage if the shell is not covered.** → The
  reload tests are retargeted rather than dropped, and the browser test proves
  the rendered result end to end.
- **Behavior change: animation controls appear in the development loop.** →
  Stated above as a ratifiable decision rather than an implementation detail.

## Open Questions

None blocking. Deliberately deferred: retiring `react-scripts` and the React
shell for the development viewer, and with it whether `--web-dev` still earns
its keep.
