## Context

`solid_node/viewers/widget` is 505 lines of TypeScript that already renders a
published tree correctly: `evaluator.ts` evaluates OpenSCAD expressions,
`tree.ts` mirrors the document as a three.js `Group` hierarchy with per-frame
local matrices, and `widget.ts` mounts it, fits the camera, builds an animation
bar, and auto-mounts every `[data-solid-widget]` element on load. Two other
renderers reproduce it — the shop floor's `viewer.ts` almost token for token,
and the development-loop app on a different architecture entirely.

What stops the other two from adopting it is not the rendering. It is that
`widget.ts` is an application, not a library: `mount()` resolves to `void`, so a
host cannot unmount, re-render, or ask what the maker is looking at; options
cover only initial animation state; model paths are always taken from the
manifest's own location; and merely loading the module mounts into whatever
`[data-solid-widget]` elements the page happens to have.

This cycle rests on `unified-node-serializer`, which converged `manifest.json`
and `viewer.json` onto one schema. The loader therefore reads shared fields
rather than branching per document. Model rooting stays a consumer parameter,
which is exactly what the shop floor's hardcoded `/artifacts/` is today.

Constraints: the published names are ratified as unchanged for this sprint
(`solid-widget.js`, `data-solid-widget`, `SolidNodeWidget`, and the directory
`solid_node/viewers/widget`); the package stays private; the bench cannot run
`npm install`, so no new dependency may be introduced; and `solid export`,
`solid_node/sphinx.py`, and every committed export must keep working unchanged.

## Goals / Non-Goals

**Goals:**

- A viewer core that any host can mount, control, and unmount, with the options
  the three consumers require and no side effect on load.
- One loader for both published documents, with mesh rooting supplied by the
  host and defaulting to the document's own location.
- A declared API version readable from the package by a Python caller, so the
  next cycle can report a mismatch as a sentence.
- Unchanged published export behavior, proven by the existing export, Sphinx,
  and headless-browser tests.

**Non-Goals:**

- Delivering the bundle inside the wheel or adding a CLI accessor
  (`viewer-bundle-delivery`).
- Changing the shop floor or the development-loop app (`floor-uses-framework-viewer`,
  `dev-viewer-on-shared-package`).
- Publishing to a package registry, renaming a published name or the package
  directory, or shipping TypeScript declarations.
- Any rendering capability beyond current parity: no new materials, lighting,
  measurement, sectioning, or selection.

## Decisions

**Split the entry point from the core; keep the bundle's entry file where it
is.** `src/viewer.ts` becomes the core, exporting `mount()` and the option and
handle types, and touching no global. `src/widget.ts` shrinks to the auto-mount
entry: it imports the core, mounts every `[data-solid-widget]` element with the
inline animation presentation and the page's `?t=` / `?autoplay=0`, and remains
`build.mjs`'s entry point, so `globalName: SolidNodeWidget` and
`outfile: dist/solid-widget.js` are untouched. The entry also re-exports
`mount` and the API version, so the global keeps its current shape and gains the
library surface.

*Alternative rejected:* one module with an `autoMount: false` opt-out. The
side effect happens at import, before any host can opt out, which is the whole
reason a second host cannot use it.

**One options object with flat keys and conservative defaults.** `mount(target,
sourceUrl, options)` keeps its current positional shape, so the auto-mount path
is unchanged. Options: `baseUrl` (default: the source URL's directory),
`animation` (`'inline' | 'toggle' | 'none' | 'external'`, default `'inline'`),
`time` (default `0`), `autoplay` (default `true` for animated models),
`view` (default: fit), `className`, `role`, `ariaLabel` (default: none). Every
default reproduces today's published behavior, so an export renders identically
with an empty options object.

*Alternative rejected:* nesting options under `animation: {...}` and
`canvas: {...}`. Reads better in isolation but makes every call site in the
three consumers deeper for no added expressiveness at this size.

**`mount()` resolves to a handle carrying `dispose`, `view`, `reload`,
`setTime`, and `apiVersion`.** `dispose()` clears the animation loop,
disconnects the `ResizeObserver`, disposes controls, renderer, and the tree's
geometries and materials, and empties the container. `view()` clones the camera
position and orbit target. `reload()` re-fetches the source document, builds a
replacement tree, swaps it into the scene, disposes the old one, and recomputes
only clipping from the new bounds — leaving camera position and orbit target
untouched. `setTime()` exists for the external presentation, where the host owns
the clock.

This is brief section 4's handle plus `setTime`, which the externally driven
animation mode requires in order to be usable at all; section 4 permits a cycle
to name and shape these differently as long as the behavior is covered.

*Alternative rejected:* returning the internal three.js objects and letting
hosts drive them. It makes every internal a public contract on the first cycle
that ships one.

**Declare the API version in `package.json` and inject it at build and test
time.** A `solidNodeViewerApi` field is the single declared source. `build.mjs`
reads it and passes it through esbuild's `define`; a new `vitest.config.ts`
applies the same `define` so tests and bundle can never disagree, and a test
asserts the handle's `apiVersion` equals the field. This is what makes the
version readable by a Python caller with `json.load` — the next cycle needs it
without building or running the bundle.

*Alternative rejected:* a TypeScript constant in `src/`. Python would have to
parse TypeScript to read it, and the next cycle would inherit that. Also
rejected: emitting a JSON sidecar into `dist/`, which is only readable after a
build the next cycle should not have to require.

**Toggled presentation emits class-named, unstyled elements; inline
presentation keeps today's inline styles.** In `'toggle'` mode the bar carries
`animation-controls`, the toggle carries `timeline-toggle` with `aria-expanded`,
and the package supplies no CSS — the host page styles them, which is what the
shop floor does today. In `'inline'` mode the bar keeps its current inline
styles, because a published export must render standalone with no stylesheet.

*Alternative rejected:* one presentation with a style hook. An export with no
host page and a shop floor with a full stylesheet want opposite defaults; a
single mode makes one of them wrong.

**Keep every decision in a pure function so vitest can reach it without a
DOM.** three.js geometry, matrix, and bounds classes run headless in node, but
element creation and `OrbitControls` do not. So the parts that carry judgement
are extracted as pure functions and unit-tested: resolving options against their
defaults, deriving the mesh base from the source URL, deciding from
`(mode, animated)` which controls a mount should build and whether they are
inline-styled or class-named, and framing bounds into a camera position, orbit
target, and near/far. Colour inheritance and tree composition stay where they
are in `tree.ts`, already reachable in node. DOM assembly becomes thin enough
that what remains untested by vitest is only element wiring.

**Drive the browser surface with Playwright, not with the screenshot harness.**
`tests/test_widget_e2e.py` today invokes `chrome --headless --screenshot` and
asserts on pixels. That renders one URL and returns an image: it cannot click a
toggle, read an attribute, or observe that a container was emptied — so
`dispose`, `view`/restore, `reload`, canvas chrome, and the toggle are all out
of its reach. Playwright's Python API is already importable in the development
venv, so the new cases drive a real page: mount through the bundle's global,
assert on the live DOM, click the toggle, and compare `view()` across a remount.
The existing pixel tests stay exactly as they are.

Playwright is undeclared in `setup.py` and in CI, precisely as `Pillow` already
is, and the new cases skip when it is absent — the posture this test module
already documents for itself. These tests therefore prove the browser surface
locally and are not a CI gate.

*Alternative rejected:* a self-asserting harness page that runs the scenario in
its own JavaScript and paints the outcome in a colour the existing screenshot
comparison can discriminate. It needs no new import, but it encodes the
assertions in an HTML fixture where they cannot be read as tests, and a harness
that fails to run at all still paints something.

*Alternative rejected:* a DOM environment for vitest. `jsdom` and `happy-dom`
are both absent, adding either means an npm install the bench is forbidden to
run, and neither provides the WebGL context the renderer needs — so the tests
that motivate it would still not run.

## Risks / Trade-offs

- **The external animation mode has no consumer until `dev-viewer-on-shared-package`.**
  It is specified in brief section 4 but first exercised a cycle later, so it
  could be shaped wrong. → Keep it to the minimum that mode means: create no
  controls, and let the host set time. Its whole cost is a branch and a setter,
  so a later correction is cheap.

- **Returning a handle changes `mount()`'s signature.** → The only in-repo
  caller is the auto-mount entry, which is changed in the same commit; the
  published global, attribute, filename, and query parameters are untouched, and
  the headless-browser tests assert exactly that a page written against the
  documented contract still renders.

- **Toggle-mode class names couple the package to a host's stylesheet.** →
  They are deliberately host-styling hooks, and the mode is opt-in; the shop
  cycle that selects it supplies the CSS it already has.

- **`reload()` keeps the camera while the model's bounds may have changed
  substantially.** → Recompute near and far from the new bounds while leaving
  position and target alone: the maker's viewpoint survives a rebuild without
  the model falling outside the clipping planes.

- **A build/test skew on the injected version would ship a bundle claiming the
  wrong API.** → The assertion that the handle's version equals `package.json`'s
  field runs in the suite, and the field is the only place the number is
  written.

- **The end-to-end tests skip when the bundle, a chromium, Pillow, or
  Playwright is missing, and CI declares none of them**, so the browser surface
  is proven locally or not at all and a green suite can be silent about it. →
  Report explicitly whether those cases ran or skipped when presenting evidence,
  rather than reporting the suite as uniformly green. Making them a CI gate
  would mean declaring browser dependencies for the whole framework, which is
  its own change.
