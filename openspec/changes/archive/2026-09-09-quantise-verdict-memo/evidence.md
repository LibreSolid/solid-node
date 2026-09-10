# Evidence: quantise-verdict-memo

Measured from `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`,
model `wall_clock_02`, test `test_movement_runs_free_through_a_swing`
(`@testing_steps(48)`), under the exact kernel, driving
`solid_node.manager.test.Test` directly (per tasks.md task 5.1's harness)
with the workspace venv and this worktree on `PYTHONPATH`. Every other
declared test method in the file is counted by the runner (`num_tests`)
but filtered out before it runs (`run_test` returns `None` for any name
other than the target), so only the 48-instant sweep actually executes;
this is why every run below reports "Ran 17 tests ... 1 passed".

The harness verified against the finding's own shape before any run: the
instrumentation counts a keyed ask each time `_memoized` is called with a
non-`None` key, a hit each time that key is already in `_verdict_cache`
at that point, and a boolean each time `solid_node.test.intersect_shapes`
is actually called (whether reached through the memo or not). No
monkeypatch point needed adjusting.

## Runs

| Run | Tree | `--placement-quantum` | Keyed asks | Memo hits | Booleans | Wall time |
|---|---|---|---:|---:|---:|---:|
| **Before** | unmodified (base `1822221`) | n/a (no such flag) | 5527 | 1823 | 3820 | 779.37 s |
| **After** | this cycle's `_verdict_key` | default (`1e-9` mm) | 5643 | 3117 | 2526 | 533.39 s |
| **After, quantum 0** | this cycle's `_verdict_key` | `0` | 5643 | 1963 | 3680 | 692.68 s |

The quantum-0 run's summary line read
`Ran 17 tests in 692.68 seconds: 1 passed, 0 failed (placement quantum 0 mm)`
— the non-default-quantum announcement (task 2.6/3.5) firing correctly in
a real run, not just under test.

All three runs report `Ran 17 tests in <time> seconds: 1 passed, 0 failed`
— the sweep's own verdict (pass) is identical across all three.

## Per-instant arithmetic

- **Before**: 5527 keyed asks / 48 instants ≈ 115.1 keyed comparisons per
  instant, close to the finding's ≈118 candidate pairs. 1823 hits / 48 ≈
  38.0 per instant — higher than the finding's "only 5 pairs hit", because
  the finding's "5" describes pairs that are freshly asked and then hit on
  every SUBSEQUENT instant (the steady state after instant 1), while this
  count is hits summed over the whole 48-instant run: most of the
  assembly's 118-ish pairs never move relative to each other at all across
  the sweep (only the swinging pendulum, the motion works and the weight
  do), so once the first instant asks and answers them, every following
  instant's byte-identical relative placement already hits — that is
  ADR-070's own steady-state behaviour, not a change this cycle makes.
  3820 booleans / 48 ≈ 79.6 per instant. 779.37 s / 48 ≈ 16.2 s/instant.
- **After**: 5643 keyed asks / 48 ≈ 117.6 per instant — 116 more than
  "before"'s 5527; see the note below. 3117 hits / 48 ≈ 64.9 per
  instant, up from 38.0: the ~30 co-moving pairs the finding named now
  hit from the second instant on instead of missing every time. 2526
  booleans / 48 ≈ 52.6 per instant, down from 79.6. 533.39 s / 48 ≈
  11.1 s/instant, down from 16.2 s.
- **After, quantum 0**: 5643 keyed asks / 48 ≈ 117.6 per instant (same
  count as the default-quantum "after" run, both on the changed tree).
  1963 hits / 48 ≈ 40.9 per instant, close to "before"'s 38.0 — the
  quantum-0 key reproduces the exact-bytes behaviour, so the ~30 co-moving
  pairs miss again. 3680 booleans / 48 ≈ 76.7 per instant, close to
  "before"'s 79.6. 692.68 s / 48 ≈ 14.4 s/instant, close to "before"'s
  16.2 s/instant.

The two changed-tree runs (default quantum and quantum 0) agree with each
other EXACTLY on keyed asks (5643 both) and, within each run, `booleans`
equals `keyed asks − memo hits` exactly (2526 = 5643 − 3117; 3680 =
5643 − 1963): every keyed miss costs one boolean and nothing else does.
"Before" differs: 5527 keyed asks, 1823 hits, so 3704 keyed misses, but
3820 booleans — 116 more booleans than keyed misses, i.e. 116 booleans
`_memoized` ran WITHOUT a key (the `if key is None: return compute()`
path), invisible to `asked`/`hit` counting. This is not the quantum: the
non-finite refusal this cycle adds lives entirely on the CHANGED tree and
can only LOWER a changed-tree run's keyed-ask count by turning a
degenerate comparison's key into `None` — it cannot explain 116 unkeyed
comparisons on the UNMODIFIED "before" tree, which never runs that code
at all.

What the unmodified tree's own code says instead: a comparison is
unkeyed there only when a shape has no cache identity, and
`ExactLeafNode.shape()` (`solid_node/node/exact_leaf.py:55`) returns an
uncached `shape_from_rendered(...)` — no identity — whenever the node's
BREP is not yet up to date at that call, falling back to `cached_shape`
only once it is. 116 is one instant's worth of candidate pairs (5527/48
≈ 115). The reading consistent with the code and with the counts is that
the "before" run was the first run against that build: its first
instant's comparisons ran on shapes not yet marked current (unkeyed,
uncounted, one boolean apiece), and every instant after that — and both
changed-tree runs, which found the build already current from "before"'s
own artifacts on disk — keyed every comparison, which is why the
changed-tree keyed-ask count is 5643 = 5527 + 116. This is offered as
consistent with the code and the measured counts, not as something this
evidence proves independently, and it does not touch the boolean-count
comparison the win above is measured from.

## The predicted win, honestly

The finding (`workflow/warts.md`) estimated "a quarter of every instant"
(~25%) spent on the 30 co-moving pairs that miss on float noise. Measured:
booleans fell 3820 → 2526, a 33.9% reduction (1294 fewer, exactly the
1294-entry rise in memo hits, 1823 → 3117 — every new hit is one fewer
boolean, as ADR-070's own accounting predicts). Wall time fell
779.37 s → 533.39 s, a 31.6% reduction. Both figures are at or somewhat
ABOVE the finding's 25% forecast rather than below it — the opposite
direction from ADR-070's own history, where the forecast was generous by
more than a factor of two. The quantum was not raised to chase a bigger
number; these are the numbers as measured.

## Verdicts identical before and after

All three runs reported `Ran 17 tests in <time> seconds: 1 passed,
0 failed` for `wall_clock_02`'s `test_movement_runs_free_through_a_swing`
— the same single test selected, the same pass, no failure message in any
run. Nothing about `_verdict_key`'s change can be observed in the test's
own outcome, only in how much work it costs to reach it.

Nothing was committed in the project repository by this cycle; only its
ignored `_build/` directory was written by these runs.
