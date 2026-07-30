## Context

`BuildSessionPublisher.publish()` installs a completed candidate in two
renames:

```python
if os.path.lexists(self.build_dir):
    previous = tempfile.mktemp(prefix='.solid-node-previous-', dir=...)
    os.replace(self.build_dir, previous)      # (1) build dir now absent
try:
    os.replace(self.staging_dir, self.build_dir)   # (2)
except Exception:
    if previous is not None and not os.path.lexists(self.build_dir):
        os.replace(previous, self.build_dir)
    raise
```

Two defects follow, both measured against the current implementation:

- Between (1) and (2) the build directory does not exist. A reader polling
  `_build/viewer.json` saw it absent 228 times across 200 single-publisher
  publications.
- Two publishers interleaving across (1) and (2) collide. Over 60 rounds of 3
  concurrent publishers: 0 torn trees, 0 lost build directories, 70
  exceptions. `Builder._publish()` does not guard the call, so the exception
  escapes the builder process and `solid build` exits non-zero with a
  traceback for a model that built correctly.

The tree-integrity half of ADR-030 holds. What is missing is the reader-facing
guarantee that ADR-030's own rejected alternative was rejected for.

The dance exists because no POSIX operation renames a directory onto a
non-empty directory: `os.replace` reports `ENOTEMPTY` (errno 39, verified).

## Goals / Non-Goals

**Goals:**

- A reader sees the previous complete build or the next complete build, never
  nothing.
- Overlapping publications settle on one complete artifact set without
  failing a build that succeeded.
- One code path on Linux and macOS. No platform detection, no `ctypes`.
- Build artifacts stay invisible to Git with no user action.

**Non-Goals:**

- Serializing *builds*. Two builders may still do duplicate work; only
  publication is made safe.
- Windows support for the atomic path (symlink creation there needs
  privilege). Windows is not supported today either.
- Changing the candidate model, seeding, the consumer-facing build path,
  the callback contract, or `.stl.lock` render locking.
- Choosing a winner between two genuinely different concurrent builds.

## Decisions

**Decision: swap a symlink, not the directory.**

The completed candidate is renamed to a versioned sibling
(`<build>.<token>`), a symlink to it is created at a temporary path, and that
symlink is moved onto the build path with `os.replace` — atomic on POSIX,
including macOS. The previous versioned directory is then removed.

Measured on this approach: **0 missing reads and 0 publisher exceptions
across 300 concurrent publications by 3 workers.** Both defects close.

Alternatives considered:

- **`renameat2` with `RENAME_EXCHANGE`.** Atomically exchanges two
  directories, closing both defects without a symlink. Rejected: it is
  Linux-only, macOS needs a different symbol (`renamex_np` /`RENAME_SWAP`),
  and reaching either requires `ctypes` and a per-OS branch. That is
  architecture dependence the framework does not want, and it would add
  friction to a future macOS port.
- **Advisory publication lock** (`fcntl.flock`, or a `.publish.lock` PID file
  following the existing `.stl.lock` idiom). Portable and POSIX, and it fixes
  the collisions — but it cannot close the reader gap, because readers do not
  take the lock.
- **Guard `_publish()` and accept both defects.** Removes the traceback only.

**Decision: the build path becomes a symlink, and that is a visible change.**

It still behaves as a directory for `os.path.isdir`, reads, and globs. It is
visibly a symlink to `realpath`, to `git`, and to archive tooling. The cost is
accepted here rather than hidden: the alternative that avoids it is the
platform-specific one.

**Decision: keep Git unaware, without touching a tracked file.**

Git's `_build/` pattern does not match a symlink, so an unmodified project
would show `?? _build` and `?? _build.<token>` — and `git add -A` would stage
the build artifacts (verified). Two paths keep that invisible:

- **New projects:** the scaffold template ignores `<build>*`, covering both
  the symlink and the versioned directories.
- **Existing projects:** the framework writes that pattern to
  `.git/info/exclude`, and **only when the project's `.gitignore` does not
  already cover it**.

`.git/info/exclude` is used rather than `.gitignore` because `.gitignore` is
tracked: writing to it during a build dirties the working tree at an arbitrary
moment, which contradicts the shop machinist's rule to stop on unrelated dirty
changes, and risks the edit being swept into an unrelated commit.
`.git/info/exclude` produces no status change and cannot be committed.

**Decision: the Git helper fails silently and does nothing clever.**

It acts only when `.git` is a real directory — skipping worktrees and
submodules, where `.git` is a file — so no `git` subprocess enters the build
path. Coverage is detected textually by looking for the pattern in
`.gitignore`; a project that ignores builds by some other means gets a
redundant but harmless exclude line. Writing is idempotent, and any failure
(no git, no permission, read-only) is ignored: the publication still works and
the only consequence is untracked noise.

**Decision: a lost race is a build failure, not an exception.**

`Builder._publish()` gets the same treatment as a failed render: the error
goes through `report_error`/`errors.json` and the ordinary outcome codes. A
publication that loses a race leaves the winner's complete tree in place,
which is a correct state for every reader — so it is reported, not retried.

## Risks / Trade-offs

- **A pre-existing project cloned to another machine keeps showing untracked
  build artifacts**, because `.git/info/exclude` is per-clone. → Inherent to
  not touching a tracked file. One line of `.gitignore` fixes it, and new
  projects are unaffected.
- **The migration publication is not atomic.** The first publish after upgrade
  finds a real directory at the build path and must move it aside before
  installing the symlink, reopening the reader gap exactly once per project.
  → Accepted; every later publication is atomic.
- **Consumers that resolve the build path may see a changed target
  mid-request.** A consumer that calls `realpath` twice within one operation
  can straddle a swap. → Consumer-side concern; the shop's artifact route is
  the known case and is handled there, not here.
- **Crash leftovers.** A process that dies between the swap and the cleanup
  leaves a `<build>.<token>` directory behind. → Same exposure as today's
  `.solid-node-previous-*`; a publisher removes only the directory it
  replaced, never a general sweep, so it cannot delete a concurrent
  publisher's fresh tree.
- **Last-writer-wins remains** between two genuinely different concurrent
  builds. → Out of scope; the framework has no notion of which is newer.

## Migration Plan

Automatic and per project, on the first publication after upgrade: the real
build directory is replaced by a symlink to a versioned directory, and the
Git exclusion is written if `.gitignore` does not already cover it. No user
action. Rollback is reverting the commit; a project left with a symlinked
build path is repaired by deleting it, since the next build republishes.

## Open Questions

None.
