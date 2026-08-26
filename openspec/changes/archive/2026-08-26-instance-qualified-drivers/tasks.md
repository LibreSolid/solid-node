# Tasks: instance-qualified drivers

Red-first throughout: every behavioral task lands its failing test
before the change that turns it green. `node/` never imports
`simulation/`.

## 1. Qualified identity and the driver token (kinematics)

- [x] 1.1 Red tests for qualified-id computation: dotted path from
  linked names, bare name at root, loud failure on unlinked and on
  illegal (`<attr>-<index>`) segments, no fallback and no
  sanitization
  — `tests/test_driver_ids.py` red on
  `ModuleNotFoundError: solid_node.node.qualified`
- [x] 1.2 Implement the qualified-id walk on linked trees and the
  `DriverToken` (`OpenSCADConstant` subclass stringifying as the id);
  verify tokens ride solid2 arithmetic and `solid_node.math` symbolic
  trig with red tests from the spike's expression shapes (linear,
  port-scaled, degree trig, mixed `$t`, `^`)
  — `solid_node/node/qualified.py`; 12/12 green. `DriverDeclaration`
  marker added there so the node layer can recognize a declaration
  without importing `simulation/`; `simulation.Driver` subclasses it.

## 2. Qualified state binding (kinematics)

- [x] 2.1 Red tests: sibling instances bind independently via
  qualified entries; consumed path segment strips on descent; `time`
  propagates flat; ambiguous bare bind fails listing colliding ids;
  unambiguous bare bind still works; `clear_state` accepts qualified
  names; existing flat/merge/idempotency scenarios stay green
  — `tests/test_state_binding.py::QualifiedStateBindingTest`, 7 red on
  the qualified entry never reaching the child (`KeyError: no driver
  state 'motor' bound`)
- [x] 2.2 Implement qualified `set_state`/`clear_state` delivery and
  make the propagation walk link children before recursing
  (`_rendered_children`), preserving leaf no-op tolerance
  — 21/21 green; full suite 816 passed, zero regressions from the
  linking change

## 3. Symbolic serialization mode and document schema v2 (export)

- [x] 3.1 Red tests: serializing a driver-declaring tree binds every
  declared driver to its token internally (never through
  `set_state`'s numeric door — `_validate_state` untouched), emits
  expressions with qualified ids verbatim even from a
  numerically-snapshotted node, and restores the prior binding after,
  matching the existing symbolic-`$t` producer guarantee
  — `tests/test_document_drivers.py` red on
  `ImportError: cannot import name 'drivers_table'`
- [x] 3.2 Red tests for the v2 document: `version: 2`, `drivers`
  table with declared metadata verbatim (`range`
  presentation-only), every referenced id present in the table, empty
  table for driverless trees, `manifest.json`/`viewer.json` parity
  — same file; parity pinned in `tests/test_export.py`
- [x] 3.3 Implement symbolic mode in the serializer and export
  producer; bump the shared schema version; update consumers for the
  version gate (widget/web viewer render empty-table v2 documents
  exactly as v1; a non-empty table fails loudly — evaluation is stage
  3b)
  — `symbolic_drivers`/`drivers_table` in `core/serializer.py`, used by
  `core/export.py` and `core/builder.py`; `viewer.ts:assertRenderable`
  + `src/document.test.ts` (verified red with the gate disabled);
  vitest 43/43. The web-snapshot producer keeps a numeric document and
  an empty table — see the note under "Deviations" below.
- [x] 3.4 Red test that the `.scad` path still substitutes bound
  driver values numerically with `$t` live (spike verdict 4 as a
  regression test)
  — `tests/test_document_drivers.py::ScadSubstitutionTest`

## 4. Qualified simulation layer (simulation)

- [x] 4.1 Red tests for tree-wide enumeration: qualified ids with
  declaration metadata off a driverless root with declaring
  descendants; loud failure through illegal segments
  — `tests/test_simulation_enumeration.py` red on
  `ModuleNotFoundError: solid_node.simulation.enumeration`. Landed
  before task 3 because the export producer consumes this authority
  (D6: one enumeration feeds bank AND driver table).
- [x] 4.2 Implement the enumeration authority; rekey the `Sim` bank,
  trajectory, and programs by qualified id; construction binds
  defaults tree-wide (red: driverless-root scenario from the spike)
  — `solid_node/simulation/enumeration.py`;
  `tests/test_simulation_sim.py::QualifiedSimTest` 3 red then green
- [x] 4.3 Red tests then implementation for qualified instructions:
  discovery on any node, `x_axis.Home` ramps only `x_axis.motor`,
  unknown trigger lists known qualified names, target conversion
  unchanged
  — `QualifiedInstructionTest`, 2 red then green
- [x] 4.4 Red tests then implementation for the simulation clock:
  each tick binds global `time` to exact `k*dt` seconds; `self.time`
  under a Sim reads it; symbolic `$t` restored after; existing
  whole-tick and deferred-action semantics unchanged
  — `SimulationClockTest`, 4 red then green

## 5. Build-path defaults (build-pipeline)

- [x] 5.1 Red test: a driver-declaring project with a bare `__init__`
  builds and tests through the CLI; a driverless project's load path
  performs no binding
  — `tests/test_build_defaults.py` (2 red on the unbound driver) and
  `tests/test_meta.py::DriverDefaultsMetaTest` (both red end-to-end
  with the loader call disabled)
- [x] 5.2 Implement default binding in the loader/manager via the
  enumeration authority; remove the self-bind workaround from the
  `tests/meta_project` fixture and note it in the fixture
  — `core/loader.py:load_node`; `tests/meta_project/axis.py` self-bind
  deleted and its docstring rewritten; fixture green under both
  `solid test` and pytest

## 6. Caller validation and records

- [x] 6.1 Migrate `spike/expressions/` onto the shipped API: dissolve
  the shims in `symbolic.py` (tokens, qualified bank, linked-walk
  workarounds), rerun `run_spike.py` — all five verdicts must
  revalidate — and add an addendum to
  `spike/expressions/FINDINGS.md`; rerun `spike/axis/scenario.py`
  — `symbolic.py` reduced to `collect_ops` (measurement, not a shim);
  `run_spike.py` exit 0, all five verdicts revalidate, parity
  unchanged at 2.487e-14 / 4.302e-16; `spike/axis/scenario.py`
  unmodified, exit 0. The revalidation caught a real defect: the
  ambiguous-bind rollback re-rendered an unbound tree and raised the
  unbound-read `KeyError` over the `ValueError` that caused it —
  fixed, and pinned by
  `test_an_ambiguous_bare_name_on_an_unbound_tree_still_says_so`.
- [x] 6.2 Full framework suite green (pytest, from the worktree with
  the workspace venv); zero regressions against the 813 baseline
  — `PYTHONPATH="$PWD" .venv/bin/python -m pytest tests/`:
  **872 passed, 44 subtests, 0 failed** (813 baseline + 59 new);
  widget `npx vitest run`: 43 passed (40 + 3 new)
- [x] 6.3 v8-engine unchanged: `solid test` 33/33 via the worktree
  `PYTHONPATH`
  — `Ran 33 tests in 215.30 seconds: 33 passed, 0 failed`; the project
  working tree untouched
- [x] 6.4 Update `docs/architecture.md` (qualification, symbolic
  serialization mode, schema v2, build-path defaults resolved) and
  ADR-056 (implementation status; open questions: build-path defaults
  and time-driver unification resolved; stage-3b items remain);
  archive the change and sync baseline specs
  — **documentation done**: `docs/architecture.md` (kinematics
  qualification + token + declaration marker, the enumeration
  authority and the qualified/clocked `Sim`, symbolic serialization
  mode and schema v2, loader default binding, restated stage
  boundaries) and ADR-056 (stage 3a implementation status; document
  schema versioning, build-path defaults and time-driver unification
  moved to resolved; client-side driver evaluation and name
  sanitization added as the remaining stage-3b items; ADR-022
  staleness annotated with seam 7's status). Archive and baseline
  spec sync performed after independent verification (872 pytest +
  44 subtests, v8-engine 33/33 via `solid test`, both spike runners
  exit 0 from clean state, widget vitest 43/43, `node/`→`simulation/`
  import grep clean).

## Deviations and judgment calls

- **`DriverDeclaration` in `node/`.** `set_state`'s ambiguity check
  and its qualified delivery both need the node layer to recognize a
  driver declaration, and `node/` may not import `simulation/`. A
  marker base class in `solid_node/node/qualified.py`, subclassed by
  `simulation.Driver`, places that dependency explicitly rather than
  registering a hook (the pattern D9 rejects). The node layer reads
  only `default` off a declaration; every driver semantic stays in
  `simulation/`.
- **Web-snapshot producer publishes an empty driver table.**
  `viewers/browser.py` photographs ONE instant: the web-snapshot
  capability requires the model "at the requested animation time", so
  it serializes the node exactly as the caller keyframed and bound it
  and its document references no driver id. Publishing a non-empty
  table there would make the shipped viewer refuse a picture it can
  render correctly. The export manifest and the normal-build
  `viewer.json` — the two documents the export delta names — do
  serialize in symbolic mode with the full table.
- **Ambiguous bare bind rolls back rather than pre-checking.**
  Ambiguity is only knowable from the linked tree, and reaching the
  tree means rendering, which a cold state-consuming assembly cannot
  survive without the entries being bound first. So the walk binds,
  records what it can restore, and on collision restores every touched
  node's snapshot and re-renders before raising — the ratified "neither
  instance's state changes" outcome, reached by rollback.
- **Widget bundle not rebuilt.** `solid_node/viewers/widget/dist` and
  `node_modules` are symlinks into the primary `solid-node` checkout
  in this bench, so `npm run build` would write outside the worktree.
  The TypeScript source and its vitest suite carry the version gate;
  the shipped bundle is regenerated by the packaging step.
