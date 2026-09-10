## 1. Red first: the memo

- [x] 1.1 In `tests/test_intersection_memo.py`, extend `MemoTestCase` so a
  test can fix the run's placement quantum: set a `ComparisonPolicy` in
  `setUp` (default quantum unless the test says otherwise), reset it with
  `set_comparison_policy(None)` in `tearDown` beside the existing cache
  reset. Keep the module docstring's account of the finding and add the
  wall-clock-02 measurement and its `workflow/warts.md` citation to it.
- [x] 1.2 A pair carried together through a parent is served from the memo:
  compare two `FakeNode`s, then place BOTH by the same rigid transform
  composed so the recomputed relative matrix differs from the first by
  ~1e-13 (compose the parent's rotation into each child's chain in a
  different order, the shape the finding describes — assert first that the
  two relative matrices are NOT bytewise equal, so the test is proving the
  new behaviour and not a coincidence), compare again, assert the verdict is
  served and no boolean ran. RED on the current tree.
- [x] 1.3 A pair displaced by more than the quantum is recomputed: same pair,
  one node translated by 10× the quantum, assert the boolean runs.
- [x] 1.4 `--placement-quantum 0` restores the exact key: the 1.2 scenario
  under a policy with quantum `0` recomputes.
- [x] 1.5 Signed zero does not split a cell: two relative matrices whose
  corresponding entries are `-0.0` and `0.0` (and equal elsewhere) are one
  key. Assert directly against `_verdict_key`, since the point is the key's
  construction — this is the test that fails if the implementation rounds
  floats instead of taking integer cells.
- [x] 1.6 The exact kernel quantises too: the 1.2 scenario with two exact
  nodes under an exact policy, asserting no OCCT boolean runs. Reuse the
  exact fixtures of `tests/test_exact_geometry.py`.
- [x] 1.7 A non-finite relative matrix yields no key: `_verdict_key` with a
  singular matrix returns `None` and the comparison is computed.
- [x] 1.8 Two quanta in one process never cross-serve: build a key at
  quantum `q`, another at `2q` from a different relative placement chosen so
  the integer cells coincide, and assert the keys differ.
- [x] 1.9 The placed geometry is not quantised. On a memo HIT nothing is
  placed at all, so the scenario is about the comparisons that DO run:
  compare an exact pair, clear `test_module._verdict_cache` (the reset
  `MemoTestCase.setUp` already uses), then compare again at a relative
  placement a fraction of a quantum away, and assert
  `solid_node.exact._placement_cache` now holds TWO placement keys for that
  shape identity whose matrix bytes DIFFER — each comparison that ran was
  handed geometry placed by its own exact matrix, not by a quantised one.
  Keeps §5 of design.md honest.
- [x] 1.10 Keep every existing scenario in the file green as written,
  flush contact included, now under the default quantum.

## 2. Red first: the option

- [x] 2.1 In `tests/test_manager_test.py`, `ComparisonKernelSelectionTest`:
  widen every policy EQUALITY assertion from a 2-tuple to a 3-tuple carrying
  the default quantum — a 2-tuple never equals a 3-tuple, and no namedtuple
  default can make it (design.md §6). These are the assertions of the form
  `self.assertEqual(policy, ('exact', 0.0))`.
- [x] 2.2 The seven POSITIONAL two-argument constructions of
  `ComparisonPolicy` keep working and mean "at the default quantum" —
  `solid_node/test.py:140` and `:153`, `solid_node/manager/test.py:281`,
  `tests/test_exact_geometry.py:560` and `:731`,
  `tests/test_tessellation_precision.py:489`,
  `tests/test_manager_test.py:698`. Assert directly that
  `ComparisonPolicy('exact', 0.0).placement_quantum` is the default, and run
  those three test modules; none of the seven sites is edited to pass a
  quantum. RED on a naive three-mandatory-field implementation
  (`TypeError`).
- [x] 2.3 `--placement-quantum` parses into `args.placement_quantum`, and is
  `None` when absent; it is NOT part of the `--exact`/`--faceted` mutually
  exclusive group.
- [x] 2.4 Resolution: the flag beats `SOLID_TEST_PLACEMENT_QUANTUM` beats the
  default; `0` resolves to `0.0`; the exact kernel ACCEPTS a quantum where it
  refuses an epsilon; `SOLID_TEST_PLACEMENT_QUANTUM` is read under both
  kernels.
- [x] 2.5 Errors: a negative flag value and a negative environment value each
  raise naming the flag or the variable; a non-numeric environment value
  raises naming `SOLID_TEST_PLACEMENT_QUANTUM` and saying it is a length in
  mm.
- [x] 2.6 The summary line: unchanged at the default quantum (assert the
  exact string), and naming the quantum at any other, with the prefix
  verbatim and beside the faceted label and epsilon when the run is faceted.

## 3. Implementation

- [x] 3.1 `solid_node/test.py`: add `DEFAULT_PLACEMENT_QUANTUM = 1e-9` and
  widen `ComparisonPolicy` to
  `'kernel volume_epsilon placement_quantum'` **declared with
  `defaults=(DEFAULT_PLACEMENT_QUANTUM,)`**, so a two-argument construction
  means "at the default quantum" (design.md §6). Update the module comment
  above it so it states what the quantum is and is not (a judgement about
  float noise, not about material).
- [x] 3.2 `resolve_comparison_policy`: resolve and validate the quantum
  BEFORE the kernel branch, so both the exact and the faceted return path
  carry it; the error messages name the flag or the variable, in the shape
  the epsilon's already use.
- [x] 3.3 `_verdict_key`: refuse a non-finite relative matrix with `None`;
  with `q > 0` key on `np.rint(relative / q).astype(np.int64).tobytes()`;
  with `q == 0` key on `relative.tobytes()`; carry `q` in the key tuple.
  Rewrite the docstring to say what the key now identifies and why a
  quantised hit cannot be a wrong verdict (design.md §2, in short).
- [x] 3.4 Confirm by reading — and note in the commit message — that
  `_record_key`, `_memoized`, `_engine_intersection_stats` and
  `_placed_intersection` need no edit, and that
  `solid_node/exact.py`'s `placed_shape`, `_placement_cache`, `_bounds_cache`
  and `test.py`'s `_world_bounds`/`_boxes_disjoint` are untouched.
- [x] 3.5 `solid_node/manager/test.py`: add `--placement-quantum MM`
  (`type=float`, `default=None`, outside the kernel group), pass it to
  `resolve_comparison_policy`, and extend the summary suffix in `report()`
  per design.md §4 — including the `ComparisonPolicy` fallback default.
  Add no pre-build line.
- [x] 3.6 Run `tests/test_intersection_memo.py`, `tests/test_manager_test.py`,
  `tests/test_exact_geometry.py`, `tests/test_broad_phase_culling.py` and
  `tests/test_meta.py` green; then the whole suite.

## 4. Documentation and the decision record

- [x] 4.1 `docs/adrs/TEST-FRAMEWORK/ADR-090-the-placement-quantum-is-a-property-of-the-test-run.md`,
  written from the outline at the end of design.md, with the numbers from
  task 5 in its Consequences. Status **Accepted**, **Amends** ADR-070,
  related to ADR-073/029/025.
- [x] 4.2 `docs/adrs/README.md`: add the row in the TEST-FRAMEWORK section in
  chronological order — `**Accepted**, amends 070` — and add "amended by
  090" to ADR-070's row.
- [x] 4.3 `docs/architecture.md`: rewrite the memo paragraph (the one reading
  "The identity of an intersection question is `(both geometry identities,
  evaluation path, exact bytes of inv(M1) @ M2)`" and "The key carries no
  tolerance and no rounding") so it describes the quantised key, the run's
  quantum, and the separation from `volume_epsilon`. Leave the sentence
  about the exact placement LRU keying on exact matrix bytes with no
  rounding exactly as it is — it is still true and now load-bearing.
- [x] 4.4 `docs/testing.rst`: a subsection beside the comparison-kernel one
  covering the quantum, per the user-documentation delta.
- [x] 4.5 `docs/cli.rst`: `--placement-quantum MM` in the `solid test`
  synopsis and option list, and `SOLID_TEST_PLACEMENT_QUANTUM` in the
  environment section.
- [x] 4.6 `docs/changelog.rst` "Unreleased".
- [x] 4.7 `workflow/warts.md`: mark the first wall-clock-02 finding as fixed
  by this cycle, with the measured before/after, leaving the other findings
  as they stand.

## 5. Validation in the originating project

- [x] 5.1 From `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`,
  run ONE sweep test of `wall_clock_02` — `test_movement_runs_free_through_a_swing`,
  `@testing_steps(48)` — under the exact kernel, before and after the
  change, counting booleans and memo hits. The project selects models by
  name (`[tool.solid-node.models] wall_clock_02 = ...`), so the reference is
  `wall_clock_02`. `solid test` has no single-test selector, so drive the
  runner and instrument it in one script, with the workspace venv and this
  worktree on `PYTHONPATH`. The runner class is
  `solid_node.manager.test.Test` (there is no `Runner`); its
  `run_test(self, klass, name, method, node)` return value is discarded by
  `run_class_tests` (`solid_node/manager/test.py:306`), so a filter may
  simply return `None` — note that `num_tests` is incremented by the caller
  before the filter, so the summary counts the skipped tests and only the
  target actually runs.

  ```
  cd /home/asa/devel/libresolid-studio/projects/3DPrintedClocks
  PYTHONPATH=/home/asa/devel/libresolid-studio/solid-node/WTs/exact-negative-shortcuts \
  /home/asa/devel/libresolid-studio/.venv/bin/python - <<'PY'
  import sys
  import solid_node.test as t
  from solid_node.manager.test import Test

  TARGET = 'test_movement_runs_free_through_a_swing'
  run_test = Test.run_test
  Test.run_test = (lambda self, klass, name, method, node:
                   run_test(self, klass, name, method, node)
                   if name == TARGET else None)

  booleans = [0]
  intersect = t.intersect_shapes
  def counted(*args, **kwargs):
      booleans[0] += 1
      return intersect(*args, **kwargs)
  t.intersect_shapes = counted

  asked = [0]; served = [0]
  memoized = t._memoized
  def counting_memo(key, compute):
      if key is not None:
          asked[0] += 1
          if key in t._verdict_cache:
              served[0] += 1
      return memoized(key, compute)
  t._memoized = counting_memo

  import atexit
  atexit.register(lambda: sys.stderr.write(
      f'\nkeyed asks {asked[0]}, memo hits {served[0]}, '
      f'booleans {booleans[0]}\n'))

  sys.argv = ['solid', 'test', 'wall_clock_02']
  from solid_node.cli import manage
  manage()
  PY
  ```

  Verify the harness first by checking that the "before" run reproduces the
  finding's shape (≈118 candidate pairs and ≈5 hits per instant); if the
  monkeypatch points do not hold on the tree as implemented, adjust them and
  say so in the evidence.
- [x] 5.2 Repeat 5.1 with `--placement-quantum 0` appended to `sys.argv`,
  which must reproduce the "before" numbers on the changed tree — the check
  that the win comes from the quantum and nothing else.
- [x] 5.3 Write `openspec/changes/quantise-verdict-memo/evidence.md`: the
  three runs (before, after, after with quantum 0), keyed asks, memo hits,
  booleans and wall time each, the per-instant arithmetic, and one honest
  sentence on how the measured win compares to the ~25 % the finding
  predicted. Record the number whatever it is; do not raise the quantum to
  chase a forecast (ADR-070's consequence).
- [x] 5.4 Confirm the test's verdicts are identical before and after — same
  passes, same failures, same messages — and say so in `evidence.md`.
  Nothing is committed in the project repository by this cycle.

## 6. Close the cycle

- [x] 6.1 `openspec validate quantise-verdict-memo --strict` passes.
- [x] 6.2 Sync the two modified baseline specs and archive the change, per
  the shop's framework-change skill.
