# Planning-head performance baseline

This is the fresh pre-implementation performance evidence for the ratified
`bound-framework-performance-costs` change.  It measures planning HEAD
`4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on branch
`performance-analysis`.  The committed production and test trees were
`d1481386a91cc1fe5aa40a525c8f1f217fb922ad` (`solid_node/`) and
`7c970429e4479ddc68155f68e3fd5ce8436f3415` (`tests/`); both areas had empty
working-tree status throughout the run.  This is performance evidence, unlike
the separately recorded full-suite correctness baseline.

The historical probe remained byte-for-byte unchanged at SHA-256
`6136114978e5bc9eb0cf5a0276d5b7b33f036a27c3928cb972c077f1bc727542`.
The remediation wrapper measured here is SHA-256
`6a30224c0dabbfb87fa57832d2146cc473e3948fb69d15bc1cc62df006219d16`.
It imports the historical measurement functions but writes seven new labelled
JSON records here.  The old report, probe, fixtures, raw JSON, XML, patch and
verifier were not regenerated.

## Command and environment

Run from the framework worktree:

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 \
  /home/asa/devel/libresolid-studio/.venv/bin/python \
  workflow/due-dilligence-performance/remediation/run_performance_probe.py \
  --all --label planning-head-baseline \
  --catalogue /home/asa/devel/libresolid-studio/projects
```

The seven sections started from 2026-09-07T18:49:37Z through
2026-09-07T19:00:03Z.  Their recorded section wall times total 627.41 seconds.
The host was Linux 6.8.0-139-generic x86-64 on an AMD Ryzen 9 5900X with CPUs
0--15 available.  It used workspace Python 3.12.3, CadQuery 2.7.0,
cadquery-ocp 7.8.1.1.post1, build123d 0.10.0, trimesh 4.4.9, manifold3d 3.5.2,
molejo 0.2.0, NumPy 2.2.6, SciPy 1.18.1 and OpenSCAD 2021.01; JSCAD was absent.
OMP, OpenBLAS and MKL thread-count variables were unset.  Recorded one-minute
load averages ranged from 4.64 to 9.46, so all wall times are shared-host
observations, not CI limits or isolated-hardware comparisons.

## Integrity and outcome

- All 104 actual worker records returned status 0.  There were no worker error
  fields, timeouts or wrapper failures.
- All 15 cold/warm fixture pairs preserved the viewer manifest.  All three
  24-STL batch pairs had identical complete filename-to-SHA-256 maps.
- All six real-project settle/detail workers and all 15 real-project
  settle/warm/profile workers succeeded.  Each project retained the same Git
  status in the historical probe's own before/after fields.
- The wrapper independently recorded each original project's commit, Git
  status and complete relevant input SHA-256 map before and after each of the
  `projects` and `empirical` sections.  Both full snapshots compare equal.  The
  copied-project input maps equal the corresponding original input maps.
- Every unchanged project manifest comparison, published-fact counterfactual
  manifest comparison, real-axis candidate-set comparison and V8 flexible
  volume comparison passed.
- The 18-file historical audit inventory matched before and after every one of
  the seven sections, and a final `sha256sum -c` passed 18/18 entries.
- No framework test suite was run as part of this performance capture.  No
  production or test file was edited by the capture.

The exact original project identities were:

| Project | Commit | Working state | Hashed relevant inputs |
| --- | --- | --- | ---: |
| `Vibecoded-demos/abacus` | `98dc357c4e14a56637884949564952df246b3829` | modified `abacus/abacus.py`; untracked `screenshot.png` | 16 |
| `Vibecoded-demos/v8-engine` | `3740f6a8cd3efc03fa5dfb854ff0728177bf5dc1` | modified `v8_engine/v8_engine.py`; untracked `.env`, `screenshot.png`, `v8_engine/#timing_drive.py#` | 355 |
| `3D-Printers/Metamaquina2` | `a81f86267329754243b292a8ce83ca6ff8e8d438` | clean | 224 |

The relevant input count covers the historical probe's non-build Python, TOML,
SCAD, JavaScript, STEP/STP and STL selection.  The JSON records retain every
relative filename and SHA-256 value; counts alone are not the identity.

## Fresh observations

### Startup and fixture builds

Five-process startup medians included: empty Python 98.6 ms, CLI import 103.8
ms, `Solid2Node` import 273.8 ms, `CadQueryNode` import 3.793 s, test-framework
import 1.024 s, viewer report 145.2 ms, model discovery 288.8 ms and build help
286.4 ms.  The CLI/discovery operations did not import CadQuery/OCP.

| Fixture | Cold median | Cold builder children | Unchanged median | Unchanged children |
| --- | ---: | ---: | ---: | ---: |
| Solid2, 1 artifact | 2.943 s | 2 | 1.542 s | 1 |
| Solid2, 8 artifacts | 11.076 s | 9 | 1.428 s | 1 |
| Solid2, 24 artifacts | 30.042 s | 25 | 1.485 s | 1 |
| CadQuery, 1 artifact | 6.443 s | 1 | 6.534 s | 1 |
| CadQuery, 8 artifacts | 7.576 s | 1 | 7.375 s | 1 |

In the historical single-interpreter counterfactual, the three 24-artifact
pairs took 2.652/2.376/2.370 s versus 35.187/34.209/32.459 s for normal CLI
builds (medians 2.376 s and 34.209 s).  The counterfactual still made 25
retained passes while normal CLI started 25 children, and all 24 STL hashes
matched.  This is an unchanged-baseline experiment, not an implemented P01 fix
and not evidence for reload, failure or locking correctness.

### Current copied projects

| Project | Unchanged CLI samples | Median | Builder children per run | Manifest unchanged |
| --- | --- | ---: | --- | --- |
| abacus | 7.721 / 8.313 / 7.753 s | 7.753 s | 1 / 1 / 1 | yes |
| v8-engine | 12.030 / 12.002 / 8.578 s | 12.002 s | 1 / 1 / 1 | yes |
| Metamaquina2 | 16.769 / 16.297 / 17.203 s | 16.769 s | 1 / 1 / 1 | yes |

The separate detail workers observed:

| Project | Nodes / selected rigid / artifact paths | SCAD calls | Identical SCAD / `.sources` churn | Closure entries / distinct sources | Meshes / triangles decoded | Snapshot cold / published-fact counterfactual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| abacus | 65 / 56 / 5 | 9 | 3 / 3 | 159 / 11 | 5 / 14,180 | 46.1 / 19.6 ms |
| v8-engine | 170 / 119 / 24 | 51 | 14 / 14 | 565 / 40 | 24 / 749,594 | 1.328 / 0.0707 s |
| Metamaquina2 | 576 / 443 / 100 | 133 | 59 / 59 | 40,199 / 210 | 100 / 715,984 | 1.310 / 0.211 s |

“SCAD calls” counts calls to the atomic text writer during unchanged assembly;
the churn columns count distinct same-byte files whose inode/ctime changed.
“Meshes / triangles decoded” is the populated process mesh cache after the
ordinary snapshot phase.  The published-fact path is the historical stable-
artifact counterfactual and is not a production identity scheme.

Reading source mtimes across all nodes took median 0.353 ms / 1.363 ms / 84.788
ms for abacus/V8/Metamaquina2.  Looking up those same observations in the
already-created local census took 0.025 / 0.075 / 3.801 ms.  Census construction
is excluded; this is not an end-to-end speedup claim.  The raw cProfile text is
retained in the project record, including filesystem-call counts, without
summing overlapping cumulative rows.

At V8 time 0.1, 16 springs occupied three useful bindings.  Eighty interleaved
faceted reads took 351.9 ms and admitted 35 Manifolds under the current cache;
the request-local historical counterfactual took 35.4 ms and admitted three.
All returned volumes matched.  Across four sampled instants, exact and faceted
policies were explicitly selected and both reported empty intersections; exact
three-call medians were 0.372--0.447 s and faceted medians 1.73--2.20 ms after
their first-call work remained present in each raw sample list.  This does not
silently substitute faceted policy or cache flexible verdicts.

### Algorithms and retained memory

For 1,024 disjoint boxes, the current X sweep took a 0.401 ms median.  The same
shape oriented so all X intervals stayed active but separation was on Y or Z
took 1.215 s and 1.195 s; all returned zero candidates.  The complete 128, 256,
512 and 1,024 scaling samples are in the algorithm record.

At 2,048 children, automatically derived names took 55.8 ms to link and 1.180 s
for 20 simulation ticks.  Explicit equivalent names took 0.179 ms and 24.4 ms.
The first real rigid intersection took 9.78 ms; a run of 1,000 memoized reads
took a 36.9 ms median and returned the same result.

The exact-placement experiment retained exactly 100, 1,000, 2,000 and 4,000
cache entries after that many distinct translations.  Current RSS rose from
513,732 KiB to 571,324 KiB, a 57,592 KiB observation.  This is retained cache
growth on one shape and allocator state, not a universal bytes-per-placement
law.

## Evidence files and reuse limit

The detailed source/probe/input provenance, raw stdout/stderr tails, environment,
load average, profiles, all samples, process and cache counts, and equality
checks are in `planning-head-baseline-{startup,build,batch,projects,empirical,
algorithms,memory}.json`.

This wrapper is reusable for an unchanged committed tree, but this v1 record
identifies the measured framework by HEAD tree ids plus the clean production/
test status.  A future uncommitted implementation measurement must use a new
wrapper/version that adds a candidate content identity covering uncommitted
source, tests, probe and fixed inputs while excluding generated outputs and its
own identity record.  The v1 CLI also assumes its fixed safe label; it does not
validate an arbitrary label as a single path component.  Neither limitation
invalidates this fixed-label, clean-tree baseline.
