# Open-run mechanical simulation

Status: proposed architecture and authorized experimental work, 2026-09-12.
This is the full design proposed in the pilot conversation, followed by a
mechanism spike campaign. It is not an accepted ADR, an OpenSpec baseline, or
an implemented public API. The pilot explicitly authorized this folder and its
spikes on framework `main`; framework and viewer production code stay outside
this experiment. Initial framework HEAD: `518bed114c94697a58d95e85ad2831c8fcd9f3a3`.

The mechanical-law, browser-interface and current-planning sections record the
pilot's subsequent acceptance of action-based controls and ratification of the
input/instruction/control relationship, build-time `running(r)` law extension
and Curta acceptance scope. On 2026-09-13 the pilot selected the completed
Pascaline as first validator, following the assessment's finite-time kinematic
fall recommendation, and preserved Curta as second. Those scoped decisions do not
ratify this entire architecture, change a baseline spec, establish mechanical
acceptance evidence, or authorize production implementation.

The subsequent Pascaline readiness checkpoint is recorded in the
[active roadmap](roadmap.md): the sampled frozen-input fall passes, but a
narrow pawl-return collision in the unchanged production motion law keeps
the readiness gate open. This is project evidence to resolve before production
proposals, not a change to the proposed framework architecture or solver class.
The authorized bounded correction investigation subsequently found a sampled
delayed-return candidate on unchanged parts. It leaves the pawl pin-supported
after one independent input step and needs retained contact state. The pilot
approved carrying that direction into the project-owned running draft on
unchanged parts; production behavior is still unchanged and full ratification
remains ahead.

## Intent and the boundary that matters

The maker operates physical components and observes the machine in 3D. A
Curta has individual selector positions, rotating shafts, contact surfaces,
carry levers, springs and numbered wheels. No calculator algorithm computes
an answer and positions the wheels to match. Arithmetic is the maker's
interpretation of the marks on those wheels. A G-code interpreter supplies
actuator commands; it does not prescribe the positions of downstream parts.

One framework execution engine must serve Curta, a motor running while a
maker independently steers a car, and a printer whose program can pause and
resume. Models supply their components and mechanical relationships. The
runtime has no calculator, engine or printer dispatch branch. There are no
alternative levels in which a logical calculator substitutes for mechanics.

The original empirical limitation was loss of mechanical history when every
pose was reduced to a function of the current input values. Expression sharing
repairs construction and publication growth but does not recover that history.
The recorded Curta expression-graph manifest is 1,669,980 bytes; its final
warm/cold export memory peaks were 831,078,400 and 1,179,168,768 bytes. The
gigabyte figure is process-tree build memory, not the published formula size.
See [the archived evidence](../../openspec/changes/archive/2026-09-11-expression-graphs/evidence.md).

## Three execution modes

| Mode | What determines pose | Time controls |
| --- | --- | --- |
| Untimed | Current inputs | No playback clock |
| Looping | Current inputs and a position within a cycle | Play, pause, scrub, repeat |
| Running | Previous mechanical state plus new input movements | Run, pause, step, reset; replay recorded history |

Free-running simulation selects both a clock that never wraps and execution
that retains mechanical state. Removing the modulo from today's browser clock
would provide only the first half. Untimed input posing remains useful and is
not necessarily a static model; existing undeclared-time behavior remains
compatible.

Proposed authoring syntax, not currently implemented:

```python
time = Time(loop=2.0)   # Existing: repeat a two-second timeline.
time = Time.running()  # Proposed: elapsed seconds and persistent mechanics.
```

`self.time` in running mode is elapsed simulation seconds. There is no infinite
`loop`, zero-length loop, automatic reset, or implicit rescaling of existing
`$t` documents. A periodic component may compute its local phase from its
coordinate: the cam's phase wraps after two crank revolutions, but crank travel,
the machine clock, and every other component retain their state. A changing
motor rate is integrated over the interval for which it applies; multiplying
the latest rate by all elapsed time would incorrectly rewrite prior motion.

Numerical resolution belongs to the simulation run, separately from playback
speed. Speed changes how many simulation steps are processed per wall second;
it must not change the mechanical answer. Public stepping retains a positive
finite `dt` and integer outer ticks. Internal event localization can subdivide
a tick; precise event semantics and tolerances need validation. A worker that
cannot keep up reports the actual simulation clock and does not skip mechanics
to catch up with the wall clock. A paused page does not accumulate an invisible
backlog by accident; background-tab policy must be explicit.

## Runtime-owned mechanical state

Each run owns the positions of its joint coordinates and the additional memory
required by its mechanical relationships: the engaged contact, the side of a
clearance taken up, or the stable branch of a latch. State is associated with
component and relation instances, never shared through class declarations or
process-global registries.

Three values must be distinguished:

1. A coordinate's previously committed position.
2. A movement requested by an input.
3. The position admitted by the mechanism after resolving that movement.

The previous position is not another binding that fixes a coordinate in place.
Today's solver clears previous bindings and propagates from bound coordinates
to unbound ones. Retaining all coordinates in that solver makes both ends of
a relation already bound. Running simulation needs a new solving context;
removing `clear_solved()` is not the implementation.

Ordinary derived quantities remain calculations over the current mechanical
state: a belt's shape follows pulley positions, and a rod's placement follows
its endpoints. Every intermediate expression or ordinary port need not be
stored. The runtime can retain all joint coordinates for snapshots while
treating only the mechanically independent ones as independent unknowns.

In this kinematic execution model, an undriven and unconstrained coordinate
holds position unless a mechanical law advances it. Memory alone does not
imply mass or inertia. Initial state must be mechanically admissible; initial
coordinates, local contact state and consistent relation phase belong together.

Rendering is still pure:

```text
next mechanical state = resolve(previous state, input movements, interval)
pose                  = position parts(current mechanical state)
```

An inspection, snapshot or extra rendering pass advances nothing. Do not put
state integration in `render()`, `simulate()`, a port read, or a law's existing
`forward()` callback. These can be evaluated repeatedly at the same instant.

## Mechanical law interface

Keep the existing authoring boundary:

```python
shaft.turn.drives(wheel.turn, law=meshing)
```

The framework executes the supplied relationship. A permanently engaged gear
pair can retain its existing algebraic law. An intermittent pair describes
movement over the interval in which it is engaged, for example:

```text
change in wheel angle = -tooth ratio * change in shaft angle
```

While disconnected, the wheel retains its attained position. Re-engagement
must follow contact geometry and relative phase; it cannot arbitrarily reset
either part. A bare `when=engaged` switch on an absolute formula is therefore
insufficient. The condition and the transition across its boundary are part
of the law.

| Running-law capability | Meaning |
| --- | --- |
| Motion constraints | Relations between candidate coordinate movements |
| Event boundaries | Contact, release, stop, or another mechanical transition |
| Local state changes | Mechanical memory changed by that transition |

The pilot ratified the build-time declaration extension below after reviewing
the spikes and the existing law contract. These capabilities build explicit
mathematical descriptions that can be exported, rather than arbitrary runtime
Python mutations. A law factory may still inspect its realized component owners
and resolved geometric parameters at build time. It must declare all runtime
dependence in the mechanical program.

Simultaneous constraints are resolved together. Two incompatible prescribed
inputs on one rigidly connected group are a conflict, not last-writer-wins.
Redundant but consistent constraints, reverse solving, disconnected groups and
closed loops need explicit support boundaries. Nonlinear loops may require a
numeric solver; a propagation-only solver must refuse what it cannot solve.

### Running law protocol — pilot ratification, 2026-09-12

The pilot explicitly ratified adding one optional method, `running(r)`, to
the existing project-owned law protocol. Keep nodes, joints, frame conventions,
`.drives(...)`, grouped ends and the existing factory called with realized
coordinate owners. The factory still returns the law; the framework acquires
no catalogue of gears, latches or calculator mechanisms.

`running(r)` executes once when building a relation's compiled running
description, not once per simulation tick. Its arguments and returned symbolic
references describe the program. The law object's Python fields may hold
geometry-derived parameters and pure profile helpers, but never mutable live
mechanical state. Python and the browser execute the published description
through their runtime implementations, not through per-frame Python callbacks.

The ratified authoring shape, illustrated with one carry relation, is:

```python
(dial.turn & bell.turn).drives(
    (lever.travel, next_shaft.turn),
    law=carry_contact,
)
```

`carry_contact` is the existing kind of project factory. Its returned law can
declare running behavior as follows. This is an API design example, not a
working Curta implementation: the helper methods stand for project-owned
measured profiles, geometry/frame offsets and fitted phase checks, omitted
here. The actual Curta slice still needs its geometric acceptance evidence.

```python
class CarryLaw:
    def running(self, r):
        dial, bell = r.sources
        lever, shaft = r.targets

        latched = r.state("latched", initial=False)

        r.event(
            "trip",
            crossing=self.pin_drop(dial) - self.trip_height,
            direction=1,
            updates={latched: True},
        )

        r.event(
            "reset",
            crossing=self.reset_lift(bell) - self.reset_height,
            direction=1,
            updates={latched: False},
        )

        r.equal(
            lever,
            self.slider_path(dial, bell, latched),
        )

        engaged = latched & self.tooth_window(bell)

        r.on_enter(
            "mesh",
            engaged,
            require=self.phase_match(bell, shaft),
        )

        r.equal(
            r.delta(shaft),
            self.ratio * r.delta(bell),
            when=engaged,
        )
```

The declared capabilities have these meanings:

- `r.state` declares retained local memory, stored separately for each
  realized relation and simulation run. Its initial value participates in
  validating the complete initial mechanical state; it is not a command to
  reset that state on each build, render or tick of an existing run.
- `r.equal` declares a constraint on coordinate positions or movements.
  `r.delta` is movement within the current event-free interval, not total
  travel since initialization. When an engagement is inactive its conditional
  constraint contributes no coupling: other valid connections may move the
  coordinate, and an otherwise undriven coordinate holds its attained state.
- `r.event` declares a crossing and the local-memory update to settle there.
  It does not mutate that memory while the Python declaration executes.
  `r.on_enter` checks admissible engagement, including tooth phase; neither
  part may be reset to make an incompatible mesh fit.
- The runtime localizes crossings, contact changes and profile boundaries,
  settles simultaneous events, and commits coherent state. These are not
  endpoint-only tests or events whose order is chosen by rendering cadence.

Compatibility and first implementation scope are part of this ratification:

1. Existing `forward`/`inverse` laws retain their absolute-position meaning.
   Do not silently reinterpret them as displacement laws.
2. Supported ordinary algebraic laws compile into running constraints without
   requiring their authors to add another method.
3. History-dependent laws provide the running description. A running-only law
   is not silently treated as a valid old looping/pose law.
4. Begin with the spike's piecewise-affine solving class. Unsupported laws
   fail during compilation, with no hidden Python execution fallback and no
   claim of general nonlinear contact or closed-loop solving.
5. State mutation remains runtime-owned. Never use `forward()`, `render()` or
   `simulate()` as a place to accumulate mechanical history.

This records ratification of the extension and demonstrated declaration
semantics. Complete validation rules, numeric limits, wire representation,
tests and the repository-owned OpenSpec changes still need preparation and
review. It does not ratify the whole campaign, certify the omitted Curta
contact paths, or authorize implementation, integration or release.

## One step and mechanical events

1. Read the committed state and input movements due at this tick.
2. Resolve candidate motion through the affected relationships.
3. Find the earliest mechanical event along that motion.
4. Advance to it, settle the resulting contact/engagement changes together,
   and continue through the unconsumed interval.
5. Publish a coherent state for display.

A fast crank movement must not skip an engagement between display frames.
An event enabled by another event at the same instant must settle without
advancing time. Updates read one previous snapshot and commit together;
declaration order must not select the physical result. Conflicting writes,
chattering or a solve that cannot converge must fail with component/relation
identities and preserve the last valid state. Commands report partial travel
and blocking rather than pretending they reached their target.

Non-interference requires constraints on the motion path. Remembering
positions does not prevent overlap, and testing only two endpoints can miss
an obstruction. Contact laws must be validated against the component geometry
with engagement as well as clearance evidence. Running a relation graph is
not proof of arbitrary geometry-wide contact response. Exact geometric
validation, contact-profile approximation and runtime numerical tolerance
must be reported separately; no volume epsilon legitimizes interference.

This prior-value/event-iteration structure has established reference art in
the [Modelica execution representation](https://specification.modelica.org/maint/3.6/modelica-dae-representation.html).
That is design evidence, not a dependency decision or adoption of Modelica.

## Python-to-browser architecture

```text
Python model: geometry, joints, mechanical laws
                       |
                     build
                       v
       geometry + compact mechanical program
                       |
            +----------+----------+
            v                     v
     Python simulation     Browser worker
       and testing         running simulation
                                  |
                          coordinate snapshots
                                  v
                            browser viewer
```

Current export resolves joints/relations into pose expressions and does not
publish the relations themselves. A running document additionally carries:

- Stable joint/coordinate identities, frames and initialization.
- Input-to-coordinate connections and control metadata.
- Mechanical relations and their executable expressions.
- State slots, event conditions and state-update rules.
- Bindings from mechanical coordinates to geometry and flexible parameters.

The expression graph remains useful: new leaves read previous state and
candidate coordinates, and local expressions describe motion and events.
The runtime performs repeated solving and atomic state commits. A feedback
edge through previous state does not become an illegal cycle in the current
expression DAG. Same-instant cyclic constraints are a separate solver concern.
Compile the rules once, then execute them repeatedly. Never expand operation
history into the graph.

Python-authored laws must use the exportable vocabulary. Ordinary Python
branching over unknown runtime values, arbitrary dependency imports and
runtime CAD queries do not automatically become JavaScript. Refuse an
unexportable law by its model/source identity rather than silently freezing
it. This is the substantive language boundary beside instruction parsing.

The preferred first architecture extends the existing expression compilation
path and runs a generic numeric engine in a browser worker. It does not need
Python or a CAD kernel in the browser. Python and browser executors consume
one mechanical program and share a conformance corpus. If maintaining parity
becomes costly, a single compiled runtime can replace the two implementations
without changing model authoring or the published program contract.

Alternatives remain evidence-driven: Pyodide can execute the same Python
mechanical runtime in a worker, at a runtime download/startup cost; a native
Python service can produce snapshots, at the cost of a live service. Neither
alternative justifies machine-specific controller logic. This work does not
select the architecture for building CAD in the browser.

The running document needs a new capability/version boundary. An old viewer
must refuse it rather than display a plausible, incomplete animation. Model
builds publish geometry/program atomically. Live updates must invalidate or
explicitly migrate incompatible simulation state, not preserve coordinates
solely because strings happen to match.

## Runtime and program interfaces

Illustrative proposed API, not existing functionality:

```python
sim = Sim(machine, dt=1 / 240)  # Example resolution, not a universal default.
sim.move("crank", by=360, duration=2.0)
sim.run(0.5)
checkpoint = sim.snapshot()
sim.run(1.5)
sim.restore(checkpoint)
```

Names identify declared inputs. `move()` requests travel through the
mechanism; it never overwrites downstream coordinates. Its result distinguishes
completed, blocked and cancelled motion and reports actual displacement.
Continuous drives and simultaneous commands use that same interface:

```python
sim.rate("engine_motor", 720)              # Input units per simulated second.
sim.move("steering", to=20, duration=0.3)
sim.run(1.0)
```

Snapshots include the clock, component/relation state, active trajectories,
pending commands and the model/program identity. Restoring visible positions
alone cannot resume a partial movement. Reset restores the initial snapshot;
rewind restores a checkpoint and replays recorded commands, never negative dt.
Restoring a mismatched model must fail before changing live state.

G-code parsing is an adapter producing coordinated actuator commands. The
interpreter owns language state, such as positioning mode and program cursor;
mechanical components own machine state. Manual controls and every instruction
source enter the same command interface. Command ownership must prevent two
independent sources from silently overriding one actuator. G-code dialect and
supported vocabulary are explicit; no full firmware compatibility is implied.

Pause simulation freezes everything. Pause program suspends that program's
actuator trajectories at their current progress, retaining cursor and remaining
motion; independently driven components continue. A future actuator law may
specify deceleration rather than instantaneous rate cessation. Resume does not
repeat or skip the interrupted movement. Cancelling is a distinct operation.

## Browser interface

The pilot accepted the action-panel recommendation on 2026-09-12. This
accepts the interaction direction and implementation order below, not the
complete OpenSpec cycle or a particular Python/host API spelling.

Running controls submit movement requests; the runtime emits committed state
changes and command outcomes. There is no two-way binding between an editable
position and the mechanism. Nudge controls request finite relative movements;
hold-to-jog controls request a rate until released. Amount and rate editors
configure future commands, not current mechanical coordinates. Readouts follow
committed state and never feed another movement request back into the run.

Implement nudge and hold-to-jog first, then constrained 3D dragging through
the same command interface. Report completed, blocked, refused and cancelled
requests with actual admitted motion. A blocked drag accumulates no hidden
movement for later execution. Release, lost pointer capture and lost window
focus end the manual jog; manual controls never silently replace a program's
ownership of the same input. No live-time scrubber is offered: seeking belongs
to recorded history and replay. Existing static/looping position controls keep
their existing semantics and do not become running mechanical controls.

- Run, pause, step, speed and elapsed simulation time.
- Physical picking and constrained dragging bound to declared inputs.
- Actual input positions and blocked-motion feedback.
- Reset to the initial configuration.
- Optional recording with checkpoints and replay for seeking.
- Program-level pause/resume independently of the simulation clock.

Internal mechanical state is not rendered as an extra bank of editable
calculator registers. In Curta the visible answer is the geometry of the
numbered wheels. Eight physical selectors require eight physical input
coordinates, not a single numerical operand pretending to be the mechanism.

The renderer can drop intermediate display frames but not mechanical events.
It draws absolute poses from committed coordinates, retaining today's rest
placement and joint-frame conventions. Large STL data is loaded once; moving
the machine sends coordinates or transforms, not rebuilt CAD.

### Inputs, instructions and controls — pilot ratification, 2026-09-12

The pilot explicitly ratified the following relationship after reviewing the
Python declaration sketch and asking how controls relate to instructions:

- An **input** exposes a mechanical coordinate as an entry point for movement
  requests. It does not store an additional editable copy of that coordinate.
- An **instruction** is a reusable, named movement request: for example, turn
  the crank another revolution over six simulated seconds. A declaration
  executes nothing and carries no mutable run state. Each invocation creates
  a command against the actual mechanical state; requested movement can be
  completed, blocked, refused or cancelled.
- A **control** describes how a person issues requests: clicking a button,
  holding a jog control or dragging a part. A button for a named instruction
  references that instruction; it does not repeat its movement definition.
  Python scripts and the viewer invoke the same named action through the same
  command semantics and mechanical constraints.
- Named instructions receive ordinary buttons by default, preserving the
  current authoring convenience. An optional controls declaration adds jog/drag
  interactions or customizes presentation. Authors do not maintain two
  matching lists just to make named actions usable.
- Not every control needs a named instruction. A jog starts a rate command on
  press and cancels that command on release; its duration comes from the
  interaction. A nudge is an inline button/relative-request convenience, not a
  second instruction execution engine. Give a movement a named instruction
  when it needs reuse from scripts or demonstrations.
- Instructions remain usable without a viewer. Both instructions and direct
  controls submit to the same runtime with the same ownership, admission and
  outcome rules. Neither controls nor instructions assign downstream wheel
  positions or manufacture carry state.

This ratifies the conceptual separation, shared execution path and default
presentation, not final constructor signatures, import paths or serialization.
The illustrative `Input`, `Instruction.move`, `Button`, `Nudge` and `Jog`
spellings remain proposed. Today's `Instruction(targets, duration)` keeps its
existing target-ramp contract for existing modes; the running-mode extension
must be explicit in the later repository-owned proposals, not a silent
reinterpretation of old documents. No complete OpenSpec cycle, implementation,
ADR or release choice is ratified by this record.

## Resource and verification discipline

Working memory should depend on the model, active work and deliberately kept
history, not elapsed ticks. Current `Sim` appends every tick to `trajectory`;
running mode needs optional/bounded recording. A printer's deposited material
is deliberately growing output and needs its own representation and budget.
No claim of constant total memory can include an unlimited retained toolpath.

Parity requires more than similar pictures: pin coordinate values, event
identities/order, blocked commands, local states and checkpoint restoration.
Use exact equality for discrete state and specified tolerances for numeric
coordinates. Test near event boundaries so numeric variation cannot quietly
change a contact branch. Vary display cadence and numerical step independently.

## Spike campaign

Keep code, tests, fixtures, measurements and inspected images in this folder.
Spikes are experimental code, not a second production simulation package.

1. Connected pair: transmit motion, disengage, hold, re-engage without a jump.
2. Ratchet/latch: direction-dependent travel, backlash, stop and retained state.
3. A real Curta input-to-wheel-and-carry chain, physically actuated with no
   arithmetic result driving it; pin source measurements and limitations.
4. Concurrent motor/steering, then coordinated printer-style motion with
   program pause/resume, on the same generic runtime.
5. Python/browser conformance, frame-cadence independence, mid-operation
   checkpoint/replay, long-run memory, and deliberate broken-mechanism controls.

Tests must demonstrate the relevant failures before implementation, and
negative controls must show that a missing connection, wrong transmission or
lost event is detected. Pictures verify the machine actually posed from the
computed coordinates; they do not replace contact/clearance tests.

The present Curta root imports `simulation.arithmetic.calculate` and uses its
outputs to drive registers. That model must be migrated mechanically; opting
into running time cannot infer what is missing. Spikes may read its geometry
and measured contact evidence but must not call that arithmetic function or
use a calculator state machine. Whole-machine migration remains separate work
in the project repository.

## Ownership and architectural consequences

Framework: mechanical program, state/solver semantics, Python execution and
model authoring. Viewer: program consumer, worker, physical interaction and
display. Mechanical projects: their component geometry and supplied laws.
Instruction adapters: translation into the common actuator command interface.
The shop remains a host of published artifacts rather than an importer of
project Python. Framework and AGPL viewer remain separate repositories.

Production implementation would extend the state-only-in-drivers boundary in
ADR-056, the relation/solver exclusions in ADR-089 and its later extensions,
and the document/time contracts. It preserves pure pose evaluation, joint
frames/composition, expression sharing and existing untimed/looping behavior.
Changes to accepted records require the later ratified framework/viewer cycles;
this exploratory folder does not supersede them.

## Evidence and decisions after the spikes

See [spikes/README.md](spikes/README.md) for the executable scope and commands,
and [evidence/report.md](evidence/report.md) for measured outcomes, failures,
refinements and what remains unproven. The original proposal above is retained
so the investigation cannot silently rewrite its starting claim.

### Refinements supported by the completed investigation

The [evidence report](evidence/report.md) now contains the completed bounded
spikes: 17 native tests, 20 shared Python/Node/browser scenarios, a reduced
three-wheel measured-contact Curta rig, a browser G-code command adapter,
inspected 3D screenshots, 100,000-tick memory measurements, model-size scaling
and large-angle precision stress. No production capability has been added.

The recommended architecture stands, with these substantive refinements:

- A mechanical event must be able to refuse inadmissible engagement, not just
  change an `engaged` flag. The phase-mismatch test proved the distinction.
- Restoring or rolling back a run includes the active instruction sources'
  cursor/modal state as well as mechanical coordinates and memory. A real
  failing spike exposed loss of program/physical synchronization otherwise.
- Store periodic coordinates as bounded local phase plus separate winding,
  with an explicit convention for associated contact memory. Total travel and
  elapsed time remain non-looping. The large-origin experiment exposed error
  in ever-growing float angles; the prototype kernel is not yet converted.
- Retire completed motions as well as bounding event history. Commands can
  otherwise leak memory even when the mechanical state itself is fixed-size.
- Compile topology and execution plans, and benchmark the actual model.
  Synthetic 500-coordinate affine runs fit a 240 Hz budget on the measured
  host; 5,000-coordinate runs do not. This is not full Curta performance proof.

The tested first execution class is explicit piecewise-affine motion with
localized coordinate events, local detent memory and unilateral stops. This
defines a support boundary for the initial implementation, not a lower-fidelity
calculator substitute. Actual model laws and geometry must be migrated and
validated. The current spike deliberately refuses automatic continuation of a
blocked finite move; precise fractional progress/replanning remains a required
design item for production. Normal program pause/resume and replay are proven
at public tick boundaries.

The next framework/viewer cycles should carry these tests into a real compiled
program/export contract and preserve the originating Curta mechanical evidence.
Neither this recommendation nor the successful experiments ratify a new API,
supersede accepted ADRs, or authorize implementation outside this folder.

## Current planning direction: Pascaline first, Curta second

Pilot direction, 2026-09-13: rebase Pascaline's `open-run-simulation` worktree
onto its completed restoration, commit the planning records and follow the
assessment's recommendations with Pascaline as the first validator. Curta's
roadmap and ratified slice remain the second project, currently paused.
The framework's 0.7/0.8 release placement remains undecided.

The [active roadmap](roadmap.md) owns the current sequence, bases and gates.
The [preserved Curta-first roadmap](curta-roadmap-2026-09-13.md) retains the
previous draft verbatim beneath its historical-status notice. The original
Curta experiments and their evidence remain relevant to the generic engine;
the accepted `running(r)` and input/instruction/control decisions above stand.

Pascaline's new base is `1b0bb5c7979451ce4bc6ffbea187408078229930`, its completed
source-led restoration. Its project `docs/open-run-acceptance.md` owns the
readiness and migration plan. The first stage proves one transmission/carry
pair, then three positions and two carries, then all eight positions in both
accounting 12/20 and scientific 10/10 presets. The real framework must compile
the project laws into the same program that Python and the browser execute.

The current Pascaline computes counts from a starting register and one stroke.
Its restored lift uses contact-derived profiles, but its fall consumes further
input travel. Following the approved assessment, the running model should use
a finite-time kinematic fall triggered by local release. Stopping the input
after release must not freeze the fall; whole-run pause does freeze it, and
checkpoint/replay must preserve its progress. Pawl contact transmits movement
to the receiver; no arithmetic carry or precomputed output count does so.
This is explicit kinematic fidelity, not a claim of gravity or force dynamics.

The subsequent project readiness checkpoint `169b035` validates sampled
released-fall poses with the driving wheel held at/just beyond release and
all installed neighbours retained, on exact solids in both presets. It also
exposes a narrow pawl-return collision during independent receiver movement
using the original production controls. The [roadmap](roadmap.md) records that
blocker and the authorized bounded correction investigation. The subsequent
project record `readiness/PAWL-RETURN-2026-09-13.md` finds a delayed-return
candidate on unchanged parts: the pawl stays pin-supported at one input pitch
and returns only after further requested receiver motion clears its path.
The pilot approved carrying that retained-contact behavior into the running
proposal on unchanged parts. Pascaline commit `135f94f` opens the draft
`run-pascaline-with-retained-contact`, with proposal, design, four interface
deltas and 37 open tasks; strict OpenSpec validation passes. This is a
planning checkpoint, not a delivered repair or complete proposal ratification.
Timed-law, admitted rate, initialization, subsequent engagement and
profile/numeric bounds still need completion.
Finite faceted and exact checks remain distinct from continuous clearance
proof. A conflict with geometry or the accepted piecewise-affine execution
class returns to the pilot before scope expands.

Curta's mechanical checkpoint is `d7bf44b5ddd7ffb5b2521fdb5979c7fc1f6adff9`.
The carry/frame correction is archived but unintegrated; selector fit remains
paused at 2/22 tasks with 19 expected red tests. Its full 0–9 input,
three-wheel/two-carry slice, ideal detent fidelity, cross-revolution reset and
later whole-machine sequence remain intact. They no longer gate Pascaline's
first validation. The project handoff is the current mechanical status.

This is a pre-spec documentation checkpoint. No production cycle is complete
or newly ratified by it. Close Pascaline's bounded evidence gate, reconcile
its draft with the separate framework/viewer proposals, and obtain complete
ratification and the pilot's previously requested feature-start go-ahead before actual solid-node
feature implementation. The new readiness evidence is project-owned; no
framework/runtime implementation or running-browser measurement accompanies
this planning update.

## Earlier Curta-first planning, preserved for context

Historical direction from 2026-09-12 through the early selector investigation,
superseded in project order by the section above. The readiness counts below
describe those earlier checkpoints; the later Curta handoff at `d7bf44b` is
the mechanical status. Instructions in this historical section do not resume
the paused project or make its remaining work a Pascaline dependency.

Pilot direction on 2026-09-12 reopens the timing: prepare matching
`open-run-simulation` worktrees and work out a roadmap before implementation.
After assessing Pascaline's ongoing historical restoration, the pilot chose
Curta as the first project consumer, alongside the framework and viewer.
Its assembled source, measured contacts and existing carry spikes provide the
stronger reference for this work. Pascaline remains a later independent
validation project; its restoration does not gate this campaign.

The pilot will decide whether the framework work belongs in 0.7 or 0.8.
See [roadmap.md](roadmap.md) for repository bases, dependencies, scoped pilot
decisions and the remaining draft details. On 2026-09-12 the pilot ratified
one input column, three result wheels and two carry stages, addition only
with the carriage fixed: `099 + 1 -> 100` must emerge from mechanics. The
slice preserves paused and cross-turn carry state, permits selector changes
only at a stationary verified home window, uses ideal quasi-static detents
with checked transition clearance, and explicitly refuses operations beyond
its boundary. Full-machine migration follows this slice's acceptance.

The scope is settled. Profile-input provenance and byte-for-byte reproduction
are now verified in the project-owned `simulation/docs/open-run-evidence-2026-09-12.md`;
that report distinguishes its fresh bounded checks from complete running
acceptance. Curta's subsequent frame-only prerequisite is verified and
committed as `3afcac97a808aebf9d7019d6e43a6dc3086fea62`: continuous local frame
clearance and four sampled installed transitions pass. Continuous-neighbour,
complete home-window, initial-fixture and outgoing-boundary evidence remain
open. Close those gaps and prepare the three coordinated
repository-owned OpenSpec proposals;
after full proposal ratification, begin implementation with a tiny Python
mechanism proving the contract before tackling the actual Curta geometry.
This records planning decisions, not a complete cycle ratification or
authorization to begin production implementation. The pilot explicitly asks
to be consulted once ready, before actual solid-node feature development.

### Subsequent selector-readiness finding, 2026-09-13

Curta's evidence commit `dd981041ff41108727abc9ae02db0c291d0126cd` records
the selected input's installed 0–9 travel at initial and post-cascade home.
Independent native copies preserve the latter's pending second carry without
using the old operand law. Both 428-body fixtures expose eight intersecting
pairs at seated digits and nine with half-detents included. Housing, installed
detent and helical-follower findings prevent home-travel acceptance; see the
project-owned `simulation/docs/open-run-selector-evidence-2026-09-13.md`.
The completed two-station frame fit remains unchanged. That evidence led to
the bounded Curta-only selector-fit cycle ratified below; it does not authorize
package feature implementation. Retain the
full 0–9 acceptance requirement, the current framework contract direction and
the pilot's explicit solid-node feature-start gate.

The pilot then approved preparation of that bounded correction. Curta's
`openspec/changes/fit-selected-input-selector/` now contains the complete
proposal/design/spec/tasks. The pilot subsequently ratified the complete plan
("ratify, go on", 2026-09-13), strictly validated and committed in Curta as
`aec7ca4877c58820c6c02a32c44d8c6c206c9e9b`. It authorizes the manual's 5 mm
ball, installed quasi-static spring/ball motion, two conditional fixed-seat
candidates and protected local fitting, subject to its source/support stop
conditions. Task 1.1 is complete: 20 independent native contracts produced
three passing geometry/frozen-fixture guards and 17 expected red failures.
Measurements then exposed a source detent/guide indexing conflict: with the
5 mm ball on the source guide, numbered setting one lies on the ramp while
the sampled seat is near 0.83. A new native retention contract reproduces it;
the updated 21-test run has three passing guards and 18 expected red failures.
Curta paused at its alignment/protected-seat decision gate before operating
geometry changes. No operating fit is accepted and no package feature code
has changed. See Curta's
`simulation/docs/selector-fit-implementation-2026-09-13.md` for current evidence.

## Earlier sequencing: immediately after the 0.7 release

Historical recommendation, superseded on release timing and first-project
ordering by the current planning direction above. Its Curta-subassembly scope
and evidence requirements inform the preserved second-project roadmap.

Pilot direction recorded 2026-09-12: take up this work immediately after the
solid-node 0.7 release. It is a post-release priority, not additional scope or
a release gate for 0.7. This update records the next step; it does not start
implementation or ratify the illustrative interfaces above.

### Recommendation

Implement one narrow end-to-end mechanical subassembly through the actual
framework and browser viewer. Use the Curta carry mechanism as the first
acceptance case: the smallest actual subassembly containing an input
transmission, adjoining carry stages, their pin/lever engagement and reset cam.
Use its fitted source geometry and physical input travel, not only the
standalone spike's schematic meshes and normalized selector.

The assessment is that the execution architecture is viable for the tested
mechanical-law class, but the complete Curta is not yet proven. The largest
remaining gap is authoring and exporting those laws through solid-node and
validating the resulting moving parts. Closing that gap is more informative
than expanding the standalone interpreter or starting a whole-machine
conversion immediately.

The first increment should connect the whole path:

```text
Python component/joint/law declarations
    -> compiled mechanical program and geometry bindings
    -> stateful run in the browser worker
    -> actual moving subassembly, with Python/browser conformance
```

The numeric program must be produced by the framework's build/export path,
not hand-authored a second time for the browser. Keep one generic runtime:
the model supplies mechanical relationships, and manual or scripted operation
requests movement through declared inputs. No calculator result, operand
evaluation or arithmetic carry routine may determine the wheel poses.

### Acceptance evidence for that increment

1. Operate the physical input and crank repeatedly in the browser. Show
   engagement, transmitted movement, retained position after disengagement,
   successive carries and reset across a revolution boundary on the actual
   fitted parts. Declare and refuse unsupported operations explicitly.
2. Validate engagement and the swept movement against the subassembly's source
   geometry, including clearance and inadmissible re-engagement. Inspect
   rendered evidence. A plausible image or a correct final wheel position
   alone does not establish non-interference.
3. Run the same exported mechanical program in Python and the browser; compare
   coordinates, local mechanical state, events and admitted/blocked movement.
   Vary display cadence without changing the mechanical outcome.
4. Demonstrate pause/resume and checkpoint/replay through the common movement
   interface, including atomic rollback of mechanics and any active command
   source. Retain bounded history and verify the phase/winding representation.
5. Measure build/export cost, retained runtime memory, event-processing cost
   and browser responsiveness for this actual subassembly. Agree its target
   operating rate during planning; the synthetic 240 Hz result is not an
   acceptance promise for the real machine.
6. Preserve existing untimed and looping simulations. Version the new running
   capability so incompatible consumers refuse it instead of showing an
   incomplete animation.

After the release, recheck the released/current architecture and open the
repository-owned framework and viewer change cycles for this increment, with
the Curta validation work owned by its project. Resolve the concrete law API,
initialization, blocked-motion behavior and shared export contract there before
implementation. Carry the spike corpus and its failure cases into those real
paths; the experimental folder is evidence, not a second production package.

Successful acceptance justifies expanding supported mechanisms and then
migrating the rest of the Curta using the same engine. General nonlinear
contact, full-machine conversion and broad G-code/firmware compatibility are
not prerequisites for this first increment and must not be claimed by it.
