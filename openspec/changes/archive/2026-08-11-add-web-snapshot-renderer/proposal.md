## Why

`solid snapshot` renders through the OpenSCAD CLI, which has no
transparent-background option: every PNG carries an opaque canvas. A host that
composites the image onto its own surface — SolidNode Studio's project hub,
which shows one screenshot per project — must therefore approximate
transparency by flood-filling near-white pixels inward from the border, a
heuristic that erases light features and cannot represent a soft edge.

The framework already ships a browser viewer that renders the same model tree
with WebGL. A headless browser can screenshot its canvas with a real alpha
channel, so the framework can produce the transparent image directly instead of
leaving every host to approximate one.

## What Changes

- `solid snapshot` gains `--renderer openscad|web`, defaulting to `openscad`.
  The OpenSCAD path is unchanged and remains the default because it is faster
  and needs no browser — agents inspecting their own work keep the cheap path.
- A new `web` renderer stages the current build, serves it over an ephemeral
  loopback HTTP server, mounts the viewer widget in headless Chromium, and
  screenshots the canvas with an alpha channel.
- `--renderer web` rejects, with a clear error naming them, the options the
  browser viewer cannot honour: `--projection`, `--colorscheme`, `--view`,
  `--preview`, `--render`. It does not silently ignore them.
- `--camera` is supported under `web` in both OpenSCAD forms. A new pure-math
  module converts the gimbal form (translate, rotations, distance) and passes
  the vector form (eye, target) through.
- The viewer widget gains two additive `mount()` options, `up` and `fov`, so a
  converted OpenSCAD camera reproduces OpenSCAD's framing rather than
  approximating it. Defaults are unchanged, so exports, `solid develop`, and
  existing hosts render exactly as before. The declared viewer API version
  becomes 3.
- The browser renderer is an optional install, `solid-node[web-snapshot]`.
  A missing Playwright package, a missing Chromium binary, a missing widget
  bundle, or running as root each fails with a specific, actionable error.
  `--renderer web` never falls back to OpenSCAD: a silent fallback would
  produce exactly the opaque image the renderer exists to avoid.

## Capabilities

### New Capabilities
- `web-snapshot`: rendering a node to a PNG with a real alpha channel through
  the packaged browser viewer — renderer selection, staging from the existing
  build, camera conversion, and the failure modes of an optional browser
  dependency.

### Modified Capabilities
- `cli`: the Snapshot command requirement gains renderer selection and the
  per-renderer option constraints.
- `viewer-package`: the camera requirement gains a host-supplied up vector and
  field of view; the declared API version becomes 3.

## Impact

- `solid_node/manager/snapshot.py` — reduced to shared validation and renderer
  dispatch; OpenSCAD command construction moves to `solid_node/viewers/openscad.py`.
- `solid_node/viewers/browser.py` (new) — staging, static serving, and the
  Playwright screenshot.
- `solid_node/core/camera.py` (new) — OpenSCAD camera specifications to eye,
  target, up, and field of view. Pure math, no I/O.
- `solid_node/viewers/widget/` — `up` and `fov` options in `options.ts`,
  `camera.ts`, and `viewer.ts`; `solidNodeViewerApi` 2 → 3.
- `pyproject.toml` — a `web-snapshot` extra depending on `playwright`.
- `_build/` is read, never written, by the web renderer: artifacts are
  hardlinked into a staging directory under a briefly held project build lock.
- Development environments must have Chromium installed: the end-to-end
  transparency test is mandatory, not skipped when a browser is absent.
- SolidNode Studio can drop its flood-fill approximation and pass
  `--renderer web`. That is a separate change in that repository, not part of
  this one.
