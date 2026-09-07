## Why

Due-diligence finding F02 reproduced `prepare_build_dir()` deleting arbitrary
files and directories merely because their names begin with `<build-dir>.`.
Build preparation must not erase paths it cannot prove the framework owns, and
the same sweep can currently delete a browser snapshot stage still in use.

## What Changes

- Stop sweeping prefix-matching siblings during ordinary build preparation.
- When migrating an ADR-032 symlink layout, move only the build path's
  referenced target into the ordinary build directory.
- Preserve every other sibling, including user files, backup directories,
  unreferenced legacy-looking directories, the project lock, and active
  browser snapshot stages.
- Accept that an orphaned directory from the retired symlink layout can remain
  on disk because its name alone is insufficient proof of ownership.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: constrain legacy build-directory migration to the
  referenced symlink target and make sibling preservation explicit.

## Impact

- `solid_node/core/builder.py`: remove the unbounded sibling sweep and its now
  unused filesystem-removal dependency.
- `tests/test_build_publication.py`: cover ordinary preparation, symlink
  migration, build-lock preservation, and unrelated sibling paths.
- `tests/test_browser_renderer.py`: prove a staged browser snapshot survives
  overlapping build preparation after the snapshot releases the build lock.
- `docs/changelog.rst` and the due-diligence remediation records describe the
  corrected ownership boundary.
- The independent `solid-node-viewer` repository is not changed in this
  framework cycle; `PROGRESS.md` will retain a cross-repository follow-up to
  audit capture behavior when its input stage disappears unexpectedly.
- No command syntax, artifact layout, or successful build output changes.
