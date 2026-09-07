## Context

`prepare_build_dir()` supports the one-time transition from ADR-032's symlinked
publication layout to ADR-038's ordinary build directory. It correctly
identifies the active legacy directory through the build path's symlink, moves
that target into place, and then sweeps every other sibling whose name begins
with `<build-dir>.`. Due-diligence finding F02 demonstrated that the sweep
deletes unrelated `_build.notes` and `_build.backup` paths on every build.

The retired ADR-032 publisher generated version names with `tempfile`, but it
wrote no ownership marker. A name, directory shape, or contained artifact
cannot prove that an unreferenced sibling belongs to the framework. Browser
snapshot staging also deliberately uses a sibling named
`<build-dir>.web-snapshot.<token>` and remains live after releasing the build
lock while capture runs.

## Goals / Non-Goals

**Goals:**

- Preserve every path build preparation cannot prove it owns.
- Keep the one-time symlink-to-directory migration working for the exact
  directory referenced by the build path.
- Keep a browser snapshot stage readable while another build starts.
- Preserve existing build paths, locks, artifact publication, and Git
  exclusion behavior.

**Non-Goals:**

- Garbage-collect orphaned directories from the retired ADR-032 layout.
- Introduce a new cleanup command or ownership marker for historical paths.
- Change the browser renderer's staging location or lock duration.

## Decisions

### D1: Remove prefix-based sibling deletion

Ordinary preparation will create or reuse the build directory and touch no
sibling paths. During legacy migration it will move only the directory reached
through the build path's symlink. Once that target is renamed to the build
path, its old sibling pathname is already gone; no additional cleanup is
required for the migration to succeed.

Restricting deletion to directories, to names matching `tempfile`'s current
eight-character token, or to directories containing `viewer.json` was
rejected. Each remains circumstantial and can match user data, while historical
Python implementations are not a durable ownership protocol.

### D2: Preserve unreferenced legacy-looking directories knowingly

An orphaned `_build.<token>` can remain after migration. This is preferable to
deleting a path with no ownership proof. A future cleanup facility would need
an explicit user action or a marker written when the path is created; neither
can establish ownership retroactively for historical directories.

Keeping the broad sweep only while the build path is a symlink was rejected:
it narrows when data loss occurs but does not make any unreferenced sibling
safer to delete.

### D3: Test the browser interleaving at its staging boundary

The browser regression will create a real `BrowserRenderer.stage()`, call
`prepare_build_dir()` while that stage exists, and then read the staged
document and linked artifact. Chromium is unnecessary because the failure is
deletion before capture begins, not browser behavior.

A filename-only stand-in would cover the cleanup helper but would not prove
that the renderer's actual prefix and linked artifact survive.

## Risks / Trade-offs

- **Retired version directories may remain on disk.** → No safe automatic
  ownership test exists; preservation is the required direction for uncertain
  paths.
- **A user-created symlink at the configured build path is still treated as
  the build being migrated.** → This is the existing explicit build-path
  contract and outside F02's sibling sweep; the change neither broadens nor
  narrows it.
- **The browser regression depends on the optional viewer bundle for staging.**
  → The focused preparation tests remain unconditional; environments with the
  viewer installed exercise the real overlap, as the current baseline does.

## Migration Plan

No data migration is required. The next build still converts an ADR-032
symlink by moving its referenced directory into place. Other siblings remain
where they are. Reverting the code would restore deletion on preparation, so
rollback requires no data conversion but would reintroduce F02.

## Open Questions

None.
