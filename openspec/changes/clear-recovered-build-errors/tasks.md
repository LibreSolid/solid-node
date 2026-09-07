## 1. Regression proof

- [ ] 1.1 Add publication regressions proving a byte-identical successful
  snapshot clears a prior error, returns a changed-state result, and leaves the
  existing viewer document bytes and mtime untouched.
- [ ] 1.2 Add lifecycle coverage proving recovery invokes the callback after
  the build lock is released, while an unchanged build with no prior error
  remains silent.
- [ ] 1.3 Add a failure-ordering regression proving an exception during viewer
  document construction leaves the prior error visible.
- [ ] 1.4 Run the saved stale-error CLI probe before and after the fix, requiring
  the successful rebuild to remove `errors.json` and make `solid models --json`
  report `published`.

## 2. Recovery publication state

- [ ] 2.1 Make error removal report whether prior failure state existed, without
  changing the `errors.json` format or introducing a second status channel.
- [ ] 2.2 Clear the prior error only after complete viewer-document construction
  and before the byte-identical early return.
- [ ] 2.3 Return an observable publication-state change for recovery, preserving
  callback timing outside the project lock and the true no-op path.
- [ ] 2.4 Run focused builder lifecycle, publication, model-status, and CLI
  tests plus the saved probe.

## 3. Completion

- [ ] 3.1 Run the complete framework suite and strict OpenSpec validation.
- [ ] 3.2 Update the changelog and due-diligence records, mark F07 complete in
  `PROGRESS.md`, and identify F08 as next.
- [ ] 3.3 Synchronize and archive `clear-recovered-build-errors`; record the ADR
  disposition against the existing publication and callback decisions.
- [ ] 3.4 Commit the completed implementation as the second F07 commit, then
  require a clean worktree and exactly two-commit ancestry from F06 content
  commit `19dc267`.
