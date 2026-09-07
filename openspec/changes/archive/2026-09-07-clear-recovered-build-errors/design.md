## Context

`errors.json` is the build directory's failure signal. A successful builder
constructs the complete viewer document in memory, compares it with the
published `viewer.json`, then clears the error immediately before atomically
writing a changed document. When the bytes match, the early return skips error
removal. The CLI still exits successfully, but directory-derived status remains
`failed`.

The return value of `_write_viewer_snapshot()` controls the build-ready
callback: it is false for an ordinary no-op and true when publication changed.
A recovery that removes `errors.json` changes externally visible publication
state even when geometry and document bytes are unchanged.

## Goals / Non-Goals

**Goals:**

- Remove a prior error only after load, assembly, artifact currency/rendering,
  and complete viewer-document construction have succeeded.
- Recover status even when the constructed document matches `viewer.json`.
- Preserve the byte-identical viewer document and avoid an unnecessary sweep
  on that recovery path.
- Notify a development callback when failure state changes to successful, and
  preserve the existing no-callback behavior for a true no-op with no error.
- Prove both direct publication ordering and the public CLI status transition.

**Non-Goals:**

- Change the `errors.json` schema or the directory-derived `solid models`
  states.
- Rewrite `viewer.json` merely to signal recovery.
- Notify on a successful no-op when no prior error exists.
- Change how failures are reported, retained, or displayed by a viewer.

## Decisions

### D1: Clear the error after document construction and before byte comparison

The builder will finish serialization and piece inventory construction first.
It will then remove any prior error and remember whether removal occurred
before deciding whether `viewer.json` needs replacement. This is the latest
common success point shared by changed-document and byte-identical builds.

Clearing immediately after node load was rejected because assembly, rendering,
or serialization can still fail. Clearing only when writing `viewer.json` is
the current defect.

### D2: Treat error removal as a publication-state change

`_write_viewer_snapshot()` will return true when it either publishes different
document bytes or removes a prior error. `_start()` already uses that result to
send the callback after releasing the project build lock, so recovery gains the
same ready notification without a second communication path.

Returning false after recovery was rejected because callback consumers would
not learn that a previously failed development build is now ready. Always
returning true for successful builds was rejected because it would violate the
established no-op behavior for repeated builds with neither content nor status
changes.

### D3: Keep the unchanged document untouched

If document bytes match after the error is cleared, the builder will return the
recovery result without rewriting `viewer.json` or sweeping artifacts. The
status transition needs only removal of `errors.json`; preserving the manifest
mtime and bytes keeps existing no-op and inventory guarantees.

### D4: Cover the public status consumer as well as the helper

A focused test will publish a document, add a prior error, invoke the snapshot
path again, and verify error removal, a true recovery result, and unchanged
manifest bytes and mtime. Lifecycle coverage will require one callback after
recovery and none for an ordinary no-op. A failure injected during document
construction will prove the error remains. The saved CLI probe will require a
successful rebuild to change `solid models --json` from `failed` to
`published`.

## Risks / Trade-offs

- **Removing an error changes state without rewriting the manifest.** → Status
  is already defined from the presence of `errors.json`; tests assert both the
  state transition and byte-identical manifest.
- **A callback consumer may receive the same geometry twice around a failure.**
  → The second notification carries meaningful recovery state; true no-op
  builds still send nothing.
- **An exception before complete document construction could clear too early.**
  → Error removal remains after serialization and inventory work, with a
  regression that forces construction to fail.

## Migration Plan

No migration is required. Existing stale error files clear on the next
successful build. Rollback restores the early-return defect but changes no
stored format.

## Open Questions

None.
