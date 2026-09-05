## 1. Prove the failure red

- [ ] 1.1 Add a test that starts a build subprocess from a parent that has
      already initialised a native worker team, and fails if the child does not
      reach its outcome within a bounded time — red under the current `fork`
      default, green under an isolated child.
- [ ] 1.2 Add a test asserting every subprocess target in `manager/build.py` and
      `manager/develop.py` survives being pickled — red today for the
      `Develop` targets, which carry an unpicklable `ArgumentParser`.
- [ ] 1.3 Confirm both tests fail for the stated reason before any source
      change, and record the failure output.

## 2. Isolate the build subprocess

- [ ] 2.1 Move `solid build`'s subprocess target to a module-level function
      taking the node reference and overrides as plain values.
- [ ] 2.2 Start it from an explicit `spawn` context, leaving the loop, its exit
      codes, and the `MODEL_NOT_FOUND` path unchanged.
- [ ] 2.3 Verify the entry point a spawned child re-imports is guarded, so the
      child does not re-run the CLI.

## 3. Isolate the develop subprocesses

- [ ] 3.1 Move the builder, OpenSCAD viewer, web viewer, and web dev-server
      targets to module-level functions taking plain values; keep the manager
      object in the parent.
- [ ] 3.2 Start every one of them from the same `spawn` context, preserving the
      watch loop's reload semantics, first-run failure handling, teardown of
      child processes, and `KeyboardInterrupt` behaviour.

## 4. Prove it green

- [ ] 4.1 Run the tests from task 1 and show them green.
- [ ] 4.2 Run the framework's build, builder, and manager test modules, then the
      full suite.
- [ ] 4.3 Build the originating project end to end from a genuinely cold build
      directory, in a parent that has already resolved the model, and confirm it
      publishes its artifacts and exits 0.
- [ ] 4.4 Measure the cold-build wall clock and the per-iteration cost against
      the pre-change baseline where the baseline can complete, and report the
      numbers. If the cost is unacceptable, stop and return the evidence to the
      pilot rather than reverting the isolation.

## 5. Record the decision

- [ ] 5.1 Extract an ADR for the subprocess isolation decision, update the ADR
      index, and update `docs/architecture.md` if the synthesis changed.
