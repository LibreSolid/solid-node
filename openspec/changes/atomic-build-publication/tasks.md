## 1. Red: reader never sees a missing build path

- [ ] 1.1 Add `tests/test_build_publication.py` with a test that polls the
      published viewer file from a reader thread across repeated
      publications and asserts it is never absent.
- [ ] 1.2 Run it and observe it fail on the current two-rename publisher,
      recording the observed absence count.

## 2. Red: overlapping publications

- [ ] 2.1 Add a test that runs concurrent publishers against one build path
      and asserts no publisher raises and the final tree comes wholly from
      one publisher.
- [ ] 2.2 Add a test that a publication losing the race is reported as a
      build failure through `errors.json` rather than escaping
      `Builder._publish()`.
- [ ] 2.3 Add a test that a publisher removing its superseded artifact set
      does not remove a concurrent publisher's fresh one.
- [ ] 2.4 Run all three and observe them fail.

## 3. Red: Git invisibility

- [ ] 3.1 Add a test that a project whose ignore file does not cover the
      versioned directories gets the pattern recorded in the repository's
      local exclude file, with the tracked ignore file unmodified.
- [ ] 3.2 Add a test that a project whose ignore file already covers them
      gets no local exclusion written.
- [ ] 3.3 Add a test that a missing or unwritable git directory is ignored
      and publication still succeeds.
- [ ] 3.4 Run them and observe them fail.

## 4. Implement publication

- [ ] 4.1 Rewrite `BuildSessionPublisher.publish()`: rename the completed
      candidate to a versioned sibling, create a symlink to it at a temporary
      path, and `os.replace` that symlink onto the build path.
- [ ] 4.2 Migrate a build path that is still a plain directory: move it aside
      once, install the symlink, then remove the moved directory.
- [ ] 4.3 Remove only the versioned directory this publication superseded;
      never sweep siblings.

## 5. Implement Git invisibility

- [ ] 5.1 Add a helper that records `<build-basename>*` in
      `.git/info/exclude` when the project's `.gitignore` does not already
      contain that pattern, acting only when `.git` is a real directory and
      ignoring every failure.
- [ ] 5.2 Call it from publication, idempotently.
- [ ] 5.3 Update `solid_node/manager/templates/project/gitignore` so new
      projects cover the build path and its versioned directories.

## 6. Implement the failure channel

- [ ] 6.1 Guard the `Builder._publish()` call site so a publication error
      becomes a reported build failure via the existing error path instead of
      an escaping exception.
- [ ] 6.2 Confirm a failed publication leaves the other publisher's complete
      tree untouched.

## 7. Green and regression

- [ ] 7.1 Run the new publication and Git-invisibility tests green, including
      the reader-gap test that previously counted absences.
- [ ] 7.2 Run `tests/test_builder_lifecycle.py`, `tests/test_manager_build.py`,
      `tests/test_manager_develop.py` and `tests/test_export.py` green.
- [ ] 7.3 Run the full framework suite and report the result.
- [ ] 7.4 Verify by hand in this worktree that a real `solid build` publishes
      through the symlink, that `solid develop --no-web` still rebuilds on
      edit, and that `git status` in a scaffolded project stays clean.
- [ ] 7.5 Verify by hand that a project built under the old layout migrates on
      its first publication.

## 8. Records

- [ ] 8.1 Write an ADR under `docs/adrs/BUILD/` recording the symlink-swap
      publication decision, the rejected `renameat2` and lock alternatives,
      and the Git-exclusion choice; mark its relationship to ADR-030 and
      update `docs/adrs/README.md`.
- [ ] 8.2 Update `docs/architecture.md` if the publication description there
      no longer matches.
- [ ] 8.3 Note the build-path layout change in `HISTORY.rst`, including that
      a pre-existing project cloned elsewhere may need one ignore line.
- [ ] 8.4 Sync the `build-pipeline` and `one-shot-build-and-notification`
      baseline specs and archive the change.
