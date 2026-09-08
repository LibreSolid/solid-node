# Combined validation record

## Completion workflow

Final independent implementation/evidence review is **green**; see the final
decision in [adversarial-review.md](adversarial-review.md). The v4 verifier was
rerun immediately before documentation completion: 141 successful workers,
seven sections, candidate identity `d3615253…1250`, all provenance/equivalence
gates passing. The three separate post-capture diagnostic file hashes are
recorded in [the final report](current-candidate-v4.md).

OpenSpec status resolved the local `bound-framework-performance-costs` change
and exactly six delta paths. One successful current specs-instruction lookup
preceded every main-spec write. Its rule requires observable implemented
behavior; stale prompt context about per-increment commits and an embedded web
app does not override the shop's ratified two-commit and independent-viewer
boundaries. The optional archive-instruction lookup is unsupported by this
schema, so no additional archive prompt guidance applies.

All six capabilities were synchronized: seven requirements added and three
modified across build-pipeline, flexible-parts, node-model, printed-pieces,
source-closure-cost and test-framework. A read-only semantic comparison verified
every delta requirement present, every unrelated existing requirement and
Purpose byte-preserved, and no delta-operation header in main specs. The old
exact-placement scenario was intentionally replaced by the ratified
retained-entry scenario; unrelated scenarios are preserved.
`openspec validate --all --strict --no-interactive` passed all **29** active
change/spec items before archive. Final archive/test/commit results follow here
when complete.

ADRs 084 (fresh source-generation worker), 085 (verified persistent piece
facts) and 086 (assembly-phase final SCAD publication) are Accepted, with
amendment links and the architecture synthesis updated. Independent bounded
documentation review corrected worker-versus-lock recovery lifetime, coherent
late imports, stat-versus-digest work, rigid render eligibility, managed-test
reset scope, direct-export lock ownership and the scope of stronger cache keys;
the final re-review is green. No source or test changed during documentation.

The change was archived with all planning artifacts done and all six specs
verified synced, at
`openspec/changes/archive/2026-09-08-bound-framework-performance-costs/`.
Two self-referential workflow tasks (final test/commit and clean-history
verification) remained in progress under the pilot-ratified full completion
authority; their checkboxes close after those operations pass. The archive
preserved `.openspec.yaml`. Post-archive strict validation passed all **28**
remaining baseline-spec items, zero failures.

The final post-archive focused command uses the common environment below and
the same 13-module matrix as focused v4, with
`--junitxml=workflow/due-dilligence-performance/remediation/final-focused.xml -q`.
Combined stdout/stderr was saved with `set -o pipefail` and `tee` to
[final-focused.log](final-focused.log); [JUnit](final-focused.xml) records
**153 passed, 51 subtests, 10 warnings, 48.38 seconds**, zero failures/errors.
The independent harness test command also passed **21 tests and 18 subtests**
in 0.43 seconds. Seven final report/ADR documents' local links resolve,
including all three links to the actual dated archive.

Final post-archive full command (with the common environment):
`python -m pytest --junitxml=workflow/due-dilligence-performance/remediation/final-framework.xml -q`.
Combined stdout/stderr and pipeline status were preserved in
[final-framework.log](final-framework.log); [JUnit](final-framework.xml) records
**1,773 passed, 353 subtests, 16 skipped, 49 warnings, 294.69 seconds**,
zero failures/errors. Skip categories and environmental blind spots are unchanged.
These durations are suite execution evidence, not performance comparisons.

The complete measured source/test/probe manifest is unchanged after these
tests. The formal v4 verifier again passes all 141 workers and seven sections;
all 15 raw failed-capture hashes also match. The separate
[EVIDENCE.sha256](EVIDENCE.sha256) inventories final and historical-remediation
machine records (`.json`, `.xml`, `.log`, `.txt`) without modifying the formal
eight-file v4 inventory or the immutable planning/historical inventories.

The pilot subsequently authorized “merge to main”. Integration is scoped to
the independent framework repository, not the dirty shop checkout. Primary
`main` was clean at the recorded `66401867b8510f0a24f6a0771b732aea6c949828`;
the cycle base is the subsequent audit commit `40a848d6f8939b3e0d69e45a11b514b4ebfa263f`.
The performance branch must contain exactly its planning and completed
implementation commits above that audit base before fast-forward integration.

## Recorded correctness and measurement checkpoints

The correctness and measurement commands below ran from
`/home/asa/devel/libresolid-studio/solid-node/WTs/performance-analysis`, on branch
`performance-analysis`, with implementation uncommitted above the planning
commit. Earlier checkpoints used
`4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c`; the AR-07 re-ratification amended
planning only to `2ca4b9f06835d1133b6ad00eceecdee6e29b714c`. They use the workspace virtualenv
(Python 3.12.3), `PYTHONPATH` set to that exact worktree, and
`PYTHONDONTWRITEBYTECODE=1`. Dependency/host provenance is also retained in the
separate planning baseline and current-performance capture; suite durations
are not controlled performance comparisons.

## Final commit verification

The implementation/archive commit was created above planning `2ca4b9f`, then
`git status --porcelain` was empty and `git rev-list --count 40a848d..HEAD`
returned **2**. All 375 committed source/test/probe entry records exactly equal
the measured candidate. The candidate aggregate includes its original planning
HEAD, so after committing, entry equality is checked with
`candidate_identity(expected_head=None)` and the saved capture verifier runs
without `--require-current-candidate`; it passes all 141 workers and the saved
inventory. This does not relabel the capture as a new post-commit benchmark.

The complete staged-content whitespace check exposed one preserved extra
blank line at EOF in `_artifact.py` and intentional Markdown hard-break spaces
in three package evidence records. They are not correctness failures; source
bytes were kept identical to the measured/tested candidate. Source/tests pass
the whitespace check with only `blank-at-eof` disabled; raw logs/XML are
preserved rather than reformatted. Final bookkeeping changes only this record,
the progress index and the two completion checkboxes, by amending the same
implementation commit, after which clean/two-commit identity is reverified.

## Checkpoints

| Record | Result | Meaning |
| --- | --- | --- |
| [Planning baseline](README.md) | 1,639 passed, 302 subtests, 16 skipped, 46 warnings; 209.68 s | Unchanged pre-implementation correctness baseline. |
| `candidate-framework.log` / [JUnit](candidate-framework.xml) | 1,749 passed, seven failed, 353 subtests, 16 skipped, 48 warnings; 269.04 s | First combined run; preserved failures exposed the retained tests' build-directory leak. |
| [Isolation diagnosis](full-suite-isolation.md) | 1,756 passed, 353 subtests, 16 skipped, 48 warnings; 294.29 s | Diagnostic only: concurrent production correction prevents claiming one frozen candidate. |
| `candidate-focused-v2.log` / [JUnit](candidate-focused-v2.xml) | 131 passed, 51 subtests, one warning; 42.94 s | All remediation package suites together after AR-01/02/04 and fixture corrections. |
| `candidate-framework-v2.log` / [JUnit](candidate-framework-v2.xml) | 1,758 passed, 353 subtests, 16 skipped, 48 warnings; 267.59 s | Frozen source/tests through AR-04, before the AR-05 recovery-watch correction. |
| `candidate-focused-v3.log` / [JUnit](candidate-focused-v3.xml) | 139 passed, 51 subtests, 10 warnings; 82.78 s | The package matrix plus the complete reload-resilience module after AR-05. |
| `candidate-framework-v3.log` / [JUnit](candidate-framework-v3.xml) | 1,759 passed, 353 subtests, 16 skipped, 49 warnings; 278.57 s | Frozen production/tests through AR-01–AR-06, before the later AR-07 project finding; no failures/errors. |
| `candidate-focused-v4.log` / [JUnit](candidate-focused-v4.xml) | 153 passed, 51 subtests, ten warnings; 51.14 s | The package matrix plus reload resilience after the re-ratified AR-07 correction. |
| `candidate-framework-v4.log` / [JUnit](candidate-framework-v4.xml) | 1,773 passed, 353 subtests, 16 skipped, 49 warnings; 277.69 s | Frozen production/tests after AR-07, no failures/errors. |

The first full run and every subsequent checkpoint are separate files; failed
evidence is never overwritten by a green rerun. AR-01 through AR-08 are
independently closed at the targeted implementation/harness level. Final
measurement and overall independent evidence review are complete and green,
including Metamaquina2's exact timestamp-only baseline/current manifest proof.
Archive, final post-archive checks and commit are recorded below as they finish.

## Coordinator commands

Common environment prefix:

```sh
env PYTHONPATH=/home/asa/devel/libresolid-studio/solid-node/WTs/performance-analysis \
  PYTHONDONTWRITEBYTECODE=1 \
  /home/asa/devel/libresolid-studio/.venv/bin/python -m pytest
```

The focused v2 run appends:

```sh
-q tests/test_source_generation.py tests/test_source_census.py \
  tests/test_retained_builder_generation.py tests/test_persistent_piece_facts.py \
  tests/test_generation_dedup.py tests/test_flexible_cache_performance.py \
  tests/test_adaptive_broad_phase.py tests/test_traversal_naming.py \
  tests/test_exact_placement_cache.py tests/test_sparse_statics.py \
  tests/test_manifold_cache.py tests/test_exact_test_isolation.py \
  --junitxml=workflow/due-dilligence-performance/remediation/candidate-focused-v2.xml
```

The focused v3 run uses the same list plus
`tests/test_builder_reload_resilience.py`, with the JUnit suffix changed to
`candidate-focused-v3.xml`.

Each coordinator full run appends `-q --durations=25` and its corresponding
`--junitxml=workflow/due-dilligence-performance/remediation/<record>.xml`.
Shell `pipefail` is enabled and combined output is captured with `tee` to the
same record's `.log`. The v2 JUnit records a start timestamp of
2026-09-07T20:47:44.205091+00:00 on host `devel`, 2,127 cases including
subtests, and zero errors/failures. No empirical benchmark ran concurrently.

The v3 JUnit records 2026-09-07T21:02:26.891201+00:00 on `devel`, 2,128 cases,
zero errors/failures, and the same 16 skip cases. Its one additional warning
is the existing fork-fixture warning emitted by the new native-watchdog
regression. The frozen source/test/probe identity was checked during the run
and after completion:
`689974d2373f57f9f33074f833be96ffae80db9a2ee09fb5050405f430945fa7`
(374 entries). No CAD benchmark ran until this suite completed.

The coordinator separately reran the non-CAD harness sanity suite:

```sh
env PYTHONPATH=/home/asa/devel/libresolid-studio/solid-node/WTs/performance-analysis/workflow/due-dilligence-performance/remediation \
  PYTHONDONTWRITEBYTECODE=1 \
  /home/asa/devel/libresolid-studio/.venv/bin/python -m pytest -q \
  workflow/due-dilligence-performance/remediation/test_current_performance_harness.py
```

Result: 13 passed, 14 subtests, 0.43 seconds. Actual-builder preflight and
independent harness review are recorded under AR-03 in the
[review report](adversarial-review.md).

After the first formal capture exposed the cold/first-warm SCAD settlement
boundary, the same coordinator command passed 18 tests and 14 subtests in
0.40 seconds. The corrected candidate identity is
`59fad19d6560b7830372adc33e31b0765b5932f6ffc4c1b8ec80af281aa837bf`
(374 entries). Comparing both complete identity manifests shows exactly two
changed entries: `run_current_performance_probe.py` and
`test_current_performance_harness.py`, both under this remediation directory.
Framework source and tests remain byte-identical to the full-v3 tested state.

The first capture is preserved, including its rejected build record:

```text
87100889eabf10190309077e308776fec2e5f3a79dfb0e57c057df8842ddce4d  current-candidate-candidate-identity.json
53a14b2b79f5d6f10cb86b456efc8be5e58158048a48285013792c84e81a7700  current-candidate-startup.json
f357ac095683eb6129d5baf0f2fe8d3950272920694bfad95b7340327d6eba17  current-candidate-build.json
```

Those are evidence-file SHA-256 values, not candidate-content identities.
The rejected build record is not a passing no-churn measurement. Its Solid2
first-warm changes are different desired SCAD bytes, while STL maps and viewer
manifest bytes agree; the revised capture separately gates a third, settled
build without discarding cold/first-warm timing comparability.

## AR-07 re-ratification and planning preservation

On 2026-09-07 the pilot approved the deferred non-rigid assembly SCAD
publication boundary. Strict OpenSpec validation and independent planning
re-review passed before the four planning artifacts alone were amended.
Commit `2ca4b9f06835d1133b6ad00eceecdee6e29b714c` was verified planning-only,
clean, and exactly one commit above `40a848d6`. The temporarily stashed
implementation was restored from `91fd62697532f5c6ac99af60cdb69e2960c0ad0b`:
`git diff` against its tracked tree was empty for source/tests/progress, and
every blob in its untracked-file tree matched `git hash-object` of the restored
file. Ignored test logs were left in place throughout. Both immutable checksum
inventories passed again. The original baseline/failed-capture records still
name their original measured commit and bytes; they are not relabelled as the
amended planning state. OpenSpec apply reported 50/65 tasks complete after the
previous completion markers were restored and the three added tasks left open.

The CLI's older design-context suggestion of one commit per increment and an
embedded viewer does not override the shop's current two-commit cycle and
independent-viewer repository boundary. No viewer package work is in this cycle.

The frozen post-AR-07 source/test/probe record is
[candidate-frozen-v4.json](candidate-frozen-v4.json):
`b8b16185cb9e524c8cd119ff291c4a8d206fe4389794ef5293021909db39a4b0`,
375 entries, planning HEAD `2ca4b9f06835d1133b6ad00eceecdee6e29b714c`.
The focused-v4 command is the focused-v3 list with only the output suffix
changed. The candidate identity was rechecked after its successful completion
and immediately after starting the full-v4 command. AR-07's independently
closed correction and finite nine-build caller proof are recorded in
[ar07.md](ar07.md) and [the review](adversarial-review.md). The package log
contains summarized/transcribed red and green excerpts, explicitly not a
complete raw failure transcript; coordinator v4 logs capture complete combined
output with `tee` and JUnit. Formal remeasurement remains a separate gate.

The full-v4 JUnit records 2,142 cases, zero errors/failures, the same 16 skip
cases, timestamp `2026-09-07T22:20:08.841084+00:00`, and hostname `devel`.
The complete candidate identity was checked again after success and matched
the frozen record exactly. Only then was the all-seven-section
`current-candidate-v3` formal capture released. Task-owned competing CAD tests
are paused for the capture.

## AR-08 measurement subprocess correction

The v3 capture passed startup, build, batch, projects and empirical, then
stopped at algorithms because the absolute subprocess script could not import
its disposable `bench` fixture. Memory was not run. The complete failed
records and their SHA-256 inventory remain in [failed-captures.md](failed-captures.md).
This is a harness failure, not a failing framework correctness run.

The runner now replaces ambient `PYTHONPATH` with the exact framework root
followed by the resolved, verified disposable worker directory, recording the
effective value on successful, failed and timed-out worker records. The real
subprocess regression requires both a fixture-only import and the framework
module's resolved origin at this candidate checkout; original catalogue and
framework directories are rejected as worker fixture directories. The owner
recorded the red failure before correction and 21 passing harness tests after
correction. Independent re-review and finite algorithm/memory smoke precede
another all-seven-section formal capture; neither smoke nor earlier incomplete
captures may substitute into its headline comparison.

The coordinator compared every candidate manifest entry against the full-v4
frozen record. Only `run_current_performance_probe.py` and
`test_current_performance_harness.py` changed, both in this remediation folder;
production and framework tests remain the exact bytes validated by full-v4.

Independent AR-08 re-review passed 21 harness tests in 0.341 seconds. The
finite `ar08-smoke` algorithm/memory capture then passed 14 workers and every
structural/equivalence/provenance gate in an independent coordinator check.
Its saved identity and the current candidate match exactly:
`d3615253809628a7b9e988354f669da26a0a84ab2ac3855ac8b6cd4d20841250`,
375 entries. Comparing that final manifest with the full-v4 tested manifest
again confirmed only the two harness paths differ. The all-seven
`current-candidate-v4` formal run was released only after these checks;
the smoke has its own three-record raw inventory and is not comparative data.

## Complete replacement performance capture

`current-candidate-v4` completed startup, build, batch, projects, empirical,
algorithms and memory with **141 successful nested workers**. The coordinator
independently ran:

```sh
env PYTHONPATH=workflow/due-dilligence-performance/remediation \
  PYTHONDONTWRITEBYTECODE=1 \
  /home/asa/devel/libresolid-studio/.venv/bin/python \
  workflow/due-dilligence-performance/remediation/verify_current_performance_evidence.py \
  --label current-candidate-v4 --require-current-candidate --require-inventory
```

It passed all seven structural/equivalence sections, current candidate equality,
generated-evidence hashes, immutable historical/planning inventories and
original-project provenance. The candidate is the post-AR-08 identity above;
the original catalogue remains exactly at its planning-baseline source/status
snapshots, including pre-existing dirty files. No task-owned CAD tests ran
concurrently with this formal capture. The sole final comparative report is
[current-candidate-v4.md](current-candidate-v4.md); prior incomplete labels and
the smoke are not substituted into it. [DISPOSITION.md](DISPOSITION.md) links
all audit items to their production, red/green and current measurement proof.

## Metamaquina2 timestamp-only document difference

Final claim review caught an incorrect unqualified baseline-equality statement:
Metamaquina2's v4 manifest digest differs, although its aggregate STL/piece
fields and current repeat-build outputs agree. A finite, separately labelled
legacy/candidate disposable reproduction verified actual framework module
origins and produced the same current document with both implementations,
including a framework-only import-path variant. No source change was made.

The coordinator then recovered the exact baseline digest by replacing only
226 current document root-tree `mtime` values with the older values present
in the original project's saved document, and serializing with the producer's
ordinary `json.dumps`. The result is exactly 173,799 bytes and SHA-256
`d1ba8ddfdfc993b1d56f180877a3715a77e0e536dd6817a5e573928df88ec338`,
matching planning and v3. Current v4 is 173,857 bytes with digest
`f9f904f826eca8fce579fb6cb440f22342609f3ca8215ef9ac8d4d3be2598919`.
Names, geometry references, piece facts, placements, operations, bindings,
instructions and every other field are untouched by that substitution.

The original source-byte/status/HEAD snapshots remain equal, but they do not
record metadata. Source timestamps around 22:34 changed between v3 and v4;
the document correctly exposes that metadata refresh. This is not an AR-08
import-path effect or a reason to relabel literal document hashes as equal.
The diagnostic is explanatory evidence, not a replacement timing sample.
Only disposable data and in-memory JSON are used; original files are not
written or restamped by this task.

## Environmental limits

The 16 full-suite skips retain the baseline categories: 13 missing-Sphinx
cases, two absent Internal-Cycloidal-Actuator vendor STEP fixtures, and one
opt-in web snapshot case. No live browser capture or real JSCAD CLI integration
is claimed. JSCAD renderer races have mocked process/atomic-publication tests.
Warnings are retained, including dependency deprecations, legacy driver reads
in `render()`, deprecated pairwise assertions, and historical test fixtures
using fork in a multithreaded process. Production builders continue to use
the explicit fresh-interpreter context.
