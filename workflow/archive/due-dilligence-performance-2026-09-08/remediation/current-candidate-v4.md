# Current performance comparison — complete v4 capture

The audited cost mechanisms are substantially improved, with correctness and
explicit precision policy preserved. This is not a claim of universally
optimal performance: dependency import cost remains, some timings regress,
dense real overlap remains expensive, and entry-bounded caches are not a
universal native-memory bound. See [the complete disposition](DISPOSITION.md)
for each finding's source, red/green proof, current evidence and limits.

## Provenance and method

This report uses **only `current-candidate-v4`** as its final post-change
capture: 141 successful workers across startup, build, batch, projects,
empirical, algorithms and memory. Section environment timestamps span
2026-09-07 22:47:22–22:55:10 UTC; the final memory section took 21.46 seconds.
The measured [candidate identity](current-candidate-v4-candidate-identity.json)
is `d3615253809628a7b9e988354f669da26a0a84ab2ac3855ac8b6cd4d20841250`,
375 selected entries at amended planning HEAD `2ca4b9f06835d1133b6ad00eceecdee6e29b714c`.
The separate [eight-record inventory](current-candidate-v4-evidence-inventory.json)
covers its identity and seven raw sections. Generated outputs are excluded
from the candidate hash to avoid self-reference.

The comparator is the immutable [planning baseline](planning-head-baseline.md)
at its actual original planning HEAD `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c`,
not an intermediate candidate or the earlier historical audit. Production and
framework tests in v4 equal the frozen full-suite candidate; only the AR-08
runner and harness-test correction changed after that suite. Failed/incomplete
captures and the `ar08-smoke` are preserved separately and provide no substitute
timing samples. No v5 was needed: the later MM2 discrepancy proved to be
timestamp metadata, not a source or harness defect.

Host: Linux 6.8, AMD Ryzen 9 5900X, affinity CPUs 0–15, Python 3.12.3;
CadQuery 2.7.0, OCP 7.8.1.1.post1, build123d 0.10.0, trimesh 4.4.9,
manifold3d 3.5.2, molejo 0.2.0, NumPy 2.2.6, SciPy 1.18.1. Installed
solid-node distribution metadata still says 0.6.0; the source identity above,
not that version string, identifies the candidate. OpenSCAD is 2021.01;
the real JSCAD executable is absent. Section-start one-minute load varied
from 2.76 to 4.49; this shared host is not an isolated timing laboratory.
No task-owned CAD test ran concurrently with the formal capture.

Startup rows use each probe's saved `median_s`. Build/project rows below use
the worker's `elapsed_s` on **both** sides, excluding the outer worker-launch
wall time; these therefore differ from older summaries using `wall_s`.
Build configurations and project warm runs each have three fresh-process
samples; algorithm current medians span three workers. Raw records preserve
individual samples, outer times, environment, counters and failures.

## Build and startup results

The dominant P01 improvement is structural: a cold 24-artifact Solid2 build
uses **one builder child instead of 25**, retaining one sealed generation and
assembled tree. Its measured inner elapsed median falls from 29.910 to 1.961
seconds, about 15.3×. Native-state isolation still uses a fresh spawned process;
source changes and failures end that generation.

| Fixture | Baseline cold s | Current cold s | Baseline/current cold children | Baseline first-warm s | Current first-warm s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Solid2, 1 artifact | 2.831583 | 1.420924 | 2 / 1 | 1.414748 | 1.387618 |
| Solid2, 8 artifacts | 10.971447 | 1.471568 | 9 / 1 | 1.311658 | 1.210724 |
| Solid2, 24 artifacts | 29.910191 | 1.961253 | 25 / 1 | 1.368510 | 1.370885 |
| CadQuery, 1 artifact | 5.855497 | 5.976692 | 1 / 1 | 5.944271 | 5.622287 |
| CadQuery, 8 artifacts | 6.121206 | 5.829437 | 1 / 1 | 6.640850 | 5.615784 |

CadQuery already used one child, so its cold timings do not demonstrate the
same process-count gain. The one-artifact cold median is **2.1% slower**;
24-artifact Solid2 first-warm is essentially flat (**0.17% slower**). The
measurement preserves cold and first-warm timings, then uses a third settled
build to assert zero unchanged-write churn: cold inline root SCAD legitimately
settles into cached-child references on the first warm build.
Sources: [baseline build](planning-head-baseline-build.json),
[current build](current-candidate-v4-build.json),
[retained-tree/batch proof](current-candidate-v4-batch.json).

| Startup operation | Baseline s | Current s | Change |
| --- | ---: | ---: | ---: |
| Python control | 0.098646 | 0.092498 | −6.2% |
| CLI import | 0.103828 | 0.106688 | +2.8% |
| Parameters import | 0.108171 | 0.094175 | −12.9% |
| Solid2Node import | 0.273802 | 0.200588 | −26.7% |
| CadQueryNode import | 3.793480 | 3.192092 | −15.9% |
| Test framework import | 1.023957 | 1.042278 | +1.8% |
| Viewer command | 0.145225 | 0.124605 | −14.2% |
| Models command | 0.288776 | 0.257632 | −10.8% |
| Build help | 0.286425 | 0.265083 | −7.5% |

Positive percentages are regressions, not discarded samples. Import results
remain sensitive to host load; the roughly three-second CadQuery import is
still a substantial cost. There is no claim that P01 removes CAD imports.
Sources: [baseline startup](planning-head-baseline-startup.json),
[current startup](current-candidate-v4-startup.json).

## Real-project publication, writes and flexible geometry

| Project | Baseline warm s | Current warm s | Reduction |
| --- | ---: | ---: | ---: |
| Abacus | 7.044755 | 5.909321 | 16.1% |
| V8 engine | 11.139725 | 5.884097 | 47.2% |
| Metamaquina2 | 15.999232 | 11.170294 | 30.2% |

These are settled, unchanged warm builds of disposable copies, not cold
reconstruction of every original CAD artifact. Copies exclude `.env` in both
baseline and candidate. Original HEAD/status/selected source-byte maps match;
the timestamp limitation below is explicit. Sources:
[baseline projects](planning-head-baseline-projects.json),
[current projects](current-candidate-v4-projects.json).

The [actual-builder empirical probes](current-candidate-v4-empirical.json)
show the mechanisms behind the observed gains:

- Fresh Abacus/V8/Metamaquina2 publications hit 5/24/100 persistent piece-fact
  records with zero piece payload reads, full hashes or mesh decodes. Names,
  sources, hierarchy, counts, placements and document metadata remain freshly
  serialized; the metadata-refresh fixture verifies this separation.
- Settled unchanged project builds replace no SCAD/currency files: inode,
  mtime and ctime remain unchanged within each measured repeat. Abacus/V8
  state-dependent path churn is eliminated by the re-ratified assembly-phase
  final-value publication, not by an additional unbounded settling loop.
- The 576-node Metamaquina2 tree still has 40,199 closure memberships over
  210 distinct sources. Its 6,563 metadata observations are the total across
  multiple fresh phase boundaries, **not** a directly comparable replacement
  for the closure-membership count. Per-phase/global counter consistency and
  one distinct-path observation per census are separately checked.
- Helper calls are not writes or computations: Metamaquina2 still invokes
  `generate_scad` 133 times and text comparison 63 times, yet produces no
  settled artifact churn. Its root has one assembly computation; repeated
  cached render/assembly method calls must not be labelled repeated user work.
- V8's 80 interleaved reads over three useful flexible bindings construct
  three faceted geometries, compared with the baseline's 35. Current elapsed
  is 0.076607 seconds; this empirical detail is one instrumented workload,
  not a three-sample timing median. High-water is three within the 64-entry
  internal bound. Exact and faceted V8 comparisons are named separately at
  four instants; every flexible comparison still executes its selected Boolean.

## Algorithms and retention

| Workload | Baseline median | Current median | Structural result |
| --- | ---: | ---: | --- |
| 1,024 boxes separated on X | 0.400986 ms | 0.438998 ms | Zero candidates/checks; +9.5% measured overhead |
| Same count, separated on Y | 1,215.033806 ms | 1.769041 ms | Zero full-AABB checks instead of 523,776 |
| Same count, separated on Z | 1,194.536537 ms | 1.610243 ms | Zero full-AABB checks instead of 523,776 |
| 128 automatically named children, 20 ticks | 18.743680 ms | 2.520731 ms | 20 indexes, zero single-child scans |
| 512 children, 20 ticks | 110.403909 ms | 8.871733 ms | 20 indexes, zero single-child scans |
| 2,048 children, 20 ticks | 1,180.307541 ms | 34.401548 ms | Same endpoint names/history; about 34.3× |

Every current real-project bound set matches the legacy X-sweep candidate set
**and order**: Abacus 56 bounds/144 candidates, V8 119/450, Metamaquina2 443/965.
The adaptive sparse buffer is capped at 8,192; dense overlap falls back to the
old streaming order and can still require quadratic comparisons. Naming
mutations made by recursive child code become visible on the next traversal,
as ratified; no persistent name index was added. Sources:
[baseline algorithms](planning-head-baseline-algorithms.json),
[current algorithms](current-candidate-v4-algorithms.json).

The [memory section](current-candidate-v4-memory.json) records three runs of
each retention/construction workload:

- Exact placements retain 512 entries at every 1,000/4,000/8,000-transform
  sample. Each useful-working-set pass makes 12 requests, three constructions
  and nine hits. RSS samples are explicitly qualified by dropping returned
  placements and collecting garbage. Run 1 records 346,456/284,948/280,272 KiB;
  run 2 records 519,784/520,056/520,072; run 3 records
  519,388/519,660/519,680. The entry plateau is the hard result; native allocator
  behavior is not a universal byte bound or an apples-to-apples RSS speedup
  against the earlier differently qualified probe.
- A 1,000-free-body statics construction uses 13,000 nonzeros in a
  6,000 × 13,000 program, 180,004 CSR bytes, 152,000 vector bytes, and about
  2.014 MB traced construction peak. Historical dense coefficient/slack
  allocations would be 48/576 MB, calculated rather than allocated. HiGHS
  workspace is excluded. Sparse and dense reference arrays, feasibility,
  slack classification and ordered diagnostics agree on characterized cases;
  solver, mathematical problem, addition order and tolerances are unchanged.
- Intentional `Sim.trajectory` history remains: each 4,000-tick one-driver run
  retains 4,000 entries and 4,000 driver values. It was not capped or labelled
  a cache leak. Exact remains the default comparison policy; faster faceted
  results are not substituted for exact results, and faceted volume epsilon
  remains an explicit choice.

## Exact output equivalence and limits

Current cold/warm/batch full STL maps and unchanged-input manifest bytes are
self-equivalent. The immutable planning baseline saved aggregate STL
count/bytes and manifest digest, **not** the full filename/hash maps; its batch
saved only the old two-map equality verdict. Therefore current self-equivalence
is not misrepresented as a full historical-baseline map comparison. WP2 has a
separate controlled legacy/candidate 24-artifact map proof.

Abacus/V8 available baseline fields match. Metamaquina2's STL/piece aggregates
match (105 STL files, 47,946,420 bytes, 99 pieces, 443 instances), but its raw
manifest hash differs. The [exact diagnostic](mm2-manifest-mtime-diagnostic.md)
proves this is **only 226 of 576 serialized node `mtime` values** after a
same-byte timestamp refresh around 22:34. Substituting only the older timestamp
values yields the precise saved baseline digest
`d1ba8ddfdfc993b1d56f180877a3715a77e0e536dd6817a5e573928df88ec338`
and 173,799 bytes, from current
`f9f904f826eca8fce579fb6cb440f22342609f3ca8215ef9ac8d4d3be2598919`
and 173,857 bytes. No other field changes. Verified legacy/current framework
origins and old/current import-path variants agree under current inputs;
the suspected import-order explanation was disproved, not patched away.

Post-capture diagnostic SHA-256 inventory (these files were produced after the
formal v4 inventory and do not replace any formal capture):

```text
92b70b92d8b84db85e5e665dad25dfb6fc0629a398f48557eab761961ec0c4df  mm2-manifest-mtime-diagnostic.json
6c96e4b4ef3295ac8fc6bee7f33072b12a244ed57d29779add134545c6673488  mm2-manifest-mtime-diagnostic.md
db38174fb100da4bf7458baefbd0d0eb11d54dd763c77ce5ae0ee2ee5d261342  mm2-manifest-mtime-reconstruction.txt
```

The catalogue snapshot checks HEAD/status/selected input bytes, **not source
timestamps or every ignored generated file**. That blind spot is now explicit.
No original catalogue project was built or restamped by this task; provenance
comparison does not claim that no other actor can change filesystem metadata.
No favourable incomplete capture is substituted into the final numbers.

Correctness: 1,773 tests plus 353 subtests pass, with 16 recorded skips;
see [validation](validation.md) for frozen identity, commands, logs and JUnit.
The post-archive full run also passes 1,773 tests and 353 subtests, with 16 skips;
its separate logs and JUnit are recorded there. Missing Sphinx, two absent vendor STEP fixtures, opt-in
live web capture and absent real JSCAD CLI remain limits. Final review and
each correction/re-review are in [adversarial-review.md](adversarial-review.md).
