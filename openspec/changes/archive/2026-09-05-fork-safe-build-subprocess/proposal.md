## Why

`solid build` hangs forever on a cold build directory for any project whose
model is built with CadQuery nodes. It is not slow — it stops, at 0% CPU, and
never returns.

The cause is a fork-after-threads deadlock. `Build.handle()` resolves the model
in the parent process to distinguish `MODEL_NOT_FOUND`, and importing the model
runs OCCT geometry, which spins up native OpenMP worker pools. Measured on the
3DPrintedClocks project: a bare interpreter has 1 thread, and 46 after
`resolve_node()` alone. The build work then runs in a `multiprocessing.Process`,
which on Linux defaults to `fork`. `fork()` copies the address space but not the
threads, so the child inherits libgomp bookkeeping describing a worker team that
does not exist in it. The first OCCT operation that parallelises — tessellation
during STL export — waits on that team's barrier and never wakes.

Reproduced deterministically in that project: a forked child builds a trivial
`box().fillet()` in 0.0s, then hangs indefinitely in `exportStl` at
`futex_wait_queue`. The same child under the `spawn` start method exports in
0.1s and exits 0. A live hung build showed exactly this signature — one thread,
`futex_wait_queue`, four seconds of CPU across forty minutes of wall clock, no
subprocess of its own, no lock held.

The defect is invisible whenever a project's artifacts are already current,
because the child then reports `CURRENT` without tessellating anything. That is
why one project in the workspace opens normally and another never finishes: not
a difference in their models, a difference in whether their build directory was
cold.

## What Changes

- Builder subprocesses started by `solid build` no longer inherit the parent
  process's native runtime state. They start from a fresh interpreter, so no
  build depends on which libraries the parent happened to have initialised.
- `solid develop` starts its builder, viewer, and web-server subprocesses on
  the same footing, closing the identical latent deadlock in its watch loop.
- No change to node authoring, the build artifact layout, caching, locking,
  exit codes, or the callback protocol.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-pipeline`: adds a requirement that the subprocess a build runs in is
  isolated from the parent process's native runtime state, so a build completes
  or fails rather than deadlocking on inherited thread-pool state.

## Impact

- `solid_node/manager/build.py` — the `solid build` loop.
- `solid_node/manager/develop.py` — the `solid develop` process fan-out and
  watch loop.
- Subprocess targets and their arguments must survive being sent to a fresh
  interpreter, which constrains what a process target may close over.
- Build wall-clock cost: a fresh interpreter re-imports the geometry stack and
  the project per render iteration instead of inheriting them. The
  implementation must measure this against a real multi-part project and report
  it.
- Originating evidence: project 3DPrintedClocks
  (`design/wall_clock_01`, `CadQueryNode`), opened through the shop floor.
