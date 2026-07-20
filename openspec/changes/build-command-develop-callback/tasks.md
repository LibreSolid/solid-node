## 1. Build lifecycle contract

- [ ] 1.1 Add red tests that distinguish intermediate render work, a fully
  current build, source-change exit, and failed build lifecycle outcomes.
- [ ] 1.2 Refactor the builder/lifecycle seam to expose a complete successful
  publication only after all ordinary model artifacts are current.
- [ ] 1.3 Stage and publish normal build-directory artifacts so a failed later
  attempt leaves the prior complete successful artifact state available.

## 2. One-shot CLI build

- [ ] 2.1 Add red CLI and manager tests for `solid build`, including shared
  directory-to-`__init__.py` resolution, no watcher/viewer, and successful
  completion only after the full model is published.
- [ ] 2.2 Implement and register the `Build` command using the ordinary
  project build directory and build pipeline.
- [ ] 2.3 Add red tests for a missing resolved model and implement the
  documented `MODEL_NOT_FOUND` exit code 66 and diagnostic.

## 3. Development callback

- [ ] 3.1 Add red `Develop` tests for callback mode validation and for passing
  callback configuration through normal-web builder lifecycles.
- [ ] 3.2 Implement `develop --callback URL` so the builder POSTs the exact
  supplied URL with no body after each complete successful publication.
- [ ] 3.3 Add red tests for initial and later successful callback delivery,
  callback timeout/non-success logging without retry, no callback on failure,
  and continued watch-loop operation.

## 4. Evidence and records

- [ ] 4.1 Update CLI and viewer/build documentation with `solid build`,
  `MODEL_NOT_FOUND` (66), callback mode restrictions, and the
  artifact-ready callback boundary.
- [ ] 4.2 Run focused CLI, manager, builder, and viewer tests red-first and
  then green; run the relevant full Python suite.
- [ ] 4.3 Inspect whether the implemented publication boundary changes the
  framework architecture materially; create and index an ADR only if it does.
