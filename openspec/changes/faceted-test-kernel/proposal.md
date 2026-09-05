## Why

Since exact boundary-representation geometry arrived, a project's `solid test`
run is decided almost entirely by the OCCT kernel, and on a swept machine that
is the wrong price for a development loop: the v8-engine suite takes about
28 minutes, and `spike/interference/FINDINGS.md` (finding 6, measured
2026-09-05) shows why — one valve spring against its valve costs about 430 ms
through the exact kernel and about 14 ms through `manifold3d` on the part's
own mesh, with the same verdict at every instant, and a flexible part's
comparisons are uncacheable by construction. The `fast-test-feedback` cycle
removed every repeated computation and left this finding as evidence for a
product decision: the kernel a run compares on is a property of the run, and
a developer must be able to choose the cheap one without editing the model or
the tests, while CI keeps the exact one.

## What Changes

- `solid test` gains a run-level **comparison kernel**: `exact` (the default,
  today's behaviour, unchanged) or `faceted`. Under `--faceted` every
  intersection, containment, connectivity and weld question is answered on
  the parts' meshes — the faceted path that already exists for non-exact
  parts — including for parts that carry exact geometry. Nothing about the
  model, the build, or the test source changes between the two runs.
- The kernel is selected by mutually exclusive flags `--exact` / `--faceted`,
  else by the `SOLID_TEST_KERNEL` environment variable (loaded from the
  project's `.env` like the other `SOLID_*` settings), else exact. A
  developer sets `SOLID_TEST_KERNEL=faceted` once in the ignored `.env` of a
  checkout; a CI runner that has no such file runs exact without
  configuration.
- A faceted run carries one **volume epsilon** (mm³): `--volume-epsilon`,
  else `SOLID_TEST_VOLUME_EPSILON`, else 0.0. Every engine-native
  intersection verdict at or below it reads as empty with zero volume, so the
  tessellation noise meshes produce at contacts the exact kernel calls exactly
  empty does not fail a faceted run. Giving an epsilon to an exact run is an
  error: the exact kernel has nothing for it to absorb.
- A faceted run says so, at its start and on its summary line, so a green
  fast run is never mistaken for an exact one. The exact run's output is
  byte-for-byte what it is today.
- `assertNoSolidInterference` keeps its rule of no epsilon of its own; under
  a faceted run it inherits the run's epsilon like every other volume
  question. The perturbation assertions' `volume_epsilon` and its
  ignored-epsilon warning are unchanged in meaning: under a faceted run no
  comparison routes exact, so the epsilon is live and no warning fires.
- No verdict on the exact kernel changes. No new dependency. No node API
  change. **Not BREAKING**: the default run is today's run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: the "Accelerated intersection evaluation" helper selects
  its path from the compared nodes AND the run's kernel; a new "Run-level
  comparison kernel" requirement states the selection, the epsilon, and the
  announcement; "Whole-assembly solid interference assertion" and "Solid
  connectivity" route by the same rule; "Test runner lifecycle" gains the
  faceted summary suffix.
- `cli`: the "Test command" requirement gains `--exact`, `--faceted` and
  `--volume-epsilon`, and the `SOLID_TEST_KERNEL` /
  `SOLID_TEST_VOLUME_EPSILON` environment settings.
- `user-documentation`: the testing and CLI pages describe the two kernels
  and how a developer and a CI runner select them.

## Impact

- `solid_node/test.py`: the five sites that route on `node.exact`
  (`_solid_geometry`, `_placed_intersection`, `_intersection_stats`,
  `assertNoDisconnectedSolids`, `assertJoined`) consult one run policy; the
  two engine-native verdict helpers apply the run's epsilon.
- `solid_node/manager/test.py`: the flags, their resolution against the
  environment, the announcement and the summary suffix.
- `docs/testing.rst`, `docs/cli.rst`, `docs/changelog.rst`.
- Tests: `tests/test_manager_test.py`, `tests/test_cli.py`,
  `tests/test_assembly_integrity.py`, `tests/test_meta.py` with a faceted run
  of an exact meta fixture, and `tests/test_lazy_test_framework.py` (a
  faceted run of an exact project never imports the exact stack through the
  test framework).
- Originating project: v8-engine. Its suite is the validation: run faceted,
  every disagreement with the exact run explained, the calibrated epsilon
  recorded.
