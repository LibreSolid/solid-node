## Why

Due-diligence finding F09 reproduced `solid test --all` aborting when the
first declared model raises while rendering. The second model never runs and
the command prints no aggregate report, even though the accepted CLI contract
and ADR-073 require an all-model test run to continue unless `--failfast` is
given.

## What Changes

- Treat each declared model's load, construction, render, assembly, and
  artifact-generation work as one reportable model result during
  `solid test --all`.
- Count a failure in any of those stages once, identify the declared model in
  the diagnostic, and continue with the next model when `--failfast` is not
  set.
- Make `--failfast` stop immediately after recording that model failure while
  retaining the single aggregate report and nonzero exit status.
- Preserve the existing single-model test path and ordinary test-method
  failure accounting.
- Add focused stage regressions plus a real CLI reproduction proving a later
  model's tests run after an earlier model fails to build.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `cli`: make the existing all-model continuation requirement executable for
  failures that occur after reference resolution.

## Impact

- `solid_node/manager/test.py`: add a model-scoped failure boundary around
  preparation of each selection and share its accounting with unresolved
  model failures.
- `tests/test_named_models.py` and/or `tests/test_manager_test.py`: cover
  construction, render, assembly, and artifact-generation failures with and
  without `--failfast`.
- `docs/due-dilligence/probe_additional.py`: the existing two-model probe
  becomes caller evidence that the second model runs and the command still
  exits nonzero.
- `docs/changelog.rst` and due-diligence records will describe the fix.
- No node API, test assertion semantics, artifact schema, build-directory
  layout, dependency, or viewer behavior changes.
