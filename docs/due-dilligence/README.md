# Project due diligence

Reviewed **2026-09-07**, at commit **`fa977ac9f3621e8a56ab33ff3f80ca04e6498089`** (`main`, package metadata version 0.6.0).

The audit reproduced **11 bugs: five high priority and six medium priority**. The most consequential failures at the reviewed commit were successful builds publishing empty geometry, deletion of unrelated files, exports escaping their output directory, build-lock bypass, and stale geometry being reported current. The existing test suite passed despite all eleven findings; remediation status now lives in [PROGRESS.md](PROGRESS.md).

This report records the original findings, evidence, and recommended regression coverage. Fixes are developed on branch `due-dilligence` in `WTs/due-dilligence`, based on the commit above, under the parent workspace's worktree instructions. The branch has not been integrated into `main`.

Remediation status is tracked in [PROGRESS.md](PROGRESS.md). The original
findings and evidence in this report remain as the audit record even after a
fix lands; each resolved finding gains a separate resolution note.

## Remediation discipline

Work through one checklist item at a time in the existing `due-dilligence`
worktree. Unless the pilot chooses a different item, select the first unchecked
finding in [PROGRESS.md](PROGRESS.md), preserving the P1-first order recorded
there. Do not combine unrelated findings in one change.

For each item:

1. Re-run or inspect its saved reproduction, then read the relevant baseline
   specification, architecture synthesis, accepted decisions, source, and
   tests. Record any difference between the audit evidence and current code.
2. State the exact scope. Keep adjacent observations outside the change unless
   they are required for a coherent fix; retain them as later checklist items
   or review leads.
3. For a framework behavior change, create a focused OpenSpec change, present
   its requirements, design, and proof plan, and obtain explicit pilot
   ratification before implementation. A documentation-only correction that
   preserves the existing contract may proceed directly.
4. Add a regression that fails for the recorded reason before changing
   production code. Prefer the public CLI or originating path where practical,
   backed by a focused unit test when it pins an important boundary.
5. Implement the smallest change satisfying the ratified contract. If the
   evidence contradicts the plan, revise and re-ratify it before continuing.
6. Run focused tests, the saved probe or representative caller, the complete
   framework suite, and strict OpenSpec validation when a spec changed. Record
   skips, intermittent failures, and other limits rather than hiding them.
7. Update the finding with a resolution note, update the changelog when user
   behavior changed, archive the completed OpenSpec change when applicable,
   and mark the item done in [PROGRESS.md](PROGRESS.md).
8. Commit the planning state and completed implementation as required by the
   framework-change workflow. A documentation-only item uses one focused
   commit. Finish with a clean worktree and report commit IDs, validation, ADR
   disposition, and integration state.

An item is complete only when its regression or documentary proof passes, its
records are updated, and the corresponding commit exists. Completion does not
integrate the branch into `main`; integration remains a separate pilot
decision.

## Scope and evidence

Reviewed the build pipeline, source currency, node lifecycle and adapters, CLI managers, simulation, geometry assertions, serialization/export, viewer integration, packaging/CI configuration, and their relevant documentation and OpenSpec contracts. Ran the existing suite and small temporary-project probes against this checkout. This is a targeted engineering review, not an exhaustive proof of geometric correctness or a dependency vulnerability audit. The independent viewer, molejo, and example-project repositories were not audited.

**Baseline:** 1,524 tests passed, 14 skipped, 38 warnings, and 258 passing subtests in 203.10 seconds. Thirteen Sphinx tests skipped because Sphinx is unavailable; the real browser capture test skipped because `SOLID_NODE_WEB_SNAPSHOT_E2E` was unset. Browser staging tests ran with an installed viewer. Python 3.12.3 and OpenSCAD 2021.01 were used; Python 3.11 and other operating systems were not exercised. See [validation.txt](validation.txt) for the command and dependency versions.

The reproductions and observed output are retained:

- [probe_build.py](probe_build.py): renderer failure, error recovery, cleanup, scaffolding, source currency, watcher dispatch, and export path handling.
- [probe_additional.py](probe_additional.py): export directory escape, empty declarations, multi-model testing, real cross-process locking, and simulation inputs.
- [evidence.json](evidence.json): observed outputs, exit codes, artifact sizes, and selected diagnostics.

Run the scripts with the project's development Python, from the repository root:

```bash
python docs/due-dilligence/probe_build.py
python docs/due-dilligence/probe_additional.py
```

They create and remove their own temporary projects. Their exit code reports whether the probe completed; the JSON records the behavior observed, so these are observation probes rather than assertion-based regression tests. As fixes land, current probe output can differ from the original [evidence.json](evidence.json). Paths in that recorded evidence identify temporary directories that have since been removed. Watcher evidence is at event-dispatch level; the locking probe uses a real held `flock` and CLI subprocess.

## Priority overview

P1 means data loss, incorrect published geometry, or a broken concurrency/output boundary deserving prompt correction. P2 means a reproducible workflow or validation defect with a narrower trigger. All findings below have executed evidence; potential consequences beyond that evidence are identified as such.

| ID | Priority | Finding | Evidence key |
|---|---|---|---|
| F01 | P1 | A failed OpenSCAD render is published as a successful empty STL | `build.renderer_failure` |
| F02 | P1 | Build preparation deletes unrelated sibling files and directories | `build.cleanup` |
| F03 | P1 | Export can copy artifacts outside its requested output directory | `additional.export_escape` |
| F04 | P1 | Exact artifacts are written before acquiring the project build lock | `additional.lock_bypass` |
| F05 | P1 | Maximum-source-mtime caching can silently retain changed geometry | `build.mtime_collision` |
| F06 | P2 | The watcher ignores tracked non-Python geometry sources | `build.watch_events` |
| F07 | P2 | A successful unchanged rebuild leaves a stale failure status | `build.stale_error` |
| F08 | P2 | Numeric-leading project names generate invalid Python | `build.numeric_scaffold` |
| F09 | P2 | `solid test --all` aborts on a model build failure without `--failfast` | `additional.test_all` |
| F10 | P2 | A valid zero-count child declaration cannot build | `additional.zero_children` |
| F11 | P2 | Negative simulation step sizes silently skip scheduled checks | `additional.negative_dt` |

## F01 — Failed renderer output is committed as successful geometry

**Location:** [solid_node/node/base.py:1075–1086](../../solid_node/node/base.py#L1075), with the temporary file created at [line 856](../../solid_node/node/base.py#L856).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`reject-failed-openscad-render`. A nonzero OpenSCAD exit now fails the build,
removes its temporary output and lock, and preserves any previously published
STL and viewer snapshot. Focused unit and real CLI regressions cover cold and
replacement failures. Validation passed 30 focused tests and the complete
suite (1,527 passed, 14 skipped, 38 warnings, 258 passing subtests); the saved
probe now observes exit 1, no STL or viewer snapshot, and an error record. One
unrelated exact-geometry test failed once in the first full run, passed alone
and with its 58-test module, and passed in the repeated full suite. The
original evidence below remains the pre-fix audit record.

`StlRenderStart.wait()` ignores the subprocess return code and always calls `finish()`. The temporary output file already exists because `mkstemp()` created it before OpenSCAD ran. A failed renderer that writes nothing therefore leaves a zero-byte file which is stamped and published as current.

**Reproduction:** Create an `OpenScadNode` whose source contains:

```scad
module part() {
    assert(false, "audit deliberate failure");
    cube(1);
}
```

Run `solid build`. OpenSCAD reports the assertion failure, but the command exits **0**, publishes `viewer.json`, leaves no `errors.json`, and publishes an STL of **0 bytes**. The piece inventory logs a warning rather than rejecting publication.

**Impact:** A build consumer receives a success signal with unusable geometry. On the same failure path, an existing good artifact can be replaced by the failed output. This contradicts the [one-shot build outcome contract](../../openspec/specs/one-shot-build-and-notification/spec.md) and the [artifact publication contract](../../openspec/specs/build-pipeline/spec.md).

**Recommended correction and proof:** Check the renderer's exit status before publishing, propagate a failed build outcome, retain the previous artifact, and clean up the failed temporary output and render lock. Add a real renderer-failure regression for both a cold build and replacement of a previously valid STL. The [JSCAD adapter](../../solid_node/node/adapters/jscad.py#L73) also ignores its subprocess status and deserves the same review; an actual JSCAD failure was not exercised here.

## F02 — Build cleanup deletes files it does not own

**Location:** [solid_node/core/builder.py:191–218](../../solid_node/core/builder.py#L191).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`preserve-unowned-build-siblings`. Build preparation now consumes only the
directory referenced by a legacy build symlink and leaves every other sibling
untouched. Regression coverage includes ordinary preparation, legacy
migration, the project lock, and a real browser snapshot stage surviving an
overlapping preparation. Validation passed 21 focused tests (with the opt-in
Chromium capture test skipped) and the complete suite (1,527 passed, 16
skipped, 38 warnings, 258 passing subtests). The saved cleanup probe now
reports both the notes file and backup surviving. Two of the full-suite skips
are existing actuator-document proofs whose external vendor STEP file was not
present; thirteen require Sphinx and one requires the browser E2E opt-in. The
original evidence below remains the pre-fix audit record.

`prepare_build_dir()` unconditionally removes every sibling named `<build-dir>.*`, except the exact project lock path. The cleanup runs on every build preparation, even when the build directory is already ordinary and there is no old symlink layout to migrate. It does not establish that a matching path is a framework-owned legacy artifact.

**Reproduction:** Beside `_build`, create `_build.notes` containing user notes and `_build.backup/keep.txt` containing a backup. Call `prepare_build_dir()`. Both unrelated paths are deleted. The probe confines this operation to a temporary directory.

**Impact:** User data sharing the prefix is removed without an explicit cleanup request. A second consequence follows directly from the current code: [BrowserRenderer.stage()](../../solid_node/viewers/browser.py#L107) creates `_build.web-snapshot.*` siblings and [render() releases the lock before capture](../../solid_node/viewers/browser.py#L35). A concurrent build's preparation can delete a live snapshot stage. That interleaving was identified from source, not reproduced with Chromium.

**Recommended correction and proof:** Restrict migration cleanup to demonstrably owned legacy paths, and keep active snapshot staging outside that cleanup rule. Test ordinary repeated preparation with unrelated sibling files, plus a capture overlapping a build.

## F03 — Export paths can escape the output directory

**Location:** [solid_node/core/export.py:140–149](../../solid_node/core/export.py#L140), consumed by [the copy loop at lines 112–117](../../solid_node/core/export.py#L112).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`confine-export-models`. Export model paths now use the project-aware and
selection-aware build-directory resolver, canonicalize both the build root and
artifact, and reject an artifact outside that root before touching the output.
The CLI reports that invariant failure without a traceback or success message.
Regressions cover nested invocation, a relative configured build root, a named
model selection, direct-call rejection, and the CLI diagnostic. Validation
passed 23 focused tests with 5 passing subtests and the complete suite (1,532
passed, 16 skipped, 38 warnings, 258 passing subtests). The saved probe now
emits `models/design/part-Part-8570a2e1669f.stl`, resolves it beneath
`portable/models/`, and reports `outside_output: false`. The original evidence
below remains the pre-fix audit record.

`_model_path()` derives its build root from `SOLID_BUILD_DIR` or the current directory's `_build`. Actual node artifacts are anchored to the discovered project root. A direct file/qualifier reference does not anchor `SOLID_BUILD_DIR`, so the two roots disagree when the caller is in a project subdirectory or outside the project. The resulting `..` segments are accepted by the destination copy loop.

**Reproduction:** From `<project>/design/nested`, export an absolute reference to `<project>/design/part.py`, using `--no-widget -o <temporary>/exports/sub/portable`. The command exits **0** and writes this manifest reference:

```text
models/../../../_build/design/part-Part-8570a2e1669f.stl
```

The copied STL actually lands under `<temporary>/exports/_build/design/`, **outside** `portable/`. The probe verifies both the escape and the file's existence.

**Impact:** Copying or serving only the advertised export directory produces a broken export. The copy can also overwrite an existing file outside the requested destination if the derived path matches it. This violates the [portable export contract](../../openspec/specs/export/spec.md).

**Recommended correction and proof:** Resolve the artifact root through the same project/model selection used to build the node, and enforce destination containment before copying. Test path and qualifier exports from the project root, a nested directory, and outside the project, with both default and configured build roots.

## F04 — Exact geometry bypasses build mutual exclusion

**Location:** [solid_node/core/builder.py:290–309](../../solid_node/core/builder.py#L290), [solid_node/node/exact_leaf.py:84–91](../../solid_node/node/exact_leaf.py#L84), and [solid_node/manager/test.py:205–214](../../solid_node/manager/test.py#L205).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`lock-artifact-assembly`. The builder now acquires the selected project lock
before assembly and holds it continuously through artifact and viewer-document
publication. It checks the loaded source state before and after assembly and
defers reload-error waiting until after releasing the lock. The test runner
holds the same lock across keyframing, preliminary render, assembly, and STL
generation, then releases it before executing project tests. Real process
regressions cover cold CadQuery build and cold `StlNode` test-build contention;
184 focused tests and 2 subtests passed. The saved probe now observes no STL
while the independent holder owns the lock and a successful build after
release. The repeated complete suite passed 1,535 tests with 16 skipped, 38
warnings, and 258 passing subtests. The first complete run exposed the new
mocked-builder regression leaking `SOLID_BUILD_DIR` into later modules; after
the fixture restored its environment, the 166-test affected set and repeated
complete suite passed. The original evidence below remains the pre-fix audit
record.

The builder calls `node.assemble()` before entering `project_build_lock()`. Exact leaf assembly writes BREP and STL artifacts in `as_scad()`, so the expensive rendering and publication have already happened when the lock is acquired. The test manager likewise assembles before its lock. Other adapters that materialize during assembly warrant the same audit.

**Reproduction:** Hold the project's real `_build.lock` using `fcntl.flock(..., LOCK_EX)` in one process. Start `solid build` for a new CadQuery cube in another. A **684-byte STL appears while the first process still holds the lock**, and the CLI remains running. Release the lock; the CLI then completes successfully.

**Impact:** Two builders can render and replace the same exact artifacts concurrently. Checking source freshness later cannot undo a publication that already happened. The [mutual-exclusion requirement](../../openspec/specs/build-pipeline/spec.md#requirement-project-build-mutual-exclusion) explicitly requires every artifact producer to acquire the lock before rendering or publishing.

**Recommended correction and proof:** Enclose every artifact-producing lifecycle phase in the project lock, including assembly and any load-time hooks that can materialize artifacts. Keep watch waits and notifications outside it. Test contention with actual exact and imported leaves, rather than only a stubbed `build_stls()` call.

## F05 — Aggregate timestamp equality hides changed source contents

**Location:** [solid_node/node/base.py:737–740](../../solid_node/node/base.py#L737) and [1012–1016](../../solid_node/node/base.py#L1012).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`guard-source-set-currency` and ADR-081. Artifact timestamp equality now also
requires a versioned sidecar fingerprint covering every tracked source's
project-relative path, filesystem identity, size, mtime, and change time. A
fingerprint disagreement uses the existing node-scoped content digest, so
changed content rebuilds while metadata-only and unrelated sibling edits
refresh the record without regenerating geometry. Legacy digest-only records
verify and upgrade in place; malformed records certify nothing. The focused
red run reproduced four intended failures, including the future-maximum and
same-size restored-mtime cases. After correction, 17 currency tests and a
296-test publisher/currency set passed; the public probe published 8,000 mm³
after the helper edit; and the complete suite passed 1,540 tests with 16
skipped, 38 warnings, and 258 passing subtests. The original evidence below
remains the pre-fix audit record.

Currency compares the artifact timestamp with the **maximum** timestamp of all tracked sources. If that maximum stays the same, `_up_to_date()` returns `True` without inspecting the recorded source digest. A contributing file can change while remaining older than another tracked source, so the maximum is not a sufficient change detector.

**Reproduction:** A leaf imports `SIZE` from `dimensions.py`. Stamp the leaf file 60 seconds ahead, then build a cube with `SIZE = 1`. Change the helper to `SIZE = 20`, leaving its new timestamp below the leaf's timestamp, and build again. Both builds exit **0**, but the published volume remains **1 mm³** instead of **8,000 mm³**.

**Impact:** Clock skew, future-dated files, or source restoration preserving older timestamps can silently retain incorrect geometry. The helper is already in the tracked set: expanding dependency discovery does not fix this defect. The content fallback never runs on this path. This contradicts the [build currency requirement](../../openspec/specs/build-pipeline/spec.md), which says changed source must not be reported current.

**Recommended correction and proof:** Use a source-set fingerprint that detects changes to individual contributors, with an explicit policy for content changes under preserved timestamps. Reconcile the performance-oriented timestamp rule with the stronger correctness claim in the specs. Add a regression where a dependency changes without becoming the newest source.

## F06 — Changes to non-Python source files never trigger reload

**Location:** [solid_node/core/builder.py:302–305](../../solid_node/core/builder.py#L302) and [581–594](../../solid_node/core/builder.py#L581).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`watch-all-tracked-sources`. A successful assembly now records normalized real
paths for every precisely watched source, and any modification to one of those
paths triggers the existing thread-safe rebuild signal regardless of its file
extension. Events outside that set retain the recursive recovery watch's
Python-only and `__pycache__` filters. The red run rejected four tracked
geometry extensions and left a live imported-STL builder waiting after its
mesh changed. After correction, 165 focused lifecycle, recovery, source-set,
and adapter tests passed with 7 passing subtests; the live process exited on
the STL edit, and the saved probe reports `true` for tracked `.py`, `.scad`,
`.js`, `.stl`, and `.step` modifications while the out-of-scope move remains
`false`. The complete suite passed 1,544 tests with 16 skipped, 39 warnings,
and 263 passing subtests. The original evidence below remains the pre-fix audit
record. No new ADR was needed: the correction makes the handler honor the
individual tracked-source watch already accepted in ADR-007 and leaves that
architecture unchanged.

The builder watches each file in `node.files`, but its modification handler rejects every path that does not end in `.py`. The comment assumes the precise source list contains only Python files; OpenSCAD, JSCAD, imported STL, and STEP adapters invalidate that assumption.

**Reproduction:** Dispatch real watchdog `FileModifiedEvent` objects through a builder with an asyncio future. A `.py` modification resolves the future; modifications to `.scad`, `.js`, `.stl`, and `.step` do not.

**Impact:** Editing a watched geometry source leaves `solid develop` showing the previous build until a qualifying Python edit or a manual restart. This conflicts with the [watch-rebuild requirement](../../openspec/specs/build-pipeline/spec.md#requirement-watch-rebuild-loop).

**Recommended correction and proof:** Filter the broad recovery watch separately from the precise tracked-source watch. Accept modifications to every explicitly tracked source. Add real develop-loop tests for non-Python sources. The probe also shows that a directly dispatched move event does nothing, but actual editor atomic-save behavior is platform dependent and is not claimed as a separately confirmed defect here.

## F07 — Successful rebuilds can leave `solid models` reporting failure

**Location:** [solid_node/core/builder.py:457–461](../../solid_node/core/builder.py#L457).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`clear-recovered-build-errors`. Snapshot publication now constructs the full
document before clearing prior failure state, then reports recovery even when
the document already matches `viewer.json`. That recovery invokes the existing
development callback after the project lock is released; a true no-op with no
prior error remains silent. Focused publication, lifecycle, CLI, and model
status coverage passed 86 tests with 17 passing subtests. The saved public
probe now observes both builds exiting 0, `errors.json` removed, and `solid
models --json` reporting `"state": "published"`. No new ADR was needed: the
change fills the unchanged-document case in ADR-038's error/publication order
and uses ADR-031's existing completed-publication callback boundary. The
complete suite passed 1,547 tests with 16 skipped, 39 warnings, and 263 passing
subtests. The original evidence below remains the pre-fix audit record.

`_write_viewer_snapshot()` returns immediately when its serialized document equals the existing one. `clear_errors()` comes after that return, so an unchanged successful result cannot clear a previous failure.

**Reproduction:** Build a valid cube, place a previous transient failure in `_build/errors.json`, and run `solid build` again without modifying the model. The rebuild exits **0**, but `errors.json` survives and `solid models --json` reports **`"state": "failed"`**. The injected error file isolates recovery from the unrelated causes of a transient failure.

**Impact:** Status consumers disagree with the successful build outcome and can keep displaying an error indefinitely. The [error-publication contract](../../openspec/specs/build-pipeline/spec.md) requires successful builds to remove the previous error.

**Recommended correction and proof:** Clear recovered errors after successful validation regardless of whether document bytes changed; keep the failure state intact until the build is actually complete. Test unchanged-document recovery and define whether that status transition should notify consumers.

## F08 — `solid new 3d-printer` creates an unusable project

**Location:** [solid_node/manager/new.py:30–32](../../solid_node/manager/new.py#L30).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`normalize-scaffold-identifiers`. Scaffold naming now produces one final
package/class pair and uses it consistently for the target, modules, tests,
template substitutions, and manifest. A sanitized leading-digit or Python
keyword name gains a `project_` prefix: `3d-printer` becomes
`project_3d_printer:Project3dPrinter`, while `class` becomes
`project_class:ProjectClass`; existing `snowman-3` behavior remains
`snowman_3:Snowman3`. Focused command, CLI, loader, build, compilation, and
generated-test coverage passed 32 tests with 19 passing subtests. Both edge
projects build and pass their two generated integrity tests without edits. The
saved public probe now reports a `project_3d_printer` target and a successful
first build. No new ADR was needed because this enforces the identifier-safe
scaffolding contract already recorded by ADR-024. The printed browser URL is
tracked separately as C04. The complete suite passed 1,551 tests with 16
skipped, 39 warnings, and 270 passing subtests. The original evidence below
remains the pre-fix audit record.

Name normalization permits leading digits and derives the class name directly from the normalized package. `3d-printer` becomes package `3d_printer` and class `3dPrinter`.

**Reproduction:** `solid new 3d-printer` exits **0** and writes `class 3dPrinter(Solid2Node):`. Running `solid build` in the generated project exits **1** with `SyntaxError: invalid decimal literal`.

**Impact:** A plausible mechanical-project name produces broken source while scaffolding reports success.

**Recommended correction and proof:** Either reject invalid identifiers before creating anything or consistently prefix/normalize them into valid package and class identifiers. Compile and load generated source in tests for digit-leading names and Python keywords. The scaffold's unconditional browser URL at [line 73](../../solid_node/manager/new.py#L73) also needs to reflect the documented OpenSCAD fallback and configured port.

## F09 — Multi-model tests stop on build failures despite the continuation contract

**Location:** [solid_node/manager/test.py:135–155](../../solid_node/manager/test.py#L135) and [205–214](../../solid_node/manager/test.py#L205).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`continue-all-model-tests-after-build-failure`. Each declared model's
preparation now has its own failure boundary covering load/construction,
initial keyframe binding, render, assembly, and artifact generation. A normal
failure is named and counted once, then the next model runs unless
`--failfast` is set; failfast records the failure and still reaches the one-run
report before exiting. Focused manager, named-model, and lock coverage passed
58 tests with 4 passing stage subtests. The saved public probe now reports
`second_ran: true`, one passed and one failed entry in its aggregate report,
and the expected exit status 1. The complete suite passed 1,624 tests with 16
skipped, 44 warnings, and 274 passing subtests. No new ADR was needed because
this makes the continuation rule already accepted in ADR-073 executable. The
original evidence below remains the pre-fix audit record.

The all-model selection phase catches reference-resolution errors, but the execution loop does not catch each model's construction, render, or assembly failure. `build_node()` either raises a normal exception or calls `self.fail()`, which raises `SystemExit`. The surrounding handler catches only `StopTestRun`.

**Reproduction:** Declare `broken` first and `good` second. Make `Broken.render()` raise `RuntimeError`; give `good` a test printing a marker. Run `solid test --all` without `--failfast`. It exits **1** with a traceback, prints no aggregate report, and never runs the second model's test.

**Impact:** One broken model prevents validation of the rest of a project. The [CLI contract](../../openspec/specs/cli/spec.md#requirement-test-command) explicitly says a model that fails to load or build must not stop the run unless `--failfast` is given.

**Recommended correction and proof:** Record build failures per model, continue the selection loop, and report once at the end. Add separate regressions for constructor, render, and artifact-generation failures, both with and without `--failfast`.

## F10 — Zero repeated children break the declarative render contract

**Location:** [solid_node/node/internal.py:40–49](../../solid_node/node/internal.py#L40) and [143–146](../../solid_node/node/internal.py#L143).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`support-empty-assemblies` and ADR-082. Declarative substitution now consults
class-level child metadata, so a zero repeat remains declared structure and
renders as `[]`. Internal composition carries zero children as an empty SCAD
group; a non-rigid assembly assembles and serializes with `children: []` and
produces no STL of its own. An empty rigid fusion is instead rejected during
validation with a diagnostic naming the fusion and its requirement for at
least one rigid child. Direct declarative coverage passed 20 tests, and the
focused lifecycle/document set passed 155 tests. The saved public probe's
zero-child build now exits 0 and records non-rigid STL generation as a no-op.
The complete suite passed 1,630 tests with 16 skipped, 44 warnings, and 274
passing subtests. The original evidence below remains the pre-fix audit
record.

`RepeatDeclaration.realize()` accepts zero, but `_declarative_render()` treats an empty realized child list as absence of declarations and returns `None` unchanged. The assembly validator then rejects it. A second empty-list failure exists downstream: `as_scad()` indexes `scads[0]` when there are no children.

**Reproduction:** Declare an assembly with:

```python
count = Count(0, min=0)
parts = Part().repeat(count)
```

Supply no `render()` method, as the declarative API permits. `solid build` exits **1** with `render() should return a list, not <class 'NoneType'>`.

**Impact:** A valid non-negative count cannot describe an absent optional group. The [declarative render requirement](../../openspec/specs/declarative-nodes/spec.md#requirement-an-internal-render-that-returns-nothing) says consumers must see the substituted child list, never `None`.

**Recommended correction and proof:** Distinguish declared structure from realized child count, and handle empty non-rigid assemblies throughout assembly and serialization. Test zero repeats and omission of every child. Decide and state separately whether an empty rigid fusion is meaningful.

## F11 — Invalid simulation time inputs can silently bypass checks

**Location:** [solid_node/simulation/sim.py:112–115](../../solid_node/simulation/sim.py#L112), [run()](../../solid_node/simulation/sim.py#L216), and [_ticks()](../../solid_node/simulation/sim.py#L243).

**Resolution:** Fixed on the `due-dilligence` branch by OpenSpec change
`validate-simulation-time-boundaries` and ADR-083. Simulation construction now
requires finite positive `dt` before binding a node. Every public time value
uses the same finite-real boundary, negative runs fail before effects, and
absolute scheduling rejects ticks already passed while preserving current-tick
execution through `run(0)`. Zero-duration instructions settle every target and
rebind the complete snapshot immediately without advancing time. The focused
simulation suite passed 38 tests with 28 subtests; broader simulation coverage
passed 68 tests with 28 subtests. The saved probe now rejects `dt=-0.1` and
observes the zero-duration target in both the bank and node at tick zero with
no trajectory entry. The complete suite passed 1,638 tests with 16 skipped,
46 warnings, and 302 passing subtests. The original evidence below remains
the pre-fix audit record.

The constructor accepts `dt` without validating positivity or finiteness. `_ticks()` checks alignment only, so a positive duration with negative `dt` becomes a negative number of ticks. `run()` then skips its stepping loop without reporting an invalid scenario.

**Reproduction:** Construct `Sim(node, dt=-0.1)`, schedule a check at `0.1`, and call `run(1)`. It returns normally with **tick 0**, **zero checks executed**, and the check stranded at tick **-1**.

**Impact:** A misconfigured scenario appears to complete while its scheduled checks never run. This undermines the simulation's role as a test mechanism.

**Recommended correction and proof:** Require a finite, positive `dt`, reject negative run durations, and state a policy for scheduling before the current tick. Test invalid time inputs at API boundaries. The evidence also records the current zero-duration instruction behavior; its intended same-tick semantics need clarification before treating it as another bug.

## Documentation and process inconsistencies

These are distinct from the reproduced implementation defects above.

### C01 — Assertion documentation promises more than vertex sampling proves

**Resolution:** Corrected on the `due-dilligence` branch. The assertion list
now says exactly that `assertInside`, `assertClose`, and `assertFar` sample the
second mesh's vertices against the first mesh. It calls out density,
direction, edge, face, and concavity limits; states that no whole-surface
containment assertion exists; and directs overlap, assembly-clash, and
connectivity questions to their whole-geometry assertions. The implementation
and test-framework contract were already consistent and did not change.

[docs/testing.rst:285–289](../testing.rst#L285) says `assertInside` proves complete containment and that `assertClose`/`assertFar` constrain every point. The [implementation](../../solid_node/test.py#L1263) samples only the second mesh's vertices, exactly as the [test-framework specification](../../openspec/specs/test-framework/spec.md#requirement-mesh-assertions) explicitly requires. Faces can cross a concavity or another object while their vertices satisfy the sampled predicate. This is an overstatement in the user documentation, not a claim that the implementation violates its present sampling spec. Describe the sampling limitation and direct whole-solid claims to suitable geometric assertions.

### C02 — Browser capture instructions omit the required opt-in

**Resolution:** Corrected on the `due-dilligence` branch. The contributor
README now gives the exact opt-in command and distinguishes an intentional
default skip from dependency failure after opt-in. GitHub Actions now has a
required browser-snapshot job that installs the viewer's snapshot extra and
Chromium, sets `SOLID_NODE_WEB_SNAPSHOT_E2E=1`, and runs the real transparent
capture test. The command passed locally against the installed viewer and
browser (1 test, 1 warning).

[README.rst:129–131](../../README.rst#L129) says browser snapshot tests are mandatory for renderer changes and that missing browser setup is reported as a failure rather than skipped. The actual [end-to-end test](../../tests/test_browser_renderer.py#L230) skips unless `SOLID_NODE_WEB_SNAPSHOT_E2E=1`, even when the viewer is installed. This audit observed that skip. The [CI test job](../../.github/workflows/python-app.yml) sets no such flag. Document the exact validation command and arrange for relevant changes to exercise it; a green default suite is not evidence of a real browser capture.

### C03 — The README overstates viewer process isolation

**Resolution:** Corrected on the `due-dilligence` branch. The README and
contributor briefing now describe the exact boundary: the framework imports
and calls only the viewer's lightweight entry-point provider to discover its
bundle metadata, while serving and browser capture run in separate processes
and their modules are not imported. This aligns the introductions with the
existing implementation, architecture synthesis, and viewer-distribution
contract.

The [README's viewer introduction](../../README.rst#L38) says the framework never imports the viewer. [bundle.describe()](../../solid_node/viewers/bundle.py#L50) calls `entry.load()()`, which imports and runs the viewer's entry-point provider in the framework process. The [viewer-distribution spec](../../openspec/specs/viewer-distribution/spec.md#requirement-the-framework-finds-the-installed-viewer-through-its-entry-point) explicitly permits this narrow import and forbids other viewer imports. Align the README with that actual boundary: entry-point metadata runs locally; serving and capture run in separate processes. This observation makes no licensing determination.

The CI lint job additionally marks both Black and Flake8 `continue-on-error: true`, so formatting and lint errors do not block the test/release chain. That is a process gap to assess, rather than evidence of a particular runtime defect.

## Recommended order of work

1. Address F01–F05 first, with the recorded failing paths as regressions. They affect published geometry, filesystem ownership, or concurrent artifact production.
2. Correct the reload, recovery, and multi-model test paths (F06, F07, F09), then the scaffold and declaration/time boundaries (F08, F10, F11).
3. Align the documentation with executable behavior and close the Sphinx/browser validation gaps before relying on release-readiness claims.

Each correction should follow the project's proposal and regression-evidence discipline. The passing baseline and the audit probes establish the starting point; they do not resolve these findings.
