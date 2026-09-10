# Evidence: broad-phase-indexing-frame

Measured from `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`,
model `wall_clock_02`, driving `solid_node.manager.test.Test` directly
(the same harness shape as the archived `quantise-verdict-memo` cycle's
task 5.1, adapted to count `_bounds_candidates` output and to introspect
the frame chooser) with the workspace venv and this worktree on
`PYTHONPATH`. The baseline is this branch's base, `4f23dff` — the tree
AFTER `quantise-verdict-memo`, whose "after" row (2526 booleans,
533.39 s) is what task 5.4 compares against, not the pre-quantum numbers.

## Task 5.1: candidate-pair count at one instant, before and after

Counted by monkeypatching `solid_node.test._bounds_candidates` to record
`len(list(...))` on its first call and exit immediately (`os._exit(0)`)
so exactly one instant's count is captured, filtering the runner to
`test_movement_runs_free_through_a_swing` as the archived cycle's
harness does. Verified against the finding's own shape before trusting
the numbers: the "before" run (unmodified tree, no
`solid_node/test.py` edits at all yet) gave 116 pairs at `facing=45` and
67 at `facing=0` — close to the finding's own ~118/~69 (the finding's
numbers were an approximate per-instant average; 116/67 is this
harness's exact first-instant count, and both runs used the SAME
first-instant selection). No monkeypatch adjustment was needed.

| | `facing=45` (declared default) | `--set facing=0` |
|---|---:|---:|
| **Before** | 116 | 67 |
| **After** | 67 | 67 |

`facing=45` after the change matches `facing=0` exactly, both before and
after — the chosen frame recovers the un-turned candidate count exactly
at this instant, not merely approximately.

## Task 5.2/5.3: the chooser's own numbers, at the same instant

Recorded by wrapping `solid_node.test._placed_assembly_solids` to
capture the real placement records for one instant (facing=45, first
instant of the swing sweep), then reading each solid's own
`_diagonal(local_bounds)`, `_ranked_solid_candidates(records)`, and
scoring every ranked candidate exactly as `_indexing_frame_boxes` does.

- 53 topmost rigid solids total (matches the finding).
- Top 6 by local-bounds diagonal:

  | Solid | Diagonal (mm) |
  |---|---:|
  | `standoffs` | 442.4546 |
  | `plates` | 421.5457 |
  | `top_rod` | 236.7287 |
  | `bottom_rod` | 233.9334 |
  | `ring` | 198.1611 |
  | `wheel` | 177.3020 |

- With `K = _INDEXING_FRAME_CANDIDATES = 3`, the candidates are
  `standoffs`, `plates`, `top_rod` (indices `[1, 0, 37]`) — **the fused
  frame the finding names ("both plates and their pillars") IS among the
  candidates**, in fact the top two, so task 5.3's stop-and-report
  branch does not apply. Contrary to design.md's stated risk (that the
  longest-diagonal solids might be the pendulum's suspension or the
  weight's line instead, since a diagonal is weakest for long thin
  parts), the actual top two by diagonal are exactly the frame-like
  solids the finding is about. `top_rod`/`bottom_rod` (the pendulum's
  suspension) and `ring` (the pendulum ring) rank immediately below
  them, not above.
- Scores (total box volume, world included):

  | Candidate | Score (mm³) |
  |---|---:|
  | world | 1.763118e+07 |
  | `standoffs` (index 1) | 5.754013e+06 |
  | `plates` (index 0) | 5.754013e+06 |
  | `top_rod` (index 37) | 6.363712e+06 |

  `standoffs` and `plates` score identically at this precision — they
  are rigidly carried together with no relative rotation between them
  (both children of the root receiving the same `facing` turn and
  nothing else distinguishing their orientation), so undoing either
  one's rotation undoes the same shared turn for the whole assembly.
- **Chosen frame: `standoffs`** (the earlier of the two tied candidates
  in ranked order — `standoffs` is rank 1 by diagonal, `plates` rank 2,
  and the tie resolves to the earlier one per the tie rule). Confirmed
  independently: `_indexing_frame_boxes(records)` does NOT reproduce the
  world boxes bit for bit for this instant (a genuine non-world frame
  was chosen, not a fallback).
- The chosen frame's score (5.754013e+06) is 3.06x smaller than world's
  (1.763118e+07) — consistent with the ~3x fewer candidate pairs
  measured in task 5.1, and with the finding's own `facing=0` control
  ("three times fewer").

## Task 5.4/5.5: the swing sweep, end to end, after

`test_movement_runs_free_through_a_swing` (`@testing_steps(48)`), exact
kernel, default placement quantum, at the declared default `facing=45`,
driven exactly as the archived `quantise-verdict-memo` cycle's task 5.1
harness (counting keyed memo asks, memo hits and `intersect_shapes`
calls).

| Run | Keyed asks | Memo hits | Booleans | Wall time |
|---|---:|---:|---:|---:|
| Baseline (`4f23dff`, after `quantise-verdict-memo`) | 5643 | 3117 | 2526 | 533.39 s |
| **After `broad-phase-indexing-frame`** | 3210 | 2121 | 1089 | 265.99 s |

Booleans fell 56.9% (2526 → 1089, 1437 fewer). Wall time fell 50.1%
(533.39 s → 265.99 s). Keyed asks also fell (5643 → 3210): fewer
candidate pairs are emitted per instant, so fewer relative placements
are ever asked about at all, not only fewer that miss the memo. Fewer
candidates means fewer memo ASKS as well as fewer booleans, so the
hit/ask ratio between this row and the baseline is not comparable for
that reason (per design.md's own note); only the boolean count and the
wall time are, and both moved by roughly the same 2x factor (2.32x
fewer booleans, 2.01x faster wall time).

## Task 5.5: verdict identity

Both runs reported `Ran 17 tests in <time> seconds: 1 passed, 0 failed`
for `wall_clock_02` — the baseline's own recorded line
(`quantise-verdict-memo`'s ADR-090, "after" row) and this cycle's
`Ran 17 tests in 265.99 seconds: 1 passed, 0 failed`. The same single
test selected (the `run_test` filter), the same pass, no failure
message in either run. Nothing about the frame choice is observable in
the test's own outcome, only in how much work it costs to reach it.

## Honest comparison with the `facing=0` forecast

The original finding predicted "three times fewer" candidate pairs from
the `facing=0` control (69 vs ~118). Measured here: 116 → 67 at the
first instant (1.73x fewer), and the chosen frame's own score is 3.06x
smaller than world's — both close to but somewhat under the finding's
3x estimate at the single-instant level. Over the full 48-instant swing
sweep the win compounds: 2.32x fewer booleans and 2.01x faster wall
time, ABOVE the finding's own per-instant estimate once the whole sweep
(escapement geometry changing every instant, not just the pendulum's
overall swing) is accounted for. The number is recorded as measured, not
tuned or argued toward the forecast.

Nothing was committed in the project repository by this cycle; only its
ignored `_build/` directory was written by these runs.
