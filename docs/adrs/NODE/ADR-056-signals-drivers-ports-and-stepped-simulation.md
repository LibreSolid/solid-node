# ADR-056: Signals, drivers, ports, and stepped simulation

**Status:** Proposed (design draft; core spike-validated 2026-08-25,
expression representation spike-validated 2026-08-26); amended
2026-08-27 by `driver-attribute-reads`

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
> implementation — still applies before any of this lands. Sections
> below dated later than this preamble record what has since gone
> through that flow: the stage log under "Implementation status" and
> the ratified amendment that precedes it.

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

## Amendment (2026-08-27): a declared driver is read as an attribute

Ratified and shipped by change `driver-attribute-reads`. The draft
above named the two class-level declarations a node carries but never
settled how a driver is *read*; stage 1 shipped one shape and stage 2
brought the other, and the mismatch only became legible in project
code. This section decides it.

### What was wrong

A node acquired two kinds of declared class metadata that look
identical at the point of declaration:

    motor    = Driver(default=8000, unit='ustep', dtype=int, scale=...)
    position = TranslationalPort(unit='mm', scale=...)

Both are class attributes. Both are discovered by the same MRO scan
over `vars()`. Both name something whose VALUE belongs to one instance
while the DECLARATION belongs to the class. But they were read in two
different ways: the port as `self.position`, because `Port` is a
descriptor, and the driver as `self.state['motor']`, through a mapping
keyed by a string the class had already spelled out.

The string is the problem. It is not checked against the declaration
it depends on, so a typo is a runtime error rather than a name error;
it does not read like the declaration three lines above it; and it
offers a second, parallel vocabulary for a thing the framework already
had one for. Metamaquina 2 — a root assembly declaring `x`, `y` and
`z` and then reading three string keys — is the first real machine
where the asymmetry is visible in ordinary project code.

The `state` mapping was not designed as an alternative to a descriptor
read. It is the shape stage 1 shipped: `set_state` landed in
`multi-driver-state-seam`, and `Driver` did not exist until
`stepped-simulation-layer` came after it. Everything the mapping could
do that an attribute could not — read a name nothing declares, read
`time`, enumerate what is bound — is a consequence of that ordering,
not a capability anyone chose.

The drivers of the decision: one declaration shape should have one
read shape, and `Port` already established which one; nothing is
released, so there is no compatibility claim to weigh against removing
the older surface; a framework with two ways to read one value has to
keep explaining the difference, and every project has to pick; the
node layer must not acquire a dependency on the simulation layer; and
a mistake should fail loudly at the earliest moment it is legible.

### The decision

**A driver declared on a node is read as an attribute of that node,
and that is the only way to read it.**

`DriverDeclaration` — the marker in `solid_node/node/qualified.py`
that stage 3a introduced so the node layer could recognize a
declaration — becomes a descriptor. `__get__` returns the declaration
on class access and the bound value on instance access. The simulation
layer's `Driver` inherits the read and gains nothing of its own.

The descriptor lives in the node layer, not beside `Driver`, because
handing back a bound value and delivering the entry in the first place
are the same responsibility over the same `AssemblyNode._states` dict.
The layering this ADR drew is unchanged: the node layer recognizes a
declaration, qualifies it, delivers its state and now hands it back;
what a driver MEANS — native units, integer dtype, ramps — stays in
the simulation layer.

It is a DATA descriptor. `__set__` is defined and raises, because a
`__get__`-only descriptor loses to an instance attribute, so
`self.x = 5` would silently shadow the driver for every later read and
surface as wrong geometry rather than as an error. Defining `__set__`
also leaves `_attr_name_for` — which derives child names by scanning a
node's `__dict__` — seeing exactly what it saw before.

The name a declaration is bound under is kept in a private non-field
slot written through `object.__setattr__`, because `Driver` is a
frozen dataclass and a `name` FIELD would join the generated `__eq__`,
`__hash__` and `__repr__` — making two identical declarations on
different attributes compare unequal.

Three consequences follow, and are decided here rather than left open:

**The `state` mapping is removed.** `_BoundState` and the
`AssemblyNode.state` property are deleted. `self.time` is the only
read for animation time, and `qualified_drivers(root)` remains what
`docs/architecture.md` already called it: the one authority on what
drivers a machine has.

**`set_state` refuses a name no declaration bears.** A bare name no
declared driver in the tree carries, and a dotted name that is not a
qualified id the tree publishes, both fail naming the entry and the
declared ids; `time` stays exempt. Once the attribute is the only
read, an entry with no declaration behind it is unreachable, so
accepting one binds a value nothing can ever see. The check reuses the
`declared` map the propagation walk already builds for the ambiguity
test, and the rollback that test already performs.

**A driver may not shadow a node member.** `__set_name__` walks
`owner.__mro__[1:]` and raises at class-definition time if a base
carries the name under anything that is not itself a driver
declaration. `AssemblyNode` has 36 public members, several of them
plausible driver names for a mechanical design — `color`, `shape`,
`mesh`, `state`, `time`. A driver name used to be confined to a
mapping key where it could collide with nothing; the attribute
namespace is new exposure, and this closes it at the moment it is
cheapest to read. Redeclaring an inherited driver stays legal, which
is how a subclass overrides a declaration.

### Consequences of the amendment

**Positive**

- Declaration and read are the same vocabulary, and a mistyped driver
  is a name error at the read or a rejection at the binding.
- Drivers and ports are now one concept with one shape.
- Two silent failure modes are gone: assigning over a driver, and
  declaring one on top of a node member.
- Binding is atomic against a name it refuses, like it already was
  against an ambiguous one.

**Negative / accepted**

- Breaking, deliberately. Every `self.state['name']` read, every
  `state['time']`, and every `dict(node.state)` assertion changed;
  fixtures that bound names they never declared now declare them, and
  one had to rename its driver because a CHILD node already held the
  attribute — the collision the guard exists for, found in the
  framework's own tests.
- `hasattr(node, 'x')` is `False` for an unbound driver and
  `getattr(node, 'x', default)` yields the default, because both
  swallow `AttributeError`. Accepted: nothing probes a node that way,
  discovery reads `vars()`, and any other exception type would break
  `copy`, `pickle` and `inspect`, which probe for optional dunders
  with exactly that idiom.
- Nothing publicly reports "what is bound on this node". The document,
  `qualified_drivers`, and `_states` for a debugger cover the real
  need; a per-node view, if one is ever wanted, is an enumeration
  surface to design rather than a reason to keep a second read path.
- `set_state` now builds its rollback snapshot on every call rather
  than only when a bare project-driver name is present, so the
  stepping loop pays for it. Measured at 2.0 µs/tick against a 32.1
  µs bare tick on the two-axis fixture — 6.7% of a bare tick, and
  three orders of magnitude below the millisecond mesh assertion that
  actually sets a scenario's runtime.
- Only the walk knows what is declared, and the walk renders. So a
  qualified id addressed to nobody, bound on a tree that was never
  bound, reports that tree's own unbound read before the name can be
  judged. This is the ordering trade-off the ambiguity path already
  carried; the first message still names a real problem.

### Alternatives considered for the read surface

**Put the descriptor on `Driver`.** Works — a throwaway monkeypatch of
`Driver.__get__` ran the driver, state, port, simulation and document
tests green. Rejected because it puts knowledge of
`AssemblyNode._states` in the layer whose whole point is to be
ignorable by a driverless node.

**Keep `self.x` and the mapping side by side.** The first draft of the
change did. Rejected: the mapping's three justifications are all
stage-1 residue rather than capability, nothing is released, and a
second read surface is a permanent explanation cost.

**Non-data descriptor.** Simpler, and silently wrong the first time a
project assigns over a driver name.

**A `name` field on the frozen `Driver` dataclass** instead of a
private slot. Rejected: it would make declaration equality depend on
where a declaration is bound.

**No shadowing guard.** Rejected: it converts a class-definition
mistake into wrong geometry with no message.

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
- **Stage 3a implemented (2026-08-26)** as change
  `instance-qualified-drivers`, opening all eight seams the expression
  spike named except evaluator reconciliation (seam 7, deferred to
  3b): the qualified id and `DriverToken` in
  `solid_node/node/qualified.py`; qualified `set_state`/`clear_state`
  delivery over a walk that links before recursing, with an ambiguous
  bare bind failing loudly; the symbolic serialization mode and
  document schema v2 with its `drivers` table; the one tree-walk
  enumeration authority in `solid_node/simulation/enumeration.py`
  feeding the `Sim` bank, qualified instructions, the driver table and
  build-path defaults; `Sim` binding the global `time` clock in
  seconds each tick; and declared defaults bound by the loader. 872
  framework tests green (813 baseline), widget vitest 43 green,
  v8-engine 33/33 unchanged, and both spikes revalidate — the
  expression spike now as caller validation on the shipped API, with
  its shims deleted.
- One implementation decision worth recording: the node layer needs to
  *recognize* a driver declaration in order to qualify it and deliver
  a qualified entry, and it may not import `simulation/`. A
  `DriverDeclaration` marker base class in
  `solid_node/node/qualified.py`, subclassed by `simulation.Driver`,
  places that dependency explicitly; the node layer reads only
  `default` off it.
- **Stage 3b implemented (2026-08-26)** as change
  `driver-aware-viewer`, closing the expression spike's last seam
  (seam 7, evaluator reconciliation). The widget evaluator takes an
  evaluation scope (`{time, drivers}`) with the nested driver map the
  spike recommended, so a dotted qualified id resolves as member
  access and the grammar is unchanged; `isAnimated`'s substring test
  is gone, replaced by the free-variable set read off the cached parse,
  which is what decides that a driver change re-evaluates only the
  operations naming it. The loader gate inverts: a non-empty `drivers`
  table now loads and renders at its declared defaults, and what is
  refused is a document naming an id its own table does not declare.
  The handle gained the driving API — `drivers()`, `driver`,
  `setDriver`, `onDriverChange`, `instructions()`, `trigger` returning
  `{done, cancel()}` — with values in native units, no clamping, and
  ramps advanced on wall-clock elapsed time with exact landing and
  last-wins replacement, mirroring `Sim`'s programs without claiming
  its determinism. The producer gained the `instructions` table,
  additive within `version: 2`. Cross-runtime parity is finally
  enforced by a committed, producer-generated fixture run against the
  shipped evaluator module, and ADR-022 is revised to the resulting
  reality. 879 framework tests green (872 baseline), widget vitest 99
  green (43 baseline), v8-engine 33/33 unchanged, both spikes
  revalidate. The widget bundle is not rebuilt in the bench (its
  `dist/` is a symlink into the primary checkout), so the change is
  carried by TypeScript source and vitest; packaging rebuilds it, as
  in stage 3a.
- The one judgment worth recording from 3b: design-to-native
  conversion is reproduced in the client down to Python's
  round-half-to-even, and the parity fixture pins it. A target landing
  exactly between two native units is not hypothetical for an integer
  driver, and "nearest" is not a single rule across languages.
- **Stage 3c implemented (2026-08-26)** as change
  `layered-driver-controls`, putting the chrome on the 3b API: a
  button per instruction and a bounded slider with a numeric readout
  per driver, built from the document's own two tables and calling the
  same `setDriver`/`trigger` a host calls, so a value set on screen and
  one set through the handle are indistinguishable to expressions,
  listeners and readbacks. Scoping is strict per layer — an id belongs
  to the focused layer iff it splits into the focus path's segments
  plus exactly one more, root focus selecting the bare ids — so a root
  declaring everything on its children legitimately shows no controls,
  which is product pressure toward declaring machine-level instructions
  on the machine rather than a defect. An in-widget breadcrumb derives
  its navigable children from the tables rather than the assembly tree
  (the distinct next segments strictly below the focus), which reaches
  every declaring layer by construction and omits a child with nothing
  declared beneath it for free; it drives the same internal
  focus-changed path a host `setRoot` does, so the two can never
  disagree. `driverControls: 'inline' | 'none'` lets a host building
  its own instrument panel suppress the pixels while keeping the whole
  driving API, and a driverless document renders exactly what it
  rendered before. Every decision lives in a pure `controls.ts` tested
  in plain node (this bench has no DOM test framework and may install
  none); the thin DOM layer's proof is a live headless-Chromium drive
  of the spike machine against a fresh temp bundle. 884 framework tests
  green (879 baseline), widget vitest 141 green (99 baseline).
- **`range` is pinned to design units** by the same change: the units a
  maker thinks in and instruction targets are stated in, whatever
  `scale` says, published verbatim beside a native `default`. The
  slider is the first consumer that must convert it, so its units could
  not stay unstated; pinning was free because no shipped project
  declares a scaled range yet.
- The judgment worth recording from 3c: the chrome does not clamp, and
  says so rather than hiding it. A value bound past the declared travel
  shows a slider pinned at its end beside a readout of the true value
  (live: `setDriver(-400)` on a 0..100mm axis reads `-5`), because a
  crash is a thing a simulation must be able to show. Raycast
  click-to-focus picking on the 3D scene was deliberately excluded and
  remains deferred; the breadcrumb is the whole focus affordance.
- **The read surface settled (2026-08-27)** by change
  `driver-attribute-reads`, which amends this ADR rather than adding
  one — see the amendment section above for the decision and its
  alternatives. `DriverDeclaration` became a data descriptor, the
  `state` mapping and `_BoundState` are gone, `set_state` refuses an
  undeclared name, and a driver may not shadow a node member. Every
  caller in the framework converged, including two fixtures that had
  bound names they never declared and one whose driver collided with a
  child node held on the same attribute. Validated in Metamaquina 2,
  the originating machine, whose root declared `x`, `y` and `z` and
  read three string keys: 902 framework tests green and its own 12
  pass.

## Open questions (updated after stage 3b)

Resolved since the last revision: **expression representation** (the
2026-08-26 spike decided the eagerly-qualified token and measured
parity; stage 3a shipped it) and the **`_driver`/`Driver` naming
collision** (stage 1 renamed the ADR-023 tag to
`_animator`/`_animated_nodes`).

Resolved by stage 3a (`instance-qualified-drivers`):

- **Document schema versioning.** Settled: shared `version: 2` across
  `manifest.json` and `viewer.json`, adding a `drivers` table of
  qualified id → `{default, range, unit, dtype, scale}` verbatim from
  the declaration, with expressions free to reference qualified ids and
  preserved verbatim under the same producer guarantee `$t` has. A tree
  declaring no drivers serializes an empty table, which is exactly the
  version 1 document; consumers gate on the table, not the number, and
  a consumer that cannot evaluate driver expressions refuses a
  non-empty one rather than rendering a wrong pose.
- **Build-path defaults.** Settled in the loader: `load_node` binds the
  declarations' own defaults across the tree by qualified id, through
  the enumeration authority in `simulation/`. `node/` still imports
  nothing from `simulation/`, and the rejected alternative — a
  `node/`-level hook the simulation package registers into — would have
  hidden the dependency rather than placed it. A tree declaring no
  driver is not touched at all, so a driverless project loads exactly
  as before.
- **Time-driver unification.** Settled: `Sim` binds the global `time`
  entry every tick to the exact instant `k*dt` **in seconds**, computed
  from the integer tick count and never accumulated, so `self.time`
  under a simulation reads the stepped clock. Seconds and not a
  normalized 0..1 fraction, because a scenario's duration is unknown at
  declaration and a non-periodic machine has no natural period. `time`
  stays *global* (unqualified) — the one entry that propagates flat —
  and the ADR-008 symbolic `$t` path outside simulations is untouched.

Resolved by stage 3b (`driver-aware-viewer`):

- **Client-side driver evaluation.** Settled and shipped. `evalExpr`
  takes a scope carrying `$t` and a nested driver map; free-variable
  sets read off the parsed tree replace the substring test and bound
  re-evaluation to the operations that name a changed driver; a
  non-empty driver table is rendered rather than refused, and only a
  document naming an undeclared id still fails loudly. The driving API
  is on the handle, in native units, with no clamping.
- **ADR-022 staleness.** Resolved: ADR-022 is revised (single
  evaluator, recorded defect fixed, driver expressions in scope) and
  parity is no longer merely measured — a committed fixture of
  producer-computed values runs against the shipped evaluator module,
  and disabling the `^` rewrite fails it by up to 0.186. Seam 7 of the
  expression spike is closed.

Resolved by stage 3c (`layered-driver-controls`):

- **UI chrome for drivers.** Settled and shipped. Sliders, instruction
  buttons and readouts are the widget's, scoped strictly to the focused
  assembly layer and reachable through an in-widget breadcrumb, with a
  host option to suppress them. They use `range` as presentation bounds
  only, exactly as the open question required: the slider pins at an end
  and the readout stays truthful. A driver declaring no range gets a
  numeric input, because bounds cannot be invented from a default.
- **`range` is metadata, not a clamp.** Still true, and now first
  consumed: nothing in the framework or the widget clamps, and the
  chrome shows an out-of-range value rather than pretending the machine
  stopped. What the change adds is the units the metadata is stated in
  — design units, like an instruction target — which the slider forced
  and which the `simulation` spec now states.

Still open:

- **Instruction semantics v1.** Held to target + duration + linear
  ramp. Sequencing ("home X, then home Y") is the beginning of a
  program — that is the G-code layer's job; faking it in the UI schema
  would fight the real thing later. (Ramp mechanics themselves are
  spike-validated; `trigger` is the seat that layer will occupy.)
- **Click-to-focus picking.** The breadcrumb moves focus; picking a
  part in the 3D scene by raycast does not exist and was excluded from
  stage 3c rather than half-built. A maker pointing at the axis they
  can see is the obvious next affordance.
- **Scenario assertion cadence defaults** — resolved structurally by
  the first spike (cadence budgets assertion cost; ticks are free);
  the numeric default per model size remains a project-level choice.
- **Name sanitization for list-held children.** A driver reachable
  only through an `<attr>-<index>` name is forbidden loudly in v1, not
  sanitized. Bijective sanitization is a recorded, compatible
  extension for when a real project needs drivers on list children.
- **Unit-story unification.** `Driver.scale` (instruction targets) and
  `Port.scale` (geometry binding) state the same physical ratio in two
  places; unify when the viewer needs one authoritative unit story.
  Stage 3c made the gap visible rather than closing it: `unit` names
  the NATIVE unit while the value beside it is now design units, so the
  spike's axis honestly reads `50 ustep` for 50 millimetres of travel.
  The chrome shows what the declaration says; a declaration with two
  units and one name is the thing to fix.

## First validation targets

- **Metamaquina2**: one axis end-to-end — instruction button → driver
  increments → carriage motion → scenario test. The originating
  empirical project for the non-periodic requirement. (The spike's
  stand-in axis proves the mechanics; the real project validates the
  ratified API.)
- **v8-engine**: unchanged behavior through the derived-phase path;
  proves the periodic subset and the closed-form escape hatch survive.

## References

- solid_node/node/qualified.py — `DriverDeclaration` (marker and data
  descriptor), qualified id, `DriverToken`
- solid_node/node/assembly.py — `time` property, `set_keyframe`/`clear_keyframe`
- solid_node/node/base.py — `_render_stack`, `_tag_driver`, absolute matrix composition
- solid_node/node/operations.py — access-time symbolic resolution
- solid_node/test.py — `@testing_instant`, `@testing_steps`
- projects/v8-engine/v8_engine/kinematics.py (shop workspace) — the
  hand-built closed-form signal graph this design generalizes
- Modelica Standard Library, `Modelica.Mechanics.Rotational` and
  `Modelica.Blocks` — reference art for connector pairs vs causal
  signal blocks
