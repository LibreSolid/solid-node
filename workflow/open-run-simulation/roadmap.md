# Open-run simulation: Pascaline first, Curta second

Status: pilot-directed validation sequence and pre-spec planning checkpoint,
2026-09-13. Pascaline is the first validation project; Curta is preserved as
the second. The pilot approved the preceding assessment and requested the
Pascaline rebase, roadmap hygiene and committed handoff. This records that
direction and its recommended finite-time kinematic fall; it does not claim
mechanical readiness or ratification of complete production OpenSpec cycles.
Framework release target remains **0.7 or 0.8, undecided**.

The existing action-panel direction, input/instruction/control relationship
and build-time `running(r)` law extension remain recorded in
[design.md](design.md). The [Curta spike evidence](evidence/report.md) remains
part of the generic runtime's evidence and conformance corpus. The complete
[previous Curta-first roadmap](curta-roadmap-2026-09-13.md) is preserved with
its original wording and an explicit historical-status notice.

The pilot's separate request to be consulted when ready to start actual
solid-node feature development still applies. This preparation introduces no
compiler, runtime, viewer or mechanical-model implementation.

## Why the order changed

The earlier comparison used Pascaline checkpoint `4222796`, whose restored
supporting contact and receiving-pawl proof were incomplete. The completed
restoration is now `1b0bb5c7979451ce4bc6ffbea187408078229930`. Its project-owned
`restoration/COMPLETION-2026-09-12.md` records 108 passing cases, supporting
two-pin contact, pawl push, installed clearances and both accounting 12/20 and
scientific 10/10 presets. These are historical results, not new measurements
made during this planning update.

Curta's preparation has exposed a substantial independent fit/restoration
programme. Its latest handoff is `d7bf44b5ddd7ffb5b2521fdb5979c7fc1f6adff9`:
the two-station carry/frame correction is complete, but the selected-input
fit is paused at 2/22 tasks, with 4 passes and 19 expected red failures.
Complete home travel, valid initialization and other installed-neighbour
proofs remain open. Those findings remain Curta work; they no longer gate
the first framework/viewer increment.

Pascaline is a completed reconstruction with a precise remaining limitation:
its manual register is the state before one stroke, and its calculated counts
drive the wheel poses. Repeating "Add a denier" does not accumulate additions.
The first validation must replace that mechanism of posing with retained
coordinates and local mechanical causes, while reusing the restored parts.

## Repository ownership and verified bases

Paths are relative to `/home/asa/devel/libresolid-studio`. These are independent
repositories and standalone worktrees, not a shop sprint.

| Owner | Worktree | Verified source/checkpoint | Role |
| --- | --- | --- | --- |
| Framework | `solid-node/WTs/open-run-simulation/` | `main` at `6e41f2da132a8604f9b68895967247fb8876fc4d` | Shared authoring, compiler/program contract, Python run, export and producer fixtures |
| Viewer | `solid-node-viewer/WTs/open-run-simulation/` | `main` at `6fb082ba9823fb0839631bd4a3ecbf4a41b33b64` | Worker execution, controls, rendering, replay and publication lifecycle |
| Pascaline | `projects/Vibecoded-demos/pascaline/WTs/open-run-simulation/` | Restoration at `1b0bb5c7979451ce4bc6ffbea187408078229930` | First validation: project laws, geometry, operation and acceptance |
| Curta | `projects/Calculators/Curta-Type-I-3x/WTs/open-run-simulation/` | Paused checkpoint `d7bf44b5ddd7ffb5b2521fdb5979c7fc1f6adff9` | Second validation, preserving its existing scoped and full-machine roadmap |

Pascaline's clean `open-run-simulation` worktree was rebased from
`4a6b73149937dfec8f066e9ca0195b8e6548edc6` onto the exact completed restoration.
It had no unique commits to replay and matched the restoration tree after
rebase. The primary checkout remains on `restore-axle-mounted-carry` at
`1b0bb5c`; its `main` remains at `c274a5d`. Do not substitute that older
`main` as the model source. Pascaline's eventual integration destination
must be decided against its then-current branch state.

The project-owned first-acceptance record is Pascaline's
`docs/open-run-acceptance.md` on its rebased branch. Curta's matching
`simulation/docs/open-run-acceptance.md` records its second-project
disposition; its historical handoff and existing changes remain intact.

Committed project handoffs for this planning update:

- Pascaline: `11009101e4bf19ee932efcfb7079340cb8f3a36f`, acceptance plan
  on top of the completed restoration.
- Curta: `4f332d052234e7225b868f8229df241d6d5043d4`, disposition-only
  update on top of mechanical checkpoint `d7bf44b`.

Framework and viewer production proposals have not been created. This
documentation commit is a **pre-spec checkpoint**, not the complete ratified
planning commit of a production cycle. Establish and verify those cycle bases
when the repository-owned proposals are opened. Each cycle still needs its
ratified planning and completed implementation records.

The framework bench remains registered as slot 9 (ports 8009/3009).
No service was started for this preparation. Package integration targets remain
their respective `main` branches, subject to fresh checks and pilot direction;
no branch integration, release, publication or cleanup is included here.

## Preserved shared decisions

- Keep component/joint declarations, existing frames, `.drives(...)`, grouped
  ends and project law factories. A returned law may add build-time
  `running(r)` to declare retained local state, position/movement constraints,
  event updates and admissible engagement. Live state belongs to the run.
- Existing supported `forward`/`inverse` laws retain absolute-position
  semantics. The initial solver class is piecewise-affine; compilation refuses
  unsupported laws rather than running arbitrary Python in the browser.
- Produce one compact mechanical program and geometry bindings through the
  framework build. Python and the viewer worker execute that published
  description. The framework contains no calculator-specific engine.
- Begin physical operation with relative nudge and hold-to-jog controls, then
  picking/constrained dragging through the same movement interface. Actual
  positions are read-only; amounts/rates configure commands. Releasing or
  losing focus ends a jog, blocked travel creates no hidden backlog, and
  command ownership prevents silent replacement.
- Inputs expose mechanical coordinates; instructions name reusable movement
  requests; controls provide gestures. Named instructions get buttons by
  default and also work without a viewer. Controls never assign output digits.
- Keep a finite forward simulation clock, pure pose evaluation and independent
  rendering cadence. Live elapsed time is a readout; seeking requires recorded
  history. Existing untimed/looping behavior remains supported.
- Framework and AGPL viewer remain separate packages connected through
  published data and their existing discovery/process boundary. The shop
  remains a host of published artifacts.

The complete declaration/host spellings, validation rules and wire contract
remain proposal work. The new run must explicitly extend the simulation,
ports/time, joints/couplings and export baselines. Preserve ADR-066/097/098
pose/frame rules and address ADR-083/089/099/100 solver/time boundaries.
ADR-056 is indexed as Proposed; its later accepted amendments and baseline
specs, not an assumption that the entire draft was accepted, govern today.

## 1. Close a bounded Pascaline readiness gate

Use the restored geometry unchanged as the starting reference. Map one
transmission/carry pair, then the three lowest positions, including input
spindle, accumulator, separate numeral gearing, lifting pins, receiving-axle
sautoir, hinged pawl, journals, stops and constraining neighbours. Identify
which existing tests observe prescribed poses and which can independently
check coordinates produced by a run.

The pilot approved following the assessment's recommendation: use a
**finite-time kinematic fall triggered by contact release** for the first
validation. This is an explicit motion approximation, not gravity, friction,
spring-force or impact simulation. Its physical support, pawl engagement and
receiving-wheel movement must still follow the actual parts.

A released fall progresses on simulation time even if the operator stops
moving the input. Whole-run pause freezes it; resuming or restoring a
mid-fall checkpoint continues the same progress. No number-base test or
arithmetic carry routine initiates or completes it. The existing
`fall=0.4` parameter is in input counts and cannot become seconds by relabelling.

The immediate evidence task is to hold the driving wheel at and just beyond
release and sweep the released fork/pawl/receiver path against the complete
installed neighbours. Existing fall sweeps advance the source wheel as they
lower the lever; they do not prove the stationary-source case. Also check
supported pause before release, independent receiver travel, engagement
compatibility, valid initialization and repeated operation.

Choose the local fall trajectory/duration and admitted input rates together
with these tests. Prove the timed law can be expressed in the accepted
exportable class. The clock-driven local fall is a new law to validate;
the Curta spike did not establish it. Return a measured conflict with that
class or the restored geometry before expanding scope or changing fidelity.

Keep method and tolerances separate: the restoration used finite faceted
sweeps with 0.01 mm³ volume epsilon, 0.05 mm nominal contact and at most
0.08 mm measured gap. Those results are not continuous or exact-solid
certificates. New runtime paths require their own engagement and clearance
evidence, profile-error bounds and explicit numeric tolerances.

**Gate:** a project-owned state/event/geometry contract with a supported
released-fall path, admissible setup and operating limits, and no dependency
on precomputed register counts. The bounded readiness investigation comes
next; it is not completed by this planning commit.

## 2. Prepare and ratify the three production changes

Prepare one framework, one viewer and one Pascaline migration cycle. Present
their shared contract together while keeping their source, tests, specs and
commits in their owning repositories. Pascaline's completed
`2026-09-12-build-pascaline` archive remains historical; the new migration
must explicitly reconcile its one-stroke/register controls, input-scaled fall
and scripted demonstration with the new running behavior.

Resolve complete initial snapshots; stable coordinate/relation identities;
event localization and same-instant settlement; finite moves, rates, command
ownership and exact admitted/blocked/cancelled progress; and the timed local
fall. Transactions/checkpoints must include clock, mechanical memory,
active trajectories and instruction-source state. Retain bounded phase plus
winding and explicit bounded recording; retire completed commands.

Resolve versioned program/geometry publication, supported expression limits,
numeric tolerances, producer-generated conformance fixtures, old-consumer
refusal, running-pose capture and incompatible-republish reset/refusal.
Define background-tab policy, numerical resolution versus playback speed,
and whole-run pause versus an instruction source stopping its input motions.

**Gate:** complete proposal ratification, supported OpenSpec validation and
the pilot's explicit feature-start go-ahead before production implementation.
This resequencing is not that go-ahead.

## 3. Prove the real producer and browser path on a small mechanism

Start red-first with a tiny Python mechanism proving compilation, retained
state and the timed local law. Then connect the real Pascaline transmission
and one carry pair, followed by three positions with two carries.

Compile the project declarations once, run them in Python, and export that
same program for the browser worker. Rendering and snapshot inspection
advance nothing. Reuse meshes and update poses from committed coordinates.
No hand-authored parallel browser model or output-count setter is acceptance.

The three-position scientific case is `099 + 1 -> 100`. The accounting case
is `0 livres, 19 sols, 11 deniers + 1 denier -> 1 livre, 0 sols, 0 deniers`.
Initial digits describe validated complete setups, including lever/contact
state, not merely wheel positions. Bound the outgoing carry of a reduced
fixture explicitly; a three-position rig does not prove full overflow.

Run the same commands through Python, standalone browser export and the
development viewer. Exercise capture of a committed running pose, worker
teardown, malformed-program refusal and republish behavior. Exported worker
assets must work without an undeclared live Python service.

**Gate:** repeated physical input strokes accumulate, contact-driven carries
operate, released motion survives input cessation, and Python/browser
coordinates, local states, events and admitted movement agree.

## 4. Qualify the complete Pascaline as first validator

After the small assembly passes, extend the same laws to all eight positions
and both validated presets. Preserve the reconstructed geometry and its
recorded limitations; unrelated reconstruction or manufacturing work is not
part of this migration.

Acceptance covers:

1. Repeated strokes without register re-entry, wheel selection and independent
   receiver operation, two successive carries and a full eight-position ripple/
   overflow. The visible numerals come from moving geometry. Test arithmetic
   may independently interpret them but must not generate the runtime motion.
2. Supported stops before release, input cessation after release, whole-run
   pause/resume during fall/push, checkpoint/replay, blocked-input feedback,
   conflicting input ownership and atomic rollback.
3. Python/browser conformance, event-boundary and phase/winding cases, changed
   display cadence independently of numerical resolution, and repeated
   inspection without state advancement.
4. Engagement and swept-path clearance on runtime-produced poses; deliberately
   missing transmission/contact, reversed ratio and lost release/push events
   detected independently. Inspect actual rendered parts and numeral windows.
5. Actual build/export cost, program size, step/event cost, browser
   responsiveness and retained memory without recording. Set operating-rate
   and resource budgets during proposal work; synthetic 240 Hz results do not
   promise this machine's performance.
6. Untimed/looping regressions, version refusal, coherent geometry/program
   publication and failure-safe reload. Record exact framework, viewer and
   Pascaline content commits, resolved package/bundle paths and environment.

The running inputs operate physical spindles. A selected-wheel gesture may
choose which declared input receives a command; it must not be a numerical
operand. Clear/Nines become explicitly validated setup/reset choices unless
a physical clearing operation is separately modeled. Scripted demonstrations
request input movements; they do not precompute the downstream wheel timeline.
Detailed stylus engagement and stop/admission rules belong in the proposal.

Combined validation must use a dedicated environment containing the selected
framework and viewer worktrees and Pascaline as the model/build root.
Matching branch names do not switch the workspace-installed packages. Verify
the actual resolved implementations and carry bench ports explicitly.
Do not rewire the shared installation. Use separate, non-nested build roots
for concurrent geometry/publication checks.

## 5. Resume Curta as the second validation project

Curta stays paused until the pilot resumes it. Its existing scope is retained:

- One physical selector through the full 0–9 travel; three result wheels and
  two carries; forward addition with fixed carriage.
- Mechanical `099 + 1 -> 100`, retained second carry across a crank revolution,
  later cam reset, stationary verified home-window selector changes and
  explicit outgoing-boundary refusal.
- Ideal quasi-static detents with checked transition clearance. Pascaline's
  finite-time fall choice does not replace Curta's ratified detent fidelity.
- Finish its own fit/readiness obligations before accepting that slice; then
  expand to all selectors/result bank, subtraction, carriage lift/shift,
  turns counter and physical clearing.

Keep the original `simulate-the-curta` open at 7/17 tasks, the archived
`clear-result-carry-frame-contacts` unintegrated, and the ratified
`fit-selected-input-selector` paused at 2/22. Preserve the source and measured
geometry, fit protections, expected red tests, worktree and ignored evidence.
The exact paused code/evidence checkpoint remains `d7bf44b`; a subsequent
disposition-only documentation commit does not remeasure it.

The preserved [Curta roadmap](curta-roadmap-2026-09-13.md) and project
`simulation/docs/open-run-handoff-2026-09-13.md` hold the detailed campaign.
Curta adds independent evidence for selectable engagement, cross-turn detent
memory/reset, fitted-source geometry and scale. Its uncompleted restoration
does not block Pascaline or become silently accepted when Pascaline passes.

## Dependencies, release and handoff

```text
Pascaline bounded readiness evidence
    -> framework + viewer + Pascaline ratified proposals
    -> tiny compiled mechanism -> real pair -> three positions
    -> complete eight-position Pascaline qualification
    -> Curta's own readiness and retained validation roadmap
```

The generic motor/steering, command-source pause/rollback and existing Curta
spike cases remain cross-runtime regression fixtures throughout. Production
G-code/firmware coverage, deposition, general nonlinear contact/dynamics and
broad browser/hardware qualification remain later explicit scope.

Choose release placement from the accepted API and measured results. Curta's
later completion is not a new gate on a Pascaline-validated package increment.
Archive completed production cycles after tests, baseline synchronization and
accepted-ADR/architecture updates; integrate only on pilot direction after
fresh branch/base checks. Worktree preservation or removal never implies
permission to delete branches, push or publish.

This handoff commits the previously uncommitted design decisions, the original
Curta roadmap snapshot and the new ordering. Pascaline's rebased branch owns
its acceptance plan; Curta's branch records its deferred second-project status.
No new CAD sweep, simulation suite, build, export or browser run accompanied
this documentation/rebase task. Rebase/tree identity, record consistency,
local links and clean committed worktree checks are its verification.
