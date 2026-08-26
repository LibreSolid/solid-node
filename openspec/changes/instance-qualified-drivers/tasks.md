# Tasks: instance-qualified drivers

Red-first throughout: every behavioral task lands its failing test
before the change that turns it green. `node/` never imports
`simulation/`.

## 1. Qualified identity and the driver token (kinematics)

- [ ] 1.1 Red tests for qualified-id computation: dotted path from
  linked names, bare name at root, loud failure on unlinked and on
  illegal (`<attr>-<index>`) segments, no fallback and no
  sanitization
- [ ] 1.2 Implement the qualified-id walk on linked trees and the
  `DriverToken` (`OpenSCADConstant` subclass stringifying as the id);
  verify tokens ride solid2 arithmetic and `solid_node.math` symbolic
  trig with red tests from the spike's expression shapes (linear,
  port-scaled, degree trig, mixed `$t`, `^`)

## 2. Qualified state binding (kinematics)

- [ ] 2.1 Red tests: sibling instances bind independently via
  qualified entries; consumed path segment strips on descent; `time`
  propagates flat; ambiguous bare bind fails listing colliding ids;
  unambiguous bare bind still works; `clear_state` accepts qualified
  names; existing flat/merge/idempotency scenarios stay green
- [ ] 2.2 Implement qualified `set_state`/`clear_state` delivery and
  make the propagation walk link children before recursing
  (`_rendered_children`), preserving leaf no-op tolerance

## 3. Symbolic serialization mode and document schema v2 (export)

- [ ] 3.1 Red tests: serializing a driver-declaring tree binds every
  declared driver to its token internally (never through
  `set_state`'s numeric door — `_validate_state` untouched), emits
  expressions with qualified ids verbatim even from a
  numerically-snapshotted node, and restores the prior binding after,
  matching the existing symbolic-`$t` producer guarantee
- [ ] 3.2 Red tests for the v2 document: `version: 2`, `drivers`
  table with declared metadata verbatim (`range`
  presentation-only), every referenced id present in the table, empty
  table for driverless trees, `manifest.json`/`viewer.json` parity
- [ ] 3.3 Implement symbolic mode in the serializer and export
  producer; bump the shared schema version; update consumers for the
  version gate (widget/web viewer render empty-table v2 documents
  exactly as v1; a non-empty table fails loudly — evaluation is stage
  3b)
- [ ] 3.4 Red test that the `.scad` path still substitutes bound
  driver values numerically with `$t` live (spike verdict 4 as a
  regression test)

## 4. Qualified simulation layer (simulation)

- [ ] 4.1 Red tests for tree-wide enumeration: qualified ids with
  declaration metadata off a driverless root with declaring
  descendants; loud failure through illegal segments
- [ ] 4.2 Implement the enumeration authority; rekey the `Sim` bank,
  trajectory, and programs by qualified id; construction binds
  defaults tree-wide (red: driverless-root scenario from the spike)
- [ ] 4.3 Red tests then implementation for qualified instructions:
  discovery on any node, `x_axis.Home` ramps only `x_axis.motor`,
  unknown trigger lists known qualified names, target conversion
  unchanged
- [ ] 4.4 Red tests then implementation for the simulation clock:
  each tick binds global `time` to exact `k*dt` seconds; `self.time`
  under a Sim reads it; symbolic `$t` restored after; existing
  whole-tick and deferred-action semantics unchanged

## 5. Build-path defaults (build-pipeline)

- [ ] 5.1 Red test: a driver-declaring project with a bare `__init__`
  builds and tests through the CLI; a driverless project's load path
  performs no binding
- [ ] 5.2 Implement default binding in the loader/manager via the
  enumeration authority; remove the self-bind workaround from the
  `tests/meta_project` fixture and note it in the fixture

## 6. Caller validation and records

- [ ] 6.1 Migrate `spike/expressions/` onto the shipped API: dissolve
  the shims in `symbolic.py` (tokens, qualified bank, linked-walk
  workarounds), rerun `run_spike.py` — all five verdicts must
  revalidate — and add an addendum to
  `spike/expressions/FINDINGS.md`; rerun `spike/axis/scenario.py`
- [ ] 6.2 Full framework suite green (pytest, from the worktree with
  the workspace venv); zero regressions against the 813 baseline
- [ ] 6.3 v8-engine unchanged: `solid test` 33/33 via the worktree
  `PYTHONPATH`
- [ ] 6.4 Update `docs/architecture.md` (qualification, symbolic
  serialization mode, schema v2, build-path defaults resolved) and
  ADR-056 (implementation status; open questions: build-path defaults
  and time-driver unification resolved; stage-3b items remain);
  archive the change and sync baseline specs
