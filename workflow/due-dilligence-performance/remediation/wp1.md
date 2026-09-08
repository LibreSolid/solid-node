# WP1 — Source-generation and census foundation

## Scope

WP1 establishes a process-local source generation around the existing project
loader and builder.  Project Python modules are compiled from coherently read
source bytes instead of trusting timestamp-and-size-valid bytecode.  The
loader records each project's pre-execution identity and rejects a different
post-load identity.  External modules retain the ordinary meta-path chain and
the default loader path retains its existing `sys.modules` class identity.

Each artifact-producing phase gets a new `SourceCensus`.  A census resolves
and stats each distinct spelling/path once, shares frozen observations and
content digests with overlapping node currency checks, and is discarded at
the boundary.  The generation retains the identities consumed by earlier
phases, including observable spelling-to-canonical mappings, so a later phase
cannot bless a same-mtime replacement or a retargeted symlink while reusing
old live classes or assembled geometry.  Nested producer incorporation is an
append-only delta rather than a scan of the accumulated census.  Large foreign
sources are hashed as streams and are not retained as byte payloads; Python
analysis may retain its small source bytes inside the phase.

The guarded seams cover the initial full source closure before lock waiting,
assembly, each artifact/currency pass, asynchronous-render wait before and
after, and document publication after serialization immediately before the
manifest write.  OpenSCAD constructor reads and STEP document/cache reads join
the generation coherently.  JSCAD is the narrow additional adapter correction
approved for task 2.4: it renders to a private temporary path, checks renderer
status and current source before atomically replacing the artifact and source
record, and preserves the old published artifact on failure or source change.
The JSCAD command's public inputs and adapter API are unchanged.

## Red proof

After the planning-head baseline gate, before production edits, this command
was run from the worktree:

```text
PYTHONPATH="$PWD" /home/asa/devel/libresolid-studio/.venv/bin/python -B \
  -m pytest -q tests/test_source_generation.py tests/test_source_census.py
```

Collection failed with two errors in 0.30 s because
`project_source_generation` and `solid_node.source_generation` did not exist.
That is honest API-absence proof only; it did not by itself exercise every
load, phase, wait, or publication race.  The retained stale-bytecode test also
constructs a real timestamp/size-valid `.pyc`, edits the source to equal-sized
bytes, restores its mtime, and proves the unchanged ordinary `load_node()`
executes value `1` while the generation-aware loader executes current value
`2`.

The later approved JSCAD correction had a separate pre-implementation run:

```text
PYTHONPATH="$PWD" /home/asa/devel/libresolid-studio/.venv/bin/python -B \
  -m pytest -q tests/test_source_generation.py -k jscad
```

It failed 2 tests in 0.29 s.  The legacy adapter did not raise when its source
was atomically replaced after rendering, and it did not raise on renderer
return code 2; both cases overwrote the published target.  These are
deterministic mocked-renderer tests because the environment has no JSCAD CLI.
No claim of a real JSCAD integration run is made.

Review-driven regressions additionally cover phase-context cleanup, late
imports, inter-phase foreign replacement, inter-phase symlink retargeting,
STEP replacement during a constructor-time read, custom external import
finders, one realpath/stat per distinct census contributor, no retained large
binary bytes, and constant identity-incorporation work for 100 repeated
overlapping includes.  Those refinements were not misreported as part of the
initial collection-error proof.

## Green proof

The final WP1-focused command was:

```text
PYTHONPATH="$PWD" /home/asa/devel/libresolid-studio/.venv/bin/python -B \
  -m pytest -q tests/test_source_generation.py tests/test_source_census.py \
  tests/test_source_set.py::UpToDateLeafTest::test_jscad_runs_when_the_artifact_is_missing \
  tests/test_openscad_dependency.py::JScadDependencyBoundaryTest
```

Result: **24 passed in 2.99 s**.

A wider source/foreign-adapter run passed **96 tests, 2 skipped, 4 subtests**
in 5.24 s.  It covered the two WP1 files plus STEP node/assembly and OpenSCAD,
JSCAD, CadQuery, and build123d dependency-boundary tests.

A post-handoff review found one failure-classification gap before the project
lock: when a foreign contributor first disappeared after node construction but
before the initial census, `FileNotFoundError` escaped instead of entering the
established load/reload error path.  Two real-process JSCAD-source tests first
failed in 16.13 s: the reload wrote no error and died, and initial startup wrote
no error record.  The narrow correction routes only an unobserved initial
census/mtime error through `_on_reload_exception`; a source already observed by
the generation still produces `SOURCE_CHANGED`.  Broad recovery keeps the
known missing foreign path in its precise watch set.  The two tests then passed
in 1.07 s, proving reload waits outside the project lock and exits on repair,
while initial startup fails and records the error.  The combined source,
retained-builder, reload, lifecycle, lock, subprocess, and WP4 seam run passed
**100 tests and 10 subtests** in 52.19 s.

The requested broad package run covered loader references, source closure and
sets, node-scoped/content-verified currency, builder lifecycle and reload
recovery, retained generations, build lock/subprocess isolation, develop
management, and imported/exact adapters.  Its first run found one WP1-owned
legacy JSCAD mock that lacked an integer return code; after correcting the
mock, the same set reached **405 passed, 2 skipped, 22 subtests** with three
then-current WP3 piece-fact expectation failures.  The WP3 owner corrected
those expectations.  A subsequent concurrent-tree rerun reached **403 passed,
2 skipped, 22 subtests** with five WP7 naming fixture failures caused by the
new `_link_children` serializer seam.  No WP1 test failed in either integration
run.  These cross-package failures are not claimed green here; root owns the
final coherent-tree rerun after the concurrent packages settle.

## Provenance and limits

- Planning source: `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on branch
  `performance-analysis`.
- Interpreter: `/home/asa/devel/libresolid-studio/.venv/bin/python`, invoked
  from this framework worktree with `PYTHONPATH="$PWD"` and `-B`.
- Candidate SHA-256 at the focused green run:
  - `solid_node/source_generation.py`:
    `7794c38f0edf44f210ac4193db497272af274e777ca96b99cc9d9e8bb53ff066`
  - `solid_node/core/loader.py`:
    `65546340a825c21d9ab6ab6e2375bd369af96951ade5048ee0fafbd811ff5834`
  - `solid_node/currency.py`:
    `562e5f6e661431ef7162f40093f15f277f911d8939f3066f7bbd23bd55eac699`
  - `solid_node/node/sources.py`:
    `6b19e2daf6bf66827c41cac8e4871218c4cc10ffee95499f5aef1590934525ca`
  - `solid_node/node/adapters/openscad.py`:
    `0f45a44e53699ee6cb3e86fa654ab37c8eac4a140146824d11a745246f670548`
  - `solid_node/node/adapters/step.py`:
    `aecf9cb7ff5674350128a30e8ec8248d27344cd60a9e618f1cb28fb502949826`
  - `solid_node/node/adapters/jscad.py`:
    `8f80ca4e049cf048035fe4bf7a1a113d26ecc3cec2b5193e20cc230b8eea8455`
  - `tests/test_source_generation.py`:
    `da1e8bd4f751a665484fc4e1f15b80968dc5541b6ae6f8574ff35068b9141a08`
  - `tests/test_source_census.py`:
    `d300e91aa2a729a3954dce008de5c8e8150ebeb3eafe76468d56bc863eba5012`
- `solid_node/core/builder.py` contains both the WP1 guard call sites and the
  dependent WP2 retained-loop implementation.  `solid_node/node/base.py` is
  also shared with WP7's naming work, so their whole-file hashes are omitted
  rather than presented as WP1-only identities.
- No original catalogue project, historical audit asset, task checkbox,
  progress record, baseline spec, ADR, or OpenSpec lifecycle record was edited
  by WP1.  No commit or staging operation was performed.
