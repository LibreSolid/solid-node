# Preserved Curta-first roadmap — 13 September 2026

Status: historical planning snapshot, retained when the pilot selected
the historical Pascaline as the first validator on 2026-09-13. The pilot has
since selected the Pascaline module first, the full historical Pascaline
second, and Curta third; the latter two are stress tests. The original roadmap below is
preserved verbatim. Its first-project ordering and instructions to resume
Curta are superseded by [the active roadmap](roadmap.md); its Curta scope,
evidence, decisions and later whole-machine sequence remain the record for
the third validation project. Nothing in this snapshot resumes paused work.

The latest mechanical checkpoint is Curta
`d7bf44b5ddd7ffb5b2521fdb5979c7fc1f6adff9`, documented in that project's
`simulation/docs/open-run-handoff-2026-09-13.md`: the frame correction is
archived but unintegrated, selector fit is paused at 2/22 tasks with 19
expected red failures, and running acceptance is incomplete. This supersedes
the older progress counts in the preserved text. Consult the project records
before resuming; none of those gates is waived by the new ordering.

---

# Open-run simulation: framework, viewer and Curta

Status: draft roadmap, updated 2026-09-13. Worktrees are open;
running implementation has not started. Framework release target: **0.7
or 0.8, undecided**. The pilot selected Curta as the first acceptance project;
the detailed scope and interfaces below remain proposed, except for the
accepted action-panel direction and ratified input/instruction/control
relationship, build-time `running(r)` law extension, and first Curta acceptance
scope recorded below. Scope ratification does not establish the missing
mechanical evidence. The Curta frame-fit prerequisite and its measured
seat-edge exception are ratified; the verified implementation is committed
as `3afcac97a808aebf9d7019d6e43a6dc3086fea62` in Curta, with its focused
archive/handoff committed as `739c91a5144fba8bac3a904ddb7b2fb5338fc363`.
None of the three running OpenSpec
cycles is ratified. The pilot explicitly requires another go-ahead once the
evidence is ready, before actual solid-node feature development begins.

This updates the scheduling and first-project recommendation in
[design.md](design.md). The [Curta spike evidence](evidence/report.md) remains
the reason to pursue a generic engine that retains mechanical history.
Curta is also the first real model through that engine. Pascaline's historical
restoration proceeds independently and becomes a later validation opportunity.

## Repository shape and starting state

One coordinated increment, with one OpenSpec cycle in each package and a
project-owned migration cycle. Use `open-run-simulation` as the common branch
and proposed change name; the records and commits belong to three independent
repositories. This is standalone work, with no shop sprint membership.

Paths below are relative to `/home/asa/devel/libresolid-studio`.

| Owner | Worktree | Recorded main base | Responsibility |
| --- | --- | --- | --- |
| Framework | `solid-node/WTs/open-run-simulation/` | `6e41f2da132a8604f9b68895967247fb8876fc4d` | Authoring, compiled mechanical program, state and command semantics, Python execution, publication and producer conformance fixtures |
| Viewer | `solid-node-viewer/WTs/open-run-simulation/` | `6fb082ba9823fb0839631bd4a3ecbf4a41b33b64` | Program validation and execution in a worker, physical controls, rendering, replay and viewer lifecycle |
| Curta | `projects/Calculators/Curta-Type-I-3x/WTs/open-run-simulation/` | `60979adbc795785fc51a28a386f85d1a49bfedf7` | Mechanical laws and geometry, migration from prescribed calculator motion, mechanism acceptance and inspected images |

Each eventual integration target is that repository's `main`, subject to the
pilot's later integration direction and a fresh base check. No merge, rebase,
release or publication is implied by opening these branches. The framework
bench is registered through `scripts/dev-env`, slot 9, ports 8009/3009; no
service is running as part of this preparation.

Each primary was clean when its selected worktree was opened. The Curta base
is the same project revision used by the open-run spikes. The viewer and Curta
use local Git excludes for `/WTs/`, without changing tracked ignore files.

The previously opened Pascaline worktree at
`projects/Vibecoded-demos/pascaline/WTs/open-run-simulation/`, originally based
on `4a6b73149937dfec8f066e9ca0195b8e6548edc6`, is preserved outside this
campaign's dependency chain. Nothing here changes its restoration branch or
authorizes deleting that worktree.

Framework and viewer have no active OpenSpec changes at these bases.
Curta has `simulate-the-curta` still active, with 7/17 tasks complete at this
base. Before proposing its running migration, identify which existing
requirements it supersedes and which geometry findings remain with that
original change. Cross-reference the records without assuming the original
change is complete or making unrelated whole-machine cleanup a prerequisite.
New `open-run-simulation` change artifacts have not been created yet.

## Why Curta is the first reference

Curta provides an assembled STEP source, a construction/calibration manual,
mapped parts and joints, independently measured pin/reset profiles, and
existing input, bevel, carry and detent contact tests. These give a stronger
reference for diagnosing a new runtime than a reconstruction whose supporting
contacts are still being established. The project records are
`simulation/assessment.md`, `simulation/docs/measurements.md`, and
`simulation/docs/resumption-validation-2026-09-11.md` at the recorded base.

At the assessed restoration checkpoint `4222796`, Pascaline's axle-mounted
historical carry still had an open supporting-contact failure and no complete
receiving-pawl proof. Its earlier model also derives contact surfaces from
prescribed motion. Developing the runtime against it first would combine
reconstruction, law and runtime uncertainty. Its smaller size does not offset
that diagnostic cost.

Curta is not a fully validated running machine today. `simulation/curta.py`
imports `arithmetic.calculate` and supplies calculated register values to the
motion layers; the page retains completed calculations. The last recorded
regression has 142/144 faceted and 143/144 native passes, with a housing/thread
overlap retained in both and an additional faceted bearing disagreement.
Existing contact tests establish scoped fitted paths, not causal mechanical
execution or complete physical reliability. Their results must be rechecked
against runtime-produced states.

The proposed running model takes movements at physical inputs. Drum travel
and carry motion result from connections between parts and persist between
crank turns. Numbered geometry displays the answer; arithmetic may check the
observed result in tests, but may not drive the mechanism.

Start with **one selectable input, three adjacent result wheels and two carry
stages**, in addition mode with the carriage seated at one detent. Include
the actual stepped drum, transmission shafts and bevels, carry pins/levers,
reset cam, guides, relevant springs and stops. Preserve every neighboring
body whose contact constrains this slice; visual hiding does not remove an
obstacle. State the fixed boundary conditions for the omitted mechanisms.

Build the one-channel transmission and first carry pair before joining the
second carry stage. The spike's zero/one input rows are an initial bring-up;
slice acceptance includes the selected input's full 0–9 travel. Prove repeated
operation, two successive carries and reset across a revolution boundary
through the real exporter and viewer before expanding to the full machine.

## Roadmap and gates

### 1. Ratified first scope; close the mechanical evidence gate

The pilot ratified the minimal law extension on 2026-09-12; see
[the running-law decision](design.md#running-law-protocol--pilot-ratification-2026-09-12).
Keep the existing `.drives(...)` and project law factory. A returned law may
add `running(r)`, evaluated at build time to declare run-owned memory,
position/movement constraints, crossing updates and admissible engagement.
Supported ordinary `forward`/`inverse` laws keep their absolute-position
semantics and need no extra method. Begin with the spike's piecewise-affine
class and refuse unsupported laws at compilation without a Python fallback.
The framework, not project callbacks, owns event localization, settlement and
state advancement. This is an extension of the existing contract, not a new
assembly language or a requirement to rewrite ordinary gear relations.

The first source/code audit is recorded in Curta's
`simulation/docs/open-run-acceptance.md` on the matching branch. It maps the
actual three transmissions, dial/pin identities, carry sliders and springs,
frame offsets, candidate contact events and reusable tests.

The pilot ratified the first acceptance scope on 2026-09-12:

- One input column, three result wheels and two carry stages; addition only,
  with the carriage fixed.
- Initialize `099`, select `1` and crank to produce `100` through mechanical
  interactions, never by assigning a calculated result to the wheels.
- Pause and resume mid-carry, preserving pending carry state across crank
  revolutions.
- Allow selector changes only while stopped in a verified home window.
- Use ideal, quasi-static detent settlement initially, with verified clearance
  along the transition path. This is not a claim about force, friction or
  finite-time spring dynamics.
- Explicitly refuse operations beyond the slice, including stopping at its
  unmodelled outgoing carry interface with a fixture-scope diagnostic. The
  slice does not claim complete Curta overflow.

The pilot also ratified the next sequence: close the evidence gaps, prepare
the three coordinated repository-owned proposals, and seek full proposal
ratification before production implementation. The first implementation then
tests the contract on a tiny Python mechanism before the real Curta geometry.
These are scoped planning decisions, not acceptance evidence or ratification
of the complete cycles and all remaining draft details.

Map the three-position assembly's coordinates, physical inputs, contacts,
engagement states, limits and initialization. Pin existing geometry evidence
at the project base and identify which tests currently verify prescribed poses
and which can verify independently produced motion.

Two evidence obligations remain under that fidelity choice:

- **Detent state and transition fidelity.** A dial pin trips the adjacent
  lever, the retained detent admits a later carry tooth, and a reset cam
  releases it. The crank supplies the transmitted motion. Keep those causes
  distinct, including the measured contact approach and reset across a turn
  boundary. The ratified ideal snap settles at the same instant between stable
  branches; a pause preserves the committed branch, not an artificial
  intermediate instant inside the snap. Supported partial contact before a
  trip and mid-tooth/reset motion must still pause and resume correctly. An
  ideal detent is not proof of spring force, friction or impact behavior, and
  its moving geometry must still clear the surrounding parts.
- **Compile and validate the measured profiles.** The spike manually authored
  a reduced piecewise-affine program, normalized its selector, and rendered
  schematic meshes. Production must compile actual project laws, physical
  selector travel and joint-frame bindings. Revalidate pin approach, tooth
  engagement and reset profiles against fitted geometry, with explicit
  profile-error bounds and clearance along the complete detent-transition
  path. The ratified same-instant snap does not remove this geometric proof
  obligation or establish a finite-time spring trajectory. If those laws
  require an implicit nonlinear solve beyond the tested class, return that
  scope and cost before implementation.

Still specify and validate the complete initial snapshot for `099`, any
additional setup presets, the exact selector home window, reverse-travel
admission, blocked-motion recovery, input ownership, physical stops and target
operating rate. Selector changes during a turn are outside the ratified
admission window. Keep subtraction and carriage position/lift fixed, and
refuse unsupported operations by name. Driver slider ranges remain
presentation metadata; a physical stop is a mechanical constraint.

**Gate:** a bounded mechanical contract for the slice, including what it does
when the crank stops mid-carry, with no hidden dependence on calculated
registers or the page's operation-commit state. The pilot has ratified the
scope and fidelity above; the evidence portion of this gate remains open.

Remaining audit gaps include the exhaustive swept-neighbour/subassembly-cut
inventory, complete valid initial setups and home window, and installed
snap-path clearance. The subsequent project-owned evidence pass is
`simulation/docs/open-run-evidence-2026-09-12.md`: all three original raw-log
hashes and all six recorded source hashes match the spike provenance. Both
recovered full logs and durable compact records reproduce `carry_profiles.py`
byte for byte. Its sampled compression bounds pass again; no new pin/reset
CAD probe or continuous-contact proof is claimed. The existing isolated carry
tests pass 12/12 on each kernel, and the scoped exact `099` pose check finds
no selected slider-pair overlap while confirming 1.1630815 mm preload on each
lever. A 110-position exact pinion/drum diagnostic finds no overlap along
sampled selector travel at crank phases 0 and 357 degrees; this does not
establish the complete home window or other selector interfaces. These
results close the input-reproduction gap, not the mechanical
acceptance gate or the remaining operating/protocol decisions.

**Installed-check finding, 2026-09-12:** the next diagnostic inventories all
428 physical bodies and independently sweeps the slider, coupled sleeve and
fitted spring at both trip and reset events. Nine poses per event produce
native counterexamples at both selected stations: spring/upper-frame overlap
about 0.474 mm³, lowered-slider/frame overlap about 0.0992 mm³, and raised
reset-slider/frame overlap about 4.63 mm³. The records retain exact pair names,
contact regions and the six source-mesh interfaces; no overlap is waived.
These are current Curta fit/clearance findings, not evidence that the proposed
running-law contract needs replacing. The isolated tests did not cover these
frame interfaces. The gate remains unsatisfied.

Native localization and inspected section views also confirm spring/frame
overlap at the measured initial `099` preload (about 0.4734 mm³ per station),
although its sliders clear the frame. That snapshot is therefore not fully
clearance-valid yet; the earlier selected-pair pass does not certify it.

**Correction prerequisite ratified, 2026-09-13:** Curta's matching worktree now
owns `openspec/changes/clear-result-carry-frame-contacts/`, with proposal,
design, delta spec and tasks passing strict validation. Source/manual
comparison reproduces the contacts with the original STEP spring and the
supplied frame STL, so neither is a drop-in cure. The proposed remedy is
bounded stationary frame relief at the two selected stations, preserving
moving geometry, supports and measured motion. The ratified 0.05 mm running
gap must avoid independently mapped protected features; otherwise the remedy
returns to the pilot. Planning commit: `7d39306b2e2e0e4d476ce137f670d1c171e1ead4`.
Six independent native frame-contact tests now fail as intended and three
placement/travel/solid-validity guards pass. No production repair was made.

The support-preservation gate has been triggered: both slider endpoint gaps
reach an existing 20.43 mm² guide/frame registration land at both stations.
A 0.025 mm witness, already inside the requested gap, occupies a 0.03675 mm²
seat-edge strip at each endpoint. Native measurements and inspected sections
are in Curta's `simulation/docs/carry-frame-gate-2026-09-13.md`. Its task 1.1
is complete; the full support/envelope gates remain incomplete.

The pilot subsequently approved the bounded seat-edge exception and said to
try the fit without repeated confirmations. Revision commit: Curta `9c58255`.
The first station cleared its three native contacts and four preservation
checks before extending to station two; the two-station contact bench then
passed all nine tests. Full movement, dimensional and regression acceptance
remain pending. Complete that **Curta-owned prerequisite** under its existing
authority; do not silently waive the remaining protection or running gap.
After the correction
passes, resume complete transition, home-window and setup validation. This adds
a focused project correction ahead of the three running cycles; it does not
change their scope, resolve the 0.7/0.8 release choice, or complete Curta's
existing `simulate-the-curta` change. Framework and viewer production remain
unchanged.

Pilot boundary, 2026-09-13: "when we're clear to start developing the actual
feature in solid-node, then you ask me". Continue the approved Curta correction
and evidence work, then present readiness and request that go-ahead. Do not
treat prerequisite approval as authorization for framework production code.

### 2. Ratify the three connected changes

Produce repository-owned proposals, designs, delta specs and tasks through
the supported OpenSpec workflow. Present them together for coherence while
keeping their ownership separate. Reconcile the migration's requirements and
dependencies with Curta's active `simulate-the-curta` record first.

Carry the ratified control/instruction relationship, running-law extension
and first Curta acceptance scope into the proposals. The remaining shared
contract needs to settle:

- Running time and a distinct run context; `Time.running()` and the `Sim`
  examples in the exploration remain proposed spellings.
- Stable component/coordinate/relation identities, admissible initial state,
  local memory, event settlement and the supported solving class.
- Finite moves and continuous rates, input ownership, admitted travel,
  completed/blocked/cancelled results and exact interrupted-move progress.
- A transaction and checkpoint covering mechanics, clock, pending commands,
  active trajectories and any instruction source's cursor/state; bounded
  phase plus winding for periodic coordinates and bounded optional history.
- One versioned mechanical program and geometry bindings generated by the
  framework, with validation limits, numeric tolerances and shared fixtures.
- New document/capability versions, old-consumer refusal, running snapshot
  capture, and what invalidates state on republish. A running pose cannot be
  selected by elapsed time alone without its initialization and command history.
- Browser clock/background policy, independent numerical resolution and
  playback speed, and whole-run pause versus command-source pause.

Keep the framework's public contract independent of the viewer implementation.
The browser interpreter belongs to the viewer; communication remains through
published data and the existing entry-point/process boundary. Cross-runtime
fixtures should be producer-generated committed exports. Keep project geometry
and its mechanical acceptance tests in the project repository.

The framework baseline currently owns state in driver programs, clears solved
coordinates per pose, and excludes general constraint solving. Its new run
context must explicitly extend those contracts (simulation, ports/time,
joints, couplings and export), preserving existing untimed and looping use.
ADR-056 is still indexed as Proposed; use the baseline specs and later accepted
ADRs as current authority, not an assumption that all of that draft was accepted.
Preserve the pure-render/frame decisions in ADR-066/097/098, and address the
accepted solver/time boundaries in ADR-083/089/099/100.

The viewer cycle must explicitly extend the synchronous driver animation and
targeted-update contracts: retaining the old animation clock across an update
does not authorize retaining incompatible mechanical state. Keep cameras and
unchanged meshes where valid; define reset/refusal for incompatible programs.

**Gate:** pilot ratification and successful OpenSpec validation before production
implementation. The framework's first commit contains the complete ratified
planning state, including this working record; its second contains the tested,
documented and archived implementation. Prepare equivalent reviewable planning
and completion records for the viewer and project under their own workflows.

### 3. Build the real producer and Python run path

Move the spike's behavioral proofs into tests of actual model declarations,
compilation, execution and serialization. Start with a small synthetic pair,
then the Curta transmission, carry pair and three-position assembly. Write the
failing tests before the production change.

Compile relations/events once into a compact program. Separate committed
coordinates from requested movement and admitted movement; retain disconnected
coordinates, settle same-instant events together, and restore the last valid
transaction on failure. Pose the real parts from the committed result using
the existing joint frames and absolute transform composition. A render,
inspection or snapshot advances no mechanics.

**Gate:** the Python run accepts successive crank turns without resetting registers,
preserves partial state, produces contact-driven carries, and publishes the
same mechanical program the browser will execute. Exporting the program does
not require inventing a second model in JSON.

### 4. Complete the browser path on the same small assembly

Consume the framework-generated program in the viewer worker and compare it
against the Python fixtures. Load geometry once and send committed coordinate
snapshots to the renderer. Expose run/pause, step, speed, elapsed time, reset,
and declared physical input operation with feedback showing the motion
actually admitted.

The pilot accepted the action-panel recommendation on 2026-09-12: build
relative nudge and hold-to-jog controls first, then picking/constrained dragging
through the same movement-command interface. Running mode has read-only actual
positions, not synchronized position sliders; editable amounts and rates
configure commands only. Release/focus loss ends a manual jog, blocked input
does not accumulate hidden movement, and input ownership prevents silent
manual/program replacement. Live elapsed time is a readout, not a scrubber;
seeking requires recorded history. Preserve existing static/looping controls.

The pilot also ratified the input/instruction/control relationship on
2026-09-12; see [the decision record](design.md#inputs-instructions-and-controls--pilot-ratification-2026-09-12).
An input exposes a mechanical coordinate, an instruction names a reusable
movement request, and a control supplies the human gesture. Named instructions
get ordinary buttons by default; optional controls add jog/drag or customize
presentation without requiring duplicate movement definitions. Jog and inline
nudge controls need no separately named instruction but use the same runtime
commands, ownership and admission rules. Instructions work without the viewer.
The exact Python declaration and host API spellings still need design and
review; this scoped decision does not ratify the full package/project cycles.

Record/replay and command-source pause use the same commands as manual input.
Reset restores a validated initial snapshot; physical clearing is a separate
machine operation and must not be represented by directly zeroing outputs.
The page's current operand and initial-register setters are not running
mechanical controls. Bind the selected physical input and crank directly;
retain reproducible initial configurations as explicit validated setup presets.
The page's Commit operation must no longer manufacture retained machine state.

Exercise standalone export, the development viewer, and capture of a committed
running pose. Validate worker teardown, malformed-program refusal and republish
behavior through the real packaged viewer. Its worker assets must travel with
the export, without an undeclared live Python service.

**Gate:** a maker operates the real Curta slice in the browser, with native
and browser state/event results agreeing through carry, pause and replay.

### 5. Qualify the slice, then expand Curta

Required slice evidence:

1. Repeated crank turns, the selected input's full 0–9 positions and physical
   travel, two successive carries, retained wheel positions after
   disengagement, and carry detents retained/reset across a revolution
   boundary. Include stopping the crank mid-contact and mid-carry.
2. Pause/resume and mid-carry checkpoint/replay; blocked input reporting;
   incompatible input conflict and complete transaction rollback.
3. Python/browser agreement on coordinates, local state, events and admitted
   movement. Vary display cadence separately from simulation resolution;
   test event-boundary cases and phase/winding restoration.
4. Engagement and swept-path clearance on actual parts, with units and method
   stated. Remove a connection, reverse a ratio or lose a trip/reset event and
   show which test detects it. Inspect captured images; final arithmetic and
   endpoint pictures alone do not establish a working mechanism.
5. Actual export size/build cost, step/event costs, responsiveness and retained
   memory without recording. Choose rate and resource acceptance budgets during
   planning. The synthetic 240 Hz spike measurement is not a model guarantee.
6. Existing untimed/looping regressions, incompatible-consumer refusal, matching
   program/geometry publication and failure-safe reload. Record the exact
   framework, viewer and project commits plus browser/environment versions.

After that gate, expand in project-owned increments: all eight independent
selectors and the complete result bank, then subtraction, carriage lift/shift,
the turns counter and physical clearing. Use the manual's calibration sequence
and complete overflow as independent operation checks. Add further package
cycles only for measured gaps. Whole-machine acceptance includes the remaining
frame/housing interfaces and full operation sweeps; the first slice does not
establish full-machine clearance or performance and does not waive those
findings. Unrelated housing cleanup does not gate the validated slice.

### 6. Decide release placement and integrate

The release choice stays independent of branch names. Review API size,
mechanical scope, compatibility and measured acceptance evidence to decide
0.7 versus 0.8. Keeping this work on its branches does not add a gate to 0.7.

Archive each completed cycle after its own tests and spec synchronization,
extract accepted ADRs from the confirmed design, and update the corresponding
architecture and changelog. Integrate only on pilot direction. Recheck targets
and bases: other work may advance `main` while this campaign is open.

Combined validation must exercise the exact three selected revisions. The
framework bench currently uses the workspace-installed viewer; matching branch
names do not switch that installation. Before running the acceptance model,
prepare a dedicated environment containing both selected package worktrees,
verify the resolved framework and viewer/bundle paths, use the project worktree
as the model/build root, and carry the bench ports explicitly. Keep that setup
out of the shared workspace installation. Local bench wiring is preparation,
not a new shop product feature or a reason to introduce a shop sprint.

## Dependencies and later scope

```text
Curta subassembly audit and scope decisions
                  |
      three ratified planning records
                  |
 framework compiler + Python runtime + fixtures
                  |
   viewer worker + controls + Curta slice
                  |
   geometry / parity / resource acceptance
                  |
 selectors / result bank / remaining Curta operations
                  |
       Pascaline and later mechanism migrations
```

The small generic motor/steering and command-source fixtures remain useful
guards against a calculator-specific engine. A production G-code dialect,
printer deposition, general nonlinear contact/dynamics, and broad browser/
hardware qualification require later explicit scope; the current spikes do
not promise them. Full Curta migration follows the slice in separately planned
increments rather than becoming the first package cycle's acceptance gate.

Pascaline is the next independent mechanism candidate once its restoration
establishes supporting contact and a complete carry. Its weighted sautoir and
mixed bases will test generality beyond Curta's crank-driven carry mechanism.
Its reconstruction and any gravity/fall-fidelity decisions are not dependencies
of this first increment.

## Preparation record — 2026-09-12

- Opened and verified the framework and viewer branches/worktrees, then the
  matching Curta worktree at the base above after the pilot selected Curta.
  Preserved the earlier Pascaline worktree.
- Recorded the release-neutral direction, selected project and draft roadmap
  in the framework worktree; the design and roadmap remain uncommitted for
  planning review. The subsequent mechanical audit is project-owned at
  Curta's `simulation/docs/open-run-acceptance.md`; the subsequent evidence
  package was committed there with the prerequisite plan on 2026-09-13.
- Inspected repository records and relevant source. Existing spike results
  are cited historical evidence; no simulations or test suites were rerun.
- Recorded pilot acceptance of action-based controls and ratification of the
  input/instruction/control relationship, including default instruction
  buttons and optional controls, in the design and this roadmap. Exact control
  API spelling and the complete cycles remain pending; no baseline specs or
  implementation code changed.
- Recorded pilot ratification of the build-time `running(r)` extension and
  its memory/constraint/event declaration semantics, preserving existing
  algebraic laws. The design carries the reviewed Python sketch and scoped
  compatibility rules. No simulation, compiler or viewer code was changed.
- Recorded pilot ratification of the first Curta acceptance scope: the
  three-wheel/two-carry `099 + 1 -> 100` case, pause/resume and cross-turn
  retention, stationary-home selector changes, ideal quasi-static detents
  with checked transition clearance, and explicit slice limits. Recorded the
  coordinated-proposal and tiny-Python-mechanism-first sequence. Updated the
  project-owned acceptance dossier without marking its evidence gaps passed.
- At this initial preparation checkpoint, no new OpenSpec cycle had been
  generated, ratified, implemented or integrated. The first code/source audit
  was complete and the initial scope
  and fidelity choices above are settled. The mechanical evidence gate and
  remaining detailed operating/protocol decisions are still open. No new CAD
  sweeps, profile reproduction or simulation tests accompanied ratification.
- The later evidence pass recovered and hash-verified the three profile logs,
  preserved compact project-owned inputs, and reproduced the profile byte for
  byte with fresh sampled-error checks. It reran the 12 isolated carry tests
  on both kernels and checked selected slider contacts in the static `099`
  setup. See the project-owned evidence report above for scope and remaining
  proofs. This is subsequent verification, not retroactive acceptance of the
  historical spike or completion of a production cycle.
- On 2026-09-13 the pilot ratified Curta's focused frame-fit prerequisite.
  Its planning commit `7d39306` contains the accumulated project evidence.
  Independent native red tests and source seating measurements subsequently
  triggered its explicit protected-feature stop condition. The pilot then
  approved the bounded frame-side seat-edge exception; revision `9c58255`
  records that decision and the native gate evidence. The local two-station
  fit is implemented in Curta's worktree, with all 17 new contracts passing
  on both runners, continuous frame-clearance enclosures, four installed
  transition reruns, dimensional/protected-feature measurements and inspected
  OpenSCAD views. Its complete 39-module matrix is 159/161 faceted and
  160/161 native, with only the recorded failures and all 191 source hashes
  unchanged. Verified implementation is Curta commit
  `3afcac97a808aebf9d7019d6e43a6dc3086fea62`; the focused archive/handoff
  is commit `739c91a5144fba8bac3a904ddb7b2fb5338fc363`. Its four requirements
  are synced, all 19 tasks are complete, and the original `simulate-the-curta`
  remains active at 7/17. No integration is performed.
- After the frame prerequisite closes, the next evidence pass checks the
  complete physical selector travel in the initial and post-carry home
  configurations. It must freeze the retained carry state independently of
  the old calculator operand, whose prescribed laws reconstruct that state.
  Initial-slice setup, continuous-neighbour and outgoing-boundary obligations
  remain separate from the frame-clearance certificates. Complete the three
  coordinated proposals and ask the pilot before actual solid-node feature
  development; the prerequisite's approval does not authorize it.
- That selected-input pass is now committed in Curta as
  `dd981041ff41108727abc9ae02db0c291d0126cd`, with the complete record at
  `simulation/docs/open-run-selector-evidence-2026-09-13.md`. All 428 physical
  bodies remain in the inventory. Independent native input copies traverse
  0–9 while the initial and post-cascade roots stay unchanged; the latter
  retains result 100 and carry fractions `[0, 1]`. Both fixtures have eight
  intersecting pairs at ten seated settings, and nine when the nine
  half-detents are included. Housing slot/window, installed ball/spring and
  helical-follower findings keep the home-travel gate open. The source's
  nominally named 5 mm ball is a native 5.4 mm sphere; replacing it had not
  yet been proved a remedy or authorized in that evidence pass. Co-moving screw/shaft fits need explicit
  classification, not a blanket clearance waiver. No production geometry or
  framework/viewer feature code changed; all 191 frame-regression source hashes
  remain unchanged. The recommended next prerequisite is a bounded,
  Curta-owned selected-selector fit/detent proposal. That expands beyond the
  ratified frame-only correction and was not yet ratified at that point. It neither reduces
  the 0–9 acceptance scope nor changes the release-neutral running design.
- The pilot subsequently approved preparing that bounded selector correction
  ("yes, go on", 2026-09-13). Curta now owns the complete, strictly validated
  `openspec/changes/fit-selected-input-selector/` proposal, design, delta spec
  and tasks. Its six requirements cover full home-fixture travel, installed
  detent support, mechanical capture, two conditional fixed-seat entries,
  local protection and honest acceptance. All 22 implementation tasks were
  open at preparation; preparation approval was not hardware/cutter acceptance.
  No operating geometry or framework/viewer production code changed in that pass.
- The pilot then ratified the complete selector-fit plan ("ratify, go on",
  2026-09-13). Curta planning commit
  `aec7ca4877c58820c6c02a32c44d8c6c206c9e9b` contains the strictly validated
  plan before implementation. Task 1.1 is complete: 20 independent native
  contracts, three passing geometry/frozen-fixture guards and 17 expected red
  failures. The complete 428-body inventory, both retained states and all 191
  frame-regression source hashes remain intact. Subsequent measurements exposed
  a guide/detent indexing conflict: the 5 mm ball on the source guide has its
  sampled seat near setting 0.83, not numbered one. An additional independent
  native retention contract fails (updated run: 21 tests, three passing guards,
  18 expected failures). Work paused during task 1.2 for an alignment/protected
  spring-seat decision; no operating fit or continuous path is accepted. Current
  evidence: Curta `simulation/docs/selector-fit-implementation-2026-09-13.md`.
  This authorizes only the bounded project correction, not solid-node/viewer
  feature development or a change to the release-neutral acceptance scope.
