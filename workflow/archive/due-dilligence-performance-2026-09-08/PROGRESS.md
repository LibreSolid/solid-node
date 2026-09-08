# Performance remediation progress

This is the execution index for the performance audit. The original
[report](PERFORMANCE.md) and [measurement evidence](performance/README.md) are
historical records and are not overwritten by remediation runs.

## Scope and authority

The pilot requested remediation of the full list on the existing
performance-analysis branch/worktree, a Sol High proposal author, Sol or Terra
implementers selected by complexity, and adversarial review before spec sync and
archival.

- Worktree: solid-node/WTs/performance-analysis.
- Starting content: 40a848d6f8939b3e0d69e45a11b514b4ebfa263f.
- Local main at cycle opening: 66401867b8510f0a24f6a0771b732aea6c949828.
- Original measured framework: 4bf9b69421b7114809af75fe663441d115407631.
- OpenSpec archive: [bound-framework-performance-costs](../../openspec/changes/archive/2026-09-08-bound-framework-performance-costs/).
- Planning commit: 2ca4b9f06835d1133b6ad00eceecdee6e29b714c (amended after AR-07 re-ratification; original measurement baseline remains at 4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c).
- Current gate: **65/65 tasks complete; implementation and documentation independently reviewed green; archived; final focused/full tests pass; clean two-commit cycle verified**.
- Implementation: **complete and independently reviewed**. Synchronization: **six capabilities synced**. Archival: **complete, 2026-09-08**.

The same-worktree instruction overrides opening a new bench for this cycle.
The pilot explicitly ratified the complete proposal with “ratify” on 2026-09-07,
including all six design choices and the full implementation/review workflow.
After strict validation, the planning-only commit was created in the verified
framework worktree. The worktree was clean and exactly one commit ahead of the
recorded cycle base before apply bookkeeping and baseline capture began.
This is standalone framework work, not sprint work. The cycle starts at the
audit commit above; its planning and implementation commits will follow that
commit. The pilot subsequently authorized integration into `main` with “merge to main”.
Pushing, release and worktree removal remain outside this request.

## Full-list coverage

The proposal's design and tasks define package ordering, dependencies, model
assignments and proof requirements. This index tracks audit coverage, not a
second competing task list.

| Audit item | Required disposition | Status |
| --- | --- | --- |
| P01 — Process-per-artifact overhead | Amortize stable-source build work while retaining fresh-process isolation, reload correctness and error outcomes | Implemented, measured and independently reviewed green ([WP2](remediation/wp2.md)) |
| P02 — Repeated publication mesh facts | Reuse only verified artifact facts while preserving document contents, metadata changes and recovery | Implemented, measured and independently reviewed green ([WP3](remediation/wp3.md)) |
| P03 — Repeated SCAD writes/source work | Eliminate redundant generation and source work without weakening contributor currency or locking | Implemented, measured and independently reviewed green ([WP1](remediation/wp1.md), [WP4](remediation/wp4.md)) |
| P04 — Flexible binding cache churn | Bounded, source-aware reuse of simultaneously useful geometry bindings; no flexible verdict memo | Implemented, measured and independently reviewed green ([WP5](remediation/wp5.md)) |
| P05 — Broad-phase orientation cliff | Reduce avoidable sparse-case comparisons while proving conservative completeness and diagnostic behavior | Implemented, measured and independently reviewed green ([WP6](remediation/wp6.md)) |
| P06 — Child naming cost | Reduce wide-tree bookkeeping, preserve alias/name precedence and between-traversal mutation, and explicitly ratify sibling snapshot timing | Implemented, measured and independently reviewed green ([WP7](remediation/wp7.md)) |
| P07 — Exact placement retention | Bound placement-cache growth while preserving exact placement results and useful reuse | Implemented, measured and independently reviewed green ([WP8](remediation/wp8.md)) |
| Additional: dense statics matrices | Measure and bound representation cost; preserve the existing equilibrium problem and diagnostics | Implemented, measured and independently reviewed green ([WP9](remediation/wp9.md)) |
| Additional: exact/faceted precision choice | Retain explicit kernel selection and epsilon semantics; no silent precision tradeoff | Preserved; measured proof and independent review green |
| Additional: simulation trajectory retention | Retain intentional trajectory behavior; do not label it a leak or silently discard history | Preserved; measured proof and independent review green |

The prior correctness audit's F04 locking and F05 source-currency findings are
already resolved on this cycle's starting main. They are regression constraints,
not unchecked remediation work. The previous audit and its resolutions remain
in [the correctness archive](../archive/due-dilligence-2026-09-07/PROGRESS.md).
The independent viewer follow-up there is outside this framework cycle.

## Execution discipline

1. Sol High authors the concrete proposal, design, delta specs and implementation
   tasks using the supported OpenSpec workflow.
2. Present the proposal for pilot ratification. Validation/readiness does not
   substitute for ratification. Then validate and create the planning-only
   commit, with no implementation changes.
3. Assign each implementation package to the named Sol/Terra model and reasoning
   level in the ratified plan. Keep one writer per overlapping source area;
   use the same worktree and leave implementation uncommitted until completion.
4. Prove each performance regression red structurally or with a controlled
   baseline before changing code; prove the optimized path green with unchanged
   geometry, currency, errors, naming and precision semantics as applicable.
5. Record fresh empirical evidence separately from the historical audit. Run
   catalogue projects only in disposable copies, with input provenance and
   before/after equivalence checks; never mutate their original repositories.
6. Have an independent adversarial reviewer inspect the implementation, tests and
   evidence before spec sync or archival. Fix accepted findings, rerun relevant
   tests and re-review; an unresolved material finding blocks completion.
7. Run focused and complete framework validation, document skips and limits,
   promote only implementation-confirmed ADRs, and update the architecture where
   its boundaries changed. Then use the supported sync/archive workflows.
8. Commit the completed implementation and records only when the full list is
   coherently addressed. Update this index with evidence, review disposition,
   commits and final checks; finish with a clean worktree.

A contradicted design or a materially different interface returns to the pilot
for re-ratification. No finding is marked complete solely because code changed,
a benchmark improved, or a reviewer found no issue.

## Validation history (earlier checkpoints preserved)

The rebased pre-implementation framework baseline passed: **1,639 tests and
302 subtests; 16 skipped, 46 warnings**, in 209.68 seconds. Source and tests
were unchanged at 40a848d. See [the baseline record](remediation/README.md).
The historical audit's results remain separate and unchanged.

OpenSpec reports proposal, design, all six delta specs and tasks complete;
`openspec validate bound-framework-performance-costs --strict --no-interactive`
passed. This is planning readiness, not ratification or implementation progress.
See the [proposal preflight review](remediation/proposal-review.md) for findings
and their disposition. The exact post-implementation review gate is still pending.

Fresh pre-implementation performance capture at planning HEAD completed all
seven sections with **104 successful workers**, no worker error or timeout,
unchanged historical evidence, and unchanged original catalogue snapshots.
New raw records are `remediation/planning-head-baseline-*.json`; source and tests
remained untouched throughout capture. Sol High owns WP1; its builder seams are
released to Sol XHigh for WP2 while source checks finish. Sol High implementers
also own WP3 and WP9. Terra High completed WP5, WP6 and WP8 focused work; WP6's
current real-project comparison remains pending. All implementation remains
uncommitted and awaits the combined independent adversarial review. Coordinator
findings are recorded separately in the [implementation preflight](remediation/implementation-preflight.md).

The first combined candidate run recorded **1,749 passed, seven failed,
16 skipped, 48 warnings and 353 passing subtests** in 269.04 seconds;
`remediation/candidate-framework.xml` and `.log` preserve that failed run.
The seven failures concern SCAD/build-directory state, snapshot lock observation
and current/missing adapter artifacts. Sol High is investigating the shared
cause before remeasurement. Independent finding AR-01 (historical exact-test
cache isolation) is corrected and independently re-reviewed green; no production
exact-cache change was needed. Neither result is a final review gate.

The seven full-suite failures were traced deterministically to new in-process
builder tests leaking `SOLID_BUILD_DIR`, not a production build-directory
regression. A test-only correction is in progress. Independently, reviewer
AR-02 identified an actual split-observation race: faceted geometry/bounds and
their verdict/placement keys could describe different STL replacements. Sol
High completed that red-first correction, and AR-02 plus AR-04 (a stale nominal
STL accidentally enabling flexible verdict caching) are independently closed.
AR-03's confirmed measurement assembly-counter defect is also corrected and
re-reviewed; a suspected duplicate observation increment was withdrawn as a
concurrent-inspection artifact.

The coordinator's combined package run passed **131 tests and 51 subtests**
in 42.94 seconds. The subsequent full `candidate-framework-v2` run passed
**1,758 tests and 353 subtests; 16 skipped, 48 warnings**, in 267.59 seconds.
Both runs have separate logs and JUnit records. A later static-review finding,
AR-05, identifies missing recovery-watch coverage for a known foreign source
outside a nested entry module's directory. That narrow correction and its
re-review preceded the final frozen full-suite run and empirical capture.

All six adversarial findings are now independently closed, including AR-06's
measurement-verifier checks. The expanded focused run passed **139 tests and
51 subtests**. The final `candidate-framework-v3` run passed **1,759 tests and
353 subtests; 16 skipped, 49 warnings**, in 278.57 seconds (2,128 JUnit cases,
zero errors/failures). Source/test/probe identity remained
`689974d2373f57f9f33074f833be96ffae80db9a2ee09fb5050405f430945fa7`
across 374 selected entries. The new `current-candidate` capture was released
only after this green result; the overall evidence-review gate remains open.

That first capture passed startup (46 workers) but stopped at the build
no-churn gate. Cold Solid2 root SCAD uses inline geometry; the first post-cold
build replaces it with cached-child references. All STL filename/hash maps and
viewer manifests were unchanged. Independent review classified this as a
harness settlement-boundary defect, not a violation of compare-before-write
when desired bytes are equal. AR-06 is reopened for the narrow measurement
correction: preserve cold and first-warm timings for baseline comparison, then
assert zero churn on an explicitly third, settled build. The original
`current-candidate-*` files remain immutable; revised probe bytes require a
new identity and `current-candidate-v2` capture label. Production/tests do not
change for this correction.

The finite three-pass correction passed its red/green regression and independent
re-review; AR-06 is closed again. All 18 harness tests and 14 subtests pass.
The restarted `current-candidate-v2` uses candidate identity
`59fad19d6560b7830372adc33e31b0765b5932f6ffc4c1b8ec80af281aa837bf`
over 374 entries. Comparison with the first identity changes only the probe
runner and its harness tests; production and framework tests remain exactly
those of the successful full-v3 run. Startup, build and batch have passed
independent evidence verification; remaining sections and the final review
gate are pending. The v2 startup has slower model-listing and test-import
medians than planning, which will be reported rather than replaced with the
first capture's more favorable timings.

The v2 project section then failed the unchanged-write gate. All three Abacus
samples replaced `Column.scad` and its source record; all three V8 samples
replaced `CylinderUnit.scad` and `ValveMotion.scad` plus their records, with
identical before/after bytes and desired SCAD timestamps. Metamaquina2 passed.
A finite three-build disposable Abacus diagnostic reproduced the same churn
on both later builds, excluding the earlier cold-settlement explanation.
STL maps, manifests, source identity and original catalogue snapshots passed.
The failed raw section remains preserved. AR-07 is accepted as a remaining
WP4 production defect; Sol High owns its narrow red-first correction and
independent re-review. No additional settlement pass or weaker measurement
gate is authorized. All seven sections will be recaptured under a new identity
after the correction and a fresh combined/full test run.

AR-07 diagnosis refined the boundary: non-rigid assemblies can contain
state-dependent descendants, so merely admitting them to rigid SCAD reuse
would conflate distinct desired contents. The proposed correction is to retain
their latest desired text/currency state per canonical path during assembly
and publish only on successful assembly-phase completion, with fresh source
checks before and after the flush. This preserves final last-instance bytes
and per-instance in-memory composition; flexible publication and direct calls
outside a phase remain immediate. Separately, rigid reuse would track the
currently published identity per path, not every identity ever published there,
so an A/B/A sequence cannot falsely reuse historical A after B. Two focused
regressions are red; production is unchanged. Phase-completion coalescing
expands D4's publication boundary and is **proposed, not ratified**. Framework
work is paused for the pilot's decision under the framework-change skill;
no planning amendment, ADR promotion, spec sync or archival has occurred.

The pilot then explicitly ratified that revision on 2026-09-07. Sol High
reconciled the proposal, design D4, build-pipeline delta and task list; the
independent reviewer found no blocking ambiguity and strict OpenSpec validation
passed. The implementation was temporarily preserved in recoverable stash
`91fd62697532f5c6ac99af60cdb69e2960c0ad0b`; only the four planning files were
amended into commit `2ca4b9f06835d1133b6ad00eceecdee6e29b714c`. The planning
worktree was clean and exactly one commit ahead of cycle base before restore.
Tracked implementation content and every stashed untracked file were then
compared byte-for-byte with the stash; both comparisons passed. Historical
audit and planning-baseline checksum inventories also passed. The original
50 completion checkboxes were restored without claiming the three new tasks
5.6–5.8 complete. Sol XHigh now owns the correction because its phase boundary
is more consequential than the original WP4 mechanical reuse. Sync, ADR
promotion and archival still await fresh implementation and evidence review.

AR-07 is now implemented and independently closed. The expanded red run
recorded 11 failures before correction; the 24 focused publication tests are
green, with 343 combined geometry/currency/publication tests and 115 lifecycle
tests plus ten subtests passing. Independent re-review passed 27 focused tests.
The finite disposable-project proof completed nine builds: all three projects
had no SCAD/currency churn in either first-to-second or second-to-third
transition, equal STL maps/manifests, and unchanged original catalogue inputs.
The coordinator's new combined package run passed 153 tests and 51 subtests
(ten warnings), in 51.14 seconds. The full suite is running against frozen
candidate `b8b16185cb9e524c8cd119ff291c4a8d206fe4389794ef5293021909db39a4b0`
over 375 selected entries at amended planning HEAD. Only after it passes will
`current-candidate-v3` repeat all seven formal measurement sections; overall
review remains open until that complete evidence is verified.

The full-v4 run passed **1,773 tests and 353 subtests; 16 skipped, 49 warnings**
in 277.69 seconds (2,142 JUnit cases, zero errors/failures). Its complete frozen
candidate identity still matched after completion. The replacement
`current-candidate-v3` capture is now running with no competing task-owned CAD
tests; historical and incomplete capture records are preserved separately.

The v3 capture passed startup, build, batch, projects and empirical sections,
including zero real-project churn. It then stopped because all three algorithm
workers could not import the disposable `bench` fixture: the absolute worker
script path and framework-only `PYTHONPATH` omitted its verified fixture cwd.
Memory was not run. AR-08 is a harness defect, not a production regression;
the failed raw section and all prior v3 outputs remain preserved. The narrow
correction adds that disposable cwd after the framework root in worker import
paths and records the effective path, with a real subprocess regression and
independent re-review. A finite algorithms/memory smoke will precede the next
complete `current-candidate-v4` capture. No partial label supplies the final
comparative results, and no production change is proposed for this failure.

AR-08 is independently closed after 21 passing harness tests, including a
real subprocess importing its disposable fixture and proving the framework's
resolved module origin. Task 7.2 is also independently verified: the v3
empirical diagnostic contains 1/56/119/443 real bounds and 0/144/450/965
candidates, with exact legacy-X set and order equality in every case, alongside
the package's exhaustive/randomized tests. Final comparative claims will still
use only the forthcoming complete v4 label.

The finite `ar08-smoke` completed algorithms and memory with 14 successful
workers; coordinator verification passed every identity, structural and
equivalence gate. Its identity
`d3615253809628a7b9e988354f669da26a0a84ab2ac3855ac8b6cd4d20841250`
contains 375 entries and differs from the full-v4 tested identity only in the
runner and harness-test files. The replacement all-seven formal
`current-candidate-v4` capture was released with no task-owned competing CAD
tests. Smoke remains diagnostic only.

The replacement v4 capture completed all seven sections with **141 successful
workers** at the same frozen identity. Coordinator saved-evidence verification
passed current-byte equality, the generated-evidence inventory, historical and
planning inventories, catalogue provenance, and structural/equivalence gates.
Tasks 11.2–11.5 are complete. The disposition now traces every audit item to
production seams, red/green proof, v4 raw results and explicit limitations;
the human comparative report and final independent review are being completed.

Final raw-claim review found that Metamaquina2's saved available-baseline
comparison is not entirely equal: STL/piece aggregates match, but its viewer
manifest digest differs from planning. Settled-to-unchanged current manifests
and complete STL maps remain equal. The disposition's unqualified baseline
equality claim was corrected and task 11.4 reopened pending an exact semantic
explanation. The measurement verifier's successful gates do not themselves
require every available baseline field to be identical. No ADR, sync or archive
has started; the measurement owner and independent reviewer are diagnosing the
document difference with originals protected.

The coordinator recovered the exact saved baseline document identity without
changing any source, artifact or benchmark record. Taking the current disposable
Metamaquina2 document and replacing only its 226 changed root-tree `mtime`
values with those from the original project's older saved document produces
`d1ba8ddfdfc993b1d56f180877a3715a77e0e536dd6817a5e573928df88ec338`,
exactly 173,799 bytes: the immutable planning/v3 digest and length. The current
document is 173,857 bytes. Every non-timestamp field remains current. Source
timestamps were refreshed around 22:34 despite unchanged byte hashes, HEAD and
status; the provenance snapshots did not include timestamps. Paired legacy and
candidate builds with verified module origins agree under the same current
inputs, including the old import-path variant. The initial import-order
hypothesis is therefore not the cause, and no production or harness correction
is warranted for this document difference. Independent confirmation and the
final comparative report remained pending at that checkpoint.

## Final independent gate and integration authority

The independent Sol xhigh reviewer marked the complete candidate, all seven
measured sections, final report and disposition **green** on 2026-09-07.
AR-01–08 are corrected and re-reviewed; AR-09 was a disproved hypothesis,
closed by exact timestamp-only reconstruction without a code change.
See [DISPOSITION](remediation/DISPOSITION.md) and
[current-candidate-v4](remediation/current-candidate-v4.md).

The pilot explicitly requested “merge to main”. Primary framework `main` was
rechecked clean at the original `66401867b8510f0a24f6a0771b732aea6c949828`.
The audit commit plus this two-commit cycle can fast-forward it after the final
documentation, archive, tests and commit gates pass. The worktree and recovery
stash are retained; no push, release or unrelated checkout change is authorized.

Completion on 2026-09-08: ADRs 084–086 are Accepted, six capabilities are
synced, and the change is archived. Final focused validation passed 153 tests
and 51 subtests; the full suite passed 1,773 tests and 353 subtests with 16
documented skips. The final report, all 141 formal benchmark workers, 83
machine-evidence hashes and all 375 measured source/test/probe entries verify.
The implementation/archive commit was created and the worktree verified clean,
exactly two commits above audit base `40a848d`; this final bookkeeping closes
the remaining two self-referential tasks by amending only that implementation
commit. Planning remains `2ca4b9f`. The commit immediately following it is the
completed implementation record; exact final IDs are reported at handoff.
