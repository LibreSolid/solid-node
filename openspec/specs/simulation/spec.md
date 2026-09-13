# simulation Specification

## Purpose
The stepped simulation layer over the node model (ADR-056): stateless
class-level driver declarations, per-simulation state advanced by
deterministic programs, design-unit instructions, a fixed-dt stepping
loop binding qualified snapshots and the global `time` clock through
`set_state`, tree-wide qualified driver enumeration, and scenario
tests that run under both pytest and the `solid test` runner. State
lives in drivers; geometry stays a pure function of the bound
snapshot.
## Requirements
### Requirement: Driver declarations separate from simulation state

The system SHALL let an assembly declare its drivers as stateless
class attributes: `Driver(default, range=None, unit=None, dtype=None,
scale=None)`, where `dtype=int` marks a discrete device whose state is
integer-typed and `scale` declares design units per native unit. A
declared `range` SHALL be expressed in design units — the units a
maker thinks and instruction targets are stated in — regardless of
`scale`; it is presentation metadata and never a clamp. A node class's
declared drivers SHALL be discoverable by name off the class without
instantiating it. Mutable driver state SHALL live only in a running
simulation, never on the declaration and never shared between node
instances or between simulations.

#### Scenario: Declarations carry no state

- **WHEN** two simulations run over nodes of the same class, stepping
  the same declared driver differently
- **THEN** each simulation observes only its own state trajectory and
  the class declaration is unchanged

#### Scenario: Declared drivers are discoverable

- **WHEN** a consumer inspects an assembly class declaring
  `x = Driver(default=100, range=(0, 200), unit='mm')`
- **THEN** it can enumerate the driver with its default, range, unit,
  dtype, and scale without constructing the assembly

#### Scenario: A scaled driver's range reads in design units

- **WHEN** an axis declares
  `motor = Driver(default=0, range=(0, 100), unit='ustep', dtype=int, scale=0.0125)`
- **THEN** the range means 0 to 100 design units of travel — 0 to 8000
  native microsteps — and a presenter converts through `scale` to
  relate it to native state, while nothing anywhere clamps state to it

### Requirement: Programs advance driver state deterministically

The system SHALL advance driver state only through programs. A program
SHALL be a pure function of the tick number and its captured start
state. `RampProgram` SHALL distribute a delta over n ticks; for an
integer-typed driver the distribution SHALL be integer-exact
(`start + (delta * k) // n`), landing exactly on `start + delta` at
`k == n`, after which the program completes. A driver with no active
program SHALL hold its state.

#### Scenario: Integer ramp lands exactly

- **WHEN** a ramp moves an integer driver from 8000 to 0 over 100
  ticks
- **THEN** the state at tick 100 is exactly 0 and every intermediate
  state is an integer

#### Scenario: Determinism is exact

- **WHEN** the same scenario script is run twice in fresh simulations
- **THEN** the recorded state trajectories compare exactly equal

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

### Requirement: Scenario testing

The system SHALL provide a scenario test base extending the existing
CAD `TestCase`: a scenario method builds the node once (assembling and
generating STLs where mesh assertions need them), obtains a fresh
simulation per scenario, scripts events and assertions against it, and
runs a bounded time slice. Scenario tests SHALL pass under the plain
pytest suite and under the `solid test` runner without modification to
either runner.

#### Scenario: A homing scenario asserts along the way

- **WHEN** a scenario triggers a homing instruction at t=0, registers
  an interference assertion at a 0.1 s cadence, checks the terminal
  state with a deferred action, and runs 3.0 s
- **THEN** the assertions execute at their scheduled ticks and the
  test passes exactly when every one holds

### Requirement: Qualified tree-wide driver enumeration

The system SHALL provide one enumeration authority that walks a
constructed assembly's linked tree and returns its declared drivers
keyed by qualified id (dotted instance path plus local name;
root-declared drivers keep bare names). This enumeration SHALL be the
single source feeding the simulation state bank, instruction-target
resolution, build-path default binding, and the serialized document's
driver table, so the id in the document and the key in the bank are
the same string by construction. Enumeration SHALL fail loudly on a
driver reachable only through an illegal id segment, per the
qualified-identity requirement.

#### Scenario: Drivers on descendants are enumerated qualified

- **WHEN** a driverless root holds `x_axis` and `y_axis` instances of
  one class declaring `motor = Driver(default=8000)`
- **THEN** enumeration yields exactly `x_axis.motor` and
  `y_axis.motor`, each carrying the declaration's default, range,
  unit, dtype, and scale

### Requirement: A driver states a relation to a coordinate

The system SHALL give every `Driver` declaration the verb that states a
relation between two coordinates, so a root class body may write
`art3.drives(shoulder.art2.art3.elbow)` and a driver reach a joint or a
port at any depth without every class between them declaring and
forwarding one. The driver's value SHALL be what reaches the relation:
the bound number under `set_state`, the test runner and the stepped
simulation, and the driver's symbolic token when nothing is bound, so
the relation publishes an expression in that driver's qualified id.

A driver SHALL be a SOURCE only. A `Driver` named as the DRIVEN end of
a relation SHALL be refused at class definition, naming the driver and
saying that its value belongs to the bound snapshot and is set with
`set_state`, which is the rule an assignment to a driver already
states.

A driver's declared range SHALL remain presentation metadata and never
a clamp; a relation SHALL NOT read it and SHALL NOT check against it.
A range declared by a joint the relation drives SHALL apply to the
value that reaches that joint, exactly as it does for a hand binding.

Reaching a driver sideways — reading one off a child declaration in a
class body — SHALL be refused, because a driver is addressed by the
qualified id its position in the tree gives it and a second address for
one value is what that qualification exists to prevent.

#### Scenario: A driver reaches a deep joint

- **WHEN** a root declares `art3 = Driver(...)`, three levels of
  children below it, and states
  `art3.drives(shoulder.art2.art3.elbow)`
- **THEN** the elbow coordinate holds the driver's value on every run,
  the forearm is placed by it, and no intermediate class declares a
  port for it

#### Scenario: A driver drives through a ratio

- **WHEN** a root states `art1.drives(base.pinion.turn, ratio=5.0)` and
  binds `art1` to `12` with `set_state`
- **THEN** the pinion's coordinate reads `60`

#### Scenario: A driver's symbolic read rides through a relation

- **WHEN** the same tree is serialized with nothing bound
- **THEN** the pinion's operation carries an expression in the driver's
  qualified id, and `set_state` makes it numeric

#### Scenario: A driver cannot be driven

- **WHEN** a class body states `some_port.drives(art3)` where `art3` is
  a `Driver` declaration
- **THEN** class definition raises naming the driver and pointing at
  `set_state`

#### Scenario: A driver read off a declaration is refused

- **WHEN** a class body reads a `Driver` off a child declaration
- **THEN** class definition raises, naming the declaration and the
  driver, and the driver's qualified id remains its one address

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
the refusals below inspect. A graph containing a DISCONTINUOUS
primitive — a call to `floor`, `ceil` or `sign`, the `%` operator, or a
comparison — SHALL additionally be compiled into a JUMP PLAN: its jump
nodes in the graph's postorder, each with the level quantity whose
surfaces it crosses, the graph of that level quantity with the jump
nodes inside it replaced by branch placeholders, whether that level
quantity is AFFINE in the sources, and the SKELETON of the whole
expression with every jump node so replaced. A wiring into a bank
coordinate SHALL be an
identity edge and a derived coordinate a linear edge. A relation or
wiring none of whose driven ends is, or reaches through such
intermediates, a bank coordinate SHALL be left to the ordinary
enumeration. The program SHALL have an IDENTITY derived from the root
class, the bank's ids, the inputs' declarations and every edge's ends,
direction and expression.

The system SHALL refuse, at construction and by relation identity —
naming the relation as written and the class that stated it:

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
  coordinates and some are not;
- a law whose expression contains a DISCONTINUOUS primitive and none of
  whose driven ends is a coordinate the run owns — a plain port or a
  derived coordinate the ordinary enumeration recomputes from the bank
  on every tick — saying that a subtracted jump implies a history,
  that only a coordinate the run owns keeps one, and that the relation
  should be stated into the joint coordinate so the port follows it.

A law whose expression has no free coordinate — a constant — SHALL
compile and contribute a zero increment; a law that can move its
coordinate only by jumping SHALL be refused under the requirement "A
law that can only jump is refused as arithmetic".

#### Scenario: A running root with a floor in a law compiles

- **WHEN** a running root states `crank.drives(first.turn, law=window)`
  where the law's expression contains `floor(angle / 360)`
- **THEN** construction succeeds, the compiled graph names the source's
  qualified id, its jump plan holds one `floor` node whose level
  quantity is that qualified id divided by 360 and is AFFINE in the
  sources, and the same root without `Time.running()` poses exactly as
  before

#### Scenario: A jumping law into a plain port is refused

- **WHEN** a running root states `crank.drives(register, law=window)`
  where `register` is a plain port wired to a joint coordinate and the
  law's expression contains `floor`
- **THEN** construction is refused naming the relation and the port, and
  saying to state the relation into the joint coordinate the run owns;
  and the same relation stated into that joint coordinate compiles

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

### Requirement: A jump is located inside the tick and subtracted

Under a running root a law whose expression contains a DISCONTINUOUS
primitive SHALL contribute, over one tick, the CONTINUOUS part of its
change: the tick's path SHALL be cut at every crossing of every jump
surface it meets, and the law's change SHALL be summed over the pieces
between those cuts, so that no jump ever moves a part.

The PATH of a tick SHALL be the straight line from the values the law's
sources hold to those values plus the increments they were given,
parametrised by a fraction `t` in `[0, 1]` — in the JOINT space of the
sources for a law naming several. A tick in which no source moves SHALL
contribute zero without evaluating the law.

Each jump node SHALL have a LEVEL QUANTITY and a family of SURFACES:
`floor(x)` and `ceil(x)` over `x` at every integer; `sign(x)` over `x`
at zero; `a % b` over `a / b` at every NONZERO integer, the operator
being the remainder that takes the sign of the DIVIDEND and is
therefore continuous where `a / b` crosses zero; a comparison over
`a − b` at zero. `wrap()` SHALL be integrated as the `ceil` it is built
on, and `piecewise()` SHALL need nothing, being built on `clamp01`.

On each open piece between two cuts every jump node SHALL hold one
BRANCH — the integer for `floor` and `ceil`, `-1`, `0` or `+1` for
`sign`, the integer quotient for `%` so that the node reads `a − q·b`,
and `1` or `0` for a comparison — determined by evaluating its level
quantity at the MIDPOINT of that piece, in the graph's postorder so
that a jump nested inside another's argument is determined first. The
law with those branches substituted SHALL be continuous on the closed
piece, and the increment SHALL be the sum, over the pieces, of that
substituted law's value at the piece's end minus its value at the
piece's start. A piece's endpoints SHALL therefore carry the one-sided
values of the law, at the tick's own start and end as well as at each
cut.

Crossings SHALL be found for every jump node of the law, in the graph's
postorder, over each piece the nodes before it have already produced,
and ALL crossings of one node inside one piece SHALL be found — not
only the difference of the piece's endpoints. Where the level quantity
is AFFINE in the sources along the path the crossings SHALL be solved
exactly, every surface between the endpoint values included; otherwise
the piece SHALL be sampled at a fixed number of sub-intervals and each
bracketed crossing located by bisection to a stated tolerance, with the
limit of that search documented. Two crossings closer than the
tolerance SHALL be one cut, and several jump nodes crossing at one
fraction SHALL be one cut whose midpoint sample fixes every branch at
once.

A tick that would cut one law's path more than a stated maximum number
of times SHALL be refused naming the relation, the driven coordinate,
the primitive and the count, and SHALL commit nothing — the bank, the
tick count and the bound tree standing as before and the commands that
moved an input in it retired reporting `refused` — exactly as a
conflict does. A `%` whose divisor is zero anywhere the tick evaluates
SHALL be refused the same way.

#### Scenario: A periodic window advances once per revolution

- **WHEN** a running root states
  `crank.drives(pinion.turn, law=periodic_window)` carrying
  `4 + 72 * clamp01((angle − 360 * floor(angle / 360) − 113.5) / 11.25)`,
  the crank rests at `100`, `dt` is `1/240`, and the simulation moves
  `crank` by `360` over one second, twice
- **THEN** `pinion.turn` reads `4` before the first move, `76` after it
  and `148` after the second, and the tick in which the crank passes
  `360` contributes exactly zero

#### Scenario: A tick that passes three windows adds three throws

- **WHEN** the same root is given `move('crank', by=1080, duration=0)`
  from a crank of `100`
- **THEN** `pinion.turn` reads `220`, three crossings are located inside
  that one tick, and the crank stands at `1180`

#### Scenario: A gate holds open and re-engages without a jump

- **WHEN** a running root states
  `(shaft.turn & sleeve.travel).drives(wheel.turn, law=clutch)` carrying
  `-2 * shaft * (sleeve > 0.5)`, and the shaft turns by `4` over a tick
  in which the sleeve stands at `0`, then over a tick in which it
  stands at `1`, then over a tick in which it travels from `0` to `1`
- **THEN** `wheel.turn` moves by `0`, then by `-8`, then by `-4` — the
  travel after engagement only — and never by the value the gate factor
  would have jumped to

#### Scenario: A wrapped law integrates to the unwrapped travel

- **WHEN** a running root's law is `2 * wrap(angle, 360)` and the crank
  travels `500` degrees from `100`
- **THEN** the driven coordinate gains exactly `1000`, and the two
  `ceil` crossings inside that travel contribute nothing of their own

#### Scenario: A remainder window and a floor window agree

- **WHEN** two running roots carry the same tooth window, one written
  with `angle − 360 * floor(angle / 360)` and one with `angle % 360`,
  and both cranks are moved through one revolution from `100`
- **THEN** both driven coordinates read the same value at every tick

#### Scenario: A sign that does not jump integrates as its continuous twin

- **WHEN** a running root's law is `5 * (x − 50) * sign(x − 50)` and a
  second root's is `5 * abs(x − 50)`, and both are driven across `50`
- **THEN** both driven coordinates read the same value at every tick,
  the crossing of `sign` having been located and contributed nothing

#### Scenario: A jump nested in another jump's argument

- **WHEN** a running root's law engages only on alternate revolutions,
  `72 * clamp01((angle − 360 * w − 113.5) / 11.25) * (1 − (w − 2 * floor(w / 2)))`
  with `w = floor(angle / 360)`, and the crank is moved through four
  revolutions from `100`
- **THEN** the driven coordinate reads `72` after the first revolution,
  `72` after the second, `144` after the third and `144` after the
  fourth

#### Scenario: The same movement split differently gives the same answer

- **WHEN** one running simulation takes a revolution of the crank in a
  single tick, another in twelve, and another in two hundred and forty
- **THEN** all three leave the driven coordinate at the same value

#### Scenario: A tick that would cross too many surfaces is refused

- **WHEN** a periodic law is driven far enough in one tick to cross more
  surfaces than the stated maximum
- **THEN** the tick is refused naming the relation, the coordinate, the
  primitive and the count; the bank, the tick count and the tree are
  unchanged; and the move's handle reports `refused`

### Requirement: A law that can only jump is refused as arithmetic

Under a running root the system SHALL REFUSE, at construction and by
relation identity — naming the relation as written and the class that
stated it — a law that can move its driven coordinate only by jumping:
the law's expression with every jump node, and the whole argument
subtree beneath it, replaced by a constant SHALL be examined, and a law
whose expression so reduced holds no free coordinate SHALL be refused.
The message SHALL say that every jump is subtracted, so such a law can
never move the coordinate, and that it states arithmetic rather than a
mechanism.

A law whose reduced expression still holds a free coordinate SHALL
compile, whatever else it contains.

#### Scenario: A law that is only a step counter is refused

- **WHEN** a running root states `crank.drives(dial.value, law=counter)`
  whose expression is `floor(turns)`
- **THEN** construction is refused naming that relation and saying the
  law can only jump and states arithmetic rather than a mechanism

#### Scenario: A jump beside a sloped term compiles

- **WHEN** a running root's law is `9 * enabled + floor(turns)` over two
  sources
- **THEN** construction succeeds, because `enabled` still carries slope,
  and moving `turns` alone moves the coordinate not at all

#### Scenario: A periodic window is not a law that only jumps

- **WHEN** a running root's law is
  `4 + 72 * clamp01((angle − 360 * floor(angle / 360) − 113.5) / 11.25)`
- **THEN** construction succeeds, the reduced expression still naming
  `angle`

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

`record=N` SHALL additionally keep a SECOND ring, of the most recent
`N` CROSSINGS located inside a tick, readable through `sim.crossings`
oldest first, each entry naming the tick, the relation as written, the
driven coordinate, the primitive that jumped, the surface value in the
level quantity's own units, and the fraction of the tick at which it
was crossed. Entries SHALL be appended in order of that fraction within
a tick, in the graph's postorder where two coincide, and in program
order across relations. `record=None` SHALL keep no crossings and build
none. Restore and reset SHALL clear both rings.

#### Scenario: Nothing is recorded by default

- **WHEN** a running simulation steps ten thousand ticks with no `record`
  option
- **THEN** `sim.trajectory` and `sim.crossings` are both empty and the
  run's memory does not grow with the tick count

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
