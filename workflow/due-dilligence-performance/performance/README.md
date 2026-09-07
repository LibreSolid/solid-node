# Performance evidence and reproduction

Start with [the report](../PERFORMANCE.md). These files support the 2026-09-07
audit; they are observations, not a performance guarantee or accepted design.

## Identity and environment

- Shop root: /home/asa/devel/libresolid-studio.
- Owning repository: /home/asa/devel/libresolid-studio/solid-node.
- Bench: solid-node/WTs/performance-analysis, branch performance-analysis.
- Recorded base / audited content: 4bf9b69421b7114809af75fe663441d115407631,
  from framework main. No sprint scope was assumed.
- Interpreter: /home/asa/devel/libresolid-studio/.venv/bin/python,
  Python 3.12.3 on Linux x86-64.
- CPU: AMD Ryzen 9 5900X; affinity exposed CPUs 0–15.
- CadQuery 2.7.0; cadquery-ocp 7.8.1.1.post1; build123d 0.10.0;
  trimesh 4.4.9; manifold3d 3.5.2; molejo 0.2.0; NumPy 2.2.6;
  SciPy 1.18.1; OpenSCAD 2021.01. JSCAD was not installed.

Each JSON repeats the actual environment, timestamp, commit, CPU affinity,
load average and relevant thread environment. The solid-node distribution's
0.6.0 metadata is not the identity of the audited development sources.

The bench was created with the shop's scripts/dev-env performance-analysis setup.
Only the report and its supporting evidence were authored here; framework source,
tests, specs and ADRs were not changed. The audit-only commit records this evidence;
no integration was performed.

## Evidence index

| File | Content / interpretation |
| --- | --- |
| [probe.py](probe.py) | Standalone observation harness; normal framework paths plus explicitly marked in-process counterfactuals |
| [fixtures/](fixtures/) | Small Solid2/CadQuery cubes; repeated children; one driven part |
| [startup.json](startup.json) | Five fresh-process samples per startup/import/CLI operation |
| [build.json](build.json) | Three cold + unchanged pairs per fixture configuration; child process counts and artifact checks |
| [batch.json](batch.json) | Three independent cold 24-cube single-interpreter/normal-CLI pairs; identical STL hash-map checks |
| [projects.json](projects.json) | Copied-project settle, three unchanged CLI builds each, and a separate current-builder cProfile |
| [empirical.json](empirical.json) | Direct phase timers, mesh counts, unchanged-file churn, source closures, real bounds and V8 springs |
| [empirical-initial.json](empirical-initial.json) | Retained initial probe errors for abacus/V8; **excluded** from report timings |
| [algorithms.json](algorithms.json) | Direct framework broad-phase scaling, wide-tree linking/simulation, rigid-pair memo reuse |
| [memory.json](memory.json) | Exact placed-shape cache size and Linux process RSS over 4,000 distinct translations |
| [project-inputs.patch](project-inputs.patch) | Informational pre-existing abacus/V8 working diffs, separated by project labels |
| [validation.xml](validation.xml) | Full framework pytest JUnit results |
| [verify_evidence.py](verify_evidence.py) | Checks worker success, provenance, equality checks and suite results without rerunning CAD |

Raw process output and profile text are retained in JSON with bounded stdout/stderr
tails. File paths naming temporary snapshots no longer exist: the harness removes
only its own temporary directories when each section finishes.

## Project provenance and protection

The selected inputs were:

| Catalogue-relative repository | Observed commit | Observed working state |
| --- | --- | --- |
| Vibecoded-demos/abacus | 98dc357c4e14a56637884949564952df246b3829 | Modified abacus/abacus.py; untracked screenshot |
| Vibecoded-demos/v8-engine | 3740f6a8cd3efc03fa5dfb854ff0728177bf5dc1 | Modified root.py; existing untracked local files |
| 3D-Printers/Metamaquina2 | a81f86267329754243b292a8ce83ca6ff8e8d438 | Clean |

The JSON carries exact Git status before/after and SHA-256 of copied Python,
TOML, SCAD, JS, STEP/STP and non-build STL inputs. Abacus's existing column count
was seven rather than nine. V8's existing root change imported Length from
parameters and set handle_throw to 40 rather than 35. The saved patch records
those differences; it is informational evidence across separate repositories,
not a single patch to apply to the framework.

The harness checks each selected input is its own Git repository. It uses real
copies, not hardlinks, preserves timestamps, omits .git/.env/.venv/cache directories
and node_modules, and rejects symlinks escaping the copied project. Existing
build artifacts are copied and settled first. All builds, assemblies, geometry
experiments, restamping and publication then occur in the disposable copy.
No project test suite or mechanical design was modified. Original Git statuses
matched before and after both project measurement sections.

A later rerun uses the then-current working snapshots. Compare its source hashes
and statuses before calling it an identical-input reproduction.

## Reproduce

Use the existing workspace environment and run from inside the bench so the
worktree environment is selected. Commands below intentionally regenerate their
named JSON evidence files; preserve the original evidence separately if comparing
a proposed optimization.

```bash
cd /home/asa/devel/libresolid-studio/solid-node/WTs/performance-analysis
export PYTHONPATH="$PWD"
export PYTHONDONTWRITEBYTECODE=1

for section in startup build batch algorithms memory; do
  /home/asa/devel/libresolid-studio/.venv/bin/python \
    workflow/due-dilligence-performance/performance/probe.py --section "$section"
done

for section in projects empirical; do
  /home/asa/devel/libresolid-studio/.venv/bin/python \
    workflow/due-dilligence-performance/performance/probe.py --section "$section" \
    --catalogue /home/asa/devel/libresolid-studio/projects
done

/home/asa/devel/libresolid-studio/.venv/bin/python -m pytest -q \
  --durations=25 --junitxml=workflow/due-dilligence-performance/performance/validation.xml

/home/asa/devel/libresolid-studio/.venv/bin/python \
  workflow/due-dilligence-performance/performance/verify_evidence.py
```

The full measurement run takes several minutes. Project sections assume the three
named repositories and their required CAD dependencies/assets are present.
Do not install a different framework version into the environment when comparing
the recorded base. Retain the framework bench on PYTHONPATH.

The observation harness's exit code indicates that it saved observations, not
that every nested experiment passed; inspect nested status/error fields or run
verify_evidence.py. Worker timeouts terminate only that worker's own process
group. The batch worker intentionally supports only stable-source RENDERED and
CURRENT outcomes; unexpected outcomes fail the experiment, not silently retry.

## Method and interpretation

- Sections ran sequentially; no audit subprocess was deliberately benchmarked
  against another audit workload. The host was shared and its OS caches were not
  flushed. No CPU pinning, governor control or system-wide process termination
  was attempted.
- “Cold fixture” means an empty build output tree and a fresh interpreter, not
  cold filesystem caches. “Unchanged project” means the copied project has
  settled artifacts and each timed CLI call uses a new process.
- Fresh-process startup numbers include Python and probe imports. Five samples
  are retained; the empty control median was 87.7 ms. Do not subtract it as an
  exact constant from other results.
- CLI build numbers are outer wall time. Phase numbers use perf_counter inside
  a worker. cProfile runs are separate because profiler overhead changes timing;
  nested cumulative entries overlap and must not be summed.
- RSS values are KiB. peak_self_rss_kib and peak_child_rss_kib are resource
  high-water marks, **not summed simultaneous resident memory**. The placement
  experiment instead reads current VmRSS from /proc/self/status.
- Phase probes import framework/test helpers before load_node timing. Their
  subphase totals therefore do not reconstruct the full CLI elapsed time.
- Snapshot reuse is a single stable-artifact experiment per project. It clears
  mesh/fingerprint caches, reuses published facts, falls back for uncovered
  artifacts and verifies byte-identical publication. A production identity and
  invalidation scheme remains to be designed.
- Source census lookup excludes the one-time construction of that census.
  The optimization is not proposed as a persistent mtime-blind cache.
- Broad-phase real-project samples bind numeric keyframe zero, compare candidate
  sets for each axis and time only candidate generation. Initial abacus/V8 probes
  tried to convert symbolic placements to floats before binding a keyframe.
  That harness error was corrected and the entire empirical section rerun;
  empirical-initial.json remains untouched for transparency.
- Flexible measurements use the first V8 spring/valve pair at four instants,
  not every pair over an animation. The interleaved-cache comparison checks 80
  returned volumes for equality, not mesh-byte equality.
- The batch comparison checks equality of the complete STL filename→SHA-256 maps
  for 24 unique artifacts. It does not certify source reloads, errors, locking,
  or exact-backend thread safety.

## Framework validation

Command: the pytest invocation above, on the unchanged audited framework content.

Result: **1,527 passed, 16 skipped, 38 warnings, 258 subtests passed in 181.40 s**.
JUnit counts 1,801 test cases (including subtests), zero failures and zero errors.
The 16 skips comprise 13 Sphinx-not-installed cases, two missing
Internal-Cycloidal-Actuator vendor STEP cases, and one opt-in web snapshot test
requiring SOLID_NODE_WEB_SNAPSHOT_E2E=1. No live browser capture was run.

Warnings were reported rather than suppressed; the suite's green result does not
disprove the measured overhead or the earlier correctness audit's findings.

Saved-evidence verification also passed: 104 successful workers across seven
sections; fixture/output equivalence, original project status, candidate-set and
flexible-volume checks all passed. Report links resolve and every audit Python
file compiles. The retained initial failed empirical run is explicitly excluded.
