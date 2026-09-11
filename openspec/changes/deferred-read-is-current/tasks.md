## 0. Before anything

- [x] 0.1 Work only in `solid-node/WTs/deferred-read-current` (branch
  `deferred-read-current`, from main `9a2ff68`), with
  `PYTHONPATH="$PWD"` and the workspace venv
  `/home/asa/devel/libresolid-studio/.venv/bin/python`. Confirmed
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path. No `git` write command anywhere; no write inside
  `projects/`; one heavy process at a time, foreground.

## 1. Red

- [x] 1.1 Reproduce by measurement, not guess: trace `_step_relation`
  and `ResolvedEnd.bound()` over the `FixRoot`/`FixAxis` shape re-posed
  with a `Driver` in place of `FixAxis`'s constant, confirming the
  driven end lags the source by one enumeration and that, at the moment
  the ROOT's own attempt reads the source, its `_enum_marker` names the
  PREVIOUS (closed) enumeration, not the current one.
- [x] 1.2 Add `RFAxis`/`RFRoot` (a `Driver`-fed variant of
  `FixAxis`/`FixRoot`, so a re-pose actually changes the source) and
  `TreeFixpointTest::test_a_deferred_relation_reads_the_source_s_current_value`
  to `tests/test_couplings.py`: `set_state` four times with different
  driver values, asserting after EACH that the driven end equals the
  law applied to the source's CURRENT value. Confirm it fails at the
  base with the exact lagged numbers, and record the red text in
  `evidence.md`.

## 2. Fix

- [x] 2.1 Measure why the naive fix (defer whenever `_enum_marker` is
  not the current enumeration) is wrong: it must not break
  `SymbolicFaceTest::test_a_derived_chain_publishes_the_driver_it_came_from`
  (the serializer's node-by-node `render()`, each opening its own
  enumeration over a narrower subtree once its parent's has already
  closed) or `FanOutTest::test_symbolic_values_pass_through_a_broadcast`
  (a coordinate bound before the first `render()` ever opened one).
  Record both failures and their cause in `evidence.md` before writing
  the real fix.
- [x] 2.2 Add `BoundPort._bound_by = None` (`solid_node/motion/ports.py`),
  stamped by `phase.note_bound` alongside its existing `phase.bound`
  bookkeeping (`solid_node/node/phase.py`) — same guard, same call
  site.
- [x] 2.3 Add `_is_descendant_or_self` and rewrite `ResolvedEnd.bound()`
  in `solid_node/motion/couplings.py`: a value fresh for the current
  enumeration is bound; otherwise it is bound unless some assembly's own
  attempt is currently running AND the value's last binder is that
  assembly or one of its own descendants, in which case it defers.
- [x] 2.4 Confirm 1.2 is green, and that both tests named in 2.1 stay
  green.

## 3. Verify

- [x] 3.1 Full suite `python -m pytest -x -q` from the worktree; record
  the exact counts in `evidence.md` against the base (2199 passed, 16
  skipped).
- [x] 3.2 Construct and run a second, independently-shaped regression
  (two separate descendant subtrees — the source two levels down one
  child, the driven end in a sibling subtree with no relation of its
  own, matching OpenTorque's `reducer.planet_1.orbit.drives(
  output_stack.planet_carrier_b.turn)`) re-posed four times, confirming
  the fix generalizes past the single-chain shape the red test exercises.
  Record it in `evidence.md`.
- [x] 3.3 Run openflexure-microscope's own
  `simulation/openspec/changes/restore-the-root-sentence/evidence/repro_stale.py`
  against this worktree (`PYTHONPATH=.:<worktree>` from the project
  root, read-only) and record the four corrected lines in `evidence.md`.
- [x] 3.4 Capture openflexure-microscope's poses on this worktree with
  `docs/motion-general-refactor/capture_poses.py` and compare against
  its own `before2` reference capture; record the max deviation (must be
  `0.000e+00`, against `1.793e-04` at `all@0.63`/`z_motor@1.0` on main).

## 4. Record

- [x] 4.1 `specs/couplings/spec.md` delta: one scenario ADDED under the
  MODIFIED requirement "Relations are solved from the bound side, at
  the end of the owning simulate phase", every existing scenario
  heading unchanged. `openspec validate deferred-read-is-current
  --strict` passes.
- [x] 4.2 `docs/changelog.rst`: one Unreleased line under Fixed.
- [x] 4.3 `workflow/warts.md`: one entry naming the openflexure sighting
  and the measured cause.
- [x] 4.4 Do NOT archive this change.
