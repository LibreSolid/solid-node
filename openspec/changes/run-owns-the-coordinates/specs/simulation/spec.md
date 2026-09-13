## MODIFIED Requirements

### Requirement: Instructions carry design-unit targets

The system SHALL let an assembly declare named instructions:
`Instruction(targets, duration)` with targets keyed by driver name and
expressed in design units, or `Instruction(by=..., duration)` with
RELATIVE travel keyed the same way and expressed in the same units. An
instruction SHALL state exactly one of `targets` and `by`; both, or
neither, SHALL be refused at declaration naming the rule, and the one
given SHALL read back off the declaration with the other reading `None`.
An instruction duration SHALL be a finite real
number of seconds greater than or equal to zero. Instructions declared on any
node in the tree SHALL be discoverable and triggerable through the simulation
by qualified name — the declaring node's instance path joined with the
instruction name, with root-declared instructions keeping their bare names —
and each instruction's local target names SHALL resolve to the declaring
node's qualified driver ids. Triggering an instruction SHALL convert each
target, or each relative travel, to native driver state through that
driver's declared scale (rounding
to the nearest native unit for an integer-typed driver; a driver with no scale
takes the value verbatim) and start a ramp program over the instruction's
duration: a `targets=` ramp lands on the converted target, a `by=` ramp
lands on the driver's current value plus the converted travel, and either
replaces whatever ramp the driver was running. Under a root declaring
`Time.running()` triggering SHALL instead issue the run's own commands —
`targets=` as a move TO each target and `by=` as a move BY each travel,
under the requirement "Commands have one owner per input and report their
outcome" — claiming every input the instruction names before starting
any, so an ownership conflict refuses the whole instruction and starts
nothing. A zero-duration instruction SHALL reach every target and bind the
complete node snapshot immediately at the current tick, without advancing the
clock or adding a trajectory entry. Triggering an unknown name SHALL fail
listing the known qualified instruction names. Instruction semantics are held
to target-plus-duration and travel-plus-duration linear ramps; sequencing
and richer programs are explicitly out of scope. The serialized document's
instructions table SHALL OMIT a relative instruction until a later change
publishes the compiled program under a new schema version, because the
shipped viewer reads `targets` off every entry; a root whose instructions
are all relative SHALL publish an empty table, and the rest of the
document SHALL be unchanged.

#### Scenario: Millimetre target reaches a microstep driver

- **WHEN** an instruction targets `x=0` (mm) for a driver declared
  with `scale` millimetres-per-microstep and dtype `int`
- **THEN** the ramp's native target is 0 microsteps and intermediate
  states are whole microsteps

#### Scenario: A child's instruction homes only that child

- **WHEN** both axis instances declare `'Home': Instruction({'motor':
  0.0}, duration=2.0)` and the scenario triggers `x_axis.Home`
- **THEN** only `x_axis.motor` ramps to its native target while
  `y_axis.motor` holds its state

#### Scenario: A zero-duration instruction settles now

- **WHEN** an instruction with duration zero is triggered at tick 20
- **THEN** its targets are immediately visible in `sim.state`, the bound node,
  and a later deferred action at tick 20
- **AND** the simulation remains at tick 20 with no new trajectory entry

#### Scenario: An invalid instruction duration is refused

- **WHEN** an instruction is declared with a negative, infinite, NaN,
  boolean, or non-numeric duration
- **THEN** construction raises `ValueError` naming the duration

#### Scenario: A relative instruction ramps from where the driver stands

- **WHEN** an untimed root declares
  `'Advance': Instruction(by={'motor': 10.0}, duration=1.0)` over a scaled
  integer driver and the scenario triggers it twice, one second apart
- **THEN** after two seconds the driver stands at its start plus twice the
  travel converted through its scale, every intermediate state a whole
  native unit, and `Instruction.by` reads `{'motor': 10.0}` while
  `Instruction.targets` reads `None`

#### Scenario: An instruction names exactly one of targets and by

- **WHEN** an instruction is declared with both `targets` and `by`, or with
  neither
- **THEN** declaration raises naming the rule

#### Scenario: Under a running root an instruction is a move

- **WHEN** a root declaring `Time.running()` declares
  `'Park': Instruction({'crank': 40.0}, duration=0.5)` and
  `'Advance': Instruction(by={'crank': 10.0}, duration=0.5)`, and the
  simulation triggers `Park` and then, once it completes, `Advance`
- **THEN** the crank moves from its committed value to `40` over the first
  half second and from `40` to `50` over the next, every joint coordinate
  its relations reach follows by increments, and each trigger issued one
  command whose handle reports `completed`

#### Scenario: A relative instruction is not yet published

- **WHEN** a root declares `'Advance': Instruction(by={'crank': 10.0}, duration=0.5)`
  beside `'Park': Instruction({'crank': 40.0}, duration=0.5)` and is
  serialized
- **THEN** the instructions table carries `Park` with its targets and no
  entry for `Advance`, and the document is otherwise the one the root
  publishes without `Advance`

#### Scenario: An instruction whose input is owned starts nothing

- **WHEN** a rate command is active on `crank` and an instruction naming
  `crank` and a second input is triggered
- **THEN** the trigger is refused naming `crank` and the owning command,
  and no command was started on either input

### Requirement: Fixed-dt stepping loop with deferred actions

The system SHALL provide a simulation loop constructed over one assembly and
a fixed `dt`, which SHALL be a finite real number of seconds strictly greater
than zero and SHALL be validated before any node state is bound. On
construction it SHALL enumerate declared drivers across the whole linked tree
and bind every driver's default through `set_state` by qualified id, so a
state-consuming assembly — including one whose drivers live only on
descendants — renders under a complete snapshot from the first render.
`Sim(node, dt, meshes=False, state=None, record=None)`: `state` MAY give
initial values for declared drivers by qualified id, bound over the declared
defaults before that first render; a name in it that is not a declared driver
id SHALL be refused as `set_state` refuses it, and a joint coordinate id SHALL
be refused too, because initial coordinates come from the rest pose. Each
tick SHALL: advance every driver's program, bind the full snapshot via
`set_state` together with the global `time` entry set to the exact simulation
instant in seconds (`k*dt`, computed from the integer tick count, never
accumulated), record the tick and snapshot in a trajectory keyed by qualified
id, then run due deferred actions and cadence actions. Under a running
simulation, `self.time` therefore reads the stepped simulation clock; the
normalized symbolic `$t` animation path outside simulations is unchanged.

Under a root declaring `Time.running()` construction SHALL continue as the
requirement "A running root's simulation owns every driver and joint
coordinate" states, each tick SHALL be the tick the requirement "A
continuous law is integrated over a tick and increments propagate" states,
and the trajectory SHALL be the bounded recording the requirement
"Recording is explicit and bounded under a running root" states. Under any
other root `record` SHALL be ignored, the trajectory SHALL append every
tick as it does today, and the running-only surface — `move`, `rate`,
`commands`, `snapshot`, `restore`, `reset`, `initial`, `program` — SHALL be
refused naming `Time.running()`; `sim.running` SHALL report which case
holds.

Instants, cadence periods, and run durations SHALL be finite real seconds and
SHALL be validated as whole numbers of ticks (`round(t/dt)*dt == t` within
float tolerance), represented as integer tick counts rather than accumulated
floats. `run(duration)` SHALL require a nonnegative duration and SHALL reject
an invalid duration before firing actions or changing simulation state.
`at(t)` SHALL treat `t` as an absolute instant, reject a tick before the
current simulation tick, and accept the current tick, whose actions run in the
existing pre-step phase of the next `run()` including `run(0)`. Scheduled
actions SHALL be deferred callables — `at(t).trigger(name)` and
`at(t).run(fn)` where `fn` receives the simulation — never eagerly evaluated
expressions. `every(period, fn, *args)` SHALL require a positive period of at
least one whole tick, run `fn` at the declared tick cadence, and account its
cost per slot, so scenario reports can state assertion cost separately from
stepping cost.

#### Scenario: Non-whole instants are rejected

- **WHEN** `at(0.05)` is requested on a simulation with `dt=0.02`
- **THEN** the call fails naming the instant and `dt`

#### Scenario: Defaults bind before first render

- **WHEN** a simulation is constructed over an assembly whose
  `render()` reads a declared driver
- **THEN** construction succeeds with the declared default bound, with
  no unbound-state error

#### Scenario: A driverless root with driver-declaring children simulates

- **WHEN** a simulation is constructed over a root declaring no
  drivers whose two children each declare `motor`
- **THEN** construction binds both children's defaults under
  `x_axis.motor` and `y_axis.motor` and stepping addresses each
  independently

#### Scenario: Time reads the simulation clock

- **WHEN** a simulation with `dt=0.02` has advanced 125 ticks and a
  deferred action reads the assembly's `time`
- **THEN** the value is exactly the instant 2.5 seconds, not symbolic
  `$t` and not a normalized fraction

#### Scenario: Deferred action sees stepped state

- **WHEN** `at(2.5).run(fn)` is registered and the simulation runs
  past 2.5
- **THEN** `fn` is called once, at tick `2.5/dt`, observing the state
  after that tick's binding

#### Scenario: Invalid dt is refused before binding

- **WHEN** `Sim(node, dt)` receives zero, a negative value, infinity, NaN,
  a boolean, or a non-numeric value
- **THEN** construction raises `ValueError` naming `dt`
- **AND** the node has not received a simulation state binding

#### Scenario: Negative run duration has no effects

- **WHEN** a simulation with a current-tick action calls `run(-dt)`
- **THEN** `ValueError` is raised and its tick, state, trajectory, pending
  actions, and cadence counts are unchanged

#### Scenario: Past scheduling is refused

- **WHEN** a simulation at tick 10 registers an action for tick 9
- **THEN** `ValueError` is raised naming the instant and current time
- **AND** no action is registered or executed

#### Scenario: Current-tick scheduling remains valid

- **WHEN** a simulation at tick 10 registers an action for tick 10 and calls
  `run(0)`
- **THEN** that action runs once at tick 10 without adding a trajectory entry

#### Scenario: An author-bound plain port follows a run-owned coordinate

- **WHEN** an assembly under a running root binds a plain port in its
  `simulate()` from a run-owned joint coordinate it reads,
  `self.readout = self.first.turn.value`, and the simulation runs ten ticks
  of a move on the input that drives `first.turn`
- **THEN** after every tick `readout` equals `first.turn`, its binder is the
  author's and not the running simulation's, and it is cleared and rebound
  each tick rather than holding a stale value

#### Scenario: Initial driver values bind over the defaults

- **WHEN** `Sim(node, dt, state={'crank': 30.0})` is constructed over a root
  whose `crank` declares a default of `0.0`
- **THEN** `sim.state['crank']` is `30.0` before the first tick and the
  first render was posed at it

#### Scenario: The running surface is refused under a looping root

- **WHEN** a simulation over a root declaring `Time(loop=2.0)` calls
  `move`, `rate`, `snapshot`, `restore` or `reset`
- **THEN** each is refused naming `Time.running()`, `sim.running` is
  `False`, and the trajectory keeps appending every tick

## ADDED Requirements

### Requirement: A running root's simulation owns every driver and joint coordinate

Under a root assembly declaring `time = Time.running()` the simulation
SHALL own a BANK holding every driver AND every joint coordinate of the
linked tree — on assemblies and leaves alike, class-declared and
site-declared joints alike — keyed by the qualified id the driver
enumeration and the port enumeration produce: the instance path joined
with the driver's name, the joint's name, or `<joint>.<coordinate>` for a
joint owning several. `sim.state` SHALL return the whole bank by id, as a
fresh mapping. Plain ports and derived coordinates SHALL NOT be in the
bank: they are computed by the ordinary enumeration from the bank on
every tick. There SHALL be no separate memory bank, and the author SHALL
declare no state. An id two declarations of one node would both claim
SHALL be refused at construction naming both.

The initial bank SHALL be the untimed rest pose at the requested driver
values: construction SHALL bind the driver values (the declared defaults,
overridden by `state=`) with `time` at zero, enumerate the tree once
exactly as an untimed root is enumerated — the author's `simulate()` and
every relation solving as they do today — and read every joint coordinate
off the tree. A joint coordinate that rest render leaves unbound SHALL be
refused at construction naming the node path and the coordinate and
saying that the run owns every joint coordinate and needs a rest value for
each.

From the moment construction completes, every bank coordinate SHALL be
bound by the run — through `set_state` with the whole bank and `time`,
the run recorded as the binder — so that `render()` and `simulate()` stay
pure functions of the bound snapshot: rendering, inspecting, or binding
the same snapshot again SHALL advance nothing and change no value. An
author's `simulate()` that binds a run-owned coordinate SHALL be refused
as doubly bound naming the class and the coordinate, at construction; a
binding written under a guard that finds the coordinate already bound is
not a binding and SHALL keep working.

`sim.time` SHALL remain `tick * dt`, and every instant, duration and
period SHALL keep the whole-tick rule.

#### Scenario: The bank lists joint coordinates by qualified id

- **WHEN** a simulation is constructed over a running root declaring
  drivers `crank` and `lever`, its own joint `spindle` wired into a
  child's plain port `wheel.turn`, children `first` and `second` each
  owning a `turn` joint on a leaf, and a child `slide` owning a `travel`
  joint
- **THEN** `sim.state` has exactly the keys `crank`, `lever`, `spindle`,
  `first.turn`, `second.turn` and `slide.travel` — the plain port
  `wheel.turn` among them nowhere

#### Scenario: The initial bank is the rest pose

- **WHEN** the same root states `crank.drives(first.turn, ratio=2.0)`,
  `first.turn.drives(second.turn, ratio=-1.5)` and
  `lever.drives(slide.travel, law=tooth_window)`, and the simulation is
  constructed with `state={'crank': 10.0}`
- **THEN** the initial bank reads `first.turn == 20.0`,
  `second.turn == -30.0` and `slide.travel` equal to the law at the
  lever's default — the values the untimed root poses at

#### Scenario: Rendering and rebinding advance nothing

- **WHEN** a running simulation has moved its crank for ten ticks and the
  caller then renders the node, reads every coordinate, and calls
  `set_state` with `sim.state` and `time=sim.time` once more
- **THEN** `sim.state`, `sim.tick` and every joint coordinate on the tree
  are unchanged, and the next tick continues from the same bank

#### Scenario: An author binding of a run-owned coordinate is refused

- **WHEN** a running root's `simulate()` binds `self.first.turn` from its
  crank unconditionally
- **THEN** construction is refused naming that class and `first.turn` as
  doubly bound, saying the running simulation owns it and a law belongs
  in a relation

#### Scenario: A guarded rest default keeps working

- **WHEN** a running root's `simulate()` reads `self.slide.travel.value`,
  finds it `None` and binds `4.0`
- **THEN** construction succeeds, the bank reads `slide.travel == 4.0`, and
  the guard never binds again while the run owns the coordinate

#### Scenario: An unbound joint coordinate is refused at construction

- **WHEN** a running root's rest render leaves a joint coordinate unbound —
  nothing drives it and no `simulate()` binds it
- **THEN** construction is refused naming its qualified id and saying the
  run needs a rest value for every joint coordinate

#### Scenario: A joint on a leaf is owned like any other

- **WHEN** the joint `turn` is declared on a leaf class held as `first`
- **THEN** `first.turn` is in the bank, the run binds it on every tick, and
  the leaf's body is placed by the bound value

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
formula or relation that predicted each and the coordinate; a joint
coordinate whose new value would leave its declared range SHALL be
refused naming the joint, the value and the range. A tick that fails
SHALL commit nothing: the bank, the tick count and the bound tree stand
as before, and every command that moved an input in that tick is
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

#### Scenario: A joint's range fails the tick in this cycle

- **WHEN** `first.turn` declares `range=(-90, 90)` and the crank is moved
  so that `first.turn` would reach `100`
- **THEN** the tick that would cross the range is refused naming
  `first.turn`, `100`, the range and the unit, and the bank stands at the
  last admitted tick

### Requirement: A relation's law is compiled to an expression over coordinate ids

At construction under a running root the system SHALL COMPILE the
relations the rest render solved into a program over the bank: each
relation's law SHALL be applied ONCE to a symbolic token per source
coordinate, in the direction the rest render solved it, and the
expression graph that application builds — over the qualified ids of
the sources — SHALL be what the run evaluates on every tick and what
the refusals below inspect. A wiring into a bank coordinate SHALL be an
identity edge and a derived coordinate a linear edge. A relation or
wiring none of whose driven ends is, or reaches through such
intermediates, a bank coordinate SHALL be left to the ordinary
enumeration. The program SHALL have an IDENTITY derived from the root
class, the bank's ids, the inputs' declarations and every edge's ends,
direction and expression.

The system SHALL refuse, at construction and by relation identity —
naming the relation as written and the class that stated it:

- a law whose expression contains a DISCONTINUOUS primitive — a call to
  `floor`, `ceil` or `sign`, the `%` operator, or a comparison — saying
  that jumps are not yet supported by the running mode;
- a law that cannot be applied to symbols — one that raises when handed
  a symbolic token, returns something that is neither a number nor an
  expression, or whose expression holds text the framework cannot
  evaluate or a call outside the symbolic vocabulary — saying that a
  running law is an expression over its sources;
- a relation or wiring INTO a bank coordinate whose source is a
  coordinate the run does not own and no compiled edge computes — a
  plain port the author's `simulate()` binds — saying to state that
  value as a relation or a joint;
- a relation naming several driven ends of which some are bank
  coordinates and some are not.

A law whose expression has no free coordinate — a constant — SHALL
compile and contribute a zero increment; the refusal of a law whose
slope is zero everywhere needs jump detection and is not this cycle's.

#### Scenario: A running root with a floor in a law is refused

- **WHEN** a running root states `crank.drives(first.turn, law=window)`
  where the law's expression contains `floor(angle / 360)`
- **THEN** construction is refused naming that relation and saying jumps
  are not yet supported, and the same root without `Time.running()`
  poses exactly as before

#### Scenario: A law over stdlib math is refused as non-symbolic

- **WHEN** a running root's law computes `math.sin(angle)` from Python's
  standard library
- **THEN** construction is refused naming the relation and saying the law
  cannot be applied to symbols

#### Scenario: A relation sourced from an author-bound port is refused

- **WHEN** a running root's `simulate()` binds a plain port from its
  crank and a relation drives a joint from that port
- **THEN** construction is refused naming the relation and the port, and
  advising a relation or a joint

#### Scenario: A law with a kink compiles

- **WHEN** a running root's law is `4 + 72 * clamp01((angle − 113.5) / 11.25)`
- **THEN** construction succeeds and the compiled expression names the
  source's qualified id and only `min` and `max` among calls

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
reverse request — negative `by`, a `to` below the committed value, a
negative `rate` — SHALL be refused naming the input in this cycle,
because a reverse move meets no stop until ranges become physical stops.

`move` and `rate` SHALL return a HANDLE reporting the input, the kind,
the status — `active`, `completed`, `blocked`, `refused` or `cancelled`
— the travel requested and the travel actually ADMITTED so far, in
design units, and offering `cancel()`. `blocked` SHALL NOT occur in this
cycle; the vocabulary is fixed now. A request that fails validation SHALL
raise rather than return a handle; `refused` is the status of a command
whose tick failed. Per-tick admission SHALL be a pure function of the
tick count since the command started: a move distributes its travel as
the ramp program does, integer-exact for an integer input and landing
exactly; a rate admits the difference of its cumulative travel at
successive ticks, floored for an integer input. A zero-duration move
SHALL integrate at once at the current tick without advancing it.
`sim.commands` SHALL be the active handles; a command SHALL be RETIRED
from them the tick it completes, so a long run accumulates no completed
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

#### Scenario: A reverse move is refused in this cycle

- **WHEN** `move('crank', by=-10, duration=1.0)`, `move('crank', to=5, duration=1.0)`
  from `20`, or `rate('crank', -90.0)` is requested
- **THEN** each is refused naming `crank` and saying reverse travel meets
  no stop yet, and nothing changed

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

### Requirement: Snapshot, restore and reset act on the run's bank

Under a running root `sim.snapshot()` SHALL return a VALUE OBJECT holding
the compiled program's identity, `dt`, the tick, the whole bank and the
active commands with their progress; two snapshots of one state SHALL
compare equal. `sim.restore(snapshot)` SHALL compare the program identity
and `dt` FIRST and refuse a mismatch naming both, touching nothing; it
SHALL then replace the bank, the tick and the active commands, clear the
recording, and bind the restored bank to the tree. Handles issued before a
restore SHALL report `cancelled` with what they had admitted; the restored
commands SHALL be reachable through `sim.commands` and continue from their
recorded progress. `sim.initial` SHALL be the snapshot taken at
construction and `sim.reset()` SHALL be `restore(sim.initial)`.

#### Scenario: A snapshot restores mid-run

- **WHEN** a simulation runs five ticks of a ten-tick move, takes a
  snapshot, runs the remaining five, restores the snapshot and runs five
  again
- **THEN** after the restore the bank, the tick and the tree equal the
  snapshot's, and after the second five ticks they equal what the first
  completion produced

#### Scenario: A mismatched program or dt is refused before anything changes

- **WHEN** a snapshot taken over a different root class, or over the same
  class at a different `dt`, is restored
- **THEN** the restore is refused naming the two identities or the two
  steps, and the bank, the tick and the commands are unchanged

#### Scenario: Reset returns to the initial snapshot

- **WHEN** a simulation has run and `reset()` is called
- **THEN** `sim.snapshot() == sim.initial`, the tick is zero, the bank is
  the rest pose, no command is active and the recording is empty

### Requirement: Recording is explicit and bounded under a running root

Under a running root the simulation SHALL keep no per-tick record unless
asked: `Sim(..., record=None)` keeps nothing and `sim.trajectory` reads
empty; `record=N`, a positive integer, keeps a ring of the most recent
`N` `(tick, bank)` entries readable oldest first; any other value SHALL
be refused naming the option. Restore and reset SHALL clear the ring.
Unbounded recording SHALL NOT be offered under a running root.

#### Scenario: Nothing is recorded by default

- **WHEN** a running simulation steps ten thousand ticks with no `record`
  option
- **THEN** `sim.trajectory` is empty and the run's memory does not grow
  with the tick count

#### Scenario: A ring keeps the most recent ticks

- **WHEN** `Sim(node, dt, record=64)` steps one hundred ticks
- **THEN** `sim.trajectory` holds exactly sixty-four entries, for ticks
  37 through 100, oldest first

#### Scenario: An invalid recording option is refused

- **WHEN** `record=0`, `record=-1`, `record=True` or `record='all'` is
  given
- **THEN** construction is refused naming `record`
