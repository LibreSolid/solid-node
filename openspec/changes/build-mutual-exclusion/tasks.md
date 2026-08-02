## 1. The lock itself

- [ ] 1.1 Red: a test that two processes cannot hold the project build lock at
      once, that the second acquires as soon as the first releases, and that a
      killed holder's lock is immediately available.
- [ ] 1.2 Red: a test that the lock path is derived from the published build
      directory (honouring `SOLID_BUILD_DIR`), never from a builder's staging
      directory, and that two projects with different build directories do not
      serialise.
- [ ] 1.3 Implement the build lock in `solid_node/core/builder.py`: a context
      manager over `fcntl.flock` on `<published build dir>.lock`, opening the fd
      inside the acquiring process, closing it on release, logging once when the
      lock is not immediately available, and safe to re-enter within a process.
- [ ] 1.4 Record the lock file in the repository's local exclude at creation
      time by reusing `exclude_build_from_git`, and assert the working tree
      stays clean in a project whose `.gitignore` predates the pattern.

## 2. The builder as a lock participant

- [ ] 2.1 Red: a `Builder` test that the lock is held across render and publish
      and released before `wait_for_change`, and that it is released when the
      build fails and the error is reported.
- [ ] 2.2 Implement acquisition in `Builder._start` after load and assemble, and
      release after publication or error reporting.
- [ ] 2.3 Red: a test that a builder child holding the lock does not leave it
      held by an inherited descriptor after the child exits, with `Build` and
      `Develop` spawning through `multiprocessing`.

## 3. The dedup rule

- [ ] 3.1 Red: a test that a builder whose tracked sources moved while it waited
      publishes nothing and reports the source-changed outcome.
- [ ] 3.2 Red: a test that a builder acquiring the lock against an already
      current published set renders nothing, publishes nothing, and reports the
      model current.
- [ ] 3.3 Red: the end-to-end ordering test — two builds raced with the stale one
      finishing last; the published model matches the newest source.
- [ ] 3.4 Implement the post-acquisition re-evaluation from `node.mtime`, the
      tracked source files on disk, and the published artifact set, adding no
      new metadata to any published artifact.
- [ ] 3.5 Confirm an ordinary uncontended build is unchanged: it renders,
      publishes, clears `errors.json`, and fires the build-ready callback as
      before.

## 4. Test runner and export

- [ ] 4.1 Red: a test that `solid test` builds under the lock and that the lock
      is free once test methods start running.
- [ ] 4.2 Implement the lock around `build_node` in `solid_node/manager/test.py`,
      releasing before `run_tests`.
- [ ] 4.3 Implement the lock around the `build_stls()` call in
      `solid_node/core/export.py`, releasing before the export directory is
      written, with a test that export does not hold the lock while writing.

## 5. Whole-system checks

- [ ] 5.1 Run the full framework test suite and `openspec validate --all
      --strict`.
- [ ] 5.2 Exercise a real project: `solid build` beside a running
      `solid develop --no-web` on `projects/v8-engine`, confirming no
      publication error, one model, and no leftover lock state.
- [ ] 5.3 Confirm nothing in this cycle changed the publication mechanism: the
      symlink swap, its race-tolerance behaviour, and `errors.json` handling are
      untouched, leaving them for F2 to replace.
