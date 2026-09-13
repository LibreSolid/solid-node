## Why

Cycle 1 gave the run the coordinates and refused a reverse move,
saying so in the message: reverse travel meets no stop until a joint
range becomes a physical stop. Cycle 2 lifted the jump refusal and left
that one standing. This is the cycle that makes a range a stop, and it
is the cycle the campaign's acceptance project is waiting on.

Two mechanisms want it, one from the acceptance project and one from
the spike's evidence:

- **The Pascaline module's ratchet**
  (`projects/Calculators/Pascaline-module/.../simulation/`). The input
  arbor carries a ten-tooth ratchet — `DIGIT_STEP = 36.0`, ten faces on
  the number drum — against a flexible blade with no pawl lift. Forward
  rotation of the arbor is free; reverse rotation is blocked at the
  last seated tooth. Today the module cannot express that at all: the
  only joint on the arbor is `turn = Revolute(axis=(1, 0, 0))` with no
  range, and the blade is a `SignalPort` deflection, so nothing in the
  model blocks reverse. The project's own acceptance record says it
  outright — *"Validate ratchet admission/retention separately from the
  existing blade clearance samples; those samples do not prove reverse
  blocking"* — and its execution plan has one row, *"Ratchet retention
  through the range stop"*, depending on framework cycle 3. A detent is
  a force this kinematic model does not have; a stop at the last seated
  tooth is a kinematic statement of the same fact, and that is what a
  range evaluated at the committed state gives.
- **The spike's swept stop**
  (`workflow/open-run-simulation/spikes/kernel.py`, evidence report row
  *"Swept stop"*). A rack stops at its admitted limit even when a
  requested step extends beyond it, while an independent motor
  continues. The spike proved it with a unilateral coordinate stop, a
  blocked-group rule and a `blocked` status, and deliberately refused
  to auto-resume a blocked move. Its recorded gap is this cycle's
  obligation: *"precise fractional progress/replanning remains a
  required design item for production"* (`design.md`, spike
  recommendation).

Today neither is expressible. A joint range under a running root FAILS
THE WHOLE TICK: `Run._check_spans` raises `JointRangeError`, the tick
commits nothing, the bank stands at the last admitted tick, and every
command that moved retires `refused`. A machine that reaches a stop is
therefore a machine that cannot be stepped past it, which is not what a
stop is.

The authority is the pilot's decision of 2026-09-13 in
`workflow/open-run-simulation/design.md`, "a law is integrated, not
declared": item 6, *"In running mode a joint's `range` is a physical
stop, localized inside the tick, blocking the connected group while
unrelated drives continue. A range may be an expression over
coordinates evaluated at the committed state; a ratchet's lower bound
is the last seated tooth"*; item 7's commands reporting *"the travel
actually admitted"*; and the clause of item 5 this cycle lifts, *"A
reverse move on an input is refused until ranges become physical
stops"*. The cycle split is `roadmap.md`, "Execution, 2026-09-13": this
is cycle 3, it depends on cycle 2, and export (cycle 4) comes after.

## What Changes

- **A range is a physical stop, located inside the tick.** When a tick
  would leave a banked joint coordinate outside its declared range, the
  run LOCATES the fraction `t*` of the tick at which that coordinate
  reaches the bound, along the same path cycle 2 integrates over, and
  the coordinate stops there — committed AT its bound. The tick still
  commits, and the tick count still advances.
- **What stops with it is the connected group.** Every input that
  reaches the stopped coordinate through the compiled program stops at
  `t*` too, and so does everything those inputs alone determine. An
  input that does not reach it runs its full tick. A coordinate
  determined by both a stopped input and a free one keeps moving on
  what the free one contributes. The tick becomes two sub-ticks, `[0,
  t*]` and `[t*, 1]`, each integrated by exactly the procedure cycles 1
  and 2 already state; the second is examined for a further stop, and
  the earliest `t*` is always taken first.
- **A command on a stopped input is retired `blocked`,** with the
  travel it actually admitted — fractional within the tick — in design
  units. A `rate` on a stopped input is retired `blocked` too. A
  blocked command NEVER resumes by itself: the caller issues a new one,
  which may move away from the stop or push into it again and be
  blocked at once with `0` admitted. `blocked` is the word cycle 1
  reserved; no word is added to the vocabulary.
- **Reverse moves are admitted.** A negative `by`, a `to` below the
  committed value and a negative `rate` are no longer refused. Reverse
  travel meets a stop exactly as forward travel does. A rate's integer
  flooring becomes truncation toward zero, so the two directions round
  the same way.
- **A range bound may be an EXPRESSION over the joint's own
  coordinate,** written as a callable of one argument inside the pair —
  `range=(lambda turn: 36 * floor(turn / 36), None)` — and either bound
  may be `None` for unbounded on that side. Under a running root it is
  compiled once, like a law, and EVALUATED AT THE START OF EVERY TICK
  from the committed bank, so within a tick the bound is a number and
  the self-reference is well defined. Untimed and looping, it is
  evaluated at the value being bound, exactly as a number bound is
  compared against it. That is the ratchet: the last seated tooth.
- **Stops are recorded, bounded.** `record=N` keeps a THIRD ring,
  `sim.stops`, of the most recent `N` stops, each naming the tick, the
  coordinate, the bound reached, the fraction of the tick and the
  inputs the stop blocked. `record=None` keeps and builds none.

What does NOT change: untimed and looping documents, `Time(loop=)` and
the untimed meaning of a plain numeric range, which still REFUSES the
binding rather than clamping it; a `Driver`'s own `range`, which stays
presentation metadata and never a clamp; the bank, the binder, the
compile step, edge ordering, propagation, hold, conflict and rollback;
the other four command statuses and the one-owner rule; snapshot,
restore and reset; the document schema; and every rule of cycles 1 and
2 about jumps. A tick that fails still commits NOTHING, segments
included: a conflict, a `TooManyCrossings` or an unintegrable law in
any segment refuses the whole tick. No memory, no declared events, no
`Running` object, no new symbolic primitive, no export.

## Capabilities

### New Capabilities

None. A stop is a mode of the existing `simulation` capability over the
existing `joints` capability's declared range.

### Modified Capabilities

- `simulation`: the continuous-law requirement loses its
  "range fails the tick" clause and gains the sentence naming where a
  stop is answered; a new requirement states the localization, the
  group, the multi-stop order, the blocked reporting and the admitted
  travel; the commands requirement loses the reverse refusal and gains
  `blocked`; the recording requirement gains the stops ring and says
  how a segmented tick's crossings are ordered.
- `joints`: the range requirement gains the expression bound, the open
  bound and their meaning at binding time; the argument-resolution
  requirement gains the per-bound callable beside the whole-range one.

## Impact

- `solid_node/motion/joints.py`: `Joint._span` accepts `None` for
  either bound and a CALLABLE as either bound, carrying the callable
  through unevaluated instead of refusing it; the `lo <= hi` check
  moves to where both bounds are numbers; `_refuse_out_of_range`
  evaluates a callable bound AT THE VALUE BEING BOUND and refuses by
  name when the evaluated pair is reversed or not a number;
  `JointRangeError` prints the evaluated bound and the expression it
  came from.
- `solid_node/simulation/program.py`: `compile_program` resolves each
  banked coordinate's span and compiles a callable bound into an
  expression graph exactly as a law is compiled — applied once to a
  symbolic token, checked against `SYMBOLIC_BUILTINS`, jumps allowed
  because it is evaluated at one point and never integrated; `Program`
  carries `spans` and `sources` (the inputs reaching each node key, one
  pass over the ordered edges) and `described()` names each span, so a
  changed range changes the program identity a snapshot is checked
  against; `Edge` gains `affine`, the compile-time classification per
  driven end that decides whether a stop is SOLVED or SEARCHED;
  `JumpPlan.cuts()` exposes the partition the stop search brackets on;
  a new `Stop` record beside `Crossing`.
- `solid_node/simulation/run.py`: `Run.integrate` becomes a SEGMENT
  LOOP over one unchanged propagation pass — the pass is today's body,
  lifted — staging the bank, the admissions and the records until every
  segment has succeeded; `_spans` evaluated once per tick from the
  committed bank; `_locate` for `t*`; `_group` reading
  `program.sources`; `_block` retiring the group's commands as
  `blocked`; `_check_spans` becomes the detection that starts a stop
  instead of the refusal that ends a tick; `move` and `rate` lose the
  reverse refusals; `Command._cumulative` truncates toward zero; a
  third bounded ring and `Run.stops`.
- `solid_node/simulation/sim.py`: `sim.stops` delegating to the run and
  refused under an untimed or looping root as `sim.crossings` is.
- `solid_node/simulation/__init__.py`: `Stop` exported lazily beside
  `Crossing`.
- Tests: `tests/running_project/machine.py` gains the stop fixtures and
  `Ranged` changes meaning; a new `tests/test_running_stops.py`;
  `tests/test_running_simulation.py`'s reverse-refusal test and
  `RangeTest` are rewritten to the new behaviour; the joints suite
  gains the expression-bound and open-bound cases; every other suite
  unchanged.
- Docs: `docs/scenarios.rst` ("Running a machine that keeps its
  history" — the reverse-move and range bullets leave "What this
  release refuses" and a subsection states stops, blocked commands and
  the ratchet), `docs/api-reference.rst`, `docs/changelog.rst`,
  `docs/architecture.md` (the Simulation section's running paragraph).
- Projects: none edited here. The Pascaline module's ratchet retention
  is its own change in its own repository, which this cycle unblocks.
