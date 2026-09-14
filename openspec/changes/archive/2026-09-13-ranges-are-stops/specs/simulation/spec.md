## MODIFIED Requirements

### Requirement: A continuous law is integrated over a tick and increments propagate

Under a running root the driven coordinate of a relation SHALL move BY the
change of its law along its sources' movement, from where it stood: over
one tick a CONTINUOUS law contributes exactly `f(end) − f(start)`, `f`
being the law's `forward` face — or its `inverse` face where the rest
render solved the relation backward — evaluated over the sources' values
at the start and at the end of the tick. This SHALL be exact across the
kinks of `abs`, `min` and `max` and of the compositions built on them
(`clamp`, `clamp01`, `ramp`, `piecewise`), because it is the difference
of two exact evaluations. A law whose increment is zero although its
source moved SHALL contribute nothing, which is what disengagement is.
A law whose expression contains a DISCONTINUOUS primitive SHALL
contribute the sum of its change over the continuous pieces between its
crossings, under the requirement "A jump is located inside the tick and
subtracted"; every other rule of this requirement applies to it
unchanged.

The tick SHALL be: every input's increment is the movement its active
command admits for the tick, zero with no command; increments SHALL then
propagate over the relation graph in the direction each relation was
solved by the rest render — forward through a law, backward through an
invertible one, identity through a wiring into a bank coordinate,
forward or backward through a derived coordinate's linear formula —
every source of a relation naming several being determined before it
contributes. A coordinate no increment reaches SHALL HOLD its committed
value. Two increments that disagree on one coordinate — beyond
`1e-9 · max(1, |a|, |b|)` — SHALL be a CONFLICT, refused naming the
formula or relation that predicted each and the coordinate. A joint
coordinate whose new value would leave its declared range SHALL NOT
fail the tick: it SHALL STOP at its bound under the requirement "A
declared range is a physical stop located inside the tick", which
splits the tick into segments and integrates each by this requirement
unchanged. A tick that fails
SHALL commit nothing: the bank, the tick count and the bound tree stand
as before, every segment of it included, and every command that moved
an input in that tick is
retired reporting `refused`. A tick that succeeds SHALL commit the
increments, advance the tick count, bind the whole snapshot through
`set_state` with `time` at `k*dt`, record if recording is on, and only
then run due actions and cadences.

Derived coordinates and plain ports SHALL NOT be stored: the ordinary
enumeration computes them from the run-bound terms on every tick.

#### Scenario: Moves accumulate and an affine chain follows

- **WHEN** a running root states `crank.drives(first.turn, ratio=2.0)`
  and `first.turn.drives(second.turn, ratio=-1.5)`, and the simulation
  moves `crank` by `10` over one second twice
- **THEN** the bank reads `crank == 20`, `first.turn == 40` and
  `second.turn == -60`, and the leaves stand at those angles

#### Scenario: A law with a kink integrates exactly

- **WHEN** `lever.drives(slide.travel, law=tooth_window)` carries
  `4 + 72 * clamp01((angle − 113.5) / 11.25)` and `lever` moves from
  `100` to `140` in eight ticks of five degrees
- **THEN** `slide.travel` reads exactly `13.6` after the third tick,
  `45.6` after the fourth, `76.0` from the fifth on, and stays `76.0`
  while the lever goes on to `140`

#### Scenario: Backward propagation through an invertible law

- **WHEN** a running root states `crank.drives(first.turn, ratio=2.0)`
  and `second.turn.drives(first.turn, ratio=4.0)`, so the rest render
  solved the second relation backward, and `crank` moves by `10`
- **THEN** `first.turn` reads `20` and `second.turn` reads `5`, the
  inverse of the affine law having propagated the increment

#### Scenario: An undriven joint holds while an unrelated input moves

- **WHEN** the crank of the same root moves while `lever` has no command
- **THEN** `slide.travel` and `lever` read exactly what they read before
  the move, on every tick

#### Scenario: Two inputs prescribing one rigid group inconsistently are refused

- **WHEN** a running root declares `wrist` and `tool` joints,
  `left = wrist + 2 * tool`, and states `wrist_in.drives(wrist)`,
  `wrist.drives(tool, ratio=1.0)` and `sum_in.drives(left)`, and the
  simulation moves `wrist_in` by `10` while `sum_in` has no command
- **THEN** the tick is refused naming `left`, the formula, the relation
  from `sum_in` and the two increments `0` and `30`; the bank, the tick
  count and the tree are unchanged; the move's handle reports `refused`
  with no travel admitted

#### Scenario: The same group moved consistently is admitted

- **WHEN** the same simulation moves `wrist_in` by `10` and `sum_in` by
  `30` over the same duration
- **THEN** every tick is admitted and the bank reads `wrist == 10`,
  `tool == 10` and the derived `left` reads `30`

#### Scenario: A joint's range stops the tick's motion rather than failing it

- **WHEN** `first.turn` declares `range=(-90, 90)` and the crank is moved
  so that `first.turn` would reach `100`
- **THEN** the tick commits with `first.turn` at exactly `90`, the tick
  count advances, and the move's handle reports `blocked` with the
  travel it admitted

### Requirement: Commands have one owner per input and report their outcome

Under a running root the system SHALL provide one path for every
movement request: `move(input, by=..., duration=...)`,
`move(input, to=..., duration=...)`, `rate(input, rate)` and
`trigger(name)`. `input` SHALL be the qualified id of a declared driver;
naming anything else — a joint coordinate, an unknown id — SHALL be
refused naming the id and the declared inputs. `by`, `to` and `rate` are
stated in the input's DESIGN units and converted through its declared
scale once; `rate` is design units per simulated second; `duration` is a
whole number of ticks, zero included. Exactly one of `by`/`to` SHALL be
given.

Each input SHALL have ONE OWNER at a time: a move or a rate on an input
that an active move or rate already owns SHALL be refused naming the
input and the owning command. `rate(input, 0)` SHALL release the active
rate, completing it, and SHALL be a no-op on an input no rate owns. A
REVERSE request — negative `by`, a `to` below the committed value, a
negative `rate` — SHALL be admitted and SHALL meet a declared range as
a physical stop exactly as a forward request does.

`move` and `rate` SHALL return a HANDLE reporting the input, the kind,
the status — `active`, `completed`, `blocked`, `refused` or `cancelled`
— the travel requested and the travel actually ADMITTED so far, in
design units, and offering `cancel()`. A request that fails validation SHALL
raise rather than return a handle; `refused` is the status of a command
whose tick failed, and `blocked` the status of one whose input was
stopped. Per-tick admission SHALL be a pure function of the
tick count since the command started: a move distributes its travel as
the ramp program does, integer-exact for an integer input and landing
exactly, in either direction; a rate admits the difference of its
cumulative travel at successive ticks, TRUNCATED TOWARD ZERO for an
integer input so that the two directions round alike. A zero-duration move
SHALL integrate at once at the current tick without advancing it.
A command whose input is STOPPED SHALL be retired reporting `blocked`,
with the travel it actually admitted — every completed tick's travel
plus the fraction of the stopping tick's travel it made before the
stop — and SHALL NOT resume: no travel it did not make is remembered
anywhere, and a later tick SHALL NOT continue it. A `rate` on a stopped
input SHALL be retired `blocked` in the same way. A new request on that
input SHALL be accepted at once, and SHALL be blocked again with `0`
admitted if it pushes into the same stop. A request that lands EXACTLY
on a bound SHALL report `completed`, the bounds being inclusive. Where
one instruction names several inputs, EACH command SHALL report for
itself and no instruction-level summary SHALL be owed: an instruction
one of whose inputs is stopped reports that handle `blocked` and the
others by their own outcome.

`sim.commands` SHALL be the active handles; a command SHALL be RETIRED
from them the tick it completes, blocks or is refused, so a long run
accumulates no finished
commands, while the handle the caller holds keeps reporting.

#### Scenario: A rate and a move on one input are an ownership conflict

- **WHEN** `rate('crank', 90.0)` is active and `move('crank', by=10, duration=1.0)`
  is requested, or two moves are requested on `crank`
- **THEN** the second request is refused naming `crank` and the owning
  command, and the first command keeps running

#### Scenario: A rate accumulates until released

- **WHEN** `rate('crank', 90.0)` runs for two seconds and `rate('crank', 0)`
  is then called
- **THEN** the crank has moved `180` and its joints followed, the handle
  reports `completed` with `180` admitted, and `sim.commands` is empty

#### Scenario: A reverse move runs

- **WHEN** `move('crank', by=-10, duration=1.0)`, `move('crank', to=5, duration=1.0)`
  from `20`, or `rate('crank', -90.0)` is requested on a crank meeting no
  stop
- **THEN** each runs, the bank and the driven coordinates follow
  backwards through the same laws, and each handle reports `completed`
  with its travel admitted

#### Scenario: A blocked command does not resume and reports its travel

- **WHEN** a move whose input is stopped part way through a tick is
  followed by ten more ticks with no new command
- **THEN** the handle reports `blocked` with the travel made up to the
  stop, `sim.commands` is empty, the coordinate stands at its bound
  through all ten ticks, and a new move on that input is accepted at once

#### Scenario: An instruction naming two inputs reports each for itself

- **WHEN** an instruction moves a stopped input and a free one over the
  same duration
- **THEN** its handle tuple holds one `blocked` handle with the fraction
  of its travel it made and one `completed` handle with all of its own,
  and the free input was not held back

#### Scenario: Only a declared input can be moved

- **WHEN** `move('first.turn', by=10, duration=1.0)` names a joint
  coordinate
- **THEN** it is refused naming `first.turn` and listing the declared
  inputs

#### Scenario: Completed commands are retired

- **WHEN** one hundred single-tick moves are issued one after another,
  each after the previous completed
- **THEN** `sim.commands` never holds more than one entry, every handle
  reports `completed`, and the crank has moved the sum of the travels

#### Scenario: A zero-duration move integrates now

- **WHEN** `move('crank', by=10, duration=0)` is requested at tick 20
- **THEN** the bank and the tree reflect the move at tick 20, the handle
  reports `completed`, and no tick was added

#### Scenario: A failed tick retires its commands as refused

- **WHEN** a move's tick is refused as a conflict
- **THEN** the handle reports `refused` with the travel admitted before
  that tick, `sim.commands` no longer holds it, and the run continues from
  the last committed bank once a consistent command is issued

### Requirement: Recording is explicit and bounded under a running root

Under a running root the simulation SHALL keep no per-tick record unless
asked: `Sim(..., record=None)` keeps nothing and `sim.trajectory` reads
empty; `record=N`, a positive integer, keeps a ring of the most recent
`N` `(tick, bank)` entries readable oldest first; any other value SHALL
be refused naming the option. Restore and reset SHALL clear the ring.
Unbounded recording SHALL NOT be offered under a running root.

`record=N` SHALL additionally keep a SECOND ring, of the most recent
`N` CROSSINGS located inside a tick, readable through `sim.crossings`
oldest first, each entry naming the tick, the relation as written, the
driven coordinate, the primitive that jumped, the surface value in the
level quantity's own units, and the fraction of the tick at which it
was crossed. Entries SHALL be appended in order of that fraction within
a tick, in the graph's postorder where two coincide, in program
order across relations, and segment by segment where a stop split the
tick — the recorded fraction being the fraction of the TICK in every
case, whichever segment located it. `record=None` SHALL keep no
crossings and build none.

`record=N` SHALL additionally keep a THIRD ring, of the most recent `N`
STOPS, readable through `sim.stops` oldest first, each entry naming the
tick, the coordinate that stopped, which bound it reached and that
bound's evaluated value, the fraction of the tick at which it was
reached, and the inputs the stop blocked. `record=None` SHALL keep no
stops and build none. A stop SHALL be appended only when the tick
commits. Restore and reset SHALL clear all three rings.

#### Scenario: Nothing is recorded by default

- **WHEN** a running simulation steps ten thousand ticks with no `record`
  option
- **THEN** `sim.trajectory`, `sim.crossings` and `sim.stops` are all
  empty and the run's memory does not grow with the tick count

#### Scenario: The stop ring names the coordinate, the bound and the inputs

- **WHEN** `Sim(node, dt, record=8)` drives a ranged coordinate into its
  bound
- **THEN** `sim.stops` holds one entry for that tick, naming the
  coordinate, the bound it reached, the bound's value, a fraction in
  `[0, 1]` and the inputs blocked, and a tick in which a stop is refused
  for another reason adds none

#### Scenario: The crossing ring names the relation and stays bounded

- **WHEN** `Sim(node, dt, record=4)` runs a periodic law through six
  window boundaries
- **THEN** `sim.crossings` holds exactly four entries, the last four,
  each naming the relation as written, the driven coordinate, `'floor'`,
  the integer surface it crossed and a fraction in `[0, 1]`

#### Scenario: A ring keeps the most recent ticks

- **WHEN** `Sim(node, dt, record=64)` steps one hundred ticks
- **THEN** `sim.trajectory` holds exactly sixty-four entries, for ticks
  37 through 100, oldest first

#### Scenario: An invalid recording option is refused

- **WHEN** `record=0`, `record=-1`, `record=True` or `record='all'` is
  given
- **THEN** construction is refused naming `record`

## ADDED Requirements

### Requirement: A declared range is a physical stop located inside the tick

Under a running root a banked joint coordinate's declared `range` SHALL
be a PHYSICAL STOP rather than a refusal: when the committed value of
the coordinate at the end of the stretch of tick being integrated would
lie outside one of its bounds AND lie further outside than the value it
held at the START of that stretch, the system SHALL
LOCATE the fraction `t*` of the tick at which the coordinate reaches
that bound and SHALL truncate that tick's motion there for the
coordinate and its group. A coordinate that does not move over a
stretch SHALL NOT stop in it. The tick SHALL COMMIT and the tick count
SHALL advance. Both bounds SHALL remain INCLUSIVE, so a tick landing
exactly on a bound SHALL NOT be a stop. A bound stated as `None` SHALL
be unbounded on that side and SHALL never stop anything.

Each bound SHALL be evaluated ONCE PER TICK, at the tick's START, from
the committed bank, so that every segment of one tick is measured
against the same number.

The coordinate's value along the tick SHALL be `v(0)` plus the
increment its DETERMINER gives over the tick's path truncated at `t` —
the same path, in the same joint source space, that a law is integrated
over, so that a law which jumps contributes its subtracted-jump
increment here too. `t*` SHALL be the SMALLEST fraction at which that
value reaches the bound, and SHALL be `0` when the coordinate already
stands at or beyond it. Where the determiner is AFFINE in its sources
along the path `t*` SHALL be SOLVED exactly, over the pieces of its own
jump partition where it has one; otherwise the value SHALL be sampled
at the same fixed number of sub-intervals a jump search uses and `t*`
bracketed and bisected to the same tolerance, with the same documented
limit. No further tolerance SHALL be introduced, and the stopped
coordinate SHALL be committed at its bound EXACTLY.

The GROUP a stop stops SHALL be every INPUT that reaches the stopped
coordinate through the compiled program AND whose own movement over the
stretch changes it — tested with that input's admission alone and every
other input's set to zero — together with everything those inputs alone
determine. An input that does not reach it, or reaches it only through
a law that contributes nothing to it over the stretch (a disengaged
coupling), SHALL run its full tick; a coordinate determined by both a stopped input and a free
one SHALL move by what the free one contributes after `t*`. The tick
SHALL therefore be integrated as SEGMENTS — `[0, t*]` with every
input's admission scaled by `t*`, then `[t*, 1]` with the stopped
inputs admitting nothing and the others scaled by `1 − t*` — each
segment by the ordinary tick procedure, its own jump partition
included.

The remaining segment SHALL then be examined for a further stop and the
process repeated, always taking the EARLIEST `t*` first. Two stops
whose fractions are within the crossing tolerance of each other SHALL
be ONE event, stopping the union of their groups at one boundary,
whether they are on one group or on two. A tick SHALL admit at most as
many stop events as it has inputs admitting travel, because each event
stops at least one moving input for the rest of that tick.

A tick SHALL remain ATOMIC across its segments: the bank, the commands'
admitted travel and the records SHALL be staged and applied only when
every segment has succeeded, and a conflict or an unintegrable law in
any segment SHALL commit nothing and retire the commands that moved as
`refused`, exactly as an unsegmented tick does.

Untimed and looping documents SHALL be unchanged: there a declared
range REFUSES a binding outside it and never clamps or stops.

#### Scenario: A rack stops at its bound while an independent motor continues

- **WHEN** a running root drives `rack.travel`, declaring
  `range=(None, 50)` and standing at `45`, from `steer` at ratio `1.0`,
  drives an unrelated `wheel.turn` from `motor` at ratio `3.0` under
  `rate('motor', 90)`, and `move('steer', by=10, duration=0.1)` is
  requested at `dt = 0.1`
- **THEN** the tick commits with `rack.travel` at exactly `50`, the
  steering handle reports `blocked` with `5.0` admitted of `10`
  requested, the wheel gains its full `27` degrees for that tick, and
  the rack does not move on any later tick

#### Scenario: A ratchet blocks reverse at the last seated tooth

- **WHEN** an input arbor declares
  `range=(lambda turn: 36 * floor(turn / 36), None)`, stands at `40`,
  and `move('arbor', by=-10, duration=0.1)` is requested at `dt = 0.1`
- **THEN** the tick commits with the arbor at exactly `36`, the handle
  reports `blocked` with `-4` admitted, and a further
  `move('arbor', by=-10, duration=0.1)` from `36` reports `blocked` with
  `0` admitted while a `move('arbor', by=4, duration=0.1)` completes

#### Scenario: A stop admits the same travel at any cadence

- **WHEN** the same reverse move of `-10` from `40` against the same
  ratchet is taken in one tick, in four and in forty
- **THEN** all three leave the arbor at exactly `36` and all three
  handles report exactly `-4` admitted

#### Scenario: A multi-source coordinate keeps moving on its free input

- **WHEN** `a_in` drives `c.turn` at ratio `1.0` with
  `range=(None, 10)` from `8`, `(a_in & b_in).drives(d.turn, law=2a+3b)`
  is stated, and one tick moves `a_in` by `4` and `b_in` by `6`
- **THEN** `c.turn` stops at `10` with `a_in` admitting `2`, `b_in`
  admits its full `6`, and `d.turn` gains exactly `22` rather than `26`

#### Scenario: Two stops in one tick are taken earliest first

- **WHEN** one tick would take a lever past its bound at a quarter of
  the tick and a rack past its own at half of it, on two groups that
  share no input
- **THEN** both commit at their bounds, both handles report `blocked`
  with the travel each made, and `sim.stops` holds two entries with the
  two fractions in that order

#### Scenario: A stop and a jump crossing in one tick

- **WHEN** a crank at `130` drives `first.turn` at ratio `1.0` with
  `range=(None, 145)` and drives `wrapped.turn` by
  `2 * wrap(angle, 90)`, whose fold falls at `135`, and one tick would
  move the crank by `20`
- **THEN** `first.turn` stops at `145`, `wrapped.turn` gains exactly
  `30`, the `wrap` crossing is recorded at the fraction `0.25` OF THE
  TICK — not at the `1/3` it sits at within the segment — the stop at
  `0.75`, and the handle reports `blocked` with `15` admitted

#### Scenario: A block replays identically from a snapshot

- **WHEN** a snapshot taken before a blocking tick is restored and the
  same command is issued again
- **THEN** the run blocks at the same coordinate value, admits the same
  travel and records the same stop; and a snapshot taken AFTER the block
  restores a run with no command on that input

#### Scenario: A tick that fails after a stop commits nothing

- **WHEN** the segment after a stop meets a conflict
- **THEN** the bank, the tick count and the tree stand as before the
  whole tick, no stop and no crossing is recorded, and the commands that
  moved retire `refused`

#### Scenario: A disengaged coupling does not stop its input

- **WHEN** a wheel with a declared upper bound is driven by
  `(push & crank & gate)` through `push + crank * (gate > 0.5)`, `crank`
  also drives an unrelated flywheel, the gate stands at `0`, and one tick
  moves `push` past the wheel's bound while `crank` moves too
- **THEN** the wheel stops at its bound, `push`'s command is retired
  `blocked` with the travel admitted before the stop, `crank`'s command
  runs its full tick and completes, and the flywheel gains the full
  tick's travel; with the gate at `1` the same tick retires both
  commands `blocked`
