## Context

The project lock already spans build-directory preparation, asynchronous STL
generation, viewer-document publication, and export's `build_stls()`. It does
not span `Builder._start()`'s earlier `node.assemble()` or the test runner's
`set_keyframe()` / `render()` / `assemble()` sequence. Assembly is not a pure
tree operation: `ExactLeafNode.as_scad()` writes BREP and STL files,
`StlNode.as_scad()` materializes its selected mesh, and every assembled node
writes SCAD. The saved F04 probe held `_build.lock` and observed a real
CadQuery STL appear while the builder was supposedly blocked.

The build-pipeline specification and ADR-032 already define one critical
section for every framework artifact producer. Snapshot and export enter it
before assembly. This change brings the ordinary builder and test runner into
conformance without changing the lock file or advisory-lock mechanism.

## Goals / Non-Goals

**Goals:**

- Prevent ordinary builds and test setup from rendering or publishing any
  framework artifact before they own the selected project's lock.
- Hold one uninterrupted builder critical section from assembly through
  artifact and viewer-document publication.
- Preserve stale-loaded-build rejection when a process waits for the lock.
- Release the lock before callbacks, source-change waits, and user test cases.
- Exercise both exact and imported-file assembly-time producers.

**Non-Goals:**

- Lock arbitrary side effects in project constructors or user test methods.
- Change per-STL render locks, atomic file replacement, or build layout.
- Move project loading under the lock when loading only imports and constructs
  the framework node tree.
- Change export or snapshot, whose artifact-producing phases are already
  correctly locked.

## Decisions

### D1: Move assembly inside the builder's existing critical section

`Builder._start()` will load the node and capture its source timestamp before
acquiring the lock. After acquisition it will prepare the build directory,
reject a source state that changed while waiting, assemble the node, and then
continue directly through currentness checks, STL generation, and viewer
publication without releasing and reacquiring the lock. It will compare the
source timestamp again after assembly, catching an edit during that phase
before later publication.

Adding a second lock only around `assemble()` was rejected because another
builder could render and publish in the gap before this builder reacquired the
lock. Moving only the exact adapter's writes was rejected because STL imports
and ordinary SCAD generation share the same lifecycle boundary, and future
adapters would repeat the omission.

### D2: Start watching after successful assembly while still locked

A precise watch needs the complete union of source files learned while the
tree assembles. After assembly and the second timestamp check, a watching
builder will schedule those files and start its observer before generating or
publishing further artifacts. The observer is stopped by the existing process
lifecycle, and the builder releases the project lock before awaiting its
future.

Starting a broad observer before assembly was rejected because successful
builds already know the precise source set and should retain targeted watches.
Starting the observer only after publication was rejected because it could
miss an edit made during a longer STL render; the source-event future must be
active by then.

### D3: Defer assembly failure handling until after lock release

An assembly exception will be captured inside the critical section and passed
to the existing `_on_reload_exception(..., 'assemble')` path after leaving it.
That path may start a broad watch and wait for a repair during develop, so it
must not retain the lock. The exception object and traceback remain available
because `_on_reload_exception` is invoked from the surrounding exception
handler after the context manager unwinds.

Calling the existing async error handler from inside the lock was rejected:
on a reload it waits indefinitely for a file change and would block every
other project producer.

### D4: Lock the test runner's complete build phase once

`Test.build_node()` will acquire `project_build_lock()` before setting the
keyframe and invoking the preliminary render, and will keep it through
`assemble()` and `build_stls()`. It returns the built node only after release,
so discovery and execution of project test cases remain outside the lock.

Keeping only `build_stls()` locked was rejected because it is the current bug.
Separate locks around render/assembly and `build_stls()` were rejected because
they create an unnecessary interleaving within one test setup.

### D5: Test phase ownership and real filesystem contention

The existing lock participant tests will observe lock state in builder
assembly and every test-runner build phase, plus release before callbacks,
watch waits, and test execution. Process-level regressions will hold the real
project lock, start a cold CadQuery build and a cold `StlNode` test build, and
assert that no BREP, STL, or SCAD artifact appears until release. They will
then release the holder and require successful completion and valid artifacts.

Mocks alone were rejected because F04 depends on writes hidden inside real
adapter assembly. Testing only CadQuery was rejected because the same defect
exists in imported-file materialization without an exact backend.

## Risks / Trade-offs

- **Assembly lengthens lock hold time.** → That time already produces the
  artifacts the lock promises to serialize; independent model directories
  retain independent locks.
- **A source edit while a builder waits can cause an extra retry before any
  assembly.** → This is the existing newest-source-wins policy and prevents an
  old imported class from stamping artifacts with a new file timestamp.
- **An assembly failure can leave earlier atomic artifacts from the same tree.**
  → They were already possible, but are now serialized; existing currency and
  error publication behavior remains responsible for the next attempt.

## Migration Plan

No data migration is required. Lock paths and artifact formats do not change.
Rollback restores the earlier critical-section boundary and therefore the F04
race.

## Open Questions

None.
