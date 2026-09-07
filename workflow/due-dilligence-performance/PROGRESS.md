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
- OpenSpec change: [bound-framework-performance-costs](../../openspec/changes/bound-framework-performance-costs/).
- Current gate: **explicitly ratified by the pilot; preparing planning commit and apply baseline**.
- Implementation, synchronization and archival: **not started**.

The same-worktree instruction overrides opening a new bench for this cycle.
The pilot explicitly ratified the complete proposal with “ratify” on 2026-09-07,
including all six design choices and the full implementation/review workflow.
This is standalone framework work, not sprint work. The cycle starts at the
audit commit above; its planning and implementation commits will follow that
commit. Nothing here authorizes integration, pushing, release or worktree removal.

## Full-list coverage

The proposal's design and tasks define package ordering, dependencies, model
assignments and proof requirements. This index tracks audit coverage, not a
second competing task list.

| Audit item | Required disposition | Status |
| --- | --- | --- |
| P01 — Process-per-artifact overhead | Amortize stable-source build work while retaining fresh-process isolation, reload correctness and error outcomes | Proposed work; not implemented |
| P02 — Repeated publication mesh facts | Reuse only verified artifact facts while preserving document contents, metadata changes and recovery | Proposed work; not implemented |
| P03 — Repeated SCAD writes/source work | Eliminate redundant generation and source work without weakening contributor currency or locking | Proposed work; not implemented |
| P04 — Flexible binding cache churn | Bounded, source-aware reuse of simultaneously useful geometry bindings; no flexible verdict memo | Proposed work; not implemented |
| P05 — Broad-phase orientation cliff | Reduce avoidable sparse-case comparisons while proving conservative completeness and diagnostic behavior | Proposed work; not implemented |
| P06 — Child naming cost | Reduce wide-tree bookkeeping, preserve alias/name precedence and between-traversal mutation, and explicitly ratify sibling snapshot timing | Proposed work; not implemented |
| P07 — Exact placement retention | Bound placement-cache growth while preserving exact placement results and useful reuse | Proposed work; not implemented |
| Additional: dense statics matrices | Measure and bound representation cost; preserve the existing equilibrium problem and diagnostics | Proposed work; not implemented |
| Additional: exact/faceted precision choice | Retain explicit kernel selection and epsilon semantics; no silent precision tradeoff | Preservation proof pending |
| Additional: simulation trajectory retention | Retain intentional trajectory behavior; do not label it a leak or silently discard history | Preservation proof pending |

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

## Current validation

The rebased pre-implementation framework baseline passed: **1,639 tests and
302 subtests; 16 skipped, 46 warnings**, in 209.68 seconds. Source and tests
were unchanged at 40a848d. See [the baseline record](remediation/README.md).
The historical audit's results remain separate and unchanged.

OpenSpec reports proposal, design, all six delta specs and tasks complete;
`openspec validate bound-framework-performance-costs --strict --no-interactive`
passed. This is planning readiness, not ratification or implementation progress.
See the [proposal preflight review](remediation/proposal-review.md) for findings
and their disposition. The exact post-implementation review gate is still pending.
