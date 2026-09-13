## 0. Before anything

- [ ] 0.1 Work only in `solid-node/WTs/open-run-simulation` (branch
  `open-run-simulation`, base `8019c6d`), with `PYTHONPATH="$PWD"` and the
  workspace venv `/home/asa/devel/libresolid-studio/.venv/bin/python`.
  Confirm `git rev-parse --show-toplevel` prints that worktree and
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path. Never write inside
  `/home/asa/devel/libresolid-studio/projects/` and never write in the
  pilot's primary `solid-node/` checkout.
- [ ] 0.2 Record the FULL SUITE at the base (`python -m pytest -x -q`),
  exact counts, into `evidence.md`, beside cycle 2's recorded 2380
  passed / 4 skipped / 1245 subtests. Any failure here is pre-existing
  and must be shown to be so before task 7.
- [ ] 0.3 Record the BASE per-tick cost by re-running cycle 1's probe,
  `openspec/changes/archive/2026-09-13-run-owns-the-coordinates/evidence/probe_cost.py`,
  on this worktree. Paste the output into `evidence.md`. It is the
  1.07 ms this cycle is answerable to (design §15).
- [ ] 0.4 Probe and paste: that `Joint._span` today REJECTS `None` as a
  bound and EVALUATES a callable bound (so both are new), that
  `RampProgram` with a NEGATIVE delta lands exactly on its target at
  `k == ticks` for both dtypes, and that `solid_node.math.floor`
  applied to a float returns a number while applied to `symbol('turn')`
  it builds a `floor` call node. These are the three facts design §8
  and §9 are written against.

## 1. The fixtures: `tests/running_project/machine.py`

Project-style code, no meshes. Everything below is added beside the
existing fixtures; `Ranged` CHANGES MEANING and keeps its name, so the
disappearance of the refusal is visible in the diff.

- [ ] 1.1 `Ratchet`: a running root with `arbor = Driver(default=40.0,
  unit='deg')` driving `wheel.turn` at ratio `1.0`, the joint declared
  `Revolute(axis=(1, 0, 0), range=(lambda turn: 36 * floor(turn / 36), None),
  unit='deg')`. The rest pose must be admissible at `40` (it is:
  `36 * floor(40 / 36) == 36 <= 40`).
- [ ] 1.2 `Swept`: a running root with `steer` driving
  `rack.travel` at ratio `1.0`, the joint
  `Prismatic(axis=(1, 0, 0), range=(None, 50.0), unit='mm')` resting at
  `45`, and `motor` driving an UNRELATED `wheel.turn` at ratio `3.0`.
  Two inputs, two groups, nothing shared.
- [ ] 1.3 `Shared`: a running root with `a_in` driving `c.turn` at
  ratio `1.0`, `c.turn` declaring `range=(None, 10.0)` and resting at
  `8`, plus `(a_in & b_in).drives(d.turn, law=summed)` where
  `summed` returns `lambda a, b: 2 * a + 3 * b`. `b_in` reaches `d.turn`
  and not `c.turn`.
- [ ] 1.4 `TwoStops`: a running root with two independent groups — a
  lever bounded at `20` resting at `18` driven by `lever_in`, and a rack
  bounded at `50` resting at `45` driven by `steer` — so one tick can
  reach both bounds at different fractions.
- [ ] 1.4b `OpenGate`: a running root with inputs `push`, `crank` and
  `gate`; `(push & crank & gate).drives(wheel.turn, law=gated)` where
  `gated` returns `lambda p, c, g: p + c * (g > 0.5)`, `wheel.turn`
  declaring `range=(None, 20.0)` and resting at `15`; and
  `crank.drives(flywheel.turn, ratio=1.0)`.
- [ ] 1.5 `StopAndJump`: a running root whose `crank` rests at `130`,
  drives `first.turn` at ratio `1.0` with `range=(None, 145.0)`, and
  drives `wrapped.turn` by `lambda angle: 2 * wrap(angle, 90.0)`, whose
  fold falls at `135` — the jump crossing falling BEFORE the stop at
  crank `145`.
- [ ] 1.6 `Ranged` rewritten: keep `crank.drives(first.turn, ratio=2.0)`
  and `range=(-90, 90)`, and add a sibling `RangedExact` whose move
  lands `first.turn` on exactly `90`.
- [ ] 1.7 `Curved`: a running root whose ranged coordinate is driven by
  a NON-AFFINE law (`lambda x: 40 * sin(x)` over a `Revolute` bounded at
  `20`), to exercise the sampled-and-bisected path of design §2 case 3.
- [ ] 1.8 `Lifted`: the shape a bound over a SECOND coordinate would
  take, written as a comment and a skipped test naming design §10, so
  the deferral is recorded in the suite rather than only in prose. No
  framework support is added for it.
- [ ] 1.9 An UNTIMED control for each new fixture that has one, so the
  untimed reading is asserted unchanged beside the running one.

## 2. Red first

Write every case below and SEE IT RED before task 3. Paste the exact
red text of each into `evidence.md`. A case red for the wrong reason (an
import error where a wrong number was expected) is not evidence;
re-run it after the names exist.

- [ ] 2.0 The names do not exist yet: `sim.stops`, `Stop`,
  `Program.sources`, `Edge.affine`, `JumpPlan.cuts`. Record the
  `ImportError`/`AttributeError` for each, then write the behavioural
  cases so the eventual red text is a wrong ANSWER, not a missing name.
- [ ] 2.1 **(1) Reverse moves are admitted.** On `Train`:
  `move('crank', by=-10, duration=1.0)`, `move('crank', to=5,
  duration=1.0)` from `20` and `rate('crank', -90.0)` each RUN; the bank
  and the driven coordinates follow backwards through the same laws; each
  handle reports `completed` with its travel. This is
  `test_a_reverse_request_is_refused` rewritten: it must be seen red as
  a wrong ANSWER (the refusal) before it is green.
- [ ] 2.2 **(1b) A reverse rate on an INTEGER input truncates toward
  zero.** A `dtype=int` input under `rate(input, -1.5)` at `dt = 1.0`
  stands at `-1, -3, -4, -6` over four ticks, not at the `-2, -3, -5, -6`
  flooring gives; the positive rate's existing sequence is unchanged,
  asserted in the same test.
- [ ] 2.3 **(2) The ratchet, the whole worked example of design §11.**
  On `Ratchet` at `dt = 0.1`: `by=+20` in one tick completes and leaves
  `60`; from `40`, `by=-10` in one tick leaves the arbor at EXACTLY
  `36.0`, the handle `blocked` with `admitted == -4.0`, the tick count
  advanced, `sim.commands` empty; from `36`, `by=-10` leaves `36.0` with
  `admitted == 0.0` and status `blocked`; `by=+4` from `36` completes at
  `40`; and a further `by=-10` blocks again at `36.0` with `-4.0`. Also
  assert the tooth advances: from `75` the block is at `72.0`.
- [ ] 2.4 **(3) The swept stop.** On `Swept` at `dt = 0.1` with
  `rate('motor', 90)` running: `move('steer', by=10, duration=0.1)`
  leaves `rack.travel` at exactly `50.0`, the steering handle `blocked`
  with `5.0` admitted, `wheel.turn` up by exactly `27.0` for that tick,
  and the motor's handle still `active`. Ten further ticks leave the rack
  at `50.0` and go on turning the wheel.
- [ ] 2.5 **(4) Landing exactly on the bound completes.** On
  `RangedExact`, the move that puts `first.turn` on exactly `90.0`
  reports `completed`, `sim.stops` is empty and no tick was refused. On
  `Ranged`, the move that would take it to `100` now COMMITS with
  `first.turn` at `90.0` and the handle `blocked` — this is `RangeTest`
  rewritten, and its old `JointRangeError` assertion must be seen red.
- [ ] 2.6 **(5) A push into a stop from the stop.** Covered by 2.3's
  third row; assert additionally that the new command is ACCEPTED (no
  ownership error), that it retires in the same tick it was issued, and
  that `sim.stops` gains an entry with `t == 0.0`.
- [ ] 2.7 **(6) A multi-source coordinate with one input stopped.** On
  `Shared`, one tick moving `a_in` by `4` and `b_in` by `6` leaves
  `c.turn` at exactly `10.0`, `a_in`'s handle `blocked` with `2.0`
  admitted, `b_in`'s handle with its full `6.0`, and `d.turn` up by
  exactly `22.0` — not `26.0`, and not `13.0`.
- [ ] 2.8 **(7) Two stops in one tick.** On `TwoStops`, one tick that
  would take the lever by `8` and the rack by `10` leaves both at their
  bounds (`20.0`, `50.0`), both handles `blocked` with `2.0` and `5.0`
  admitted, and `sim.stops` holding two entries at `t == 0.25` and
  `t == 0.5` in that order. Assert the same answer when the two moves
  are issued in the opposite order, so nothing depends on command order.
- [ ] 2.9 **(8) A stop and a jump crossing in one tick.** On
  `StopAndJump`, one tick moving the crank by `20` leaves `first.turn`
  at exactly `145.0`, `wrapped.turn` up by exactly `30.0`, the handle
  `blocked` with `15.0` admitted; with `record=8`, `sim.crossings` holds
  ONE entry whose `t` is `0.25` — the fraction OF THE TICK, not the
  `1/3` it sits at within the segment — and `sim.stops` one entry at
  `0.75`.
- [ ] 2.10 **(9) Snapshot and restore across a block.** A snapshot taken
  BEFORE the blocking tick, restored, then re-run with the same command,
  blocks at the same value, admits the same travel and records the same
  stop. A snapshot taken AFTER the block restores a run whose
  `sim.commands` is empty and whose bank stands at the bound; the
  original handle still reports `blocked` with its travel. `reset()`
  returns to the rest pose and clears all three rings.
- [ ] 2.11 **(10) The untimed meaning of an expression range.** The
  untimed control of `Ratchet` poses at `0`, `36`, `40`, `359` and
  `-720` without refusal, because the bound evaluates at the value being
  bound; a joint declaring `range=(lambda turn: turn + 1, None)` refuses
  EVERY binding naming the joint, the value and the evaluated bound; a
  joint declaring `range=(0, None)` accepts `10000` and refuses `-1`;
  and the existing numeric-range refusal tests are unchanged.
- [ ] 2.12 **(11) A stop's record.** With `record=4`, six stops leave
  exactly the last four entries, each naming the tick, the coordinate,
  which bound, the bound's value, `t` in `[0, 1]` and the inputs
  blocked; with `record=None`, `sim.stops` is empty and no ring is
  built; under an untimed or looping root `sim.stops` raises the same
  way `sim.crossings` does.
- [ ] 2.13 **(12) Cadence independence.** The same reverse move of `-10`
  from `40` against the ratchet, taken in 1, 4 and 40 ticks, leaves the
  arbor at exactly `36.0` and admits exactly `-4.0` in all three, with
  the block falling on tick 1, 2 and 17 respectively and `t*` reading
  `0.4`, `0.6` and `0.0`. Assert the 40-tick run's tick 16 is ORDINARY
  (lands on `36.0`, status still `active`, no stop recorded).
- [ ] 2.14 **(6b) A stop on a NON-AFFINE chain is found by search.** On
  `Curved`, the tick that would take the coordinate past `20` leaves it
  at exactly `20.0` and the located `t` matches a separately computed
  root to `1e-9`. Assert the affine fixtures do NOT take that path (the
  classification is asserted directly off `Edge.affine`).
- [ ] 2.15 **(A tick that fails after a stop commits nothing.)** A
  fixture whose segment after the stop raises `RunConflict` leaves the
  bank, the tick count and the tree as before the WHOLE tick, records no
  stop and no crossing, and retires the commands that moved as
  `refused`.
- [ ] 2.16 **(The group is the program's, not the tree's.)** Assert
  `sim.program` exposes, for the stopped coordinate, exactly the inputs
  design §3 names — on `Swept` the steering input alone, on `Shared`
  `a_in` alone — and that `motor` and `b_in` are absent from them.
- [ ] 2.16b **(The group is who pushes.)** On `OpenGate` with the gate at
  `0`: `move('push', by=10, duration=1.0)` and `move('crank', by=30,
  duration=1.0)` in one tick of `dt=1.0` → `wheel.turn == 20`, `push`'s
  handle `blocked` with `5` admitted, `crank`'s handle `completed`,
  `flywheel.turn` gained `30`; with the gate at `1` (`state=`) the same
  tick retires both `blocked` and the flywheel gains what `crank`
  admitted before the stop. RED: a static group blocks `crank` in the
  first case.
- [ ] 2.17 **(14) Every existing suite unchanged.** Run
  `tests/test_running_simulation.py`, `tests/test_running_jumps.py`, the
  joints suites, the couplings and kinematics suites and the full suite;
  the only changes are 2.1 and 2.5's rewritten cases and the added ones.

## 3. The compile (`simulation/program.py`)

- [ ] 3.1 `Program.sources`: the inputs reaching each node key, one pass
  over the already ordered edges, a `check` edge contributing nothing.
  Frozensets, built once. This is the CANDIDATE table; the group of a
  stop is decided per stretch by the contribution test of design §3,
  in `run.py` (task 4.x), one sub-program propagation per candidate
  with a nonzero admission, on blocking ticks only.
- [ ] 3.2 `Edge.affine`: one flag per driven end, from
  `_affine_in_sources` over the graph for a continuous law and over the
  SKELETON for a jump-carrying one; `True` for a wiring and a formula
  edge, which are linear by construction.
- [ ] 3.3 `JumpPlan.cuts(start, delta, ...)`: `_partition` made
  reachable, with no recording, so a stop search can bracket on the
  pieces a jump law already has.
- [ ] 3.4 The span table: `compile_program` resolves every banked
  coordinate's declared range once and carries `(low, high, unit)` per
  coordinate, each bound a number, `None`, or a compiled GRAPH. A
  callable bound is applied ONCE to `symbol(qualified_id)` and its graph
  checked exactly as a law's is — raw text and calls outside
  `SYMBOLIC_BUILTINS` refused by joint and node identity — with jump
  nodes ADMITTED and no plan built.
- [ ] 3.5 `Program.described()` names each coordinate's span, so a
  changed range changes the identity a snapshot is checked against.
  Assert an identity change in the tests.
- [ ] 3.6 The `Stop` record beside `Crossing`: tick, coordinate, which
  bound, the bound's value, `t`, and the inputs blocked.

## 4. The joint (`motion/joints.py`)

- [ ] 4.1 `_span` accepts `None` for either bound and a CALLABLE as
  either bound, returning the pair as declared without evaluating it;
  everything else resolves as today. The `lo <= hi` check applies where
  both bounds are numbers.
- [ ] 4.2 `_refuse_out_of_range` applies a callable bound to the value
  being bound, refuses a non-number or reversed evaluated pair by name,
  and treats `None` as unbounded on that side. The message names the
  evaluated bound.
- [ ] 4.3 No import of the simulation layer, asserted by the existing
  import-boundary test if there is one and by inspection otherwise.

## 5. The tick (`simulation/run.py`, `sim.py`, `__init__.py`)

- [ ] 5.1 Lift `integrate`'s current body into `_pass(values, deltas,
  found, tick)`, returning the increments — unchanged behaviour, same
  conflict tests, same exceptions. Commit this refactor with its own
  green suite before anything new uses it.
- [ ] 5.2 The per-tick span evaluation: each bound evaluated once, at
  the tick's start, from the committed bank.
- [ ] 5.3 `_locate`: design §2's three cases, reusing
  `_CROSSING_TOLERANCE`, `_SUBDIVISIONS` and `_BISECTION_ROUNDS` and no
  new tolerance.
- [ ] 5.4 The segment loop: detection by the committed value and the
  direction test, the earliest `t*`, ties within the tolerance as one
  event, the staged bank/admissions/records, the stopped coordinate
  committed at its bound, the input-count iteration bound.
- [ ] 5.5 `_block`: retire every active command whose input is in the
  union of the stopped groups as `blocked`, with its accumulated
  admitted travel, releasing ownership.
- [ ] 5.6 `move` and `rate` lose the reverse refusals;
  `Command._cumulative` truncates toward zero.
- [ ] 5.7 The third ring, `Run.stops`, cleared by restore and reset with
  the other two; `sim.stops` on `Sim`, refused under an untimed or
  looping root; `Stop` exported lazily from
  `solid_node/simulation/__init__.py`.
- [ ] 5.8 The crossing fraction rescaled to the TICK when a segment
  records it.

## 6. Evidence and documentation

- [ ] 6.1 `evidence/probe_cost.py` re-run and a new
  `evidence/probe_stop_cost.py` measuring, on the same host and method:
  one `Train` tick (no ranged coordinate) against the recorded 1.07 ms;
  one tick of a ranged machine that does NOT block; one tick that
  blocks on an affine chain; one that blocks on `Curved`. Paste all four
  into `evidence.md` against design §15's expectations, and state any
  regression on the unranged tick honestly.
- [ ] 6.2 `evidence/probe_projects.py` extended: the Pascaline module's
  own laws and the Curta bench's window, copied verbatim into a
  throwaway probe (never into the projects, never edited), still compile
  and integrate, and the module's `input.turn` with the ratchet bound
  added blocks reverse where design §11 says it does.
- [ ] 6.3 `docs/scenarios.rst`: the reverse-move and range bullets leave
  "What this release refuses"; a subsection states stops, the group,
  `blocked`, the admitted travel and the ratchet declaration.
  `docs/api-reference.rst` gains `sim.stops` and the expression bound;
  `docs/changelog.rst` and `docs/architecture.md` follow.
- [ ] 6.4 `workflow/open-run-simulation/design.md` is NOT edited: it is
  the pilot's record, and this change's design is this file's sibling.

## 7. Green and checked

- [ ] 7.1 Every case of section 2 green; the full suite green with the
  counts of 0.2 plus the added cases; no new `FutureWarning`.
- [ ] 7.2 `openspec validate ranges-are-stops --strict` passes.
- [ ] 7.3 Hand the implementation report to the adversarial review with
  `evidence.md`: name any deviation from `design.md` and why, and any
  scenario whose wording had to change to be testable.

## 8. After the code is green (the skill's own steps)

- [ ] 8.1 Extract the TWO ADRs `design.md` §18 names — a range is a
  physical stop that stops the connected group; a range bound may be an
  expression evaluated at the committed state — under the next free
  numbers, citing this change; update `docs/adrs/README.md`.
- [ ] 8.2 Sync the delta specs into the baselines (`openspec-sync-specs`)
  and archive the change.
- [ ] 8.3 Record in `workflow/open-run-simulation/roadmap.md` that cycle
  3 is on the branch, with the commit, and list `design.md`'s open
  questions for the pilot. Nothing is pushed and nothing is integrated
  into any `main`.
