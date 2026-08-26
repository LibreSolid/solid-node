# Tasks: layered driver-controls

Red-first throughout: every behavior lands as a failing test before
the code that turns it green, and the red run is recorded in the task
note. All commands run from the worktree root with the workspace venv
(`PYTHONPATH="$PWD" ../../../.venv/bin/python`), vitest from
`solid_node/viewers/widget`. Never install into or build over the
symlinked `node_modules`/`dist`.

## 1. Pin `range` in design units

- [ ] 1.1 Red: extend the Python driver/document tests with a scaled
  driver declaring a range, asserting the table carries it verbatim
  and that nothing clamps to it; add the design-unit reading to the
  spike model (`range=(0, 100)` on `motor`) and update the
  enumeration/document assertions it feeds.
- [ ] 1.2 Green: state the design-unit meaning in `Driver`'s
  docstring and the serializer's drivers-table note. No behavioral
  Python change is expected — record the red/green evidence that the
  tests pin representation, not new logic.

## 2. Controls core (pure, tested)

- [ ] 2.1 Red: `controls.test.ts` covering D2–D5 and D8 —
  layer scoping (root bare ids; exact prefix-plus-one; other branches
  and descendants excluded), relative labels, design-unit display and
  slider bounds from `range`, int-dtype step = `scale`, rangeless
  drivers marked for numeric input, out-of-range pinning with
  truthful readout, navigable-children derivation from both tables
  (declaring layers all reachable, empty children absent), breadcrumb
  segments for a focus path, and re-scoping when focus resets.
- [ ] 2.2 Green: implement `controls.ts` as pure functions over the
  manifest tables, focus path, and current native values. No DOM, no
  three.js, no store import.

## 3. Viewer wiring

- [ ] 3.1 Red: `options.test.ts` cases for `driverControls`
  (`'inline'` default, `'none'` suppression) resolved beside the
  animation mode.
- [ ] 3.2 Green: resolve the option; build the chrome DOM in
  `viewer.ts` from the core's output — slider/numeric input plus
  readout per driver, button per instruction with busy state riding
  `trigger().done`, breadcrumb driving `setRoot`; subscribe via
  `onDriverChange`; route host `setRoot` and breadcrumb through one
  internal focus-changed path; rebuild on republish after store and
  navigation reconciliation; tear down on dispose. Accessible names
  on every control. Driverless documents and `'none'` render no
  chrome.
- [ ] 3.3 `tsc --noEmit` clean; full vitest suite green.

## 4. Documentation

- [ ] 4.1 ADR-056: record stage 3c status (chrome shipped on the 3b
  API; strict layer scoping; breadcrumb; `range` pinned to design
  units), and strike the UI-chrome item from open questions, leaving
  raycast picking noted as deferred.

## 5. Verification (independent, before archive)

- [ ] 5.1 Full Python suite from the worktree root; v8-engine via
  `solid test` (never plain pytest); both spike runners exit 0.
- [ ] 5.2 Widget vitest full run and `tsc --noEmit`.
- [ ] 5.3 Live browser drive of the chrome (D11): fresh temp bundle
  via the widget's esbuild config, spike-machine export, headless
  Chromium via playwright — breadcrumb descends to `x_axis`, `Home`
  button plays the ramp with busy indication and a travelling
  slider, slider jog moves the pose and reads back through
  `driver()`, out-of-range API value shows pinned-plus-truthful,
  `driverControls: 'none'` mounts chromeless with the API intact,
  and a version-1 driverless document is pixel-identical to before.
- [ ] 5.4 Sync baseline specs, archive the change, and commit the
  completed implementation record.
