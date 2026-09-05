# ADR-067: Fresh-Interpreter Build Subprocesses

**Status:** Accepted
**Date:** 2026-09-05

**Related to:**
- [ADR-018: Lean Framework Separation](../IPC/ADR-018-lean-framework-separation.md)
- [ADR-059: Import at the Point of Use](./ADR-059-import-at-the-point-of-use.md)

## Context and Problem Statement

`solid build` stopped, permanently, on a cold build directory in a CadQuery
project. Not a slow build — no CPU, no work in flight, no error, no timeout.
A live instance had run forty minutes on four seconds of CPU.

`Build.handle()` resolves the model in the command's own process, because
telling a missing model (exit 66) from a failed build has to happen before any
build starts. Resolving imports the model module, and importing it runs its
geometry. Measured in the originating project: a bare interpreter has 1 thread,
and 46 after `resolve_node()` — numpy/OpenBLAS accounts for the first 15, OCCT's
OpenMP (libgomp, vendored in `cadquery_ocp.libs`) for the rest.

The build itself then ran in a `multiprocessing.Process`, whose default start
method on Linux is `fork`. `fork()` copies the address space but not the
threads. The child inherited libgomp's record of a worker team none of whose
threads existed in it, and the first parallel OCCT call — tessellation during
STL export — waited on that team's barrier forever. CPython names the hazard
itself: *"This process is multi-threaded, use of fork() may lead to deadlocks in
the child."*

What made this expensive to find is that it is invisible on a warm build
directory. A child whose artifacts are current returns `CURRENT` without
tessellating anything, so it never reaches the barrier. Two projects in the same
workspace, both using `CadQueryNode`, behaved completely differently: one opened
in seconds, the other never opened at all. The difference was not their models.
It was whether their build directory was cold.

`solid develop` carried the identical defect, unfired, in its watch loop.

## Decision Drivers

- A build must reach an outcome. Publishing or failing are both fine; stopping
  forever is not, and a hang gives an agent or a shop floor nothing to act on.
- The hazard is structural, not local. Any parent-side import that touches
  geometry re-arms it, and nothing at the fork site can see that it happened.
- The process-per-iteration structure is load-bearing and must survive: exit
  codes carry `BuildOutcome`, and process death is what clears module state
  between reload attempts.
- Correctness before wall clock, with the cost measured rather than assumed.

## Considered Options

1. **Start build subprocesses from a fresh interpreter (`spawn`)** (chosen)
2. `forkserver` — fork children from a pristine helper process
3. Avoid the parent-side import that spins the pools
4. Run each build iteration in the command process, without a subprocess

## Decision Outcome

Chosen: **a fresh interpreter**, via an explicit `spawn` context in
`solid_node/core/processes.py`, used by every subprocess `solid build` and
`solid develop` start. A spawned child inherits no thread pool, no worker team,
and no lock from whatever the parent happened to import.

Verified before deciding: under `fork`, a child that has done nothing but
inherit a post-import parent hangs indefinitely in `exportStl`; under `spawn`,
the identical child exports in 0.1 s and exits 0.

A spawned child is handed its target rather than inheriting it, so every
subprocess target became a module-level function taking plain values. This was
forced, not stylistic: `Develop` holds `self.parser`, and an
`argparse.ArgumentParser` cannot be pickled (`Can't pickle local object
'ArgumentParser.__init__.<locals>.identity'`), so bound-method targets would
have broken `solid develop` outright. The command object now stays in the
parent.

**Option 3 is the one worth explaining.** Not importing the model in the parent
would have fixed the observed hang with no cost at all, and it was rejected
anyway: it treats the one import we happened to find. The next parent-side
import that touches geometry re-arms the same deadlock, silently, and the
symptom is a hang with no error to trace back to the import that caused it. The
guarantee has to hold regardless of what the parent imported, or it is not a
guarantee.

Option 2 stays available. It would keep children cheap by forking from a
pristine helper, but its saving depends on preloading modules into that helper —
which reintroduces exactly the question this decision exists to stop asking:
what has that process already initialised? The behavioural requirement is
written as isolation rather than as a start method, so moving to `forkserver`
would not need re-ratification.

Option 4 was rejected because a build failure would then take the command down
with it, and the reload path depends on process death to clear module state.

## Consequences

- A build always reaches an outcome. What the parent imported no longer decides
  whether the build completes.
- **Builds cost more wall clock.** A forked child inherited the parent's
  imported geometry stack and model for free; a spawned one re-imports both,
  roughly 2.5 s, once per render iteration — and the build loop runs one
  iteration per artifact rendered. Measured on the originating project: a cold
  build takes 93.3 s and publishes 12 STLs and its manifest; a warm rebuild
  takes 14.1 s. There is no baseline to compare against, because on this
  project the pre-change build completes neither — it was killed after 203.5 s
  having produced nothing. This is the price of the guarantee and was ratified
  as such.
- Subprocess targets are constrained: plain values only, module-level functions
  only. A test pickles every target the two commands actually pass, so a target
  that stops being reconstructable fails in the suite rather than at a user's
  first build.
- The fix generalises past the reported symptom. `solid develop` had the same
  latent deadlock and is closed by the same change.
- The regression test is slow by construction — proving a process does not hang
  means waiting for it — and must render from a genuinely cold build directory,
  because a warm one passes without exercising anything.
- `solid`'s console script guards its body with `if __name__ == '__main__'`, so
  the re-import a spawned child performs does not re-run the CLI. Any future
  entry point must keep that guard.

## References

- `solid_node/core/processes.py` — the start method and why it is not the default
- `solid_node/manager/build.py`, `solid_node/manager/develop.py` — module-level
  subprocess targets
- `tests/test_build_subprocess_isolation.py` — outcome and reconstructability
- OpenSpec change `fork-safe-build-subprocess`, capability `build-pipeline`
- Originating evidence: project 3DPrintedClocks, `design/wall_clock_01`,
  opened through the LibreSolid Studio shop floor
