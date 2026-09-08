# Independent adversarial implementation review

Reviewer: independent Sol xhigh agent

Status: **green -- final implementation and evidence review passed**. The
reviewed candidate is
`d3615253809628a7b9e988354f669da26a0a84ab2ac3855ac8b6cd4d20841250`
over 375 entries at amended planning HEAD
`2ca4b9f06835d1133b6ad00eceecdee6e29b714c`. No accepted review finding
remains open. This decision releases ADR promotion, specification sync and
archival under the repository workflow; those later lifecycle mutations and
their post-archive validation are not claimed as already reviewed here.

## Static review coverage and final disposition

- WP1/WP2: reviewed coherent project-byte loading, pre/post import and phase
  observations, late imports, foreign OpenSCAD/STEP/JSCAD reads, retained
  passes, renderer wait cleanup, publication guard, failure classification,
  F04 lock lifetime, callbacks/watches, and supervisor process creation. Build
  and Develop use the explicit `spawn` context with module-level targets and
  plain inputs; no fork/forkserver or unbounded worker path was found. No open
  defect remains after AR-05.
- WP3: reviewed fact-record schema and malformed-record refusal, pinned
  artifact reads/copies, retry/closure, live metadata reconstruction, complete
  digest collision refusal, lower mesh/bounds/Manifold identity, builder,
  export, and browser staging. No open defect remains after AR-02.
- WP4: reviewed generation-local canonical-path/source-identity SCAD reuse,
  rigid/flexible separation, shared census work, text/record compare-before-
  replace, metadata-only restamp, and currency ordering. A privileged external
  replacement after an equality snapshot closes can race any publication
  boundary, but framework writers remain F04-serialized and the ratified
  ADR-081 boundary requires such a writer to invalidate; this is not a newly
  introduced certification path. AR-07's targeted production correction,
  candidate-wide proof and formal measurement are independently closed.
- WP5--WP9: reviewed full flexible source/structure/binding/spec keys and
  override bypass, 64-entry LRU and uncacheable verdicts; adaptive pressure,
  inclusive overlap, X/Y/Z tie break, legacy-X order and 8,192 fallback;
  two-phase naming precedence and inter-child timing in all four consumers;
  exact 512-entry access ordering, exact matrix bytes/signed zero, unstable
  shapes and held-eviction recomputation; and sparse coefficient addition
  order, deterministic emission, HiGHS program/tolerances, allocation, and
  dense-reference equivalence. No open implementation finding remains after
  AR-01 and AR-04.
- WP10 harness: reviewed candidate/input/catalogue identities, no-overwrite
  output, timeout process-group cleanup, raw failure preservation, nested
  worker status/candidate attribution, planning-baseline comparison labels,
  counters, and section verification. No open harness defect remains after
  AR-03, the second AR-06 correction, and AR-08; AR-09 records and closes the
  later disproved import-precedence hypothesis without a speculative change.

This static coverage is now joined by the frozen-candidate, full-suite and
all-seven evidence review recorded in the final section below.

## Candidate-wide verification incident -- closed

Root's first combined full-suite run produced seven later-suite failures after
the new retained-builder module. The failure was test isolation, not a
production lifecycle defect: five classes in
`tests/test_retained_builder_generation.py` invoke `Builder._start()` directly
in pytest's long-lived interpreter, where `_start()` intentionally exports its
selected `SOLID_BUILD_DIR`. They did not restore that process environment, so
later SCAD, snapshot-lock, CadQuery, and JSCAD tests constructed nodes against a
deleted prior temporary build directory. `_InProcessBuilderTest` now snapshots
and restores the variable with `addCleanup`, all five direct-call classes use
it, and every custom setup calls `super()`. Fresh-process tests are correctly
unchanged. My independent retained-module-plus-seven-victims reproduction
passed 21 tests in 48.87 seconds. The source-generation implementer separately
recorded the exact minimal sequence, 21-test run, and a diagnostic whole-suite
run of 1,756 passed, 16 skipped, and 353 subtests; final candidate-wide proof
remains pending after later corrections.

## AR-01 -- stale exact-shape side identities make the test suite flaky

- Severity: medium (verification integrity; historical test isolation defect,
  not caused by the WP8 LRU production change)
- Affected paths: `tests/test_tessellation_precision.py:151`,
  `tests/test_tessellation_precision.py:466`, and
  `tests/test_exact_geometry.py:175`; the paired production invariant is at
  `solid_node/exact.py:24-36` and `solid_node/exact.py:62-69`.
- Violation: those existing test fixtures clear `_shape_cache` alone, leaving
  `_shape_keys`, `_bounds_cache`, and `_placement_cache` alive. The production
  invariant makes `id(shape)` safe only while `_shape_cache` retains that
  shape. Breaking the invariant in a test permits a later unrelated CadQuery
  shape that reuses the Python address to be recognized as an old BREP. A
  matching placement key can then return unrelated geometry, as observed by
  the order-dependent failure of
  `ExactIntersectionTest.test_volume_assertions_share_the_exact_helper`.
- Deterministic evidence: in one interpreter, running
  `pytest.main(["-q", "tests/test_tessellation_precision.py",
  "tests/test_exact_geometry.py::ExactArtifactTest"])` and then comparing
  `{id(value) for value in exact._shape_cache.values()}` with
  `set(exact._shape_keys)` produced `shape_cache=1`, `shape_keys=16`,
  `stale_ids=15`, and `placements=11`. The reported wrong-volume symptom did
  not recur in two fresh command runs because it additionally requires
  allocator address reuse; the orphaned state itself is deterministic.
- Cause classification: planning commit `4bcf4cb5` already has the same paired
  `_shape_cache`/`_shape_keys` invariant and the same incomplete fixture
  clears. Production `_evict()` removes both together. WP8 changes only
  placement key bytes, ordering, capacity, and the managed-run placement reset.
- Required correction: use one coherent private reset for the four related
  exact caches in these fixtures (or equivalently clear all four in an order
  that cannot leave a held shape falsely stable), and add a regression proving
  a formerly held shape is unstable after reset. Do not change the LRU policy
  to mask the fixture defect.
- Re-review: **closed**. `tests/exact_test_support.py` clears dependent
  `_shape_keys`, `_bounds_cache`, and `_placement_cache` before releasing
  `_shape_cache`; the three incomplete fixtures now call it.
  `tests/test_exact_test_isolation.py` populates all four registries, proves
  they are all empty after reset, proves a held former cached shape has no
  stable identity, and proves two subsequent placements are uncached distinct
  objects. The independent focused re-run passed 28 tests and 12 subtests.
  The Terra exact-placement implementer separately recorded two fresh
  repetitions of the formerly failing ordered suite at 306 passed and 1
  skipped, coordinated by root.

## AR-02 -- a replacement between Manifold lookup and verdict identity caches a stale false negative

- Severity: high (comparison correctness)
- Affected paths: `solid_node/test.py:371-386`,
  `solid_node/test.py:539-573`, and `solid_node/test.py:1308-1319`; the lower
  caches correctly bind decoded mesh, bounds, and Manifold at
  `solid_node/test.py:278-305`.
- Violation: the faceted direct-pair helper first obtains each cached Manifold
  and bounds from one strong artifact observation, but then independently
  re-observes both paths to construct the verdict key. If an artifact is
  atomically replaced in that interval, the Boolean uses the old Manifold
  while the result is stored under the new artifact identity. Later
  comparisons of the new artifact hit that stale verdict. This contradicts
  D3's requirement that the in-process Manifold and faceted-verdict identities
  remain no broader than the observation that validates them, and can turn a
  real interference into a cached no-interference result. The placement-record
  path has the same split: it obtains local bounds, then re-observes the path
  for its faceted identity, while its deferred Manifold can later load yet
  another observation. A replacement can therefore pair old broad-phase bounds
  with new geometry and incorrectly cull an interference before any Boolean.
- Deterministic evidence: a disposable diagnostic created a 1 mm box at the
  first path and another 1 mm box translated 3 mm away. Immediately after
  `_fast_geometry()` returned the first old Manifold, it atomically replaced
  that path with a 10 mm box. The raced call returned
  `IntersectionStats(is_empty=True, volume=0.0, exact=False)` and cached it
  under the replacement's identity. A second ordinary call returned the same
  cached empty result; after clearing only `_verdict_cache`, the same current
  files and matrices returned
  `IntersectionStats(is_empty=False, volume=1.0, exact=False)`.
- Required correction: carry the exact artifact observation used by
  `_cached_manifold`/`_cached_local_bounds` through `_fast_geometry` into the
  verdict key, or validate that observation after the Boolean and decline to
  cache/raise on replacement. Add a deterministic regression covering the
  replacement interval and proving no old result is reusable under the new
  identity. Review both direct-pair and placement-record paths for the same
  split-observation pattern.
- Re-review: **closed**. `_cached_manifold()` now returns the strong
  observation that supplied its mesh, bounds, and admitted Manifold;
  `_fast_geometry()` carries it directly into the verdict key. Placement
  construction takes one observation before local bounds, carries it into the
  record, and makes `_DeferredManifold` request that same observation. If the
  retained decode for an old record is no longer available after replacement,
  the pinned-observation rebuild raises `ArtifactChanged` instead of reading
  the replacement under predecessor bounds. The two deterministic regressions
  now prove respectively that the raced old direct result is not served for
  the replacement, and that an old placement retains old bounds/Manifold while
  the next placement obtains the new identity, bounds, and interference.
  Independent re-run: 4 passed including AR-04 below (one pre-existing
  legacy-render warning). The separately generated affected-suite evidence is
  157 passed, 21 subtests, and two warnings.

  `_solid_geometry()` still obtains an exact BREP shape separately from its
  faceted STL observation. This is not an unclosed AR-02 variant: D3 expressly
  scopes this correction to the byte-derived STL fact path and its in-process
  fingerprint/base-mesh/local-bounds/Manifold caches. Framework-owned BREP and
  STL production remains serialized by the unchanged project build lock and
  currency protocol; an uncoordinated external replacement between two exact
  artifacts was possible before this change and is outside the ratified
  strong-STL-observation boundary. No new exact cache contract was inferred.

## AR-03 -- the measurement assembly counter classified every real first assembly as cached

- Severity: medium (evidence integrity; found before measurement)
- Affected path: `workflow/due-dilligence-performance/remediation/current_performance_worker.py`,
  initially in `counted_assemble`.
- Violation: `counted_assemble` classified a computation only when `_assembled is None`,
  although every node initializes `_assembled = False`, so a real first root
  assembly would have recorded zero computations. These counters are part of
  the required WP10 proof of census work and retained assembly, not decorative
  diagnostics.
- Required correction: recognize the actual unassembled sentinel and gate the
  real-worker result on exactly one computation. Keep source-observation path
  counters internally checked against the global call count.
- Re-review: **closed**. `root_assembly_will_compute()` now recognizes only the
  explicit `False` sentinel without invoking arbitrary truthiness, its unit
  test covers fresh, completed, and hostile truthiness states, and the section
  verifier requires exactly one computation. An authorized disposable Solid2
  Builder-detail smoke recorded three legitimate root `assemble()` invocations
  but one computation, and source-observation global/per-phase totals of 40/40;
  13 harness tests passed. An earlier review of the live, concurrently edited
  harness appeared to show a duplicate per-path observation increment. That
  condition could not be reproduced once writers stopped: the inspected
  candidate has exactly one labelled increment and a hard 40/40-style runtime
  consistency assertion. It is withdrawn as a concurrent-inspection artifact,
  not claimed as a separate historical defect.

## AR-04 -- a stale rigid artifact path enables forbidden flexible-verdict memoization

- Severity: high (comparison correctness; historical edge defect, but the
  ratified flexible-parts delta explicitly requires that it remain impossible)
- Affected path: `solid_node/test.py:371-386` and
  `solid_node/test.py:1308-1319`.
- Violation: `_fast_geometry` correctly evaluates a flexible node from its
  current binding, but the direct-pair helper then builds the verdict key from
  `node.stl_file` without checking flexibility. A flexible leaf normally does
  not write that rigid path, which makes the identity `None` by accident. If a
  stale file exists there (for example after converting a formerly rigid node),
  the first current-binding Boolean is cached by that unrelated file identity;
  later reads, including changed bindings at the same placement, can reuse the
  old verdict. This violates the delta's unconditional requirement that every
  comparison involving a flexible node execute the selected Boolean for the
  current binding.
- Deterministic evidence: in a disposable build directory, a real
  `Valvetrain`/`Spring` was assembled at lift 4, a valid box STL was written to
  the flexible spring's otherwise-unused `stl_file`, and the same faceted
  spring/retainer comparison was invoked twice. `_faceted_verdict` ran once and
  `_verdict_cache` gained one entry; without that stale file the existing test
  passes only because `_geometry_identity` returns `None`.
- Required correction: propagate an explicitly uncacheable faceted verdict
  identity for flexible geometry through the same AR-02 identity plumbing,
  independent of filesystem contents at `stl_file`. Add a regression with a
  present stale path and a binding change; it must invoke the Boolean for each
  comparison and retain no flexible verdict.
- Re-review: **closed**. The flexible `_fast_geometry()` branch now carries
  `None` as its verdict identity unconditionally, so `_verdict_key()` declines
  every such cache insertion regardless of nominal-path contents. The real
  Valvetrain regression creates valid stale spring and retainer STLs, changes
  the lift binding between comparisons, and proves two faceted Boolean
  invocations with an empty verdict cache. It passed in the independent
  four-test re-run recorded under AR-02.

## AR-05 -- recovery does not watch a known missing foreign source outside the entry subtree

- Severity: medium (development recovery availability; the directory limit is
  historical, but the newly ratified initial foreign-source recovery path
  makes this case explicit)
- Affected path: `solid_node/core/builder.py:473-515`, especially
  `_on_reload_exception()` passing `node.files` to `_watch_broadly()` while
  `_watch_broadly()` schedules only `dirname(realpath(self.path))`.
- Violation: after construction succeeds but the initial census finds a
  foreign contributor missing, a reload correctly records the failure and
  waits outside the build lock. It also adds the missing path to
  `_watched_sources`, but that event filter cannot help if the observer did
  not subscribe to a directory containing the path. With a path-based entry
  such as `models/model.py` and a valid contributor such as
  `assets/shape.js`, recreating the known missing foreign source is outside
  the recursively watched `models/` subtree. The reload worker consequently
  waits indefinitely instead of exiting source-changed on the relevant
  repair. This contradicts the retained-builder requirement that a
  watch-reload failure wait under the recovery watcher and exit on repair,
  including the recursively discovered foreign source set.
- Deterministic evidence: a disposable `Builder` with entry
  `/tmp/<root>/models/model.py` and known source
  `/tmp/<root>/assets/shape.js` was given a mocked observer and
  `_watch_broadly([shape.js])` was invoked. Its only subscription was
  `schedule(..., "/tmp/<root>/models", recursive=True)` and a common-path
  check printed `covered=False`. The current real-process regression keeps
  `shape.js` beside its entry module, so it does not exercise this layout.
- Required correction: ensure recovery subscriptions cover every known source
  that may be repaired (including a presently missing path) as well as the
  existing broad Python recovery area, without turning unrelated foreign
  changes into reloads. Add a real or faithful observer regression with a
  nested path entry and a known non-Python contributor in a sibling project
  directory, proving repair ends the waiting worker outside the lock.
- Re-review: **closed**. `_watch_broadly()` now retains the entry directory as
  the only broad-Python area, adds the nearest existing parent of every exact
  known source as an observer candidate, and drops recursively redundant
  descendant subscriptions. `on_modified()` admits an event from those wider
  transport subscriptions only when its canonical path is an exact known
  source; Python outside the original entry subtree and unrelated foreign
  files remain irrelevant. The real-watchdog regression removes both sibling
  `assets/shape.js` and its parent, proves new unrelated JavaScript and Python
  files do not wake recovery, and proves recreation of the exact known path
  ends the worker outside the lock. The pre-fix run failed after 18.59 seconds;
  the correction's focused evidence is 85 passed plus 7 subtests. My
  independent combined re-run of that exact real-process regression and the
  complete harness suite passed 17 tests and 14 subtests in 3.63 seconds.

## AR-06 -- the evidence verifier accepts failed no-write and exact-cache outcomes

- Severity: medium (evidence integrity; found before measurement)
- Affected path:
  `workflow/due-dilligence-performance/remediation/run_current_performance_probe.py:545-627`.
- Violation: the build and project records capture `unchanged_churn`, including
  inode/mtime/ctime changes, but `verify_section()` gates only the STL content
  map and manifest bytes. It therefore accepts an unchanged build that rewrote
  byte-identical SCAD/currency files, despite the ratified no-replacement
  outcome. The exact-placement memory verifier checks only the last sample's
  cache count and ignores the recorded working-set result. It accepts a prior
  sample above the internal cap if the last sample is at the cap, and accepts
  zero useful hits, despite the WP8 measurement requirement to show both a
  plateau and useful working-set reuse.
- Deterministic evidence: direct calls to `verify_section()` with otherwise
  valid minimal records printed both
  `accepted_nonempty_unchanged_churn=True` for a build record whose
  `unchanged_churn.changed` contained `part.scad`, and
  `accepted_overcap_intermediate_and_zero_hits=True` for placement samples of
  999 then 512 entries at a 512 limit with 0 hits/12 constructions. Neither
  call raised.
- Required correction: gate every unchanged-build/project churn record on an
  empty `changed` list (and the analogous settled-detail churn where it claims
  no mutation). Gate every exact-placement sample at or below the cache limit
  and require the fixed repeated working set to demonstrate its expected
  reuse, or at minimum a positive useful-hit count consistent with the
  recorded requests/constructions. Add negative harness tests proving these
  contradictory records are rejected.
- Re-review: **reopened** after the first formal capture. Section verification
  correctly rejects any changed entry in
  settled unchanged fixture/project/detail churn and separately requires zero
  actual SCAD publishes or restamps on the warmed real-Builder detail path;
  first generation and the intentional metadata-refresh probe remain outside
  that no-mutation assertion. Exact-placement verification now requires the
  bounded mode, the exact 1,000/4,000/8,000 sample sequence, every sample at or
  below its reported internal limit, and the fixed 12-request working set to
  report exactly three constructions plus nine hits while remaining bounded.
  Three red-first negative tests cover unchanged churn, an early over-cap
  sample, and zero reuse. My independent combined re-run of all 16 harness
  tests with the AR-05 real-process regression passed 17 tests and 14 subtests
  in 3.63 seconds. The five current harness hashes independently match the
  durable red/green record in `ar06-harness-verifier.md`.

  The immutable `current-candidate-build.json` then exposed that `build_section`
  took its purported settled snapshot immediately after the cold CLI build.
  In all nine Solid2 samples the first same-source warm build legitimately
  completed representation settlement: the root Machine SCAD changed bytes
  (for count 1, 56 to 102 bytes as final child-STL references became usable),
  and its `.scad.sources` record was republished with identical bytes. All
  workers succeeded and the complete STL maps and manifests remained equal;
  all six exact samples had no churn. The hardened gate correctly stopped the
  run, but it was applied to a transition whose desired SCAD state was not yet
  byte-identical. This is not a production violation of the ratified rule,
  which suppresses replacement when bytes, timestamp, and currency already
  match and permits atomic replacement when desired bytes differ.

  Required follow-up was to preserve cold and first-warm timing/comparison data, take
  the settled snapshot after that first warm build, run a third same-source
  build, and apply the zero-churn gate to first-warm to third-build only. Keep
  the failed evidence immutable. Because the harness Python content is part of
  candidate identity, the corrected seven-section capture must use a new label
  and identity, then receive another targeted review before overall green.

  Second re-review: **closed**. `build_section()` is now an explicit finite
  three-pass sequence with no retry loop. It retains cold and first-warm worker
  timings and the post-cold planning comparison, records cold-to-first-warm
  churn without rejecting legitimate byte changes, then compares the snapshot
  after first warm with a third same-source build and applies the zero-churn,
  STL-map, and manifest gates only there. The verifier requires all three
  successful worker records and every named state record, so an old two-pass
  shape cannot pass. A red-first negative test proved the missing-third-pass
  shape was previously accepted; the correction adds both its rejection and
  acceptance of settlement churn followed by an unchanged third pass. My
  independent harness run passed 18 tests and 14 subtests in 0.37 seconds.
  Current hashes match the owner handoff (`run_current_performance_probe.py`
  `a5deca…d6ce`, harness tests `1726cd…6b3c`), and independent recomputation
  yields new candidate identity `59fad19d…37bf` with 374 entries. The failed
  first-label evidence remains intact. Overall green still requires all seven
  successful sections under the new label.

  The new-label project section then stopped on real continuous unchanged
  churn. This does not reopen the verifier correction: unlike the build
  fixture's one cold-to-first-warm byte transition, every affected project
  SCAD and sidecar retained identical bytes and the churn repeated on a third
  invocation. The AR-06 gate is correctly rejecting AR-07 below and must not
  be weakened.

  Planning-amendment provenance re-review: **closed**. Candidate identity and
  every newly captured section must now name amended planning HEAD
  `2ca4b9f06835d1133b6ad00eceecdee6e29b714c`, while the immutable seven-section
  planning baseline is independently inventoried and each baseline JSON is
  required to retain provenance commit
  `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c`. The inventory records both values
  and requires them to be distinct; the saved-evidence verifier checks this
  before section semantics. The three changed harness hashes match the owner
  handoff (`current_performance_common.py` `feb66661…87cc`, verifier
  `ea99e5fb…7ec5`, tests `513c51f2…a9e0`), and my independent lightweight run
  passed all 19 tests in 0.327 seconds. No formal capture, baseline mutation,
  or candidate identity was produced by this review.

## AR-07 -- repeated real-project instances continuously replace byte-identical SCAD state

- Severity: medium (ratified performance/write-amplification contract)
- Affected paths: `solid_node/node/base.py:848-864` and
  `solid_node/source_generation.py:542-551`; formal evidence is the immutable
  `current-candidate-v2-projects.json`.
- Violation: a stable, already-settled same-source project build replaces SCAD
  and currency records even though desired SCAD bytes, artifact mtime, and
  recorded currency bytes are unchanged. This directly violates the
  build-pipeline requirement that matching text/timestamp/currency state retain
  inode, mtime, and ctime. It is not the permitted metadata-refresh case and
  not the build fixture's one-time changed-byte representation settlement.
- Reproducible evidence: all three Abacus repeats replaced the same Column
  `.scad` inode and changed its `.sources` ctime while both files retained the
  same SHA-256. All three V8 repeats did the same for CylinderUnit and
  ValveMotion (four changed files per run); all three Metamaquina2 runs were
  clean. Complete STL maps, manifest bytes, project-copy hashes, candidate
  identity, and every worker status remained correct. The formal verifier
  stopped on the first affected project. A separately authorized finite
  three-invocation Abacus diagnostic reproduced the same two identical-byte
  mutations from first to second and second to third, excluding settlement.
- Cause and design boundary: `generate_scad()` remembers
  `(realpath(scad_file), (mtime_ns, source_digest, source_fingerprint))` only
  when `self.rigid`. Column, CylinderUnit, and ValveMotion are repeated
  `AssemblyNode` classes, whose framework base sets `rigid = False`, so every
  occurrence bypasses the generation cache and logs `generated`. Their
  per-instance states can oscillate one shared output path through distinct
  intermediate desired text and end with the same last-instance bytes on every
  build. The next build therefore replaces the prior final bytes on its first
  occurrence and later returns the path to the identical final bytes.
  Crucially, `rigid` is also a real safety boundary, not merely the wrong
  discriminator: a non-flexible Assembly can compose flexible or otherwise
  binding-dependent descendants, so its SCAD can differ across instances under
  the same source identity. Simply changing eligibility to `not flexible`
  would freeze the first instance's state-dependent text and conflict with
  WP4's recorded legacy-non-rigid bypass. The observed write defect is proven;
  a safe correction such as phase-level coalescing to the historical final
  desired state changes publication timing. Implementation correctly stopped
  at that boundary; the pilot subsequently authorized the narrow design in
  amended planning commit `2ca4b9f06835d1133b6ad00eceecdee6e29b714c`.
- Required correction/decision: establish the invariant promised by WP4 for
  repeated instances sharing a canonical artifact without conflating genuinely
  different state-dependent content or weakening fingerprint/currency checks.
  Preserve per-instance composed geometry and the externally observable final
  SCAD selection; a set-only A→B→A memo must not suppress B and then falsely
  claim the final A was written. If last-desired phase coalescing or another
  timing change is not authorized by the amended design, return that choice to
  the pilot before implementation. Add a
  deterministic real Abacus/V8-shaped or minimal regression proving a second
  and third stable build retain SCAD and sidecar identities, binding-dependent
  Assemblies keep their distinct in-memory geometry, and the flexible path
  remains uncached. Preserve the failed project record and keep the zero-churn
  verifier gate unchanged.

  Design review and ratification: the proposed narrow repair was technically
  coherent but outside the original ratification, so production remained
  frozen until the pilot explicitly re-ratified it. The proposal, D4 design,
  build-pipeline delta, and WP4 tasks now record the boundary coherently in
  planning commit `2ca4b9f06835d1133b6ad00eceecdee6e29b714c` (clean and
  exactly one commit ahead of base `40a848d6f8939b3e0d69e45a11b514b4ebfa263f`
  before implementation restoration). During an active assembly
  source phase it would retain the latest immutable desired text and complete
  currency tuple per canonical path for non-rigid, non-flexible nodes, then on
  clean exit perform a fresh pre-flush checkpoint, atomic compare/write, and
  fresh post-flush checkpoint. Body or checkpoint failure must discard all
  pending writes, flush failure must propagate, and queued state must remain
  phase-local. Flexible generation and direct calls outside a phase remain
  immediate; rigid generation remains immediate but its memo must represent
  only the path's current identity, rather than a historical identity set, so
  A→B→A cannot leave B while claiming A is current. The queue must retain
  historical last-occurrence semantics (including cross-path ordering where
  partial-failure observability matters), and generation logging must describe
  actual flushed writes rather than discarded requests. Tests must cover
  binding-dependent per-instance output plus last-wins disk output, clean
  second/third-build identity retention, flexible/direct immediacy, discard on
  body and pre-flush failure, post-flush race/failure handling, and rigid
  A→B→A. The amended design authorized that publication-timing change and
  released the narrow production implementation for the targeted review below;
  candidate-wide verification and a replacement seven-section capture were
  still pending at that checkpoint.

  Targeted implementation re-review: **closed**. `SourcePhase` owns a private
  ordered, phase-local pending map only for the established `assembly` label;
  replacement moves a canonical path to last-occurrence order, and the frozen
  dataclass captures the desired text plus complete currency values before the
  node can mutate. Clean exit performs pre-flush check, finite flush, and
  post-flush check while the Builder is still under F04. Every exit clears the
  map; body/pre-flush failure publishes nothing, a flush failure cannot attempt
  later queued paths, completed paths retain ordinary atomic currency proof,
  and a post-flush `SourceChanged` reaches the Builder's existing assembly-exit
  handler before any STL or viewer publication. Rigid reuse now maps canonical
  path to current full identity and invalidates incomplete identities, while
  flexible, non-assembly, and direct generation remain immediate. Logging and
  currentness update happen only at successful flush/publication, never on
  enqueue or discard.

  The focused tests cover distinct binding-dependent compositions and
  historical last-wins disk content, immutable capture, cross-path order,
  second/third-build inode/mtime/ctime stability, immediate bypasses,
  body/pre/post and partial-flush failures, no discarded log, A→B→A, and
  A→unknown→A. My independent run of the 24 generation-dedup cases plus the
  three exact Builder/source-race cases passed 27/27 in 1.46 seconds. Frozen
  source/test hashes independently match `ar07.md`; its finite disposable
  record contains nine successful workers, empty churn on both transitions for
  all three projects, equal complete STL maps/manifests and copied input maps,
  and an unchanged original catalogue. The compositional post-flush proof is
  adequate: the unit produces `SourceChanged` after a real atomic publication,
  and the Builder phase-exit regression asserts SOURCE_CHANGED with no viewer
  or STL pass. No duplicate whole-Builder race test is required. AR-07 itself
  is closed; the later frozen-candidate suite and replacement seven-section
  evidence also passed.

## AR-08 -- direct fixture probes cannot import their disposable project

- Severity: medium (formal measurement completeness; harness only)
- Affected path: `workflow/due-dilligence-performance/remediation/run_current_performance_probe.py:69-86`;
  preserved evidence is `current-candidate-v3-algorithms.json`.
- Violation: `invoke()` launches an absolute worker-script path from a
  disposable project working directory but replaces `PYTHONPATH` with the
  framework repository alone. Python therefore puts the remediation script
  directory, then the repository, but not the subprocess working directory on
  `sys.path`. Direct fixture imports cannot resolve even though the fixture is
  the declared workload input, so the formal seven-section capture cannot
  reach its algorithm and memory gates.
- Reproducible evidence: all three fresh algorithm workers were attributed to
  frozen candidate `b8b16185…a4b0` and exited 1 at
  `current_performance_worker.py:582`, `from bench.solid import Driven`, with
  `ModuleNotFoundError: No module named 'bench'`. The runner preserved the raw
  failed record and stopped; candidate identity remained unchanged. Startup,
  build, batch, projects, and empirical had completed before this harness
  failure, but memory did not run. This is not a framework algorithm failure.
- Required correction: give each worker the exact verified effective import
  path `REPO + os.pathsep + resolved cwd`, retaining the candidate repository
  first and replacing rather than inheriting ambient `PYTHONPATH`. Record that
  effective value and add a real subprocess regression whose module exists
  only in the disposable working directory while framework imports still
  resolve to the candidate. Review both direct fixture seams: algorithms and
  the 4,000-tick memory trajectory import `bench.solid`; the external WP8/WP9
  probes already run with repository cwd and need no project path. Preserve the
  failed v3 identity/raw files, compute a new candidate identity after the
  harness edit, and run all seven sections under a new label. No retry or
  verifier weakening is warranted.
- Re-review: **closed**. `verified_worker_cwd()` resolves the directory
  strictly and rejects the framework checkout and the original project
  catalogue (including descendants). `invoke()` replaces ambient
  `PYTHONPATH` with exactly resolved candidate repository first and resolved
  disposable cwd second, and records both the joined value and its entries on
  success, timeout, and malformed/no-marker outcomes. The real subprocess
  regression imports a cwd-only module through an absolute worker script and
  proves `solid_node.__file__` resolves to this candidate checkout; a second
  test proves the source-scope refusals. The two changed hashes independently
  match the owner handoff (runner `4f0859c7…c3fc`, tests
  `84262458…d295`), and my independent full lightweight run passed 21/21 in
  0.341 seconds. Read-only identity recomputation yielded
  `d3615253…1250` with 375 entries, differing from v3 only in those two
  harness files. All seven replacement-label sections subsequently verified
  under that one identity.

## AR-09 -- suspected AR-08 project-precedence regression, disproved

- Severity: not a confirmed defect (closed diagnostic hypothesis; formal
  evidence qualification)
- Affected records: `current-candidate-v3-projects.json`,
  `current-candidate-v4-projects.json`, and the original Metamaquina2
  `_build/viewer.json` retained outside the framework checkout.
- Initial concern: production and framework-test bytes are identical between
  v3 and v4, but all three v2/v3 Metamaquina2 samples emit viewer manifest
  `d1ba8ddf...c338` (173,799 bytes), equal to the immutable planning baseline,
  while all three v4 samples emit `f9f904f8...8919` (173,857 bytes). AR-08 also
  pre-populates the disposable project directory behind the candidate in
  `PYTHONPATH`, while `_seed_project_path()` inserts at index zero only when
  the root is absent. That difference warranted investigation, but it did not
  establish that import precedence caused this output change.
- Disproof: fresh processes loaded independently proven legacy-4bc and current
  framework modules yet both emitted `f9f904f8...8919`; current builds under
  both the former framework-only environment and the AR-08 environment also
  emitted that same document. The fixed project set supplied no project-module
  collision or differing import result. The source/test change therefore did
  not reproduce as the cause, and a speculative harness or loader correction
  would be outside this review's evidence.
- Exact cause and independent reproduction: the original project's preserved
  173,776-byte `70c4f516...8c08` version-3 viewer document retains the prior
  serialized node timestamps. Starting with the current 173,857-byte
  `f9f904f8...8919` document and replacing **only** recursive `mtime` values in
  its `root` tree from that preserved tree visits 576 timestamp fields, changes
  226, and serializes with the framework's default `json.dump` formatting to
  exactly 173,799 bytes and SHA-256 `d1ba8ddf...c338`. I reproduced those exact
  count, size, and digest results independently in memory. Current selected
  input bytes, project HEAD, and status equal the planning snapshot, while the
  same files' filesystem mtimes were externally refreshed; all 105 current STL
  filenames/hashes and all aggregate piece fields remain equal. Thus the
  baseline/current digest difference is timestamp metadata, not naming,
  geometry, piece identity, source selection, or AR-08 precedence.
- Disposition: **closed without code or harness change**. The v4 record may
  stand, but the final human report and disposition must state that the
  manifest is metadata-sensitive and not byte-equal to the baseline, explain
  the exact timestamp-only reconstruction, and must not generalize the saved
  baseline digest into a complete historical STL map. The logical
  `_seed_project_path()` ordering seam was not exercised by this fixed
  catalogue and remains a non-finding, not grounds to alter the ratified
  implementation or measured candidate.

## Final candidate and evidence decision

- Frozen correctness: the final production and framework-test candidate passed
  1,773 tests and 353 subtests, with 16 skips and 49 warnings, in 277.69
  seconds. Its JUnit contains 2,142 cases and zero failures/errors. The final
  measured identity differs from that frozen record only in the AR-08 runner
  and harness-test files; those passed targeted independent review (21 tests)
  and the separately labelled 14-worker algorithms/memory smoke before the
  formal capture.
- Formal measurement: my final read-only invocation of
  `verify_current_performance_evidence.py --label current-candidate-v4
  --require-current-candidate --require-inventory` verified 141 successful
  nested workers across all seven sections at identity `d3615253...1250`.
  Candidate equality, the eight-file generated-evidence inventory, original
  catalogue provenance, structural/equivalence gates, and immutable historical
  and planning-baseline inventories all passed. I separately reran both SHA-256
  inventories successfully and `git diff --check` is clean.
- Human claims: `current-candidate-v4.md`, `DISPOSITION.md`, and
  `validation.md` accurately separate structural results from shared-host
  timing/RSS observations; retain exact/faceted policy and trajectory history;
  report regressions and skips; and do not substitute incomplete captures or
  claim a missing historical filename/hash map. Their build, project,
  algorithm, cache, sparse-matrix and provenance headline values match the raw
  records I checked.
- MM2 qualification: I independently reproduced the exact timestamp-only
  reconstruction recorded under AR-09 and verified identical v3/v4 complete
  105-file STL maps. The three post-capture diagnostic files are durably named
  and hashed in the final report (`92b70b92...c0c4df`,
  `6c96e4b4...73488`, and `db38174f...61342`); no formal raw record was
  altered. The final documents correctly state that literal manifest hashes
  differ and that baseline metadata/full-map blind spots remain.
- Limitations: the 16 skips, absent real JSCAD executable/live web capture,
  entry rather than native-byte cache bounds, dense-overlap fallback, shared-
  host timing/RSS, and metadata-sensitive project provenance are explicit.
  None is concealed as green coverage.

**Overall decision: green.** All accepted implementation, test-isolation and
measurement-harness findings are corrected and independently re-reviewed;
AR-09 is closed as a disproved diagnostic hypothesis with an exact metadata
explanation. No unresolved correctness, compatibility, performance-contract,
provenance or evidence finding blocks the repository's ADR/sync/archive phase.
The later archive/commit/post-archive checks remain separate workflow gates,
not evidence already completed by this decision.
