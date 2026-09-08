## Why

The 2026-09-07 performance due-diligence audit measured avoidable repeated work in builds, publication, flexible geometry, spatial filtering, tree naming, and exact placement caching, and identified a dense static-equilibrium allocation risk. The audit was measured at framework commit `4bf9b69421b7114809af75fe663441d115407631`; this change addresses every finding against the current descendant `40a848d6f8939b3e0d69e45a11b514b4ebfa263f` while preserving the intervening correctness fixes, especially project-lock coverage and per-contributor source currency. A later formal candidate capture exposed AR-07: repeated non-rigid assembly instances continuously replaced byte-identical SCAD and currency files on disposable Abacus and V8 copies, so P03 also needs a safe assembly-completion publication boundary rather than an identity-unsafe broad cache.

## What Changes

- Amortize repeated artifact passes within one fresh builder process while retaining fresh-interpreter isolation, failure cleanup, source reload isolation, lock ownership, and a complete outcome boundary (P01).
- Reuse printed-piece fingerprints and geometry facts only under a persistent, source-current artifact identity strong enough to reject same-mtime replacement, with a recomputation path that cannot be served stale process-local mesh data (P02).
- Deduplicate SCAD generation and source-currency work within one stable source snapshot, coalesce repeated non-rigid/non-flexible assembly SCAD paths to their historically final desired value, and avoid replacing byte-identical generated text or currency records (P03).
- Retain a bounded, source-aware working set of flexible faceted mesh/Manifold geometry across simultaneously useful bindings without adding a cross-instance exact-geometry cache or memoizing flexible intersection verdicts (P04).
- Choose a deterministic sweep axis from the complete set of conservative bounds so sparse assemblies avoid an orientation-dependent quadratic candidate scan while retaining every true/touching candidate and stable diagnostic pair order (P05).
- Index automatic child-name ownership without changing explicit-name, direct-attribute alias, list-position, or parent-update rules; make each traversal use one entry snapshot so legacy list mutations remain visible on the next traversal rather than changing later siblings midway through the current one (P06).
- Replace unbounded exact-placement retention with a documented bounded run-level cache that preserves exact matrix identity and useful reuse while allowing old placements to be recomputed after eviction (P07).
- Build the static-equilibrium feasibility program with sparse matrices, preserving the same mathematical program, deterministic solver configuration, verdicts, and diagnostics while removing the avoidable dense quadratic allocation risk.
- Add red-first structural regressions and benchmark remeasurements on disposable copies of the three audited projects. Evidence will record source and framework provenance, freshness, output hashes/semantic equivalence, process/work counters, wall time, and memory; shared-host timings will remain observations rather than hard CI thresholds.
- Add an independent adversarial review gate after implementation and evidence. Every review finding must be dispositioned and any fix re-reviewed before specification sync or archival.
- Keep the exact-versus-faceted kernel as an explicit run choice and retain `Sim.trajectory` intentionally proportional to ticks × drivers; neither is treated as a defect.

No public callable is intentionally removed. Two existing spec/ADR contracts are amended rather than silently overridden: ADR-067's process-per-iteration mechanism becomes a fresh-process-per-source-generation mechanism while preserving its isolation outcome, and the exact-placement “once per shape and matrix” promise becomes bounded reuse with correct recomputation after eviction. Tree naming also gains an explicit traversal-snapshot timing rule: child-driven parent mutations apply on the next traversal, not midway through naming the current sibling batch. That compatibility choice requires ratification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-pipeline`: Bound repeated builder passes, define a source-generation guard stronger than aggregate maximum mtime, preserve fresh-process and locking guarantees, and make stable generation/publication avoid redundant writes.
- `printed-pieces`: Permit persistent reuse of content identity and geometry facts only under verified artifact identity and require stale in-process mesh state to be bypassed on recomputation.
- `source-closure-cost`: Share a source-metadata census only within one verified source snapshot while preserving the exact tracked set and late-import correctness.
- `node-model`: Preserve the public naming contract while making automatic naming linear for wide stable structures and correct under aliases and mutable legacy lists.
- `flexible-parts`: Define bounded, source-aware reuse of faceted evaluated geometry for multiple active bindings while preserving the existing per-instance exact memo.
- `test-framework`: Make broad-phase work orientation-adaptive and deterministic, bound exact-placement retention, preserve explicit kernel policy, and use a sparse-equivalent static-equilibrium formulation.

## Impact

Affected implementation areas are `solid_node/manager/build.py`, `solid_node/core/builder.py`, `solid_node/core/pieces.py`, source-generation/currency/closure and project-loading helpers, all four child-link consumers (`core/serializer.py`, `node/internal.py`, `node/qualified.py`, `node/assembly.py`), `solid_node/node/base.py`, `solid_node/node/flexible.py`, `solid_node/exact.py`, and `solid_node/test.py`, with focused and lifecycle tests under `tests/`. The change adds no required runtime dependency: SciPy's sparse structures and HiGHS interface are already available through the existing statics dependency. The 18 pre-existing historical audit evidence files inventoried at the cycle base remain byte-for-byte unchanged; new records and before/after evidence live under the separate remediation area and identify the audited baseline plus planning HEAD and a reproducible content identity for the uncommitted implementation candidate measured before commit 2.
