## Why

ADR-030 rejected rendering directly into the public build directory because
"readers can observe a mixed artifact set while a build is in progress". The
publication step it chose instead does not fully deliver that goal:
`BuildSessionPublisher.publish()` moves the build directory aside and then
moves the candidate into place, so between those two renames the build
directory **does not exist at all**.

Measured on the current implementation: a reader polling
`_build/viewer.json` observed it absent **228 times across 200 publications**
by a single publisher. A local consumer serving those artifacts over HTTP —
the case ADR-030 was written for — can return 404 for a model that is present
before and after.

The same two-step dance also collides when two publishers overlap, which
happens whenever a verification build runs beside a watch loop. Measured over
60 rounds of 3 concurrent publishers: **0 torn trees and 0 lost build
directories**, but **70 exceptions** — `Directory not empty` when the
candidate is moved onto a directory another publisher just created, and
`No such file or directory` when the build directory another publisher
already moved aside is moved again. `Builder._publish()` does not guard the
call, so the exception escapes the builder process: `solid build` exits
non-zero with a traceback for a model that built correctly.

## What Changes

- Publish by **atomically replacing a symlink**: the completed candidate
  becomes a versioned sibling directory, and the build path becomes a symlink
  swapped onto it with `os.replace`. A reader following the build path always
  reaches one complete artifact set.
- Use only `os.symlink` and `os.replace`, which are atomic on POSIX. **No
  platform-specific code, no `ctypes`, no syscall numbers** — the same code
  path runs on Linux and macOS.
- Migrate an existing real build directory to the symlink layout on the first
  publication after upgrade.
- Keep build artifacts invisible to Git without the user doing anything:
  `solid new` scaffolds a `.gitignore` that covers the new layout, and for an
  existing project the framework writes the pattern to `.git/info/exclude`
  **only when the project's `.gitignore` does not already cover it**.
- Report a publication that fails because another publisher won the race as a
  **build failure through the normal error channel**, not an escaping
  traceback.
- No change to the candidate-directory model, the seeding of a candidate from
  the last published build, `SOLID_BUILD_DIR` as the consumer-facing location,
  or the callback contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-pipeline`: the build artifact layout requirement describes a build
  directory; it becomes a symlink to a versioned directory. Add what a
  concurrent reader and a second publisher observe, and the Git-invisibility
  guarantee.
- `one-shot-build-and-notification`: the completion of `solid build` must not
  depend on winning a race with another publisher.

## Impact

- `solid_node/core/builder.py`: `BuildSessionPublisher.publish()`, the
  `Builder._publish()` call site's error handling, and a small helper that
  keeps the build path excluded from Git.
- `solid_node/manager/templates/project/gitignore`: `_build/` becomes a
  pattern that also covers the versioned directories.
- **BREAKING for direct consumers that require the build path to be a real
  directory.** It remains a directory for every ordinary use (`os.path.isdir`,
  reads, globs) but is a symlink to `realpath`, to `git`, and to archive
  tooling.
- Amends ADR-030's publication mechanism while keeping its boundary; an ADR
  recording the symlink-swap decision is expected.
- Downstream: solid-node-shop serves the build directory statically to a
  browser and is the reporting consumer for both defects.
