# Evidence: face-box-broad-phase

Measured from `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`,
model `wall_clock_02`, driving `solid_node.manager.test.Test` directly
(the same harness shape as the archived `quantise-verdict-memo` and
`broad-phase-indexing-frame` cycles' evidence, adapted to count
`_faces_disjoint`, `_mutually_outside` and `intersect_shapes` calls) with
the workspace venv and this worktree on `PYTHONPATH`. The baseline is
this branch's base, `93612db` — the tree AFTER `broad-phase-indexing-frame`,
whose "after" row (67 candidate pairs at the first swing-sweep instant,
1089 booleans, 3210 keyed asks, 2121 memo hits, 265.99 s over the
48-instant sweep) is what this cycle compares against.

## Task 5.1: the decided/boolean split at one instant

Counted by wrapping `_faces_disjoint` and `intersect_shapes`, and
patching `TestCase.assertNoSolidInterference` to run once for real then
report and exit (`os._exit(0)`) — filtering the runner to
`test_movement_runs_free_through_a_swing` as the archived siblings'
harness does, at the declared default `facing=45`.

The emitted count reproduces the baseline's 67 exactly before anything
else is trusted:

| | Count |
|---|---:|
| **Candidate pairs emitted** | 67 |
| Decided empty by the tier (no boolean) | 10 |
| Declined by the tier (boolean ran) | 57 |
| Booleans run | 57 |

Decided + declined (10 + 57 = 67) equals the emitted count exactly: at
this instant, with the verdict memo empty, every emitted pair reaches
`_faces_disjoint` exactly once. Declined (57) equals booleans run (57)
exactly: every pair the tier does not decide reaches the boolean, and no
pair reaches the boolean without first passing through the tier.

## Task 5.2: which solids remain in the undecided pairs

Recorded by wrapping `_placed_intersection` and, whenever it caused a new
boolean, capturing both records' `.name` and the face count of their
`record[8]` (local exact shape). All 57 declined pairs, tallied by how
often each solid name appears across them:

| Solid | Appearances (of 57 pairs) |
|---|---:|
| `wheel` (5 distinct train wheels) | 24 |
| `rod` | 23 |
| `plates` | 9 |
| `shell` | 6 |
| `ring` | 5 |
| `cannon_pinion` | 5 |
| `bottom_rod` | 5 |
| `hour_holder` | 4 |
| `standoffs` | 3 |
| `arbor` | 3 |
| `collet` | 3 |
| `hour_hand` | 3 |
| `top_rod` | 3 |
| `rating_button` | 3 |
| `rating_nyloc` | 3 |
| `lid`, `hook`, `minute_hand`, `body`, `upper_ring_nut`, `lower_ring_nut` | 2 each |

**This corrects the finding's own wording.** `workflow/warts.md`'s third
bullet said "the fused frame (both plates and their pillars, one solid)
sits in 40 of the 118 pairs" — a count that predates
`broad-phase-indexing-frame` and a solid that, as that cycle's own
evidence already showed, does not exist: `standoffs` and `plates` are two
separate topmost rigid solids, not one fused frame. Measured here, at 67
pairs, neither one dominates the population the face-box tier cannot
decide: `plates` appears in 9 of the 57 declined pairs and `standoffs` in
only 3. What actually dominates is the wheel train itself — `wheel` in
24 and `rod` (a 3-face cylindrical shaft, almost certainly the arbor the
wheels are mounted on) in 23 — a genuinely close mechanical fit between a
wheel's bore and the rod it turns on, not a spurious whole-solid
enclosure a smarter box could have avoided. The remaining declined pairs
are two other genuinely tight assemblies: the motion-works gear train
(`cannon_pinion`, `arbor`, `hour_holder`, `hour_hand`, `minute_hand`,
`collet`, `body`) and the pendulum's suspension and weight hardware
(`top_rod`, `bottom_rod`, `ring`, `upper_ring_nut`, `lower_ring_nut`,
`shell`, `lid`, `hook`, `rating_button`, `rating_nyloc`).

## Task 5.3: the tier's own cost, at the same instant

Timed with `time.perf_counter()` around the `_faces_disjoint` wrapper
(summed over all 67 calls) and, separately, around `_mutually_outside`
(the containment guard, called only when face boxes are disjoint):

| | Time | Calls |
|---|---:|---:|
| Tier (`_faces_disjoint`), all 67 pairs | 0.955 s | 67 |
| — of which the containment guard (`_mutually_outside`) | 0.770 s | 10 |
| Boolean (`intersect_shapes`), the 57 declined pairs | 10.035 s | 57 |

The containment guard's share (0.770 s of the tier's 0.955 s, across the
10 pairs that reached it, i.e. ~77 ms per decided pair) is the dominant
cost of the tier itself, as design.md section 7 named it might be. The
boolean time of the 10 decided pairs is not measured here (they never
ran), so the honest comparison is the sweep in task 5.4: the tier's
~0.95 s per instant, about 46 s over 48 instants, is paid inside a net
saving of 49 s. That makes the guard the tier's own next lever: at
~0.77 s per instant it is roughly a sixth of the 216 s that remain, and
a classifier cached per placed shape — the follow-up design.md section 7
names — would remove most of it. No classifier cache was added in this
cycle; the number is recorded for the pilot's decision.

## Task 5.4: the swing sweep, end to end, after

`test_movement_runs_free_through_a_swing` (`@testing_steps(48)`), exact
kernel, default placement quantum, `facing=45`, against the baseline's
3210 asks / 2121 hits / 1089 booleans / 265.99 s:

| Run | Keyed asks | Memo hits | Booleans | Tier decided | Wall time |
|---|---:|---:|---:|---:|---:|
| Baseline (`93612db`, after `broad-phase-indexing-frame`) | 3210 | 2121 | 1089 | — | 265.99 s |
| **After `face-box-broad-phase`** | 3210 | 2121 | 708 | 381 | 216.50 s |

Booleans fell 35.0% (1089 → 708, 381 fewer). Wall time fell 18.6%
(265.99 s → 216.50 s, 49.49 s faster). Keyed asks and memo hits are
UNCHANGED (3210 and 2121, exactly), as design.md and tasks.md both said
they must be: this cycle adds no bound and changes no candidate set, so
the same relative placements are asked about the same number of times —
only whether an asked-and-missed question needs a boolean changed. Tier
decided (381) + booleans (708) = 1089, exactly the baseline's boolean
count: every relative placement that was a genuine memo miss before this
cycle is still a genuine memo miss now, and the tier decides just over a
third of those (381 of 1089, 35.0%) without ever reaching OCCT.

Wall time was read from the wall_clock_02 test run's own reported line,
not the harness's own `atexit` timer (which also includes process
start-up and build time and is not directly comparable across runs); see
"Verdict identity" below for the reported line itself.

## Task 5.5: verdict identity

Before (recorded by `broad-phase-indexing-frame`'s own evidence, its
baseline row): `Ran 17 tests in 265.99 seconds: 1 passed, 0 failed`.

After this cycle: `Ran 18 tests in 216.50 seconds: 1 passed, 0 failed`.

The test COUNT differs (17 vs 18) for a reason unrelated to this cycle:
`git log -- simulation/shared/testing.py` in the project repository shows
commit `590189b` ("simulation: standardize clock motion and assemblies")
added four new test methods to the shared base class every clock's test
case inherits from — `test_the_bob_lid_screws_engage_the_separate_shell`,
`test_rod_turns_use_the_rods_geometric_centreline`,
`test_the_split_holder_fasteners_engage_their_mates`,
`test_the_split_spring_ratchet_parts_remain_engaged` — after the sibling
cycles' baseline was recorded and before this cycle's evidence was
gathered, as ordinary independent project development (the pilot note in
the task brief: "Another session may run heavy CAD jobs here"). The
harness filters to exactly one test by name
(`test_movement_runs_free_through_a_swing`), so the discovery count
changing does not affect which test actually ran; what matters for
verdict identity is preserved exactly: **1 passed, 0 failed**, both
before and after, same test, same outcome, no failure message in either
run.

## Honest comparison with the finding's own forecast

The finding this cycle answers estimated "plates × wheel booleans cost
0.5–2.2 s each, ~8 s of the 19 [s per instant]" and predicted the tier
would "decide a wheel between two plates without a boolean." Measured
here: the tier decides 10 of 67 pairs at the first instant (15%), not
the "40 of 118" (34%) the original, since-corrected wording estimated,
and the pairs it does NOT decide are dominated by the wheel train's own
mounting rod and by genuinely tight-fitting gear and hardware pairs, not
by the plates. Over the full sweep the win is real and measured —
35.0% fewer booleans, 18.6% faster — but smaller than the forecast's
implied share, precisely because the forecast's premise (one enclosing
frame sitting in a third of the pairs) did not survive measurement once
`broad-phase-indexing-frame` had already reduced the candidate set and
this cycle looked at what was actually left. The cycle's win is reported
as measured, not tuned toward the forecast: no margin, chunk size, or
fixture was adjusted to chase either the finding's number or a rounder
one.

Nothing was committed in the project repository by this cycle; only its
ignored `_build/` directory was written by these runs.
