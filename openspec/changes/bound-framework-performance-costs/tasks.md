## Suggested execution map

| Work package | Scope | Dependency | Suggested model / effort |
| --- | --- | --- | --- |
| WP0 | Ratification, immutable evidence, current baseline | none | Sol, high |
| WP1 | Source-generation/census foundation | WP0 | Sol, high |
| WP2 | Retained fresh builder lifecycle (P01) | WP1 | Sol, xhigh |
| WP3 | Persistent verified piece facts (P02) | WP1 | Sol, high |
| WP4 | Generation/write deduplication (P03), including AR-07 phase publication | WP1; coordinate with WP2 | Sol, xhigh |
| WP5 | Flexible faceted working set (P04) | WP0 | Terra, high |
| WP6 | Adaptive ordered broad phase (P05) | WP0 | Terra, high |
| WP7 | Traversal-snapshot naming (P06) | WP0 | Sol, high |
| WP8 | Bounded exact placements (P07) | WP0 | Terra, high |
| WP9 | Sparse-equivalent statics | WP0 | Sol, high |
| WP10 | Combined evidence, adversarial review, completion | WP2–WP9 | Sol, xhigh |

The packages are review boundaries, not commit boundaries. The framework-change cycle still has exactly one ratified planning commit and one final implementation/archive commit; do not create intermediate implementation commits.

## 1. WP0 — Ratification and baseline evidence (Sol high)

- [x] 1.1 Present the complete proposal, six delta specs, design choices, package dependencies, model/effort map, and planned proof to the pilot; obtain explicit ratification before any source or test edit.
- [ ] 1.2 Run supported OpenSpec validation after ratification, create the planning-only commit including the repository-owned performance remediation index/baseline record, and verify the worktree is clean and exactly one commit ahead of recorded base `40a848d6f8939b3e0d69e45a11b514b4ebfa263f` before apply work.
- [x] 1.3 Verify the cycle-base inventory of the 18 tracked historical audit files recorded in `workflow/due-dilligence-performance/remediation/historical.sha256`, excluding the new `remediation/` records, so completion can prove the original report/raw evidence/reproduction assets remain byte-for-byte unchanged.
- [x] 1.4 Preserve the current full-suite planning baseline (`1,639 passed, 16 skipped, 46 warnings, 302 subtests`, 1,957 JUnit cases at source `40a848d6`, recorded under `workflow/due-dilligence-performance/remediation/`) as correctness context; do not describe it as a performance baseline.
- [ ] 1.5 Before production edits, run the relevant existing audit probes against planning HEAD into new remediation baseline files, using fresh disposable copies of abacus, v8-engine, and Metamaquina2 and refusing every original catalogue path as a write/restamp/build target; record project commits/statuses/source hashes and environment identity.

## 2. WP1 — Source-generation and census foundation (Sol high; depends on WP0)

- [ ] 2.1 Add red tests proving a post-load-only census can bless stale live classes after atomic source replacement and that timestamp/size-valid `.pyc` can execute stale bytes after a same-size restored-mtime edit; specify a narrow project-local source/bytecode freshness seam plus the import pre-execution/post-load identity handshake for entry/facade and every newly imported project module.
- [ ] 2.2 Add red tests for one distinct-path metadata observation per phase census across overlapping closures, a fresh uncached census at the next lifecycle boundary, late-import incorporation, missing/replaced contributors, and unchanged source-set/currency results.
- [ ] 2.3 Implement the immutable request-local source census and load-stability handshake using ADR-081's observable metadata fields; expose a phase/generation context without persisting source generations or placing source identity in viewer documents.
- [ ] 2.4 Bracket artifact-producing assembly/render seams with pre/post observations so foreign SCAD/JS/STL/STEP contributors are sealed only against the epoch under which work read them, and bracket asynchronous renderer waits with uncached checks.
- [ ] 2.5 Run source-set, loader, currency, watcher, exact/imported adapter, build-lock, and F05 same-maximum/restored-mtime regressions; confirm late imports and node-scoped digests remain correct.

## 3. WP2 — One fresh builder per stable generation, P01 (Sol xhigh; depends on WP1)

- [ ] 3.1 Add red structural tests showing a cold 24-artifact fixture starts one builder child for the stable generation rather than one per artifact, while producing the same complete filename-to-SHA-256 map and publication; count exactly one root construction, structural render/full assembly, and unchanged exact-fusion order across continuation.
- [ ] 3.2 Add red lifecycle/race tests for source replacement beneath the same aggregate maximum before lock acquisition, during assembly, during an asynchronous render, between retained passes, and immediately before publication; require no stale publication and a fresh-process retry.
- [ ] 3.3 Add red development regressions proving a reload failure writes `errors.json`, releases the project lock, waits without further geometry, and exits `SOURCE_CHANGED` only after repair, with no tight respawn/viewer-restart loop; preserve fatal initial develop failure and one-shot failure.
- [ ] 3.4 Implement the internal retained-pass loop inside one spawned builder generation over the same loaded and assembled memoized tree, preserving parent preflight error classification, reconstructable process targets, F04 lock lifetime, renderer cleanup, publication-last ordering, callbacks/watches outside the lock, and complete outcome reporting.
- [ ] 3.5 Re-run the real cold OCCT isolation proof after parent-side geometry import, multi-model builds, fusion ordering, lock contention, source-edit/recovery paths, and build/develop manager suites; confirm no fork/forkserver/unbounded worker path exists.

## 4. WP3 — Verified persistent printed-piece facts, P02 (Sol high; depends on WP1)

- [ ] 4.1 Add red tests counting mesh decode/hash work across fresh builder processes and requiring current artifacts with valid fact records to reuse only full digest, size, volume, and watertightness while reserializing current metadata/hierarchy/placements; require hash and mesh facts to derive from one pinned artifact read.
- [ ] 4.2 Add red same-process and fresh-process replacement tests where different same-size STL bytes retain mtime; prove the fact record and the lower `cached_base_mesh`/bounds/Manifold seam cannot return old geometry after inode/ctime identity changes, and add a concurrent export replacement test requiring copied bytes and facts from one coherent identity or a retry.
- [ ] 4.3 Add red tests for missing/malformed/unknown/interrupted fact records, atomic record creation, sweep ownership, artifact removal, and deterministic rejection of two different full SHA-256 values sharing one public 12-hex prefix.
- [ ] 4.4 Implement a private versioned artifact-fact record carrying full digest, facts, and strong artifact observation plus an artifact-snapshot seam that validates open/path identity before and after consumption; make recomputation bypass or evict every weaker process-local geometry cache, make export/staging bytes use the same pinned identity, and keep public piece ids compatible when no collision exists.
- [ ] 4.5 Run printed-piece, build/export/browser publication, content-currency, atomic-publication, and unreadable/unclosed-artifact tests; prove artifact facts never cache display/source/model/count/document metadata.

## 5. WP4 — SCAD, write, and source-census deduplication, P03 (Sol xhigh; depends on WP1 and coordinates with WP2)

- [ ] 5.1 Add red counters for repeated-instance SCAD generation, per-phase distinct-source stat/digest work, and unchanged SCAD/currency-file replacement on the audit fixtures and current real-project copies.
- [ ] 5.2 Add red correctness cases for distinct placements sharing one artifact, same path under different source/currency identity, metadata-only equal-content changes, real content changes beneath an unchanged maximum, and a source change between pre/post phase censuses.
- [ ] 5.3 Implement generation-local SCAD deduplication by canonical artifact path plus source/currency identity, and route overlapping node source work through the WP1 census without persisting it beyond the sealed generation.
- [ ] 5.4 Implement compare-before-replace for SCAD and currency records: perform no write when bytes/stamp/record match, refresh only stamp/record when scoped content is equal under changed metadata, and atomically replace changed content.
- [ ] 5.5 Run F04 build-lock and F05 currency suites plus SCAD/STL/exact/flexible/imported publisher tests; preserve every source-freshness and immediate flexible/direct-publication boundary.
- [ ] 5.6 Preserve the AR-07 red evidence from the formal disposable-project capture and add deterministic regressions for non-rigid/non-flexible instances producing different SCAD at one path, distinct in-memory compositions with historical last-wins final bytes, unchanged second/third-build inode stability, last-occurrence ordering across paths, and rigid A→B→A current-identity behavior.
- [ ] 5.7 Implement assembly-phase-local coalescing of immutable desired SCAD text/stamp/digest/fingerprint by canonical path, moving replacements to last-occurrence order; flush only final non-rigid/non-flexible values between fresh pre/post checks under the active census and F04 lock, discard on body/pre-flush failure, route flush errors through the existing assembly failure path, and retain immediate flexible/direct behavior plus rigid path-to-current-identity reuse.
- [ ] 5.8 Add source-race and failure proof for pre-flush discard, flush failure, post-flush source change, partial atomic safety, and no stale viewer publication; rerun the focused combined source/currency/builder/publisher suites and finite disposable Abacus/V8/Metamaquina2 builds before returning to WP10 formal capture and independent re-review.

## 6. WP5 — Bounded flexible faceted geometry, P04 (Terra high; depends on WP0)

- [ ] 6.1 Add red interleaved-binding regression reproducing the V8 shape: 80 flexible reads over three useful bindings construct exactly three meshes/Manifolds when the working set holds three, with identical bounds, volumes, and admission results.
- [ ] 6.2 Add red identity tests for same `uniq_id` from different defining modules/sources, forced collisions in shortened structural and binding hashes, changed source fingerprint or serialized spec with equal binding, adapter technology, eviction/revisit, and a long unique-binding sequence whose retained entries exceed the intended limit today.
- [ ] 6.3 Implement the access-ordered bounded cache over full source fingerprint/digest, full canonical structural identity, exact sorted binding values, full serialized-spec digest, evaluated mesh, bounds, and admitted Manifold; never use twelve-hex artifact/display hashes as correctness keys, dispose least-recently-used references, and keep the initial limit internal/tunable under the bounded contract.
- [ ] 6.4 Prove flexible comparison verdicts still execute on every call through the selected kernel, and prove `FlexibleNode._exact_solid()` remains the separate per-instance last-binding memo with no cross-instance exact cache.
- [ ] 6.5 Run flexible-node, molejo-adapter, exact/faceted policy, interference, and V8-oriented structural tests in both kernels where applicable.

## 7. WP6 — Adaptive ordered broad phase, P05 (Terra high; depends on WP0)

- [ ] 7.1 Add red scaling tests for 128/256/512/1,024 boxes overlapping on X and separated on Y or Z, using operation/candidate counts rather than wall-clock thresholds.
- [ ] 7.2 Add exhaustive and randomized tests proving adaptive candidates and emitted order equal the current X sweep for touching faces/edges/vertices, zero extent, containment, coincidence, rotation, each single-axis separation, input permutations, and real-project bounds.
- [ ] 7.3 Implement bounded `O(N log N)` pressure estimates, deterministic X/Y/Z tie-break, least-pressure candidate discovery, and current-X-order reconstruction from a bounded sparse buffer.
- [ ] 7.4 Implement and test the buffer-limit fallback that discards the adaptive materialization and streams the existing X sweep for dense candidates; assert bounded auxiliary pair storage and unchanged first-foul/statics column order.
- [ ] 7.5 Run all whole-assembly interference, support drop/lift, pairwise, exact/faceted, broad-phase completeness, and diagnostic-order tests.

## 8. WP7 — Linear traversal-snapshot child naming, P06 (Sol high; depends on WP0)

- [ ] 8.1 Add red wide-list tests at 128/512/2,048 children proving one public-attribute/list scan per parent traversal and constant-time lookup per linked child in simulation and publication walks.
- [ ] 8.2 Add red compatibility tests for explicit names, first direct-attribute alias precedence, first list membership, private/`children` exclusions, class-name fallback, repeated child identity, parent reassignment, append/removal/replacement, and same-length in-place reorder between traversals.
- [ ] 8.3 Add a red inter-child mutation regression pinning the ratified timing: all returned siblings are linked/named from the traversal-entry snapshot before child recursion, and a mutation made by one child's render/simulate appears on the next traversal rather than renaming a later current sibling.
- [ ] 8.4 Implement the two-phase batch-linking/index seam in all four consumers (`core/serializer.py`, `node/internal.py`, `node/qualified.py`, `node/assembly.py`) without extra renders; preserve correct single-child `_link_child` behavior for legacy direct callers.
- [ ] 8.5 Run node naming, driver qualification/state binding, simulation enumeration, declarative/legacy render lifecycle, serialization, and wide-tree 20-tick structural regressions.

## 9. WP8 — Bounded exact placement retention, P07 (Terra high; depends on WP0)

- [ ] 9.1 Add red tests showing unique transforms grow `_placement_cache` without bound, then cover access-order hits, least-recent eviction, exact matrix-byte distinction, unstable-shape no-cache behavior, and eager old-shape eviction after rebuild.
- [ ] 9.2 Implement an exact-module-owned bounded LRU for placed shapes with an internal/tunable initial limit, leaving local bounds tied to shape identity and never rounding transforms; start fresh builder/develop processes empty, reset at new managed test runs, and expose only an internal reset seam for direct isolation tests.
- [ ] 9.3 Add equivalence tests comparing cached, evicted/recomputed, and uncached OCCT placements and Boolean verdicts, including repeated working sets smaller than the limit and the case where a caller still holds an evicted placed object but a later lookup correctly recomputes.
- [ ] 9.4 Remeasure a long changing trajectory with cache entry count and process RSS samples; require retained entry plateau and report useful-hit behavior without claiming a universal bytes-per-shape law.
- [ ] 9.5 Run exact geometry, intersection memo, kernel-policy, keyframe, and rebuild-invalidation suites.

## 10. WP9 — Sparse-equivalent static equilibrium (Sol high; depends on WP0)

- [ ] 10.1 Extract a test-only dense reference of current matrix construction and add paired characterization over every existing statics fixture plus generated feasible/infeasible and near-tolerance systems, comparing feasibility, optimized slack, ordered body names, and force/torque classification.
- [ ] 10.2 Add red structural allocation tests proving production currently creates a dense `rows × variables` matrix and two dense identities, including the derived 1,000-free-body `576 * F²` slack-block risk without allocating that historical 576 MB in the test process.
- [ ] 10.3 Implement deterministic per-cell accumulation in the exact existing nested-loop order, emit one sparse entry per cell, convert to the installed SciPy sparse format, and build both slack blocks with sparse identity/hstack while preserving column/row ordering, targets, objective, bounds, tolerances, and `method='highs'`; do not delegate duplicate floating sums to sparse coalescing.
- [ ] 10.4 Run dense-versus-sparse equivalence and all `assertAssemblySupported` unit/meta tests, including counterweights, overhead couples, declared wrenches, stability margins, exact support-edge routing, repeated determinism, and broad-phase order.
- [ ] 10.5 Measure construction memory/nonzero counts on a representative large sparse system and show scaling with non-zero coefficients plus row/column vectors rather than free-body-squared dense slack storage.

## 11. WP10 — Combined proof and current-source remeasurement (Sol xhigh; depends on WP2–WP9)

- [ ] 11.1 Run every focused package suite together, then the complete framework suite, preserving warnings/skips and saving JUnit plus commands/environment under the new remediation evidence area.
- [ ] 11.2 Compute a cryptographic identity of planning HEAD plus uncommitted source, tests, probe code, and fixed probe inputs, explicitly excluding generated measurement outputs and the identity record itself; record it as the candidate measured by every post-change probe so no intermediate implementation commit or self-referential hash is needed, then separately inventory generated evidence.
- [ ] 11.3 On fresh disposable current-project copies, re-run build/startup/batch/project/empirical/algorithm/memory probes with multiple samples and load/environment provenance; record process/import/decode/write/stat/construction counts, timings, cache high-water marks, and RSS.
- [ ] 11.4 Prove output/correctness equivalence: complete STL filename-to-SHA-256 maps where expected, manifest byte equality for unchanged input, explicitly explained semantic differences for metadata-only refresh, piece facts, exact and faceted verdicts under separately named policies, broad-phase candidates/order, naming, and dense/sparse statics results.
- [ ] 11.5 Verify original catalogue statuses/source hashes before and after and verify the WP0 historical-evidence SHA-256 inventory byte-for-byte; fail the evidence check if any original project or historical audit asset changed.
- [ ] 11.6 Record a complete disposition table for P01–P07, dense statics, explicit exact/faceted choice, and intentional `Sim.trajectory` retention, linking each to its code, red/green tests, measurement, limitations, and status.

## 12. Adversarial review, correction, and completion (Sol xhigh; depends on section 11)

- [ ] 12.1 Give an independent adversarial reviewer the ratified artifacts, baseline/current evidence, complete uncommitted diff identity, tests, and measurements; require explicit review of load/source races, F04 lock lifetime, F05 currency, watch-failure recovery, persistent-fact and lower-cache identity, digest-prefix collision, flexible geometry/verdict separation, broad-phase completeness/order/memory, naming aliases/mutation timing, eviction correctness, sparse numerical equivalence, and provenance.
- [ ] 12.2 Record every review finding and disposition. For each accepted finding, add a red regression before the fix, implement the narrow correction, rerun affected and combined suites/evidence, update candidate identity, and obtain targeted re-review; return any material design conflict to the pilot for OpenSpec update and re-ratification.
- [ ] 12.3 Require a green final review and re-review record before completion. Do not sync specs, promote ADRs, archive, or create the implementation commit while an accepted finding is open.
- [ ] 12.4 After final evidence confirms the architecture, extract the accepted ADR-067 amendment and any other genuinely consequential decisions, update the ADR index and `docs/architecture.md`, and avoid ADRs for bounded mechanical optimizations that do not shift architecture.
- [ ] 12.5 Invoke the supported OpenSpec sync and archive workflows, run supported validation plus final focused/full tests, verify implementation/tests/evidence/completed record/specs/ADRs are coherent, and create the single final implementation/archive commit.
- [ ] 12.6 Verify the worktree is clean and exactly two commits ahead of base, then report both commits, tests, evidence provenance and limitations, review/re-review disposition, ADR disposition, archive path, worktree, and standalone integration target `main`; do not integrate, push, publish, open a PR, or remove the branch/worktree without explicit pilot authority.
