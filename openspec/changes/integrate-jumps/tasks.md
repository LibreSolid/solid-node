## 0. Before anything

- [ ] 0.1 Work only in `solid-node/WTs/open-run-simulation` (branch
  `open-run-simulation`, base `5b7f4d0`), with `PYTHONPATH="$PWD"` and the
  workspace venv `/home/asa/devel/libresolid-studio/.venv/bin/python`.
  Confirm `git rev-parse --show-toplevel` prints that worktree and
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path. Never write inside
  `/home/asa/devel/libresolid-studio/projects/` and never write in the
  pilot's primary `solid-node/` checkout.
- [ ] 0.2 Record the FULL SUITE at the base (`python -m pytest -x -q`),
  exact counts, into `evidence.md`, beside cycle 1's recorded 2339
  passed / 4 skipped / 925 subtests. Any failure here is pre-existing
  and must be shown to be so before task 7.
- [ ] 0.3 Record the BASE per-tick cost by re-running cycle 1's own probe,
  `openspec/changes/archive/2026-09-13-run-owns-the-coordinates/evidence/probe_cost.py`,
  on this worktree. Paste the output into `evidence.md`. It is the
  1.16 ms this cycle is answerable to (design §12).
- [ ] 0.4 Read `design.md` §1 against `solid_node/scad_expression.py`
  and confirm by a probe in `evidence/` that `GraphValue.evaluate`
  spells `%` as `math.fmod` (sign of the DIVIDEND) and a comparison as
  a Python `bool`. Paste the output. These are the two semantics the
  branch table of §1 is written against.

## 1. The fixtures: `tests/running_project/machine.py`

Project-style code, no meshes. `periodic_window`, `Stepped` and
`SteppedBody` are already there and keep their spelling; everything
below is added beside them.

- [ ] 1.1 Laws: `clutch(sources, target)` returning
  `lambda shaft, sleeve: -2 * shaft * (sleeve > 0.5)`;
  `wrapped(source, target)` returning `lambda angle: 2 * wrap(angle, 360.0)`;
  `remainder_window(source, target)` returning
  `lambda angle: 4 + 72 * clamp01(((angle % 360) - 113.5) / 11.25)`;
  `reversing(source, target)` returning
  `lambda x: 5 * (x - 50.0) * sign(x - 50.0)` and `kinked(source, target)`
  returning `lambda x: 5 * abs(x - 50.0)` — the continuous twin it must
  match; `throwing(source, target)` returning
  `lambda x: 5 * x * sign(x - 50.0)`, a `sign` that genuinely jumps.
- [ ] 1.2 The nested law `alternating(source, target)`: `w = floor(angle / 360)`,
  `even = 1 - (w - 2 * floor(w / 2))`, returning
  `72 * clamp01((angle - 360 * w - 113.5) / 11.25) * even` — a jump node
  whose argument contains another, and mechanically the alternating
  engagement the Pascaline's column chain has.
- [ ] 1.3 The Pascaline-shaped carry, with the fixture's own round
  constants (`CARRY_OPEN = 100.0`, period `360.0`, `CARRY_THROW = 60.0`,
  `CARRY_SEGMENTS = ((100.0, 10.0, 20.0), (110.0, 40.0, 40.0))`,
  `DIGIT_STEP = 36.0`): `handed_on(wheel, lead)` with the module's own
  shape — `turns = floor((wheel - CARRY_OPEN) / 360.0)`,
  `phase = wheel - 360.0 * turns`, `advance = CARRY_THROW * turns`, then
  one `rise * clamp01((phase - start + lead) / width)` term per segment;
  `carried_column(sources, driven)` returning
  `lambda entry, below: DIGIT_STEP * entry + handed_on(below, 0.0)` and
  `carried_column_lead` the same with `lead=0.5`.
- [ ] 1.4 The only-jumps laws: `counter(source, target)` returning
  `lambda turns: floor(turns)`; `settled(sources, target)` returning
  `lambda enabled, turns: 9 * enabled + floor(turns)` — the Curta carry
  bench's shape, which must COMPILE.
- [ ] 1.5 The awkward laws: `moving_divisor(sources, target)` returning
  `lambda a, b: 0.5 * a + (a % b)`; `non_affine(sources, target)`
  returning `lambda a, b: a * floor(a * b / 100.0)`;
  `crowded(source, target)` returning
  `lambda a: clamp01(a - floor(a)) * 0.5`, whose period is one unit.
- [ ] 1.6 Running roots, each `time = Time.running()`, each with an
  untimed `...Body` twin where a test needs the untimed control:
  `Window` (`crank = Driver(default=100.0, unit='deg')`, `pinion = Arbor()`,
  `crank.drives(pinion.turn, law=periodic_window)`) — the pilot's
  illustration; `Remainder` (the same with `remainder_window`);
  `Wrapped`; `Reverser`, `Kinked`, `Throwing` (all
  `crank = Driver(default=40.0, unit='deg')`); `Alternating`
  (`crank = Driver(default=100.0)`).
- [ ] 1.7 `Clutch`: `shaft = Driver(default=10.0, unit='deg')`,
  `sleeve = Driver(default=0.0, unit='mm')`, `wheel = Arbor()`,
  `(shaft & sleeve).drives(wheel.turn, law=clutch)`.
- [ ] 1.8 `Carry` and `CarryLead`: `column = Driver(default=100.0, unit='deg')`,
  `tens_entry = Driver(default=0.0, unit='digit')`, `units = Arbor()`,
  `tens = Arbor()`, `column.drives(units.turn, ratio=1.0)`,
  `(tens_entry & units.turn).drives(tens.turn, law=carried_column)` —
  one driver and one JOINT COORDINATE as the two sources, which is the
  module's own shape.
- [ ] 1.9a `PortDriven`: a running root whose jumping law drives a PLAIN
  PORT wired to a joint (`register = RotationalPort(unit='deg')`,
  `register.drives(first.turn, ratio=1.0)`,
  `crank.drives(register, law=periodic_window)`) — the Pascaline
  module's own shape, and the case design.md §9a refuses; and
  `PortDrivenJoint`, the same relation stated into `first.turn`, which
  must compile.
- [ ] 1.9 `OnlyJumps` (`counter`), `Settled` (`settled`, two drivers),
  `Divisor` (`moving_divisor`, `a = Driver(default=10.0)`,
  `b = Driver(default=-2.0)`), `NonAffine` (`non_affine`,
  `a = Driver(default=10.0)`, `b = Driver(default=5.0)`), `Crowded`
  (`crowded`).
- [ ] 1.10 Every new fixture POSES UNTIMED at the base, unchanged: a
  parametrized case that builds each `...Body` (or the class with its
  `time` removed) and renders it at several driver values, recorded in
  `evidence.md` before any implementation. A jump law's untimed reading
  is not this cycle's business and must not move.

## 2. Red first

Write every case below and SEE IT RED before task 3. Paste the exact
red text of each into `evidence.md`. A case that is red for the wrong
reason (an import error where a wrong number was expected) is not
evidence; re-run it after the names exist.

- [ ] 2.0 The names do not exist yet: `TooManyCrossings`,
  `sim.crossings`, `JumpPlan`, `Edge.plans`. Record the
  `ImportError`/`AttributeError` for each, then write the behavioural
  cases so the eventual red text is a wrong ANSWER, not a missing name.
- [ ] 2.1 **(1) The periodic window gives 76 then 148.** `Sim(Window(), 1/240)`
  constructs (today it raises `UnsupportedLaw`); `sim.state['pinion.turn']`
  is `4.0`; `sim.move('crank', by=360, duration=1.0)` then `sim.run(1.0)`
  leaves it at `76.0`; a second identical move leaves it at `148.0`
  (`pytest.approx`, rel 1e-12). Assert the intermediate table of
  design §6 too: `13.6` after tick 10, `71.2` after tick 16, `76.0`
  from tick 17, `76.0` at tick 173, `76.0` at tick 174 — the crossing
  tick contributing exactly zero.
- [ ] 2.2 **(1b) The untimed reading is untouched.** `SteppedBody` and
  `WindowBody` pose exactly as at the base at a spread of crank angles,
  including 359.9 and 360.1.
- [ ] 2.3 **(2) The clutch.** With `Sim(Clutch(), 1.0)`: moving `shaft`
  by `4` over one tick with the sleeve at `0` leaves `wheel.turn`
  unchanged; from `Sim(Clutch(), 1.0, state={'sleeve': 1.0})` the same
  move gives `-8.0`; and from the sleeve at `0`, moving `shaft` by `4`
  AND `sleeve` by `1` over the SAME one tick gives exactly `-4.0` —
  the travel after engagement only, never the `-24` the gate factor
  would have jumped to.
- [ ] 2.4 **(3) Three teeth in one tick.** `Sim(Window(), 1/240)` with
  `sim.move('crank', by=1080, duration=0)` leaves `pinion.turn` at
  `220.0`, the crank at `1180.0`, and three crossings recorded at
  `t = 260/1080, 620/1080, 980/1080`.
- [ ] 2.5 **(4) A nested jump.** `Sim(Alternating(), 1/240)`: four
  moves of `360` leave the driven coordinate at `72`, `72`, `144`,
  `144`. Assert that the compiled plan holds TWO jump nodes and that
  the outer one's level quantity contributes no crossing of its own.
- [ ] 2.6 **(5a) `%` agrees with `floor`.** `Window` and `Remainder`
  stepped side by side through one revolution from `100` read the same
  driven value at EVERY tick.
- [ ] 2.7 **(5b) `sign`.** `Reverser` and `Kinked` stepped from `40`
  through `60` read the same driven value at every tick, the `sign`
  crossing having contributed nothing; `Throwing` over one tick from
  `40` to `60` gives the two segment contributions of design §6
  (`-50` then `+50`) and not the `500` jump.
- [ ] 2.8 **(5c) `wrap`.** `Sim(Wrapped(), 1.0)` moved `500` from `100`
  leaves the driven coordinate at exactly `1000.0`, and two `ceil`
  crossings are recorded.
- [ ] 2.9 **(6) The only-jumps refusal.** `Sim(OnlyJumps(), 0.1)`
  raises `UnsupportedLaw` naming the relation as written, the stating
  class, and saying the law can only jump and states arithmetic rather
  than a mechanism. `Sim(Settled(), 0.1)` CONSTRUCTS, and moving its
  `turns` driver alone moves the driven coordinate not at all while
  moving `enabled` by `1` moves it by `9`. `Sim(Window(), 0.1)`
  constructs — a periodic window is not a law that only jumps.
- [ ] 2.9a **(6b) A jumping law with nowhere to keep its history.**
  `Sim(PortDriven(), 0.1)` raises `UnsupportedLaw` naming the relation,
  the port and the stating class, and saying to state the relation into
  the joint coordinate the run owns; `Sim(PortDrivenJoint(), 0.1)`
  constructs. A CONTINUOUS law driving the same port still compiles —
  assert it, so the refusal is shown to be the jump's and not the
  port's.
- [ ] 2.10 **(7) The crossing record.** `Sim(Window(), 1/240, record=4)`
  run through six window boundaries leaves `sim.crossings` with exactly
  four entries, the last four, each naming the relation as written, the
  driven coordinate `pinion.turn`, `'floor'`, an integer level and a
  fraction in `[0, 1]`. `record=None` leaves `sim.crossings` empty after
  ten thousand ticks with `tracemalloc` flat. `reset()` clears it.
- [ ] 2.11 **(8) Display-cadence independence.** The same 360° of crank
  taken in 1, 12, 40 and 240 ticks leaves `pinion.turn` at the same
  value (`approx`, rel 1e-12), and so does 720° taken as one move or as
  two. This is the spike's "a fast crank movement must not skip an
  engagement between display frames", restated over ticks.
- [ ] 2.12 **(9) The large origin.** `Sim(Window(), 1/240, state={'crank': W * 360 + 100})`
  for `W` in `0, 1e3, 1e6, 1e9, 1e12, 1e13`: two turns leave
  `pinion.turn` at `144` above its rest value with a max per-tick
  deviation from the `W = 0` run of zero, and the table of design §11
  is written into `evidence.md`. At `W = 1e14`, where `ulp` exceeds the
  tick's own travel, the crank does not move at all: assert that
  explicitly as the BOUNDARY, and that it is the bank's resolution and
  not the crossing search.
- [ ] 2.13 **(10) The Pascaline-shaped carry.** `Sim(Carry(), 1.0)`
  moved `column` through two full revolutions (`720`, in ticks of `10`)
  leaves `tens.turn` at exactly `120.0` above its rest value — two
  throws — with `tens_entry` never commanded; moving `tens_entry` by
  `1` adds `36.0` on top. `CarryLead` gives `118.0` instead, the
  lead-induced jump being subtracted, and the test says so in a comment
  naming the module's own `0.136666…`.
- [ ] 2.14 **(11) Per-tick cost.** A probe in `evidence/` measuring
  `Train` (no jump — must come back within noise of task 0.3's number),
  `Window` on a non-crossing tick and `Window` on a crossing tick, each
  over 10 000 ticks with `tracemalloc`. RED is "the probe does not run";
  the NUMBER is evidence, not an assertion, except for one regression
  assertion on `Train`.
- [ ] 2.15 **(12) Every existing suite is the regression net.** Nothing
  in `tests/test_running_simulation.py`, `tests/test_simulation_*.py`,
  `tests/test_time_base.py`, `tests/test_couplings.py`,
  `tests/test_joints.py`, `tests/test_export.py` or
  `tests/test_motion_package.py` is edited except: the three cases named
  in 2.16, and ADDED cases.
- [ ] 2.16 The three cases cycle 1 wrote for the refusal change meaning:
  `CompileRefusalTest::test_a_jump_is_refused` becomes
  `test_a_jump_compiles` (the plan holds one `floor`, its level quantity
  is `crank / 360`, it is affine, and `SteppedBody` still poses
  unchanged); `test_a_law_with_a_kink_compiles` keeps its
  `assertNotIn('floor', ...)` on `Train` unchanged; the docs assertion in
  `tests/test_documentation.py`, if one pins the refusal list, is
  updated with task 5.2.
- [ ] 2.17 The compile plan itself: `Sim(Window(), 0.1).program` exposes,
  for the law edge, one jump node whose primitive is `'floor'`, level
  quantity affine, and a skeleton whose SCAD text no longer contains
  `floor`. `Sim(Alternating(), 0.1)` exposes two, in postorder.
- [ ] 2.18 The search path: `Sim(NonAffine(), 1.0)` with `a` moved from
  `10` to `30` over one tick (`b` at `5`) gives exactly `10.0`, the
  level quantity `a*b/100` being classified NON-affine and located by
  bisection; assert the classification as well as the number.
- [ ] 2.19 The two per-tick refusals: `Sim(Crowded(), 1.0)` moved `2000`
  in one tick raises `TooManyCrossings` naming the relation, the
  coordinate, `'floor'`, the count and the limit, with the bank, the
  tick and the tree unchanged and the move's handle `refused`;
  `Sim(Divisor(), 1.0)` moving `b` by `4` from `-2` raises the
  zero-divisor refusal naming the relation, with the same rollback.
- [ ] 2.20 Snapshot and restore across a crossing: a snapshot taken on
  the tick before a window boundary, restored, and re-run gives the same
  bank and the same crossings — the tick is a pure function of the bank
  and the commands, crossings included.
- [ ] 2.21 A jump in a BACKWARD-solved relation: a root whose law is
  solved backward by the rest render and whose `inverse` contains a
  `floor` integrates through the same machinery, the path being over the
  driven end's id.

## 3. The jump plan (`simulation/program.py`)

- [ ] 3.1 `_JUMP_CALLS`/`_JUMP_OPERATORS` become the RECOGNIZED set;
  `_graph_of` stops raising on them and returns `(GraphValue, plan)`,
  the plan `None` when the graph holds no jump node. `_law_graphs` and
  `Edge` carry `plans` beside `graphs`. Greens the compile half of 2.1,
  2.16 and 2.17.
- [ ] 3.1a `_relation_edge`: a law whose graph carries a jump and none of
  whose driven ends is a bank coordinate raises `UnsupportedLaw` with
  the message of design §9a. Greens 2.9a.
- [ ] 3.2 `_skeleton(root)`: the graph with every jump node replaced by
  `symbol('$j<k>')`, and every `%` node by `a - symbol('$q<k>') * b`,
  memoised BY NODE IDENTITY so a shared subgraph stays shared
  (`expression_graph.postorder` visits an identity once; ADR-080).
- [ ] 3.3 `_argument_graph(node)`: each jump node's level quantity of
  design §1 — the child for `floor`/`ceil`/`sign`, `a / b` for `%`,
  `a - b` for a comparison — with the jump nodes INSIDE it replaced by
  the same placeholders.
- [ ] 3.4 `_affine_in_sources(graph)`: the structural classification of
  design §4 (numbers, names, placeholders, unary minus, `+`/`-`, `*`
  with a constant operand, `/` by a constant operand; anything else not
  affine), computed once per argument graph.
- [ ] 3.5 `_only_jumps(root)`: the continuous skeleton of design §9 —
  every jump node AND ITS ARGUMENT SUBTREE replaced by a constant — and
  `free_names` over it; empty means refuse, with the message of §9 and
  the relation identity `_law_graphs` already has. Greens 2.9.
- [ ] 3.6 `JumpPlan.increment(start, delta, out)`: the partition of
  design §4 (postorder over jump nodes, midpoint branch sampling,
  affine solve or subdivision+bisection, merge within
  `_CROSSING_TOLERANCE`, `_MAX_CROSSINGS`), then the sum of design §3
  over the segments; appends `Crossing` entries to `out` when `out` is
  not `None`. `_CROSSING_TOLERANCE = 1e-12`, `_SUBDIVISIONS = 64`,
  `_BISECTION_ROUNDS = 64`, `_MAX_CROSSINGS = 1000`, each named and
  commented with §5's justification. Greens 2.1, 2.3–2.8, 2.11, 2.13,
  2.18.
- [ ] 3.7 `TooManyCrossings(CouplingError)` and the zero-divisor refusal,
  both raised from `JumpPlan.increment` naming the relation, the
  coordinate and the primitive. Greens the raising half of 2.19.
- [ ] 3.8 `Edge.increments(values, deltas, crossings=None)`: a graph with
  no plan keeps cycle 1's exact two evaluations — the branch must be the
  FIRST thing the method tests, so a continuous law pays nothing
  (design §12, measured by 2.14). A graph with a plan takes §3.6.

## 4. The run (`simulation/run.py`, `sim.py`, `__init__.py`)

- [ ] 4.1 `Run`: a second ring beside `self.ring`, the same `maxlen`,
  `None` when `record` is `None`; `Run.crossings`; `integrate` passes a
  fresh list into each edge and appends it to the ring only on COMMIT,
  so a refused tick records no crossing; `restore` clears both rings.
  Greens 2.10 and the rollback halves of 2.19.
- [ ] 4.2 `Run.integrate`: `TooManyCrossings` and the zero-divisor
  refusal are caught where `RunConflict` is raised, take `self._refuse(moved)`
  and re-raise, committing nothing. Greens 2.19.
- [ ] 4.2a `Run._values()` skips an edge whose targets are all bank keys
  (design §12): behaviour-neutral — the values were computed and
  discarded — and it removes one graph evaluation per law per tick from
  cycle 1's cost as well as this cycle's. Prove it neutral by the
  unchanged suite and measure it in 2.14.
- [ ] 4.3 `simulation/sim.py`: `sim.crossings` delegating to the run and
  refused under an untimed or looping root, naming `Time.running()`
  exactly as `sim.commands` does.
- [ ] 4.4 `simulation/__init__.py`: `_EXPORTS` gains `TooManyCrossings`
  and `Crossing` (lazy, from `program`). `docs/api-reference.rst`
  autoclass entries beside `UnsupportedLaw`.

## 5. Evidence and documentation

- [ ] 5.1 `evidence.md`: the base suite and base cost (0.2, 0.3), the
  `fmod`/`bool` probe (0.4), the untimed-pose table (1.10), the RED text
  of every case of section 2, the final suite counts, the per-tick cost
  table (2.14) beside cycle 1's 1.16 ms, the large-origin table (2.12),
  and the Pascaline lead finding (2.13) with the module's own
  `0.136666…` and the `65.403333…` it implies.
- [ ] 5.2 `docs/scenarios.rst`: the jump bullet LEAVES "What this release
  refuses"; a new subsection under "Running a machine that keeps its
  history" states the integrated reading of a jump with the Curta window
  and the clutch, names the five primitives and their surfaces, says
  that `wrap` and `piecewise` need nothing of their own, states the
  only-jumps refusal, the crossing record, the `_MAX_CROSSINGS` refusal
  and the resolution limit of a non-affine level quantity.
- [ ] 5.3 `docs/changelog.rst` entry; `docs/architecture.md` Simulation
  section's running paragraph gains the jump plan.
- [ ] 5.4 `workflow/open-run-simulation/roadmap.md`: record cycle 2 on
  the branch with its commit, its open questions, and the Pascaline lead
  finding as a note for the module's running migration.

## 6. Green and checked

- [ ] 6.1 Every case of section 2 green; every suite of 2.15 green with
  the same counts as 0.2 plus the added cases; no new `FutureWarning`.
- [ ] 6.2 The Curta bench's law and the Pascaline module's `handed_on`,
  copied verbatim into a throwaway probe under `evidence/` (never into
  the projects, never edited), compile and integrate. Record the numbers.
- [ ] 6.3 `openspec validate integrate-jumps --strict` passes.
- [ ] 6.4 Hand the implementation report to the adversarial review with
  `evidence.md`: name any deviation from `design.md` and why, and any
  scenario whose wording had to change to be testable.

## 7. After the code is green (the skill's own steps)

- [ ] 7.1 Extract the ONE ADR `design.md` §15 names — how a jump is
  integrated — under the next free number, citing this change; update
  `docs/adrs/README.md`.
- [ ] 7.2 Sync the delta spec into the baseline (`openspec-sync-specs`)
  and archive the change.
- [ ] 7.3 Record in `workflow/open-run-simulation/roadmap.md` that cycle 2
  is on the branch, with the commit, and list `design.md`'s open
  questions for the pilot. Nothing is pushed and nothing is integrated
  into any `main`.
