## 1. Atomic artifact writes

- [ ] 1.1 Red: a reader polling an artifact across a rebuild never sees a
      partial file, and a reader holding an open artifact reads it to
      completion after it is replaced.
- [ ] 1.2 Implement the atomic write helper and use it for `.scad` and
      `viewer.json` in `solid_node/node/base.py` and
      `solid_node/core/builder.py`.
- [ ] 1.3 Red: a render leaves no partially written STL visible at the artifact
      path at any moment.
- [ ] 1.4 Point OpenSCAD at a temporary sibling and move it into place in
      `StlRenderStart.finish()`, keeping the source-mtime stamp so
      mtime-equality caching is unchanged.

## 2. One build directory

- [ ] 2.1 Red: a build writes into `_build` itself — no symlink, no versioned
      sibling, no candidate directory — and a consumer reaches artifacts
      without resolving anything.
- [ ] 2.2 Remove `BuildSession` and `BuildSessionPublisher`, and the
      candidate/published split in `Builder`, `Build` and `Develop`.
- [ ] 2.3 Red: a project whose build path is a symlink to a versioned directory
      is converted in place on the next build, and its versioned siblings are
      removed.
- [ ] 2.4 Implement the one-time migration under the project build lock.
- [ ] 2.5 Rewrite `tests/test_build_publication.py` around per-artifact
      atomicity, removing the symlink-swap tests with the mechanism they cover.

## 3. Ordering and sweeping

- [ ] 3.1 Red: an added node's artifact is readable before the snapshot naming
      it; a removed node's artifact is removed only after the snapshot that
      drops it.
- [ ] 3.2 Red: a renamed node leaves no artifact behind, and a failed build
      sweeps nothing.
- [ ] 3.3 Implement manifest-last publication and the manifest-driven sweep,
      confined to the build directory and sparing `.scad` inputs, live render
      locks and in-flight temporaries.

## 4. Error file lifecycle

- [ ] 4.1 Red: a successful build after a failure removes `errors.json`, and no
      consumer can observe a new model beside the previous build's error file.
- [ ] 4.2 Red: `errors.json` is never readable half-written.
- [ ] 4.3 Implement atomic error writing and clearing on successful
      publication, replacing the behaviour the candidate copy used to provide.

## 5. Architecture record

- [ ] 5.1 Write the BUILD record covering D1 and D2 as one decision, with the
      v8-engine measurement, the ADR-030 reversal argued head-on (complete set
      versus no torn reads), ADR-032 superseded, and ADR-018 shown not to be
      regressed.
- [ ] 5.2 Mark ADR-030 and ADR-032 as the new record directs, update the ADR
      index, and update `docs/architecture.md` where the synthesis changed.

## 6. Whole-system checks

- [ ] 6.1 Run the full framework test suite and `openspec validate --all
      --strict`.
- [ ] 6.2 Exercise a real project: edit one leaf of a multi-node project and
      confirm only that leaf's artifact is rewritten, with the rest of the
      build directory untouched.
- [ ] 6.3 Confirm a `solid test` sweep and a `solid develop` rebuild still
      interleave correctly under the F1 lock with the new layout.
