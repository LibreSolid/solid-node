## 1. Regression proof

- [x] 1.1 Add construction regressions for zero, negative, infinite, NaN,
  boolean, and non-numeric `dt`, proving rejection precedes node binding.
- [x] 1.2 Add finite/alignment/sign regressions at `at()`, `every()`,
  `run()`, and instruction-duration boundaries.
- [x] 1.3 Prove a rejected negative run and past schedule do not change the
  tick, state, trajectory, current actions, or cadence accounting.
- [x] 1.4 Prove a current-tick action remains valid and a zero-duration
  instruction updates simulation and node state immediately, including
  visibility to a later action at the same tick.
- [x] 1.5 Run the saved probe before and after the fix, requiring a negative
  `dt` construction refusal and immediate target state for the zero-duration
  instruction.

## 2. Time boundaries

- [x] 2.1 Add one private finite-real seconds validator shared by the
  simulation loop and instruction declarations.
- [x] 2.2 Require positive `dt`, nonnegative run and instruction durations,
  and the existing positive cadence period before effects.
- [x] 2.3 Reject absolute scheduled ticks before `self.tick`, preserving the
  current tick's pre-step firing behavior.
- [x] 2.4 Complete zero-tick ramps immediately and rebind the node once after
  every zero-duration instruction target has settled.
- [x] 2.5 Preserve tick alignment tolerance, integer tick storage, positive
  ramp arithmetic, trajectories, and cadence cost accounting.

## 3. Completion

- [x] 3.1 Run focused simulation, driver, scenario, node-binding, and caller
  coverage plus the saved probe.
- [x] 3.2 Run the complete framework suite and strict OpenSpec validation.
- [x] 3.3 Update the changelog and due-diligence records, mark F11 complete in
  `PROGRESS.md`, and identify the first documentation inconsistency as next.
- [x] 3.4 Synchronize and archive `validate-simulation-time-boundaries`; after
  final evidence, record the ADR and architecture disposition.
- [x] 3.5 Commit the completed implementation as the second F11 commit, then
  require a clean worktree and exactly two-commit ancestry from F10 content
  commit `313902a`.
