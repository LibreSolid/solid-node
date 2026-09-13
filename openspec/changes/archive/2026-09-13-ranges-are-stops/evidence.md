# Evidence: ranges-are-stops

Cycle 3 of the open-run simulation campaign, implemented in the framework
worktree `solid-node/WTs/open-run-simulation` (branch
`open-run-simulation`, base `8019c6d`, planning commit `5045b9c`) on the
workspace venv, with `PYTHONPATH="$PWD"`.

## How red-first was run here

Section 2 of `tasks.md` asks for every case to be seen red before any
production change, and its own task 2.0 states the qualification this
cycle needs: several fixtures cannot even be CONSTRUCTED on the unchanged
tree, because `Joint._span` refuses `None` and a callable as a bound at
realization. So the red is taken in TWO passes, exactly as 2.0 directs:

- **red pass 1**, on the unchanged production tree: every case run, every
  red text recorded. Cases that need no new declaration surface
  (`Train`'s reverse requests, `Ranged`'s stop) are already red for a
  WRONG ANSWER here; the rest are red for a missing name or a refused
  declaration, which is 2.0's own evidence.
- **red pass 2**, after tasks 3 and 4 only — the compile surface and the
  joint's declaration — and before any of task 5's tick: the fixtures now
  construct, the names now exist, and every remaining case is red for a
  wrong ANSWER, which is the refusal cycle 1 wrote.

No production file was touched between the base suite below and red pass
1; `git status -- solid_node/ docs/` was empty at that point.

## 0.2 The base suite

Recorded on the planning commit `5045b9c` (the unchanged tree), before
any test or production change of this cycle:

```
$ python -m pytest -x -q
2380 passed, 4 skipped, 50 warnings, 1245 subtests passed in 294.22s (0:04:54)
```

Exactly cycle 2's recorded 2380 passed / 4 skipped / 1245 subtests. The
50 warnings are the pre-existing `FutureWarning`s of the legacy
`render()` fixtures; nothing fails at the base.

## 0.3 The base per-tick cost

Cycle 1's own probe, re-run on this worktree:

```
$ python openspec/changes/archive/2026-09-13-run-owns-the-coordinates/evidence/probe_cost.py
running  Train   (record=None): 10.443 s for 10000 ticks = 1.044 ms/tick, tracemalloc peak 13.4 KiB, trajectory 0 entries
running  Train   (record=64) : 10.553 s for 10000 ticks = 1.055 ms/tick, tracemalloc peak 42.3 KiB, trajectory 64 entries
untimed  TrainBody           : 3.237 s for 10000 ticks = 0.324 ms/tick, tracemalloc peak 2739.3 KiB, trajectory 10010 entries
ratio running/untimed per tick: 3.23x
```

And cycle 2's, for the `Window` numbers this cycle is answerable to
beside `Train`:

```
$ python openspec/changes/archive/2026-09-13-integrate-jumps/evidence/probe_cost.py
running  Train    no jump          : 10.565 s for 10000 ticks = 1.057 ms/tick, tracemalloc peak 11.2 KiB
untimed  TrainBody                 : 3.404 s for 10000 ticks = 0.340 ms/tick, tracemalloc peak 2676.0 KiB
running  Smooth   no jump          : 3.424 s for 10000 ticks = 0.342 ms/tick, tracemalloc peak 7.2 KiB
running  Window   no crossing      : 4.472 s for 10000 ticks = 0.447 ms/tick, tracemalloc peak 7.2 KiB
running  Window   one crossing/tick: 6.158 s for 10000 ticks = 0.616 ms/tick, tracemalloc peak 7.2 KiB
```

**1.044 / 1.057 ms/tick** on `Train` and **0.447 / 0.616 ms/tick** on
`Window` are the numbers design.md section 15 pins this cycle to (cycle 2
recorded 1.07 and 0.46 / 0.64 on the same probes).

## 0.4 The three facts sections 8 and 9 are written against

`evidence/probe_declarations.py`, on the unchanged tree.

```
1. Joint._span on the unchanged tree
   range=(0, None)                                      -> ParameterError: Probe.turn: range -- bound None is not a number
   range=(None, 50.0)                                   -> ParameterError: Probe.turn: range -- bound None is not a number
   range=(lambda turn: 36 * floor(turn / 36), None)     -> ParameterError: Probe.turn: range -- bound <function <lambda> at 0x...> is not a number
   range=lambda node: (-90, 90)  (the NODE form, unchanged)   -> (-90, 90)

2. RampProgram over a NEGATIVE delta
   dtype=float 0 -> -10 over 4 ticks: [0.0, -2.5, -5.0, -7.5, -10]
   dtype=int   0 -> -10 over 4 ticks: [0, -3, -5, -8, -10]
   dtype=int   0 ->  10 over 4 ticks: [0, 2, 5, 7, 10]

3. solid_node.math.floor
   floor(40 / 36)                = 1 (int)
   floor(symbol("turn") / 36)    = floor((turn / 36)) -> node kind='call' op='floor'
   36 * floor(symbol("turn")/36) = (36 * floor((turn / 36)))
```

So both forms of design.md section 9 are genuinely new — `None` is
refused as "not a number" and a callable given as a BOUND is refused the
same way, while a callable given as the WHOLE range keeps its existing
node meaning, which is the distinction by POSITION the design rests on.
`RampProgram` already distributes a negative delta monotonically and
lands exactly on its target at `k == ticks` for both dtypes (section 8),
and `floor` is a plain number on a float and a `floor` CALL NODE on a
symbol, which is what lets a bound be compiled exactly as a law is
(section 9).

## 2.0 The names do not exist yet

On the unchanged tree:

```
from solid_node.simulation import Stop: AttributeError: module 'solid_node.simulation' has no attribute 'Stop'
sim.stops: AttributeError: 'Sim' object has no attribute 'stops'
sim.program.sources: AttributeError: 'Program' object has no attribute 'sources'
Edge.affine: AttributeError: 'Edge' object has no attribute 'affine'
JumpPlan.cuts: AttributeError: type object 'JumpPlan' has no attribute 'cuts'
```

and the whole new suite cannot even be collected:

```
$ python -m pytest tests/test_running_stops.py -q
ImportError while importing test module 'tests/test_running_stops.py'.
tests/test_running_stops.py:33: in <module>
    from solid_node.simulation import Instruction, RunConflict, Sim, Stop
E   ImportError: cannot import name 'Stop' from 'solid_node.simulation'
```

## Red pass 1: the cases that are already a wrong ANSWER

`tests/test_running_simulation.py`, on the unchanged production tree.

**2.1 Reverse moves are admitted** (`test_a_reverse_request_runs`, the
rewrite of `test_a_reverse_request_is_refused`):

```
E  ValueError: move('crank', ...) would travel backwards (-10.0 in design units). A reverse move is refused in this cycle: reverse travel meets no stop until a joint range becomes a physical stop.
E  ValueError: move('crank', ...) would travel backwards (-15.0 in design units). A reverse move is refused in this cycle: reverse travel meets no stop until a joint range becomes a physical stop.
E  ValueError: rate('crank', -90.0) would run backwards. A reverse rate is refused in this cycle: reverse travel meets no stop until a joint range becomes a physical stop.
```

**2.2 A reverse rate on an INTEGER input truncates toward zero**
(`test_a_reverse_rate_on_an_integer_input_truncates_toward_zero`): the
negative subtest is red, the POSITIVE one passes unchanged, which is what
makes `math.trunc` a change to nothing already ratified.

```
E  ValueError: rate('step', -1.5) would run backwards. A reverse rate is refused in this cycle: reverse travel meets no stop until a joint range becomes a physical stop.
```

**2.5 The range stops the tick rather than failing it**
(`RangeTest::test_the_crossing_tick_commits_at_the_bound`, the rewrite of
`test_the_crossing_tick_is_refused_and_the_bank_stands`):

```
E  solid_node.motion.joints.JointRangeError: first.turn would reach 100.0 over this tick, outside the range -90 to 90 deg its joint declares. The tick committed nothing and the bank stands at the last admitted tick: in this cycle a range fails the tick rather than stopping the group it is connected to.
```

and its sibling, the move that lands EXACTLY on the bound:

```
E  AttributeError: 'Sim' object has no attribute 'stops'
```

```
$ python -m pytest tests/test_running_simulation.py -q
6 failed, 52 passed, 15 subtests passed in 15.65s
```

**2.11 The untimed meaning of an expression range**
(`tests/test_joints.py::RangeTest`, six added cases): every one red at
REALIZATION, because the declaration itself is new.

```
E  solid_node.parameters.ParameterError: HalfOpen.spin: range -- bound None is not a number
E  solid_node.parameters.ParameterError: Ratchet.turn: range -- bound <function ...<lambda>> is not a number
E  solid_node.parameters.ParameterError: Impossible.turn: range -- bound <function ...<lambda>> is not a number
E  solid_node.parameters.ParameterError: Wrong.turn: range -- bound None is not a number
E  solid_node.parameters.ParameterError: Backwards.turn: range -- bound <function ...<lambda>> is not a number
```

```
$ python -m pytest tests/test_joints.py::RangeTest -q
12 failed, 8 passed, 6 subtests passed in 1.99s
```

The existing numeric-range cases of that class (`-135`/`135` refused by
name, the inclusive bounds, the symbolic binding unchecked, a joint with
no range) all pass, unchanged, in the same run.

## Red pass 2: every case red for a WRONG ANSWER

After tasks 3 and 4 ONLY — `Program.sources`, `Edge.affine`,
`JumpPlan.cuts`, the compiled span table, `Stop`, and the joint's `None`
and callable bounds — and before any of task 5's tick. The fixtures now
construct and the names now exist, so what remains red is cycle 1's
refusal answering where a stop is owed.

```
$ python -m pytest tests/test_running_stops.py -q
29 failed, 12 passed, 1 skipped, 16 subtests passed in 1.61s
```

What passes already is exactly the compile surface: the candidate table
(`GroupTest::test_the_candidate_table_names_the_reaching_inputs`,
`test_a_check_edge_contributes_nothing_to_the_table`), the affine
classification (`CurvedStopTest::test_the_classification_is_read_off_the_edge`),
the span in the program identity (`ProgramIdentityTest`), and the untimed
controls. Every behavioural case is red:

**2.3 The ratchet** (`RatchetTest`, seven cases):

```
E  ValueError: move('arbor', ...) would travel backwards (-10.0 in design units). A reverse move is refused in this cycle: reverse travel meets no stop until a joint range becomes a physical stop.
E  ValueError: rate('arbor', -40.0) would run backwards. A reverse rate is refused in this cycle: reverse travel meets no stop until a joint range becomes a physical stop.
E  AttributeError: 'Sim' object has no attribute 'stops'      (the forward row, which already commits)
```

**2.4 The swept stop** (`SweptStopTest`, three cases):

```
E  solid_node.motion.joints.JointRangeError: rack.travel would reach 55.0 over this tick, outside the range None to 50.0 mm its joint declares. The tick committed nothing and the bank stands at the last admitted tick: in this cycle a range fails the tick rather than stopping the group it is connected to.
```

**2.7 A multi-source coordinate with one input stopped**
(`SharedCoordinateTest`):

```
E  solid_node.motion.joints.JointRangeError: c.turn would reach 12.0 over this tick, outside the range None to 10.0 deg its joint declares. ...
```

**2.8 Two stops in one tick** (`TwoStopsTest`, both command orders):

```
E  solid_node.motion.joints.JointRangeError: lever.turn would reach 26.0 over this tick, outside the range None to 20.0 deg its joint declares. ...
```

**2.9 A stop and a jump crossing in one tick** (`StopAndJumpTest`):

```
E  solid_node.motion.joints.JointRangeError: first.turn would reach 150.0 over this tick, outside the range None to 145.0 deg its joint declares. ...
```

**2.14 A stop on a NON-AFFINE chain** (`CurvedStopTest`):

```
E  solid_node.motion.joints.JointRangeError: dial.turn would reach 25.71150438746157 over this tick, outside the range None to 20.0 deg its joint declares. ...
```

**2.16b The group is who pushes** (`GroupTest`, the open gate and the
closed one):

```
E  solid_node.motion.joints.JointRangeError: wheel.turn would reach 55.0 over this tick, outside the range None to 20.0 deg its joint declares. ...   (gate at 1)
E  solid_node.motion.joints.JointRangeError: wheel.turn would reach 25.0 over this tick, outside the range None to 20.0 deg its joint declares. ...   (gate at 0)
```

The gate-open red is the one the review added 1.4b and 2.16b for: with
the gate at `0` the whole tick fails today, and a STATIC group would
block `crank` tomorrow. Both are wrong answers to the same tick.

**2.15 A tick that fails after a stop commits nothing**
(`AtomicTickTest`, and `StopRecordTest::test_a_refused_tick_records_no_stop`):

```
E  solid_node.motion.joints.JointRangeError: wrist would reach 10.0 over this tick, outside the range None to 5.0 deg its joint declares. ...
```

— the range refuses before the second segment's conflict can be reached
at all, which is the point of the case.

**2.10 Snapshot and restore across a block** (`SnapshotAcrossBlockTest`,
three cases) and **2.12 the stop record** (`StopRecordTest`, four cases)
are red on the reverse refusal and on `'Sim' object has no attribute
'stops'`.

## 6.1 What a stop costs

`evidence/probe_stop_cost.py`, same host and method as sections 0.3 and
cycle 2's probe.

```
1. A tick with no stop pays what it pays today

running  Train    no ranged coordinate  : 10.653 s for 10000 ticks = 1.065 ms/tick, tracemalloc peak 11.7 KiB
untimed  TrainBody                      : 3.554 s for 10000 ticks = 0.355 ms/tick, tracemalloc peak 2741.0 KiB
running  Smooth   no jump               : 3.861 s for 10000 ticks = 0.386 ms/tick, tracemalloc peak 7.4 KiB
running  Window   no crossing           : 4.786 s for 10000 ticks = 0.479 ms/tick, tracemalloc peak 7.5 KiB
running  Window   one crossing/tick     : 6.534 s for 10000 ticks = 0.653 ms/tick, tracemalloc peak 7.5 KiB
running  Swept    number bound, no stop  : 5.153 s for 10000 ticks = 0.515 ms/tick, tracemalloc peak 123.1 KiB
running  Ratchet  EXPRESSION bound, no stop: 4.155 s for 10000 ticks = 0.415 ms/tick, tracemalloc peak 11.9 KiB

2. A blocking tick, against the same loop that does not block

Swept    affine chain, no stop      : 0.624 s for 2000 iterations = 0.312 ms/iteration   -> completed
Swept    affine chain, STOPS       : 0.713 s for 2000 iterations = 0.356 ms/iteration   -> blocked
  blocking / free on the same machine: 1.14x
Curved   searched chain, no stop   : 0.482 s for 2000 iterations = 0.241 ms/iteration   -> completed
Curved   searched chain, STOPS    : 2.454 s for 2000 iterations = 1.227 ms/iteration   -> blocked
  blocking / free on the same machine: 5.09x

3. One tick, deterministically

Train    no range  :    8 graph evaluations, 1 propagation pass(es), 0 candidate pass(es)   -> crank completed
Swept    no stop   :    4 graph evaluations, 1 propagation pass(es), 0 candidate pass(es)   -> steer completed
Swept    STOPS     :   14 graph evaluations, 3 propagation pass(es), 1 candidate pass(es)   -> steer blocked
Ratchet  no stop   :    3 graph evaluations, 1 propagation pass(es), 0 candidate pass(es)   -> arbor completed
Ratchet  STOPS     :    9 graph evaluations, 3 propagation pass(es), 1 candidate pass(es)   -> arbor blocked
Curved   no stop   :    2 graph evaluations, 1 propagation pass(es), 0 candidate pass(es)   -> crank completed
Curved   STOPS     :  206 graph evaluations, 3 propagation pass(es), 1 candidate pass(es)   -> crank blocked
TwoStops TWO STOPS :   24 graph evaluations, 5 propagation pass(es), 2 candidate pass(es)   -> lever_in blocked, steer blocked
OpenGate STOPS     :   38 graph evaluations, 3 propagation pass(es), 2 candidate pass(es)   -> push blocked, crank completed
```

Against design.md section 15, item by item, and honestly:

- **A tick with no stop pays what it pays today.** `Train` comes back at
  **1.065 ms/tick** against the base's 1.044 and 1.057 on the same probes
  — inside the run-to-run spread of that measurement, and the
  deterministic count says why: one propagation pass and eight graph
  evaluations, exactly cycle 2's. `Window` reads 0.479 / 0.653 against
  the base's 0.447 / 0.616; both are within the same spread and neither
  machine has a ranged coordinate, so nothing in this cycle's code runs
  on their ticks beyond the empty span loop. **No regression is claimed
  beyond that spread, and none is hidden**: the counts, which do not vary
  between runs, are identical to cycle 2's.
- **A ranged coordinate that does not block** costs the comparison that
  was always there. `Ratchet`'s EXPRESSION bound costs one extra graph
  evaluation per tick — three instead of the two its single law needs —
  which is the one number this cycle adds to a non-blocking tick.
- **A blocking tick on an affine chain costs `2S + 1` propagation
  passes**: 3 for one stop, 5 for `TwoStops`' two. Exactly as stated.
- **The contribution test costs one pass per candidate with a nonzero
  admission, on a blocking tick only**: 1 on `Swept` and `Ratchet`, 2 on
  `TwoStops` (one per group), 2 on `OpenGate` — where both `push` and
  `crank` are candidates and only `push` is found to push. A non-blocking
  tick runs none.
- **A blocking tick on a non-affine chain costs EDGE evaluations, not
  program passes**: `Curved` runs 3 propagation passes like any other,
  and 206 graph evaluations — 103 edge evaluations of 2 graphs each, the
  65 samples plus the bisection rounds, inside the
  `_SUBDIVISIONS + _BISECTION_ROUNDS` bound. 5.1x the same loop that does
  not block, and paid once, at the stop.
- **Memory is flat**: `tracemalloc` peak unchanged on every unranged
  machine. `Swept`'s higher PEAK (123 KiB against `Train`'s 12) is its
  `Prismatic` leaf's per-tick placement, not growth — measured directly,
  with `record=None` and a rate running:

  ```
  Swept growth over 9x the ticks: 64 bytes
  Train growth over 9x the ticks: 64 bytes
  ```

  which is the same 64 bytes cycle 1's own "nothing is recorded by
  default" test allows over the same shape.

## 6.2 The originating projects

`evidence/probe_projects.py`. Cycle 2's two laws are copied verbatim and
unchanged; the RATCHET BOUND is the one line this probe adds, and it adds
it here rather than in the project.

```
the Curta bench's law, made periodic -- dt = 1/240
  rest                    pinion.turn = 4.0
  after crank turn 1      pinion.turn = 76.0   crank 460.0
  after crank turn 2      pinion.turn = 147.99999999999994   crank 820.0
  crossings: [('floor', 1.0, 0.333333), ('floor', 2.0, 0.333333)]
  stops: []

the Pascaline module's carry, over its own constants
  one column revolution   tens.turn +65.40333333333331
  against CARRY_THROW 65.54: deficit 0.1366666666666987
  stops: []
```

Both are cycle 2's own numbers, unchanged: nothing in this cycle moves a
machine that declares no range.

The module's own chain — `input.turn` -> `drum.turn` at `-1` ->
`carry.turn` at `-1` — with `DIGIT_STEP * floor(turn / DIGIT_STEP)` as
`input.turn`'s lower bound, is design.md section 11's table row for row:

```
the module's own chain WITH the ratchet bound, dt = 0.1
  the tooth is 36.0 degrees, ten of them
  each row of design.md section 11, from its own start:
   start  request  bound    t*  admitted     status  turn after  drum after
    40.0    +20.0   36.0     -    +20.00  completed       60.00      -60.00
    40.0    -10.0   36.0   0.4     -4.00    blocked       36.00      -36.00   blocked ('angle',)
    36.0    -10.0   36.0     0     +0.00    blocked       36.00      -36.00   blocked ('angle',)
    36.0     +4.0   36.0     -     +4.00  completed       40.00      -40.00
    40.0    -10.0   36.0   0.4     -4.00    blocked       36.00      -36.00   blocked ('angle',)
    75.0    -10.0   72.0   0.3     -3.00    blocked       72.00      -72.00   blocked ('angle',)

  read down rows 3-5: retention. And the same reverse at three
  cadences, which is the cadence independence a stop must have:
   1 tick(s) of -10.000: blocking tick  1, t* 0.4                  input.turn 36.0   admitted -4.0
   4 tick(s) of -2.500: blocking tick  2, t* 0.6                  input.turn 36.0   admitted -4.0
  40 tick(s) of -0.250: blocking tick 17, t* 0.0                  input.turn 36.0   admitted -4.0
```

The drum follows the arbor through the `-1` ratio and stops with it,
because it is what the stopped input alone determines; the last row is
the tooth advancing with the arbor (`36 * floor(75 / 36) == 72`).

## 7.1 Green

The full suite, with every case of section 2 green and no new warning:

```
$ python -m pytest -q
2424 passed, 5 skipped, 50 warnings, 1295 subtests passed in 294.37s (0:04:54)
```

Against the base's **2380 passed / 4 skipped / 50 warnings / 1245
subtests**: +44 tests, +50 subtests, +1 skip. The one extra skip is
`DeferredBoundTest::test_a_bound_may_name_a_second_coordinate`, the
suite's own record of design.md section 10's deferral (task 1.8). The
warning count is unchanged at 50, all of them the pre-existing
`FutureWarning`s of the legacy `render()` fixtures.

The four suites the cycle touches, run together:

```
$ python -m pytest tests/test_running_stops.py tests/test_running_simulation.py \
      tests/test_running_jumps.py tests/test_joints.py -q
286 passed, 1 skipped, 1 warning, 609 subtests passed in 26.14s
```

One existing test changed for a reason outside this cycle's behaviour:
`tests/test_lazy_test_framework.py::SimulationPackageExports` carries a
hand-written table of the package's public exports, and `Stop` joins it.
It was caught by the full suite rather than by the four above, as

```
$ python -m pytest -q
FAILED tests/test_lazy_test_framework.py::SimulationPackageExports::test_all_lists_exactly_the_names_exported_before
1 failed, 2423 passed, 5 skipped, 50 warnings, 1292 subtests passed in 295.64s
```

— `__all__` had gained `Stop` and the table had not. The table is written
out by hand on purpose ("a table that agreed with itself would prove
nothing about what consumers used to import"), so adding the row is the
correct fix and the assertion is the correct guard.

`openspec validate ranges-are-stops --strict` passes, and
`openspec validate --specs --strict` passes over all 32 baselines after
the sync (32 passed, 0 failed).

## 7.3 Deviations from `design.md`

None in behaviour. Three things are worth the reviewer's eye:

1. **Task 5.1's own commit.** The task asks for the `_pass` refactor to
   be committed separately with its own green suite; the cycle makes
   exactly one implementation commit, so the refactor was landed with its
   own green run of the four running and joints suites instead.
   `Run._pass` IS cycle 1's `integrate` body verbatim, with one change
   the segment loop forces: `self._refuse(moved)` is lifted out of it to
   the caller, because a failed SEGMENT is not a failed tick until the
   caller says so. The refusal itself is unchanged and its tests are
   unchanged.
2. **Red-first in two passes.** Stated at the top of this file: the
   fixtures cannot be constructed on the unchanged tree, which task 2.0
   anticipates. Every behavioural case was seen red for a wrong ANSWER
   before any of task 5.
3. **The compile refusal's error kind.** Design section 9 says a bound
   the expression cannot say is "refused by joint and node identity" and
   names no exception class. `UnsupportedLaw` is used — the compile
   step's existing refusal kind, whose docstring gained one clause saying
   a bound is compiled by the same rule and refused by the same kind. No
   new exported name. The run's own broken-invariant refusal (design
   section 5's "internal refusal" when a stop stops no moving input) is a
   module-private `StopInvariantError(RuntimeError)` in `run.py`, not
   exported, caught by the same handler that refuses the tick.
