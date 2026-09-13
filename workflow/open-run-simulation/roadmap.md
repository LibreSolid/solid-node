# Open-run simulation: Pascaline module, historical Pascaline, Curta

Status: pilot-directed validation sequence and pre-spec planning checkpoint,
updated 2026-09-13. The pilot selected `Calculators/Pascaline-module` as the
first scope, sufficient to develop and validate the running feature. The full
historical Pascaline follows second, then Curta third; both are stress tests.
Their remaining restoration and migration work does not gate the first
feature increment. Framework release target remains **0.7 or 0.8, undecided**.
Updated later on 2026-09-13: the pilot replaced the `running(r)` law
protocol with the integrated-law reading and gave the feature-start
go-ahead; see the design note's "Decision 2026-09-13" and the execution
section at the end of this file.

This changes project priority and the first acceptance scope. It does not
claim that the module's assembly or mechanics are already validated. Complete
production proposals and the pilot's previously requested feature-start
go-ahead remain ahead; no compiler, runtime, viewer or model implementation
is introduced by this planning update.

## Why this is the first scope

The original José Campos modular calculator in
`projects/Calculators/Pascaline-module/` already has a source-backed single
decimal module, an authorized flexible ratchet stop and a planned three-column
alternating carry train. One module, one carry pair, then three columns give
a bounded path through physical input, transmission, intermittent engagement,
retention and chained carry. The aim is to build the generic feature against
this machine and then stress it with the larger mechanisms.

The historical Pascaline adds an eight-position mixed-base reconstruction,
timed sautoir fall and retained pawl contact. Its unresolved return and
subsequent-engagement questions belong to its second-stage migration.
Curta adds selectable engagement, cross-revolution detent/reset behavior,
source-fit obligations and scale at the third stage. Keep those findings and
approved fidelity choices, without requiring their completion for the module.

The [design](design.md) retains the accepted action controls,
input/instruction/control relationship and build-time `running(r)` law
extension. The [Curta spike evidence](evidence/report.md) remains generic
runtime evidence and a conformance corpus. Earlier plans are preserved in the
[historical-Pascaline-first roadmap](pascaline-roadmap-2026-09-13.md) and
[Curta-first roadmap](curta-roadmap-2026-09-13.md). Their former ordering and
package-start dependencies are historical.

## Repository ownership and checkpoints

Paths are relative to `/home/asa/devel/libresolid-studio`. Each row is an
independent repository; this is standalone work, not a shop sprint.

| Owner | Working location | Recorded content checkpoint | Role |
| --- | --- | --- | --- |
| Framework | `solid-node/WTs/open-run-simulation/` | Primary base `6e41f2da132a8604f9b68895967247fb8876fc4d`; preceding planning head `67b767ae40c7058bbc38c174b365ff576fd6d301` | Shared authoring, compiler/program contract, Python run, export and producer fixtures |
| Viewer | `solid-node-viewer/WTs/open-run-simulation/` | Recorded base `6fb082ba9823fb0839631bd4a3ecbf4a41b33b64` | Worker execution, controls, rendering, replay and publication lifecycle |
| Pascaline module | `projects/Calculators/Pascaline-module/` | `36e72e70f598a6d3fff9f0d59801e021824389b7` | First feature-development and acceptance project; source fit, project laws and three-column validation |
| Historical Pascaline | `projects/Vibecoded-demos/pascaline/WTs/open-run-simulation/` | Restoration `1b0bb5c7979451ce4bc6ffbea187408078229930`; running draft `135f94f2680d1819557a11a4dd903be5a5300a31` | Second validation: full-machine stress test |
| Curta | `projects/Calculators/Curta-Type-I-3x/WTs/open-run-simulation/` | Mechanical checkpoint `d7bf44b5ddd7ffb5b2521fdb5979c7fc1f6adff9`; disposition `4f332d052234e7225b868f8229df241d6d5043d4` | Third validation: scoped carry rig, then full-machine stress test |

Project-owned acceptance records are `docs/open-run-acceptance.md` in both
Pascaline repositories and `simulation/docs/open-run-acceptance.md` in Curta.
The module's active `simulate-the-pascaline` change still owns unfinished
assembly work. The historical Pascaline's `run-pascaline-with-retained-contact`
draft remains open and deferred to stage two, with its decisions and unchecked
tasks preserved. Reconcile it with the module-validated package contract when
that migration is taken up; draft completion is not mechanical acceptance.

The historical Pascaline worktree was previously rebased onto restoration
`1b0bb5c`; its older `main` at `c274a5d` is not the restored model base.
That history and the readiness commits remain in the preserved roadmap.
No rebase, integration or worktree removal is part of this resequencing.

Framework and viewer production proposals have not been created. These are
pre-spec checkpoints, not complete ratified planning commits. Reverify the
selected bases when opening those cycles. Package integration targets remain
their respective `main` branches subject to fresh checks and pilot direction;
project integration destinations follow their own branch state.

## Preserved shared decisions

- Keep component/joint declarations, existing frames, `.drives(...)`, grouped
  ends and project law factories. Superseded 2026-09-13: a law declares
  nothing for running mode; the run integrates the existing law along the
  input's movement and owns every coordinate (design note, "Decision
  2026-09-13"). Live state belongs to the run.
- Supported `forward`/`inverse` laws keep absolute-position semantics in
  untimed and looping documents and are integrated in running mode. Start with
  continuous laws, then the five discontinuous primitives; compilation refuses
  unsupported laws rather than executing arbitrary project Python in the browser.
- Compile one compact mechanical program and geometry bindings through the
  framework build. Python and the viewer worker consume that description.
  The framework contains no calculator-specific engine.
- Begin physical operation with relative nudge and hold-to-jog, then constrained
  dragging through the same movement interface. Actual positions are readouts;
  amounts/rates configure requests. Release or lost focus ends a jog, blocked
  travel creates no hidden backlog, and ownership prevents silent replacement.
- Inputs expose mechanical coordinates; instructions name reusable movement
  requests; controls provide gestures. Named instructions get buttons by
  default and also work without a viewer. Neither assigns output digits.
- Keep a finite forward simulation clock, pure pose evaluation and independent
  rendering cadence. Seeking requires recorded history. Preserve existing
  untimed/looping behavior.
- Framework and AGPL viewer remain separate packages connected through
  published data and the existing discovery/process boundary. The shop hosts
  published artifacts. Flexible shape follows committed mechanical state.

Complete declaration spellings, validation rules and the wire contract remain
proposal work. Explicitly extend the simulation, ports/time, joints/couplings
and export baselines. Preserve ADR-066/097/098 pose/frame rules and address
ADR-083/089/099/100 solver/time boundaries. ADR-056 is indexed as Proposed;
its accepted amendments and baseline specs govern today's behavior.

## 1. Prepare the Pascaline module's mechanical contract

The module's recorded validation has four passing source tests and five
flexible-stop contracts, including 145 sampled tooth poses, on both kernel
settings. A single-module build exists. Gear phase/axial-stack interference and
the missing second/third columns remain red. These are historical results from
the project checkpoint, not tests rerun for this update. STL source parts
remain mesh comparisons even under the exact-kernel setting.

Close those assembly findings within the project's existing change and map the
input/ratchet, dial-to-drum transmission and alternating A/B carry pieces.
Validate one fitted module, then one actual carry pair; retain bases, supports,
stops and constraining covers in geometric checks. Derive engagement windows,
ratios and phases from the source parts. The current fixed drum/carry ratio
is provisional posing, not proof of intermittent carry.

Declare independent coordinates, local contact/retention states, admissible
initial setups and input travel. Prove disengaged retention and admissible
re-engagement, and test ratchet admission separately from blade clearance.
The authorized blade deformation remains prescribed geometric kinematics,
without a force, material-strength or reverse-blocking claim from sampling.

**Gate:** a bounded project-owned state/event/geometry contract for the modular
mechanism, with validated fit and named operating limits. Neither the historical
Pascaline's timed fall/pawl return nor Curta's selector fit is part of this gate.
If the actual module cannot fit the accepted exportable law class, record the
measured conflict before changing the solver or fidelity.

## 2. Prepare and ratify the first production changes

Prepare one framework cycle, one viewer cycle and the module-owned running
migration plan. Reconcile the module's active assembly change and controls
with that migration without duplicating tasks or silently changing accepted
behavior. Present the shared contract together; each repository owns its
source, tests, specs and commits. Historical Pascaline and Curta migration
proposals are not required for this first increment.

Resolve initial snapshots; coordinate/relation identities; localized events
and same-instant settlement; finite moves, rates, command ownership and
admitted/blocked/cancelled progress. Checkpoints and rollback include the
clock, local mechanical state, active trajectories and instruction sources.
Keep bounded phase plus winding, bounded recording and command retirement.

Resolve versioned program/geometry publication, expression limits, profile and
numeric tolerances, producer-generated conformance fixtures, old-consumer
refusal, running-pose capture and incompatible-republish reset/refusal. Define
background-tab behavior, simulation resolution versus playback speed, and
whole-run pause versus an instruction source stopping input motion.
Timed released-sautoir motion remains historical-Pascaline stress scope; it
is not an extra first-module acceptance condition.

**Gate:** complete proposal ratification, supported OpenSpec validation and the
pilot's explicit feature-start go-ahead before production implementation.
This planning adjustment does not start feature development. The go-ahead was
given on 2026-09-13; per-cycle ratification is delegated to the repository
agent's adversarial review of each proposal, and integration stays the pilot's.

## 3. Build and qualify the feature with the Pascaline module

Start red-first with a tiny Python mechanism proving the compiler, retained
state and event contract, then the actual fitted module, one carry pair and
three alternating decimal columns with two carry stages.

Compile the project declarations once. Python, standalone browser export and
the development viewer execute that same program. Reuse source meshes and
pose them from committed coordinates; inspection, rendering and capture
advance nothing. The browser must not depend on an undeclared live Python
service or a second hand-authored mechanical model.

Acceptance covers:

1. Repeated physical dial movements accumulate without register re-entry.
   Single carry `009 + 1 -> 010` and chained carry `099 + 1 -> 100` arise from
   contact/transmission and retained coordinates. Arithmetic may independently
   check readouts in tests; it must not determine runtime poses or carry events.
2. Validated complete setups include gear phases, local contact state and the
   ratchet/blade configuration. Determine the highest column's actual end
   condition; refuse travel into an unvalidated outgoing interface. Reset
   restores a setup, without claiming physical clearing.
3. Pause/resume and checkpoint/replay during engagement, independent input
   operation within declared limits, blocked travel, conflicting commands and
   atomic rollback. Compare Python/browser coordinates, local states, events
   and admitted motion, including phase/winding and changed display cadence.
4. Engagement and clearance checks on runtime-produced poses and inspected
   images of the actual assembly. Missing transmission, incorrect phase/ratio
   and lost contact events must fail independent negative controls. State
   finite mesh sampling and profile/numerical bounds separately.
5. Actual build/export cost, program size, step/event cost, browser
   responsiveness and retained memory without recording. Choose operating-rate
   and resource budgets during proposal work; synthetic 240 Hz results do not
   promise this machine's performance.
6. Untimed/looping regression, version refusal, coherent publication, running
   pose capture, worker lifecycle and reload. Record exact framework, viewer
   and module content commits, resolved packages/bundle and environment.

Use an isolated combined-validation environment with the selected framework
and viewer content and the module as model/build root. Matching branch names
do not select installed packages; verify resolved paths and carry bench ports
explicitly. Use separate, non-nested build roots for concurrent checks.

**Gate:** the module validates a useful end-to-end running feature. Completing
the next two machines is not an acceptance or release gate for this increment.

## 4. Stress-test the full historical Pascaline

Resume its project-owned migration after the module increment. Reuse the
restored parts and preserve the approved finite-time kinematic fall triggered
by release and the retained pin-supported pawl-return direction. They do not
claim gravity/friction/impact dynamics.

The exact frozen-input fall samples pass; independent receiver operation in
the unchanged production law still has a narrow pawl/pin collision. The
sampled delayed-return candidate and draft at `135f94f` do not close subsequent
engagement, repeated operation, initialization, timing or admitted-rate bounds.
Keep the original red control and distinguish imposed geometric samples from
a running or continuous certificate. Full detail and pinned evidence are in
the preserved Pascaline roadmap and the project's readiness records.

Qualify a real carry pair, three positions, then all eight positions in both
scientific 10/10 and accounting 12/20 presets. Stress retained contact branches,
input cessation after release, pause/replay during timed fall/push, independent
receiver motion, mixed-base cascading and full ripple/overflow. Preserve
lifting-pin geometry when replacing the old input-count-based fall parameter.

Reconcile the deferred draft with the module-validated program/API. New
generic requirements supported by this evidence become separately scoped
package changes; the historical machine's readiness failures do not
retroactively make the first module increment incomplete.

## 5. Stress-test Curta third

Curta remains paused until resumed by the pilot. Preserve its ratified slice:
one physical selector through full 0–9 travel, three result wheels and two
carries, forward addition with fixed carriage, mechanical `099 + 1 -> 100`,
retained second carry across a revolution and later cam reset. Selector
changes require a stationary verified home window; refuse outgoing-boundary
travel. Ideal quasi-static detents with checked transition clearance remain
its fidelity choice.

The original `simulate-the-curta` remains at 7/17 tasks; the carry/frame
correction is archived but unintegrated, and `fit-selected-input-selector`
is paused at 2/22 with 19 expected red tests at mechanical checkpoint
`d7bf44b`. Preserve fit protections, source geometry and ignored evidence.
Finish those obligations for Curta, then expand to all selectors/result bank,
subtraction, carriage lift/shift, turns counter and physical clearing.

The preserved Curta roadmap and project handoff hold the detailed campaign.
Curta tests selectable engagement, cross-turn detent memory/reset and scale
against the shared feature. Its readiness is independent of both Pascalines.

## Dependencies, release and handoff

```text
Module fit + bounded mechanical contract
    -> framework + viewer + module ratified production plans
    -> tiny compiled mechanism -> module -> carry pair -> three columns
    -> accepted first running feature increment
    -> full historical Pascaline readiness + migration + stress tests
    -> Curta readiness + scoped rig + full-machine stress tests
```

Generic motor/steering, command-source pause/rollback and the existing Curta
spike cases remain conformance fixtures throughout. Production G-code/firmware
coverage, deposition, general nonlinear contact/dynamics and broad browser/
hardware qualification remain later explicit scope.

Choose release placement from the accepted API and measured module results.
Archive completed production cycles after tests, baseline synchronization and
accepted-ADR/architecture updates; integrate only on pilot direction after
fresh branch/base checks. No integration, release, publication or cleanup is
included in this documentation update.

This handoff changes planning records and project dispositions only. No CAD
sweep, build, export, running parity or performance measurement was repeated.
Earlier evidence and its limits remain preserved; record/link consistency,
diff hygiene and repository ownership are the validation for this edit.

Committed project handoffs for this resequencing:

- Pascaline module: `ee52b9433f6694d1594937185e06fa88898948a7`, first-scope
  acceptance plan and README on project `main`.
- Historical Pascaline: `6b40bd5aff713560e9b6260fd777b18fb8479946`, second-stage
  disposition on its existing `open-run-simulation` branch.
- Curta: `06bdfc5718f9ad1af0362955fdc79a7fcd176177`, third-stage disposition
  on its existing `open-run-simulation` branch.

All three are documentation-only commits; the mechanical checkpoints above
remain the evidence bases. The framework planning update stays in its existing
isolated `open-run-simulation` worktree, based on primary `6e41f2d`.

## Execution, 2026-09-13

Pilot direction after the interface review. The framework cycles stack in
this worktree rather than one worktree per change, the viewer cycle runs in
`solid-node-viewer/WTs/open-run-simulation`, and the module's work runs in
`projects/Calculators/Pascaline-module/WTs/open-run-simulation`. Every `main`
stays the pilot's.

| Cycle | Repository | Depends on |
| --- | --- | --- |
| 1. The run owns the coordinates | framework | this record |
| 2. Jumps | framework | 1 |
| 3. Stops | framework | 2 |
| 4. Export | framework | 2 (3 when landed) |
| 5. Viewer | viewer | 4 |
| Fit, carry pair, three columns | module | nothing |
| Running migration | module | 1, 2 |
| Ratchet retention | module | 3 |
| Browser acceptance | module | 4, 5 |

Framework and viewer: one agent proposes, another implements, the repository
agent reviews adversarially as the ratification gate. Module: one agent
proposes and implements each cycle. The campaign's goal is the module
simulated in the browser, with the shop opened from the worktrees on port 9001
for the pilot to test. Release placement is still undecided.
