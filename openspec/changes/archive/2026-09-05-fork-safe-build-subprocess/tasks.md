## 1. Prove the failure red

- [x] 1.1 Add a test that starts a build subprocess from a parent that has
      already initialised a native worker team, and fails if the child does not
      reach its outcome within a bounded time — red under the current `fork`
      default, green under an isolated child.
- [x] 1.2 Add a test asserting every subprocess target in `manager/build.py` and
      `manager/develop.py` survives being pickled — red today for the
      `Develop` targets, which carry an unpicklable `ArgumentParser`.
- [x] 1.3 Confirm both tests fail for the stated reason before any source
      change, and record the failure output.

## 2. Isolate the build subprocess

- [x] 2.1 Move `solid build`'s subprocess target to a module-level function
      taking the node reference and overrides as plain values.
- [x] 2.2 Start it from an explicit `spawn` context, leaving the loop, its exit
      codes, and the `MODEL_NOT_FOUND` path unchanged.
- [x] 2.3 Verify the entry point a spawned child re-imports is guarded, so the
      child does not re-run the CLI.

## 3. Isolate the develop subprocesses

- [x] 3.1 Move the builder, OpenSCAD viewer, web viewer, and web dev-server
      targets to module-level functions taking plain values; keep the manager
      object in the parent.
- [x] 3.2 Start every one of them from the same `spawn` context, preserving the
      watch loop's reload semantics, first-run failure handling, teardown of
      child processes, and `KeyboardInterrupt` behaviour.

## 4. Prove it green

- [x] 4.1 Run the tests from task 1 and show them green.
- [x] 4.2 Run the framework's build, builder, and manager test modules, then the
      full suite.
- [x] 4.3 Build the originating project end to end from a genuinely cold build
      directory, in a parent that has already resolved the model, and confirm it
      publishes its artifacts and exits 0.
- [x] 4.4 Measure the cold-build wall clock and the per-iteration cost against
      the pre-change baseline where the baseline can complete, and report the
      numbers. If the cost is unacceptable, stop and return the evidence to the
      pilot rather than reverting the isolation.

      Measured on 3DPrintedClocks. Cold build, isolated: 93.3s wall, 124.4s
      user CPU, exit 0, 12 STLs and `viewer.json` published. Warm rebuild,
      isolated: 14.1s, exit 0. The pre-change baseline has no comparable
      number: on the same project it does not complete either build. It was
      killed after 203.5s with no artifact produced, its forked child at one
      thread in `futex_wait_queue` on 5s of CPU across 181s of wall clock.
      There is no workload on this project where the baseline finishes and
      the isolated build can be compared against it.

## 5. Record the decision

- [x] 5.1 Extract an ADR for the subprocess isolation decision, update the ADR
      index, and update `docs/architecture.md` if the synthesis changed.
