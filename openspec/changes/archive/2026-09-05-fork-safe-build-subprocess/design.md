## Context

`solid build` and `solid develop` both run their real work in
`multiprocessing.Process` children and read the outcome from the child's exit
code. On Linux `multiprocessing` defaults to the `fork` start method, so those
children are copies of the command process taken after it has already imported
the geometry stack and, in `build`'s case, already resolved — and therefore
imported and executed — the project's model module.

Measured in the originating project, importing the model takes a bare
interpreter from 1 thread to 46: numpy/OpenBLAS accounts for the first 15, and
OCCT's OpenMP (libgomp, shipped in `cadquery_ocp.libs`) for the rest. `fork()`
duplicates libgomp's record of that worker team but none of its threads, so the
child's first parallel OCCT call blocks on a barrier no thread will ever reach.
It is a permanent stop, not a slow path: the observed child had one thread, four
seconds of CPU across forty minutes, and no work in flight.

This is a property of forking after a native library has gone multi-threaded,
not of any particular node or model. It is only hidden when the child never
reaches a parallel OCCT call — which is exactly what happens when the build
directory is already current and the child returns `CURRENT` immediately.

## Goals / Non-Goals

**Goals:**

- A build always reaches an outcome. No inherited native state can stop it.
- The same guarantee for `solid develop`, whose watch loop respawns builders
  through the identical mechanism and carries the identical latent defect.
- Keep the process-per-build-iteration structure: the exit-code outcome
  protocol, the reload semantics, and the isolation that lets a broken reload
  not poison the loop are all load-bearing and stay as they are.

**Non-Goals:**

- Making OCCT itself fork-safe, or configuring OpenMP thread counts.
- Changing node authoring, the artifact layout, caching, locking, exit codes, or
  the callback protocol.
- Removing the parent-side `resolve_node()` that produces `MODEL_NOT_FOUND`.
- Optimising build wall clock. The change is expected to cost time; measuring
  and reporting that cost is in scope, reducing it is not.

## Decisions

### Use the `spawn` start method for build subprocesses

Take an explicit `multiprocessing.get_context('spawn')` and start every builder,
viewer, and web-server subprocess from it, rather than relying on the platform
default. A spawned child is a fresh interpreter: it has no inherited libgomp
team, no inherited OpenBLAS pool, and no inherited locks.

Verified directly in the originating project before proposing: under `fork`, a
child that has done nothing but inherit the parent's post-import state hangs
indefinitely in `exportStl`; under `spawn`, the identical child exports in 0.1s
and exits 0.

*Alternatives considered.*

`forkserver` would fork children from a pristine helper process, keeping them
cheap while still avoiding the poisoned parent. It is rejected for now because
it adds a helper-process lifecycle to reason about, and because its saving
depends on preloading modules into that helper — which reintroduces the question
of what the helper has initialised, the very question this change exists to stop
asking. If measured `spawn` cost proves unacceptable, `forkserver` is the
prepared retreat, and the ratified requirement is written in terms of isolation
rather than a start method so it would not need re-ratification.

Not forking at all — running each build iteration in the command process — is
rejected: the loop depends on process death to clear module state between
iterations, and a build failure would then take the command down with it.

Avoiding the parent-side import instead of fixing the fork is rejected as
insufficient. It would treat the one import we happen to know about, and leave
the next parent-side import to reintroduce the same deadlock silently.

### Pass plain data to module-level targets, not bound methods

A spawned child reconstructs its target by pickling. `Build.builder` pickles
today, but `Develop.builder` does not: `Develop` keeps `self.parser` and an
`argparse.ArgumentParser` is unpicklable (`Can't pickle local object
'ArgumentParser.__init__.<locals>.identity'`). This is verified, not
anticipated.

So each subprocess target becomes a module-level function taking only plain
values — the node reference, the override list, the reload flag, the callback
URL. The manager object stays in the parent and is never sent anywhere. That
also removes the standing hazard of a manager growing a new unpicklable
attribute and breaking process startup at a distance.

### Guard the entry point

A spawned child re-imports the main module under the name `__mp_main__`. The
installed `solid` console script guards its body with
`if __name__ == '__main__'`, so the child imports it without re-running the CLI.
Confirmed against the installed script. Implementation must keep any
`python -m` entry path equally guarded.

## Risks / Trade-offs

- **Build wall clock regresses.** A forked child inherited the parent's already
  imported geometry stack and model; a spawned one re-imports both, on the order
  of 2.5s per render iteration in the originating project, once per artifact
  rendered. → Measure the end-to-end cold build of a real multi-part project and
  report it. If the cost is unacceptable, return the evidence to the pilot
  rather than trading correctness back.

- **A target that silently stopped being picklable breaks process startup.** →
  Targets take plain values only, and a test asserts the targets pickle, so the
  failure surfaces in the suite rather than at a user's first build.

- **`solid develop` has more subprocesses than `solid build`,** so it carries
  more of this risk while being the harder path to test end to end. → Convert
  its targets in the same change rather than leaving a half-converted module,
  and cover the picklability of every one of them.

- **The deadlock is invisible on a warm build directory,** so a regression could
  pass a suite that reuses artifacts. → The proof must render from a genuinely
  cold build directory, in a parent that has already imported the model.

## Open Questions

None outstanding for implementation. The measured cost of `spawn` is the one
number that could reopen the start-method decision.
