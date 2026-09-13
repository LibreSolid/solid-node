# Evidence: run-owns-the-coordinates

Cycle 1 of the open-run simulation campaign, implemented in the framework
worktree `solid-node/WTs/open-run-simulation` (branch
`open-run-simulation`) on the workspace venv, `PYTHONPATH="$PWD"`.

## 0.2 The base suite

Recorded on the planning commit `a1d54cc` (the unchanged tree), before
any test or production change of this cycle:

```
$ python -m pytest -q
2270 passed, 4 skipped, 50 warnings, 893 subtests passed in 279.24s (0:04:39)
```

The 50 warnings are the pre-existing `FutureWarning`s of the legacy
`render()` fixtures (`Carriage`, `InstantCarriage`, `Broken`, `Machine`
and friends); nothing fails at the base.

## 0.3 The two facts the run binder exists for

`evidence/probe_binder.py` (kept beside this file, with the manifest a
fixture project needs) states one root with a driver, one leaf with a
`Revolute`, and the relation `crank.drives(first.turn, ratio=2.0)`.

```
$ python openspec/changes/run-owns-the-coordinates/evidence/probe_binder.py
(a) after the rest render     first.turn = 20.0   binder = RelationRecord   enum_marker set: True
(a) after the hand binding    first.turn = 99.0   binder = None   enum_marker: None
(a) after one more render()   first.turn = 20.0   binder = RelationRecord
(a) VERDICT: the hand binding outside the enumeration was SWEPT and re-solved by the relation

(b) DoublyBound: first.turn would be bound by the relation crank drives first.turn and by the author's simulate(). A coordinate has exactly one binder in one enumeration of the tree, and the framework does not compare two values to decide whether two statements agree: they are ordinarily symbolic expressions. Drop one of them.
```

(a) is `clear_solved` doing exactly what design.md §5 says it would do to
a run: the slot sits in the assembly's previous phase's `_solver_bound`
list, the binding made outside any enumeration carries
`_enum_marker = None`, and the next phase drops value and binder before
the author's `simulate()` runs. Without the run-bound exemption the bank
would be swept on the first tick.

(b) is `_step_relation`'s `driver_bound and driven_bound` branch
(`couplings.py:2012-2018`) refusing a relation both of whose ends hold
values. Under a run every relation end is bound before the phase runs,
so without the `direction = 'run'` rule every relation of a running root
would refuse on the first tick.

## 1.4 Every fixture poses untimed at the base

`tests/running_project/` (`parts.py`, `machine.py`) is the tiny machine
the cycle is answerable to. Neither `Time.running()` nor
`Instruction(by=)` exists at the base, so the module cannot be imported
as written; `evidence/probe_rest_pose.py` gives the two declarations a
base spelling (a one-second loop, and a `by=` an instruction stores and
nothing reads) and poses every fixture. The numbers are properties of
the relations and of the rest render, not of the time base.

```
$ python openspec/changes/run-owns-the-coordinates/evidence/probe_rest_pose.py
TrainBody at crank=10, lever=100 (default): first.turn=20.0, second.turn=-30.0, slide.travel=4.0, spindle=10.0, wheel.turn (plain port)=10.0
Backwards at crank=10: first.turn=20.0, second.turn=5.0
Differential at wrist_in=10, sum_in=30: wrist=10.0, tool=10.0, left=30.0
Guarded at crank=10: first.turn=20.0, slide.travel=4.0
OpaqueBody at crank=10: relay=30.0, first.turn=30.0
SteppedBody at crank=470 (one turn past the window): first.turn=4.0
StdlibBody at crank=30: first.turn=-9.880316240928618
Ranged at crank=10: first.turn=20.0
Unbound at crank=10: first.turn=20.0, idle.turn=None
Sixfree at lift=5, surge=1, sway=2, heading=30: pose.x=1.0, pose.y=2.0, pose.z=5.0, pose.yaw=30.0, pose.roll=None, pose.pitch=None
Follower at crank=10: first.turn=20.0, gauge.turn=20.0, gauge.readout=20.0
HandBound at crank=10: first.turn=20.0
every fixture posed untimed on the unchanged tree
```

`TrainBody` at `crank=10` is what scenario "The initial bank is the rest
pose" compares against: `first.turn == 20.0`, `second.turn == -30.0`,
`slide.travel == 4.0` (the tooth window at the lever's default of 100,
below the window), `spindle == 10.0`, and the PLAIN port `wheel.turn` at
`10.0` — computed by the enumeration from the wiring, never banked.

## 2. Red first

Every case of section 2 was run on the UNCHANGED production tree before
any of section 3 or 4 was written.

### 2.0 The names do not exist

```
$ python -m pytest -q tests/test_running_simulation.py tests/test_time_base.py tests/test_couplings.py tests/test_motion_package.py
E   ImportError: cannot import name 'RunConflict' from 'solid_node.simulation'
E   AttributeError: type object 'Time' has no attribute 'running'
E   ImportError: cannot import name 'RunBinder' from 'solid_node.motion.ports'
3 errors in 1.18s
```

That is one collection error for sixty-odd cases, which proves only that
three names are missing. To see each case red FOR ITS OWN REASON,
`evidence/red_shim.py` is a pytest plugin installing the DECLARATIONS
this cycle adds and none of its behaviour: `Time.running()` and
`Time.mode`, a `RunBinder` marker, the two new error kinds, and an
`Instruction` that accepts `by=` and stores it. Nothing in it owns a
coordinate, compiles a law, integrates a tick or binds anything.

```
$ PYTHONPATH="$PWD:$PWD/openspec/changes/run-owns-the-coordinates/evidence" \
  python -m pytest -q -p red_shim tests/test_running_simulation.py \
  tests/test_time_base.py tests/test_couplings.py tests/test_motion_package.py
67 failed, 220 passed, 207 subtests passed in 6.75s
```

### 2.x The RED text of every case

| Case (task) | RED on the unchanged tree |
| --- | --- |
| 2.1 `Time.running()` declared (test_time_base) | `AttributeError: type object 'Time' has no attribute 'running'` at class definition |
| 2.1 `Time()` refused naming both spellings | `TypeError: Time.__init__() missing 1 required positional argument: 'loop'` |
| 2.2 the bank's keys | `AssertionError: Lists differ: ['crank', 'lever'] != ['crank', 'first.turn', 'lever', 'second.turn', 'slide.travel', 'spindle']` |
| 2.2 the initial bank is the rest pose | `TypeError: Sim.__init__() got an unexpected keyword argument 'state'` |
| 2.2 a plain port is not banked | `TypeError: Sim.__init__() got an unexpected keyword argument 'state'` |
| 2.2 a joint on a leaf is owned | `TypeError: Sim.__init__() got an unexpected keyword argument 'state'` |
| 2.2 `state=` refuses a coordinate id | `TypeError: Sim.__init__() got an unexpected keyword argument 'state'` |
| 2.2 the running surface refused under a looping root | `AttributeError: 'Sim' object has no attribute 'running'` |
| 2.3 two moves accumulate | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.4 the kink integrates exactly | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.5 backward propagation | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.6 an undriven joint holds | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.7 a disagreeing tick is refused | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.7 the increments are named | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.7 the group moved consistently | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.8 an author binding is refused | `AssertionError: DoublyBound not raised` |
| 2.8 a guarded rest default keeps working | `KeyError: 'slide.travel'` (the bank holds drivers only) |
| 2.9 snapshot restores mid-run | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.9 a mismatched program is refused | `AttributeError: 'Sim' object has no attribute 'snapshot'` |
| 2.9 a mismatched dt is refused | `AttributeError: 'Sim' object has no attribute 'snapshot'` |
| 2.9 a handle before a restore is cancelled | `AttributeError: 'Sim' object has no attribute 'restore'` |
| 2.10 reset returns to the initial snapshot | `TypeError: Sim.__init__() got an unexpected keyword argument 'record'` |
| 2.11 a relative instruction accumulates | `AttributeError: 'NoneType' object has no attribute 'items'` (`sim.py:221`, `trigger` reading `instruction.targets`) |
| 2.11 an absolute instruction moves to its target | `AttributeError: 'NoneType' object has no attribute 'items'` |
| 2.11 a relative instruction ramps under a looping root | `AttributeError: 'NoneType' object has no attribute 'items'` |
| 2.11 the declaration reads back one of the two | green under the shim's `by=`; red without it (`TypeError: __init__() got an unexpected keyword argument 'by'`) |
| 2.11 exactly one of targets and by | `AssertionError: TypeError not raised` |
| 2.11 an owned input starts nothing | `AttributeError: 'Sim' object has no attribute 'rate'` |
| 2.12 a rate and a move conflict | `AttributeError: 'Sim' object has no attribute 'rate'` |
| 2.12 two moves conflict | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.12 a rate accumulates until released | `AttributeError: 'Sim' object has no attribute 'rate'` |
| 2.12 releasing an unowned input | `AttributeError: 'Sim' object has no attribute 'rate'` |
| 2.13 rendering and rebinding change nothing | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.14 a jump is refused | `AssertionError: UnsupportedLaw not raised` |
| 2.14 a stdlib law is refused | `AssertionError: UnsupportedLaw not raised` |
| 2.14 an opaque source is refused | `AssertionError: UnsupportedLaw not raised` |
| 2.14 a law with a kink compiles | `AttributeError: 'Sim' object has no attribute 'program'` |
| 2.15 a reverse request is refused | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.15 only a declared input can be moved | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.15 completed commands are retired | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.15 a zero-duration move integrates now | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.16 the range crossing is refused | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.17 an unbound coordinate is refused | `AssertionError: ValueError not raised` |
| 2.17 a partly bound `Free` names both | `AssertionError: ValueError not raised` |
| 2.18 nothing is recorded by default | `AttributeError: 'Sim' object has no attribute 'rate'` |
| 2.18 a ring keeps the most recent ticks | `TypeError: Sim.__init__() got an unexpected keyword argument 'record'` |
| 2.18 an invalid option is refused (4 subtests) | `TypeError: Sim.__init__() got an unexpected keyword argument 'record'` |
| 2.19 a coordinate id binds under a running root | `ValueError: undeclared driver name in set_state: 'first.turn'. ... declared: crank, lever.` |
| 2.19 a dotted coordinate binds | `ValueError: undeclared driver name in set_state: 'chassis.pose.roll'. ... declared: heading, lift, surge, sway.` |
| 2.19 refused under any other root | green at the base — the REGRESSION guard that the refusal is unchanged where it must be |
| 2.19 a refused binding restores coordinates | green at the base for the same reason (nothing binds, so nothing to restore); red once 2.19's first case passes |
| 2.20 a run-bound slot survives the clear (3 subtests) | `AssertionError: 20.0 != 40.0` — the relation re-solved from the driver and overwrote the run |
| 2.20 every relation into a run-owned coordinate (4 subtests) | `AssertionError: 'forward' != 'run'` |
| 2.20 a wiring into a run-bound joint | `ValueError: cannot bind 'turn' of rod: Arbor declares rod = ...(turn=...), and that wiring binds it at the end of every simulate() of Arbor.` |
| 2.20 a backward solve into a run-bound source | `AssertionError: DoublyBound not raised` |
| 2.21 unbound time reads bare `$t` (root and child) | `AssertionError: '($t * None)' != '$t'` |
| 2.21 keyframes bind seconds, clearing restores | `AssertionError: '($t * None)' != '$t'` |
| 2.21 `animation_block` carries no loop | `AssertionError: {'fps': 30, 'frames': 360, 'loop': None} != {'fps': 30, 'frames': 360}` |
| 2.21 the snapshot keyframes the fraction | `TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'` (`manager/snapshot.py:228`) |
| 2.22 a looping root imports no engine | `AssertionError: the probed snippet exited 1` (the fixture cannot be imported at the base) |
| 2.22 a running root imports the engine | `AssertionError: the probed snippet exited 1` |
| 2.22 ports and couplings import nothing from simulation | green at the base — the REGRESSION guard the `cli-startup-cost` delta states, pinning that `RunBinder` and the couplings recognition add no import |
| 2.24 the follower keeps the author as its binder | `AttributeError: 'Sim' object has no attribute 'move'` |
| 2.25 a relative instruction is not published | `AttributeError: 'NoneType' object has no attribute 'items'` (`core/serializer.py:219`) |

Three cases are GREEN at the base and say so above: they are the
regression guards their delta specs state (the coordinate-id refusal
under a non-running root, its rollback, and the motion package's import
cost). Every other case of section 2 was seen red.

The wiring red is the one that changed the implementation: `ports.bind`
refuses ANY binding of a wired coordinate outside `wiring_binding()`, so
a run could not have bound `rod.turn` at all. See the implementation
report's deviations.

## 5.1 What a tick costs

`evidence/probe_cost.py`, on the workspace venv, `Train` at `dt=0.1`
over ten thousand ticks, beside the untimed stepping loop over the same
machine without a time base:

```
$ python openspec/changes/run-owns-the-coordinates/evidence/probe_cost.py
running  Train   (record=None): 11.546 s for 10000 ticks = 1.155 ms/tick, tracemalloc peak 13.3 KiB, trajectory 0 entries
running  Train   (record=64) : 12.146 s for 10000 ticks = 1.215 ms/tick, tracemalloc peak 42.0 KiB, trajectory 64 entries
untimed  TrainBody           : 3.616 s for 10000 ticks = 0.362 ms/tick, tracemalloc peak 2739.4 KiB, trajectory 10010 entries
ratio running/untimed per tick: 3.19x
```

A running tick costs **1.16 ms** against the untimed loop's **0.36 ms**
on this machine: 3.2x, for four compiled edges evaluated through
`GraphValue.evaluate` (a dict per evaluation and two walks of the graph
per edge) plus the same `set_state` delivery and enumeration every tick
already paid for drivers. That is the number cycle 4's compiled
evaluator is measured against, with the spike's 500-coordinate budget as
its target.

Memory is the other half of the comparison and the point of bounded
recording: **13.3 KiB** peak over ten thousand running ticks against
**2.7 MiB** for the untimed loop's unbounded trajectory. The ring at
`record=64` costs 42 KiB and does not grow with the tick count.

## 6.1 The final suite

```
$ python -m pytest -q
2339 passed, 4 skipped, 50 warnings, 925 subtests passed in 288.42s (0:04:48)
```

Against the base (`2270 passed, 4 skipped, 50 warnings, 893 subtests`):
**+69 tests and +32 subtests, no failures, no skips added, and the same
50 warnings** — the pre-existing legacy-`render()` `FutureWarning`s, with
none added.

One EXISTING case had to change rather than only gain a sibling:
`tests/test_lazy_test_framework.py::SimulationPackageExports` pins the
package's export list by value, and the two new error kinds grow it. It
was seen red for exactly that reason before the list was updated:

```
E   AssertionError: Lists differ: ['Dri[32 chars]m', 'RunConflict', 'ScenarioTest', 'Sim', 'Uns[55 chars]ons'] != ['Dri[32 chars]m', 'ScenarioTest', 'Sim', 'qualified_drivers'[22 chars]ons']
E   First differing element 3:
E   'RunConflict'
E   'ScenarioTest'
```

Every other file named by task 2.23 gained cases only.

### The set_state cases, re-checked red

Two cases of 2.19 had to be re-pointed after they first went green: they
were written against `Train`, whose `first.turn` a relation drives, and
a hand `set_state` is not a run — the enumeration `set_state` runs
afterwards clears the slot and the relation re-solves it, exactly as the
0.3 probe showed a hand binding behaves. They now bind a coordinate
nothing drives (`Unbound.idle.turn`), and a new case
(`test_a_coordinate_a_relation_drives_is_still_the_relations`) pins the
boundary they revealed: what makes the bank stick is the RUN as the
binder and nothing else.

Their red was re-checked on the finished tree with the delivery disabled
(`_coordinate_delivery` returning `None`, the base behaviour):

```
E   ValueError: undeclared driver name in set_state: 'first.turn'. ... declared: crank, lever.
E   ValueError: undeclared driver name in set_state: 'idle.turn'. ... declared: crank.
E   ValueError: undeclared driver name in set_state: 'chassis.pose.roll'. ... declared: heading, lift, surge, sway.
E   ValueError: undeclared driver name in set_state: 'idle.turn'. ... declared: crank.
4 failed, 1 passed, 2 subtests passed
```

The one that passes is the regression guard: a coordinate id stays
refused under a looping or undeclared root.
