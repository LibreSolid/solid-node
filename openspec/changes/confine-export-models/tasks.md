## 1. Regression proof

- [ ] 1.1 Add a real-project CLI regression that exports from a nested working
  directory and prove it fails against the current parent-traversing manifest
  path and escaped copy.
- [ ] 1.2 Add failing coverage for a relative configured build root, a selected
  named-model directory, and a direct-call artifact outside its build directory.
- [ ] 1.3 Add a CLI assertion for the controlled nonzero external-artifact
  diagnostic and prove the requested output remains untouched.

## 2. Export containment

- [ ] 2.1 Resolve each rigid artifact against `get_build_dir(node.src)`, verify
  canonical containment, and emit the unchanged safe `models/`-relative layout.
- [ ] 2.2 Add `ExportModelPathError` and make `solid export` report it without a
  traceback or success message.
- [ ] 2.3 Run the focused export tests and the saved F03 CLI probe; confirm nested
  invocation now copies only beneath the requested output.

## 3. Completion

- [ ] 3.1 Run the full framework suite and strict OpenSpec validation.
- [ ] 3.2 Record the fix and evidence in the changelog and due-diligence report,
  mark F03 complete in `PROGRESS.md`, and identify F04 as next.
- [ ] 3.3 Synchronize and archive `confine-export-models`; record that no ADR is
  required because the fix enforces ADR-020 and ADR-073 without changing the
  architecture.
- [ ] 3.4 Commit the complete implementation and archived record as the second
  F03 commit, then require a clean worktree and two-commit ancestry from
  `4bf9b69421b7114809af75fe663441d115407631`.
