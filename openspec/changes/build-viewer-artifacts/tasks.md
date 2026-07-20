## 1. Red-first build publication proof

- [ ] 1.1 Add a failing lifecycle/CLI test proving a successful `solid build` publishes a complete viewer snapshot with build-relative model paths.
- [ ] 1.2 Add a failing viewer test proving the private NodeAPI can serve that snapshot without invoking the project loader.
- [ ] 1.3 Add a failing failure-path test proving a later unsuccessful build preserves the preceding snapshot and no callback is emitted.

## 2. Complete viewer artifacts

- [ ] 2.1 Implement builder-side serialization of the assembled recursive viewer state into the staging build directory after all model artifacts are current.
- [ ] 2.2 Publish the viewer snapshot atomically with the normal build directory and preserve it on failed later builds.
- [ ] 2.3 Refactor private NodeAPI/viewer state serving to support the published snapshot and build-root-relative STL files without project import.

## 3. Verification and records

- [ ] 3.1 Turn the focused red tests green and run the relevant builder, CLI, and web-viewer suites.
- [ ] 3.2 Verify the originating shop-floor caller can consume a completed `_build` snapshot after `solid build` and a development callback.
- [ ] 3.3 Assess the publication boundary for an ADR and update the architecture record if the implemented decision is consequential.
