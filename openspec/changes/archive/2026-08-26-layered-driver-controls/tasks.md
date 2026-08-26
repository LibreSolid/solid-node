# Tasks: layered driver-controls

Red-first throughout: every behavior lands as a failing test before
the code that turns it green, and the red run is recorded in the task
note. All commands run from the worktree root with the workspace venv
(`PYTHONPATH="$PWD" ../../../.venv/bin/python`), vitest from
`solid_node/viewers/widget`. Never install into or build over the
symlinked `node_modules`/`dist`.

## 1. Pin `range` in design units

- [x] 1.1 Red: extend the Python driver/document tests with a scaled
  driver declaring a range, asserting the table carries it verbatim
  and that nothing clamps to it; add the design-unit reading to the
  spike model (`range=(0, 100)` on `motor`) and update the
  enumeration/document assertions it feeds.
  - RED: 6 failed, 43 passed — `test_a_scaled_drivers_range_reads_in_design_units`
    (`(0, 19200) != (0, 240.0)`), `test_the_range_travels_in_design_units_unconverted`
    and `test_the_table_never_clamps_a_bound_value_to_the_range`
    (`[0, 8000] != [0, 100]`), plus the three existing assertions the
    design-unit reading moves.
  - The two non-clamping pins passed red-run — deliberately: they
    assert the behavior already contracted, so they guard the
    representation change rather than demand new logic.
- [x] 1.2 Green: state the design-unit meaning in `Driver`'s
  docstring and the serializer's drivers-table note. No behavioral
  Python change is expected — record the red/green evidence that the
  tests pin representation, not new logic.
  - GREEN: 79 passed across `test_simulation_drivers.py`,
    `test_document_drivers.py`, `test_simulation_enumeration.py`,
    `test_simulation_sim.py`. Declarations moved to design units in
    the spike model, `tests/meta_project/{machine,axis}.py`, and the
    two local test fixtures; no framework code path changed.
  - `spike/expressions/run_spike.py` exits 0, all five verdicts
    revalidated. The committed parity fixture was regenerated (its
    `drivers` block embeds the spike's table): the only diff is
    `range: null` → `[0, 100]`, every producer value byte-identical.

## 2. Controls core (pure, tested)

- [x] 2.1 Red: `controls.test.ts` covering D2–D5 and D8 —
  layer scoping (root bare ids; exact prefix-plus-one; other branches
  and descendants excluded), relative labels, design-unit display and
  slider bounds from `range`, int-dtype step = `scale`, rangeless
  drivers marked for numeric input, out-of-range pinning with
  truthful readout, navigable-children derivation from both tables
  (declaring layers all reachable, empty children absent), breadcrumb
  segments for a focus path, and re-scoping when focus resets.
  - RED: `npx vitest run src/controls.test.ts` — 1 failed file, no
    tests collected: `Cannot find module './controls'`.
- [x] 2.2 Green: implement `controls.ts` as pure functions over the
  manifest tables, focus path, and current native values. No DOM, no
  three.js, no store import.
  - GREEN: 34 tests passed in `src/controls.test.ts`. `controls.ts`
    imports `./types` only (plain interfaces) — no DOM, no three.js,
    no `drivers.ts`.

## 3. Viewer wiring

- [x] 3.1 Red: `options.test.ts` cases for `driverControls`
  (`'inline'` default, `'none'` suppression) resolved beside the
  animation mode.
  - RED: 6 failed | 12 passed — `resolved.driverControls` undefined
    and `showsDriverChrome is not a function`.
  - GREEN: `driverControls` resolves beside `animation`, and the
    suppression decision itself is pure: `showsDriverChrome(mode,
    declaresDrivers)`, so the DOM layer decides nothing.
- [x] 3.2 Green: build the chrome DOM in
  `viewer.ts` from the core's output — slider/numeric input plus
  readout per driver, button per instruction with busy state riding
  `trigger().done`, breadcrumb driving `setRoot`; subscribe via
  `onDriverChange`; route host `setRoot` and breadcrumb through one
  internal focus-changed path; rebuild on republish after store and
  navigation reconciliation; tear down on dispose. Accessible names
  on every control. Driverless documents and `'none'` render no
  chrome.
  - `focusOn` is the single focus-changed path: `handle.setRoot` is now
    one line calling it, and every breadcrumb step and descent calls
    the same function, so navigation, camera and chrome move together.
  - `driveTo` is the single driver-value path, shared by
    `handle.setDriver` and every slider and number field.
- [x] 3.3 `tsc --noEmit` clean; full vitest suite green.
  - `npx tsc --noEmit`: clean (exit 0). `npx vitest run`: 10 files,
    141 tests passed (99 baseline + 37 controls + 5 options).
  - Live drive of the DOM layer (implementer's run of D11; task 5.3
    remains the independent verification): fresh esbuild bundle to
    `/tmp`, spike export, headless Chromium. Root shows no controls and
    offers `x_axis ▸`/`y_axis ▸`; descending gives one `motor` slider
    (`min 0 max 100 step 0.0125`, `aria-label "motor (ustep)"`) and one
    `Home` button; `Home` runs with `aria-busy="true"` while the slider
    travels (native 6851 → 5718 → 4452 → 3242 → 2185 → 1052 → 0) and
    clears on landing; a re-press mid-ramp is last-wins and only the
    newer run clears the busy state; jogging to 50 gives
    `driver()` 4000 and a moved pose; a host `setDriver(-400)` pins the
    slider at 0 with the readout showing `-5`; host `setRoot(['y_axis'])`
    moves the breadcrumb; `driverControls: 'none'` mounts with zero
    chrome nodes and a fully working API; a driverless document renders
    exactly `[CANVAS, DIV.animation-controls]`, as before this change.
    Zero console errors in both drives.

## 4. Documentation

- [x] 4.1 ADR-056: record stage 3c status (chrome shipped on the 3b
  API; strict layer scoping; breadcrumb; `range` pinned to design
  units), and strike the UI-chrome item from open questions, leaving
  raycast picking noted as deferred.
  - Implementation status gained the stage 3c entry, the `range`
    design-unit pinning, and the no-clamp judgment. "UI chrome for
    drivers" and "`range` is metadata, not a clamp" moved into a
    "Resolved by stage 3c" section; click-to-focus picking is now the
    named deferred item in its place. "Unit-story unification" is
    sharpened with the evidence 3c produced: `unit` names the native
    unit beside a design-unit value (`50 ustep` for 50mm).

## 5. Verification (independent, before archive)

- [x] 5.1 Full Python suite from the worktree root; v8-engine via
  `solid test` (never plain pytest); both spike runners exit 0.
  - Independent verifier: 884 passed + 44 subtests, exit 0 (879
    baseline, +5). v8-engine via `solid test v8_engine/v8_engine.py`
    against this worktree: 33 passed, 0 failed, exit 0. Expressions
    spike revalidated all five verdicts with the new range; axis spike
    scenario exits 0.
- [x] 5.2 Widget vitest full run and `tsc --noEmit`.
  - Independent verifier: 141 passed, 10 files (99 baseline);
    `tsc --noEmit` exit 0.
- [x] 5.3 Live browser drive of the chrome (D11): fresh temp bundle
  via the widget's esbuild config, spike-machine export, headless
  Chromium via playwright — breadcrumb descends to `x_axis`, `Home`
  button plays the ramp with busy indication and a travelling
  slider, slider jog moves the pose and reads back through
  `driver()`, out-of-range API value shows pinned-plus-truthful,
  `driverControls: 'none'` mounts chromeless with the API intact,
  and a version-1 driverless document is pixel-identical to before.
  - Independent verifier's own drive (fresh /tmp bundle, dist and
    primary checkout untouched; export with bind_declared_defaults):
    root shows 0 controls, breadcrumb `Machine` offering
    `x_axis ▸`/`y_axis ▸`; descending gives the `motor` slider
    (min 0, max 100, step 0.0125, aria-label "motor (ustep)") and
    `Home`; the press held aria-busy through 117 monotone whole-µstep
    samples 7994→0 (sampled in-page via onDriverChange), y_axis held
    8000, screenshot hash changed, busy cleared on landing; jog to 50
    read back 4000 native with readout `50 ustep`; setDriver(-400)
    pinned the slider at 0 with truthful readout `-5 ustep` and title
    "outside the declared range"; host setRoot(['y_axis']) and
    breadcrumb ascent re-scoped consistently; driverControls 'none'
    mounted 0 chrome nodes with setDriver/trigger/instructions all
    working (trigger landed at 0). Zero console or page errors.
    (Implementer's separate drive covered the driverless-document
    check; the manifest here declares drivers, so that check rode the
    implementer's run.)
- [x] 5.4 Sync baseline specs, archive the change, and commit the
  completed implementation record.
  - Archived as 2026-08-26-layered-driver-controls; merge applied
    +3 ADDED to viewer-package, +1 ADDED to
    viewer-assembly-navigation, ~1 MODIFIED in simulation (range in
    design units), all verified present in the baselines. The
    "1 incomplete task" archive warning was this task's own step.
