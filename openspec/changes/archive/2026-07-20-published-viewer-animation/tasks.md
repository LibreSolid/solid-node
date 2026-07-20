## 1. Published snapshot contract

- [x] 1.1 Add red-first builder coverage for the published animation cadence
  and its retention after a failed later build.
- [x] 1.2 Serialize the established `fps` and `frames` cadence into staging
  `viewer.json` before atomic publication.

## 2. Verification

- [x] 2.1 Run the focused build, CLI, and snapshot-backed-viewer suites and
  validate the originating Floor/V8 consumer against the completed build.
