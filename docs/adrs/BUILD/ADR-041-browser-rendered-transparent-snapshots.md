# ADR-041: Browser-Rendered Transparent Snapshots

**Status:** Accepted

**Date:** 2026-08-11

**Change:** `add-web-snapshot-renderer`

**Amends:**
- [ADR-021: Snapshot CLI Command for AI Agent Autonomy](ADR-021-snapshot-cli-command-for-agent-autonomy.md)

**Depends on:**
- [ADR-035: Reusable viewer core and declared API version](../EXPORT/ADR-035-reusable-viewer-core-and-declared-api.md)
- [ADR-038: Per-artifact atomic build publication](ADR-038-per-artifact-atomic-build-publication.md)

## Context and Problem Statement

ADR-021 gave agents a way to look at their own work by shelling out to the
OpenSCAD CLI. OpenSCAD renders onto an opaque canvas and exposes no
alpha-background option, so every snapshot carries a baked-in background.

That is invisible to an agent inspecting geometry and fatal to a host
compositing the image. SolidNode Studio's project hub shows one screenshot per
project over its own surface; lacking a transparent source, it flood-fills
near-white pixels inward from the image border. The heuristic erases pale
geometry, cannot express a soft edge, and pushes a framework deficiency into
every host that wants a composable image.

Since ADR-021, the framework acquired a second renderer of the same model tree:
the browser viewer that ADR-035 made a reusable core, shared by static exports,
the development loop, and the shop floor. A WebGL canvas has a real alpha
channel, and a headless browser can capture it with the page background
omitted. The framework can therefore produce the transparent image itself
rather than leaving each host to approximate one.

The problem is not "add a flag." It is deciding how a second renderer coexists
with the first without eroding the first, and without letting a caller receive
an image that quietly differs from what it asked for.

## Decision Drivers

- The OpenSCAD path is the hot path: agents run `solid snapshot` constantly, it
  is faster, and it needs no browser. It must not regress or lose its default.
- A browser is a heavy optional dependency — a pip package plus a separately
  downloaded binary — and cannot become a requirement of the framework.
- `_build/` is live. `solid develop` republishes it continuously and sweeps
  artifacts the new publication no longer references.
- An image is evidence. A snapshot that silently differs from the request is
  worse than no snapshot.

## Considered Options

1. **Post-process the OpenSCAD output in the framework** — move the hub's
   flood-fill into `solid snapshot`.
2. **Replace the OpenSCAD renderer with the browser renderer.**
3. **Two renderers behind an explicit, non-substituting choice.**

## Decision

Option 3. `solid snapshot` gains `--renderer openscad|web`, defaulting to
`openscad`.

Option 1 was rejected because the flood-fill is not a background removal but a
guess about which pixels are background; centralizing a guess makes it
authoritative without making it correct. Option 2 was rejected because it would
put a 150 MB browser download and a several-second startup in the path of the
command agents use most, to serve a need only compositing hosts have.

Four choices give the decision its shape.

### The renderer never substitutes itself

When `web` is requested and cannot run — Playwright absent, Chromium absent,
viewer bundle absent, or the process running as root — the command fails naming
the specific remedy. It does not fall back to OpenSCAD.

A fallback image is opaque, which is exactly the defect the web renderer exists
to remove, and a host would publish it without noticing. The same reasoning
governs options: `--projection`, `--colorscheme`, `--view`, `--render`, and
`--preview` have no browser equivalent, so combining them with `--renderer web`
is an error naming them rather than a silent omission. Honouring this required
`--projection` and `--colorscheme` to carry sentinel defaults, since a parser
default is otherwise indistinguishable from a caller's explicit request.

Running as root is refused rather than accommodated with `--no-sandbox`.
Disabling a browser sandbox is a security posture decision, and a screenshot
command is not entitled to make it on the operator's behalf.

### Geometry is borrowed from the published build, not copied

The renderer brings the photographed node's artifacts up to date, serializes
that node's tree into a staging directory beside `_build`, and hardlinks its
meshes there, all under `project_build_lock()`; it releases the lock before the
browser starts.

The document is serialized into staging rather than republished into the build.
Reusing the builder's publication step was rejected once its consequences became
visible: publication also sweeps every artifact the new document does not
reference and clears recorded build errors, so photographing a subassembly would
delete the meshes of the model `solid develop` is serving and swap the document
the shop floor reads. A snapshot is a reader; the published build belongs to
whatever produced it.

Serving `_build/` directly was rejected: a capture spans seconds, and a
concurrent `solid develop` rebuild can sweep an artifact the browser has not yet
fetched, silently yielding an incomplete model. Copying meshes, as `solid
export` does, was rejected because it would make mesh I/O the dominant cost of
every snapshot. A hardlink is constant-time regardless of mesh size and pins the
inode, so a sweep cannot pull the data out from under the capture.

Holding the build lock is safe for other producers because `Builder._start`
re-checks source mtime and artifact currency *after* acquiring the lock. A
builder that waits behind a snapshot re-evaluates what it must build; it never
skips a build because someone else held the lock. Holding delays a build, it
does not cancel one — and the lock covers staging only, not the capture.

### A camera means the same thing under either renderer

`solid_node/core/camera.py` converts both OpenSCAD camera forms — eye/target,
and translation/rotations/distance — into an eye point, target, up direction,
and field of view. Supporting only the eye/target form was rejected: the gimbal
form is what an interactive viewer produces when a maker orbits, so rejecting it
would reject the form people actually hold.

The viewer could not express that camera. It hardcoded a Z-up orientation and a
50° field of view, where OpenSCAD uses 22.5°, so a gimbal camera with roll had
no representation and an identical eye position framed the model at a different
scale. The widget therefore gains two additive `mount()` options, `up` and
`fov`, with unchanged defaults, so exports, the development loop, and the shop
floor render exactly as before. Per ADR-035's single-version rule, adding a
capability a host may require raises `solidNodeViewerApi` to 3.

### Dispatch does not live inside one renderer

OpenSCAD command construction and the xvfb wrapper move from
`manager/snapshot.py` to `solid_node/viewers/openscad.py`, beside the new
`viewers/browser.py`. The manager keeps shared validation and dispatch. Leaving
one renderer inside the dispatcher would make the two renderers structurally
unequal and bias every later change toward the incumbent.

## Consequences

**Positive**

- A transparent snapshot is a framework capability, so no host needs a
  background-removal heuristic.
- The OpenSCAD path is unchanged, still default, still dependency-free.
- Both renderers accept the same camera specification and frame it equivalently.
- The viewer gains camera controls usable by any host, not only this renderer.
- Snapshots cost no mesh copying and no redundant rebuild.

**Negative**

- Development environments must install Chromium: the end-to-end transparency
  and camera-fidelity tests are mandatory, not skipped when a browser is
  absent. A skipped test would leave the change's entire purpose unproven
  exactly where it runs.
- A colourless model renders in the viewer's normal-based fallback material
  (ADR-035's inherited-colour rule), which looks nothing like OpenSCAD's
  Cornfield. Accepted; hosts adopting the web renderer will see their
  thumbnails change appearance.
- The web renderer needs real meshes where OpenSCAD needs only a `.scad` file,
  so a stale project triggers a real build. Accepted: builds are incremental
  and normally current.
- Two renderers is two surfaces to keep honest. The rejection rules are what
  keep the second from decaying into an approximation of the first.

**Neutral**

- No orthographic projection, colour scheme, or view helper under `web`; adding
  them is separate work with a separate justification.
- The OpenSCAD gimbal rotation convention and its field of view are pinned by a
  differential test comparing silhouettes from both renderers, not asserted
  from documentation — a mirrored or quarter-turned camera looks plausible
  enough to survive review.
