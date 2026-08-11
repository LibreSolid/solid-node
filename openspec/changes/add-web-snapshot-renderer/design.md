## Context

`solid snapshot` shells out to the OpenSCAD CLI. OpenSCAD renders onto an
opaque canvas and offers no alpha-background option, so every snapshot arrives
with a background baked in. SolidNode Studio's project hub, which shows one
screenshot per project, currently works around this by flood-filling near-white
pixels inward from the image border — a heuristic that misjudges pale geometry
and cannot produce a soft edge.

The framework already renders the same model tree in the browser. The widget
under `solid_node/viewers/widget/` is built once and shared by `solid export`,
the develop-time web viewer, and the hub; a WebGL canvas has a genuine alpha
channel, and a headless browser can capture it with the page background
omitted. A spike confirmed this end to end: Chromium under SwiftShader, with no
X display, screenshotting the widget's canvas produced a PNG whose background
pixels were fully transparent.

Constraints that shape the design:

- The OpenSCAD path is faster and dependency-free, and coding agents use
  `solid snapshot` constantly to inspect their own work. It must stay the
  default and stay unchanged.
- A browser is a heavy optional dependency: a pip package plus a separately
  downloaded ~150 MB binary.
- `_build/` is live. `solid develop` republishes it continuously and
  `Builder._sweep_unreferenced_artifacts` deletes artifacts the new
  publication no longer references.

## Goals / Non-Goals

**Goals:**

- A snapshot with a real alpha channel, produced by the framework rather than
  approximated by each host.
- The OpenSCAD path preserved exactly, including as the default.
- A camera specification that means the same thing under both renderers, in
  both OpenSCAD forms.
- Honest failure: every unsupported option and every missing dependency is an
  error naming what is wrong, never a silently different image.
- No mesh copying and no redundant rebuilds; no interference with a concurrent
  `solid develop`.

**Non-Goals:**

- Orthographic projection, OpenSCAD colour schemes, and view helpers (axes,
  edges, wireframe…) under the web renderer. The widget has no equivalent, and
  adding one is separate work.
- Changing the widget's normal-based fallback material. A colourless model
  renders in the widget's normal colours, which differs visibly from OpenSCAD's
  Cornfield. Accepted as-is.
- Any pixel-scale or device-pixel-ratio option: `--imgsize` continues to mean
  literal output pixels under both renderers.
- Changing SolidNode Studio to use the new renderer, or removing its flood-fill
  workaround. That is a separate change in that repository.
- Caching staged directories between invocations.

## Decisions

### Renderer selection is an explicit option with no fallback

`--renderer openscad|web`, defaulting to `openscad`.

*Why not `--backend`:* "backend" already denotes the CAD technology
(CadQuery, OpenSCAD, JSCAD) that builds geometry. `solid snapshot --backend
openscad` would read as a statement about how the model is built rather than
how the image is drawn.

*Why no fallback to OpenSCAD when the browser is missing:* the fallback image
is opaque, which is precisely the defect the web renderer exists to remove. A
host would publish it without noticing. Failing loudly costs one error message;
falling back silently costs a wrong artifact.

### Unsupported options are rejected, which requires sentinel defaults

`--projection`, `--colorscheme`, `--view`, `--render`, and `--preview` fail
under `--renderer web`.

This is not implementable against the current parser: `--projection` defaults to
`perspective` and `--colorscheme` to `Cornfield`, so `argparse` cannot
distinguish "the user asked for this" from "nobody asked for anything". Both
become `default=None`, with the OpenSCAD default applied after parsing. The
OpenSCAD renderer's behaviour is unchanged; only the ability to detect an
explicit choice is added.

### Geometry is staged by hardlink under a briefly held build lock

The renderer brings artifacts up to date, reads `viewer.json`, and hardlinks
each referenced STL into a staging directory beside `_build`, all while holding
`project_build_lock()`. It then releases the lock and starts the browser.

*Why not serve `_build/` directly:* the capture spans seconds, and a
`solid develop` rebuild landing mid-capture can delete an artifact the browser
has not fetched yet. The result would be a silently incomplete model — the
worst possible failure for an image used as evidence.

*Why not copy, as `solid export` does:* a hardlink is O(1) regardless of mesh
size and pins the inode, so a concurrent sweep cannot remove the data. Copying
large meshes on every snapshot would be the dominant cost of the command. The
staging directory sits beside `_build` to keep it on the same filesystem.

*Why holding the lock is safe for other producers:* `Builder._start` records the
source mtime before acquiring the lock and re-checks both that mtime and
artifact currency after acquiring it. A builder that waits behind the snapshot
therefore re-evaluates what it must build; it never skips a build because
another process held the lock. Holding delays a build, it does not cancel one —
and the lock is held only for the staging, not the capture.

*On rebuild cost:* the web renderer needs real STLs, where the OpenSCAD
renderer needs only `assemble()` and a `.scad` file. On a stale project the web
renderer therefore triggers a real build. In practice builds are incremental and
kept current by the agent already working on the project, so this is accepted.

### The staged directory is served over an ephemeral loopback HTTP server

The widget fetches its manifest and meshes, which `file://` origins block. A
`SimpleHTTPRequestHandler` bound to `127.0.0.1:0` serves the staged manifest,
the hardlinked meshes, the widget bundle from the installed package, and a
generated mount page. The staging layout and the URL layout are the same fact,
so both live in `solid_node/viewers/browser.py`.

### Camera conversion is a pure-math module, and the widget learns two options

`solid_node/core/camera.py` converts either OpenSCAD camera form into an eye
point, a target, an up direction, and a field of view. No I/O, so it is
exhaustively unit-testable.

The gimbal form cannot be expressed by the widget as it stands. `viewer.ts`
hardcodes `camera.up = (0,0,1)`, and the `view` option carries only a camera
point and a target, so a gimbal camera with a non-zero middle rotation — which
rolls the view — has no representation. Separately, the widget's perspective
camera uses a 50° field of view while OpenSCAD uses 22.5°, so an identical eye
position frames the model at a visibly different scale.

The widget therefore gains two additive `mount()` options, `up` and `fov`,
threaded through `options.ts`, `camera.ts`, and `viewer.ts`. Defaults are
unchanged, so `solid export`, `solid develop`, and the hub render exactly as
before. Because a host may now require these, `solidNodeViewerApi` goes 2 → 3.

*Why not convert only the vector form and reject gimbal:* gimbal is what an
interactive viewer produces when a maker drags to orbit, so rejecting it would
reject the form people actually have in hand.

*Why the exact rotation convention is pinned by test, not by assertion:*
matching OpenSCAD's rotation order and signs from documentation alone is easy
to get subtly wrong — a mirrored or quarter-turned model looks plausible.
The differential test below pins it against OpenSCAD itself.

### Playwright drives Chromium; root is refused rather than accommodated

Playwright is the dependency, Chromium the browser, launched with
`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader` so no GPU
or X display is required. The canvas is captured with `omit_background=True`.

Chromium refuses to sandbox itself as root. Rather than passing `--no-sandbox`,
the renderer detects `uid 0` and fails with an explanation. Disabling the
sandbox to accommodate a container is a security posture decision that does not
belong to a screenshot command.

The optional extra is `solid-node[web-snapshot]`. Because `pip` cannot fetch the
browser binary, the missing-browser error names both `pip install
solid-node[web-snapshot]` and `playwright install chromium`.

A missing widget bundle reuses the existing `WidgetBundleMissing` remedy from
`solid_node/core/export.py`, which already tells a source checkout to run the
npm build. `solid export` fails the same way today, so this is a familiar error
rather than a new one.

### The OpenSCAD path moves out of the manager

`manager/snapshot.py` becomes shared validation plus dispatch; OpenSCAD command
construction and the xvfb wrapper move to `solid_node/viewers/openscad.py`,
beside the new `viewers/browser.py`. Dispatching from a module that also
contains one renderer's implementation would make the asymmetry structural.

### Transparency and camera fidelity are proven by a mandatory end-to-end test

The suite runs a real capture; it is not skipped when Chromium is absent.
Development environments must have it installed. A skipped test would leave the
change's entire purpose unproven wherever it actually runs.

Two properties are checked against a deliberately asymmetric model:

1. **Transparency** — corner and border pixels have alpha 0; model pixels have
   alpha 255.
2. **Camera fidelity** — the same `--camera` specification is rendered by both
   renderers, and the two silhouettes (the alpha mask from web, the
   non-background mask from OpenSCAD) are compared by intersection-over-union
   above a threshold. Comparing silhouettes rather than pixels tolerates the
   two renderers' different materials and lighting while still catching a
   mirrored, rolled, or misscaled camera. This is what pins the gimbal
   convention and the 22.5° field of view.

Everything below the browser — the camera math, option rejection, sentinel
defaults, hardlink staging, and the served layout — is unit-tested without a
browser.

## Risks / Trade-offs

- **The gimbal rotation convention is wrong in a plausible-looking way** → the
  differential silhouette test against OpenSCAD is written red-first, with at
  least one case having all three rotations non-zero so order and sign errors
  cannot cancel out.
- **The mandatory browser test makes a fresh clone's suite fail** → accepted by
  explicit decision; the setup path must install Chromium, and the failure
  message must say so rather than merely erroring inside Playwright.
- **Worktree development cannot rebuild the widget** — `scripts/dev-env`
  symlinks `solid_node/viewers/widget/dist` to the primary checkout, so
  building the widget inside this worktree would overwrite the primary
  checkout's bundle. The TypeScript changes here require a bundle rebuild to be
  exercised. This must be resolved with the pilot before the widget work
  begins; it is a workspace-tooling constraint, not a design choice.
- **A stale project makes a web snapshot slow** → accepted; builds are
  incremental and normally current.
- **Staging directory left behind if the process is killed** → it is created
  beside `_build` with a recognisable prefix and removed in a `finally`;
  `prepare_build_dir` already sweeps stray siblings of the build directory.
- **Colourless models look unlike their OpenSCAD counterparts** → accepted and
  documented; the hub's thumbnails change appearance when it adopts the web
  renderer.

## Open Questions

None outstanding. The widget-bundle-in-worktree constraint above is a tooling
question for the pilot, not an unresolved design decision.
