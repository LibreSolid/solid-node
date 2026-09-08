## Context

The performance audit in `workflow/due-dilligence-performance/` is immutable historical evidence for framework commit `4bf9b69421b7114809af75fe663441d115407631`. Its real-project inputs were disposable copies of abacus, v8-engine, and Metamaquina2. This proposal is authored at `40a848d6f8939b3e0d69e45a11b514b4ebfa263f`, after the separate due-diligence remediation fixed all framework findings F01–F11 and C01–C04. In particular:

- F04 moved assembly and every artifact-producing phase under the project build lock.
- F05/ADR-081 made maximum-mtime equality insufficient by adding a per-contributor `(relative real path, device, inode, size, mtime_ns, ctime_ns)` fingerprint and node-scoped content fallback.
- ADR-067 requires every builder process to begin from a fresh interpreter because parent-side geometry imports can leave native thread-pool state that deadlocks a forked child. It also records process death between reload attempts as the module-state reset boundary.
- ADR-073 makes exact versus faceted comparison an explicit run-level policy. Performance work cannot silently substitute a faceted verdict for an exact one.
- ADR-070 refuses verdict memoization for flexible geometry because its identity changes with the binding. P04 concerns reusable geometry construction, not reusable intersection answers.
- ADR-049 fixes the static-equilibrium mathematics and diagnostics, but not a dense storage representation.

The audit's P01–P07 and dense-statics observation are related by one governing objective: remove repeated work or unbounded retention only where identity and lifecycle boundaries can prove reuse safe. They are divided into independently testable work packages so a failure in the process/lifecycle work cannot obscure a bounded algorithmic optimization.

During implementation review, the formal `current-candidate-v2` project capture found AR-07 on fresh disposable inputs: all three Abacus runs replaced byte-identical `Column` SCAD/source-record pairs and all three V8 runs did the same for `CylinderUnit` and `ValveMotion`, while Metamaquina2 stayed clean. A finite third Abacus diagnostic repeated the churn. The desired bytes and timestamps settled, but inode/change-time identity did not, because repeated non-rigid assembly instances immediately alternated values at one shared path. This is empirical scope for the P03 correction below, not green evidence for its implementation.

## Goals / Non-Goals

**Goals:**

- Address P01–P07 and the dense static-equilibrium risk with explicit correctness and memory bounds.
- Preserve observable build artifacts, build failure behavior, source currency, publication ordering, comparison verdicts, diagnostic determinism, and public naming.
- Retain fresh-interpreter isolation while amortizing repeated artifact passes within one verified source generation.
- Make every reused value name the complete identity on which it depends, and make every long-lived cache bounded with explicit disposal.
- Prove each finding red before changing production code, then prove output/correctness equivalence and remeasure the audited workloads on disposable project copies.
- Preserve benchmark provenance and freshness; never overwrite the original report, JSON, patch, XML, or reproduction scripts.
- Require an adversarial implementation review, disposition and re-review of fixes before OpenSpec sync or archive.

**Non-Goals:**

- No silent change to exact/faceted defaults, tolerances, or kernel routing.
- No flexible intersection-verdict memo and no new cross-instance exact-shape cache.
- No change to `Sim.trajectory`: retaining one snapshot per tick and driver is intentional behavior, not a leak.
- No unbounded worker pool, unsafe `fork`, parallel OpenSCAD scheduling, CAD-kernel tuning, viewer work, molejo work, or new dependency.
- No hard wall-clock CI threshold based on measurements from a shared host.
- No redesign of F04 locking or F05 currency; the work only consumes and regression-protects those settled contracts.

## Decisions

### D1. Treat remediation as ten independently provable work packages

The implementation is partitioned as follows:

| Package | Finding | Depends on | Suggested implementer |
| --- | --- | --- | --- |
| WP1 | Shared source-snapshot and instrumentation foundation | none | Sol, high |
| WP2 | Fresh builder per stable source generation | WP1 | Sol, xhigh |
| WP3 | Verified persistent piece facts | WP1 | Sol, high |
| WP4 | SCAD/write/source-census deduplication | WP1; coordinate with WP2 | Sol, xhigh |
| WP5 | Bounded flexible faceted geometry | none | Terra, high |
| WP6 | Adaptive conservative broad phase | none | Terra, high |
| WP7 | Linear automatic child naming | none | Sol, high |
| WP8 | Bounded exact placement cache | none | Terra, high |
| WP9 | Sparse-equivalent statics program | none | Sol, high |
| WP10 | Current-project remeasurement and adversarial review | WP2–WP9 | Sol, xhigh review |

WP1 is deliberately a foundation, not an optimization claim. WP2 and WP4 share its source-generation concept; WP3 uses the same filesystem observation vocabulary but owns a separate artifact-fact record. WP5–WP9 can be implemented and reviewed independently, but WP10 gates completion of the umbrella change.

Alternative: implement P01–P07 as one lifecycle rewrite. Rejected because it prevents red-first attribution, makes regressions hard to localize, and couples safe bounded algorithms to the higher-risk process change.

### D2. One spawned builder process owns one verified source generation (P01)

`solid build` and `solid develop` continue to start builders through the explicit `spawn` context. The parent still performs the preflight model resolution needed for current CLI error classification, and it passes only reconstructable plain values. The child loads the model afresh and may perform multiple `Builder` artifact passes in that same interpreter until it reaches `CURRENT`, `SOURCE_CHANGED`, or an appropriate failure/recovery boundary. A complete command therefore normally pays one fresh child import per stable generation, rather than one per rendered artifact.

A **source generation** is not the aggregate maximum mtime. WP1 first establishes a load-stability handshake: the loader/import seam records the pre-execution observable identity of the entry/facade and every project-local module before Python reads/executes it, then an uncached post-load census must match those observations after root instantiation. Project-local source execution must not trust Python's timestamp-and-size `.pyc` validation alone: the narrow project loader either compiles the coherently observed source bytes or verifies cached bytecode against a content identity strong enough to reject a same-size edit with restored mtime. This prevents both stale bytecode and an atomic replacement between Python reading old bytes and a later first census from blessing new disk identity as the identity of old live classes. A mismatch abandons the child and retries in a fresh interpreter. Newly imported project modules join through the same pre/post handshake, not by post-load discovery alone; external-library imports keep their ordinary Python behavior.

After load, artifact-producing seams bracket assembly/render work with the source set known to that producer: one fresh pre-phase census, shared by every node/currency check in the phase, and one uncached post-phase census. The recursively assembled contributor set—including foreign SCAD/JS/STL/STEP sources—is sealed only when its pre/post observations agree with the identities under which the work was performed. One sealed generation owns exactly one loaded root instance and one full assembly; continuation resumes pending artifact traversal on that memoized tree and does not re-import, reinstantiate, re-render structural `render()`, reassemble, or reorder exact fusion. Later checks occur before each retained pass, immediately before and after waiting for an asynchronous renderer, and immediately before document publication. A changed, missing, replaced, newly selected, or newly imported contributor ends geometry work with `SOURCE_CHANGED`; the supervisor then starts a fresh interpreter. A source edit that changes the import graph necessarily changes an importing file observed by the handshake and cannot publish from stale classes.

The project build lock remains continuously held only around assembly, artifact generation, and publication, exactly as F04 requires. The worker may loop while it owns the lock, but watches, callbacks, and project tests remain outside. A one-shot failure returns `FAILED` and ends the process; an initial `solid develop` failure keeps the established fatal-startup behavior. A watch-reload failure writes `errors.json`, releases the project lock, starts only the existing recovery watch (no further geometry in that stale process), waits for an edit, and exits `SOURCE_CHANGED` so the next attempt is fresh. This avoids both retained failed module state and a `FAILED` respawn/viewer-restart loop. OCCT work always begins in a spawned interpreter and never in a forked copy of the parent.

This amends ADR-067's chosen *process-per-iteration* mechanism while preserving its normative outcome: fresh native state, reconstructable targets, failure isolation, reload isolation, and a process that always reaches an outcome. After implementation evidence confirms the design, the completion phase should extract an ADR that explicitly amends ADR-067 and update `docs/architecture.md`.

Alternatives rejected:

- Keep process-per-artifact and only remove parent resolution: it preserves the dominant repeated child import and ADR-067 already rejected relying on what the parent happened not to import.
- Fork or forkserver with preloaded CAD modules: it weakens the native-state guarantee that resolved the deadlock.
- A persistent daemon across source edits or failures: it retains exactly the project/module state whose disposal is load-bearing.
- Maximum-mtime generation checks: F05 proved that a contributor can change beneath an unchanged maximum.

### D3. Persist only artifact-derived facts behind a strong artifact observation (P02)

Publication still serializes the live tree on every complete build. Names, counts, placements, hierarchy, source labels, document-relative model paths, drivers, instructions, expressions, and document version are reconstructed from the current model and are never supplied by a persistent piece cache.

The reusable unit is only `(full sha256, printable extents, volume, watertight)` derived from one completed STL in its own frame. It is stored in a private versioned fact record beside the artifact and swept with that artifact. The record carries the artifact observation made for that computation: real path plus device, inode, byte size, `mtime_ns`, and `ctime_ns`. Reuse requires exact equality of those observable fields and a current artifact under the node's existing source-currency contract. A missing, malformed, unknown-version, or mismatching record certifies nothing and causes recomputation. This has the same explicit limit as ADR-081: an external privileged operation that changes bytes while preserving all exposed identity fields must explicitly invalidate the artifact/fact record.

An artifact snapshot supplies one coherent read to every producer. It opens or pins the artifact, validates `fstat` and path identity before and after reading, and derives the full hash and mesh facts from the same immutable bytes/open identity. On a cache miss this seam must explicitly evict/bypass `cached_base_mesh`; calling the existing `(path, float-mtime)` mesh cache could recompute old geometry after a same-size, restored-mtime replacement. On a fact hit, any exported/copied bytes must come from the same pinned identity the reused facts describe. A concurrent replacement either leaves a coherent old open file for both facts and copy, or makes validation fail and retries; it cannot mix facts for one artifact with bytes from another. This abstraction applies whether or not the caller already holds the project build lock, and each producer closes its snapshot after publication/copy. The in-process fingerprint, base-mesh, local-bounds, and Manifold caches remain no broader than the observation that validates them on this path.

The full SHA-256 remains internal proof. The public 12-hex piece id remains compatible, but inventory aggregation compares full hashes; two different full hashes sharing a 12-hex prefix must fail with a deterministic collision diagnostic rather than merge unrelated pieces. A successful first computation atomically publishes the fact record only after the complete artifact has been read. Interruption leaves no valid record and costs recomputation, never a stale hit.

Alternative: index facts only by path/mtime, as the audit probe did. Rejected because replacement can preserve mtime and current code reads floating timestamps. Alternative: cache the whole prior document. Rejected because it would cache placement, hierarchy, metadata, and publication completeness rather than merely artifact facts.

### D4. Share generation work only inside the sealed source snapshot (P03)

WP1 supplies a request-local `SourceSnapshot`/generation context with a per-path metadata census and content-digest memo. Source fingerprint and digest computation consume that census only while its observations still match the sealed generation. Late project imports extend the source resolver/index and cannot be answered from a superseded module-set cache. No source metadata persists into a later worker generation.

Rigid base SCAD remains eligible for immediate generation-local reuse by canonical artifact path plus its full `(mtime_ns, node-scoped source digest, source fingerprint)` identity. The generation records the identity currently published at each path, not every identity historically seen there: a legitimate A→B→A sequence therefore performs all three publications. A repeated rigid identity may reuse the current artifact, while every node still runs its user render/as-SCAD work and retains its distinct operations, placement, address, and parent-document contribution.

Non-rigid, non-flexible assemblies require a different rule. Their descendants may be state- or binding-dependent even though the assembly itself is not a `FlexibleNode`, so source/currency identity does not prove two instances emit the same SCAD. Each call therefore computes its SCAD text, timestamp, digest, and fingerprint immediately and captures those immutable values in the active assembly phase. A phase-local ordered mapping retains only the latest desired value for each canonical artifact path; replacing an entry moves that path to the end, preserving the historical order of last occurrences across paths. Every instance still renders and contributes its own in-memory composition, but the path is not exposed at an intermediate instance state. At phase completion the final value—the same last-wins value the immediate path historically left on disk—is the only value considered for publication.

The assembly phase performs a fresh source checkpoint before flushing those final values, flushes under the still-active census and F04 project build lock through the existing atomic compare-before-replace/currency ordering, and performs another fresh checkpoint after the flush. A body or pre-flush checkpoint failure discards every pending value without publication. A flush error clears the remaining phase state and follows the existing assembly-error path; any already completed write has its ordinary atomic currency proof and no viewer document is published. A post-flush source mismatch ends the generation as source-changed before document publication, so a fresh process repairs any now-stale artifact. Nested source phases remain forbidden, preventing ownership ambiguity.

Flexible SCAD and binding-snapshot publication remain immediate and uncached because their selected binding is part of the produced geometry. A direct `generate_scad` call outside an assembly phase also retains immediate behavior because no safe phase lifetime exists to own a pending value. Atomic text/currency publication still compares before replacement: identical bytes, stamp, and record cause no mutation; metadata-only change restamps and refreshes the record without rewriting equal SCAD bytes; changed bytes use normal atomic replacement. No suppression or coalescing bypasses ADR-081 fingerprint comparison, node-scoped digest fallback, project lock ownership, or the pre/post generation checks.

Alternative: allow every non-flexible node into the immediate rigid cache. Rejected because a non-rigid assembly can contain binding-dependent descendants and first-instance reuse would change its final SCAD. Alternative: invent and persist a complete legacy binding/spec identity in artifact paths. Rejected as a broader identity and compatibility redesign not required to preserve current last-wins output. Alternative: a process-global or persistent source census or pending-publication map. Rejected because its lifetime would outlive the observed filesystem/module generation and could make stale work fast.

### D5. Keep a bounded source-aware flexible Manifold working set (P04)

The flexible faceted-geometry cache becomes an access-ordered mapping, initially capped at 64 entries for the test run. Its correctness key contains full, non-truncated identities: flexible technology, defining module/source identity and full current source fingerprint/digest, the full canonical structural identity from which `uniq_id` is shortened, the exact canonical sorted binding values from which `binding_hash` is shortened, and a full digest of the current serialized flexible shape/spec. Twelve-hex display/artifact hashes are never cache identity. This separates same-named classes, forced short-hash collisions, source edits, spec changes, and bindings. A hit reuses the evaluated base mesh, bounds, and admitted Manifold. A miss evaluates the current shape and mesh through `base_mesh()`, verifies Manifold admission, inserts the result, and evicts least-recently-used entries until the cap holds. Disposal removes Python references; no disk persistence is added. `base_mesh()` has no last-binding mesh memo to invalidate; the existing exact-only memo is not read by this faceted path and retains its current lifecycle.

This fixes the audit's interleaved three-binding case without promising that every binding of a long trajectory remains resident. `FlexibleNode._exact_solid()` remains the existing per-instance last-binding memo, and exact comparisons keep using it. Flexible comparison verdicts remain uncacheable under ADR-070; every comparison still runs the selected kernel on the geometry for the current binding.

Alternative: retain all bindings. Rejected as another unbounded trajectory cache. Alternative: cache flexible verdicts by binding. Rejected because P04 measured geometry construction and the verdict contract deliberately excludes flexible nodes.

### D6. Select the sweep axis adaptively while preserving existing pair order (P05)

For each of X, Y, and Z, a cheap endpoint sweep counts interval pressure without constructing all pairs. The broad phase chooses the axis with the lowest count, tie-breaking X then Y then Z. It performs the existing conservative active-interval sweep on that axis and checks the other two axes before accepting a candidate. Touching and zero-extent intervals remain active because comparisons stay inclusive.

Accepted candidates are canonical `(min_index, max_index)` pairs but retain the order the current X-axis sweep would emit: current-X-order rank first, then active-X-order rank. A bounded sparse-candidate buffer sorts by that key. If the accepted set reaches the buffer limit, the implementation abandons the adaptive buffer and streams the current X sweep, because a dense true-overlap set has no sparse-axis win worth quadratic retained memory. Thus optimized sparse cases keep existing first-foul diagnostics and statics column order, and dense cases keep streaming rather than materializing all pairs. The candidate set and order must equal the current X sweep and exhaustive AABB overlap for adversarial degeneracy, rotation, containment, coincident bounds, input permutations, and randomized boxes. Real geometry still reaches the selected narrow phase; no bound decides a mesh or substitutes a verdict.

Alternative: always choose the axis with the widest overall range. Rejected because range does not predict active overlap. Alternative: a new spatial-index dependency. Rejected because three axis sweeps are sufficient for the measured cliff and keep the implementation inspectable.

### D7. Build and validate one child-name ownership index per parent traversal (P06)

Each parent traversal snapshots relevant public attributes once: direct child object identities in insertion order, followed by each list/tuple attribute name and its ordered child identities; private attributes and the framework's `children` field are excluded. It builds an identity-to-name map in two phases so the first direct attribute always beats every list alias and the first eligible list attribute/position remains the fallback. The traversal links and names every returned sibling from that entry snapshot before recursing into any child's render/simulate/user code. Linking the batch then performs O(1) lookup per child and always refreshes `_parent`. The traversal-scoped seam must cover all current link consumers—`core/serializer.py`, `node/internal.py`, `node/qualified.py`, and `node/assembly.py`—without adding renders, so simulation enumeration and every publication walk receive the same saving and naming result.

The next traversal takes a new snapshot. A same-length in-place reorder, replacement, append/removal, direct-attribute reassignment, or alias change between traversals is therefore visible without an O(N) validation per child. A child that mutates its parent's public list during its own recursive work does not rename a later sibling halfway through the already-started parent traversal; that mutation becomes visible on the next traversal. This is a narrow timing amendment to previously unspecified mutable behavior and requires explicit ratification. A legacy caller that invokes `_link_child` singly still gets correct one-child lookup; framework walkers use the batch context. Explicit `name=` still wins, an unreferenced child keeps its class-name fallback, and parent links are refreshed.

Alternative: memoize `_attr_name_for(child)` indefinitely. Rejected because mutable lists and aliases would become stale. Alternative: validate or rebuild after each child's recursive user code. Rejected because raw Python lists expose no constant-time mutation version, so preserving mid-traversal mutation visibility would restore the quadratic scan. Two-phase sibling linking makes the observation boundary explicit and deterministic.

### D8. Bound exact placements with access-ordered retention (P07)

The exact module owns an LRU, initially capped at 512 `(shape identity, exact matrix bytes)` entries. A lookup is guaranteed to reuse a placement only while that cache entry is retained; an evicted placed shape still held by a caller does not make a later lookup a hit. A miss computes the exact placement, inserts it, and disposes the least-recently-used cache reference when the cap is exceeded. Rebuilding a source shape still eagerly evicts all placements for its prior identity. Shapes with no stable identity remain uncached.

The existing “once per shape and matrix” requirement is amended to “once while its cache entry is retained.” Re-visiting an evicted transform recomputes it exactly; eviction cannot change a comparison result. A fresh builder/develop process begins empty and its bounded cache dies with that source-generation process. The test manager clears run caches when establishing a new run policy; direct in-process/pytest callers share only the current interpreter's bounded cache and may use an internal reset seam in isolation tests. The cap is an internal implementation constant, not a user knob or public cache API. Initial caps are defaults to validate against the benchmark working sets and may be tuned during implementation without re-ratification while the bounded identity/lifetime contract remains unchanged. A long changing trajectory must plateau at the cap and demonstrate useful hits for a repeated working set smaller than the cap.

Alternative: clear only at the end of a test method or simulation. Rejected because one long sweep can retain thousands of transforms before that boundary. Alternative: weak references alone. Rejected because they do not define a reuse or memory bound.

### D9. Preserve the statics program in sparse storage

Static equilibrium keeps the same ordered variables, six rows per free body, target/tolerance scaling, non-negative contact forces, free declared wrenches, elastic slack, objective, bounds, and HiGHS method. The coefficient builder accumulates each `(row, column)` value in the exact existing nested-loop order before emitting one deterministic sparse entry for that cell; it does not hand duplicate floating contributions to a sparse coalescer that may reassociate them. The resulting SciPy sparse matrix is accepted by `linprog`; the two slack identities use `scipy.sparse.eye`, and sparse `hstack` forms `A_eq`. Targets, tolerances, objectives, bounds, and returned slack diagnostics remain one-dimensional arrays/lists.

Dense-reference characterization tests on existing fixtures and generated small systems must compare feasibility, per-body force/torque failure classification, deterministic ordering, and near-tolerance-boundary diagnostics. A structural allocation test must prove the production path creates no dense `rows × variables` matrix or dense identity, and a representative large sparse case must complete matrix construction with memory proportional to non-zero coefficients plus rows/columns, not free-bodies squared. Solver equivalence, not a looser heuristic, is the contract. The installed SciPy/HiGHS path accepts sparse equality input end to end and needs no new dependency.

Alternative: solve each body independently. Rejected because coupled contacts and counterweights are the reason ADR-049 chose one program. Alternative: change solvers or tolerances. Rejected because that would mix performance representation with physical semantics.

### D10. Evidence freshness and adversarial review are completion gates

Every package begins with a deterministic failing structural regression: child/process/construction/write counts, candidate-set completeness/order, cache bounds/eviction, or sparse allocation shape. Timing is supporting evidence, not the red assertion. Correctness tests include F04 lock contention and F05 same-max/same-size/restored-mtime cases before any performance claim.

After WP2–WP9 are green, copy the current versions of the same three catalogue projects to fresh disposable directories using the audit's protection rules. Record project commit/status and selected-source hashes; the framework planning HEAD plus a cryptographic content identity over source, tests, probe code, and fixed probe inputs (excluding generated measurement outputs and the hash record itself); interpreter/dependency/host/load identity; command and samples; process counters; output STL SHA-256 maps; manifest bytes or semantic differences where source metadata legitimately changes; assertion verdicts; and RSS/cache high-water marks. Separately inventory generated evidence after collection. This identifies the uncommitted implementation candidate without a self-referential hash or intermediate commit; the completed evidence later joins implementation commit 2. Label results as a new current-source measurement; never rewrite or relabel the original `4bf9b694` measurements. Benchmark scripts must refuse an original catalogue path as a mutation target.

An independent Sol xhigh reviewer then receives the complete proposal/specs, current source diff, red/green evidence, and measurements. Review must attack source-generation races, lock lifetime, cache identity/collision, stale in-process mesh reuse, flexible source/binding separation, conservative candidate completeness/order, naming aliases/mutation, eviction correctness, sparse feasibility equivalence, and evidence provenance. Every finding is recorded as accepted/fixed, rejected with evidence, or returned to the pilot. Any implementation fix triggers focused tests and a targeted re-review. OpenSpec sync/archive and ADR promotion remain forbidden until review and re-review are green; the pilot's initial ratification of this complete workflow is the authority to finish unless implementation evidence materially contradicts or underspecifies it and returns a choice.

## Risks / Trade-offs

- **[Retained builder observes an incomplete source set]** → Include loader/facade/imported project modules in the initial snapshot, seal the recursively assembled contributor set, compare at every artifact/pass/publication boundary, and terminate on any mismatch.
- **[Retained native/project state contaminates a new source generation or failure recovery]** → Never retain across `SOURCE_CHANGED` or `FAILED`; the spawned worker exits and the supervisor reconstructs from plain inputs.
- **[A fact miss is recomputed from stale process-local geometry]** → Key the mesh seam with the strong artifact observation or explicitly evict/bypass it; test same-process restored-mtime replacement as well as a fresh process.
- **[Persistent facts hide new model metadata]** → Persist artifact-derived facts only and always reserialize the current tree.
- **[Source-census reuse weakens ADR-081]** → Scope it to a sealed generation and compare current observations at every boundary; uncertainty invalidates.
- **[Coalescing hides a state-dependent assembly value or publishes after its source epoch]** → Keep every instance's in-memory composition, retain the historical last desired value only within the active assembly phase, flush under the F04 lock between fresh pre/post source checks, and leave flexible/direct publication immediate.
- **[Cache bounds trade hits for recomputation]** → Use access order, prove the audited working sets hit, measure long trajectories, and treat eviction as performance-only.
- **[Adaptive axis changes diagnostics or materializes a dense candidate set]** → Re-emit the exact current X-sweep order from a bounded sparse buffer, and fall back to the streaming X sweep at the buffer limit.
- **[Naming observation timing changes for a child that mutates its parent's list mid-traversal]** → Link all siblings from one explicit traversal-entry snapshot, prove between-traversal mutation and same-length reorder remain visible, and require ratification of the narrower deterministic timing.
- **[Sparse conversion changes feasibility or failure attribution]** → Preserve coefficient/variable ordering and compare against a dense reference across current and generated systems.
- **[Shared-host timings fluctuate]** → Require structural regressions and multiple samples; report timing distributions and environment rather than pass/fail thresholds.

## Migration Plan

This is an internal performance migration with no intended project-source changes. Existing build directories without fact records remain valid and compute/write the record lazily on their next complete publication. Unknown records are ignored safely. Cache policy changes require no persisted-data migration.

Implementation proceeds WP1 through WP10 under red-first discipline. After implementation and review prove the final design, extract the ADR-067 amendment and any other consequential accepted cache/lifecycle decision, update the ADR index and `docs/architecture.md`, synchronize delta specs, archive the change, and create the second cycle commit only under the framework-change completion workflow. Rollback removes the optimization paths and private fact records; old readers already ignore those private records, and missing records trigger recomputation.

## Ratification Record

The pilot ratified the original choices below before implementation began. After AR-07 exposed the non-rigid churn and implementation paused at the broader publication boundary, the pilot explicitly re-ratified choice 7 on 2026-09-07. That confirmation authorizes only the narrow phase-local correction recorded in D4; it does not broaden persistent identity, flexible caching, viewer behavior, or the F04/F05 contracts.

1. One spawned worker per verified source generation amends ADR-067, with process death retained at source-change and failure boundaries.
2. Private persistent artifact-fact records remain inside ADR-081's observable-filesystem boundary, including deterministic refusal of a public 12-hex id collision.
3. Flexible Manifold and exact-placement working sets are bounded. The initial 64/512 internal defaults are implementation tuning values, not public design decisions.
4. Adaptive broad-phase selection exactly preserves current X-sweep candidate order and uses a bounded-buffer fallback to streaming.
5. The package/model assignment and independent Sol xhigh adversarial review remain mandatory before sync/archive.
6. Two-phase sibling linking makes parent list/alias mutations during child recursion affect the next traversal, not names of later siblings in the traversal already in progress.
7. Non-rigid, non-flexible assembly SCAD publication is coalesced to the immutable last desired value per canonical path at the assembly-phase boundary, with last-occurrence ordering, fresh pre/post-flush checks, failure discard, immediate flexible/direct behavior, and rigid current-identity—not historical-membership—reuse.
