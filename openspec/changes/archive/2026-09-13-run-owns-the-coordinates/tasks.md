## 0. Before anything

- [x] 0.1 Work only in `solid-node/WTs/open-run-simulation` (branch
  `open-run-simulation`), with `PYTHONPATH="$PWD"` and the workspace venv
  `/home/asa/devel/libresolid-studio/.venv/bin/python`. Confirm
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path. Never write inside `/home/asa/devel/libresolid-studio/projects/`
  and never run a `git` write command anywhere.
- [x] 0.2 Record the FULL SUITE at the base (`python -m pytest -x -q`),
  exact counts, into `evidence.md`. Any failure here is pre-existing and
  must be shown to be so before task 8.
- [x] 0.3 Re-read `design.md` §5–§7 against the tree: confirm by a probe
  in `evidence/` that a coordinate bound outside any enumeration and
  then rendered is (a) swept by `clear_solved` on the next phase when it
  was in the previous phase's bound list, and (b) refused `DoublyBound`
  by `_step_relation` when both ends hold values. Paste the output into
  `evidence.md`; these are the two facts the run binder exists for.

## 1. The test mechanism: `tests/running_project/`

Project-style code, no meshes. Every class below is a fixture the red
tests of section 2 read.

- [x] 1.1 `parts.py`: `Arbor(Solid2Node)` with `turn = Revolute(axis=(0, 0, 1), unit='deg')`;
  `Slide(Solid2Node)` with `travel = Prismatic(axis=(1, 0, 0), unit='mm')`;
  `Wheel(Solid2Node)` with a plain `turn = RotationalPort(unit='deg')`.
- [x] 1.2 `machine.py`: `tooth_window(source, target)` returning
  `lambda angle: 4 + 72 * clamp01((angle - 113.5) / 11.25)` over
  `solid_node.math.clamp01`; `periodic_window` the same with
  `angle - 360 * floor(angle / 360)` inside; `TrainBody(AssemblyNode)`
  (no time base) declaring `crank = Driver(default=0.0, unit='deg')`,
  `lever = Driver(default=100.0, range=(100, 140), unit='deg')`,
  `first = Arbor()`, `second = Arbor()`, `slide = Slide()`, its own joint
  `spindle = Revolute(axis=(0, 0, 1), unit='deg')`, and
  `wheel = Wheel(turn=spindle)` — a wiring from a bank coordinate into a
  PLAIN port, so the plain-port path is exercised beside the joints — the
  relations `crank.drives(first.turn, ratio=2.0)`,
  `first.turn.drives(second.turn, ratio=-1.5)`,
  `lever.drives(slide.travel, law=tooth_window)`,
  `crank.drives(spindle, ratio=1.0)`, and
  `instructions = {'Park': Instruction({'crank': 40.0}, duration=0.5), 'Advance': Instruction(by={'crank': 10.0}, duration=0.5)}`;
  `Train(TrainBody)` with `time = Time.running()`;
  `LoopingTrain(TrainBody)` with `time = Time(loop=2.0)`.
- [x] 1.3 `machine.py` continued: `Backwards` (running; `crank.drives(first.turn, ratio=2.0)`,
  `second.turn.drives(first.turn, ratio=4.0)`); `Differential` (running;
  drivers `wrist_in`, `sum_in`; joints `wrist`, `tool` on itself;
  `left = wrist + 2 * tool`; `wrist_in.drives(wrist)`,
  `wrist.drives(tool, ratio=1.0)`, `sum_in.drives(left)`); `Stepped`
  (running; `crank.drives(first.turn, law=periodic_window)`);
  `Stdlib` (running; a law calling `math.sin`); `HandBound` (running;
  `simulate()` binds `self.first.turn = self.crank * 2` unconditionally,
  no relation into it); `Guarded` (running; `simulate()` binds
  `slide.travel = 4.0` under `if ... is None`, no relation into it);
  `Opaque` (running; `simulate()` binds a plain port from the crank and
  a relation drives `first.turn` from that port); `Ranged` (running;
  `first = Arbor` with a site joint `turn=Revolute(..., range=(-90, 90))`);
  `Unbound` (running; a joint nothing drives or binds); `Sixfree`
  (running; a `Free` on an assembly, four of six bound by relations);
  `Follower` (running; a plain `readout = RotationalPort(unit='deg')`
  on the root bound in `simulate()` as `self.readout = self.first.turn.value`
  — the Pascaline module's `self.stop.angle = self.angle.value` idiom).
- [x] 1.4 Confirm every fixture except the refusal fixtures poses
  untimed (`set_state(crank=10.0)` on `TrainBody`) before any framework
  change; record the rest-pose numbers in `evidence.md` — they are what
  scenario "The initial bank is the rest pose" compares against.

## 2. Red first

Lands in `tests/test_running_simulation.py` (new),
`tests/test_time_base.py` and `tests/test_couplings.py`. **Every case
MUST be seen RED on the current tree before section 3 begins, and the RED
text recorded in `evidence.md`.** A case that is green at the base is a
case that proves nothing; say so and rewrite it.

- [x] 2.1 (1) `Time.running()` is accepted on a root: `mode == 'running'`,
  `loop is None`, `declared_time` returns it; `Time()` refused naming
  both spellings; refused under the name `clock`; refused on a leaf; a
  child declaring it under a root refused at the read naming both.
  RED: `Time.running` does not exist.
- [x] 2.2 (2) `Sim(Train(), 0.1).state` has exactly the keys `crank`,
  `lever`, `first.turn`, `second.turn`, `slide.travel`, `spindle`; with
  `state={'crank': 10.0}` the initial values equal the untimed rest pose
  of 1.4. RED: `state` unknown kwarg; bank holds drivers only.
- [x] 2.3 (3) two `move('crank', by=10, duration=1.0)` calls, each run to
  completion: `crank == 20`, `first.turn == 40`, `second.turn == -60`,
  the leaves placed at those angles (read the joints' operations);
  handles report `completed` with `10` admitted each.
- [x] 2.4 (3b) the kink case: `move('lever', by=40, duration=0.8)`, dt 0.1,
  asserting `slide.travel` after ticks 3, 4, 5 and 8 equals `13.6`,
  `45.6`, `76.0`, `76.0` exactly (`assertEqual`, not `assertAlmostEqual`
  beyond float rounding of the same arithmetic).
- [x] 2.5 (4) `Backwards`: `move('crank', by=10, duration=1.0)` →
  `first.turn == 20`, `second.turn == 5`.
- [x] 2.6 (5) `Train`: after 2.3, `slide.travel` and `lever` unchanged on
  every tick (assert inside an `every(0.1, ...)`).
- [x] 2.7 (6) `Differential`: `move('wrist_in', by=10, duration=1.0)` then
  `run(0.1)` raises `RunConflict` naming `left`, the formula, the
  relation from `sum_in` and the increments; `sim.state`, `sim.tick` and
  the node's coordinates unchanged; the handle reports `refused`,
  `admitted == 0`; then `move('wrist_in', by=10, duration=1.0)` +
  `move('sum_in', by=30, duration=1.0)` runs green to `wrist == 10`,
  `tool == 10`, `left` reading `30` on the node.
- [x] 2.8 (7) `Sim(HandBound(), 0.1)` raises `DoublyBound` naming
  `HandBound`, `first.turn` and the running simulation; `Sim(Guarded(), 0.1)`
  constructs, `slide.travel == 4.0`, and ten ticks later still `4.0`
  with no refusal.
- [x] 2.9 (8) snapshot/restore: five ticks of a ten-tick move, snapshot,
  five more, restore → `sim.state`, `sim.tick`, node coordinates equal
  the snapshot's; five more → equals the first completion; a snapshot
  from `Sim(Backwards(), 0.1)` restored into `Sim(Train(), 0.1)` refused
  naming both program identities with nothing changed; a snapshot at
  `dt=0.05` into `dt=0.1` refused naming both steps.
- [x] 2.10 (9) `reset()` → `snapshot() == initial`, tick 0, state equals
  the rest pose, `commands == ()`, `trajectory == []`.
- [x] 2.11 (10) `trigger('Advance')` twice (each run to completion) →
  `crank == 20`; `trigger('Park')` from `20` → `crank == 40` after
  0.5 s; on `LoopingTrain`, `trigger('Advance')` twice ramps the driver
  to `20` through the existing programs and `Instruction.by` reads back;
  `Instruction({'crank': 0}, duration=1, by={'crank': 1})` and
  `Instruction(duration=1)` refused.
- [x] 2.12 (11) `rate('crank', 90.0)` then `move('crank', by=10, duration=1.0)`
  refused naming `crank` and the rate command; two moves refused the
  same way; `rate('crank', 0)` after two seconds → `crank == 180`,
  handle `completed`, `commands == ()`; `rate('crank', 0)` with nothing
  active is a no-op.
- [x] 2.13 (12) after ten ticks: `node.render()`, reading every
  coordinate, and `set_state(**sim.state, time=sim.time)` change neither
  `sim.state` nor `sim.tick` nor any coordinate; the next tick continues
  from the same bank.
- [x] 2.14 (13) `Sim(Stepped(), 0.1)` raises `UnsupportedLaw` naming the
  relation `crank drives first.turn` and saying jumps are not yet
  supported; `Sim(Stdlib(), 0.1)` raises `UnsupportedLaw` saying the law
  cannot be applied to symbols; `Sim(Opaque(), 0.1)` raises naming the
  relation and the port; the same classes without `Time.running()` pose
  untimed unchanged.
- [x] 2.15 reverse refused: `move('crank', by=-10, ...)`,
  `move('crank', to=5, ...)` from `20`, `rate('crank', -90.0)`; only an
  input can be moved: `move('first.turn', ...)` refused listing the
  inputs; retirement: one hundred single-tick moves leave
  `len(sim.commands) <= 1`; zero-duration move integrates at the current
  tick with no tick added.
- [x] 2.16 `Ranged`: moving the crank so `first.turn` would reach `100`
  raises `JointRangeError` on the crossing tick naming `first.turn`,
  `100`, the range; bank at the last admitted tick.
- [x] 2.17 `Unbound`: `Sim(Unbound(), 0.1)` refused naming the coordinate;
  `Sixfree`: refused naming the two unbound coordinates (this is the open
  question of design §2; the test pins the proposal's answer).
- [x] 2.18 recording: default `trajectory == []` after 10 000 ticks and
  `tracemalloc` peak flat between tick 1 000 and 10 000 within 64 KiB;
  `record=64` after 100 ticks holds ticks 37..100 oldest first;
  `record=0`, `-1`, `True`, `'all'` refused.
- [x] 2.19 `set_state` coordinate ids: on `Train()` (no `Sim`),
  `set_state(**{'first.turn': 12.0})` binds the leaf's joint and places
  it; on `LoopingTrain()` and `TrainBody()` the same call is refused
  listing the driver ids; a call naming an unknown coordinate rolls
  `first.turn` back. `Sixfree`-style dotted id `chassis.pose.roll` binds
  through the joint.
- [x] 2.20 couplings: a run-bound slot survives `clear_solved` across
  three enumerations; a wiring into a run-bound joint is the run's while
  the wiring into `wheel.turn` (plain port) still applies from the
  run-bound `spindle`; a backward solve into a run-bound source is
  refused naming the run (an author-bound plain port driven by a
  relation whose source the run owns).
- [x] 2.21 time base plumbing: `animation_block` of a running root has no
  `loop`; `manager/snapshot` keyframes the fraction; unbound `time`
  reads `$t` on root and child, `set_keyframe(2.5)` reads `2.5`.
- [x] 2.22 import cost, in a fresh interpreter (the shape of
  `tests/test_motion_package.py`): a `Sim` over `LoopingTrain` run for
  ten ticks leaves `solid_node.simulation.run` and
  `solid_node.simulation.program` out of `sys.modules`; importing
  `solid_node.motion.ports` and `.couplings` imports nothing from
  `solid_node.simulation`; a `Sim` over `Train` imports both and no
  `cadquery`.
- [x] 2.24 `Follower`: over ten ticks of `move('crank', by=10, duration=1.0)`,
  after every tick `readout.value == first.turn` on the node, `readout`'s
  binder is `None` (the author's) and never a `RunBinder`, and the value
  is fresh each tick (assert inside an `every(0.1, ...)`). RED: the
  proposal's own trap — an enumeration run under the run binder would
  mark `readout` run-bound and freeze it from tick 2.
- [x] 2.25 serializer: a root declaring a `by=` instruction beside a
  `targets=` one serializes an instructions table with the `targets=`
  entry only, and the document is otherwise unchanged; the widget's
  `trigger` must never meet an entry without `targets`.
- [x] 2.23 (14) the existing suites are the regression net: nothing in
  `tests/test_simulation_*.py`, `tests/test_time_base.py`,
  `tests/test_couplings.py`, `tests/test_joints.py`,
  `tests/test_driver_ids.py`, `tests/test_document_drivers.py` or
  `tests/test_export.py` is edited except to ADD cases.

## 3. The time base and the run binder (ports, couplings, assembly)

- [x] 3.1 `motion/ports.py`: `Time.loop` optional (`None` for running),
  `Time.running()` classmethod, `Time.mode` property, `Time()` refused;
  `__post_init__` validates `loop` only when given. `RunBinder` marker
  with a `described()` reading "the running simulation". Greens 2.1.
- [x] 3.2 `node/assembly.py::read_time`, `core/serializer.py::animation_block`,
  `manager/snapshot.py`: `loop is None` is no loop. Greens 2.21.
- [x] 3.3 `motion/ports.py::bind`: refuse a binding of a run-bound sink by
  any binder but its run, raising `DoublyBound` (imported inside the
  branch) naming the coordinate, the current phase's assembly class or
  the slot's node, and the run. Greens the `HandBound` half of 2.8 once
  4.x binds as the run.
- [x] 3.4 `motion/couplings.py`: `ResolvedEnd.bound()` returns `True` for a
  run-bound slot first; `clear_solved` skips run-bound slots;
  `_step_relation` marks a record whose driven ends are all run-bound
  `direction = 'run'`; `_step_wiring` marks a wiring whose target is
  run-bound `applied`; `_describe_binder` describes a `RunBinder`. Greens
  2.20 with 4.x.
- [x] 3.5 `node/assembly.py::set_state`/`_receive_state`/`_undo`: under a
  running root deliver a joint-coordinate id to its owning node (own
  coordinates checked against `declared_ports` before the dotted split;
  leaves handed their addressed entries), bind through `set_coordinate`,
  record the id in `declared`, save `(slot, value, binder)` for
  rollback; under any other root unchanged. Greens 2.19. The run
  binder wraps the DELIVERY's coordinate bindings only — never the
  enumeration `set_state` runs afterwards (design §4.5, §7.7). Greens 2.24
  with 4.x.

## 4. The program and the run (simulation)

- [x] 4.1 `simulation/program.py`: `compile_program(root, bank_ids)` over
  every node's `_relations`, `_wirings` and `_solved_formulas`;
  node classification (bank / intermediate / opaque); law application to
  `symbol(id)` tokens in the recorded direction with the multi-target
  shape check; the discontinuous-primitive scan over `postorder`
  (`floor`, `ceil`, `sign`, `%`, comparisons), the non-symbolic refusals
  (exception, non-expression return, `raw`, call outside
  `SYMBOLIC_BUILTINS`), the opaque-source refusal, the mixed-group
  refusal; Kahn ordering; `Program.identity`. `UnsupportedLaw` names the
  relation as written and the stating class. Greens 2.14 and the compile
  half of 2.2.
- [x] 4.2 `simulation/run.py`: `Run` holding the bank, the program, one
  `RunBinder`, the command table and the ring; `Command` (handle);
  `RunSnapshot` (frozen); `RunConflict`. The tick of design §7 with
  increments only until commit, the tolerance check, the range pre-check,
  rollback with `refused` retirement, commit, run-bound `set_state`,
  ring, actions, cadences. Zero-duration integration. Greens 2.3–2.7,
  2.13, 2.15, 2.16, 2.18.
- [x] 4.3 `simulation/sim.py`: `state=` and `record=` arguments; the
  running branch of `__init__` (design §4, three enumerations, the
  unbound-coordinate and duplicate-id refusals); delegation of `move`,
  `rate`, `commands`, `snapshot`, `restore`, `reset`, `initial`,
  `program`, `running`; refusals naming `Time.running()` under other
  roots; `trigger` mapping under a running root (claim all inputs
  first). Greens 2.2, 2.9–2.12, 2.17, the `Guarded` half of 2.8.
- [x] 4.4 `simulation/instruction.py`: `Instruction(targets=None, duration=None, *, by=None)`,
  exactly one of the two; `sim.py::trigger` under untimed/looping ramps
  `by=` relatively; `core/serializer.py::instructions_table` OMITS a
  relative instruction (design §9). Greens 2.11 and 2.25.
- [x] 4.5 `simulation/__init__.py`: `_EXPORTS` gains `RunConflict` (run)
  and `UnsupportedLaw` (program), lazily. `docs/api-reference.rst`
  autoclass entries. Greens 2.22's positive half.

## 5. Evidence and documentation

- [x] 5.1 `evidence.md`: the base suite counts (0.2), the probe outputs
  (0.3), every RED text (section 2), the final suite counts, and a
  per-tick cost measurement of `Train` at `dt=0.1` over 10 000 ticks
  (wall time per tick, `tracemalloc` peak) beside the untimed `Sim`'s
  cost on `TrainBody` — the number cycle 4's evaluator is measured
  against.
- [x] 5.2 `docs/animation.rst`: the third base, what `self.time` reads under
  it, the preview caveat. `docs/driving.rst` and `docs/scenarios.rst`:
  `Sim(..., state=, record=)`, `move`/`rate`/`trigger`, handles and
  ownership, snapshot/restore/reset, `Instruction(by=)`, the refusals of
  this cycle and which cycle lifts each. `docs/changelog.rst` entry.
- [x] 5.3 `docs/architecture.md`: the Simulation section gains the running
  mode paragraph (bank, program, tick, binder) and the Kinematics section
  the third base; the Map row for Simulation gains the new modules.

## 6. Green and checked

- [x] 6.1 Every case of section 2 green; every suite of 2.23 green with
  the same counts as 0.2 plus the added cases; no `FutureWarning` added.
- [x] 6.2 `openspec validate run-owns-the-coordinates --strict` passes.
- [x] 6.3 Hand the implementation report to the adversarial review with
  `evidence.md`: name any deviation from `design.md` and why, and any
  scenario whose wording had to change to be testable.

## 7. After the code is green (the skill's own steps)

- [x] 7.1 Extract the three ADRs design.md §13 names, under the next free
  numbers, each citing this change; update `docs/adrs/README.md`.
- [x] 7.2 Sync the delta specs into the baselines
  (`openspec-sync-specs`) and archive the change.
- [x] 7.3 Record in `workflow/open-run-simulation/roadmap.md` that cycle 1
  is on the branch, with the commit, and list the open questions of
  design.md for the pilot.
