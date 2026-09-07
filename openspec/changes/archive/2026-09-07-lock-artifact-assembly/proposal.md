## Why

Due-diligence finding F04 reproduced a CadQuery STL being written while
another process held the project's build lock. Exact and imported adapters can
materialize BREP, STL, and SCAD artifacts during `assemble()`, but the ordinary
builder and test runner currently acquire the lock only afterward.

## What Changes

- Start the ordinary build's project-locked critical section before assembly
  and hold it through artifact and viewer-document publication.
- Put the test runner's render, assembly, and STL build phases inside the same
  project lock while continuing to release it before test cases execute.
- Detect a source change while an ordinary builder waited for the lock before
  assembling or publishing its already loaded model.
- Prove contention with real exact and imported-file adapters, in addition to
  phase-level lock assertions.
- Keep loading, watch-loop waiting, callbacks, and test execution outside the
  critical section.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: make artifact-producing assembly explicit within the
  existing project build mutual-exclusion contract.

## Impact

- `solid_node/core/builder.py`: extend the locked build region to assembly and
  preserve reload/error behavior around that region.
- `solid_node/manager/test.py`: acquire the project lock before render and
  assembly as well as `build_stls()`.
- `tests/test_build_lock.py` and relevant adapter fixtures: cover the phase
  boundary and real CadQuery/STL-import contention.
- `docs/changelog.rst` and the due-diligence records describe F04's resolution.
- Export and snapshot already lock before artifact-producing assembly and keep
  their current behavior.
