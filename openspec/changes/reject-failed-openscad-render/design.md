## Context

OpenSCAD renders into a temporary sibling created by `mkstemp()`. The
`StlRenderStart.wait()` method currently ignores `Popen.wait()`'s result and
always calls `finish()`, which stamps and publishes that file. Due-diligence
finding F01 demonstrated that an OpenSCAD assertion exits nonzero but the
empty pre-created file is still published, the CLI exits zero, and
`viewer.json` advertises the bad artifact.

The builder already catches exceptions raised during `generate_stl()`, writes
them through `errors.json`, suppresses success notification, and returns the
failed lifecycle outcome. Per-artifact atomic publication from ADR-038 already
keeps the previous public STL readable until `finish()` replaces it.

## Goals / Non-Goals

**Goals:**

- Make the OpenSCAD subprocess result decide whether its staged STL may be
  published.
- Clean up the failed render's private output and lock.
- Preserve a previous public artifact and propagate failure through the
  builder's existing lifecycle.
- Prove both cold and replacement failures with the real OpenSCAD executable.

**Non-Goals:**

- Validate the geometry or binary structure of an STL from a renderer that
  exits successfully.
- Change successful render ordering, artifact names, build outcomes, or public
  APIs.
- Change JSCAD's separate synchronous, direct-to-target publication path.

## Decisions

### D1: `StlRenderStart.wait()` is the publication gate

`wait()` will read the integer returned by `Popen.wait()` and call `finish()`
only for zero. This keeps the verdict beside the only call that can publish the
temporary file, and covers the builder, `build_stls()`, and direct test helpers
without duplicating exit checks at each caller.

Checking the result in `Builder.generate_stl()` was rejected because
`AbstractBaseNode.build_stls()` and other callers also wait on render jobs.
Changing `finish()` to wait was rejected because tests and callers use it as
the already-successful publication operation.

### D2: A failed wait discards private state, then raises the standard process error

For a nonzero exit, `wait()` will remove the temporary file and per-STL lock,
then raise `subprocess.CalledProcessError` with the renderer's status and
command. The target STL and currency sidecar are not touched. The standard
exception carries a useful command and status while flowing through the
builder's existing generic failure path.

Returning a boolean was rejected because existing callers do not inspect a
return value and could repeat the original false-success bug. Publishing and
then validating was rejected because it would destroy the previous artifact
before the failure is known.

### D3: Regression coverage spans the job seam and the real CLI

A focused filesystem test will pin cleanup, exception propagation, and
preservation of an existing target. A real temporary project will use an
OpenSCAD `assert(false)` to prove a cold `solid build` exits nonzero without a
published STL or viewer snapshot, then change a successfully built model into
the failing source and prove its previous STL and snapshot remain byte-for-byte
unchanged while `errors.json` records the failure.

The real executable test matters because a mock can return a nonzero status
without proving OpenSCAD assertion behavior or the parent CLI's exit mapping.

## Risks / Trade-offs

- **A renderer can exit zero while producing invalid output.** This change
  deliberately trusts OpenSCAD's success status; validating STL contents is a
  separate policy with different cost and compatibility questions.
- **Cleanup itself can encounter an operating-system error.** Missing files
  are harmless and will be ignored; other cleanup errors still fail the build
  rather than allowing publication.
- **A failed replacement can leave newer `.scad` input beside the older STL.**
  That is already permitted by per-artifact publication; `errors.json` marks
  the failed build and the unchanged viewer snapshot continues to name the
  last completed artifact.

## Migration Plan

No migration is required. The change affects only failed OpenSCAD renders and
can be reverted by restoring the previous `wait()` implementation and tests.

## Open Questions

None.
