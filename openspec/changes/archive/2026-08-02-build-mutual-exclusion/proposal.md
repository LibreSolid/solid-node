## Why

Nothing stops two processes from building the same project at once. `solid
develop`'s watch loop, `solid build`, `solid test` and any number of agents each
render into their own view of the build directory and publish whenever they
finish, so the last publication wins regardless of which source it came from: a
build started against older source and finishing late overwrites a newer model,
and the maker is left looking at a model that does not match the file on disk.
Today the collision is merely wasteful because each publication installs a
complete set atomically; the next cycle replaces set-atomic publication with a
single build directory written one artifact at a time, and at that point two
builders write the same files and interleave, so the same race becomes
corrupting. Mutual exclusion has to land first.

This change is F1 of SPRINT-003 and implements decision D2 of
`docs/product/sprints/PRD.md` in the shop repository.

## What Changes

- Every process that renders artifacts for a project takes an advisory `flock`
  on a lock file held in the project, so exactly one build runs at a time per
  project. Waiting is blocking: a second builder queues rather than failing.
- The lock covers the build only. `solid develop` releases it before waiting for
  the next source change, and `solid test` releases it before running tests, so
  a long test sweep never blocks the maker's next rebuild.
- A dedup rule applies at acquisition: a builder that takes the lock and finds
  the project already built at the current source state does nothing and reports
  the model current, and a builder whose own source was superseded while it
  waited stands down instead of republishing a stale model. Both decisions use
  the existing mtime-equality caching rule, so no new artifact metadata appears.
- The lock is released by the kernel when the holder dies, so an interrupted or
  killed build leaves nothing to reap and no stale-lock recovery path exists to
  get wrong.
- No change to the publication mechanism: the symlink swap of ADR-032 and the
  race-tolerance behaviour it specifies stay exactly as they are. Replacing them
  is F2 (`per-file-build-publication`).

## Capabilities

### New Capabilities

None. This extends the existing build pipeline rather than adding a capability.

### Modified Capabilities

- `build-pipeline`: adds project-wide build mutual exclusion and the
  acquisition-time dedup rule beside the existing per-artifact
  `.stl.lock` concurrent-render guard, and states that the lock is not held
  while a builder waits for a source change.
- `test-framework`: the test runner lifecycle builds under the project build
  lock and releases it before running test methods.
- `one-shot-build-and-notification`: `solid build` rebuilds from the source on
  disk when its builder stands down under the dedup rule, so the one-shot
  command still publishes the current model.

## Impact

- `solid_node/core/builder.py` — the builder acquires and releases the lock
  around the render and publish phase, and applies the dedup rule on
  acquisition.
- `solid_node/manager/test.py` — `build_node` builds under the lock, and the
  lock is released before `run_tests`.
- `solid_node/manager/build.py` — the one-shot loop rebuilds when its builder
  stands down under the dedup rule. `solid_node/manager/develop.py` is
  unchanged; its child builders become lock participants.
- New tests exercising two concurrent builders, a stale builder finishing last,
  and a test run that does not block a rebuild.
- No new dependency: `fcntl.flock` is in the standard library and POSIX. No
  daemon, socket or broker, so ADR-018's lean separation is not regressed.
- The architecture record for this decision is deliberately not filed here. PRD
  section 5 files D1 and D2 as one BUILD record because their correctness is
  joint; it is written in F2 once both halves exist.
