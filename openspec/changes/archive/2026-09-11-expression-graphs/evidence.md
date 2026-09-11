# Expression-graph implementation evidence

Status: complete machine acceptance and final whole-suite check passed.

## Baseline

- Planning base: `e51d196c74f10e240ef0f3580c52f9abee66d63b`.
- Ratified planning commit: `446bc22`.
- Worktree: `/home/asa/devel/libresolid-studio/solid-node/WTs/expression-graphs`.
- Curta clean HEAD: `d80e7bf71da130295bacc1bd72971e1029e29f9d`.
- Viewer clean HEAD: `6fb082ba9823fb0839631bd4a3ecbf4a41b33b64`.
- Installed versions: solidpython2 2.1.3, CadQuery 2.7.0, build123d 0.10.0,
  molejo 0.2.0, solid-node-viewer 0.1.0 (unreleased), pytest 9.1.1.
- Python 3.12.3; Linux 6.8.0-139-generic; OpenSCAD 2021.01 at `/usr/bin/openscad`.
- Prior Curta failure: 7,857,084 KiB maximum process RSS, before the binding
  pass. This is not an aggregate process-tree measurement.

Existing expected values remain in the tests and viewer parity fixture at the
recorded commits. No baseline fixture has been regenerated to derive expected
values from the new implementation.

## Actual measured memory

The final runs use the same unchanged framework Python-source SHA-256:

`e991bb781b705b72a778a49254f3e6e4e040c9501c05722b83b97f967454b2e0`.

| Run | Peak bytes | MiB | GiB | Elapsed seconds | Cap headroom bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Final warm geometry cache | 831,078,400 | 792.578125 | 0.7740020752 | 30.5534 | 7,168,921,600 |
| Final fresh geometry cache | 1,179,168,768 | 1,124.542969 | 1.098186493 | 73.8097 | 6,820,831,232 |

Both complete exports succeeded with zero swap peak and zero memory-limit,
OOM or OOM-kill events. The largest observed final peak is **1.10 GiB**, not
8 GB. Approximately 85.26% of the safety ceiling remained unused in that run.
Raw exact reports: [warm](evidence/final-warm.json),
[cold](evidence/final-cold.json).

Earlier implementation runs are retained too, not hidden: [warm](evidence/warm.json)
829,194,240 bytes (790.78125 MiB), 26.3112 seconds;
[cold](evidence/cold.json) 736,280,576 bytes (702.171875 MiB), 65.4659 seconds.
These precede the final source hash. They demonstrate run-to-run variation,
not that a cold build necessarily needs less memory. No causal attribution is
made for the difference.

### What was measured

`tools/measure_process_tree.py` runs inside a fresh systemd user-service cgroup,
requires `memory.max == 8000000000` and `memory.swap.max == 0`, and reads the
kernel's `memory.peak` while its wrapper still keeps the cgroup alive. This
includes the wrapper, exporter and its descendants, charged file cache and
kernel memory. It is **not** Python heap size, sampled RSS, a sum of per-process
high-water marks, or the rounded systemd completion message. The latter reported
a much smaller value after teardown and is not the measurement used here.

The warm run uses Curta's existing `_build_checks`. The cold run starts in a
new `_build_expression_graphs_cold_final` directory; no existing geometry cache
was erased. This is a geometry-artifact-cache-cold build, not an OS page-cache
flush. Shared pages charged outside the cgroup and unrelated applications are
not counted. Browser memory is not part of the export measurement. The host had
16 GB RAM and 4 GB swap; the measured service could use no swap.

These are observed peaks for the recorded processes/content. They are not a
proven minimum RAM capacity for an entire desktop or a universal bound for every
machine. No lower-cap binary search was performed. The original failed process
had reached 8,045,654,016 bytes of maximum RSS, about 7.49 GiB, without completing;
the new largest aggregate peak is about 6.82 times smaller, but those accounting
methods are different and must not be presented as a controlled RSS speedup.

## Reproduction

Run from the expression-graphs framework bench. The paths below are deliberately
explicit; Curta and the viewer remain independent, unchanged repositories.

```sh
systemd-run --user --wait --pipe --collect \\
  --unit=expression-curta-final-warm \\
  --property=MemoryMax=8000000000 --property=MemorySwapMax=0 \\
  --working-directory=/home/asa/devel/libresolid-studio/solid-node/WTs/expression-graphs \\
  --setenv=PYTHONPATH=/home/asa/devel/libresolid-studio/solid-node/WTs/expression-graphs \\
  --setenv=SOLID_BUILD_DIR=/home/asa/devel/libresolid-studio/projects/Calculators/Curta-Type-I-3x/_build_checks \\
  /home/asa/devel/libresolid-studio/.venv/bin/python tools/measure_process_tree.py \\
  --report /home/asa/devel/libresolid-studio/projects/Calculators/Curta-Type-I-3x/_build_evidence/expression-graphs-final-warm.json \\
  --log /home/asa/devel/libresolid-studio/projects/Calculators/Curta-Type-I-3x/_build_evidence/expression-graphs-final-warm.log \\
  -- /home/asa/devel/libresolid-studio/.venv/bin/solid export \\
  /home/asa/devel/libresolid-studio/projects/Calculators/Curta-Type-I-3x/simulation/curta.py:Curta \\
  -o /home/asa/devel/libresolid-studio/projects/Calculators/Curta-Type-I-3x/_build_evidence/expression-graphs-final-warm
```

For a new cold trial select a previously absent build directory, a new unit and
new report/log/output paths. Do not erase the existing caches to repeat it.
The wrapper hashes sorted relative framework Python-source paths followed by
their bytes before/after the command and reports whether they stayed unchanged.

## Machine and cross-runtime result

All four exports have the same manifest SHA-256:

`0906c214f9f5e0acae5f49d2572e4c2b42f465350299baa24aba14cb0b3af3df`.

- Manifest: 1,669,980 bytes; schema 4; 608 nodes, 390 rigid instances,
  148 distinct rigid STL artifacts, 38 flexible leaves.
- 2,558 operation/parameter scalar slots; 9,969 bindings, longest 34 characters.
- Collected native roots reach 44,718 nodes; document-local structural
  interning reduces those to 11,027 canonical nodes. Ordinary numeric string
  slots outside native roots are not included in these two node counts.
- The original pinned 451-case viewer fixture and the newly generated
  451-case fixture have identical keys and expected numbers. Both pass the
  unchanged viewer evaluator with maximum absolute error 2.4869e-14 (bound 1e-9).
  The new fixture shares all corpora through 145 bindings instead of four;
  its coverage guard checks all 14 builtins across cases and bindings together.
- 33,254 Curta values across 13 poses match the independent numeric law walk
  with maximum absolute error 1.77636e-15. Poses include rest, nine samples
  around a result carry, subtraction, carriage shift and clearing.
- The unchanged viewer suite passes: 14 files, 298 tests.

Reproduction tools: `tools/generate_parity_fixture.py OUTPUT`,
`tools/check_curta_expressions.py PROJECT MANIFEST OUTPUT`, and
`node tools/check_expression_viewer.mjs VIEWER_WIDGET OLD_FIXTURE NEW_FIXTURE CURTA_FIXTURE`.
The last probe bundles the viewer's own source into an automatically removed
temporary directory; no viewer implementation is copied into framework source.
Fixture outputs and raw logs are under Curta's `_build_evidence/expression-graphs-*`.
No viewer source or pinned viewer fixture was modified.

## Visual evidence

`tools/capture_expression_export.py EXPORT OUTPUT` mounted the unchanged
bundle in Chromium 151.0.7922.34, viewer API 7, software WebGL. It set native
driver values through the public handle and checked readback at five carry
states. No browser page errors occurred.

Inspected `expression-graphs-browser/whole-rest.png`,
`spring-carry-0.png`, `spring-carry-0.7.png` and `spring-carry-0.99.png`
under Curta's evidence directory. The entire machine renders; isolating
`carry_mechanism/result_carries/results_tens_lever_assembly_1/carry_lever_spring`
shows continuous wire geometry and visible arm spreading/reset. The independent
parameter checks pin its right tip at 7.2417306487, 6.989422 and 9.395612 for
those respective carry poses. These checks validate publication and motion
parity, not remaining mechanical fit/manufacturability work on Curta.

## Red-first and framework regression evidence

The original bounded six-test reproducer had four failures and two passes:
14 doublings produced 163,835 characters; the six-stage carry/profile produced
36,007; a 10,000-term chain fell back after recursion failure; `unserialize`
consumed its caller's input list. No host-exhausting baseline run was attempted.
Numeric standalone reconstruction and explicit-input evaluation were added red
before implementing that boundary. A later diagnostic test caught port repr
stringifying its graph, also red before the fix.

Regression coverage now includes linear traced construction growth (1,000 vs
4,000 reuses), 10,000-term depth, 10,000 doublings compiled through multiple
native roots without invoking `str`, repeated graph reclamation, every supported
operator in both legacy operand orders, nested closure scope/name capture,
restored placement, truth refusal, a real carry/profile machine through export
and build with shared rigid/flexible roots, and bounded dependency diagnostics.
Six boundary-value closures were evaluated by installed OpenSCAD; tolerance
1e-5 accounts for its six-significant-figure echo output. The viewer comparisons
above retain their tighter 1e-9 bound and independent expected values.

An additional final-source probe measured the construction heap separately
with `tracemalloc` (not a process/cgroup measurement):

| Doublings | Native nodes | Construction peak bytes | Standalone characters | Two-root publication bytes |
| ---: | ---: | ---: | ---: | ---: |
| 14 | 15 | 2,944 | 275 | 678 |
| 1,000 | 1,001 | 137,576 | 24,664 | 51,692 |
| 4,000 | 4,001 | 544,808 | 108,661 | 216,692 |
| 10,000 | 10,001 | 1,360,808 | 276,661 | 546,692 |

The 14-step standalone result falls from the red baseline's 163,835 characters
to 275. Each reuse adds one native operation; output grows with the compact
bindings and decimal reference names, not with the expanded tree.

The first full run exposed one exception-type compatibility defect at
`set_state` plus legacy mechanism-test helpers that did not read closures.
The numeric state gate remains unchanged; helper updates preserve their original
expected numbers and check expanded structure only on small fixed fixtures.
The affected follow-up run passed 258 tests and 279 subtests. Final whole-suite
result: **2,265 passed, 3 skipped, 50 warnings, 886 subtests passed in 295.16 s**.
Command: `PYTHONPATH=$PWD /home/asa/devel/libresolid-studio/.venv/bin/python -m
pytest tests -q --disable-warnings --junitxml=.../expression-graphs-framework-tests.xml`.
The new RST guide also passes docutils parsing with warning-level failures enabled.

The full-suite skips were the opt-in browser snapshot end-to-end test and two
tests requiring an absent Internal-Cycloidal-Actuator vendor STEP fixture. The
real Curta browser probe above ran independently; the missing STEP fixture is
unrelated to motion expressions.

Post-archive verification enabled `SOLID_NODE_WEB_SNAPSHOT_E2E=1` and ran the
expression, math, mechanism, driver-document and browser-renderer tests:
**179 passed, 48 subtests passed, no skips**, including the actual transparent
browser photograph. The source hash still equals the two final memory runs.
Every archived delta requirement was compared with its synchronized baseline;
all are present, and post-archive validation again passes all 31 specs.

## Repository completion

ADR-101 supersedes only ADR-080's eager construction/flat SCAD decisions;
its historical clock measurements remain intact. The export and kinematics
baseline deltas and new motion-expression-sharing capability are synchronized.
All 31 baseline specs and the active change validate with `--all --strict`.
The completed implementation commit contains this record, its raw memory
reports, synchronized specs, compatibility guide and ADR-101. The cycle archive
is `openspec/changes/archive/2026-09-11-expression-graphs/`.
Integration target is standalone framework `main`; integration and push remain
unperformed and require pilot direction.
