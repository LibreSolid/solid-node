# ADR-084: One Fresh Builder per Sealed Source Generation

**Status:** Accepted
**Date:** 2026-09-07
**Change:** `bound-framework-performance-costs`
**Amends:**
- [ADR-067: Fresh-Interpreter Build Subprocesses](ADR-067-fresh-interpreter-build-subprocesses.md)
**Depends on:**
- [ADR-038: Per-Artifact Atomic Build Publication](ADR-038-per-artifact-atomic-build-publication.md)
- [ADR-081: Per-Contributor Metadata Guards Aggregate-Mtime Currency](../NODE/ADR-081-per-contributor-metadata-guards-aggregate-mtime-currency.md)
**Related to:**
- [ADR-005: Path-Based Dynamic Module Loading](ADR-005-path-based-dynamic-module-loading.md)
- [ADR-073: Named Project Models and Per-Model Build Directories](ADR-073-named-project-models-and-per-model-build-directories.md)

## Context and Problem Statement

ADR-067 made every build iteration a spawned fresh interpreter. That fixed a
native deadlock: a forked child inherited OCCT/OpenMP bookkeeping without the
threads that bookkeeping named. Process death also cleared project-module state
between reload attempts. Both outcomes are load-bearing.

The iteration boundary was more frequent than either guarantee requires. A
cold model needing many sequential artifact renders paid the Python, framework,
CAD-stack and project import cost once per artifact. The performance audit's
P01 fixture needed 25 builder children for one unchanged 24-artifact source
state: 24 render passes and the final current/publication pass. A single
source generation could instead safely retain its loaded tree, but only if the
framework could prove that the live classes and every source consumed by
assembly still represented disk.

Maximum mtime cannot provide that proof. ADR-081 already established that one
contributor may change beneath an unchanged aggregate maximum. Python's
timestamp-and-size bytecode validation is weaker again: a same-size edit with a
restored mtime can execute stale bytecode. Foreign SCAD, JavaScript, STL and
STEP inputs may also be discovered only while assembly runs.

## Decision Drivers

- Every generation must start with fresh native and project-module state.
- Loaded classes must be tied to the exact source bytes Python executed.
- A retained tree must stop before stale geometry or a stale manifest is
  published when any contributor changes.
- Stable multi-artifact builds should pay one import, construction and full
  assembly, not one of each per artifact.
- The F04 project lock, reconstructable process targets, failure outcomes and
  reload-recovery behavior must remain intact.

## Considered Options

1. **One fresh spawned builder per sealed source generation** (chosen)
2. Keep one spawned process per artifact iteration
3. Use `fork` or a preloaded `forkserver`
4. Keep one persistent worker across source edits or failures
5. Identify a generation only by aggregate maximum mtime

## Decision Outcome

A spawned builder owns one **sealed source generation**. Project-local loading
uses a coherent source loader: it observes the entry/facade and each newly
imported project module before execution, compiles the observed bytes rather
than trusting timestamp-and-size bytecode freshness, and requires the
post-load identity to match. External-library import behavior is unchanged.

The generation retains the spelling-to-canonical-path mapping and observable
identity of imported, coherently read and producer-declared contributors. A
request-local source census resolves and stats each distinct path once within
one phase, and reads or digests it at most once when requested. Every
artifact-producing phase takes a fresh pre-observation
and an uncached post-check. Assembly incorporates its recursively discovered
Python and foreign contributors; later artifact passes, asynchronous renderer
waits and document publication compare fresh observations with the generation
they continue. A coherently imported or read contributor may join while work is
still being discovered. A known path that is missing, replaced, retargeted or
changed, or a producer contributor first appearing only after its work or the
assembly seal, ends the worker with `SOURCE_CHANGED`.

Within that stable generation, the child constructs one root and performs one
full structural render and assembly. It may continue sequential pending
artifact passes on the same memoized tree until the model is current. It does
not re-import, reinstantiate, structurally re-render, reassemble or reorder
exact fusion between passes.

The child still begins through the explicit spawn context with a module-level
target and plain reconstructable values. Its loaded generation and tree are
never reused after a source change or for a new build attempt. A one-shot
failure and initial development failure retain their existing failed outcomes.
A failed development reload is the narrow lifecycle exception: that worker
records the error, releases the project lock, performs no more geometry, stays
alive only to watch the known source locations plus the existing broad Python
area for repair, and then exits `SOURCE_CHANGED` so the supervisor starts
another fresh interpreter.

The project build lock remains continuous only around assembly, artifact
production and publication. Watches, callbacks and project tests remain
outside it. This amends ADR-067's process-per-iteration mechanism, not its
fresh-native-state, reconstructable-target, failure-isolation or reload-reset
outcomes.

## Consequences

- A stable multi-artifact build amortizes interpreter and project startup and
  preserves one coherent in-memory assembly across its artifact passes.
- Source correctness now has an explicit generation and phase boundary rather
  than depending on aggregate mtime or post-load discovery.
- The worker may live across several sequential artifact renders and, in
  development, the ordinary watch wait until a source change. The project lock
  covers only assembly, artifact work and publication; it is released before
  callbacks, watch/recovery waits and project tests.
- Each fresh phase still pays an uncached distinct-source observation. The
  census removes overlapping work inside a phase; it is not a persistent
  source cache.
- A source race may discard completed private work and start over in a new
  process. That is the intended cost of refusing stale publication.
- The implementation adds project-local import instrumentation, but does not
  change ordinary imports outside the project root or publish source identity
  in viewer documents.

## References

- `solid_node/source_generation.py`
- `solid_node/core/loader.py`
- `solid_node/core/builder.py`
- `solid_node/manager/build.py`
- `tests/test_source_generation.py`
- `tests/test_retained_builder_generation.py`
- [Archived change](../../../openspec/changes/archive/2026-09-08-bound-framework-performance-costs/)
