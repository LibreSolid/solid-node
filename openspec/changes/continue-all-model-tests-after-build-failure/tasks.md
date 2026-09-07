## 1. Regression proof

- [ ] 1.1 Add focused all-model regressions for construction/load, render,
  assembly, and artifact-generation failures, requiring each to count once.
- [ ] 1.2 Prove a non-failfast run executes a later model's tests, prints one
  aggregate report, and exits 1 after an earlier model fails to prepare.
- [ ] 1.3 Prove `--failfast` records the first preparation failure, skips the
  later model, still prints the aggregate report, and exits 1.
- [ ] 1.4 Run the saved real CLI probe before and after the fix, requiring
  `second_ran: true` after implementation while preserving exit status 1.

## 2. Model-scoped continuation

- [ ] 2.1 Introduce one model-failure accounting helper shared by unresolved
  references and failures during model preparation.
- [ ] 2.2 Place the all-model preparation boundary around load/construction,
  keyframe binding, render, assembly, and artifact generation without
  catching interpreter-control exceptions.
- [ ] 2.3 Continue with a clean next selection without `--failfast`; otherwise
  raise the existing `StopTestRun` signal after accounting.
- [ ] 2.4 Preserve single-model diagnostics/control flow and ordinary
  test-method accounting.

## 3. Completion

- [ ] 3.1 Run focused manager, named-model, CLI, loader, and build coverage,
  then the saved probe.
- [ ] 3.2 Run the complete framework suite and strict OpenSpec validation.
- [ ] 3.3 Update the changelog and due-diligence records, mark F09 complete in
  `PROGRESS.md`, and identify F10 as next.
- [ ] 3.4 Synchronize and archive
  `continue-all-model-tests-after-build-failure`; record that ADR-073 already
  decides the required continuation behavior, so no new ADR is needed.
- [ ] 3.5 Commit the completed implementation as the second F09 commit, then
  require a clean worktree and exactly two-commit ancestry from F08 content
  commit `f254d26`.
