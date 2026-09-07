## 1. Regression proof

- [ ] 1.1 Extend lock-participant tests to assert that builder assembly and the
  test runner's keyframe, render, assembly, and STL phases hold the project lock,
  while callbacks, watch waits, and test execution do not.
- [ ] 1.2 Add a process-level cold CadQuery build regression and capture the
  current STL publication while an independent holder owns the project lock.
- [ ] 1.3 Add a process-level cold `StlNode` test-build regression and capture
  imported mesh materialization before the independent holder releases the lock.

## 2. Critical-section correction

- [ ] 2.1 Move builder assembly into the existing uninterrupted project-locked
  region, with before/after source checks and precise watcher startup.
- [ ] 2.2 Defer builder assembly error handling until after lock release so a
  develop reload can wait without blocking other producers.
- [ ] 2.3 Lock the test runner once across keyframing, preliminary render,
  assembly, and `build_stls()`, releasing before project test cases execute.
- [ ] 2.4 Run focused lock, builder-lifecycle, test-manager, exact-adapter, and
  STL-import tests plus the saved F04 contention probe.

## 3. Completion

- [ ] 3.1 Run the full framework suite and strict OpenSpec validation.
- [ ] 3.2 Record the fix and evidence in the changelog and due-diligence report,
  mark F04 complete in `PROGRESS.md`, and identify F05 as next.
- [ ] 3.3 Synchronize and archive `lock-artifact-assembly`; record that no ADR
  is required because the fix enforces the existing project-lock architecture.
- [ ] 3.4 Commit the complete implementation and archived record as the second
  F04 commit, then require a clean worktree and two-commit ancestry from
  `c5d74a6`.
