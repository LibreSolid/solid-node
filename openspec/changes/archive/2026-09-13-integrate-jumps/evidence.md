# Evidence: integrate-jumps

Cycle 2 of the open-run simulation campaign, implemented in the framework
worktree `solid-node/WTs/open-run-simulation` (branch
`open-run-simulation`, base `5b7f4d0`, planning commit `84e0d1d`) on the
workspace venv, with `PYTHONPATH="$PWD"`.

## 0.2 The base suite

Recorded on the planning commit `84e0d1d` (the unchanged tree), before
any test or production change of this cycle:

```
$ python -m pytest -x -q
2339 passed, 4 skipped, 50 warnings, 925 subtests passed in 287.21s (0:04:47)
```

Exactly cycle 1's recorded 2339 passed / 4 skipped / 925 subtests. The 50
warnings are the pre-existing `FutureWarning`s of the legacy `render()`
fixtures; nothing fails at the base.

## 0.3 The base per-tick cost

Cycle 1's own probe, re-run on this worktree:

```
$ python openspec/changes/archive/2026-09-13-run-owns-the-coordinates/evidence/probe_cost.py
running  Train   (record=None): 11.732 s for 10000 ticks = 1.173 ms/tick, tracemalloc peak 13.2 KiB, trajectory 0 entries
running  Train   (record=64) : 11.989 s for 10000 ticks = 1.199 ms/tick, tracemalloc peak 42.1 KiB, trajectory 64 entries
untimed  TrainBody           : 3.259 s for 10000 ticks = 0.326 ms/tick, tracemalloc peak 2739.5 KiB, trajectory 10010 entries
ratio running/untimed per tick: 3.60x
```

**1.173 ms/tick** is the number design.md section 12 pins this cycle to
(cycle 1 recorded 1.16 ms on the same probe).

## 0.4 The two semantics the branch table is written against

`evidence/probe_semantics.py` reads them off `GraphValue.evaluate`
itself.

```
%% is math.fmod -- the sign of the DIVIDEND:
    7.0 %   3.0 = 1.0   fmod 1.0   python's %% 1.0   equal to fmod: True
   -7.0 %   3.0 = -1.0   fmod -1.0   python's %% 2.0   equal to fmod: True
    7.0 %  -3.0 = 1.0   fmod 1.0   python's %% -2.0   equal to fmod: True
   -7.0 %  -3.0 = -1.0   fmod -1.0   python's %% -1.0   equal to fmod: True
    0.5 %   1.0 = 0.5   fmod 0.5   python's %% 0.5   equal to fmod: True
   -0.5 %   1.0 = -0.5   fmod -0.5   python's %% 0.5   equal to fmod: True
trunc is 0 on the whole of (-1, 1), so a %% b is CONTINUOUS at zero
  and jumps only at a NONZERO integer of a / b:
   -1.5 % 1.0 = -0.5
   -1.0 % 1.0 = -0.0
   -0.5 % 1.0 = -0.5
    0.0 % 1.0 = 0.0
    0.5 % 1.0 = 0.5
    1.0 % 1.0 = 0.0
    1.5 % 1.0 = 0.5
a comparison evaluates to a Python bool:
  a > b at a=1.0 b=0.5 -> True (bool)
  a <= b at a=1.0 b=0.5 -> False (bool)
  a == b at a=1.0 b=0.5 -> False (bool)
  a != b at a=1.0 b=0.5 -> True (bool)
and arithmetic reads that bool as 1/0:
  -2 * a * (b > 0.5) at a=10.0 b=0.0 -> -0.0
  -2 * a * (b > 0.5) at a=10.0 b=1.0 -> -20.0
```

So `%` is `math.fmod` -- `a - b * trunc(a / b)`, the sign of the
DIVIDEND, and not Python's own `%` -- and `trunc` is `0` on the whole of
`(-1, 1)`, which is why `a % b` is CONTINUOUS where `a / b` crosses zero
and jumps only at a NONZERO integer of it (design.md section 1). A
comparison evaluates to a Python `bool` that arithmetic reads as 1/0,
which is what makes a gate factor a branch of `1.0` or `0.0`.

## 1.10 Every new fixture poses untimed, before any implementation

`evidence/probe_untimed_poses.py`, run on the unchanged tree with the
fixtures of section 1 added and nothing else. `UntimedControlTest` in
`tests/test_running_jumps.py` pins the same numbers, and they must not
move.

```
SteppedBody          crank=0.0        first.turn = 4.0
SteppedBody          crank=113.5      first.turn = 4.0
SteppedBody          crank=115.0      first.turn = 13.6
SteppedBody          crank=124.0      first.turn = 71.2
SteppedBody          crank=125.5      first.turn = 76.0
SteppedBody          crank=359.9      first.turn = 76.0
SteppedBody          crank=360.0      first.turn = 4.0
SteppedBody          crank=360.1      first.turn = 4.0
SteppedBody          crank=480.0      first.turn = 45.599999999999994
SteppedBody          crank=820.0      first.turn = 4.0
WindowBody           crank=100.0      pinion.turn = 4.0
WindowBody           crank=113.5      pinion.turn = 4.0
WindowBody           crank=115.0      pinion.turn = 13.6
WindowBody           crank=124.0      pinion.turn = 71.2
WindowBody           crank=125.5      pinion.turn = 76.0
WindowBody           crank=359.9      pinion.turn = 76.0
WindowBody           crank=360.0      pinion.turn = 4.0
WindowBody           crank=360.1      pinion.turn = 4.0
WindowBody           crank=460.0      pinion.turn = 4.0
WindowBody           crank=820.0      pinion.turn = 4.0
RemainderBody        crank=100.0      pinion.turn = 4.0
RemainderBody        crank=113.5      pinion.turn = 4.0
RemainderBody        crank=115.0      pinion.turn = 13.6
RemainderBody        crank=359.9      pinion.turn = 76.0
RemainderBody        crank=360.0      pinion.turn = 4.0
RemainderBody        crank=360.1      pinion.turn = 4.0
RemainderBody        crank=460.0      pinion.turn = 4.0
RemainderBody        crank=820.0      pinion.turn = 4.0
WrappedBody          crank=100.0      pinion.turn = 200.0
WrappedBody          crank=179.9      pinion.turn = 359.8
WrappedBody          crank=180.0      pinion.turn = 360.0
WrappedBody          crank=180.1      pinion.turn = -359.8
WrappedBody          crank=540.0      pinion.turn = 360.0
WrappedBody          crank=600.0      pinion.turn = -240.0
ReverserBody         crank=40.0       pinion.turn = 50.0
ReverserBody         crank=49.9       pinion.turn = 0.5000000000000071
ReverserBody         crank=50.0       pinion.turn = 0.0
ReverserBody         crank=50.1       pinion.turn = 0.5000000000000071
ReverserBody         crank=60.0       pinion.turn = 50.0
KinkedBody           crank=40.0       pinion.turn = 50.0
KinkedBody           crank=49.9       pinion.turn = 0.5000000000000071
KinkedBody           crank=50.0       pinion.turn = 0.0
KinkedBody           crank=50.1       pinion.turn = 0.5000000000000071
KinkedBody           crank=60.0       pinion.turn = 50.0
ThrowingBody         crank=40.0       pinion.turn = -200.0
ThrowingBody         crank=49.9       pinion.turn = -249.5
ThrowingBody         crank=50.0       pinion.turn = 0.0
ThrowingBody         crank=50.1       pinion.turn = 250.5
ThrowingBody         crank=60.0       pinion.turn = 300.0
AlternatingBody      crank=100.0      pinion.turn = 0.0
AlternatingBody      crank=460.0      pinion.turn = 0.0
AlternatingBody      crank=820.0      pinion.turn = 0.0
AlternatingBody      crank=1180.0     pinion.turn = 0.0
AlternatingBody      crank=1540.0     pinion.turn = 0.0
OnlyJumpsBody        turns=0.0        dial.turn = 0
OnlyJumpsBody        turns=0.5        dial.turn = 0
OnlyJumpsBody        turns=1.0        dial.turn = 1
OnlyJumpsBody        turns=2.5        dial.turn = 2
CrowdedBody          a=0.0        dial.turn = 0.0
CrowdedBody          a=0.25       dial.turn = 0.125
CrowdedBody          a=1.0        dial.turn = 0.0
CrowdedBody          a=2.75       dial.turn = 0.375
ClutchBody           shaft=10.0 sleeve=0.0        wheel.turn = -0.0
ClutchBody           shaft=14.0 sleeve=0.0        wheel.turn = -0.0
ClutchBody           shaft=10.0 sleeve=1.0        wheel.turn = -20.0
ClutchBody           shaft=14.0 sleeve=1.0        wheel.turn = -28.0
CarryBody            column=100.0                 tens.turn = 0.0
CarryBody            column=460.0                 tens.turn = 60.0
CarryBody            column=820.0                 tens.turn = 120.0
CarryBody            column=460.0 tens_entry=1.0  tens.turn = 96.0
CarryLeadBody        column=100.0                 tens.turn = 1.0
CarryLeadBody        column=460.0                 tens.turn = 61.0
CarryLeadBody        column=820.0                 tens.turn = 121.0
SettledBody          enabled=0.0 turns=0.0        dial.turn = 0.0
SettledBody          enabled=1.0 turns=0.0        dial.turn = 9.0
SettledBody          enabled=0.0 turns=2.0        dial.turn = 2.0
DivisorBody          a=10.0 b=-2.0                dial.turn = 5.0
DivisorBody          a=10.0 b=3.0                 dial.turn = 6.0
NonAffineBody        a=10.0 b=5.0                 dial.turn = 0.0
NonAffineBody        a=30.0 b=5.0                 dial.turn = 30.0
PortDrivenBody       crank=100.0                  first.turn = 4.0
PortDrivenBody       crank=460.0                  first.turn = 4.0
PortDrivenJointBody  crank=100.0                  first.turn = 4.0
PortDrivenJointBody  crank=460.0                  first.turn = 4.0
PortDrivenSmoothBody crank=100.0                  first.turn = 4.0
PortDrivenSmoothBody crank=125.5                  first.turn = 76.0
```

## 2 Red first

### 2.0 The names do not exist yet

```
$ python -c "<probe of the four names>"
solid_node.simulation.TooManyCrossings: AttributeError: module 'solid_node.simulation' has no attribute 'TooManyCrossings'
solid_node.simulation.Crossing: AttributeError: module 'solid_node.simulation' has no attribute 'Crossing'
solid_node.simulation.program.JumpPlan: AttributeError: module 'solid_node.simulation.program' has no attribute 'JumpPlan'
sim.crossings: AttributeError: 'Sim' object has no attribute 'crossings'
Edge.plans: AttributeError: 'Edge' object has no attribute 'plans'
```

So `tests/test_running_jumps.py` cannot be collected at all on the
unchanged tree:

```
$ python -m pytest -q tests/test_running_jumps.py
tests/test_running_jumps.py:32: in <module>
    from solid_node.simulation import Sim, TooManyCrossings, UnsupportedLaw
E   ImportError: cannot import name 'TooManyCrossings' from 'solid_node.simulation'
1 error in 0.24s
```

### The red shim, and why there are two red runs

`evidence/red_shim.py` is a pytest plugin that installs the NAMES this
cycle adds and nothing else: `TooManyCrossings`, `Crossing`, an empty
`Edge.plans` and an empty `Sim.crossings`. It partitions no tick, samples
no branch and locates no crossing.

It runs in two modes, and both are recorded, because a case has to be
seen red for its own reason:

* **lifted** (default) — `_JUMP_CALLS` and `_JUMP_OPERATORS` are emptied,
  so a jump-carrying law COMPILES and is integrated by cycle 1's own two
  evaluations: the ABSOLUTE reading. Every behavioural case then fails on
  the number that reading gives, which is exactly the number this cycle
  replaces.
* **refusing** (`JUMPS_RED_LIFT=0`) — the cycle-1 refusal is KEPT, which
  is the unshimmed tree. Every case fails on that refusal, including the
  handful whose two readings happen to agree (a jump law that is
  continuous at its boundary, such as the fixture carry with no lead, and
  the `sign` whose factor vanishes where it flips).

```
$ python -m pytest -q -p red_shim tests/test_running_jumps.py
31 failed, 14 passed, 305 subtests passed in 7.65s

$ JUMPS_RED_LIFT=0 python -m pytest -q -p red_shim tests/test_running_jumps.py
35 failed, 6 passed, 25 subtests passed in 2.08s
```

The 6 that pass in the refusing run are the three untimed controls
(`UntimedControlTest`), the two continuous controls
(`test_a_continuous_law_carries_no_plan`,
`test_a_continuous_law_into_the_same_port_still_compiles`) and
`test_crossings_belong_to_a_running_root`. Every other case of section 2
is red there.

### The red of each case

Under the **refusing** run every one of them reads, with the relation and
the primitive named:

```
AssertionError: 'joint' not found in 'crank drives register, stated by PortDriven: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.'
AssertionError: 'only' not found in 'turns drives dial.turn, stated by OnlyJumps: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.'
solid_node.simulation.program.UnsupportedLaw: (a, b) drives dial.turn, stated by Divisor: its expression contains the operator '%', which is a jump; jumps are not yet supported by the running mode.
solid_node.simulation.program.UnsupportedLaw: (a, b) drives dial.turn, stated by NonAffine: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: (enabled, turns) drives dial.turn, stated by Settled: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: (shaft, sleeve) drives wheel.turn, stated by Clutch: its expression contains the operator '>', which is a jump; jumps are not yet supported by the running mode.
solid_node.simulation.program.UnsupportedLaw: (tens_entry, units.turn) drives tens.turn, stated by Carry: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: (tens_entry, units.turn) drives tens.turn, stated by CarryLead: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: a drives dial.turn, stated by Crowded: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: crank drives first.turn, stated by PortDrivenJoint: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Alternating: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Remainder: its expression contains the operator '%', which is a jump; jumps are not yet supported by the running mode.
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Reverser: its expression contains sign(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Throwing: its expression contains sign(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Window: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Wrapped: its expression contains ceil(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
solid_node.simulation.program.UnsupportedLaw: second.turn drives first.turn, stated by BackwardJump: its expression contains ceil(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
```

Under the **lifted** run, case by case (the number on the left is what
the absolute reading gives today):

| Case | RED |
| --- | --- |
| `CompilePlanTest.test_a_gate_is_a_jump_node_over_its_difference` | IndexError: tuple index out of range |
| `CompilePlanTest.test_a_nested_jump_compiles_two_nodes_in_postorder` | IndexError: tuple index out of range |
| `CompilePlanTest.test_a_periodic_window_compiles_one_affine_floor` | IndexError: tuple index out of range |
| `CompilePlanTest.test_a_remainder_is_a_jump_node_over_its_quotient` | IndexError: tuple index out of range |
| `PeriodicWindowTest.test_the_crossing_tick_contributes_exactly_zero` | AssertionError: -72.0 != 0.0 |
| `PeriodicWindowTest.test_the_window_advances_once_per_revolution` | AssertionError: 4.0 != 76.0 |
| `NestedJumpTest.test_only_the_inner_node_ever_crosses` | AssertionError: Lists differ: [] != [1.0, 2.0, 3.0, 4.0] |
| `NestedJumpTest.test_the_law_engages_on_alternate_revolutions` | AssertionError: 0.0 != 72.0 ± 7.2e-11 |
| `PrimitiveTest.test_a_remainder_window_and_a_floor_window_agree` | AssertionError: 4.0 != 76.0 ± 7.6e-11 |
| `PrimitiveTest.test_a_wrapped_law_integrates_to_the_unwrapped_travel` | AssertionError: -440.0 != 1000.0 |
| `OnlyJumpsRefusalTest.test_a_jump_beside_a_sloped_term_compiles` | AssertionError: 2.0 != 0.0 |
| `OnlyJumpsRefusalTest.test_a_step_counter_is_refused` | AssertionError: UnsupportedLaw not raised |
| `HistoryRefusalTest.test_a_jumping_law_into_a_plain_port_is_refused` | AssertionError: UnsupportedLaw not raised |
| `CrossingRecordTest.test_a_refused_tick_records_no_crossing` | AssertionError: TooManyCrossings not raised |
| `CrossingRecordTest.test_reset_clears_the_crossing_ring` | AssertionError: 0 != 2 |
| `CrossingRecordTest.test_the_ring_keeps_the_most_recent_crossings` | AssertionError: 0 != 4 |
| `CarryTest.test_a_lead_makes_the_law_jump_and_the_jump_is_subtracted` | AssertionError: 120.0 != 118.0 ± 1.2e-10 |
| `SearchPathTest.test_a_product_of_two_sources_is_located_by_search` | IndexError: tuple index out of range |
| `PerTickRefusalTest.test_a_zero_divisor_refuses_the_tick` | AssertionError: UnsupportedLaw not raised |
| `PerTickRefusalTest.test_too_many_crossings_refuses_the_tick` | AssertionError: TooManyCrossings not raised |
| `PeriodicWindowTest.test_a_tick_that_passes_three_windows_adds_three_throws` | AssertionError: 4.0 != 220.0 ± 2.2e-10 |
| `PeriodicWindowTest.test_the_answer_does_not_depend_on_the_display_cadence` | SUBFAILED(ticks=1/12/40/240) AssertionError: 4.0 != 76.0 ± 7.6e-11 |
| `ClutchTest.test_a_gate_closing_inside_the_tick_takes_the_travel_after_it` | AssertionError: -28.0 != -4.0 |
| `PrimitiveTest.test_a_sign_that_jumps_contributes_its_segments_and_not_its_jump` | AssertionError: 500.0 != 0.0 |
| `LargeOriginTest.test_the_answer_is_bit_identical_across_six_orders_of_winding` | AssertionError: 4.0 != 148.0 ± 1.5e-10 |
| `SnapshotAcrossCrossingTest.test_a_snapshot_restored_over_a_crossing_replays_exactly` | AssertionError: 0 != 1 |
| `BackwardJumpTest.test_an_inverse_that_jumps_integrates_over_the_driven_id` | IndexError: tuple index out of range |

Three of those deserve reading as prose, because they are the campaign's
own numbers:

* `4.0 != 76.0` — the pilot's window, absolutely: the pinion is
  recomputed from the crank on every tick, so after a whole revolution it
  is back where it started rather than 72 degrees on.
* `-28.0 != -4.0` — the clutch closing inside one tick: the absolute
  reading applies `-2 * shaft` at the instant of engagement, which is the
  `-24` jump plus the `-4` of real travel. A jump never moves a part.
* `120.0 != 118.0` — the carry with a lead: the absolute reading hands on
  the full `CARRY_THROW` per revolution because it never sees the
  discontinuity the lead puts at the window boundary.

### 2.16 The three cases cycle 1 wrote for the refusal

`CompileRefusalTest::test_a_jump_is_refused` is rewritten as
`test_a_jump_compiles`, and seen red on the unshimmed tree:

```
$ python -m pytest -q tests/test_running_simulation.py -k CompileRefusalTest
E   solid_node.simulation.program.UnsupportedLaw: crank drives first.turn, stated by Stepped: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
1 failed, 3 passed, 48 deselected in 1.03s
```

`test_a_law_with_a_kink_compiles` keeps its `assertNotIn('floor', ...)`
on `Train` unchanged and goes on passing — `Program.described()` still
prints the whole graph, and `Train` carries no jump. There is no
documentation test pinning the refusal list (`tests/test_docs_exports.py`
checks embedded exports only), so the third item of task 2.16 is a
no-op; `docs/scenarios.rst` and `docs/changelog.rst` are still updated
under task 5.2.

### 2.14 The per-tick cost probe does not run

```
$ python openspec/changes/integrate-jumps/evidence/probe_cost.py
solid_node.simulation.program.UnsupportedLaw: crank drives pinion.turn, stated by Window: its expression contains floor(), which is a jump; jumps are not yet supported by the running mode, and locating a crossing inside the tick is the next cycle. Untimed and looping, the same law poses exactly as it always did.
```

## 3--4 Green

```
$ python -m pytest -q tests/test_running_jumps.py
41 passed, 314 subtests passed in 7.93s

$ python -m pytest -q tests/test_running_simulation.py tests/test_simulation_sim.py \
    tests/test_simulation_scenario.py tests/test_time_base.py tests/test_couplings.py \
    tests/test_joints.py tests/test_export.py tests/test_motion_package.py
490 passed, 8 warnings, 493 subtests passed in 29.82s
```

Two cases had to change to be testable, and both are recorded as
deviations in the implementation report:

* `test_the_ring_keeps_the_most_recent_crossings` originally drove the
  crank one degree a tick, which lands every window boundary EXACTLY on
  a tick's end. The increment is then right (the pinion gains its six
  throws) and no crossing is inside any tick, so the record is properly
  empty. The case now drives 1.5 degrees a tick, as design.md section 6
  does, and the behaviour it found is stated in `docs/scenarios.rst`.
* `test_a_wrapped_law_integrates_to_the_unwrapped_travel` asserts the
  driven coordinate GAINS exactly `1000.0`, as design.md section 6 and
  the spec scenario both word it; the task's "leaves the driven
  coordinate at exactly 1000.0" cannot be met, because the fixture's
  rest pose is `2 * wrap(100, 360) = 200`.

## 2.14 The per-tick cost

`evidence/probe_cost.py`. `Smooth` is `Window`'s machine with the
periodicity taken out -- the same law, the same shape, no jump node --
so the two `Window` rows are answerable to a control identical in
everything but the `floor`.

```
running  Train    no jump          : 10.677 s for 10000 ticks = 1.068 ms/tick, tracemalloc peak 11.2 KiB
untimed  TrainBody                 : 3.448 s for 10000 ticks = 0.345 ms/tick, tracemalloc peak 2741.0 KiB
running  Smooth   no jump          : 3.633 s for 10000 ticks = 0.363 ms/tick, tracemalloc peak 7.2 KiB
running  Window   no crossing      : 4.574 s for 10000 ticks = 0.457 ms/tick, tracemalloc peak 7.2 KiB
running  Window   one crossing/tick: 6.366 s for 10000 ticks = 0.637 ms/tick, tracemalloc peak 7.2 KiB

Window non-crossing / Smooth (same machine): 1.26x
Window crossing     / Smooth (same machine): 1.75x
Window non-crossing / Train  (cycle 1 pin):  0.43x
Window crossing     / Train  (cycle 1 pin):  0.60x
Train / untimed TrainBody:                   3.10x

Train  one tick, 4 law edges, no jump: 8 graph evaluations (4 fewer than cycle 1, which evaluated every law edge once more in _values() and discarded the result)
Smooth one tick, 1 law edge,  no jump: 2 graph evaluations
Window one tick, 1 law edge,  no crossing: 5 graph evaluations
Window one tick, 1 law edge,  one crossing: 8 graph evaluations
```

Against the base's **1.173 ms/tick** (section 0.3):

* rule 1 holds and then some: `Train`, which carries no jump, costs
  **1.068 ms/tick**, about 9% LESS than at the base. The saving is task
  4.2a -- `Run._values()` no longer evaluates a law edge whose targets
  are all bank coordinates and then discards the result -- and the
  evaluation count says it exactly: 8 graph evaluations a tick where
  cycle 1 made 12;
* a jump-carrying law costs **1.26x** its continuous twin on a
  non-crossing tick and **1.75x** on a crossing one, both inside the
  design's "twice cycle 1's" target, and both well under `Train`'s own
  per-tick cost;
* the evaluation counts are design.md section 12's prediction, checked:
  a non-crossing tick of `Window` is **5** evaluations (2 of the
  skeleton, 3 of the two-node argument) against the design's "two
  skeleton evaluations plus three evaluations of a two-node argument",
  and a crossing tick is **8** against its predicted 9 -- one cheaper,
  because the partition's midpoint branch sample is skipped when a jump
  node has no other jump inside it;
* memory is flat: 7.2 KiB peak over 10 000 ticks, against `Train`'s
  11.2 KiB and the untimed loop's 2.7 MiB.

## 2.12 The large origin

`evidence/probe_large_origin.py`, two turns of the Curta window at
dt = 1/240 from a crank already wound `W` turns, against the identical
run at zero winding.

```
| initial winding | crank magnitude | ulp | max per-tick deviation | pinion after two turns |
| --- | --- | --- | --- | --- |
| 0 | 100 | 1.4e-14 | -- | 147.99999999999994 |
| 10^3 turns | 3.6e+05 | 5.8e-11 | 0.000e+00 | 147.99999999999994 |
| 10^6 turns | 3.6e+08 | 6.0e-08 | 0.000e+00 | 147.99999999999994 |
| 10^9 turns | 3.6e+11 | 6.1e-05 | 0.000e+00 | 147.99999999999994 |
| 10^12 turns | 3.6e+14 | 6.2e-02 | 0.000e+00 | 147.99999999999994 |
| 10^13 turns | 3.6e+15 | 5.0e-01 | 0.000e+00 | 147.99999999999994 |
| 10^14 turns | 3.6e+16 | 4.0e+00 | 1.280e+01 | 148.0 |

The same 1e14 winding driven tick by tick rather than by one ramp:
  crank asked for 1.5 degrees a tick, 480 times, from 3.60000000000001e+16
  crank now 3.60000000000001e+16  (ulp 4.0e+00)
  pinion    4.0
```

Rows `0` to `10^13` are design.md section 11's table exactly: a max
per-tick deviation of ZERO and a final pinion of `147.99999999999994`,
BIT-IDENTICAL across six orders of winding. Locating a crossing adds no
error of its own -- for an affine level quantity it is solved from the
two source values the tick was handed, and the piece evaluation uses the
same path.

The `10^14` row differs from design.md's, and the difference is a
finding about the framework rather than about this cycle. The design's
table was measured by `evidence/prototype.py`, which ACCUMULATES the
source (`source += step`); at 3.6e16 the ulp is 4 degrees, so adding 1.5
degrees to it changes nothing and the crank never moves. The framework's
`RampProgram` instead computes `start + delta * k / ticks` ABSOLUTELY
from the move's own start, which resists that quantisation: the crank
does move, in steps of a whole ulp, and the trace deviates by up to 12.8
degrees of pinion while still reaching 148. Driven the prototype's way --
a fresh one-tick move from wherever the bank stands, 480 times -- the
framework reproduces the design's row exactly: the crank does not move at
all and the pinion stands at its rest 4.0.

Either way the boundary is the same and it is ADR-105's, not this
cycle's: `ulp(|crank|)` exceeding the tick's own travel. The test asserts
it in that form -- `ulp(1e13 * 360) < 1.5 < ulp(1e14 * 360)` -- and
asserts the accumulating drive standing still.

## 6.2 The two originating projects' own laws

`evidence/probe_projects.py` copies them VERBATIM -- `input_step` from
`projects/Calculators/Curta-Type-I-3x/simulation/input_mesh.py`, made
periodic exactly as the pilot's illustration states it, and `handed_on`,
`carried_column` and `trailing_idler` from
`projects/Calculators/Pascaline-module/simulation/carry.py` over the
constants of its own `simulation/layout.py` -- and states the smallest
machines that carry them. Nothing under `projects/` was read for
anything but copying, and nothing there was written.

```
the Curta bench's law, made periodic -- dt = 1/240
  rest                    pinion.turn = 4.0
  after crank turn 1      pinion.turn = 76.0   crank 460.0
  after crank turn 2      pinion.turn = 147.99999999999994   crank 820.0
  crossings: [('floor', 1.0, 0.333333), ('floor', 2.0, 0.333333)]

the Pascaline module's handed_on, over its own constants
  rest                    tens.turn = 65.53999999999999   idler.turn = -65.53999999999999
  one column revolution   tens.turn +65.40333333333331   idler.turn -65.40333333333331
  two column revolutions  tens.turn +130.80666666666664
  against CARRY_THROW 65.54: deficit 0.1366666666666987 = first_rise * lead / first_width = 0.13666666666666666
  one digit entered       tens.turn +166.80666666666664
```

Both compile and integrate, and both reproduce design.md's numbers:

* the Curta window gives `4.0` at rest, `76.0` after one crank turn and
  `147.99999999999994` after two, with one `floor` crossing per turn at
  `t = 1/3` -- design.md section 6's tick 174 exactly;
* the Pascaline module's column hands on **65.40333333333331** per
  revolution against its declared `CARRY_THROW = 65.54`. The deficit is
  **0.1366666666666987**, which is `first_rise * lead / first_width =
  4.10 * 0.10 / 3 = 0.13666666666666666` to the last bits. `CARRY_LEAD`
  carries the whole segment shape 0.1 degrees ahead of the boundary the
  sweep measured, so at the boundary the first segment already reads
  `4.10 * 0.1 / 3` up its ramp while the phase resets -- the law is
  DISCONTINUOUS there by exactly that much, and the integrated reading
  subtracts it.

  This is an empirical finding about the acceptance project, not a
  framework question. The law compiles and integrates unchanged, which
  is this cycle's obligation; whether the module wants the lead applied
  to the phase reset as well -- so that its throw integrates to the
  `CARRY_THROW` it declares -- is the module's own change, and its
  running migration now starts from this number rather than from a
  surprise. `trailing_idler`, `-handed_on(wheel)`, integrates to the
  same figure with the opposite sign.

## 6.1 The final suite

```
$ python -m pytest -q
2380 passed, 4 skipped, 50 warnings, 1245 subtests passed in 291.35s (0:04:51)
```

Against the base's 2339 passed / 4 skipped / 925 subtests (section 0.2):
**+41 cases and +320 subtests**, every one of them added by this cycle
(`tests/test_running_jumps.py`), and nothing lost. The same 50 warnings,
all of them the pre-existing legacy-`render()` `FutureWarning`s; no new
one.

One existing case beyond the three of task 2.16 had to change, and it is
a data list rather than a behaviour:
`tests/test_lazy_test_framework.py::SimulationPackageExports` pins the
exact set of `solid_node.simulation.__all__`. Its red, and the update,
are the other side of task 2.0's "the names do not exist yet":

```
E       AssertionError: Lists differ: ['Crossing', 'Driver', 'Instruction', 'Ramp[127 chars]ons'] != ['Driver', 'Instruction', 'RampProgram', 'R[95 chars]ons']
E       First extra element 9: 'qualified_drivers'
```

`TooManyCrossings` and `Crossing` were added to its `EXPECTED_EXPORTS`,
both mapped to `solid_node.simulation.program`, and the suite's own
checks that each export is lazy, is the object its submodule defines, and
survives a star import then cover them.

## 6.3 Validation

```
$ openspec validate integrate-jumps --strict
Change 'integrate-jumps' is valid

$ openspec validate --specs --strict
Totals: 32 passed, 0 failed (32 items)
```
