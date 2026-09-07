## 1. Regression proof

- [x] 1.1 Add dispatch regressions proving tracked `.scad`, `.js`, `.stl`, and
  `.step` modifications resolve the builder future while untracked non-Python,
  `__pycache__`, and directory events remain ignored.
- [x] 1.2 Add a real-observer lifecycle regression that modifies a tracked STL
  source and capture the pre-fix builder failing to exit.
- [x] 1.3 Update and run the saved watch-event probe with an explicit precise
  source set, recording the pre-fix extension filter and post-fix matrix.

## 2. Watch classification

- [x] 2.1 Retain normalized paths for every source scheduled after successful
  assembly.
- [x] 2.2 Accept modification events for every precise source regardless of
  extension, and apply the Python/no-bytecode filter only to broad recovery
  events.
- [x] 2.3 Preserve thread-safe future resolution, duplicate-event handling, and
  observer cleanup; keep moved events outside the change.
- [x] 2.4 Run focused builder lifecycle, reload resilience, adapter source-set,
  and watch tests plus the saved probe.

## 3. Completion

- [x] 3.1 Run the complete framework suite and strict OpenSpec validation.
- [x] 3.2 Update the changelog and due-diligence records, mark F06 complete in
  `PROGRESS.md`, and identify F07 as next.
- [x] 3.3 Synchronize and archive `watch-all-tracked-sources`; record the ADR
  disposition against the existing watchdog architecture.
- [x] 3.4 Commit the completed implementation as the second F06 commit, then
  require a clean worktree and exactly two-commit ancestry from F05 content
  commit `e6b92b9`.
