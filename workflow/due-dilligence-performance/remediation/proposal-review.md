# Proposal preflight review

Change: [bound-framework-performance-costs](../../../openspec/changes/bound-framework-performance-costs/).
Date: 2026-09-07. Author: Sol High. Independent reviewer: Sol XHigh.
Source baseline: 40a848d6f8939b3e0d69e45a11b514b4ebfa263f.

This is a read-only review of the proposed design against current source, not
an implementation review or performance result. No production or test code has
changed. Pilot ratification and the separate post-implementation adversarial
review remain mandatory gates.

## Findings and required dispositions

| Finding | Required proposal safeguard |
| --- | --- |
| Retained worker failure can spin the develop supervisor | Preserve reload-error recovery watching outside the build lock; wait for repair before requesting a fresh worker. Preserve initial and one-shot fatal outcomes. |
| A post-load source census can bless stale classes | Bracket project source execution with a load-stability handshake; defeat timestamp-valid stale bytecode and retry changed imports in a fresh interpreter. |
| Re-instantiation in a retained module can observe accumulated globals | One loaded root and assembly own the generation; continuation resumes pending artifacts on that tree. Prove constructor/render/assembly/fusion counts and order. |
| Persistent facts can recompute through weaker stale mesh caches | Bypass or invalidate weak path/float-mtime geometry entries when the strong artifact observation misses. |
| Hash, mesh facts and copied bytes can describe different replacements | Derive facts from one coherent artifact read and bind cache use/publication/export staging to the verified observation; cover concurrent replacement on hits and misses. |
| Public truncated ids are not full geometry identities | Use full identity for facts and flexible geometry; reject public piece-id collisions rather than merging artifacts. |
| Adaptive discovery can reorder diagnostics or retain quadratic pairs | Reproduce the existing X-sweep order, cap sparse buffering and fall back to the streaming sweep for dense candidates. |
| Once-per-parent naming changes mid-recursion mutation visibility | Explicitly ratify sibling prelink snapshot timing, preserve between-traversal mutations and cover all four framework walkers. |
| Exact placement retention lacks a precise lifetime promise | Bound an access-ordered cache, define ownership/reset, and promise reuse only while its cache entry remains retained. |
| Sparse duplicate coalescing can change floating-point association | Accumulate each cell in the existing loop order before sparse construction; compare cancellation and near-tolerance diagnostics with the dense reference. |
| Evidence cannot name a not-yet-created implementation commit | Identify the measured candidate by planning HEAD and source/test/probe/input content identity; inventory generated evidence separately to avoid a self-referential hash. |

All findings were sent to the proposal author for explicit incorporation in
design, delta requirements and red-first tasks. Internal cache capacities remain
tunable implementation constants, not new public configuration choices.

## Review status

Targeted independent re-review concluded: **ready for pilot ratification;
no blocking, high or medium proposal findings remain**. The reviewer checked
the revised proposal, design, six delta specs and tasks and confirmed coherent
disposition of the safeguards above. In particular, sibling snapshot naming is
an explicit compatibility choice, not a claim of unchanged mid-traversal
behavior. Strict OpenSpec validation also passed and reports all four planning
artifact groups complete.

This closes the proposal-text findings only. No finding is marked implemented
or empirically resolved by a planning-text correction. At preflight completion,
ratification and commits were pending. The pilot subsequently ratified the full
proposal on 2026-09-07; the execution index records subsequent commit/apply state.

The implementation review must independently inspect the eventual complete
diff, tests and fresh project evidence, record dispositions, and re-review fixes
before specification synchronization, ADR promotion or archival.
