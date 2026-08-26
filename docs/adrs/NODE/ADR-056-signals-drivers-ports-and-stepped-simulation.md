# ADR-056: Signals, drivers, ports, and stepped simulation

**Status:** Proposed (design draft; core spike-validated 2026-08-25,
expression representation spike-validated 2026-08-26)

**Date:** 2026-08-25

**Extends:** [ADR-008: Time-Based Animation System for Assemblies](ADR-008-time-based-animation-system-for-assemblies.md),
[ADR-023: Kinematic Operations and Driver-Tagged Idempotent Renders](ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

**Affects (when implemented):**
- [ADR-011: Animation Testing Decorators](../TEST-FRAMEWORK/ADR-011-animation-testing-decorators.md)
- [ADR-022: Cross-Runtime Degree-Trig Parity for `$t`](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
- [ADR-034: Shared Node-Tree Document Schema](../EXPORT/ADR-034-shared-node-tree-document-schema.md)
- [ADR-051: Producer-Owned Animation Time in Node Documents](../EXPORT/ADR-051-producer-owned-animation-time-in-node-documents.md)

> **Preamble.** This ADR is a recovery record of a pilot design
> conversation (2026-08-24/25), drafted ahead of any OpenSpec change at
> the pilot's direction. Nothing in it is ratified, implemented, or
> validated; it exists so the design can be resumed without re-deriving
> it. The normal flow — OpenSpec proposal, ratification, red-first
> implementation — still applies before any of this lands.

## Context

ADR-008 gave assemblies a single global scalar, `self.time` (OpenSCAD's
`$t`, 0..1, looping), and every motion in a project is a pure function
of it. That purity is load-bearing: operations resolve symbolically at
access time, `set_keyframe` collapses them to numbers, ADR-023's
driver-tagged sweep makes re-renders idempotent, ADR-011's decorators
sweep instants, and the viewer recomputes absolute matrices from
declarations. ADR-008 itself recorded the known limit: one global
timeline cannot express independent movement sources.

Two empirical pressures now hit that limit:

- **v8-engine** works only because the machine is *periodic*: one 0..1
  cycle fully describes it, so "time" could secretly mean "phase". Its
  `kinematics.py` is already a hand-built signal graph (crank angle
  feeding cam angle, rod angle, piston height) in closed form.
- **Metamaquina2** (parametric 3D printer rebuild) is *not* periodic.
  The goal is whole-machine simulation: instructions (eventually
  G-code) generate stepper signals, motors drive belts and screws,
  carriages move, and pose at time t depends on the history of what was
  commanded — no function of a looping scalar can express it. The same
  holds for a whole car: engine cycle, steering, and throttle are
  independent inputs.

The pilot's product goal for the first delivery: an app in which
clicking buttons triggers instructions and the simulated machine
responds visibly.

## The design

### Vocabulary

- **Signal** — a scalar value that flows between components (an angle,
  a displacement, a lift). Defined as an expression of upstream
  signals; evaluable at an instant. Having a closed symbolic form is an
  optional bonus, not the contract.
- **Driver** — a free input to the model and the *only* holder of
  simulation state. A driver integrates: each tick it consumes
  events/increments and produces a new state value. `time` remains a
  built-in driver; steering angle, throttle, and axis positions are
  project-declared ones. Declarations carry default, range, and unit —
  that metadata is what makes the app UI derivable and what tests
  sweep.
- **Port** — the typed connection point on a node. Physical ports are
  typed by domain: `RotationalPort` (carries angle), `TranslationalPort`
  (carries position). Plain `Signal` ports carry dimensionless
  commands. `connect()` is called by the parent assembly and binds a
  sink to a source.
- **Tick** — one discrete simulation step of fixed `dt`.
- **Event** — an input arriving at a tick (a button press, a G-code
  word). Events feed drivers; nothing else consumes them.
- **Instruction** — a named, project-declared event source: v1 is a set
  of driver targets plus a duration, ramped linearly client-side. The
  future G-code interpreter is a richer program in the same slot.
- **Scenario** — a deterministic test/demo artifact: initial state +
  fixed `dt` + an ordered event script over a time slice.
- **Keyframe** — retains its meaning: a bound state snapshot. Drivers
  *integrate*; a keyframe is what any tick's result looks like.
- **Phase** — a 0..1 looping scalar *derived from* a driver state
  (e.g. crank angle wrapping every 720°). What `self.time` really was.

### The one guardrail

**State lives in drivers. Geometry stays pure.**

```text
driver_states(t + dt) = step(driver_states(t), events, dt)   # stateful
pose                  = f(driver_states)                     # pure
```

The second line is ADR-027/ADR-023's absolute-composition principle
intact: given a state snapshot, everything renders fresh, idempotent,
jumpable. Stepping must never leak into `render()` — a node
accumulating its own motion across renders would reintroduce the
rewind/replay disease those ADRs removed, and would break keyframed
tests and `_idempotent_render`. Integration happens in exactly one
place (the driver) and is trivial accumulation, so replay from a
snapshot is cheap and deterministic.

### What happens to `self.time`

It is demoted, not removed. The root of simulation becomes the tick;
`time` is one driver among several. A periodic component keeps a 0..1
phase derived from a driver state, and the closed-form symbolic path
(`$t` in OpenSCAD, expression strings in the viewer) is preserved as an
optimization for the periodic subset — the v8-engine keeps animating
natively and keeps `@testing_steps`. Scenarios are not forced onto
periodic mechanisms.

`set_keyframe(time)` generalizes to binding a full snapshot:
`set_state(x=100, z=0, crank=310)`. A simulation is a sequence of
snapshots produced by stepping. Everything downstream (operation
resolution, mesh, assertions) already works per snapshot.

### Project-author interface (sketch)

```python
class Car(AssemblyNode):
    steering = Driver(default=0, range=(-30, 30), unit='deg')
    throttle = Driver(default=0, range=(0, 1))

    def render(self):
        engine = Engine()
        gearbox = Gearbox()
        self.connect(engine.crank, gearbox.input_shaft)
        self.connect(self.steering, steering_column.wheel_angle)


class Engine(AssemblyNode):
    crank = RotationalPort(out=True)

    def render(self):
        self.crank.value = 720.0 * self.time + BANK_HALF


class Gearbox(AssemblyNode):
    input_shaft = RotationalPort()

    def render(self):
        self.gear.rotate(self.input_shaft.value * self.ratio, [1, 0, 0])
```

Connection happens in the parent's `render()`, where children are
created and driven today, so ADR-023's sweep and keyframe propagation
extend naturally. The v8 `kinematics.py` pattern — a node computes its
port value in closed form — stays legal; it is the
"component ships solved equations" escape hatch.

### App interface

The web viewer already evaluates symbolic `$t` expression strings
client-side and recomputes absolute matrices per frame. The app is that
mechanism with a richer vocabulary and a client-side stepping loop:

- the serialized document gains a **driver table** (name, range,
  default, unit) and operation expressions may reference driver names.
  Driver names are class-local; the wire namespace is flat, so the
  document keys drivers by a **qualified id** — the instance path from
  the serialization root joined with the local name, Modelica-flattening
  style (`x_axis.motor`), computed during the serialization walk and
  never stored. Authors only ever write local names;
- the client holds driver states, applies increments each animation
  frame, and re-evaluates matrices — sliders and buttons change driver
  values in the browser with **no server round-trip and no re-render**;
- projects declare instructions; the UI renders one button per
  instruction, sliders for ranged drivers, a transport for `time`:

```python
class Printer(AssemblyNode):
    x = Driver(default=100, range=(0, 200), unit='mm')

    instructions = {
        'Home X': Instruction(x=0, duration=2.0),
    }
```

The client-side ramp is deliberately the seed of the future simulation
layer: it is a degenerate simulator producing a driver trace. The
G-code interpreter, when it arrives, is a better trace producer writing
to the same drivers; the viewer contract does not change. The OpenSCAD
path substitutes current numeric values for every non-time driver
(OpenSCAD only knows `$t`) and simply loses interactivity.

### Test interface (sketch)

```python
class TestHomeX(ScenarioTest):
    dt = 0.02          # fixed step; instants are i*dt, never accumulated floats

    def scenario(self, sim):
        sim.at(0.0).trigger('Home X')
        sim.every(0.1, self.assertNoSolidInterference, self.printer)
        sim.at(2.5).run(lambda sim: self.assertEqual(sim.state['x'], 0))
        sim.run(3.0)
```

(Scheduled actions are DEFERRED callables. An earlier draft sketched
`sim.at(2.5).assertEqual(sim.state.x, 0)`, which cannot work — the
arguments would evaluate at registration time. Spike finding 3.)

Determinism: fixed `dt` per scenario, instants derived as step counts
(the same integer-arithmetic reasoning as ADR-050). Cost: geometric
assertions are expensive per snapshot (ADR-029), so continuous checks
declare a cadence rather than running every tick. Existing decorators
generalize per driver: `@testing_steps(12, driver='steering')` sweeps
one driver with the others at defaults; grids are explicit opt-in
because cross-products explode.

## Bond-graph forward compatibility (and what is deferred)

The Modelica analysis behind this: Modelica models physical coupling
acausally — a connector carries a *pair* of variables (potential/flow,
e.g. angle/torque, whose product is power), `connect()` generates
equations (potentials equal, flows sum to zero), and a compiler
causalizes the flattened system. Its control layer (`Modelica.Blocks`),
however, is causal one-way signals — **buttons and instructions are
causal forever, even in full Modelica**. So the acausal-readiness
burden falls only on the mechanical ports.

This design's down payment, deliberately minimal:

1. **Ports are typed by physical domain**, so `RotationalPort` can later
   grow a `torque` flow variable and `TranslationalPort` a `force`,
   with no renaming in project code.
2. **`connect()` is the seam.** Today: bind sink expression to source
   expression (causal). Later: generate equations, oriented by a solver
   from whichever drivers are bound. Call sites are identical.
3. **"Evaluable at an instant" is the signal contract**, so sampled
   traces from numeric solving (nonlinear constraint loops, dynamics)
   slot in without touching consumers. Discrete-time integration of
   driver state is exactly the substrate a dynamics layer needs.

Explicitly deferred: `flow` variables, torque/force balance, inertia,
`der()`, any equation solver, any `constraints()` method. The
kinematic-acausal subset (linear constraint solving, back-drivable
mechanisms — attractive for Metamaquina2, whose stepper→belt→carriage
chain is linear end to end) is a plausible later bite, not part of
this decision.

## Considered options

1. **Runtime emitter/subscriber events** (callbacks, mutation) —
   rejected. Pose would depend on event history; jumping to an instant
   would require replay. That is the rewind/replay disease ADR-027
   removed, reintroduced one level up. The emitter/subscriber
   *topology* survives as declarative port wiring.
2. **Causal signal graph rooted in looping `time`** (the first draft of
   this design) — rejected as the root model. It cannot express
   non-periodic stateful machines; it survives as the derived-phase
   subset for periodic components.
3. **Full Modelica-style acausal modeling now** — deferred. It requires
   an equation solver, index reduction, and singular-system diagnostics
   (the classic Modelica UX failure is errors pointing at the flattened
   equation soup, not the offending component). The port typing above
   keeps the door open at near-zero cost.
4. **Stepped simulation with driver-held state** (this design) —
   chosen as the draft direction: expresses non-periodic machines,
   preserves the purity contract per snapshot, degrades gracefully to
   the periodic symbolic subset, and is the substrate later layers
   need.

## Spike evidence (2026-08-25)

The stepped-simulation core was spiked end-to-end in this worktree —
[`spike/SCOPE.md`](../../../spike/SCOPE.md),
[`spike/FINDINGS.md`](../../../spike/FINDINGS.md), runner
`spike/axis/scenario.py` — on a 5-leaf stand-in Metamaquina2 X axis
(integer-microstep driver, instruction ramp, per-tick port binding,
fixed-dt scenario loop), shimmed entirely over `set_keyframe` with
zero framework edits. **All five scoped sub-questions validated:**

- **Purity holds.** After 151 re-renders the driven node held exactly
  one operation (ADR-023's sweep replaced, never accumulated) and an
  arbitrary snapshot placed it absolutely. The feared invalidating
  outcome did not occur: per-tick re-renders never touch the artifact
  path — STL/scad generation stays `assemble()`-only, so stepping
  composes with the ADR-006/050 build machinery untouched.
- **Determinism is exact.** Integer driver state
  (`start + delta*k//n`, exact landing), instants as integer tick
  counts: two fresh runs compared exactly equal, no tolerance.
- **Instruction ramp v1 works** and lands exactly on target.
- **Per-tick connect in `render()`** coexists with the idempotent
  sweep.
- **Cost:** stepping is free (~267k bare ticks/s, ~4 µs/tick at spike
  model size) while one interference assertion costs ~1.0 ms (~250×
  a tick). Durable rule: **cadence budgets assertion cost; ticks are
  free.** Absolute numbers do not extrapolate to v8-scale meshes.
- **Separability confirmed:** every tick binds drivers to plain
  numbers; nothing symbolic was needed anywhere in the loop, so the
  expression-representation risk is fully decoupled (see open
  questions).

The spike names four seams the implementation must open — now design
requirements rather than open questions:

1. **`set_keyframe(time)` generalizes to a state-dict binding**
   (`set_state(**states)`, `time` one entry, same recursive
   propagation); `set_keyframe` survives as a compatibility wrapper.
2. **Driver declaration separates from driver state.** Declarations
   are class-level (default, range, unit, dtype); mutable state lives
   per simulation, never shared across node instances. Where the
   physical device is discrete (steppers), state is integer-typed.
3. **Scheduled scenario actions are deferred callables**
   (`sim.at(t).run(fn)`), never eagerly evaluated expressions.
4. **Instructions carry design units.** Makers write targets in mm;
   the port-level conversion (mm → µsteps) maps them onto driver
   state.

## Spike evidence: named-driver expressions (2026-08-26)

The expression-representation risk — named driver variables travelling
render → serialized document → client evaluation — was spiked in this
worktree with zero framework edits:
[`spike/expressions/SCOPE.md`](../../../spike/expressions/SCOPE.md),
[`spike/expressions/FINDINGS.md`](../../../spike/expressions/FINDINGS.md),
runner `spike/expressions/run_spike.py`, on one `Axis` class
(driver + port + degree trig + a mixed `$t`/driver formula + a `^`
term) instantiated twice under a driverless parent so the class-local
name collides for real. **Primary question validated; neither
design-invalidating outcome occurred.**

- **Representation decided: an eagerly-qualified token subclassing
  solid2's `OpenSCADConstant`, whose string is the qualified id** — not
  a tree-preserving expression type. The condition that picks it holds:
  both the scad and serializer passes link a child to its parent
  *before* the child's `render()` runs, so the id is final when the
  token is created and solid2's string-eager arithmetic loses nothing.
  Ordinary solid2 arithmetic produces the wire strings for free, and
  `solid_node.math`'s symbolic degree-trig mode works untouched because
  it dispatches on the base class.
- **Qualified id syntax: dotted instance path** (`x_axis.motor`).
  jokenizer parses it as member access, so the client holds a nested
  driver map and needs no evaluator grammar change.
- **Client parity: max |Python − client| 2.5e-14** over 182
  evaluations (4.3e-16 on composed world matrices), with a false-pass
  guard: without the `^`→`pow` rewrite the same expressions diverge by
  up to 0.186. Two instances of one class serialized distinct ids and
  bound distinct values.
- **OpenSCAD snapshot substitution costs nothing.** Binding drivers
  numerically and leaving `time` unbound is already what
  `set_state`/`self.time` do: driver terms collapse to literals at
  emission, `$t` stays live (`--animate` frames differ), and the mixed
  formula survives partial substitution. OpenSCAD support stays, as a
  snapshot camera — trace-driven OpenSCAD animation is excluded
  outright, not deferred.
- **`isAnimated` (`includes('$t')`) is replaced by the free-variable
  set** read off the parsed expression tree — it separates static,
  driver-only, and mixed expressions, and enables recomputing a subtree
  only when one of *its* drivers changed.
- **The shipped state bank cannot address same-named drivers on
  sibling instances** — `Sim` enumerates the root class only and
  `set_state` propagates one flat dict — while a bank keyed by the
  qualified id drives both axes independently with `DriverState`/
  `RampProgram` unchanged. The gap is addressing, nothing else.

The spike names eight seams (FINDINGS §"Seams stage 3a must open") —
now design requirements for the next stage rather than open questions:
a symbolic binding mode distinct from numeric snapshots (never a
relaxation of `_validate_state`); qualified per-instance state binding
with `time` staying global; a guaranteed-linked pass (today
`set_state`'s child walk renders without linking, so an unlinked
instance would qualify to the bare local name — a silent collision);
an identifier rule for derived names (a list-held child's `axes-0`
parses as subtraction); one tree-walk authority enumerating qualified
drivers for both the Sim bank and the document driver table; qualified
instruction lookup and targets; parity testing against the real widget
evaluator with `evalExpr` taking a driver map; and build-path defaults
(sharpened: `Sim` on a driverless root fails today).

Incidental finding: ADR-022 is stale — its "known defect" is fixed in
the shipped widget evaluator and its two-evaluator premise no longer
holds (one TS evaluator remains); cross-runtime parity is still
unenforced by any test.

## Implementation status (2026-08-25)

- **Stage 1 implemented and archived** as change
  `2026-08-25-multi-driver-state-seam`: `set_state`/`clear_state`
  multi-driver binding with `set_keyframe` as the exact time-only
  wrapper, domain-typed ports with causal `connect()`, and the
  `_driver`→`_animator` tag rename. 775 framework tests green,
  v8-engine 33/33 unchanged.
- **Stage 2 implemented** as change `stepped-simulation-layer`:
  `solid_node/simulation/` (frozen `Driver` declarations, per-sim
  state, integer-exact `RampProgram`, design-unit `Instruction`
  targets, fixed-dt `Sim` with deferred actions and cadence cost
  accounting, `ScenarioTest`). The spike migrated onto the shipped
  package (its harness deleted) and revalidates all five verdicts.
- One compatibility caveat surfaced by the spike migration, recorded
  in `spike/FINDINGS.md`: `set_keyframe`'s unchanged-behavior contract
  holds for every *caller*, but a subclass that overrides `set_state`
  now intercepts keyframing too, since `set_keyframe` routes through
  it.

## Open questions (updated after stages 1–2 and the expression spike)

Resolved since the last revision: **expression representation** (the
2026-08-26 spike decided the eagerly-qualified token and measured
parity; what remains is stage-3a implementation, not an open design
question) and the **`_driver`/`Driver` naming collision** (stage 1
renamed the ADR-023 tag to `_animator`/`_animated_nodes`).

Still open:

- **Instruction semantics v1.** Held to target + duration + linear
  ramp. Sequencing ("home X, then home Y") is the beginning of a
  program — that is the G-code layer's job; faking it in the UI schema
  would fight the real thing later. (Ramp mechanics themselves are
  spike-validated.)
- **Scenario assertion cadence defaults** — resolved structurally by
  the first spike (cadence budgets assertion cost; ticks are free);
  the numeric default per model size remains a project-level choice.
- **Document schema versioning** for the driver table and richer
  expressions (ADR-034/ADR-035 declared-API rules, ADR-051's
  producer-owned time). The expression spike settled the id scheme
  (qualified dotted instance paths) but not the schema shape or
  version gate.
- **Build-path defaults.** The CLI build/test path renders before any
  simulation exists, so a driver-declaring assembly must bind its own
  declared defaults in `__init__` to be buildable today; the
  expression spike sharpened it (`Sim` on a driverless root whose
  children declare drivers fails outright). Since `node/` cannot
  import `simulation/`, the answer must live in the loader/manager or
  a hook the simulation package offers — the tree-walk driver
  enumeration (spike seam 5) is the natural place.
- **Time-driver unification.** `Sim` does not auto-bind `time`; a node
  reading `self.time` under a simulation still gets symbolic `$t`.
  Unifying the built-in time driver with the snapshot belongs to the
  stage that also serializes the driver table. `time` stays *global*
  (unqualified) — the one entry that should propagate flat.
- **Unit-story unification.** `Driver.scale` (instruction targets) and
  `Port.scale` (geometry binding) state the same physical ratio in two
  places; unify when the viewer needs one authoritative unit story.
- **`range` is metadata, not a clamp.** Nothing enforces declared
  driver ranges (a crash scenario deliberately drives past travel); a
  later UI story must not assume clamping. Sliders may use `range` as
  presentation bounds only.
- **ADR-022 staleness.** Its "known defect" section and two-evaluator
  premise no longer describe the shipped code; the stage that makes
  the evaluator driver-aware should revise ADR-022 and finally put
  parity under test.

## First validation targets

- **Metamaquina2**: one axis end-to-end — instruction button → driver
  increments → carriage motion → scenario test. The originating
  empirical project for the non-periodic requirement. (The spike's
  stand-in axis proves the mechanics; the real project validates the
  ratified API.)
- **v8-engine**: unchanged behavior through the derived-phase path;
  proves the periodic subset and the closed-form escape hatch survive.

## References

- solid_node/node/assembly.py — `time` property, `set_keyframe`/`clear_keyframe`
- solid_node/node/base.py — `_render_stack`, `_tag_driver`, absolute matrix composition
- solid_node/node/operations.py — access-time symbolic resolution
- solid_node/test.py — `@testing_instant`, `@testing_steps`
- projects/v8-engine/v8_engine/kinematics.py (shop workspace) — the
  hand-built closed-form signal graph this design generalizes
- Modelica Standard Library, `Modelica.Mechanics.Rotational` and
  `Modelica.Blocks` — reference art for connector pairs vs causal
  signal blocks
