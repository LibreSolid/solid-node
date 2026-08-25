# Simulation Specification (new capability)

## ADDED Requirements

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
expressed in design units. Triggering an instruction SHALL convert
each target to native driver state through that driver's declared
scale (rounding to the nearest native unit for an integer-typed
driver; a driver with no scale takes the target verbatim) and start a
ramp program over the instruction's duration. Instruction semantics
are held to target-plus-duration linear ramps; sequencing and richer
programs are explicitly out of scope.

#### Scenario: Millimetre target reaches a microstep driver

- **WHEN** an instruction targets `x=0` (mm) for a driver declared
  with `scale` millimetres-per-microstep and dtype `int`
- **THEN** the ramp's native target is 0 microsteps and intermediate
  states are whole microsteps

### Requirement: Fixed-dt stepping loop with deferred actions

The system SHALL provide a simulation loop constructed over one
assembly and a fixed `dt`. On construction it SHALL bind every
declared driver's default through `set_state`, so a state-consuming
assembly renders under a complete snapshot from the first render. Each
tick SHALL: advance every driver's program, bind the full snapshot via
`set_state`, record the tick and snapshot in a trajectory, then run
due deferred actions and cadence actions.

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
