# Design: layered driver controls

## Context

Stage 3b left the widget with a complete programmatic driving API
(`drivers()`, `driver()`, `setDriver`, `onDriverChange`,
`instructions()`, `trigger`) and an assembly-focus interface
(`setRoot`, `assembly()`) whose `AssemblyPath` segments are the same
strings that qualify driver ids: `x_axis.motor` is path `['x_axis']`
plus local name `motor`. 3c joins them into on-screen chrome. No
Python or document change is needed beyond pinning `range`'s units;
everything the chrome consumes is already in the manifest.

The bench constraint that shapes the whole design: the widget's
`node_modules` and `dist` are symlinks into the pilot's primary
checkout. Nothing may be installed there, so no jsdom/happy-dom —
vitest runs in plain node. The widget already answers this with the
`controlPlan` pattern: pure, fully tested planning logic in its own
module, and a thin untested DOM layer in `viewer.ts` verified live in
a real browser.

## Decisions

- **D1 — pure core, thin DOM.** A new `controls.ts` module holds every
  decision as pure functions over plain data, unit-tested in node:
  scoping, labelling, unit conversion, slider bounds and step,
  breadcrumb derivation, out-of-range pinning. `viewer.ts` gains only
  the DOM assembly that renders what `controls.ts` computed and calls
  back into the existing store/navigation objects. No DOM test
  framework is added; the DOM layer is verified by the live browser
  drive (D11).

- **D2 — scoping is an exact prefix-plus-one match.** A driver or
  instruction belongs to the focused layer iff its qualified id splits
  into exactly the focus path's segments followed by one final
  segment. Root focus (`null`) selects bare ids. Which table an id
  sits in decides slider versus button; no assembly-tree walk is
  needed to scope.

- **D3 — labels are the final segment.** Relative to the focused
  layer, exactly one segment remains; that is the label. Sliders
  append the declared `unit` to the readout, not the label.

- **D4 — `range` is design units; sliders live in design units.**
  Display value = native × `scale` (identity when `scale` is null).
  Slider `min`/`max` come straight from `range`. A driver without a
  `range` gets a numeric input instead of a slider — bounds cannot be
  invented. Slider step: for `dtype: int`, step = `scale` (one native
  unit per stop, so every stop converts to a whole native value); for
  float, continuous.

- **D5 — the chrome never clamps.** Slider interaction converts
  through the existing `toNative` (round-half-to-even, same as
  Python's `round`) and calls the same `DriverStore.setDriver` the
  host API uses — one door, identical semantics, including
  mid-ramp replacement. A value out of range shows as a pinned slider
  plus a truthful numeric readout; the store value is untouched.

- **D6 — buttons trigger through the same door.** A button press is
  `trigger(qualifiedId)`; the returned handle's `done` promise drives
  the busy indication (`aria-busy` plus a visual state) and re-press
  is the ratified last-wins replacement, no debouncing.

- **D7 — live updates ride `onDriverChange`.** The chrome subscribes
  once per mount; a change to a scoped driver updates its slider and
  readout. This is the same channel hosts use — no private path into
  the store.

- **D8 — the breadcrumb is derived from the tables, not the tree.**
  Navigable children at a focus are the distinct next id segments
  strictly below the focus path, drawn from both tables. That
  construction reaches every declaring layer by definition and
  naturally omits children with nothing declared beneath — the spec's
  "need not be offered" is its automatic behavior. Descending and
  ascending call the existing `handle.setRoot`; host `setRoot` calls
  re-render the breadcrumb and controls through the same internal
  focus-changed notification, so widget and host can never disagree.

- **D9 — one option: `driverControls: 'inline' | 'none'`,** default
  `'inline'`, resolved in `options.ts` beside the animation mode. It
  gates the whole chrome (controls and breadcrumb). It does not touch
  the driving API. Driverless documents show no chrome regardless, so
  `'inline'` on a version-1 document is a no-op.

- **D10 — lifecycle.** Chrome is (re)built on mount, on document
  reload/republish (after the existing store and navigation
  reconciliation, so it reflects surviving values and a possibly
  reset focus), and on every focus change. Dispose unsubscribes and
  removes the chrome's DOM.

- **D11 — verification.** Unit tests pin all D2–D8 logic in
  `controls.test.ts`. The end-to-end proof is the same harness as
  3b's task 6.3: build a fresh bundle to a temp path with the
  widget's own esbuild config (never touching `dist` or the primary
  checkout), export the spike machine, drive the chrome in headless
  Chromium via playwright — press the rendered `Home` button, watch
  the slider and pose travel, jog the slider, verify readback through
  the host API, check the breadcrumb descends and ascends.

- **D12 — spike machine grows a `range`.** The spike's `motor` driver
  declares none, so the live check could not exercise slider bounds.
  Add `range=(0, 100)` (design-unit millimetres of travel) to the
  spike model — spikes are evidence and may move; the Python
  enumeration/document tests that assert table contents update with
  it.

## Risks / Trade-offs

- **No unit tests on the DOM layer** — accepted, consistent with all
  existing widget chrome; mitigated by keeping that layer thin
  (render-what-was-computed) and by the live browser drive.
- **A rangeless driver degrades to a numeric input** — less friendly,
  but honest; inventing bounds from `default` would be a silent
  product decision.
- **Strict layer scoping can show an empty control panel at a
  driverless root** — ratified deliberately as product pressure; the
  breadcrumb still shows the way down.
- **`range` unit pinning is retroactive** — no shipped project
  declares a scaled range yet (the spike is the only declarer), so
  pinning design units now is free; delaying it would let ambiguous
  declarations accumulate.

## Migration

None. Document schema unchanged (still version 2); hosts see one new
optional mount option; existing mounts and driverless documents are
pixel-identical.
