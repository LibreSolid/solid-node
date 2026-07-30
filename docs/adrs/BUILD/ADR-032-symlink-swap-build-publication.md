# ADR 032: Symlink-swap build publication

**Status:** Accepted

**Date:** 2026-07-30

**Origin:** solid-node-shop — reader-visible gap and publisher collisions
measured while designing a shop-owned model watcher

**Amends:** [ADR-030](ADR-030-complete-build-publication-boundary.md) — keeps
its boundary, replaces its publication mechanism

## Context

ADR-030 established the complete-build publication boundary and rejected
rendering directly into the public build directory because "readers can
observe a mixed artifact set while a build is in progress". Its
implementation replaced the build directory in two renames: move the existing
directory aside, then move the completed candidate into place.

That leaves the build path unbound between the two renames. Measured on the
implementation as it stood: a reader polling the published viewer snapshot
found it **absent 228 times across 200 publications** by a single publisher.
A local consumer serving those artifacts over HTTP — the case ADR-030 was
written for — can return 404 for a model present before and after.

The same two renames collide when publishers overlap, which happens whenever
a verification build runs beside a watch loop. Over 60 rounds of 3 concurrent
publishers: **0 torn trees, 0 lost build directories, 70 exceptions** —
`Directory not empty` when the candidate is moved onto a directory another
publisher just created, `No such file or directory` when the build directory
another publisher already moved aside is moved again. `Builder._publish()`
did not guard the call, so the exception escaped the builder process and
`solid build` exited non-zero with a traceback for a model that built
correctly.

The tree-integrity half of ADR-030 held. The reader-facing guarantee it was
designed to provide did not.

No POSIX operation renames a directory onto a non-empty directory —
`os.replace` reports `ENOTEMPTY` — so the two-step dance was not an
implementation slip but the only pure-`os` way to replace a directory.

## Decision

Publish by **atomically replacing a symlink**. The completed candidate is
renamed to a versioned sibling of the build path, a symlink to it is created
at a temporary path, and that symlink is moved onto the build path with
`os.replace`. The build path is therefore a symlink to
`<build>.<token>`, and every publication rebinds it in one atomic step.

A publication removes only the versioned directory it superseded, never a
sibling, so a concurrent publisher's fresh tree survives. A build path that
is still a plain directory — a project built before this decision — is
migrated once: moved aside, then replaced by the symlink. That single
publication is not atomic; every later one is.

A publication that loses a race is reported through the ordinary build error
channel (`errors.json` and the failure outcome) rather than raising out of
the builder process. The winner left a complete artifact set behind, which is
a correct state for every reader.

Build artifacts stay invisible to Git without user action: the project
template ignores `<build>*`, and for a project whose `.gitignore` does not
already carry that pattern the framework records it in `.git/info/exclude`.

Measured on this decision: **0 missing reads and 0 publisher exceptions
across 300 concurrent publications by 3 workers.**

## Alternatives considered

- **`renameat2` with `RENAME_EXCHANGE`.** Atomically exchanges two
  directories, closing both defects with no symlink and no visible layout
  change. Rejected: Linux-only. macOS needs a different symbol
  (`renamex_np` with `RENAME_SWAP`), so reaching either means `ctypes` and a
  per-OS branch. The framework does not want architecture-dependent code,
  and this would add friction to a future macOS port.
- **Advisory publication lock** — `fcntl.flock`, or a PID lock file
  following the existing `.stl.lock` idiom. Portable and POSIX, and it fixes
  the collisions. Rejected as insufficient: it cannot close the reader gap,
  because readers do not take the lock and a browser cannot be made to.
- **Guard `_publish()` and accept both defects.** Removes the traceback
  only; the gap and the collisions remain.
- **Write the ignore pattern into `.gitignore`.** Durable across clones, but
  `.gitignore` is tracked: writing to it during a build dirties the working
  tree at an arbitrary moment and can be swept into an unrelated commit.

## Consequences

- A reader following the build path always reaches one complete artifact set.
- Overlapping publications settle on one of them instead of failing a build
  that succeeded.
- One code path serves every POSIX platform; nothing here is Linux-specific.
- **The build path is a symlink.** It still behaves as a directory for
  `os.path.isdir`, reads, and globs, but is visibly a symlink to `realpath`,
  to Git, and to archive tooling. Consumers requiring a real directory are
  affected.
- A consumer that resolves the build path twice within one operation can
  straddle a swap and see two different targets; resolving once per operation
  avoids it.
- `.git/info/exclude` is per-clone, so a project that predates this decision
  and is cloned elsewhere shows untracked build artifacts there until one
  ignore line is added. Projects scaffolded after it are unaffected.
- A process that dies between the swap and the cleanup leaves a
  `<build>.<token>` directory behind — the same exposure as the previous
  `.solid-node-previous-*` directories.
