# Open-run mechanical simulation

Status: proposed architecture and authorized experimental work, 2026-09-12.
This is the full design proposed in the pilot conversation, followed by a
mechanism spike campaign. It is not an accepted ADR, an OpenSpec baseline, or
an implemented public API. The pilot explicitly authorized this folder and its
spikes on framework `main`; framework and viewer production code stay outside
this experiment. Initial framework HEAD: `518bed114c94697a58d95e85ad2831c8fcd9f3a3`.

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

The concrete low-level syntax should follow the spikes. These capabilities
must build explicit mathematical descriptions that can be exported, rather
than arbitrary runtime Python mutations. A law factory may still inspect its
realized component owners and resolved geometric parameters at build time.
It must declare all runtime dependence in the mechanical program.

Simultaneous constraints are resolved together. Two incompatible prescribed
inputs on one rigidly connected group are a conflict, not last-writer-wins.
Redundant but consistent constraints, reverse solving, disconnected groups and
closed loops need explicit support boundaries. Nonlinear loops may require a
numeric solver; a propagation-only solver must refuse what it cannot solve.

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

## Next step: immediately after the 0.7 release

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
