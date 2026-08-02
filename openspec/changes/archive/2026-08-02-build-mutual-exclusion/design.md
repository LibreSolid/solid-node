## Context

Four code paths render artifacts for a project and none of them coordinate:

- `solid develop` — `Develop` respawns a `Builder` child per render pass; the
  child publishes and then waits for a source change.
- `solid build` — `Build` runs the same `Builder` with `watch=False`.
- `solid test` — `TestRunner.build_node` calls `node.build_stls()` in process,
  writing straight into the project build directory with no staging and no
  publication step.
- `solid export` — `export_node` calls `node.build_stls()` the same way.

Two guards exist today and neither serialises a build. `.stl.lock` is a PID file
per artifact: it stops two processes rendering the same STL simultaneously, and
a locked node is *skipped*, so the second builder proceeds with the rest of the
tree. ADR-032's symlink swap makes each publication atomic and lets a loser
report a build error instead of a traceback, but it deliberately does not order
publications: whoever swaps last wins, whatever source it read.

The consequence is a lost update. A build started against source S1, overtaken
by an edit to S2 and a faster build that publishes it, still publishes S1 when
it finishes — the maker's file says S2 and the model says S1, until something
else triggers a rebuild. ADR-032 itself lists an advisory lock among the
alternatives it rejected, but rejected it only as insufficient for the
*reader* gap it was solving; it does not address ordering.

F2 (`per-file-build-publication`) removes set-atomic publication in favour of a
single build directory written one artifact at a time. At that point two
builders no longer race to swap a pointer, they write the same files, and the
lost update becomes a mixed model assembled from two sources. That is why this
cycle lands first.

## Goals / Non-Goals

**Goals:**

- Exactly one build at a time per project, across every process and every
  entry point, with no daemon, broker, socket or protocol.
- The newest source wins: a build that has been superseded while it waited does
  not publish.
- Redundant work is skipped: a builder that acquires the lock and finds the
  project already built at the current source state publishes nothing.
- No lock is held while nothing is being built — not while `solid develop`
  watches for changes, and not while `solid test` runs test methods.
- Death of a holder is not a recoverable condition to handle, because the
  kernel releases the lock.

**Non-Goals:**

- Changing the publication mechanism. The symlink swap, its race tolerance and
  its `errors.json` reporting are untouched; F2 replaces them.
- Changing `.stl.lock`. Per-artifact render locking keeps its current meaning.
- Serialising readers. Consumers do not take the lock and a browser cannot be
  made to; reader safety is ADR-032's job now and F2's later.
- Any cross-project or machine-global lock. That is ADR-017's WebSocket global
  lock, which ADR-018 removed as platform bloat.
- Filing the BUILD architecture record. PRD section 5 files D1 and D2 as one
  record because their correctness is joint; F2 writes it.

## Decisions

**D-1 — `fcntl.flock` on a file beside the build path.**
The lock file is `<published build dir>.lock` — `_build.lock` by default,
resolved from the project's *published* build directory, never from a builder's
private staging directory. Alternatives: a file inside the build directory,
rejected because publication replaces that directory (and F2 sweeps it), so the
lock would move under its holders; a PID file following the `.stl.lock` idiom,
rejected because it needs liveness checks and stale-lock reaping, which `flock`
gets from the kernel for free; a lock keyed on the source tree rather than the
build directory, rejected because `SOLID_BUILD_DIR` is what actually defines
which artifacts collide — two checkouts sharing a source path but not a build
directory do not conflict.

The lock file is created on first use and recorded in the repository's local
exclude the same way published artifacts are: the existing `<build>*` pattern
installed by `exclude_build_from_git` already covers `_build.lock`, so the call
moves to lock creation as well as publication and the working tree stays clean.

**D-2 — Blocking acquisition, not try-and-skip.**
A second builder waits. Rejected: `LOCK_NB` with an immediate skip, which would
break `solid build`'s contract that its exit status reflects whether the model
built, and would make `solid test` return a pass against artifacts nobody built.
The wait is bounded in practice by the dedup rule (D-4): the common case is that
the waiter wakes to find its work already done and returns immediately. A wait
that does not resolve immediately is logged once, so a maker never faces a
silent stall.

**D-3 — The lock is held around render-and-publish, in the process that does
it.**
In `Builder`, acquisition happens after load and assemble and release happens
after publication (or after the build error is reported), before
`wait_for_change`. In `solid test` and `solid export`, the lock wraps the
`build_stls()` call and is released before tests run or the export directory is
written. Alternative: the lifecycle parent (`Build`, `Develop`) holding the lock
across the whole render loop, rejected because `solid develop`'s waiting happens
inside the builder child — a parent-held lock inherited across `fork` would be
held for the entire idle period and block every other participant. Holding it in
the child also means `--debug-builder`, which runs the builder in process,
behaves identically.

A build that needs several render passes therefore drops the lock between
passes, because each pass is a separate process. That is deliberate and safe:
publication happens only under the lock, and a builder that lost ground between
passes stands down at its next acquisition (D-4), so no stale set can reach the
build path. Interleaved passes by two builders on the *same* source render
identical geometry and remain guarded per artifact by `.stl.lock`.

**D-4 — The dedup rule is evaluated after acquisition, from source mtimes.**
Having taken the lock, a builder answers one question: does the published state
already cover the change I woke up for?

- If the node's tracked sources on disk are newer than the source state this
  builder loaded, it is stale. It publishes nothing and reports the same
  source-changed outcome an ordinary edit produces, so the lifecycle loop
  respawns it against current source.
- If the published artifact set is already current for the loaded node under the
  existing mtime-equality rule, there is nothing to do. It publishes nothing and
  reports the model current.
- Otherwise it renders and publishes as it does today.

This reuses `node.mtime` and the mtime-equality caching already specified in the
build pipeline, so no new metadata, generation counter or build-state file
appears in the publication — an important constraint, because F2 is about to
change what a publication looks like. Alternative: recording the source mtime or
a content hash inside `viewer.json` and comparing that, rejected as a schema
change to the viewer snapshot in the cycle least able to afford one, and as
information the filesystem already carries.

**D-5 — `solid test` releases the lock before running tests.**
Building the node is exclusive; running assertions over the built artifacts is
not. A full sweep can run far longer than a build, and holding the lock across
it would make an agent's test run block the maker's next refresh — the exact
stall this sprint exists to remove. Tests then read artifacts that another
builder may republish underneath them; that exposure is unchanged from today,
where nothing serialises at all, and closing it is F2's per-artifact atomicity
(PRD acceptance criterion 5), not this cycle's.

## Risks / Trade-offs

- **A long render blocks other entry points.** A one-minute OpenSCAD render
  makes `solid test`'s build phase wait that long → mitigation: the waiter
  usually finds the work already done and returns immediately (D-4); the wait is
  logged so it is visible rather than mysterious.
- **`flock` is advisory and weak on network filesystems.** → mitigation: the
  shop is local and attended by design (PRD section 8 excludes remote floors);
  every participant is framework code and takes the lock. Documented as a
  platform assumption, not enforced.
- **Fork inheritance can extend a lock past its intended holder.** An fd open at
  `fork` time is shared, and the lock survives until every copy is closed →
  mitigation: the lock file is opened inside the process that renders, never
  before spawning a child, and is closed on release; a test covers a child
  outliving its parent's build phase.
- **Double acquisition inside one process deadlocks.** `flock` on a *second* fd
  for the same file in the same process blocks → mitigation: one acquisition
  site per entry point, and the helper is safe to re-enter within a process.
- **Mutual exclusion is per publication attempt, not per whole build.** Two
  builders can interleave render passes → accepted under D-3; correctness rests
  on publication being exclusive and stale publication being impossible, which
  is what the acceptance test for "the newest source wins" measures.
