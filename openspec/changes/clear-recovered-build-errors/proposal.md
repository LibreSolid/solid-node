## Why

Due-diligence finding F07 reproduced a successful unchanged rebuild leaving a
prior `errors.json` in place because viewer publication returns early when the
serialized document bytes already match. `solid models` consequently reports
the model as failed after the build itself exited successfully.

## What Changes

- Clear a prior build error after the current model has completed successfully,
  even when its viewer document does not need to be rewritten.
- Keep the prior error intact through load, assembly, rendering, and document
  serialization so an attempted build that still fails cannot advertise
  recovery.
- Treat removal of a prior error as an observable publication-state change:
  development callbacks fire for that recovery, while a fully unchanged
  successful build with no prior error remains a no-op.
- Add focused publication/lifecycle regressions and retain the real CLI probe
  showing `solid models --json` transitions from `failed` to `published`.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: define successful error recovery independently of whether
  the viewer document bytes change.
- `one-shot-build-and-notification`: make the existing successful-build
  callback boundary include recovery that only clears the failure record.
- `printed-pieces`: clarify that the unchanged-build no-notification rule
  applies when no prior failure state also needs to be cleared.

## Impact

- `solid_node/core/builder.py`: order error removal after successful document
  construction but before the unchanged-document return, and report recovery
  as an observable publication-state change.
- Builder lifecycle and publication tests: cover unchanged recovery, retained
  errors on failed document construction, callback behavior, and the existing
  no-error no-op path.
- `docs/due-dilligence/probe_build.py`: the existing stale-error probe becomes
  caller evidence for the corrected `solid models --json` state.
- `docs/changelog.rst` and the due-diligence records will describe the fix.
- No public API, artifact schema, dependency, viewer, or geometry change is
  required.
