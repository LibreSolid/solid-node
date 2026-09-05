## 1. The run policy and its resolution

- [ ] 1.1 Red: in `tests/test_manager_test.py`, assert that `--exact` and
      `--faceted` are mutually exclusive, that `--faceted` without an
      epsilon resolves to `('faceted', 0.0)`, that `SOLID_TEST_KERNEL=faceted`
      in the environment resolves the same, that `--exact` beats the
      environment, that `SOLID_TEST_KERNEL=fast` fails naming the variable
      and both values, that a negative epsilon fails, and that
      `--volume-epsilon` with an exact run fails before any node is built,
      saying the exact kernel has nothing to absorb.
- [ ] 1.2 Red: assert that `solid_node.test` resolves the policy from the
      environment at first use when the runner has not set it, and that the
      environment's epsilon is not read under the exact kernel.
- [ ] 1.3 Add the comparison policy to `solid_node/test.py`: a named tuple
      `(kernel, volume_epsilon)`, a resolver over explicit values and the
      environment with the errors above, a setter the runner calls, and a
      reader that resolves lazily. Add the flags to
      `solid_node/manager/test.py` and set the policy in `handle()` before
      the first build. Turn 1.1–1.2 green.

## 2. Routing every question through the policy

- [ ] 2.1 Red: in `tests/test_exact_geometry.py`, assert that under the
      faceted policy `_intersection_stats` on two exact nodes returns a
      faceted verdict (`exact` false) and never calls either `shape()`; that
      `assertNoDisconnectedSolids` counts an exact solid's bodies from its
      STL; that `assertJoined` on two exact features unions meshes and fuses
      nothing; and that `assertNoSolidInterference` on an all-exact assembly
      reads no shape and settles every candidate pair on Manifolds.
- [ ] 2.2 Red: assert the run's epsilon: a faceted verdict of 0.2 mm³ under
      an epsilon of 0.5 reads empty with zero volume, a verdict of 12 mm³
      keeps its volume, the epsilon composes with a perturbation assertion's
      `volume_epsilon` without the ignored-epsilon warning, and the verdict
      cache holds the raw verdict (a policy change re-reads the cache
      correctly).
- [ ] 2.3 Replace the five `getattr(node, 'exact', False)` routing reads in
      `solid_node/test.py` (`_solid_geometry`, `_intersection_stats`,
      `assertNoDisconnectedSolids`, `assertJoined`, and the record shape
      `_placed_intersection` consumes) with one predicate over the policy;
      apply the epsilon in `_intersection_stats` and `_placed_intersection`
      after the memo read. Turn 2.1–2.2 green, with every existing test in
      the file still green under the default policy.

## 3. The run says what it is

- [ ] 3.1 Red: in `tests/test_meta.py`, run `exact_tight_fit` under
      `--faceted`: its zero-clearance round fit is reported as interference
      with a volume, the summary line carries the faceted suffix, and a line
      before the build names the kernel and epsilon; run it again under
      `--faceted --volume-epsilon` large enough and it passes; run it under
      the default and the output has no kernel line and the unchanged
      summary. Run an exact fixture whose parts clear each other under
      `SOLID_TEST_KERNEL=faceted` in the environment and it passes labelled.
- [ ] 3.2 Red: in `tests/test_lazy_test_framework.py`, a faceted `solid test`
      of a current-built exact fixture imports no `cadquery` through the test
      framework after the build, using the import probe on the test phase.
- [ ] 3.3 Print the announcement and the summary suffix in
      `solid_node/manager/test.py`. Turn 3.1–3.2 green.

## 4. Documentation and scaffold

- [ ] 4.1 `docs/testing.rst`: a section on the two kernels — what each
      decides, how a developer selects faceted for a checkout through `.env`,
      what the epsilon absorbs and that it exists only faceted, that a faceted
      run labels itself and that CI and release runs are exact. Cross-link
      from the assembly-integrity section, whose epsilon statement is now
      "none of its own".
- [ ] 4.2 `docs/cli.rst`: `--exact`, `--faceted`, `--volume-epsilon` under
      `solid test`, and the two environment variables with their precedence
      beside the other `SOLID_*` settings.
- [ ] 4.3 `docs/changelog.rst`: record the capability under Unreleased, with
      the v8 evidence in one sentence.
- [ ] 4.4 Add `.env` to `solid_node/manager/templates/project/gitignore`, and
      extend `tests/test_manager_new.py` to assert it.

## 5. Validation in the originating project

- [ ] 5.1 Write `SOLID_TEST_KERNEL=faceted` to `projects/v8-engine/.env` and
      run the root suite through the real flag path; record wall time and
      results here, and confirm the only failure is the hand-crank arm
      against the display-stand base, which the exact kernel also reports.
- [ ] 5.2 Run the framework suite; record the result here.
- [ ] 5.3 Run the v8-engine root suite under `--exact` for the disputed test
      only if 5.1 disagrees with the spike; otherwise record the spike's
      exact confirmation (four instants, 12.3 mm³, 0.0 mm clearance).

## 6. Records

- [ ] 6.1 Extract the ADR: the comparison kernel as a property of the test
      run, exact by default, selected per checkout; update the ADR index and
      the test-framework section of `docs/architecture.md`.
- [ ] 6.2 Sync the delta specs into the baseline and archive the change.
