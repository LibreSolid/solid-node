## 1. Regression Proof

- [x] 1.1 Add a focused render-job test proving a nonzero subprocess result
  raises, removes its temporary output and lock, and preserves an existing
  target artifact.
- [x] 1.2 Add real OpenSCAD CLI tests for cold and replacement assertion
  failures, including exit status, artifact, viewer snapshot, error record,
  and cleanup observations.
- [x] 1.3 Run the focused tests red against the current implementation and
  retain the failure evidence.

## 2. Render Failure Handling

- [x] 2.1 Make `StlRenderStart.wait()` publish only after a zero subprocess
  status and discard private render files before raising
  `CalledProcessError` on failure.
- [x] 2.2 Add an Unreleased changelog entry and mark F01's resolution state in
  the due-diligence report without altering its original reproduction evidence.

## 3. Validation

- [x] 3.1 Run the focused publication, builder lifecycle, and real CLI render
  failure tests.
- [x] 3.2 Run the complete framework test suite and the saved F01 probe, then
  record the final results in the due-diligence report.
- [x] 3.3 Validate and archive the OpenSpec change, confirming whether the
  implementation introduced any architectural decision requiring an ADR.
