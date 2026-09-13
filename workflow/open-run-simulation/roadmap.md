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

### Cycle 1 landed, 2026-09-13

`run-owns-the-coordinates` is implemented on branch `open-run-simulation`
in `solid-node/WTs/open-run-simulation`, two commits from base
`1d6f794` — the planning commit `a1d54cc` and the implementation commit
below. `Time.running()`, the bank of every driver and joint coordinate,
the run as a binder the solver recognizes, continuous-law integration
with propagation, hold, conflict and rollback, commands with one owner
per input, `Instruction(by=)`, snapshot/restore/reset and bounded
recording are all in; ADR-104, ADR-105 and ADR-106 record the three
decisions and the change is archived under
`openspec/changes/archive/2026-09-13-run-owns-the-coordinates/`. The full
suite is 2339 passed / 4 skipped / 925 subtests against the base's 2270 /
4 / 893; one running tick costs 1.16 ms against the untimed loop's
0.36 ms, with memory flat. Nothing is pushed and nothing is integrated
into any `main`.

Open questions the pilot owns, carried from the change's `design.md`:

- Should an input be able to EXPOSE a joint coordinate, so a wheel
  advanced by a carry reads as the input's position (the controls record
  of 2026-09-12), instead of a `Driver` being the input? Cycles 4 and 5.
- Should a joint coordinate the rest render leaves unbound be OMITTED
  from the bank instead of refused? The cycle refuses, and a `Free` whose
  machine binds four of six now needs one guarded line per unused
  coordinate.
- Should `Instruction(by=)` be accepted under an untimed root? The cycle
  accepts it as a relative ramp.
- Should an unbound `time` read under a running root be refused instead
  of previewing as `$t`? Deferred to cycle 4 with the export.
- Whether `blocked` reports per command or per rigid group is cycle 3's;
  the vocabulary is fixed here.

### Cycle 2 landed, 2026-09-13

`integrate-jumps` is implemented on branch `open-run-simulation` in
`solid-node/WTs/open-run-simulation`, two commits from cycle 1's own head
`5b7f4d0` — the planning commit `84e0d1d` and the implementation commit
this line is part of. The refusal of `floor`, `ceil`, `sign`, `%` and a
comparison is lifted: a jump-carrying law compiles into a JUMP PLAN, and
over a tick the run cuts the path its sources take at every crossing it
meets, reads one branch per jump node at each piece's midpoint, and sums
the branch-substituted law's change over the pieces — so a jump never
moves a part. Every crossing inside the tick is found, solved exactly
where the level quantity is affine and bisected otherwise; nesting works
by the graph's postorder; a multi-source law takes one path in the joint
source space, so a clutch closing mid-tick gives the travel after
engagement only. Two laws are refused at construction — one that can move
its coordinate only by jumping, and a jumping law none of whose driven
ends the run owns — and two refusals belong to the tick, a partition over
a thousand cuts and a `%` whose divisor reaches zero, both rolling back
as a conflict does. `record=N` keeps a second bounded ring, `sim.crossings`.
ADR-107 records the decision and the change is archived under
`openspec/changes/archive/2026-09-13-integrate-jumps/`. The full suite is
2380 passed / 4 skipped / 1245 subtests against cycle 1's 2339 / 4 / 925;
one `Train` tick now costs 1.07 ms against cycle 1's recorded 1.16, the
saving being one discarded law evaluation a tick that `Run._values()` no
longer makes, and a jump-carrying law costs 1.3x its continuous twin on a
non-crossing tick and 1.8x on a crossing one. Nothing is pushed and
nothing is integrated into any `main`.

The pilot's illustration reads as it was meant to: the Curta window
leaves its pinion at 4.0 at rest, 76.0 after one crank turn and 148.0
after two, and a tick that passes three tooth windows adds three throws
(220.0). Both originating projects' laws compile and integrate VERBATIM
(`evidence/probe_projects.py` in the archived change).

**A note for the module's running migration.** The committed
`CARRY_LEAD = 0.10` makes `handed_on` DISCONTINUOUS at the carry window's
boundary, by `first_rise * lead / first_width = 4.10 * 0.10 / 3 =
0.136666…`: the lead-shifted first segment already reads that far up its
ramp when the phase resets. The integrated reading subtracts that jump, so
a column hands on **65.403333…** per revolution rather than the declared
`CARRY_THROW = 65.54`. The law compiles and integrates unchanged, which
was this cycle's obligation; whether the module wants the lead applied to
the phase reset as well is the module's own change, and its migration now
starts from the number rather than from a surprise. The module's carry
also drives `tens.wheel`, a `RotationalPort` — which cycle 2 now refuses
for a jumping law, saying to state the relation into the joint coordinate
and let the port follow it. That is the second thing the migration has to
do, and it already had to do the first (cycle 1 refuses the relation's
plain-port SOURCE).

Open questions the pilot owns, carried from the change's `design.md`:

- Should a CONSTANT law (no free name, no jump) be refused too, rather
  than compiling and contributing zero? The cycle keeps cycle 1's
  ratified behaviour and argues for it; decision item 5 can be read
  either way.
- Should `settled_value`'s shape — a sloped term added to a jump-only
  term — be refused, or is the running reading (the jump-only term
  contributes nothing) the honest answer? The cycle takes the latter.
- Should the crossing record be on by default under a running root,
  rather than tied to `record=N`? It is tied, so a run that records
  nothing pays nothing.
- Should a `%` with a MOVING divisor be refused rather than searched? It
  is searched; no project writes one.
- One more, found in implementation: a crossing reached EXACTLY at a
  tick's own boundary is integrated correctly and contributes nothing,
  but is not "located inside a tick" and so never appears in the crossing
  record. The record is a diagnostic and the increment is right either
  way, but a reader counting throws off `sim.crossings` at a cadence that
  divides the period evenly will count none.

### Cycle 3 landed, 2026-09-13

`ranges-are-stops` is implemented on branch `open-run-simulation` in
`solid-node/WTs/open-run-simulation`, two commits from cycle 2's own head
`8019c6d` — the planning commit `5045b9c` and the implementation commit
this line is part of. A joint's declared `range` is now the physical stop
it states rather than a refusal of the tick: when a tick would take a
banked coordinate outside a bound, and FURTHER outside than it stood at
the start, the run locates the fraction `t*` at which it reaches that
bound, commits it there exactly, and the tick commits. What stops with it
is the connected group — every input whose own movement PUSHES the
stopped coordinate, tested per candidate of the compiled program's static
`sources` table on blocking ticks only, and everything those inputs alone
determine. An unrelated input runs its full tick, and so does one coupled
to the stopped coordinate only through a law that is currently
disengaged: an open gate does not stop its crank, and closing it stops
both. A coordinate determined by a stopped input and a free one goes on
moving on what the free one contributes. The tick becomes segments, each
integrated by exactly cycles 1 and 2's procedure, and stays atomic across
them. A command on a stopped input retires `blocked` with the travel it
actually admitted, fractional within the tick, and never resumes; a
`rate` on one retires `blocked` too. Reverse moves and reverse rates are
admitted, and a rate's cumulative travel on an integer input now
truncates toward zero. Either bound may be `None`, or a callable of the
joint's own coordinate stating it as an expression — compiled once like a
law, evaluated once per tick from the committed bank under a running root
and at the value being bound everywhere else — which is the ratchet.
`record=N` keeps a third bounded ring, `sim.stops`. ADR-108 and ADR-109
record the two decisions and the change is archived under
`openspec/changes/archive/2026-09-13-ranges-are-stops/`. The full suite is
2424 passed / 5 skipped / 1295 subtests against cycle 2's 2380 / 4 /
1245, the one extra skip being the suite's own record of the deferred
bound over a second coordinate; one `Train` tick costs 1.065 ms against
cycle 2's recorded 1.057,
which is inside that measurement's run-to-run spread and identical in
graph evaluations, and a blocking tick costs `2S + 1` propagation passes
plus one per pushing candidate. Nothing is pushed and nothing is
integrated into any `main`.

**The module's ratchet retention is unblocked.** The one line the
Pascaline module adds in its own repository is

```python
turn = Revolute(axis=(1, 0, 0),
                range=(lambda turn: DIGIT_STEP * floor(turn / DIGIT_STEP),
                       None))
```

on `InputArbor`, and `evidence/probe_projects.py` in the archived change
runs the module's own chain — `input.turn` → `drum.turn` at `-1` →
`carry.turn` at `-1` — with it: from `40` a reverse of `-10` blocks at
exactly `36` having admitted `-4`, a further reverse blocks at once with
`0`, `+4` is free, the reverse after that blocks at `36` again, and from
`75` the bound reads `72`. The same reverse admits exactly `-4` taken in
one tick, four or forty. Both originating projects' laws still compile
and integrate VERBATIM with their cycle-2 numbers.

Open questions the pilot owns, carried from the change's `design.md`:

- Should a stop also be reported through `sim.commands` for an input
  whose group stopped but which had NO command — that is, should the run
  offer a "which inputs are standing against a stop" read at all? This
  cycle reports a stop only through the record and the commands that
  existed.
- Should a stop on an INTEGER-dtype input admit only whole native units,
  flooring `t*` of the tick's travel, rather than leaving the driver
  between steps? This cycle leaves it between steps and says so.
- Should the detection probe stop at the first stop rather than
  integrating the whole tick, so a law that cannot be integrated past
  `t*` does not refuse a tick the machine would never have reached? This
  cycle probes the whole tick.
- Should an expression bound be admitted UNTIMED at all, or only under a
  running root? This cycle admits it everywhere, evaluated at the value
  being bound, so that one declaration poses and runs.
- Should `sim.stops` be on by default under a running root rather than
  tied to `record=N`? It is tied, exactly as the crossing ring is.
- Whether `blocked` reports per command or per rigid group — cycle 1's
  open question — is answered here: per COMMAND, because a command owns
  one input and a group is not a thing a caller holds. The group is
  visible in the stop record, which names the inputs it blocked.
- A bound may not name a SECOND coordinate in this release (design §10).
  The spike's ratchet fixture carries a `lift` that releases the pawl,
  and the smallest form that would serve it is a declaration that names
  what it reads, resolved against the declarer's subtree at `Sim`
  construction. Strictly additive; deferred.
