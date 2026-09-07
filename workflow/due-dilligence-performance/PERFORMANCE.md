# Performance due diligence — solid-node

Date: 2026-09-07. Framework content: **4bf9b69421b7114809af75fe663441d115407631**.
Branch/worktree: performance-analysis, opened from framework main through the shop's
development-bench workflow. This is a diagnostic report, not a ratified optimization
design. Framework implementation, baseline specs, and project sources are unchanged.

**Relocation note:** this report was rebased onto later `main` only to preserve the
audit record. Measurements, conclusions, and source-line references describe the
audited commit above; they were not remeasured or revalidated against the rebased
sources.

## Verdict

**No: there is substantial avoidable overhead, particularly in build orchestration,
unchanged-build publication, and repeated flexible geometry.** The framework already
has useful lazy imports, artifact caching, geometry deduplication, broad-phase
filtering, and rigid-pair memoization. The opportunity is to remove repeated work
without weakening source currency, geometry precision, or build isolation.

The strongest evidence is not a hypothetical faster kernel:

- Unchanged builds of three existing projects still took **5.85–11.40 seconds**
  (project medians), while preserving the published manifest.
- A cold 24-part Solid2 fixture started **25 builder processes**. A disposable
  single-fresh-interpreter experiment reduced its paired median from **22.56 s to
  1.96 s**, with all 24 STL hashes identical in all three pairs.
- Publishing an unchanged V8 or Metamaquina2 manifest decoded hundreds of thousands
  of triangles again in each fresh process. Reusing already-published geometry
  facts reduced that measured phase from about **1.40 s to 0.058/0.184 s**.
- The real V8's 16 springs had three distinct bindings at the sampled instant.
  Eighty interleaved reads built geometry **35 times**; request-local reuse built
  it **three times**, with identical returned volumes.

These are measured opportunities, **not delivered speedups or whole-project
guarantees**. In particular, changing the builder lifecycle conflicts with an
explicit, correctness-motivated decision and needs design review.

## Scope and empirical baseline

The project catalogue supplied the primary use cases: a repeated-parts abacus, a
mixed rigid/flexible V8 engine, and a much larger 3D printer assembly. Every project
execution used a disposable independent copy, including its existing build
artifacts, never the original project directory.

| Project | Tree nodes | Selected rigid instances / artifact paths | Unchanged CLI build, median (range), 3 runs | First snapshot pass in a fresh process |
| --- | ---: | ---: | ---: | ---: |
| Vibecoded-demos/abacus | 65 | 56 / 5 | 5.85 s (5.85–5.88) | 0.043 s |
| Vibecoded-demos/v8-engine | 170 | 119 / 24 | 7.49 s (7.39–7.52) | 1.396 s |
| 3D-Printers/Metamaquina2 | 576 | 443 / 100 | 11.40 s (11.22–11.56) | 1.398 s |

The manifest's bytes and mtime remained unchanged across each project's three
CLI runs. There was still one fresh builder child on every run. The printer's
100 selected artifact paths are not its total directory count (105 STLs), nor
its 99 deduplicated printed-piece identities.

Abacus and V8 were already dirty; the printer was clean. Their observed commits,
Git statuses, copied-source hashes and relevant pre-existing diffs are preserved
in the evidence. Before/after project Git statuses matched. This is evidence for
those working snapshots, not just their nominal commits.

Results come from one Linux host (Ryzen 9 5900X, 16 CPUs exposed, Python 3.12.3),
using the workspace environment: CadQuery 2.7.0, OCP 7.8.1.1.post1, trimesh 4.4.9,
manifold3d 3.5.2 and molejo 0.2.0. Package metadata says solid-node 0.6.0;
the audited implementation is the development commit above, not the PyPI release.
Full versions, load averages, timing samples and profiles are in
[the evidence and reproduction guide](performance/README.md).

## Findings

### P01 — Process-per-artifact rebuilding dominates cheap Solid2 builds

**Priority: high. Confidence: high for the measured workload.**

[Build.build()](../../solid_node/manager/build.py#L96) resolves/imports the model in
the parent, then starts a fresh interpreter for each builder outcome. A rendered
artifact causes another iteration; the final current check requires another
process. [Builder._start()](../../solid_node/core/builder.py#L270) reloads and
assembles before returning that outcome.

The same fixture, with distinct small cubes, produced:

| Backend / distinct parts | Cold CLI median, 3 runs | Builder children per cold run | Unchanged CLI median |
| --- | ---: | ---: | ---: |
| Solid2 / 1 | 2.19 s | 2 | 1.23 s |
| Solid2 / 8 | 8.83 s | 9 | 1.26 s |
| Solid2 / 24 | 24.04 s | 25 | 1.24 s |
| CadQuery / 1 | 5.79 s | 1 | 5.94 s |
| CadQuery / 8 | 5.88 s | 1 | 5.79 s |

This is **not** evidence that CadQuery generally renders faster than OpenSCAD.
These are deliberately cheap solids. Exact leaves materialize during assembly;
the fixture therefore exposes different orchestration paths. The nearly equal
cold/warm exact timings also expose a substantial import floor.

A separate paired experiment repeated Builder._start() inside one freshly launched
interpreter until CURRENT, retaining imports and class caches. Across three cold
24-cube pairs, normal CLI median was 22.56 s and the experiment 1.96 s (**11.5×**).
Every pair produced 24 byte-identical STLs. Both sides started with empty output
directories. The experiment also bypasses the normal parent-side model resolution;
it does not isolate process creation from retained imports and model state.

**Direction to investigate:** keep fresh-process isolation, but amortize startup
over a stable source generation; alternatively investigate eliminating redundant
parent-side model evaluation while retaining its error classification. Do not
switch back to unsafe fork or add unbounded parallel workers.

**Constraint:** [ADR-067](../../docs/adrs/BUILD/ADR-067-fresh-interpreter-build-subprocesses.md)
explicitly makes process-per-iteration load-bearing, because process death clears
module state and inherited OCCT thread pools previously deadlocked. The experiment
does not prove reload freshness, fusion ordering, recovery after failure, lock
contention, or watcher behavior. Changing that boundary requires a ratified design
and those regressions, not promotion of the probe into production.

### P02 — Unchanged publication recomputes mesh facts before discovering no change

**Priority: high. Confidence: high, reproduced in real projects.**

[Builder._write_viewer_snapshot()](../../solid_node/core/builder.py#L414) rebuilds the
piece inventory before comparing the new document to the published bytes.
[Piece geometry facts](../../solid_node/core/pieces.py#L58) decode meshes to derive
size, volume and watertightness. Process-local caches help repeated calls inside
one interpreter, but the CLI starts another interpreter next time.

| Project | Meshes / triangles decoded | First snapshot pass | Warm in-process median | Reuse published facts, fresh mesh/fingerprint caches |
| --- | ---: | ---: | ---: | ---: |
| Abacus | 5 / 14,180 | 43 ms | 10 ms | 11 ms |
| V8 | 24 / 749,594 | 1,396 ms | 23 ms | 58 ms |
| Metamaquina2 | 100 / 715,984 | 1,398 ms | 157 ms | 184 ms |

The isolated reuse experiment ran after currency checks, supplied facts from the
same published artifacts, and preserved the complete manifest byte-for-byte.
It was one timed pass per project, not a full-build before/after optimization.
The raw profiles independently locate this work in piece registration and mesh
loading.

**Direction:** reuse verified per-artifact facts across builder processes, or make
a demonstrably-current publication path avoid their reconstruction. Still check
new model metadata, placements, hierarchy, source/artifact changes, and publication
completeness. The probe's path/mtime lookup is an experimental shortcut under
stable inputs, **not a sufficient production cache identity**.

### P03 — The unchanged path still rewrites SCAD and repeatedly visits source closures

**Priority: medium. Confidence: high, real-project counts and timings.**

[generate_scad()](../../solid_node/node/base.py#L802) writes SCAD while assembling,
including repeated instances of the same artifact. It also regenerates source
digest sidecars. In one unchanged assembly:

| Project | SCAD write calls | Distinct SCAD / source sidecars changed on disk | Total source-closure entries / distinct files |
| --- | ---: | ---: | ---: |
| Abacus | 9 | 3 / 3 | 159 / 11 |
| V8 | 51 | 14 / 14 | 565 / 40 |
| Metamaquina2 | 133 | 59 / 59 | 40,199 / 210 |

Every changed SCAD and sidecar retained identical bytes. File replacement/restamping
was checked using inode/ctime and content hashes, not guessed from high-level
manifest stability. The printer's assembly took 727 ms unprofiled. A separate
profile counted 216,470 stat calls over the current builder run; this includes
imports and other operations, so not all are attributable to source currency.

Reading [mtime_ns](../../solid_node/node/base.py#L722) for every printer node took
84.9 ms. Looking up the same values in an already-built, snapshot-local census took
2.29 ms. Census construction is excluded from the latter timer; this is not a
measured end-to-end 37× build improvement.

**Direction:** deduplicate generation by valid artifact identity within a stable
assembly, avoid replacing unchanged text, and share source metadata/digests only
within a well-defined source snapshot. The framework already indexes package
lookup ([ADR-058](../../docs/adrs/NODE/ADR-058-indexed-package-lookup-for-source-closures.md));
the remaining duplication is downstream, not evidence that that work failed.

**Constraint:** the existing correctness audit's [F04/F05](../archive/due-dilligence-2026-09-07/README.md#f04--exact-geometry-bypasses-build-mutual-exclusion)
identify build-lock ordering and aggregate-mtime currency problems. Do not make a
stale result faster or cache away change detection. Recheck these paths as part
of any build optimization.

### P04 — The flexible manifold cache thrashes between concurrently useful bindings

**Priority: high for animated flexible assemblies. Confidence: high for the V8 sample.**

[_flexible_manifold()](../../solid_node/test.py#L302) keys on node identity and
binding, but a miss deletes every other binding for that identity. Identical
spring definitions at different current compressions therefore evict one another,
even within a single assembly instant.

At V8 time 0.1, sixteen ValveSpring instances had **three distinct keys**. Five
walks through them (80 reads) caused **35** manifold constructions and took
**359 ms**. A request-local dictionary retaining the three keys caused **three**
constructions and took **32.5 ms**. All 80 resulting volumes matched.

**Direction:** retain a bounded working set of geometry per source generation and
binding, or scope multi-binding reuse to a comparison/instant. Include geometry
definition/source identity and disposal semantics. This is geometry reuse, not
memoization of flexible intersection verdicts.

This does not establish an 11× improvement in the whole V8 test suite: geometry
reads were isolated and expensive boolean comparisons were not part of this loop.

### P05 — The broad phase has an orientation-dependent quadratic cliff

**Priority: medium, scaling risk. Confidence: high on synthetic inputs; real-project context measured.**

[_bounds_candidates()](../../solid_node/test.py#L380) sweeps X and keeps every box
whose X interval remains active. When all X ranges overlap but the boxes are
separated along Y or Z, it still tests essentially every pair.

For 1,024 disjoint unit boxes spaced along X, candidate generation took **0.413 ms**.
The same boxes spaced along Y took **1.196 s**, and Z **1.171 s**, returning zero
candidates in all cases. Y time progressed from 17.6 ms at 128 boxes to 69.5 ms,
282 ms and 1,196 ms as the population doubled: the expected quadratic signature.

This is **not currently the leading cost in the sampled projects**. At keyframe
zero, X was the fastest axis for all three: abacus 1.04 ms, V8 4.98 ms, printer
31.3 ms; their Z sweeps were 5.12/11.6/56.6 ms. Candidate sets matched across axes.

**Direction:** consider an adaptive sweep axis or a spatial index if large,
unfavorably oriented assemblies matter. Validate touching/degenerate bounds,
rotations, candidate completeness and diagnostic ordering. Real geometry must
still reach the narrow phase; broad-phase rejection must remain conservative.

### P06 — Automatic child naming makes wide-list simulation unnecessarily expensive

**Priority: medium. Confidence: high for a synthetic wide assembly.**

[_link_child() / _attr_name_for()](../../solid_node/node/base.py#L892) rediscover a
child's attribute/list position by scanning public attributes and list contents.
Repeating this for every child yields quadratic work for broad lists, including
the simulation path.

A real framework Assembly with one driven part and otherwise shared lightweight
leaves was stepped for 20 ticks. At 2,048 children, auto-derived names took
**1.149 s**, versus **0.0240 s** with explicit, equivalent names. Linking all children
alone took 73.0 ms versus 0.179 ms. At 128/512 children the 20-tick automatic path
took 21.4/115.8 ms, versus 1.63/6.22 ms with names supplied.

Geometry construction is excluded; this demonstrates framework tree bookkeeping,
not CAD kernel performance. The catalogue's sampled roots do not establish that
everyday assemblies reach this width.

**Direction:** index child ownership/names once per stable structure, or stop
relinking unchanged children on every traversal. Preserve first-attribute naming,
aliases, list positions, parent updates, and legacy mutable model behavior.
Do not change the public naming contract to gain speed.

### P07 — Exact placement caching retains an unbounded number of transforms

**Priority: medium for long-running exact animation/tests. Confidence: high for retention; workload impact unbounded but not fully characterized.**

[exact._placement_cache](../../solid_node/exact.py#L41) retains placed shapes keyed
by source and transform. Source replacement evicts related entries; there is no
size bound or normal end-of-run clearing in this path.

Applying 4,000 distinct translations to one cached box BREP left **4,000 cache
entries**. Process RSS grew from 498,940 to 539,080 KiB, about **39.2 MiB net**.
This is retained live cache memory, not proof of unreachable-object leakage.
Allocator behavior, baseline imports and shape complexity prevent extrapolating a
reliable bytes-per-transform law from one box.

**Direction:** investigate session-scoped lifecycle or bounded placement reuse.
Contrast the rigid verdict cache, which already has an 8,192-entry limit.
Reconcile eviction with existing [exact-geometry cache contracts](../../openspec/specs/exact-geometry/spec.md)
before promising each shape/placement is computed only once per run. Verify both
memory plateau and useful cache-hit performance over a long changing trajectory.

## Additional tradeoffs and risks

### Flexible exact checks are costly, but precision is a user choice

One real V8 spring/valve pair was evaluated at four instants with both existing
comparison policies. First exact calls took **0.40–0.51 s** per instant; exact
three-call medians were **0.38–0.45 s**. First faceted calls took **14–24 ms**;
warm three-call medians were **1.7–2.2 ms**. Both policies reported an empty
intersection with zero volume at these sampled instants.

The current framework already exposes the faceted policy. This is not a missing
optimization to implement, nor proof that both kernels agree near every contact.
[ADR-073](../../docs/adrs/TEST-FRAMEWORK/ADR-073-the-comparison-kernel-is-a-property-of-the-test-run.md)
makes the kernel an explicit test-run choice. Keep tolerance and precision
decisions explicit; do not silently switch exact assertions to faceted results.
The full V8 animation/assertion suite was not rerun, and older timing claims in
[the historical performance note](../../docs/performance-improvement.md) are not current
benchmarks.

### Static-equilibrium matrix construction has a separate memory scaling risk

Source inspection of [_unbalanced_bodies()](../../solid_node/test.py#L930) found
dense equilibrium matrices and two dense identity slack blocks. For F free bodies,
those two blocks in the final concatenated float64 matrix alone occupy
576 × F² bytes: **576 MB at 1,000 free bodies**, before contacts, temporary arrays
and solver memory. This is an allocation-size derivation, not a measured
out-of-memory failure.

A sparse formulation deserves a representative statics benchmark and solver
equivalence tests. It was not modified or performance-tested in this audit.
Likewise, Sim intentionally retains a trajectory proportional to ticks × drivers;
that documented behavior should not be labelled a leak.

## What is already efficient

- Cheap CLI discovery stays cheap. Five-process medians: viewer report 116 ms,
  model discovery 265 ms, build help 281 ms. None imported CadQuery/OCP. The
  harness's empty-Python baseline was 88 ms, so these are inclusive process
  timings, not pure import times.
- Importing Solid2Node took 201 ms without CadQuery. Importing CadQueryNode took
  2.91 s and reached roughly 485 MiB peak self RSS. This supports preserving
  lazy backend boundaries rather than optimizing lightweight parser code first.
- Unchanged STLs and the viewer manifest are reused. The defects above concern
  the work performed to establish/reconstruct that result, not universal CAD
  rerendering.
- Repeated rigid shapes share cached meshes/manifolds, and relative-placement
  memoization works: one 1,280-triangle rigid-pair comparison took 9.38 ms;
  1,000 subsequent memo hits took 34.8 ms in total, with the same verdict.
- Binary STL and available kernel parallelism are already in use. CadQuery's
  exportStl defaults include binary output and parallel meshing, confirmed
  against the installed 2.7.0 implementation and
  [official API documentation](https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.Shape.exportStl).
  OpenSCAD output is explicitly binary, and exact booleans already request
  parallel execution. “Turn on binary STL/parallel export” is not a new finding.

## Recommended sequence and proof gates

These are follow-up candidates, not accepted requirements or implementation tasks.

1. **Preserve/fix currency and locking first.** Couple any unchanged-build work to
   the existing correctness findings; retain failure outcomes, source invalidation
   and atomic publication.
2. **Target repeated work with narrow scope:** verified geometry-fact reuse (P02),
   generation/write deduplication (P03), and bounded multi-binding geometry reuse
   (P04). Reproduce the three catalogue projects before and after, including
   changed source, changed geometry and changed metadata.
3. **Design-review builder amortization (P01).** This has the largest demonstrated
   end-to-end leverage but changes a deliberate isolation boundary. Require cold
   OCCT builds after parent-side imports, live source edits, failure recovery,
   multiple models, fusion ordering and lock contention to remain correct.
4. **Harden scaling:** broad-phase orientation (P05), child naming (P06), placement
   memory (P07), then sparse statics if representative projects justify it.

Retain output hashes/semantic verdicts alongside performance results, use multiple
samples and process RSS, and add non-timing structural regressions for unnecessary
processes, mesh decoding, writes, cache churn and unbounded growth. Numeric CI
budgets need a controlled runner and an agreed workload; these shared-host
measurements are not suitable as hard wall-clock thresholds.

## Validation and limitations

The unchanged framework suite completed: **1,527 passed, 16 skipped, 38 warnings,
258 subtests passed in 181.40 s**. The JUnit record contains 1,801 cases including
subtests, zero failures and zero errors. Skips were 13 missing-Sphinx cases,
two absent vendor-STEP fixtures, and one opt-in web snapshot case.
[JUnit evidence](performance/validation.xml) and [reproduction instructions](performance/README.md)
are saved alongside every probe.

All final measurement workers succeeded. Output/manifest checks accompany the
counterfactuals; synthetic fixtures exercise framework internals rather than
stand-in algorithms. Initial empirical-probe failures from evaluating symbolic
placements before setting a numeric keyframe are retained separately and excluded
from the timings above.

Limits: three deliberately chosen projects, one shared Linux machine, sequential
samples with warm OS caches, and no isolated-hardware confidence intervals.
Project build timings are **unchanged rebuilds**, not from-scratch printer/V8
geometry builds. Real-project phase probes are mostly single observations.
No browser FPS/GPU profiling, viewer-package internals, JSCAD rendering (not
installed), whole-project animated assertion timing, render-quality sweep,
multi-platform comparison or production concurrency benchmark was performed.
The viewer and molejo remain independent products; this audit measures their
framework-facing use where applicable, not their overall performance.

The report and reproducible evidence are saved in this worktree. No framework
optimization, ADR/spec change, integration, push or release was performed.
The audit-only commit records findings and evidence, not implementation changes.
