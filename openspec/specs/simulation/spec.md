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
node class's declared drivers SHALL be discoverable by name off the
class without instantiating it. Mutable driver state SHALL live only
in a running simulation, never on the declaration and never shared
between node instances or between simulations.

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
expressed in design units. Instructions declared on any node in the
tree SHALL be discoverable and triggerable through the simulation by
qualified name — the declaring node's instance path joined with the
instruction name, with root-declared instructions keeping their bare
names — and each instruction's local target names SHALL resolve to the
declaring node's qualified driver ids. Triggering an instruction SHALL
convert each target to native driver state through that driver's
declared scale (rounding to the nearest native unit for an
integer-typed driver; a driver with no scale takes the target
verbatim) and start a ramp program over the instruction's duration.
Triggering an unknown name SHALL fail listing the known qualified
instruction names. Instruction semantics are held to
target-plus-duration linear ramps; sequencing and richer programs are
explicitly out of scope.

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

### Requirement: Fixed-dt stepping loop with deferred actions

The system SHALL provide a simulation loop constructed over one
assembly and a fixed `dt`. On construction it SHALL enumerate declared
drivers across the whole linked tree and bind every driver's default
through `set_state` by qualified id, so a state-consuming assembly —
including one whose drivers live only on descendants — renders under a
complete snapshot from the first render. Each tick SHALL: advance
every driver's program, bind the full snapshot via `set_state`
together with the global `time` entry set to the exact simulation
instant in seconds (`k*dt`, computed from the integer tick count,
never accumulated), record the tick and snapshot in a trajectory keyed
by qualified id, then run due deferred actions and cadence actions.
Under a running simulation, `self.time` therefore reads the stepped
simulation clock; the normalized symbolic `$t` animation path outside
simulations is unchanged.

Instants SHALL be validated as whole numbers of ticks
(`round(t/dt)*dt == t` within float tolerance) and represented as
integer tick counts, never accumulated floats. Scheduled actions SHALL
be deferred callables — `at(t).trigger(name)` and `at(t).run(fn)`
where `fn` receives the simulation — never eagerly evaluated
expressions. `every(period, fn, *args)` SHALL run `fn` at the declared
tick cadence and account its cost per slot, so scenario reports can
state assertion cost separately from stepping cost.

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

